"""MCP client layer — connects to MCP servers, injects _agent."""
import json, os, subprocess, time

ROOT = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"

MCP_DEFS = {
    "bash":    {"cmd": ["python3", f"{ROOT}/services/bash-mcp/server.py"]},
    "megatools": {"cmd": ["python3", f"{ROOT}/services/megatool-mcp/server.py"]},
    "bmad":    {"cmd": ["python3", f"{ROOT}/services/bmad-mcp/src/server.py"]},
    "nx":      {"cmd": [f"{ROOT}/bins/nx_agents"]},
}

class MCPClient:
    def __init__(self):
        self.servers = {}
    
    def start(self, name):
        if name in self.servers and self.servers[name].poll() is None:
            return True
        if name not in MCP_DEFS:
            return False
        try:
            p = subprocess.Popen(
                MCP_DEFS[name]["cmd"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, cwd=ROOT
            )
            p.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize"}\n')
            p.stdin.flush()
            p.stdout.readline()
            self.servers[name] = p
            return True
        except:
            return False
    
    def call(self, name, method, params=None, timeout=30):
        if name not in self.servers or self.servers[name].poll() is not None:
            if not self.start(name):
                return {"error": f"Cannot start MCP server: {name}"}
        
        req = json.dumps({"jsonrpc":"2.0","id":2,"method":method,"params":params or {}})
        try:
            self.servers[name].stdin.write(req + "\n")
            self.servers[name].stdin.flush()
            self.servers[name].stdout.readline  # ensure pipe is ready
            return json.loads(self.servers[name].stdout.readline()).get("result", {})
        except Exception as e:
            return {"error": str(e)}
    
    def tool(self, server, tool_name, args, agent):
        args = args or {}
        args["_agent"] = agent
        return self.call(server, "tools/call", {"name": tool_name, "arguments": args})

    def tools_list(self, server):
        r = self.call(server, "tools/list")
        return [t["name"] for t in r.get("tools", [])]
    
    def stop_all(self):
        for name, p in self.servers.items():
            if p and p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=3)
                except:
                    p.kill()
