#!/usr/bin/env python3
"""CLI for managing N-Xyme Dictate settings."""

import argparse
import json
import sys
from pathlib import Path


def get_config_dir() -> Path:
    return Path.home() / ".config" / "nx_dictate"


def load_dict() -> dict:
    path = get_config_dir() / "dictionary.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_dict(data: dict):
    get_config_dir().mkdir(parents=True, exist_ok=True)
    path = get_config_dir() / "dictionary.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_snippets() -> dict:
    path = get_config_dir() / "snippets.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_snippets(data: dict):
    get_config_dir().mkdir(parents=True, exist_ok=True)
    path = get_config_dir() / "snippets.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def cmd_dictionary(args):
    if args.add:
        d = load_dict()
        d[args.add[0].lower()] = args.add[1]
        save_dict(d)
        print(f"Added: {args.add[0]} -> {args.add[1]}")
    elif args.remove:
        d = load_dict()
        key = args.remove[0].lower()
        if key in d:
            del d[key]
            save_dict(d)
            print(f"Removed: {args.remove[0]}")
        else:
            print(f"Not found: {args.remove[0]}")
    elif args.list:
        d = load_dict()
        if d:
            print("Personal Dictionary:")
            for k, v in d.items():
                print(f"  {k} -> {v}")
        else:
            print("Dictionary is empty")
    else:
        print("Use --add, --remove, or --list")


def cmd_snippets(args):
    if args.add:
        s = load_snippets()
        s[args.add[0].lower()] = args.add[1]
        save_snippets(s)
        print(f"Added snippet: {args.add[0]} -> {args.add[1]}")
    elif args.remove:
        s = load_snippets()
        key = args.remove[0].lower()
        if key in s:
            del s[key]
            save_snippets(s)
            print(f"Removed snippet: {args.remove[0]}")
        else:
            print(f"Not found: {args.remove[0]}")
    elif args.list:
        s = load_snippets()
        if s:
            print("Snippets:")
            for k, v in s.items():
                print(f"  {k} -> {v[:50]}{'...' if len(v) > 50 else ''}")
        else:
            print("No snippets defined")
    else:
        print("Use --add, --remove, or --list")


def main():
    parser = argparse.ArgumentParser(prog="nxyme-dictate-ctl", description="Manage N-Xyme Dictate")
    subparsers = parser.add_subparsers()

    p_dict = subparsers.add_parser("dict", help="Manage personal dictionary")
    p_dict.add_argument("--add", nargs=2, metavar=("WORD", "REPLACEMENT"), help="Add word")
    p_dict.add_argument("--remove", nargs=1, metavar="WORD", help="Remove word")
    p_dict.add_argument("--list", action="store_true", help="List dictionary")
    p_dict.set_defaults(func=cmd_dictionary)

    p_snip = subparsers.add_parser("snippet", help="Manage snippets")
    p_snip.add_argument("--add", nargs=2, metavar=("TRIGGER", "EXPANSION"), help="Add snippet")
    p_snip.add_argument("--remove", nargs=1, metavar="TRIGGER", help="Remove snippet")
    p_snip.add_argument("--list", action="store_true", help="List snippets")
    p_snip.set_defaults(func=cmd_snippets)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()