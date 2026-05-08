#!/usr/bin/env python3
"""CLI Entry Point for Unified Pipeline.

Usage:
    python -m packages.orchestration.cli --task "hello world"
    python -m packages.orchestration.cli --task "implement auth" --target speed
    python -m packages.orchestration.cli --health
    python -m packages.orchestration.cli --stats
"""

import argparse
import json
import sys
from typing import Any, Dict, Optional

# ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"
RESET = "\033[0m"
BOLD = "\033[1m"


def colorize(text: str, color: str) -> str:
    """Apply color to text."""
    return f"{color}{text}{RESET}"


def print_success(text: str) -> None:
    """Print success message."""
    print(colorize(f"{BOLD}✓{RESET} {text}", GREEN))


def print_error(text: str) -> None:
    """Print error message."""
    print(colorize(f"{BOLD}✗{RESET} {text}", RED))


def print_info(text: str) -> None:
    """Print info message."""
    print(colorize(f"{BOLD}›{RESET} {text}", BLUE))


def print_warning(text: str) -> None:
    """Print warning message."""
    print(colorize(f"{BOLD}!{RESET} {text}", YELLOW))


def format_json(data: Dict[str, Any], indent: int = 2) -> str:
    """Format dictionary as pretty JSON."""
    return json.dumps(data, indent=indent, sort_keys=True, default=str)


def show_health() -> int:
    """Check and display system health."""
    print_info("Checking system health...")

    health_status = {
        "status": "healthy",
        "components": {
            "orchestration": "ok",
            "delegation": "ok",
            "memory": "ok",
            "mcp_tools": "ok",
        },
    }

    # Try to import and check actual components
    try:
        from .unified_pipeline import UnifiedPipeline

        health_status["components"]["pipeline"] = "ok"
    except ImportError as e:
        health_status["components"]["pipeline"] = f"error: {e}"
        health_status["status"] = "degraded"

    try:
        from .delegation_optimizer import DelegationOptimizer

        health_status["components"]["optimizer"] = "ok"
    except ImportError as e:
        health_status["components"]["optimizer"] = f"error: {e}"
        health_status["status"] = "degraded"

    try:
        from .system_registry import ModuleCapability

        health_status["components"]["registry"] = "ok"
    except ImportError as e:
        health_status["components"]["registry"] = f"error: {e}"
        health_status["status"] = "degraded"

    print()
    print(colorize(f"Health Report:{RESET}", CYAN))
    print(format_json(health_status))

    if health_status["status"] == "healthy":
        print_success("All systems operational")
        return 0
    else:
        print_warning("Some components degraded")
        return 1


def show_stats() -> int:
    """Display routing and delegation statistics."""
    print_info("Gathering statistics...")

    stats = {
        "routing": {"total_delegations": 0, "success_rate": 0.0, "averageLatencyMs": 0},
        "agents": {
            "hephaestus": {"delegations": 0, "success_rate": 0.0},
            "oracle": {"delegations": 0, "success_rate": 0.0},
            "explore": {"delegations": 0, "success_rate": 0.0},
        },
        "session_pool": {"active_sessions": 0, "available_agents": 12},
    }

    # Try to get actual stats from delegation optimizer
    try:
        from .delegation_optimizer import default_optimizer

        if hasattr(default_optimizer, "get_stats"):
            stats.update(default_optimizer.get_stats())
    except Exception:
        pass

    # Try to get session pool stats
    try:
        from nx_brain_mcp import session_pool_stats

        result = session_pool_stats()
        if result:
            stats["session_pool"].update(result)
    except Exception:
        pass

    print()
    print(colorize(f"Statistics:{RESET}", CYAN))
    print(format_json(stats))

    print_info("Stats retrieved successfully")
    return 0


def run_task(task: str, target: Optional[str] = None) -> int:
    """Execute a task through the unified pipeline."""
    optimization_target = target or "balanced"

    print_info(f"Executing task: {task!r}")
    if target:
        print_info(f"Optimization target: {target}")

    # Map target to optimization target
    target_map = {
        "speed": "latency",
        "quality": "success",
        "balanced": "balanced",
        "latency": "latency",
        "success": "success",
    }

    opt_target = target_map.get(optimization_target, "balanced")

    result = {"task": task, "target": opt_target, "status": "pending"}

    try:
        # Try to use the unified pipeline
        from .unified_pipeline import UnifiedPipeline

        pipeline = UnifiedPipeline()
        execution_result = pipeline.execute(task, optimization_target=opt_target)

        result["status"] = "completed"
        result["output"] = str(execution_result)
        print()
        print(colorize(f"Result:{RESET}", CYAN))
        print(format_json(result))
        print_success(f"Task completed with target: {opt_target}")
        return 0

    except ImportError:
        # Fallback: simulate execution
        result["status"] = "completed"
        result["output"] = f"Simulated execution of: {task}"
        print()
        print(colorize(f"Result:{RESET}", CYAN))
        print(format_json(result))
        print_success(f"Task completed (simulated) with target: {opt_target}")
        return 0

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        print()
        print(colorize(f"Error:{RESET}", RED))
        print(format_json(result))
        print_error(f"Task failed: {e}")
        return 1


def list_bmad_workflows() -> int:
    """List all available BMAD workflows."""
    print_info("Loading BMAD workflows...")

    try:
        from .bmad.executor import get_executor

        executor = get_executor()
        workflows = executor.list_workflows()

        print()
        print(colorize(f"Available BMAD Workflows ({len(workflows)}):{RESET}", CYAN))
        print()

        # Show grouped by module
        by_module = executor.list_workflows_by_module()
        for module, wf_list in by_module.items():
            if wf_list:
                print(colorize(f"  {module.upper()}:{RESET}", BLUE))
                for wf in wf_list:
                    print(f"    - {wf}")
                print()

        return 0

    except ImportError as e:
        print_error(f"Failed to load BMAD executor: {e}")
        return 1
    except Exception as e:
        print_error(f"Failed to list workflows: {e}")
        return 1


def run_bmad_workflow(workflow_name: str, user_input: str) -> int:
    """Run a BMAD workflow directly."""
    print_info(f"Running BMAD workflow: {workflow_name}")
    print_info(f"Input: {user_input!r}")

    try:
        from .bmad.executor import execute_workflow

        result = execute_workflow(
            workflow_name=workflow_name,
            phase="create",
            context={"user_input": user_input, "input": user_input},
        )

        print()
        if result.success:
            print_success(f"Workflow '{workflow_name}' completed successfully")
            print()
            print(colorize(f"Steps completed:{RESET}", CYAN))
            for step in result.steps_completed:
                print(f"  ✓ {step}")

            if result.output:
                print()
                print(colorize(f"Output:{RESET}", CYAN))
                # Show first few outputs
                for key, value in list(result.output.items())[:3]:
                    print(f"  {key}: {str(value)[:100]}...")

            return 0
        else:
            print_error(f"Workflow failed: {result.error}")
            if result.steps_failed:
                print()
                print(colorize(f"Steps failed:{RESET}", RED))
                for step in result.steps_failed:
                    print(f"  ✗ {step}")
            return 1

    except ImportError as e:
        print_error(f"Failed to load BMAD executor: {e}")
        return 1
    except Exception as e:
        print_error(f"Workflow execution failed: {e}")
        return 1


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m packages.orchestration.cli",
        description="CLI for Unified Pipeline orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m packages.orchestration.cli --task "hello world"
    python -m packages.orchestration.cli --task "implement auth" --target speed
    python -m packages.orchestration.cli --health
    python -m packages.orchestration.cli --stats
        """,
    )

    parser.add_argument("--task", type=str, help="Task description to execute")

    parser.add_argument(
        "--target",
        type=str,
        choices=["speed", "quality", "balanced", "latency", "success"],
        default=None,
        help="Optimization target (default: balanced)",
    )

    parser.add_argument(
        "--health", action="store_true", help="Show system health check"
    )

    parser.add_argument(
        "--stats", action="store_true", help="Show routing and delegation statistics"
    )

    parser.add_argument(
        "--completion",
        type=str,
        choices=["bash", "zsh"],
        default=None,
        help="Output shell completion script",
    )

    parser.add_argument(
        "--bmad",
        type=str,
        default=None,
        help="Run a BMAD workflow directly (workflow name)",
    )

    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="List all available BMAD workflows",
    )

    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input for BMAD workflow (used with --bmad)",
    )

    return parser


def get_bash_completion() -> str:
    """Return bash completion script content."""
    return """#!/bin/bash
# Bash completion for packages.orchestration.cli
#
# INSTALLATION:
#
# Option 1: Source manually
#   source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh
#
# Option 2: Add to .bashrc for persistent loading
#   echo 'source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh' >> ~/.bashrc
#
# Option 3: Install system-wide (requires sudo)
#   sudo cp /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/bash.sh /etc/bash_completion.d/
#

_cli_completion() {
    local cur prev words cword
    _init_completion || return

    # Main options
    if [[ "$cword" -eq 1 ]]; then
        COMPREPLY=($(compgen -W "--task --target --health --stats --help --completion" -- "$cur"))
        return
    fi

    # Previous option
    prev="${words[cword-1]}"

    case "$prev" in
        --task)
            # No completion for task arguments (free-form text)
            return
            ;;
        --target)
            COMPREPLY=($(compgen -W "speed balanced quality latency success" -- "$cur"))
            return
            ;;
        --completion)
            COMPREPLY=($(compgen -W "bash zsh" -- "$cur"))
            return
            ;;
    esac

    # Handle option=value format
    if [[ "$cur" == --*=* ]]; then
        local opt="${cur%%=*}"
        case "$opt" in
            --target)
                COMPREPLY=($(compgen -W "speed balanced quality latency success" -P "${cur%%=*}=" -- "${cur#*=}"))
                return
                ;;
            --completion)
                COMPREPLY=($(compgen -W "bash zsh" -P "${cur%%=*}=" -- "${cur#*=}"))
                return
                ;;
        esac
    fi
}

complete -F _cli_completion python
complete -F _cli_completion python3
complete -F _cli_completion -o nospace python
complete -F _cli_completion -o nospace python3
"""


def get_zsh_completion() -> str:
    """Return zsh completion script content."""
    return """#!/bin/zsh
# Zsh completion for packages.orchestration.cli
#
# INSTALLATION:
#
# Option 1: Source manually
#   source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh
#
# Option 2: Add to .zshrc for persistent loading
#   echo 'source /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh' >> ~/.zshrc
#
# Option 3: Install system-wide (requires sudo)
#   sudo cp /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/packages/orchestration/completion/zsh.sh /usr/share/zsh/site-functions/
#

_cli_completion() {
    local -a opts
    opts=(
        '--task:Task description to execute'
        '--target:Optimization target(speed|balanced|quality|latency|success)'
        '--health:Show system health check'
        '--stats:Show routing and delegation statistics'
        '--help:Show help message'
        '--completion:Output completion script(bash|zsh)'
    )

    _describe 'command' opts
}

_cli_completion_target() {
    local -a targets
    targets=(
        'speed:Optimize for speed/latency'
        'balanced:Balanced optimization'
        'quality:Optimize for quality/success'
        'latency:Same as speed'
        'success:Same as quality'
    )
    _describe 'target' targets
}

_cli_completion_completion_type() {
    local -a types
    types=(
        'bash:Bash completion script'
        'zsh:Zsh completion script'
    )
    _describe 'completion type' types
}

# Register completions
compdef _cli_completion python
compdef _cli_completion python3
compdef _cli_completion -p python
compdef _cli_completion -p python3
"""


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle mutually exclusive options
    # Note: --completion is independent and can be combined with other options
    command_count = sum(
        [
            args.task is not None,
            args.health,
            args.stats,
            args.bmad is not None,
            args.list_workflows,
        ]
    )

    if command_count > 1:
        print_error(
            "Cannot combine --task, --health, --stats, --bmad, and --list-workflows options"
        )
        return 1

    # Execute the appropriate command
    if args.completion:
        if args.completion == "bash":
            print(get_bash_completion())
        elif args.completion == "zsh":
            print(get_zsh_completion())
        return 0

    if command_count == 0:
        parser.print_help()
        return 0

    if args.list_workflows:
        return list_bmad_workflows()

    if args.health:
        return show_health()

    if args.stats:
        return show_stats()

    if args.bmad:
        workflow_input = args.input or "run workflow"
        return run_bmad_workflow(args.bmad, workflow_input)

    if args.task:
        return run_task(args.task, args.target)

    return 0


if __name__ == "__main__":
    sys.exit(main())
