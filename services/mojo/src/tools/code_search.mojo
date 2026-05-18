// CODEX — Semantic code search megatool
// Query → ONNX 384-dim embed → cosine sim → ranked files
// Usage: python3 tools/code_search.py "find routing logic"
// Output: {"type": "search_result", "results": [{"path": "...", "score": 0.92}, ...], "id": "1"}

from std.time import perf_counter
