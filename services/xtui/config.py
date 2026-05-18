"""Configuration for XTUI."""
import json, os

DEFAULT_CONFIG = {
    "theme": "dark",
    "history_size": 1000,
    "mcp_timeout": 30,
    "prompt_format": "[{agent_short}]> ",
    "timestamp": True,
    "colors": {
        "primary": "cyan",
        "secondary": "green",
        "error": "red",
        "warning": "yellow",
        "dim": "dim",
        "agent_highlight": "bold green",
    },
    "aliases": {
        "c": "catalyst",
        "h": "hephaestus",
        "a": "atlas",
        "m": "hermes",
        "p": "prometheus",
        "o": "oracle",
        "e": "explore",
    },
    "plugins_dir": "~/.xtui/plugins",
}

def load():
    path = os.path.expanduser("~/.xtui/config.json")
    config = DEFAULT_CONFIG.copy()
    try:
        with open(path) as f:
            user = json.load(f)
            config.update(user)
    except:
        pass
    return config
