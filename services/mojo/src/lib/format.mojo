"""
Format auto-detection for model files.
Detects: GGUF, ONNX, HuggingFace, or native Mojo SIMD.
"""



def detect_format(path: String) -> String:
    """Detect model format from path string.
    
    Returns: "gguf", "onnx", "hf", "mojo", or "unknown"
    """
    var lower = path.lower()
    
    # GGUF detection - most common for local models
    if lower.endswith(".gguf"):
        return "gguf"
    
    # ONNX detection
    if lower.endswith(".onnx"):
        return "onnx"
    
    # HuggingFace detection - explicit prefixes
    if lower.startswith("hf:") or lower.startswith("huggingface:"):
        return "hf"
    
    # Native Mojo detection
    if lower.endswith(".mojo") or path == "__native__":
        return "mojo"
    
    # Implicit HuggingFace - path contains "/" but not other extensions
    if lower.find("/") >= 0 and not lower.endswith(".gguf") and not lower.endswith(".onnx"):
        return "hf"
    
    return "unknown"


def format_is_valid(kind: String) -> Bool:
    """Check if format kind is supported."""
    return kind == "gguf" or kind == "onnx" or kind == "hf" or kind == "mojo"


def format_to_backend_name(kind: String) -> String:
    """Map format to backend name for error messages."""
    if kind == "gguf":
        return "LlamaBackend"
    elif kind == "onnx":
        return "OnnxBackend"
    elif kind == "hf":
        return "HfBackend"
    elif kind == "mojo":
        return "NativeBackend"
    else:
        return "Unknown"