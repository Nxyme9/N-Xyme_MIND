# MCP Core — Hot-Swappable Infrastructure

**Goal:** Industry-standard MCP server architecture with hot-swappable tools, self-healing, and structured debugging.

**Key Principles:**
1. **No server restarts** — Tools reload automatically when files change
2. **Never crash** — Graceful degradation with fallback to previous version
3. **Self-healing** — Detect failures and recover automatically
4. **Debuggable** — Structured logging, health endpoints, error tracing
5. **Modular** — Each tool is independent, testable in isolation

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP SERVER                               │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ TOOL REGISTRY│  │ FILE WATCHER │  │ HEALTH MONITOR        │  │
│  │             │  │              │  │                       │  │
│  │ - register()│  │ - watch()    │  │ - status()            │  │
│  │ - unregister│  │ - detect()   │  │ - metrics()           │  │
│  │ - hot_swap()│  │ - reload()   │  │ - recover()           │  │
│  │ - fallback()│  │ - debounce() │  │ - alert()             │  │
│  └─────────────┘  └──────────────┘  └───────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ JSON-RPC HANDLER                                          │  │
│  │ - initialize() → returns server info + capabilities       │  │
│  │ - tools/list() → returns registered tools                 │  │
│  │ - tools/call() → routes to tool, logs, handles errors     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ STRUCTURED LOGGER                                         │  │
│  │ - Level: DEBUG/INFO/WARN/ERROR                            │  │
│  │ - Format: JSON (machine-readable)                         │  │
│  │ - Output: stderr (doesn't interfere with JSON-RPC stdout) │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## TOOL REGISTRY PATTERN

```python
class ToolRegistry:
    """Hot-swappable tool registry with fallback support."""
    
    def __init__(self):
        self.tools: Dict[str, ToolEntry] = {}
        self.history: Dict[str, List[ToolEntry]] = {}  # Version history for rollback
    
    def register(self, name: str, handler: Callable, schema: dict):
        """Register a tool. If it exists, save old version as fallback."""
        if name in self.tools:
            # Save current version as fallback
            if name not in self.history:
                self.history[name] = []
            self.history[name].append(self.tools[name])
            # Keep only last 3 versions
            if len(self.history[name]) > 3:
                self.history[name] = self.history[name][-3:]
        
        self.tools[name] = ToolEntry(
            name=name,
            handler=handler,
            schema=schema,
            registered_at=time.time(),
            status="active"
        )
        logger.info(f"Tool registered: {name}")
    
    def hot_swap(self, name: str, new_handler: Callable, new_schema: dict):
        """Hot-swap a tool without restarting the server."""
        if name not in self.tools:
            return {"error": f"Tool {name} not found"}
        
        try:
            # Test new handler before swapping
            test_result = self._test_handler(new_handler)
            if not test_result:
                return {"error": f"New handler for {name} failed validation"}
            
            # Perform swap
            self.register(name, new_handler, new_schema)
            logger.info(f"Tool hot-swapped: {name}")
            return {"success": True, "tool": name}
        except Exception as e:
            # Rollback to previous version
            self._rollback(name)
            return {"error": f"Hot-swap failed, rolled back: {str(e)}"}
    
    def _rollback(self, name: str):
        """Rollback to previous version of a tool."""
        if name in self.history and self.history[name]:
            old_entry = self.history[name].pop()
            self.tools[name] = old_entry
            logger.warn(f"Tool rolled back: {name}")
    
    def call(self, name: str, args: dict) -> dict:
        """Call a tool with error handling and metrics."""
        if name not in self.tools:
            return {"error": f"Unknown tool: {name}"}
        
        entry = self.tools[name]
        start_time = time.time()
        
        try:
            result = entry.handler(args)
            duration = time.time() - start_time
            
            # Log success
            logger.info(f"Tool called: {name} ({duration:.3f}s)")
            
            # Track metrics
            entry.call_count += 1
            entry.total_time += duration
            entry.last_call = time.time()
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Tool failed: {name} ({duration:.3f}s): {str(e)}")
            
            # Track error
            entry.error_count += 1
            
            # Auto-recover: if tool fails 3 times in a row, rollback
            if entry.error_count >= 3:
                self._rollback(name)
                logger.warn(f"Tool {name} auto-recovered via rollback")
            
            return {"error": f"Tool {name} failed: {str(e)}"}
```

---

## FILE WATCHER (Auto-Reload)

```python
class FileWatcher:
    """Watches tool files for changes and triggers hot-swap."""
    
    def __init__(self, registry: ToolRegistry, watch_dirs: List[str]):
        self.registry = registry
        self.watch_dirs = watch_dirs
        self.file_hashes: Dict[str, str] = {}
        self.debounce_timers: Dict[str, threading.Timer] = {}
        self._running = False
    
    def start(self):
        """Start watching files in background thread."""
        self._running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        logger.info(f"File watcher started for: {self.watch_dirs}")
    
    def stop(self):
        """Stop watching files."""
        self._running = False
        for timer in self.debounce_timers.values():
            timer.cancel()
    
    def _watch_loop(self):
        """Main watch loop — check files every 2 seconds."""
        while self._running:
            for watch_dir in self.watch_dirs:
                if not os.path.exists(watch_dir):
                    continue
                
                for root, dirs, files in os.walk(watch_dir):
                    for file in files:
                        if file.endswith('.py') and not file.startswith('_'):
                            file_path = os.path.join(root, file)
                            self._check_file(file_path)
            
            time.sleep(2)  # Check every 2 seconds
    
    def _check_file(self, file_path: str):
        """Check if file has changed."""
        try:
            current_hash = self._file_hash(file_path)
            if file_path not in self.file_hashes:
                self.file_hashes[file_path] = current_hash
                return
            
            if current_hash != self.file_hashes[file_path]:
                # File changed — debounce reload
                if file_path in self.debounce_timers:
                    self.debounce_timers[file_path].cancel()
                
                timer = threading.Timer(1.0, self._reload_file, args=[file_path])
                self.debounce_timers[file_path] = timer
                timer.start()
        except Exception as e:
            logger.error(f"File watcher error: {file_path}: {str(e)}")
    
    def _reload_file(self, file_path: str):
        """Reload a changed file."""
        try:
            # Import the module fresh
            module_name = file_path.replace('/', '.').replace('.py', '')
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find tool definitions in module
            if hasattr(module, 'TOOL_DEFS'):
                for tool_def in module.TOOL_DEFS:
                    self.registry.hot_swap(
                        tool_def['name'],
                        module.__dict__[tool_def['handler']],
                        tool_def['schema']
                    )
            
            self.file_hashes[file_path] = self._file_hash(file_path)
            logger.info(f"File reloaded: {file_path}")
        except Exception as e:
            logger.error(f"File reload failed: {file_path}: {str(e)}")
    
    def _file_hash(self, file_path: str) -> str:
        """Compute hash of file contents."""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
```

---

## HEALTH MONITOR

```python
class HealthMonitor:
    """Monitors MCP server health and triggers recovery."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.start_time = time.time()
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
    
    def get_status(self) -> dict:
        """Return current health status."""
        uptime = time.time() - self.start_time
        
        tool_stats = {}
        for name, entry in self.registry.tools.items():
            tool_stats[name] = {
                "status": entry.status,
                "call_count": entry.call_count,
                "error_count": entry.error_count,
                "avg_time": entry.total_time / max(entry.call_count, 1),
                "last_call": entry.last_call
            }
        
        return {
            "status": "healthy" if self.consecutive_errors == 0 else "degraded",
            "uptime_seconds": uptime,
            "consecutive_errors": self.consecutive_errors,
            "tools": tool_stats,
            "memory_mb": self._get_memory_usage()
        }
    
    def record_error(self):
        """Record an error for health tracking."""
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.max_consecutive_errors:
            logger.critical(f"Server degraded: {self.consecutive_errors} consecutive errors")
            self._trigger_recovery()
    
    def record_success(self):
        """Record a success for health tracking."""
        self.consecutive_errors = 0
    
    def _trigger_recovery(self):
        """Trigger self-healing recovery."""
        logger.warn("Triggering self-healing recovery...")
        
        # Rollback all tools with errors
        for name, entry in self.registry.tools.items():
            if entry.error_count > 0:
                self.registry._rollback(name)
        
        # Reset error counter
        self.consecutive_errors = 0
        logger.info("Self-healing recovery complete")
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        except:
            return 0.0
```

---

## STRUCTURED LOGGER

```python
class StructuredLogger:
    """JSON logger that outputs to stderr (doesn't interfere with MCP stdout)."""
    
    def __init__(self, level: str = "INFO"):
        self.level = getattr(logging, level.upper(), logging.INFO)
        self.logger = logging.getLogger("mcp")
        self.logger.setLevel(self.level)
        
        # Handler outputs to stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            json.dumps({
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s",
                "message": "%(message)s",
                "module": "%(module)s",
                "function": "%(funcName)s"
            })
        ))
        self.logger.addHandler(handler)
    
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra=kwargs)
    
    def warn(self, msg: str, **kwargs):
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, **kwargs):
        self.logger.error(msg, extra=kwargs)
    
    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, extra=kwargs)
```

---

## USAGE EXAMPLE

```python
# In megatool-mcp/server.py (or any MCP server):

from mcp_core import ToolRegistry, FileWatcher, HealthMonitor, StructuredLogger

# Initialize core components
logger = StructuredLogger(level="INFO")
registry = ToolRegistry()
health = HealthMonitor(registry)
watcher = FileWatcher(registry, watch_dirs=["tools/"])

# Register tools
registry.register("read_tool", handle_read, READ_SCHEMA)
registry.register("write_tool", handle_write, WRITE_SCHEMA)
registry.register("agent_edit", handle_agent_edit, AGENT_EDIT_SCHEMA)

# Start file watcher (auto-reload on changes)
watcher.start()

# In JSON-RPC handler:
def handle_tool_call(name, args):
    result = registry.call(name, args)
    if "error" in result:
        health.record_error()
    else:
        health.record_success()
    return result

# Health endpoint (can be called via MCP tool)
registry.register("health_check", lambda _: health.get_status(), HEALTH_SCHEMA)
```

---

## BENEFITS

| Feature | Before | After |
|---------|--------|-------|
| Tool changes | Restart server (5-10s downtime) | Hot-swap (0 downtime) |
| Error recovery | Manual restart | Auto-rollback after 3 failures |
| Debugging | Print statements to stdout | Structured JSON logs to stderr |
| Health monitoring | None | Real-time status + metrics |
| File changes | Manual reload | Auto-detect + reload (2s debounce) |
| Version history | None | Last 3 versions per tool |

---

## IMPLEMENTATION PLAN

1. Create `services/mcp-core/` directory with:
   - `__init__.py` — Exports core classes
   - `registry.py` — ToolRegistry with hot-swap
   - `watcher.py` — FileWatcher with auto-reload
   - `health.py` — HealthMonitor with self-healing
   - `logger.py` — StructuredLogger

2. Refactor all 4 MCP servers to use mcp-core:
   - bash-mcp/server.py
   - megatool-mcp/server.py
   - bmad-mcp/src/server.py
   - nx_agents (Rust — separate implementation)

3. Add health_check tool to all servers

4. Test hot-swap by modifying a tool file and verifying auto-reload
