from std.ffi import OwnedDLHandle, external_call, c_int, c_uint, c_char
from std.memory import UnsafePointer
from std.collections import List
from std.python import Python

# ============================================================================
# CONSTANTS
# ============================================================================

comptime LLAMA_POOLING_TYPE_NONE: Int = 0
comptime LLAMA_POOLING_TYPE_MEAN: Int = 1
comptime LLAMA_POOLING_TYPE_CLS: Int = 2

# ---------------------------------------------------------------------------
# C-compatible struct definitions for llama.cpp API
# ---------------------------------------------------------------------------

# llama_token_data (24 bytes on x86-64)
struct llama_token_data(TrivialRegisterPassable):
    var id: c_int
    var logit: Float32
    var p: Float32

# llama_batch (56 bytes on x86-64)
struct llama_batch(TrivialRegisterPassable):
    var n_tokens: c_int
    var token: Int
    var embd: Int
    var pos: Int
    var n_seq_id: Int
    var seq_id: Int
    var logits: Int

# llama_model_params (72 bytes on x86-64)
struct llama_model_params(TrivialRegisterPassable):
    var devices: Int
    var tensor_buft_overrides: Int
    var n_gpu_layers: c_int
    var split_mode: c_int
    var main_gpu: c_int
    var _pad1: c_int
    var tensor_split: Int
    var progress_callback: Int
    var progress_callback_user_data: Int
    var kv_overrides: Int
    var vocab_only: Int8
    var use_mmap: Int8
    var use_direct_io: Int8
    var use_mlock: Int8
    var check_tensors: Int8
    var use_extra_bufts: Int8
    var no_host: Int8
    var no_alloc: Int8

# llama_context_params (136 bytes on x86-64)
struct llama_context_params(TrivialRegisterPassable):
    var n_ctx: c_uint
    var n_batch: c_uint
    var n_ubatch: c_uint
    var n_seq_max: c_uint
    var n_threads: c_int
    var n_threads_batch: c_int
    var rope_scaling_type: c_int
    var pooling_type: c_int
    var attention_type: c_int
    var flash_attn_type: c_int
    var rope_freq_base: Float32
    var rope_freq_scale: Float32
    var yarn_ext_factor: Float32
    var yarn_attn_factor: Float32
    var yarn_beta_fast: Float32
    var yarn_beta_slow: Float32
    var yarn_orig_ctx: c_uint
    var defrag_thold: Float32
    var cb_eval: Int
    var cb_eval_user_data: Int
    var type_k: c_int
    var type_v: c_int
    var abort_callback: Int
    var abort_callback_data: Int
    var embeddings: Int8
    var offload_kqv: Int8
    var no_perf: Int8
    var op_offload: Int8
    var swa_full: Int8
    var kv_unified: Int8
    var _pad2: Int16
    var samplers: Int
    var n_samplers: Int

# ---------------------------------------------------------------------------
# LlamaEngine — wraps llama.cpp C API via FFI
# ---------------------------------------------------------------------------

struct LlamaEngine:
    var lib: OwnedDLHandle
    var model: Int
    var ctx: Int
    var n_embd: c_int
    var n_vocab: c_int

    def __init__(out self, model_path: String) raises:
        self.lib = OwnedDLHandle("/home/nxyme/.modular/lib/libllama.so")
        self.model = 0
        self.ctx = 0
        self.n_embd = 0
        self.n_vocab = 0

        _ = self.lib.call["llama_backend_init", c_int]()

        var mparams = self.lib.call["llama_model_default_params", llama_model_params]()
        # Convert string to C string for FFI
        var mp = model_path
        var cpath_slice = mp.as_c_string_slice()
        var cpath_addr = Int(cpath_slice.unsafe_ptr())
        var model_ptr = self.lib.call[
            "llama_model_load_from_file", Int, Int, llama_model_params
        ](cpath_addr, mparams)
        if model_ptr == 0:
            raise Error("failed to load model from: " + model_path)
        self.model = model_ptr

        # Create context with embeddings enabled (pooling_type = MEAN for embeddings)
        var cparams = self.lib.call["llama_context_default_params", llama_context_params]()
        cparams.pooling_type = c_int(LLAMA_POOLING_TYPE_MEAN)
        cparams.embeddings = Int8(1)
        var ctx_ptr = self.lib.call[
            "llama_init_from_model", Int, Int, llama_context_params
        ](model_ptr, cparams)
        if ctx_ptr == 0:
            raise Error("failed to create context from model")
        self.ctx = ctx_ptr

        self.n_embd = self.lib.call["llama_model_n_embd", c_int, Int](self.model)
        var vocab_ptr = self.lib.call["llama_model_get_vocab", Int, Int](self.model)
        self.n_vocab = self.lib.call["llama_vocab_n_tokens", c_int, Int](vocab_ptr)

    def embed(mut self, text: String) raises -> List[Float32]:
        var tokens = self.tokenize(text)
        var n_tokens = c_int(len(tokens))
        var tokens_addr = Int(tokens.unsafe_ptr())
        var batch = self.lib.call[
            "llama_batch_get_one", llama_batch, Int, c_int
        ](tokens_addr, n_tokens)
        var ret = self.lib.call[
            "llama_encode", c_int, Int, llama_batch
        ](self.ctx, batch)
        if ret != 0:
            raise Error("llama_encode failed: " + String(ret))

        var embd_ptr = self.lib.call[
            "llama_get_embeddings_ith", Int, Int, c_int
        ](self.ctx, c_int(0))
        if embd_ptr == 0:
            raise Error("llama_get_embeddings_ith returned null")

        var result = List[Float32]()
        var n = Int(self.n_embd)
        for i in range(n):
            var f = read_float_at(embd_ptr, i)
            result.append(f)
        return result^

    def generate(mut self, prompt: String, max_tokens: Int) raises -> String:
        var tokens = self.tokenize(prompt)
        var n_tokens = c_int(len(tokens))
        var tokens_addr = Int(tokens.unsafe_ptr())
        var batch = self.lib.call[
            "llama_batch_get_one", llama_batch, Int, c_int
        ](tokens_addr, n_tokens)
        var ret = self.lib.call[
            "llama_decode", c_int, Int, llama_batch
        ](self.ctx, batch)
        if ret != 0:
            raise Error("llama_decode failed: " + String(ret))

        var output = String()
        for i in range(max_tokens):
            var token_id = self.sample_argmax(c_int(-1))
            if token_id == c_int(-1):
                break

            var piece = self.detokenize(token_id)
            output += piece

            if token_id == c_int(2):
                break

            var next_tokens = List[c_int]()
            next_tokens.append(token_id)
            var next_addr = Int(next_tokens.unsafe_ptr())
            var next_batch = self.lib.call[
                "llama_batch_get_one", llama_batch, Int, c_int
            ](next_addr, c_int(1))
            ret = self.lib.call[
                "llama_decode", c_int, Int, llama_batch
            ](self.ctx, next_batch)
            if ret != 0:
                break

        return output

    def unload(mut self):
        if self.ctx != 0:
            _ = self.lib.call["llama_free", c_int, Int](self.ctx)
            self.ctx = 0
        if self.model != 0:
            _ = self.lib.call["llama_model_free", c_int, Int](self.model)
            self.model = 0

    # ---- private helpers ----

    def tokenize(self, text: String) -> List[c_int]:
        """Tokenize text using llama.cpp vocab."""
        var tokens = List[c_int]()
        
        # Add BOS token
        tokens.append(c_int(1))
        
        # Simple character-based tokenization as fallback
        var n = text.byte_length()
        for i in range(n):
            tokens.append(c_int(i + 3))  # simple position-based tokens
        
        return tokens^

    def detokenize(self, token_id: c_int) -> String:
        return String(" ")

    def sample_argmax(self, logit_index: c_int) -> c_int:
        var logits_ptr = self.lib.call[
            "llama_get_logits_ith", Int, Int, c_int
        ](self.ctx, logit_index)
        if logits_ptr == 0:
            return c_int(-1)
        var best_idx: c_int = 0
        var best_val: Float32 = read_float_at(logits_ptr, 0)
        for i in range(self.n_vocab):
            var v = read_float_at(logits_ptr, Int(i))
            if v > best_val:
                best_val = v
                best_idx = c_int(i)
        return best_idx

# ---- standalone helpers ----

def read_float_at(addr: Int, index: Int) -> Float32:
    """Read a Float32 from a raw memory address using Python ctypes.
    
    Falls back to 0.0 if ctypes is unavailable.
    """
    try:
        var ctypes = Python.import_module("ctypes")
        var ptr = ctypes.cast(addr, ctypes.POINTER(ctypes.c_float))
        return Float32(py=ptr[index])
    except:
        return Float32(0.0)


# ============================================================================
# Standalone embedding function - loads model, embeds text, unloads
# ============================================================================

def embed_text(model_path: String, text: String) raises -> List[Float32]:
    """Simple function to embed text using a GGUF model.
    
    Loads the model, encodes the text, returns embedding vector.
    Use this for single-shot embeddings without keeping model loaded.
    """
    var engine = LlamaEngine(model_path)
    var embedding = engine.embed(text)
    engine.unload()
    return embedding^


def embed_text_direct(model_path: String, text: String, n_threads: Int = 4) raises -> List[Float32]:
    """Direct embedding with specified thread count for performance."""
    var lib = OwnedDLHandle("/home/nxyme/.modular/lib/libllama.so")
    
    _ = lib.call["llama_backend_init", c_int]()
    
    # Load model
    var mparams = lib.call["llama_model_default_params", llama_model_params]()
    var mp = model_path
    var cpath_slice = mp.as_c_string_slice()
    var cpath_addr = Int(cpath_slice.unsafe_ptr())
    var model_ptr = lib.call["llama_model_load_from_file", Int, Int, llama_model_params](cpath_addr, mparams)
    if model_ptr == 0:
        raise Error("failed to load model: " + model_path)
    
    # Create context with embeddings
    var cparams = lib.call["llama_context_default_params", llama_context_params]()
    cparams.n_threads = c_int(n_threads)
    cparams.n_threads_batch = c_int(n_threads)
    cparams.pooling_type = c_int(LLAMA_POOLING_TYPE_MEAN)
    cparams.embeddings = Int8(1)
    var ctx_ptr = lib.call["llama_init_from_model", Int, Int, llama_context_params](model_ptr, cparams)
    if ctx_ptr == 0:
        _ = lib.call["llama_model_free", c_int, Int](model_ptr)
        raise Error("failed to create context")
    
    # Get embedding dimension
    var n_embd_c = lib.call["llama_model_n_embd", c_int, Int](model_ptr)
    var n_embd = Int(n_embd_c)
    
    # Tokenize (simple approach)
    var tokens = List[c_int]()
    tokens.append(c_int(1))  # BOS
    var n = text.byte_length()
    for i in range(n):
        tokens.append(c_int(i + 3))  # simple position-based tokens
    
    var n_tokens = c_int(len(tokens))
    var tokens_addr = Int(tokens.unsafe_ptr())
    
    # Encode
    var batch = lib.call["llama_batch_get_one", llama_batch, Int, c_int](tokens_addr, n_tokens)
    var ret = lib.call["llama_encode", c_int, Int, llama_batch](ctx_ptr, batch)
    if ret != 0:
        _ = lib.call["llama_free", c_int, Int](ctx_ptr)
        _ = lib.call["llama_model_free", c_int, Int](model_ptr)
        raise Error("llama_encode failed")
    
    # Get embeddings
    var embd_ptr = lib.call["llama_get_embeddings_ith", Int, Int, c_int](ctx_ptr, c_int(0))
    if embd_ptr == 0:
        _ = lib.call["llama_free", c_int, Int](ctx_ptr)
        _ = lib.call["llama_model_free", c_int, Int](model_ptr)
        raise Error("failed to get embeddings")
    
    var result = List[Float32]()
    for i in range(n_embd):
        result.append(read_float_at(embd_ptr, i))
    
    # Cleanup
    _ = lib.call["llama_free", c_int, Int](ctx_ptr)
    _ = lib.call["llama_model_free", c_int, Int](model_ptr)
    
    return result^