#!/usr/bin/env python3
"""
Brain CLI - Interactive tool calling from terminal
Usage: brain-cli [model]
"""

import argparse
import json
import sys
import os
import readline

API_URL = "http://localhost:8100/brain/execute"
DEFAULT_MODEL = "qwen2.5-coder:7b"


def call_brain(message: str, model: str) -> dict:
    import urllib.request
    import urllib.error

    data = json.dumps({"message": message, "model": model}).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=data, headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason}", "detail": body}
    except urllib.error.URLError as e:
        return {"error": f"Connection failed: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def format_result(result: dict) -> str:
    """Pretty print the result."""
    if "error" in result:
        return f"❌ Error: {result['error']}"

    # Handle text response with content as string
    if result.get("type") == "text":
        content = result.get("content", "")
        # Content may be a JSON string or plain text
        if content.startswith("Result:"):
            # Try to parse the embedded JSON
            try:
                # Strip "Result: " prefix and parse
                json_str = content[8:]  # Remove "Result: "
                data = json.loads(json_str)
                return json.dumps(data, indent=2)
            except:
                return content
        return content

    # Handle direct JSON result
    data = result.get("result", {})
    if isinstance(data, dict):
        return json.dumps(data, indent=2)
    return str(data)


def main():
    parser = argparse.ArgumentParser(description="Brain CLI - Interactive tool calling")
    parser.add_argument("prompt", nargs="?", help="Single prompt (non-interactive)")
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Force interactive mode"
    )
    args = parser.parse_args()

    # If prompt provided as first positional arg, use it
    prompt_arg = args.prompt

    is_interactive = args.interactive or not prompt_arg

    if is_interactive:
        print(f"🧠 Brain CLI - Interactive Mode")
        print(f"   Model: {args.model}")
        print(f"   API: {API_URL}")
        print("   Type 'exit' or 'quit' to stop\n")

        while True:
            try:
                prompt = input("brain> ").strip()
                if prompt.lower() in ("exit", "quit", "q"):
                    print("👋 Goodbye!")
                    break
                if not prompt:
                    continue

                print("🔄 ", end="", flush=True)
                result = call_brain(prompt, args.model)
                print("\n" + format_result(result) + "\n")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                break
    elif prompt_arg:
        result = call_brain(prompt_arg, args.model)
        print(format_result(result))


if __name__ == "__main__":
    main()
