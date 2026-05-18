"""
Compiled Agent Binary Template for N-Xyme MIND.
Compile-time identity, MCP stdio protocol, memory-backed learning.

Usage:
  mojo build agents/templates/compiled-agent.mojo -o bins/hephaestus-agent
    -D AGENT_NAME="Hephaestus - Builder"
    -D AGENT_TOOLS="write,read,glob,search"
    -D AGENT_DESCRIPTION="Builds complex code with quality gates"
"""

from std.time import perf_counter
from std.python import Python

comptime AGENT_NAME: String = "Librarian - Research"
comptime AGENT_TOOLS_RAW: String = ""
comptime AGENT_DESCRIPTION: String = "Compiled N-Xyme agent"
comptime AGENT_MODEL: String = "opencode/deepseek-v4-flash-free"
comptime MEMORY_FILE: String = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/data/memory/compile-patterns.jsonl"

comptime AGENT_TOOLS_LIST = AGENT_TOOLS_RAW.split(",")


def main() raises:
    """
    MCP Protocol Server Loop.
    Reads JSON-RPC 2.0 from stdin, writes responses to stdout.
    """
    var py_json = Python.import_module("json")
    var py_sys = Python.import_module("sys")
    var py_b = Python.import_module("builtins")
    var py_os = Python.import_module("os")
    var py_time = Python.import_module("time")

    # ── Load compile patterns from memory ──────────────────────────────
    var patterns = py_b.list()
    if py_os.path.exists(MEMORY_FILE):
        var f = py_b.open(MEMORY_FILE, "r")
        for line in f:
            var trimmed = String(line).strip()
            if trimmed.byte_length() > 0:
                try:
                    var entry = py_json.loads(trimmed)
                    if String(entry.get("agent", "")) == AGENT_NAME:
                        patterns.append(entry)
                except:
                    pass
        f.close()

    var total_patterns = len(patterns)
    var successes = 0
    for i in range(total_patterns):
        if patterns[i].get("success") is not None and patterns[i].get("success") == True:
            successes += 1
    var rate = Float64(successes) / Float64(total_patterns) if total_patterns > 0 else 0.0

    # Log startup to stderr (use Python stderr.write, not Mojo print)
    py_sys.stderr.write("[startup] Agent: " + AGENT_NAME + "\n")
    py_sys.stderr.write("[startup] Tools: " + String(comptime(len(AGENT_TOOLS_LIST))) + "\n")
    py_sys.stderr.write("[startup] Patterns: " + String(total_patterns) + "\n")
    py_sys.stderr.write("[startup] Success rate: " + String(rate * 100.0) + "%\n")
    py_sys.stderr.flush()

    # ── Build tools list ──────────────────────────────────────────────
    var tools = py_b.list()
    tools.append(py_b.dict(
        name="get_context",
        description="Agent identity, patterns loaded, success rate",
        inputSchema=py_b.dict(type="object", properties=py_b.dict(), required=py_b.list())
    ))
    tools.append(py_b.dict(
        name="search_memory",
        description="Search compile patterns by substring",
        inputSchema=py_b.dict(
            type="object",
            properties=py_b.dict(
                query=py_b.dict(type="string", description="Search text"),
                k=py_b.dict(type="number", description="Max results")
            ),
            required=py_b.list()
        )
    ))
    tools.append(py_b.dict(
        name="get_patterns",
        description="Get formatted compile patterns",
        inputSchema=py_b.dict(type="object", properties=py_b.dict(), required=py_b.list())
    ))

    # ── MCP Loop ──────────────────────────────────────────────────────
    var running = True
    while running:
        try:
            var raw = py_sys.stdin.readline()
            var line = String(raw).strip()
            if not line:
                running = False
                break

            var msg = py_json.loads(line)
            var msg_id = msg.get("id", 0)
            var method = String(msg.get("method", ""))
            var params = msg.get("params", py_b.dict())

            if method == "initialize":
                var ident = py_b.dict(
                    protocolVersion="2025-06-18",
                    capabilities=py_b.dict(tools=py_b.dict()),
                    serverInfo=py_b.dict(
                        name="nx-" + AGENT_NAME.lower().replace(" ", "-"),
                        version="1.0.0b1"
                    )
                )
                var resp = py_json.dumps(py_b.dict(jsonrpc="2.0", id=msg_id, result=ident))
                py_sys.stdout.write(resp + "\n")
                py_sys.stdout.flush()

            elif method == "notifications/initialized":
                continue

            elif method == "tools/list":
                var resp = py_json.dumps(py_b.dict(jsonrpc="2.0", id=msg_id, result=py_b.dict(tools=tools)))
                py_sys.stdout.write(resp + "\n")
                py_sys.stdout.flush()

            elif method == "tools/call":
                var tool_name = String(params.get("name", ""))
                var args_obj = params.get("arguments", py_b.dict())

                if tool_name == "get_context":
                    var ctx = py_b.dict(
                        agent=AGENT_NAME,
                        desc=AGENT_DESCRIPTION,
                        model=AGENT_MODEL,
                        patterns_loaded=total_patterns,
                        success_rate=py_b.float(rate * 100.0)
                    )
                    # Build content array
                    var content_arr = py_b.list()
                    content_arr.append(py_b.dict(type="text", text=py_json.dumps(ctx)))
                    var result = py_b.dict(content=content_arr, isError=False)
                    var resp = py_json.dumps(py_b.dict(jsonrpc="2.0", id=msg_id, result=result))
                    py_sys.stdout.write(resp + "\n")
                    py_sys.stdout.flush()

                elif tool_name == "search_memory":
                    var query = String(args_obj.get("query", "")).lower()
                    var k = Int(py=py_b.int(args_obj.get("k", 5)))
                    var results = py_b.list()
                    for i in range(total_patterns):
                        var p = patterns[i]
                        var p_content = String(p.get("content", "")).lower()
                        var found = py_b.int(p_content.find(query)) >= 0
                        if found:
                            results.append(p)
                            if py_b.len(results) >= k:
                                break
                    # Build response
                    var sresult = py_b.dict(results=results, count=py_b.len(results))
                    var content_arr = py_b.list()
                    content_arr.append(py_b.dict(type="text", text=py_json.dumps(sresult)))
                    var resp = py_json.dumps(py_b.dict(
                        jsonrpc="2.0", id=msg_id,
                        result=py_b.dict(content=content_arr, isError=False)
                    ))
                    py_sys.stdout.write(resp + "\n")
                    py_sys.stdout.flush()

                elif tool_name == "get_patterns":
                    var text = String()
                    if total_patterns > 0:
                        text += "## Compilation patterns from memory:\n"
                        for i in range(min(5, total_patterns)):
                            var p = patterns[i]
                            var p_success = p.get("success")
                            var status = "OK" if (p_success is not None and p_success == True) else "FAIL"
                            var src = String(p.get("source", "?"))
                            text += "  [" + status + "] " + src + "\n"
                    var content_arr = py_b.list()
                    content_arr.append(py_b.dict(type="text", text=text))
                    var resp = py_json.dumps(py_b.dict(
                        jsonrpc="2.0", id=msg_id,
                        result=py_b.dict(content=content_arr, isError=False)
                    ))
                    py_sys.stdout.write(resp + "\n")
                    py_sys.stdout.flush()

                else:
                    var content_arr = py_b.list()
                    content_arr.append(py_b.dict(type="text", text="Unknown tool: " + tool_name))
                    var err = py_b.dict(content=content_arr, isError=True)
                    var resp = py_json.dumps(py_b.dict(jsonrpc="2.0", id=msg_id, result=err))
                    py_sys.stdout.write(resp + "\n")
                    py_sys.stdout.flush()

            else:
                var err_resp = py_json.dumps(py_b.dict(
                    jsonrpc="2.0", id=msg_id,
                    error=py_b.dict(code=-32601, message="Method not found: " + method)
                ))
                py_sys.stdout.write(err_resp + "\n")
                py_sys.stdout.flush()

        except:
            py_sys.stderr.write("[error] exception in MCP loop\n")
            py_sys.stderr.flush()
            running = False
