#!/usr/bin/env python3
"""
N-Xyme_MIND Setup Wizard
First-run configuration and environment verification.
Run with: uv run python3 scripts/setup-wizard.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_success(text: str) -> None:
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str) -> None:
    print(f"  {text}")


def run_command(cmd: list[str], check: bool = False) -> tuple[int, str, str]:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", "Command not found"
    except Exception as e:
        return -1, "", str(e)


def check_uv_setup() -> bool:
    """Check if uv and .venv are properly set up."""
    print_header("Step 1: Verifying uv and .venv")

    project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    venv_path = project_root / ".venv"

    # Check if pyproject.toml exists
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        print_error("pyproject.toml not found in project root")
        return False
    print_success("pyproject.toml found")

    # Check .venv directory
    if not venv_path.exists():
        print_warning(".venv directory not found")
        print_info("Run: uv venv to create virtual environment")
        return False
    print_success(".venv directory exists")

    # Check Python in .venv
    venv_python = venv_path / "bin" / "python3"
    if not venv_python.exists():
        print_error("Python not found in .venv")
        return False

    # Test that .venv Python works
    code, stdout, stderr = run_command([str(venv_python), "--version"])
    if code == 0:
        print_success(f"Python in .venv: {stdout.strip()}")
    else:
        print_error(f"Failed to run Python in .venv: {stderr}")
        return False

    # Check uv is available
    code, stdout, stderr = run_command(["which", "uv"])
    if code == 0:
        print_success(f"uv found: {stdout.strip()}")
    else:
        print_error("uv not found in PATH")
        print_info("Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

    # Check dependencies are installed
    code, stdout, stderr = run_command([
        str(venv_python), "-c", "import fastmcp"
    ])
    if code == 0:
        print_success("fastmcp installed in .venv")
    else:
        print_warning("fastmcp not installed")
        print_info("Run: uv sync to install dependencies")
        return False

    return True


def check_ollama() -> bool:
    """Check Ollama connectivity and model availability."""
    print_header("Step 2: Checking Ollama (localhost:11434)")

    import urllib.request
    import urllib.error

    # Check if Ollama is running
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            print_success("Ollama is running")

            # Check available models
            models = data.get("models", [])
            if models:
                print_info("Available models:")
                for m in models:
                    print(f"  - {m.get('name', 'unknown')}")
                    print_success(f"Found {len(models)} model(s)")
            else:
                print_warning("No models downloaded")
                print_info("Run: ollama pull qwen2.5-coder:7b")
            return True

    except urllib.error.URLError as e:
        print_error(f"Cannot connect to Ollama: {e}")
        print_info("Start Ollama: ollama serve")
        return False
    except Exception as e:
        print_error(f"Error checking Ollama: {e}")
        return False


def check_mcp_servers() -> bool:
    """Verify all 6 MCP servers can be imported."""
    print_header("Step 3: Verifying 6 MCP Servers")

    project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    venv_python = project_root / ".venv" / "bin" / "python3"

    # MCP servers to check (from opencode.json mcp section)
    mcp_servers = [
        ("n-xyme-core", "core_mcp"),
        ("nx-mind", "nx_mind_mcp"),
        ("unified-memory", "packages.memory_core.mcp_server"),
        ("learning-engine", "packages.learning_engine.mcp_server"),
        ("intelligence", "packages.intelligence.mcp_server"),
        ("quality-gates", "quality_gates_mcp"),
    ]

    all_passed = True

    for name, module in mcp_servers:
        code, stdout, stderr = run_command([
            str(venv_python), "-c", f"import {module}"
        ])
        if code == 0:
            print_success(f"{name}: can be imported")
        else:
            print_error(f"{name}: import failed - {stderr.splitlines()[0] if stderr else 'unknown error'}")
            all_passed = False

    return all_passed


def check_opencode_config() -> bool:
    """Verify OpenCode config validity."""
    print_header("Step 4: Validating OpenCode Config")

    project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
    config_path = project_root / "opencode.json"

    if not config_path.exists():
        print_error("opencode.json not found")
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)

        # Check required sections
        required = ["model", "mcp", "provider"]
        for key in required:
            if key in config:
                print_success(f"Config has '{key}' section")
            else:
                print_error(f"Missing required config section: {key}")
                return False

        # Count MCP servers
        mcp_count = len(config.get("mcp", {}))
        print_info(f"Found {mcp_count} MCP server configurations")

        # Check enabled providers
        providers = config.get("enabled_providers", [])
        print_info(f"Enabled providers: {', '.join(providers)}")

        print_success("OpenCode config is valid JSON")
        return True

    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in opencode.json: {e}")
        return False
    except Exception as e:
        print_error(f"Error reading config: {e}")
        return False


def is_interactive() -> bool:
    """Check if running in interactive mode."""
    return sys.stdin.isatty()


def safe_input(prompt: str) -> str:
    """Safe input that returns empty string if not interactive."""
    if not is_interactive():
        return ""
    try:
        return input(prompt)
    except EOFError:
        return ""


def offer_fixes() -> None:
    """Offer to fix common issues."""
    if not is_interactive():
        print_info("Skipping interactive fixes (non-interactive mode)")
        return

    print_header("Offering Fixes for Common Issues")

    project_root = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

    # Check PYTHONPATH
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    expected_pythonpath = str(project_root)

    if current_pythonpath != expected_pythonpath:
        print_warning(f"PYTHONPATH is not set correctly")
        print_info(f"  Current: {current_pythonpath or '(not set)'}")
        print_info(f"  Expected: {expected_pythonpath}")

        response = safe_input(f"\n{Colors.YELLOW}Set PYTHONPATH to {project_root}? (y/n): {Colors.END}")
        if response.lower() == "y":
            # Write to a shell rc file
            rc_file = project_root / ".env.sh"
            if not rc_file.exists():
                with open(rc_file, "w") as f:
                    f.write(f"export PYTHONPATH={project_root}\n")
            print_success("Added PYTHONPATH to .env.sh")
            print_info("Run: source .env.sh to apply")

    # Check .env file
    env_file = project_root / ".env"
    if not env_file.exists():
        print_warning(".env file not found")
        response = safe_input(f"\n{Colors.YELLOW}Create .env from .env.example? (y/n): {Colors.END}")
        if response.lower() == "y":
            example = project_root / ".env.example"
            if example.exists():
                import shutil
                shutil.copy(example, env_file)
                print_success("Created .env from template")
                print_info("Edit .env to add your API keys")
            else:
                print_error(".env.example not found")

    # Check uv sync
    venv_python = project_root / ".venv" / "bin" / "python3"
    if not (project_root / ".venv").exists():
        print_warning("Virtual environment not set up")
        response = safe_input(f"\n{Colors.YELLOW}Run 'uv venv && uv sync'? (y/n): {Colors.END}")
        if response.lower() == "y":
            print_info("Running uv venv...")
            run_command(["uv", "venv"], check=True)
            print_info("Running uv sync...")
            run_command(["uv", "sync"], check=True)
            print_success("Environment set up")


def main() -> int:
    """Main wizard entry point."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        N-Xyme_MIND Setup Wizard - First Run Setup        ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    results = {}

    # Run all checks
    results["uv_setup"] = check_uv_setup()
    results["ollama"] = check_ollama()
    results["mcp_servers"] = check_mcp_servers()
    results["opencode_config"] = check_opencode_config()

    # Summary
    print_header("Setup Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    if passed == total:
        print_success(f"All checks passed ({passed}/{total})")
        print(f"\n{Colors.GREEN}N-Xyme_MIND is ready to use!{Colors.END}")
        print_info("Run: opencode-desktop or uv run opencode")
    else:
        print_error(f"Some checks failed ({passed}/{total} passed)")
        print_warning("Offering fixes...")
        offer_fixes()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())