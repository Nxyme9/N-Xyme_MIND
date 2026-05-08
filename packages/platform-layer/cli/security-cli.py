#!/usr/bin/env python3
"""CLI tool for filesystem security policy management.

Usage:
    python bin/security-cli.py list
    python bin/security-cli.py show <agent_type>
    python bin/security-cli.py add <agent_type> --paths src/,tests/ --level read_write
    python bin/security-cli.py remove <agent_type>
    python bin/security-cli.py validate <agent_type>
    python bin/security-cli.py save <path>
    python bin/security-cli.py load <path>
    python bin/security-cli.py check <path> <agent_type>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from packages.orchestration.governance.policy import AgentPolicy, SecurityPolicy
from packages.orchestration.governance.sandbox import AccessLevel, FilesystemSandbox


def cmd_list(args: argparse.Namespace) -> None:
    policy = SecurityPolicy(workspace_root=PROJECT_ROOT)
    for p in policy.list_policies():
        print(
            f"{p.agent_type:25s} level={p.access_level.value:12s} symlinks={p.follow_symlinks}"
        )
        for ap in p.allowed_paths:
            print(f"  + {ap}")
        for dp in p.denied_paths:
            print(f"  - {dp}")
        print()


def cmd_show(args: argparse.Namespace) -> None:
    policy = SecurityPolicy(workspace_root=PROJECT_ROOT)
    p = policy.get_policy(args.agent_type)
    if p is None:
        print(f"No policy found for agent type: {args.agent_type}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(p.to_dict(), indent=2, default=str))


def cmd_add(args: argparse.Namespace) -> None:
    policy_obj = SecurityPolicy(workspace_root=PROJECT_ROOT)
    new_policy = AgentPolicy(
        agent_type=args.agent_type,
        allowed_paths=args.paths or ["."],
        access_level=AccessLevel(args.level),
        follow_symlinks=args.follow_symlinks,
        description=args.description or f"Custom policy for {args.agent_type}",
    )
    errors = policy_obj.validate_policy(new_policy)
    if errors:
        print("Policy validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    policy_obj.set_policy(new_policy)
    print(f"Policy set for '{args.agent_type}':")
    print(json.dumps(new_policy.to_dict(), indent=2, default=str))


def cmd_remove(args: argparse.Namespace) -> None:
    policy_obj = SecurityPolicy(workspace_root=PROJECT_ROOT)
    removed = policy_obj.remove_policy(args.agent_type)
    if removed:
        print(f"Removed custom policy for '{args.agent_type}'")
    else:
        print(
            f"Cannot remove default policy or policy not found: '{args.agent_type}'",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    policy_obj = SecurityPolicy(workspace_root=PROJECT_ROOT)
    p = policy_obj.get_policy(args.agent_type)
    if p is None:
        print(f"No policy found for agent type: {args.agent_type}", file=sys.stderr)
        sys.exit(1)
    errors = policy_obj.validate_policy(p)
    if errors:
        print(f"Policy for '{args.agent_type}' has errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"Policy for '{args.agent_type}' is valid")


def cmd_save(args: argparse.Namespace) -> None:
    policy_obj = SecurityPolicy(workspace_root=PROJECT_ROOT)
    policy_obj.save(args.path)
    print(f"Policy saved to {args.path}")


def cmd_load(args: argparse.Namespace) -> None:
    policy_obj = SecurityPolicy.load(args.path, workspace_root=PROJECT_ROOT)
    print(f"Policy loaded from {args.path}")
    for p in policy_obj.list_policies():
        print(f"  {p.agent_type}: {p.access_level.value}")


def cmd_check(args: argparse.Namespace) -> None:
    sandbox = FilesystemSandbox(workspace_root=PROJECT_ROOT)
    policy_obj = SecurityPolicy(workspace_root=PROJECT_ROOT)
    for p in policy_obj.list_policies():
        sandbox.set_policy(
            agent_type=p.agent_type,
            allowed_paths=p.allowed_paths,
            denied_paths=p.denied_paths,
            access_level=p.access_level,
            follow_symlinks=p.follow_symlinks,
        )
    result = sandbox.validate_path(args.path, args.agent_type)
    print(json.dumps(result.to_dict(), indent=2, default=str))
    if not result.allowed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Filesystem security policy management CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    sub.add_parser("list", help="List all policies")

    # show
    p_show = sub.add_parser("show", help="Show policy for an agent type")
    p_show.add_argument("agent_type", help="Agent type name")

    # add
    p_add = sub.add_parser("add", help="Add or update a policy")
    p_add.add_argument("agent_type", help="Agent type name")
    p_add.add_argument("--paths", nargs="*", help="Allowed paths")
    p_add.add_argument(
        "--level", default="read", choices=["none", "read", "read_write", "full"]
    )
    p_add.add_argument("--follow-symlinks", action="store_true", default=False)
    p_add.add_argument("--description", default="")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a custom policy")
    p_rm.add_argument("agent_type", help="Agent type name")

    # validate
    p_val = sub.add_parser("validate", help="Validate a policy")
    p_val.add_argument("agent_type", help="Agent type name")

    # save
    p_save = sub.add_parser("save", help="Save policies to file")
    p_save.add_argument("path", help="Output file path")

    # load
    p_load = sub.add_parser("load", help="Load policies from file")
    p_load.add_argument("path", help="Input file path")

    # check
    p_check = sub.add_parser("check", help="Check path access for an agent")
    p_check.add_argument("path", help="Path to check")
    p_check.add_argument("agent_type", help="Agent type name")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "show": cmd_show,
        "add": cmd_add,
        "remove": cmd_remove,
        "validate": cmd_validate,
        "save": cmd_save,
        "load": cmd_load,
        "check": cmd_check,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
