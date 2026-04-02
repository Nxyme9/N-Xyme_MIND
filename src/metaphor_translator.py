"""Metaphor Translator — speaks your language, not technical jargon."""

METAPHOR_MAP = {
    "triggers wired": "synapses connected",
    "tests pass": "organs healthy",
    "services online": "hive mind awake",
    "embeddings done": "memories crystallized",
    "patterns found": "insights emerged",
    "velocity": "cognitive speed",
    "friction": "cognitive drag",
    "verification": "consciousness check",
    "claims verified": "truth confirmed",
    "blocks cataloged": "enzymes cataloged",
    "config valid": "nervous system healthy",
    "memory stored": "knowledge preserved",
    "healthy": "blood flowing",
    "degraded": "walking through fog",
    "down": "lost in the void",
    "error": "storm gathering",
    "warning": "clouds on horizon",
    "success": "sun has risen",
    "failed": "wound needs stitching",
}

def translate_status(technical):
    parts = []
    for key, value in technical.items():
        metaphor = METAPHOR_MAP.get(key.lower(), key)
        parts.append(f"{metaphor}: {value}")
    return " | ".join(parts)

def translate_event(event):
    source = event.get("source", "")
    action = event.get("action", "")
    severity = event.get("severity", "")
    severity_metaphor = METAPHOR_MAP.get(severity.lower(), severity)
    return f"{source} {action} — {severity_metaphor}"
