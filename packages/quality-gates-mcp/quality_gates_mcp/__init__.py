"""Quality Gates MCP Server - wraps 11 gate scripts as MCP tools."""

from mcp.server.fastmcp import FastMCP
import subprocess
import json
import os

mcp = FastMCP("quality-gates")

GATES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "bin",
    "quality-gates",
)

GATES = [
    ("run_typecheck", "Run TypeScript type check (gate-1)", "gate-1-typecheck.sh"),
    ("run_lint", "Run linting (gate-2)", "gate-2-lint.sh"),
    ("run_format", "Run formatting check (gate-3)", "gate-3-format.sh"),
    ("run_tests", "Run test suite (gate-4)", "gate-4-test.sh"),
    ("run_secrets_scan", "Scan for secrets (gate-5)", "gate-5-secrets.sh"),
    (
        "run_placeholder_check",
        "Check for placeholders (gate-6)",
        "gate-6-placeholders.sh",
    ),
    ("run_agent_call_check", "Validate agent calls (gate-7)", "gate-7-agent-calls.sh"),
    (
        "run_security_paths",
        "Check security-sensitive paths (gate-8)",
        "gate-8-security-paths.sh",
    ),
    ("run_deps_check", "Check dependencies (gate-9)", "gate-9-deps.sh"),
    ("run_sast", "Run SAST with bandit (gate-10)", "gate-10-sast.sh"),
    (
        "run_coverage_trend",
        "Check coverage trend (gate-11)",
        "gate-11-coverage-trend.sh",
    ),
    ("run_all_gates", "Run ALL quality gates", "gate-all.sh"),
]


def _run_gate(script_name: str) -> dict:
    """Run a gate script and return structured result."""
    script_path = os.path.join(GATES_DIR, script_name)
    if not os.path.isfile(script_path):
        return {
            "gate": script_name,
            "status": "error",
            "error": f"Script not found: {script_path}",
        }
    try:
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.dirname(GATES_DIR),
        )
        return {
            "gate": script_name,
            "status": "pass" if result.returncode == 0 else "fail",
            "exit_code": result.returncode,
            "stdout": result.stdout.strip()[-2000:],
            "stderr": result.stderr.strip()[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {
            "gate": script_name,
            "status": "timeout",
            "error": "Gate timed out after 120s",
        }
    except Exception as e:
        return {"gate": script_name, "status": "error", "error": str(e)}


for func_name, description, script in GATES:

    def make_handler(s):
        def handler() -> dict:
            return _run_gate(s)

        return handler

    fn = make_handler(script)
    fn.__name__ = func_name
    fn.__doc__ = description
    mcp.tool()(fn)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
