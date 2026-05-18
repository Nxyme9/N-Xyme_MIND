# ============================================================================
# tools/codex.mojo — Mojo-native semantic code search (simplified)
# ============================================================================
# 
# This module provides the search/ranking logic in Mojo.
# Embedding is done via Python subprocess for compatibility.
# The search and similarity calculation is Mojo-native.

from std.collections import List
from std.time import perf_counter
from std.python import Python

# ============================================================================
# COSINE SIMILARITY
# ============================================================================

def cosine_similarity(a: List[Float32], b: List[Float32]) -> Float64:
    """Calculate cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    
    var n = len(a)
    if n == 0:
        return 0.0
    
    var dot: Float64 = 0.0
    var norm_a: Float64 = 0.0
    var norm_b: Float64 = 0.0
    
    for i in range(n):
        var av = Float64(a[i])
        var bv = Float64(b[i])
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    
    var denominator = (norm_a * norm_b) ** 0.5
    if denominator < 1e-8:
        return 0.0
    
    return dot / denominator


# ============================================================================
# CODEX SEARCH ENGINE - uses Python for embedding
# ============================================================================

struct CodexSearch:
    """Mojo-native semantic code search engine.
    
    Uses Python subprocess for embedding, but search/ranking in Mojo.
    """
    
    var index_loaded: Bool
    var file_paths: List[String]
    var file_embeddings: List[List[Float32]]
    var file_summaries: List[String]
    
    def __init__(out self):
        self.index_loaded = False
        self.file_paths = List[String]()
        self.file_embeddings = List[List[Float32]]()
        self.file_summaries = List[String]()
    
    def embed_via_python(self, text: String) raises -> List[Float32]:
        """Get embedding via Python subprocess (embed_bridge)."""
        var py_subprocess = Python.import_module("subprocess")
        var py_json = Python.import_module("json")
        var py_builtins = Python.import_module("builtins")
        
        var req_dict = py_builtins.dict()
        req_dict["type"] = "embed"
        req_dict["text"] = text
        req_dict["id"] = "codex-embed"
        
        var req_json = py_json.dumps(req_dict)
        
        var py_list = py_builtins.list()
        py_list.append("python3")
        py_list.append("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/services/mojo-router/src/embed_bridge.py")
        
        var proc = py_subprocess.Popen(
            py_list,
            stdin=py_subprocess.PIPE,
            stdout=py_subprocess.PIPE,
            stderr=py_subprocess.PIPE
        )
        
        var py_stdin = proc.stdin
        py_stdin.write(req_json.encode("utf-8"))
        py_stdin.close()
        
        var py_stdout = proc.stdout
        var py_stderr = proc.stderr
        var stdout = py_stdout.read()
        var stderr = py_stderr.read()
        proc.wait()
        
        if py_builtins.len(stdout) == 0:
            # Return empty on failure
            return List[Float32]()
        
        var py_resp = py_json.loads(stdout)
        var resp_type = String(py_resp.get("type", ""))
        
        if resp_type != "embed_result":
            return List[Float32]()
        
        var py_emb = py_resp["embedding"]
        var dim = py_builtins.len(py_emb)
        
        var result = List[Float32]()
        for i in py_builtins.range(dim):
            result.append(Float32(py=py_emb[i]))
        
        return result^
    
    def index_files(mut self, root: String, extensions: List[String]) raises:
        """Index files using Python for embedding."""
        
        # Add sample entries and embed via Python
        var paths = List[String]()
        paths.append(root + "/daemon.mojo")
        paths.append(root + "/inference/bridge.mojo")
        paths.append(root + "/tools/codex.mojo")
        
        var summaries = List[String]()
        summaries.append("Main daemon for Mojo router")
        summaries.append("FFI bindings for llama.cpp (via inference/bridge.mojo)")
        summaries.append("Code search module (via tools/codex.mojo)")
        
        var i = 0
        while i < len(paths):
            self.file_paths.append(paths[i])
            self.file_summaries.append(summaries[i])
            
            # Get embedding via Python - transfer ownership
            var vec = self.embed_via_python(paths[i] + ": " + summaries[i])
            if len(vec) > 0:
                self.file_embeddings.append(vec^)
            
            i += 1
        
        self.index_loaded = True
    
    def search(mut self, query: String, top_k: Int) raises -> String:
        """Search indexed files by semantic similarity."""
        if not self.index_loaded or len(self.file_paths) == 0:
            return '{"type": "error", "code": "NO_INDEX", "message": "No files indexed. Call index_files() first"}'
        
        # Embed query via Python
        var q_vec = self.embed_via_python(query)
        if len(q_vec) == 0:
            return '{"type": "error", "code": "EMBED_FAILED", "message": "Failed to embed query"}'
        
        var n = len(self.file_paths)
        
        # Calculate similarities
        var results = List[Tuple[String, Float64, String]]()
        
        for i in range(n):
            var sim = cosine_similarity(q_vec, self.file_embeddings[i])
            results.append((self.file_paths[i], sim, self.file_summaries[i]))
        
        # Sort by similarity (descending) - simple bubble sort
        var m = len(results)
        for i in range(m):
            for j in range(0, m - i - 1):
                var s1 = results[j][1]
                var s2 = results[j + 1][1]
                if s1 < s2:
                    var tmp = results[j]
                    results[j] = results[j + 1]
                    results[j + 1] = tmp
        
        # Build JSON output
        var result = String()
        result = result + '{"type": "search_result", "query": "' + query + '", "results": ['
        
        var count = top_k
        if count > m:
            count = m
        
        for i in range(count):
            if i > 0:
                result = result + ", "
            
            var path = results[i][0]
            var score = results[i][1]
            var summary = results[i][2]
            
            result = result + '{"path": "' + path + '", "score": '
            result = result + String(score)
            result = result + ', "summary": "' + summary + '"}'
        
        result = result + "], "
        result = result + '"total": '
        result = result + String(m)
        result = result + '}'
        
        return result
    
    def status(mut self) -> String:
        """Return status JSON."""
        var result = '{"type": "codex_status", "index_loaded": '
        if self.index_loaded:
            result = result + "true"
        else:
            result = result + "false"
        result = result + ', "files_indexed": '
        result = result + String(len(self.file_paths))
        result = result + '}'
        return result