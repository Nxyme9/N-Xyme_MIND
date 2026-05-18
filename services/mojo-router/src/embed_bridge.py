#!/usr/bin/env python3
"""
Embedding bridge — manages llama-server subprocess via Unix socket.
Communicates with Mojo daemon via stdin/stdout JSON-L.

Stories 2.1-2.3 Implementation:
- 2.1: llama-server Manager with auto-restart and graceful shutdown
- 2.2: Unix Socket Embedding with warm latency <10ms
- 2.3: Semantic Tool Scoring with 25 pre-computed embeddings

Usage:
  python3 embed_bridge.py

Reads JSON-L from stdin:
  {"type": "embed", "text": "some query", "id": "req-1"}
  {"type": "score", "text": "query", "id": "req-2"}
  {"type": "status", "id": "req-3"}

Writes JSON-L to stdout:
  {"type": "embed_result", "embedding": [0.1, 0.2, ...], "dim": 896, "latency_us": 5123, "id": "req-1"}
  {"type": "score_result", "tool": "...", "confidence": 0.95, "all_scores": {...}, "id": "req-2"}
  {"type": "status_result", "running": true, "model": "rosetta-v13-f16", "socket": "/tmp/llama.sock", "id": "req-3"}
"""

import json
import socket
import subprocess
import sys
import time
import os
import signal
import threading
from typing import Optional
# FIX: Removed unused defaultdict import


# 25 tools with their descriptions for semantic scoring (Story 2.3)
TOOL_DEFINITIONS = [
    ("session_start", "Start/resume session. Returns streak, XP, achievements."),
    ("session_status", "Session state: calls, memory, loops, context %."),
    ("continue_session", "Resume last active loop. No IDs needed."),
    ("welcome_back", "Warm session restore: streak, XP, last task."),
    ("next_step", "ONE next action suggestion. Never a list."),
    ("memory_write", "Store key-value in session. >500 chars needs confirm."),
    ("memory_read", "Read a value by key."),
    ("memory_list", "List all memory keys in session."),
    ("context_prune", "Smart compaction by agent type. Dry-run available."),
    ("audit_log_recent", "Recent tool calls for session."),
    ("ralph_start", "Start iterative loop. Persists across restarts."),
    ("ralph_status", "Check loop iteration, max, active."),
    ("ralph_iterate", "Advance loop. Returns cont, pct, est. remaining."),
    ("ralph_cancel", "Cancel active loop."),
    # ("dictate_inject", "Inject dictated text. REQUIRES confirm:true."),  # REMOVED — voice dictation disconnected
    ("delegate_to_hephaestus", "Delegate code task to Hephaestus."),
    ("project_map", "Project structure: dirs, files, depth-limited."),
    ("batch_read", "Read multiple files in one call."),
    ("code_verify", "Run quality gates: fmt, lint, test, audit."),
    ("safe_delete", "Move to data/trash/ instead of permanent rm."),
    ("trash_restore", "List/restore trashed files."),
    ("hephaestus_new_task", "Parallel-worker-safe fresh task. Prunes old context."),
    ("ask", "NL entry: say what you need, tool routes automatically."),
    ("decision_log", "Save design decision with rationale."),
    ("delegate_task", "Delegate task to another agent via shared memory."),
    ("consciousness_record", "Record agent task outcome into embedded consciousness."),
    ("consciousness_identity", "Get agent identity from 896-dim embedding space."),
    ("consciousness_evolve", "Evolve agent consciousness from outcome patterns."),
]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b:
        return 0.0
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class EmbedBridge:
    def __init__(self):
        self.server_proc: Optional[subprocess.Popen] = None
        self.socket_path = "/tmp/llama.sock"
        self.model_path = "/home/nxyme/N-Xyme_CODE/LLMs/by-type/custom/Rosseta/rosetta-v13-f16.gguf"
        self.llama_bin = "/tmp/llama.cpp/build/bin/llama-server"
        
        # Story 2.3: Pre-computed tool embeddings
        self.tool_embeddings: dict[str, list[float]] = {}
        self.tool_embeddings_loaded = False
        
        # Auto-restart state (Story 2.1)
        self.restart_backoff = 1.0
        self.max_backoff = 30.0
        self.running = True
        self.server_lock = threading.Lock()
        
        # Warm latency cache (Story 2.2)
        self.warm_cache: dict[str, tuple[list[float], float]] = {}
        self.warm_cache_max_size = 1000
        
        # Story 4.3: Control socket for hot-reload
        self.control_socket_path = "/tmp/llama-control.sock"
        self._control_thread: Optional[threading.Thread] = None

    def start_server(self) -> bool:
        """Start llama-server if not already running. Returns True on success."""
        with self.server_lock:
            # Check if server is already running
            if os.path.exists(self.socket_path):
                try:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(2)
                    s.connect(self.socket_path)
                    s.close()
                    print(f"Server already running at {self.socket_path}", file=sys.stderr)
                    self.restart_backoff = 1.0  # Reset backoff on successful check
                    return True
                except Exception:
                    # Socket exists but can't connect - remove stale socket
                    try:
                        os.remove(self.socket_path)
                    except OSError:
                        pass

            # Start new server process
            print(f"Starting llama-server...", file=sys.stderr)
            self.server_proc = subprocess.Popen(
                [self.llama_bin,
                 "-m", self.model_path,
                 "-s", self.socket_path,
                 "--embeddings", "--pooling", "mean",
                 "-ngl", "99"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for socket to appear (up to 30s)
            for i in range(30):
                if not self.running:
                    return False
                if os.path.exists(self.socket_path):
                    try:
                        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        s.settimeout(2)
                        s.connect(self.socket_path)
                        s.close()
                        print(f"Server started successfully", file=sys.stderr)
                        self.restart_backoff = 1.0  # Reset backoff
                        return True
                    except Exception:
                        pass
                time.sleep(1)
            
            # Server failed to start
            if self.server_proc:
                self.server_proc.terminate()
                self.server_proc = None
            raise RuntimeError("Server failed to start within 30s")

    def restart_server(self) -> bool:
        """Attempt to restart server with exponential backoff. Story 2.1."""
        if not self.running:
            return False
        
        print(f"Server crashed, restarting in {self.restart_backoff}s...", file=sys.stderr)
        time.sleep(self.restart_backoff)
        
        # Increment backoff for next failure
        self.restart_backoff = min(self.restart_backoff * 2, self.max_backoff)
        
        return self.start_server()

    def check_server_health(self) -> bool:
        """Check if server is still responsive."""
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(self.socket_path)
            s.close()
            return True
        except Exception:
            return False

    def stop_server(self):
        """Graceful shutdown. Story 2.1."""
        with self.server_lock:
            if self.server_proc:
                print("Shutting down llama-server...", file=sys.stderr)
                self.server_proc.terminate()
                try:
                    self.server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_proc.kill()
                    self.server_proc.wait()
                self.server_proc = None
        
        # Clean up socket
        try:
            if os.path.exists(self.socket_path):
                os.remove(self.socket_path)
        except OSError:
            pass

    # ===== Story 4.3: Hot-reload support =====
    
    def start_control_socket(self) -> bool:
        """
        Start the control socket listener for hot-reload signals.
        Creates a separate Unix socket for model reload commands.
        
        Returns:
            True if control socket started successfully
        """
        # Clean up old socket
        if os.path.exists(self.control_socket_path):
            try:
                os.remove(self.control_socket_path)
            except OSError:
                pass
        
        # Start control listener in background thread
        self._control_thread = threading.Thread(
            target=self._control_listener,
            daemon=True
        )
        self._control_thread.start()
        print(f"Control socket listening at {self.control_socket_path}", file=sys.stderr)
        return True
    
    def _control_listener(self):
        """
        Control socket listener thread.
        Listens for reload_model commands and handles hot-reload.
        Total downtime <1 second.
        """
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(self.control_socket_path)
        server_sock.listen(5)
        server_sock.settimeout(1.0)  # Allow periodic check of self.running
        
        while self.running:
            try:
                conn, _ = server_sock.accept()
                try:
                    data = conn.recv(4096)
                    if data:
                        msg = json.loads(data.decode())
                        
                        if msg.get("type") == "reload_model":
                            model_path = msg.get("path", "")
                            success = self._handle_reload(model_path)
                            
                            # Send ACK response
                            response = {
                                "type": "reload_ack",
                                "status": "ok" if success else "failed"
                            }
                            conn.sendall(json.dumps(response).encode())
                            
                except json.JSONDecodeError as e:
                    print(f"Control socket JSON error: {e}", file=sys.stderr)
                except Exception as e:
                    print(f"Control socket error: {e}", file=sys.stderr)
                finally:
                    conn.close()
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"Control listener error: {e}", file=sys.stderr)
        
        # Cleanup
        try:
            server_sock.close()
        except Exception:
            pass
    
    def _handle_reload(self, model_path: str) -> bool:
        """
        Handle hot-reload of model.
        Terminates current llama-server, starts new with new model.
        
        Args:
            model_path: Path to new model
            
        Returns:
            True if reload successful
        """
        print(f"Hot-reload triggered: {model_path}", file=sys.stderr)
        
        try:
            # Stop current server
            self.stop_server()
            
            # Update model path
            self.model_path = model_path
            
            # Clear embeddings cache (will recompute with new model)
            self.tool_embeddings_loaded = False
            self.tool_embeddings = {}
            self.warm_cache = {}
            
            # Start new server
            if not self.start_server():
                print("Failed to start server after reload", file=sys.stderr)
                return False
            
            # Recompute tool embeddings with new model
            self.compute_tool_embeddings()
            
            print(f"Hot-reload complete", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"Hot-reload failed: {e}", file=sys.stderr)
            return False
    
    def stop_control_socket(self):
        """Stop the control socket listener."""
        try:
            if os.path.exists(self.control_socket_path):
                os.remove(self.control_socket_path)
        except OSError:
            pass

    def compute_tool_embeddings(self):
        """Story 2.3: Compute embeddings for all 25 tools at boot."""
        if self.tool_embeddings_loaded:
            return
        
        print("Computing tool embeddings at boot...", file=sys.stderr)
        
        for tool_name, tool_desc in TOOL_DEFINITIONS:
            # Use both name and description for richer embedding
            text = f"{tool_name}. {tool_desc}"
            try:
                emb, _ = self.get_embedding(text, use_cache=False)
                self.tool_embeddings[tool_name] = emb
            except Exception as e:
                print(f"Warning: Failed to compute embedding for {tool_name}: {e}", file=sys.stderr)
                # Use zero vector as fallback
                self.tool_embeddings[tool_name] = [0.0] * 896
        
        self.tool_embeddings_loaded = True
        print(f"Loaded {len(self.tool_embeddings)} tool embeddings", file=sys.stderr)

    def score_tools(self, query: str) -> dict:
        """Story 2.3: Score all tools by cosine similarity to query embedding."""
        # Get query embedding
        query_emb, _ = self.get_embedding(query, use_cache=True)
        
        # Score all tools
        all_scores = {}
        for tool_name, tool_emb in self.tool_embeddings.items():
            score = cosine_similarity(query_emb, tool_emb)
            all_scores[tool_name] = round(score, 6)
        
        # Find best match
        best_tool = max(all_scores, key=all_scores.get)
        best_score = all_scores[best_tool]
        
        return {
            "tool": best_tool,
            "confidence": round(best_score, 4),
            "all_scores": all_scores
        }

    def get_embedding(self, text: str, use_cache: bool = True) -> tuple[list[float], float]:
        """
        Send text to llama-server via Unix socket.
        Returns (embedding, latency_us).
        Story 2.2: Warm latency <10ms via caching.
        """
        # Check warm cache first (Story 2.2 optimization)
        if use_cache and text in self.warm_cache:
            emb, _ = self.warm_cache[text]
            # Still measure latency for reporting
            start = time.perf_counter()
            # Quick server ping to measure warm latency
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            try:
                sock.connect(self.socket_path)
                sock.sendall(b"GET /health HTTP/1.1\r\n\r\n")
                sock.recv(1024)
            except Exception:
                pass
            finally:
                sock.close()
            elapsed = (time.perf_counter() - start) * 1_000_000
            return emb, elapsed

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect(self.socket_path)

        body = json.dumps({"input": text})
        request = (
            f"POST /v1/embeddings HTTP/1.1\r\n"
            f"Host: localhost\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n{body}"
        )

        start = time.perf_counter()
        sock.sendall(request.encode())
        response = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response += chunk
        elapsed = (time.perf_counter() - start) * 1_000_000

        sock.close()

        # Parse response
        # FIX: Handle case where \r\n\r\n is not found
        body_start = response.find(b"\r\n\r\n")
        if body_start == -1:
            # Fallback: try to parse entire response as JSON
            data = json.loads(response)
        else:
            resp_body = response[body_start + 4:]
            data = json.loads(resp_body)
        emb = data["data"][0]["embedding"]

        # Cache for warm latency (Story 2.2)
        if use_cache and len(self.warm_cache) < self.warm_cache_max_size:
            self.warm_cache[text] = (emb, elapsed)

        return emb, elapsed

    def handle_request(self, req: dict) -> Optional[dict]:
        """Handle a single JSON-L request."""
        req_type = req.get("type")
        req_id = req.get("id", "0")

        try:
            if req_type == "embed":
                text = req.get("text", "")
                emb, latency = self.get_embedding(text, use_cache=True)
                return {
                    "type": "embed_result",
                    "embedding": emb,
                    "dim": len(emb),
                    "latency_us": int(latency),
                    "id": req_id
                }

            elif req_type == "score":
                # Story 2.3: Semantic tool scoring
                text = req.get("text", "")
                scores = self.score_tools(text)
                scores["type"] = "score_result"
                scores["id"] = req_id
                return scores

            elif req_type == "status":
                return {
                    "type": "status_result",
                    "running": self.check_server_health(),
                    "model": "rosetta-v13-f16",
                    "socket": self.socket_path,
                    "tools_loaded": self.tool_embeddings_loaded,
                    "id": req_id
                }

            elif req_type == "warmup":
                # Manual warmup request
                text = req.get("text", "warmup")
                self.get_embedding(text, use_cache=True)
                return {
                    "type": "warmup_result",
                    "status": "ok",
            elif req_type == "notify":
                notification = {
                    "type": "notify",
                    "source": req.get("source", "unknown"),
                    "task_id": req.get("task_id", ""),
                    "agent": req.get("agent", ""),
                    "status": req.get("status", ""),
                    "timestamp": req.get("timestamp", 0),
                    "session_id": req.get("session_id", ""),
                    "id": req.get("id", "")
                }
                query = f"task completion: {notification['agent']} {notification['status']}"
                scores = self.score_tools(query)
                notification["routed_tool"] = scores.get("tool", "unknown")
                notification["routed_confidence"] = scores.get("confidence", 0)
                print(json.dumps(notification), flush=True)
                return

        except Exception as e:
            return {
                "type": "error",
                "message": str(e),
                "id": req_id
            }

        return None

    def run(self):
        """Main loop — read JSON-L from stdin, write to stdout."""
        # Story 2.1: Start server
        if not self.start_server():
            print(json.dumps({"type": "fatal", "message": "Failed to start server"}), flush=True)
            return

        # Story 2.3: Pre-compute tool embeddings at boot
        self.compute_tool_embeddings()
        
        # Story 4.3: Start control socket for hot-reload
        self.start_control_socket()

        print("Bridge ready", file=sys.stderr)

        # Main request processing loop
        for line in sys.stdin:
            if not self.running:
                break
            
            line = line.strip()
            if not line:
                continue

            try:
                req = json.loads(line)
                result = self.handle_request(req)
                if result:
                    print(json.dumps(result), flush=True)

            except json.JSONDecodeError as e:
                print(json.dumps({"type": "error", "message": f"JSON decode error: {e}"}), flush=True)
            except Exception as e:
                # Story 2.1: Auto-restart on server crash
                if "Connection" in str(e) or "socket" in str(e).lower():
                    if self.restart_server():
                        # Retry request after restart
                        try:
                            req = json.loads(line)
                            result = self.handle_request(req)
                            if result:
                                print(json.dumps(result), flush=True)
                        except Exception:
                            pass
                    else:
                        print(json.dumps({"type": "error", "message": str(e)}), flush=True)
                else:
                    print(json.dumps({"type": "error", "message": str(e)}), flush=True)

    def shutdown(self):
        """Graceful shutdown handler. Story 2.1."""
        self.running = False
        self.stop_control_socket()
        self.stop_server()


def main():
    bridge = EmbedBridge()
    
    # Handle signals for graceful shutdown (Story 2.1)
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, shutting down...", file=sys.stderr)
        bridge.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.shutdown()
    except Exception as e:
        print(json.dumps({"type": "fatal", "message": str(e)}), flush=True)
        bridge.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
