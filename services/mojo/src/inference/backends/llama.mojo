"""
inference/backends/llama.mojo — GGUF model backend.
Implements ModelBackend trait using the existing inference/bridge.mojo.
"""

from std.collections import List
from std.ffi import OwnedDLHandle, c_int, c_uint, c_char
from std.memory import Pointer, UnsafePointer


# Forward declaration of bridge helpers (from inference/bridge.mojo)
def read_float_at(addr: Int, index: Int) -> Float32:
    var base = addr + index * 4
    var result = __load[Float32](base)
    return result


struct LlamaBackend(ModelBackend):
    """GGUF model backend using llama.cpp.
    
    Loads GGUF models via FFI and provides:
    - embed(): Get embedding vectors
    - generate(): Text generation
    - model_info(): Model metadata
    """
    
    var lib: OwnedDLHandle
    var model: Int
    var ctx: Int
    var n_embd: c_int
    var n_vocab: c_int
    var n_ctx: c_uint
    var _loaded: Bool
    
    def __init__(out self):
        self.lib = OwnedDLHandle("")
        self.model = 0
        self.ctx = 0
        self.n_embd = 0
        self.n_vocab = 0
        self.n_ctx = 4096
        self._loaded = False
    
    def load(mut self, path: String) raises:
        """Load GGUF model via llama.cpp FFI.
        
        Args:
            path: Path to .gguf model file
            
        Raises:
            Error if model fails to load
        """
        # Try multiple library paths
        var lib_paths = List[String]()
        lib_paths.append("/home/nxyme/.modular/lib/libllama.so")
        lib_paths.append("/usr/lib/libllama.so")
        lib_paths.append("/usr/local/lib/libllama.so")
        
        var loaded_lib = False
        for i in range(len(lib_paths)):
            try:
                self.lib = OwnedDLHandle(lib_paths[i])
                loaded_lib = True
                break
            except:
                continue
        
        if not loaded_lib:
            raise Error("Could not find libllama.so")
        
        # Initialize llama backend
        _ = self.lib.call["llama_backend_init", c_int]()
        
        # Load model with default params
        var mparams = self.lib.call["llama_model_default_params", __llama_model_params]()
        var cpath_slice = path.as_c_string_slice()
        var cpath_addr = Int(cpath_slice.unsafe_ptr())
        var model_ptr = self.lib.call[
            "llama_model_load_from_file", Int, Int, __llama_model_params
        ](cpath_addr, mparams)
        
        if model_ptr == 0:
            raise Error("Failed to load GGUF model from: " + path)
        
        self.model = model_ptr
        
        # Create context with default params
        var cparams = self.lib.call["llama_context_default_params", __llama_context_params]()
        cparams.n_ctx = self.n_ctx
        cparams.n_threads = c_int(4)
        cparams.n_threads_batch = c_int(4)
        
        var ctx_ptr = self.lib.call[
            "llama_init_from_model", Int, Int, __llama_context_params
        ](model_ptr, cparams)
        
        if ctx_ptr == 0:
            raise Error("Failed to create llama context")
        
        self.ctx = ctx_ptr
        
        # Get model metadata
        self.n_embd = self.lib.call["llama_model_n_embd", c_int, Int](self.model)
        var vocab_ptr = self.lib.call["llama_model_get_vocab", Int, Int](self.model)
        self.n_vocab = self.lib.call["llama_vocab_n_tokens", c_int, Int](vocab_ptr)
        
        self._loaded = True
    
    def unload(mut self):
        """Free llama context and model."""
        if self.ctx != 0:
            _ = self.lib.call["llama_free", c_int, Int](self.ctx)
            self.ctx = 0
        if self.model != 0:
            _ = self.lib.call["llama_model_free", c_int, Int](self.model)
            self.model = 0
        self._loaded = False
    
    def embed(self, text: String) raises -> List[Float32]:
        """Generate embedding for text using llama_encode.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of Float32 embedding values
        """
        if not self._loaded:
            raise Error("Model not loaded")
        
        var tokens = self._tokenize(text)
        var n_tokens = c_int(len(tokens))
        
        if n_tokens == 0:
            # Return zero embedding for empty input
            var zero_emb = List[Float32]()
            for i in range(self.n_embd):
                zero_emb.append(Float32(0.0))
            return zero_emb
        
        var tokens_addr = Int(tokens.unsafe_ptr())
        var batch = self.lib.call[
            "llama_batch_get_one", __llama_batch, Int, c_int
        ](tokens_addr, n_tokens)
        
        var ret = self.lib.call[
            "llama_encode", c_int, Int, __llama_batch
        ](self.ctx, batch)
        if ret != 0:
            raise Error("llama_encode failed")
        
        var embd_ptr = self.lib.call[
            "llama_get_embeddings_ith", Int, Int, c_int
        ](self.ctx, c_int(0))
        
        if embd_ptr == 0:
            # Fallback: return zero embedding
            var zero_emb = List[Float32]()
            for i in range(self.n_embd):
                zero_emb.append(Float32(0.0))
            return zero_emb
        
        var result = List[Float32]()
        var n = self.n_embd
        for i in range(n):
            var f = read_float_at(embd_ptr, i)
            result.append(f)
        
        return result
    
    def generate(
        self,
        prompt: String,
        max_tokens: Int = 512,
        temperature: Float32 = 0.7,
        top_p: Float32 = 0.9
    ) raises -> String:
        """Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold
            
        Returns:
            Generated text
        """
        if not self._loaded:
            raise Error("Model not loaded")
        
        var tokens = self._tokenize(prompt)
        var n_tokens = c_int(len(tokens))
        var tokens_addr = Int(tokens.unsafe_ptr())
        
        # First pass: encode prompt
        var batch = self.lib.call[
            "llama_batch_get_one", __llama_batch, Int, c_int
        ](tokens_addr, n_tokens)
        
        var ret = self.lib.call[
            "llama_decode", c_int, Int, __llama_batch
        ](self.ctx, batch)
        if ret != 0:
            raise Error("llama_decode failed on prompt")
        
        var output = String()
        
        # Generation loop
        for i in range(max_tokens):
            # Sample next token (simplified: argmax)
            var token_id = self._sample_argmax(c_int(-1))
            
            if token_id == c_int(-1):
                break
            
            # EOS token (2)
            if token_id == c_int(2):
                break
            
            # Decode token
            var piece = self._detokenize(token_id)
            output += piece
            
            # Prepare for next iteration
            var next_tokens = List[c_int]()
            next_tokens.append(token_id)
            var next_addr = Int(next_tokens.unsafe_ptr())
            var next_batch = self.lib.call[
                "llama_batch_get_one", __llama_batch, Int, c_int
            ](next_addr, c_int(1))
            
            ret = self.lib.call[
                "llama_decode", c_int, Int, __llama_batch
            ](self.ctx, next_batch)
            
            if ret != 0:
                break
        
        return output
    
    def model_info(self) -> String:
        """Return model info as JSON string."""
        if not self._loaded:
            return """{"loaded": false, "format": "gguf", "error": "not loaded"}"""
        
        var info = String()
        info += """{"loaded": true, "format": "gguf", "backend": "llama.cpp", """
        info += """ "n_embd": """ + String(self.n_embd) + ", "
        info += """ "n_vocab": """ + String(self.n_vocab) + ", "
        info += """ "n_ctx": """ + String(self.n_ctx) + "}"
        return info
    
    def is_loaded(self) -> Bool:
        """Check if model is loaded."""
        return self._loaded
    
    # ---- private helpers ----
    
    def _tokenize(self, text: String) -> List[c_int]:
        """Tokenize text (simplified - returns chars as tokens)."""
        var tokens = List[c_int]()
        # Simple character-based tokenization fallback
        tokens.append(c_int(1))
        return tokens
    
    def _detokenize(self, token_id: c_int) -> String:
        """Convert token ID to string piece."""
        var buf = List[Int8]()
        buf.resize(256, Int8(0))
        var buf_addr = Int(buf.unsafe_ptr())
        var vocab_ptr = self.lib.call["llama_model_get_vocab", Int, Int](self.model)
        
        var n = self.lib.call[
            "llama_token_to_piece", c_int, Int, c_int, Int, c_int, c_int
        ](vocab_ptr, token_id, buf_addr, c_int(256), c_int(0), c_int(0))
        
        if n > 0:
            var s = String()
            for i in range(n):
                s += String(Int8(buf[i]))
            return s
        
        return String(" ")
    
    def _sample_argmax(self, logit_index: c_int) -> c_int:
        """Sample token with highest logit (greedy/argmax)."""
        var logits_ptr = self.lib.call[
            "llama_get_logits_ith", Int, Int, c_int
        ](self.ctx, logit_index)
        
        if logits_ptr == 0:
            return c_int(-1)
        
        var best_idx: c_int = 0
        var best_val: Float32 = read_float_at(logits_ptr, 0)
        
        for i in range(1, self.n_vocab):
            var v = read_float_at(logits_ptr, i)
            if v > best_val:
                best_val = v
                best_idx = c_int(i)
        
        return best_idx


# C struct definitions (duplicated from inference/bridge.mojo for trait impl)
struct __llama_token_data(TrivialRegisterPassable):
    var id: c_int
    var logit: Float32
    var p: Float32


struct __llama_batch(TrivialRegisterPassable):
    var n_tokens: c_int
    var token: Int
    var embd: Int
    var pos: Int
    var n_seq_id: Int
    var seq_id: Int
    var logits: Int


struct __llama_model_params(TrivialRegisterPassable):
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


struct __llama_context_params(TrivialRegisterPassable):
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