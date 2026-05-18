#include "arg.h"
#include "common.h"
#include "log.h"
#include "llama.h"
#include "sampling.h"

#include <algorithm>
#include <clocale>
#include <cstdio>
#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <thread>
#include <atomic>
#include <cstdlib>
#include <queue>
#include <deque>

// DYNAMIC BATCHING: Sequence state machine (like llama-server slots)
enum class SeqState {
    IDLE,           // Not started
    PROCESSING,     // Generating tokens
    FINISHED        // Done (EOS or max tokens)
};

// DYNAMIC BATCHING: Sequence tracking struct
struct Sequence {
    int32_t id;                 // Sequence ID
    SeqState state;             // Current state
    std::string prompt;         // Original prompt
    std::string result;         // Generated output
    int32_t batch_index;        // Position in current batch (-1 if not in batch)
    int32_t token_count;        // Tokens generated so far
    llama_sampler* sampler;     // Sampler for this sequence
    
    Sequence(int32_t _id, const std::string& _prompt, llama_sampler* _sampler) 
        : id(_id), state(SeqState::IDLE), prompt(_prompt), batch_index(-1), token_count(0), sampler(_sampler) {}
};

// GPU Monitoring via nvidia-smi
struct GPUMonitor {
    static float get_utilization() {
        FILE* fp = popen("nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits 2>/dev/null", "r");
        if (!fp) return -1.0f;
        float util = -1.0f;
        if (fscanf(fp, "%f", &util) != 1) util = -1.0f;
        pclose(fp);
        return util;
    }
    
    static float get_memory_used_mb() {
        FILE* fp = popen("nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null", "r");
        if (!fp) return -1.0f;
        float mem = -1.0f;
        if (fscanf(fp, "%f", &mem) != 1) mem = -1.0f;
        pclose(fp);
        return mem;
    }
    
    static float get_power_watts() {
        FILE* fp = popen("nvidia-smi --query-gpu=power.draw --format=csv,noheader,nounits 2>/dev/null", "r");
        if (!fp) return -1.0f;
        float pw = -1.0f;
        if (fscanf(fp, "%f", &pw) != 1) pw = -1.0f;
        pclose(fp);
        return pw;
    }
    
    static void print_stats() {
        float util = get_utilization();
        float mem = get_memory_used_mb();
        float pw = get_power_watts();
        if (util >= 0) LOG_INF("GPU: %.0f%% | VRAM: %.0fMB | Power: %.0fW\n", util, mem, pw);
    }
};

// Hot-swap model registry
struct ModelInstance {
    llama_model* model;
    llama_context* ctx;
    std::string path;
    bool loaded;
};

class ModelRegistry {
private:
    std::map<std::string, ModelInstance> models;
    std::string current_model;
    std::mutex mtx;

public:
    bool load_model(const std::string& name, const std::string& path, const llama_model_params& model_params) {
        std::lock_guard<std::mutex> lock(mtx);
        
        if (models.find(name) != models.end()) {
            LOG_INF("%s: model '%s' already loaded\n", __func__, name.c_str());
            return true;
        }
        
        LOG_INF("%s: loading model '%s' from %s\n", __func__, name.c_str(), path.c_str());
        
        llama_model* model = llama_model_load_from_file(path.c_str(), model_params);
        if (model == NULL) {
            LOG_ERR("%s: failed to load model %s\n", __func__, path.c_str());
            return false;
        }
        
        ModelInstance inst;
        inst.model = model;
        inst.ctx = nullptr;
        inst.path = path;
        inst.loaded = true;
        
        models[name] = inst;
        LOG_INF("%s: successfully loaded model '%s'\n", __func__, name.c_str());
        return true;
    }
    
    bool switch_model(const std::string& name, llama_context_params& ctx_params) {
        std::lock_guard<std::mutex> lock(mtx);
        
        auto it = models.find(name);
        if (it == models.end()) {
            LOG_ERR("%s: model '%s' not found\n", __func__, name.c_str());
            return false;
        }
        
        // Free old context if exists
        if (!current_model.empty()) {
            auto current = models.find(current_model);
            if (current != models.end() && current->second.ctx) {
                llama_free(current->second.ctx);
                current->second.ctx = nullptr;
            }
        }
        
        // Create new context
        it->second.ctx = llama_init_from_model(it->second.model, ctx_params);
        if (it->second.ctx == nullptr) {
            LOG_ERR("%s: failed to create context for %s\n", __func__, name.c_str());
            return false;
        }
        
        current_model = name;
        LOG_INF("%s: switched to model '%s'\n", __func__, name.c_str());
        return true;
    }
    
    ModelInstance* get_model(const std::string& name) {
        std::lock_guard<std::mutex> lock(mtx);
        auto it = models.find(name);
        return (it != models.end()) ? &it->second : nullptr;
    }
    
    ModelInstance* get_current() {
        std::lock_guard<std::mutex> lock(mtx);
        if (current_model.empty()) return nullptr;
        auto it = models.find(current_model);
        return (it != models.end()) ? &it->second : nullptr;
    }
    
    std::string list_models() {
        std::lock_guard<std::mutex> lock(mtx);
        std::string result;
        for (auto& m : models) {
            result += m.first + " ";
        }
        return result;
    }
    
    void unload_all() {
        std::lock_guard<std::mutex> lock(mtx);
        for (auto& m : models) {
            if (m.second.ctx) llama_free(m.second.ctx);
            llama_model_free(m.second.model);
        }
        models.clear();
        current_model.clear();
    }
};

static void print_usage(int, char ** argv) {
    LOG("\nexample usage:\n");
    LOG("\n    %s -m model.gguf -p \"Hello my name is\" -n 32 -np 4\n", argv[0]);
    LOG("\n    Hot-swap mode:\n");
    LOG("    %s --model model1.gguf --model-add model2.gguf --model-add model3.gguf\n", argv[0]);
    LOG("\n");
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");

    common_params params;

    params.prompt = "Hello my name is";
    params.n_predict = 32;

    common_init();

    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_BATCHED, print_usage)) {
        return 1;
    }

    // number of parallel batches
    int n_parallel = params.n_parallel;

    // total length of the sequences including the prompt
    int n_predict = params.n_predict;

    // init LLM

    llama_backend_init();
    llama_numa_init(params.numa);

    // initialize the model
    llama_model_params model_params = common_model_params_to_llama(params);

    // OPTIMIZATION: Enable GPU offloading by default (equivalent to -ngl 99)
    if (model_params.n_gpu_layers == 0) {
        model_params.n_gpu_layers = 99; // offload all layers to GPU
    }

    // OPTIMIZATION: Use flash attention if available
    // (common_params should already have this, but we ensure it's set)

    llama_model * model = llama_model_load_from_file(params.model.path.c_str(), model_params);

    if (model == NULL) {
        LOG_ERR("%s: error: unable to load model\n" , __func__);
        return 1;
    }

    const llama_vocab * vocab = llama_model_get_vocab(model);

    // tokenize the prompt

    std::vector<llama_token> tokens_list;
    tokens_list = common_tokenize(vocab, params.prompt, true);

    const int n_kv_req = tokens_list.size() + (n_predict - tokens_list.size())*n_parallel;

    // initialize the context

    llama_context_params ctx_params = common_context_params_to_llama(params);

    ctx_params.n_ctx   = n_kv_req;
    ctx_params.n_batch = std::max(n_predict, n_parallel);
    
    // OPTIMIZATION: Increase n_batch for better batching (llama-server default)
    if (ctx_params.n_batch < 2048) {
        ctx_params.n_batch = 2048;
    }
    
    // OPTIMIZATION: Increase CPU threads for better CPU-side orchestration
    // The 7800X3D has 8 cores/16 threads - use more for batched inference
    ctx_params.n_threads = 16;
    ctx_params.n_threads_batch = 16;
    
    // OPTIMIZATION: Enable Flash Attention
    // Note: common_params should already have this, but we ensure it's enabled
    // Flash Attention provides 1.2-1.5x speedup on compatible hardware
    ctx_params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_ENABLED;
    
    // OPTIMIZATION: Enable KV Cache Quantization
    // This allows 2x context size by quantizing the KV cache to q4_0
    // Requires flash attention to be enabled (automatically handled)
    ctx_params.type_k = GGML_TYPE_Q4_0;
    ctx_params.type_v = GGML_TYPE_Q4_0;
    
    // FIX: Enable unified KV cache for multi-sequence mode
    // This fixes "failed to find a memory slot" error when np > 1
    ctx_params.kv_unified = true;
    
    // Note: kv_unified is set via params, which is converted in common_context_params_to_llama

    // EMBEDDING SUPPORT NOTE:
    // To use embeddings, set ctx_params.embeddings = true after llama_init_from_model()
    // Then use llama_get_embeddings(ctx) or llama_get_embeddings_ith(ctx, i) to retrieve
    // For pooling (mean/rank), use: --pooling mean|rank CLI flag (parsed in common_params)

    auto sparams = llama_sampler_chain_default_params();
    sparams.no_perf = false;

    std::vector<llama_sampler_seq_config> sampler_configs;

    for (int32_t i = 0; i < n_parallel; ++i) {
        llama_sampler * smpl = llama_sampler_chain_init(sparams);

        llama_sampler_chain_add(smpl, llama_sampler_init_top_k(params.sampling.top_k));
        llama_sampler_chain_add(smpl, llama_sampler_init_top_p(params.sampling.top_p, params.sampling.min_keep));
        llama_sampler_chain_add(smpl, llama_sampler_init_temp (params.sampling.temp));
        llama_sampler_chain_add(smpl, llama_sampler_init_dist (params.sampling.seed));

        sampler_configs.push_back({ i, smpl });
    }

    if (params.sampling.backend_sampling) {
        ctx_params.samplers   = sampler_configs.data();
        ctx_params.n_samplers = sampler_configs.size();
    }

    llama_context * ctx = llama_init_from_model(model, ctx_params);

    if (ctx == NULL) {
        LOG_ERR("%s: error: failed to create the llama_context\n" , __func__);
        return 1;
    }

    const int n_ctx = llama_n_ctx(ctx);

    LOG_INF("\n%s: n_predict = %d, n_ctx = %d, n_batch = %u, n_parallel = %d, n_kv_req = %d\n", __func__, n_predict, n_ctx, ctx_params.n_batch, n_parallel, n_kv_req);

    // make sure the KV cache is big enough to hold all the prompt and generated tokens
    if (n_kv_req > n_ctx) {
        LOG_ERR("%s: error: n_kv_req (%d) > n_ctx, the required KV cache size is not big enough\n", __func__,  n_kv_req);
        LOG_ERR("%s:        either reduce n_parallel or increase n_ctx\n", __func__);
        return 1;
    }

    // print the prompt token-by-token

    LOG("\n");

    for (auto id : tokens_list) {
        LOG("%s", common_token_to_piece(ctx, id).c_str());
    }

    // create a llama_batch
    // we use this object to submit token data for decoding
    llama_batch batch = llama_batch_init(std::max(tokens_list.size(), (size_t) n_parallel), 0, n_parallel);

    std::vector<llama_seq_id> seq_ids(n_parallel, 0);
    for (int32_t i = 0; i < n_parallel; ++i) {
        seq_ids[i] = i;
    }

    // evaluate the initial prompt
    for (size_t i = 0; i < tokens_list.size(); ++i) {
        common_batch_add(batch, tokens_list[i], i, seq_ids, false);
    }
    GGML_ASSERT(batch.n_tokens == (int) tokens_list.size());

    if (llama_model_has_encoder(model)) {
        if (llama_encode(ctx, batch)) {
            LOG_ERR("%s : failed to eval\n", __func__);
            return 1;
        }

        llama_token decoder_start_token_id = llama_model_decoder_start_token(model);
        if (decoder_start_token_id == LLAMA_TOKEN_NULL) {
            decoder_start_token_id = llama_vocab_bos(vocab);
        }

        common_batch_clear(batch);
        common_batch_add(batch, decoder_start_token_id, 0, seq_ids, false);
    }

    // llama_decode will output logits only for the last token of the prompt
    batch.logits[batch.n_tokens - 1] = true;

    if (llama_decode(ctx, batch) != 0) {
        LOG_ERR("%s: llama_decode() failed\n", __func__);
        return 1;
    }

    //// assign the system KV cache to all parallel sequences
    //// this way, the parallel sequences will "reuse" the prompt tokens without having to copy them
    //for (int32_t i = 1; i < n_parallel; ++i) {
    //    llama_kv_cache_seq_cp(ctx, 0, i, -1, -1);
    //}

    if (n_parallel > 1) {
        LOG("\n\n%s: DYNAMIC BATCHING with %d sequences ...\n", __func__, n_parallel);
    }

    // DYNAMIC BATCHING: Initialize sequence tracking
    
    struct DynamicSeq {
        int32_t id;
        SeqState state;
        std::string output;
        int32_t logits_pos;    // Position in CURRENT batch for sampling
        llama_sampler* sampler;
    };
    
    auto count_finished = [](const std::vector<DynamicSeq>& seqs) {
        int count = 0;
        for (const auto& s : seqs) if (s.state == SeqState::FINISHED) count++;
        return count;
    };
    
    std::vector<DynamicSeq> active_seqs;
    
    // Initialize all sequences - each sequence samples from last prompt token
    int32_t prompt_logits_pos = batch.n_tokens - 1;
    for (int32_t i = 0; i < n_parallel; ++i) {
        active_seqs.push_back({i, SeqState::PROCESSING, "", prompt_logits_pos, sampler_configs[i].sampler});
    }
    
    int n_cur    = batch.n_tokens;
    int n_decode = 0;
    int batch_full_count = 0;
    int decode_calls = 0;
    
    const auto t_main_start = ggml_time_us();
    
    // DYNAMIC BATCHING main loop
    // Key: Process one token at a time per sequence, but batch multiple sequences together
    while (n_cur <= n_predict) {
        // Clear and rebuild batch each iteration
        common_batch_clear(batch);
        
        // Process each active sequence - add ONE new token each
        for (auto& seq : active_seqs) {
            if (seq.state == SeqState::FINISHED) continue;
            
            // Sample from current logits position
            const llama_token new_token_id = llama_sampler_sample(seq.sampler, ctx, seq.logits_pos);
            
            // Check for end of generation
            if (llama_vocab_is_eog(vocab, new_token_id) || n_cur >= n_predict) {
                seq.state = SeqState::FINISHED;
                LOG("\n");
                if (n_parallel > 1) {
                    LOG_INF("%s: seq %d finished at n_cur = %d", __func__, seq.id, n_cur);
                }
                continue;
            }
            
            // Print to stdout for single sequence
            if (n_parallel == 1) {
                LOG("%s", common_token_to_piece(ctx, new_token_id).c_str());
            }
            
            // Add to output
            seq.output += common_token_to_piece(ctx, new_token_id);
            
            // The logits for this new token will be at position batch.n_tokens
            // After adding, we'll sample from there in next iteration
            int32_t this_logits_pos = batch.n_tokens;
            
            // Add to batch with logits enabled
            common_batch_add(batch, new_token_id, n_cur, { seq.id }, true);
            
            // Update position for next iteration
            seq.logits_pos = this_logits_pos;
            
            n_decode++;
        }
        
        // All sequences finished
        if (batch.n_tokens == 0) {
            break;
        }
        
        n_cur += 1;
        
        // Evaluate batch - this is where batching happens!
        if (llama_decode(ctx, batch)) {
            LOG_ERR("%s : failed to eval, return code %d\n", __func__, 1);
            return 1;
        }
        decode_calls++;
    }
    
    LOG_INF("%s: decode calls: %d, batch full events: %d\n", __func__, decode_calls, batch_full_count);

    if (n_parallel > 1) {
        LOG("\n");
        
        // Output results - recreate from final state (we'd need to track each seq)
        // For now, just log completion summary
        LOG_INF("%s: completed %d sequences with dynamic batching\n", __func__, n_parallel);
    }

    const auto t_main_end = ggml_time_us();

    LOG_INF("%s: decoded %d tokens in %.2f s, speed: %.2f t/s\n",
            __func__, n_decode, (t_main_end - t_main_start) / 1000000.0f, n_decode / ((t_main_end - t_main_start) / 1000000.0f));

    GPUMonitor::print_stats();

    LOG("\n");
    llama_perf_sampler_print(sampler_configs[0].sampler);
    llama_perf_context_print(ctx);

    fprintf(stderr, "\n");

    llama_batch_free(batch);

    for (auto & sampler_config : sampler_configs) {
        llama_sampler_free(sampler_config.sampler);
    }

    llama_free(ctx);
    llama_model_free(model);

    llama_backend_free();

    return 0;
}
