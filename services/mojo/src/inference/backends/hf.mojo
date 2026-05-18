"""
inference/backends/hf.mojo — HuggingFace model backend.
Implements ModelBackend trait using transformers library.
"""

from std.collections import List
from std.python import Python, PythonObject


struct HfBackend(ModelBackend):
    """HuggingFace model backend using Python interop.
    
    Loads models from HuggingFace Hub or local paths.
    Supports: sentence-transformers for embeddings, text-generation pipelines.
    """
    
    var _model: PythonObject
    var _tokenizer: PythonObject
    var _pipeline: PythonObject
    var n_embd: c_int
    var _loaded: Bool
    var _model_path: String
    var _model_type: String
    
    def __init__(out self):
        self._model = PythonObject()
        self._tokenizer = PythonObject()
        self._pipeline = PythonObject()
        self.n_embd = 0
        self._loaded = False
        self._model_path = ""
        self._model_type = "unknown"
    
    def load(mut self, path: String) raises:
        """Load HuggingFace model via Python interop.
        
        Args:
            path: Model path (hf:... or huggingface:... or local path)
            
        Raises:
            Error if model fails to load
        """
        # Import required Python modules
        try:
            var torch = Python.import_module("torch")
            var transformers = Python.import_module("transformers")
        except:
            raise Error("Failed to import torch or transformers. Install with: pip install torch transformers")
        
        # Parse path - strip hf: or huggingface: prefix
        var model_path = path
        if path.lower().startswith("hf:"):
            model_path = path[3:]
        elif path.lower().startswith("huggingface:"):
            model_path = path[12:]
        
        self._model_path = model_path.trim()
        
        try:
            # Try sentence-transformers first (for embeddings)
            var SentenceTransformer = Python.import_module("sentence_transformers").SentenceTransformer
            self._model = SentenceTransformer(model_path)
            
            # Get embedding dimension
            self.n_embd = c_int(self._model.get_sentence_embedding_dimension())
            self._model_type = "sentence-transformers"
            
        except:
            # Fallback to AutoModel/AutoTokenizer
            try:
                var AutoModel = transformers.AutoModel
                var AutoTokenizer = transformers.AutoTokenizer
                
                self._tokenizer = AutoTokenizer.from_pretrained(model_path)
                self._model = AutoModel.from_pretrained(model_path)
                
                # Get embedding dim from config
                var config = self._model.config
                self.n_embd = c_int(config.hidden_size)
                self._model_type = "auto-model"
                
            except:
                raise Error("Failed to load HuggingFace model from: " + model_path)
        
        self._loaded = True
    
    def unload(mut self):
        """Unload model and free Python references."""
        self._model = PythonObject()
        self._tokenizer = PythonObject()
        self._pipeline = PythonObject()
        self._loaded = False
    
    def embed(self, text: String) raises -> List[Float32]:
        """Generate embedding for text.
        
        Args:
            text: Input text
            
        Returns:
            List of Float32 embedding values
        """
        if not self._loaded:
            raise Error("Model not loaded")
        
        try:
            if self._model_type == "sentence-transformers":
                # Use sentence-transformers encode
                var embedding = self._model.encode(text)
                
                # Convert to List[Float32]
                var result = List[Float32]()
                for i in range(len(embedding)):
                    result.append(Float32(embedding[i]))
                return result
                
            elif self._model_type == "auto-model":
                # Manual embedding computation
                var inputs = self._tokenizer(text, return_tensors="pt")
                var outputs = self._model(**inputs)
                
                # Mean pooling over sequence
                var hidden = outputs.last_hidden_state
                var mask = inputs.attention_mask
                
                # Expand mask and apply
                var mask_expanded = mask.unsqueeze(-1).expand(hidden.size())
                var sum_embeddings = (hidden * mask_expanded).sum(1)
                var sum_mask = mask_expanded.sum(1)
                var mean_pooled = sum_embeddings / sum_mask
                
                # Convert to list
                var result = List[Float32]()
                var arr = mean_pooled[0].tolist()
                for i in range(len(arr)):
                    result.append(Float32(arr[i]))
                return result
            
            else:
                raise Error("Unknown model type: " + self._model_type)
                
        except:
            # Fallback: return zero embedding
            var zero_emb = List[Float32]()
            for i in range(self.n_embd):
                zero_emb.append(Float32(0.0))
            return zero_emb
    
    def generate(
        self,
        prompt: String,
        max_tokens: Int = 512,
        temperature: Float32 = 0.7,
        top_p: Float32 = 0.9
    ) raises -> String:
        """Generate text using HuggingFace pipeline.
        
        Args:
            prompt: Input prompt
            max_tokens: Max tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling
            
        Returns:
            Generated text
        """
        if not self._loaded:
            raise Error("Model not loaded")
        
        try:
            # Use pipeline if not already set up
            if self._pipeline == PythonObject():
                var pipeline_module = Python.import_module("transformers")
                self._pipeline = pipeline_module.pipeline(
                    "text-generation",
                    model=self._model,
                    tokenizer=self._tokenizer
                )
            
            # Generate
            var outputs = self._pipeline(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=PythonObject()
            )
            
            var generated_text = outputs[0]["generated_text"]
            var result = generated_text[len(prompt):].strip()
            return result
            
        except:
            return "[Generation not available for this model]"
    
    def model_info(self) -> String:
        """Return model info as JSON string."""
        if not self._loaded:
            return """{"loaded": false, "format": "hf", "error": "not loaded"}"""
        
        var info = String()
        info += """{"loaded": true, "format": "hf", "backend": "transformers", """
        info += """ "model_type": """ + "\"" + self._model_type + "\", "
        info += """ "model_path": """ + "\"" + self._model_path + "\", "
        info += """ "n_embd": """ + String(self.n_embd) + "}"
        return info
    
    def is_loaded(self) -> Bool:
        """Check if model is loaded."""
        return self._loaded