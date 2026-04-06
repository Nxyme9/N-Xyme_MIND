import os
import time
from cachetools import TTLCache
from typing import Literal

Decision = Literal["allow", "deny", "prompt"]

CACHE: TTLCache = TTLCache(maxsize=1000, ttl=300)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_SECURITY_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "10"))

WHITELIST = {
    "ls",
    "ls -la",
    "ls -l",
    "cd",
    "pwd",
    "cat",
    "grep",
    "find",
    "echo",
    "mkdir",
    "touch",
    # "rm",  # Removed: rm can be dangerous, let blacklist handle it
    "cp",
    "mv",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "git status",
    "git log",
    "git diff",
    "git show",
    "npm run",
    "npm test",
    "npm install",
    "pnpm run",
    "pnpm test",
    "pnpm install",
    "python -m",
    "python3 -m",
    "docker ps",
    "docker images",
    "docker logs",
}

BLACKLIST = {
    "rm -rf /",
    "rm -rf /home",
    "rm -rf /var",
    "rm -rf /etc",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",
    "curl http",
    "wget http",
    "ssh ",
    "scp ",
    "sftp ",
    "chmod -R 777",
    "chmod 000",
    "kill -9 -1",
    "killall",
}

SENSITIVE_PATTERNS = [
    "password",
    "secret",
    "api_key",
    "token",
    "credential",
    "Authorization:",
    "Bearer ",
    "AWS_",
    "AZURE_",
]


def check_whitelist(command: str) -> tuple[bool, str]:
    cmd_lower = command.lower().strip()
    for pattern in WHITELIST:
        # Only match if command starts with pattern and is followed by space or end-of-string
        if cmd_lower == pattern:
            return True, f"Whitelisted: {pattern}"
        if cmd_lower.startswith(pattern + " "):
            return True, f"Whitelisted: {pattern}"
    return False, ""


def check_blacklist(command: str) -> tuple[bool, str]:
    cmd_lower = command.lower()
    for pattern in BLACKLIST:
        if pattern in cmd_lower:
            return True, f"Blacklisted: {pattern}"
    return False, ""


def check_sensitive(command: str) -> tuple[bool, list[str]]:
    found = []
    for pattern in SENSITIVE_PATTERNS:
        if pattern.lower() in command.lower():
            found.append(pattern)
    return len(found) > 0, found


def analyze_with_ollama(command: str, context: dict) -> tuple[Decision, str, float]:
    try:
        import httpx

        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a security analyzer. Respond ONLY with: ALLOW|DENY|PROMPT and a brief reason.",
                },
                {
                    "role": "user",
                    "content": f"Command: {command}\nContext: {context}\nDecision:",
                },
            ],
            "stream": False,
        }
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "").upper()

            if content.startswith("ALLOW"):
                return "allow", content, 0.9
            elif content.startswith("DENY"):
                return "deny", content, 0.9
            else:
                return "prompt", content, 0.6
    except Exception as e:
        return "prompt", f"Ollama unavailable: {e}", 0.3


def get_cached(command: str) -> tuple[Decision, str, float] | None:
    key = command[:200]
    if key in CACHE:
        entry = CACHE[key]
        entry["hits"] += 1
        return entry["decision"], entry["reason"], entry["confidence"]
    return None


def store_feedback(command: str, decision: Decision, user_override: Decision):
    key = command[:200]
    if key in CACHE:
        CACHE[key]["user_override"] = user_override
        CACHE[key]["override_count"] = CACHE[key].get("override_count", 0) + 1
