"""
inference/backend.mojo — ModelBackend trait interface.
Each backend (GGUF, HuggingFace, Native) implements this.
"""

from std.collections import List


trait ModelBackend:
    """Interface for all model backends.
    
    Implementations must provide:
    - load: Load model from path
    - unload: Free model resources
    - embed: Get embedding vector for text
    - generate: Generate text from prompt
    - model_info: Return model metadata
    - is_loaded: Check if model is loaded
    """
    
    def load(mut self, path: String) raises:
        """Load model from path."""
        ...
    
    def unload(mut self):
        """Unload model and free resources."""
        ...
    
    def embed(self, text: String) raises -> List[Float32]:
        """Generate embedding vector for input text.
        
        Returns list of Float32 values representing the text embedding.
        """
        ...
    
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
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling threshold
            
        Returns:
            Generated text string
        """
        ...
    
    def model_info(self) -> String:
        """Return model metadata as JSON string.
        
        Returns format info, dimensions, vocab size, etc.
        """
        ...
    
    def is_loaded(self) -> Bool:
        """Check if model is currently loaded."""
        ...