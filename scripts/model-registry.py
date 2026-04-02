#!/usr/bin/env python3
"""N-Xyme Model Registry - Capability ratings and safety constraints for all models."""

import json
import sys
from datetime import datetime
from pathlib import Path

CATALYST_DIR = Path(os.environ.get("CATALYST_DIR", Path(__file__).resolve().parent.parent))

# Model capability registry with safety ratings
MODEL_REGISTRY = {
    # === EXCELLENT TIER ===
    "mimo-v2-pro-free": {
        "tier": "excellent",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high", "critical"],
        "max_consecutive_retries": 5,
        "warnings": [],
    },
    "minimax-m2.5-free": {
        "tier": "excellent",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high", "critical"],
        "max_consecutive_retries": 5,
        "warnings": [],
    },
    "mimo-v2-omni-free": {
        "tier": "excellent",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "medium",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 3,
        "warnings": [
            "Causes loops with Metis/Momus agents - use minimax-m2.5-free instead"
        ],
    },
    # === GOOD TIER ===
    "qwen2.5-coder:14b-instruct-q4_0": {
        "tier": "good",
        "speed": "slow",
        "tool_calling": "via_toolbridge",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 4,
        "warnings": ["Requires ToolBridge for tool calling"],
    },
    "qwen2.5-coder:14b": {
        "tier": "good",
        "speed": "slow",
        "tool_calling": "via_toolbridge",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 4,
        "warnings": ["Requires ToolBridge for tool calling"],
    },
    "qwen2.5-coder:7b": {
        "tier": "good",
        "speed": "medium",
        "tool_calling": "via_toolbridge",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 4,
        "warnings": ["Requires ToolBridge for tool calling"],
    },
    "deepseek-r1:14b": {
        "tier": "good",
        "speed": "slow",
        "tool_calling": "none",
        "loop_risk": "medium",
        "safe_for": ["low", "medium"],
        "max_consecutive_retries": 3,
        "warnings": [
            "No tool calling - reasoning only",
            "Higher loop risk on complex tasks",
        ],
    },
    "deepseek-coder-v2:16b": {
        "tier": "good",
        "speed": "slow",
        "tool_calling": "none",
        "loop_risk": "medium",
        "safe_for": ["low", "medium"],
        "max_consecutive_retries": 3,
        "warnings": [
            "No tool calling - coding only",
            "Higher loop risk on complex tasks",
        ],
    },
    "qwen3:8b": {
        "tier": "good",
        "speed": "medium",
        "tool_calling": "via_toolbridge",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 4,
        "warnings": ["Requires ToolBridge for tool calling"],
    },
    "llama3.1:8b": {
        "tier": "good",
        "speed": "medium",
        "tool_calling": "native",
        "loop_risk": "low",
        "safe_for": ["low", "medium", "high"],
        "max_consecutive_retries": 4,
        "warnings": [],
    },
    # === BASIC TIER ===
    "llama3.2:3b-instruct-q4_K_M": {
        "tier": "basic",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "medium",
        "safe_for": ["low", "medium"],
        "max_consecutive_retries": 3,
        "warnings": ["Small model - may struggle with complex tasks"],
    },
    "llama3.2:3b": {
        "tier": "basic",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "medium",
        "safe_for": ["low", "medium"],
        "max_consecutive_retries": 3,
        "warnings": ["Small model - may struggle with complex tasks"],
    },
    "llama3.2:latest": {
        "tier": "basic",
        "speed": "fast",
        "tool_calling": "native",
        "loop_risk": "medium",
        "safe_for": ["low", "medium"],
        "max_consecutive_retries": 3,
        "warnings": ["Small model - may struggle with complex tasks"],
    },
    "sciphi/triplex:1.5b": {
        "tier": "basic",
        "speed": "very_fast",
        "tool_calling": "none",
        "loop_risk": "high",
        "safe_for": ["low"],
        "max_consecutive_retries": 2,
        "warnings": [
            "Very small model - minimal capabilities",
            "No tool calling",
            "High loop risk",
        ],
    },
}


def get_model(model_name):
    """Get model info from registry."""
    return MODEL_REGISTRY.get(model_name)


def check_safety(model_name, risk_level):
    """Check if model is safe for given risk level."""
    model = get_model(model_name)
    if not model:
        return {"safe": False, "reason": f"Unknown model: {model_name}"}
    if risk_level not in model["safe_for"]:
        return {
            "safe": False,
            "reason": f"Model {model_name} not safe for {risk_level} risk tasks",
            "safe_for": model["safe_for"],
        }
    return {"safe": True, "model": model_name, "risk_level": risk_level}


def list_models(tier=None):
    """List all models, optionally filtered by tier."""
    models = {}
    for name, info in MODEL_REGISTRY.items():
        if tier and info["tier"] != tier:
            continue
        models[name] = info
    return models


def get_report():
    """Generate full registry report."""
    return {
        "timestamp": datetime.now().isoformat(),
        "model_count": len(MODEL_REGISTRY),
        "tiers": {
            "excellent": len(
                [m for m in MODEL_REGISTRY.values() if m["tier"] == "excellent"]
            ),
            "good": len([m for m in MODEL_REGISTRY.values() if m["tier"] == "good"]),
            "basic": len([m for m in MODEL_REGISTRY.values() if m["tier"] == "basic"]),
        },
        "models": MODEL_REGISTRY,
    }


def main():
    if "--json" in sys.argv:
        report = get_report()
        print(json.dumps(report, indent=2))
        return

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "check":
            if len(sys.argv) < 4:
                print("Usage: model-registry.py check <model> <risk_level>")
                return
            result = check_safety(sys.argv[2], sys.argv[3])
            print(json.dumps(result, indent=2))
            return

        if cmd == "list":
            tier = sys.argv[2] if len(sys.argv) > 2 else None
            models = list_models(tier)
            for name, info in models.items():
                print(
                    f"  {name}: {info['tier']} | {info['speed']} | tools={info['tool_calling']} | loop_risk={info['loop_risk']}"
                )
            return

        if cmd == "get":
            if len(sys.argv) < 3:
                print("Usage: model-registry.py get <model>")
                return
            model = get_model(sys.argv[2])
            if model:
                print(json.dumps({sys.argv[2]: model}, indent=2))
            else:
                print(f"Unknown model: {sys.argv[2]}")
            return

    # Default: print summary
    print("=" * 60)
    print("  N-XYME MODEL REGISTRY")
    print("=" * 60)

    for tier in ["excellent", "good", "basic"]:
        models = list_models(tier)
        if not models:
            continue
        print(f"\n  [{tier.upper()} TIER]")
        for name, info in models.items():
            warnings = (
                f" ⚠ {len(info['warnings'])} warning(s)" if info["warnings"] else ""
            )
            print(f"    {name}")
            print(
                f"      speed={info['speed']} tools={info['tool_calling']} loop_risk={info['loop_risk']}"
            )
            print(
                f"      safe_for={info['safe_for']} max_retries={info['max_consecutive_retries']}{warnings}"
            )

    print("\n" + "=" * 60)
    print("  Usage:")
    print("    model-registry.py check <model> <risk_level>")
    print("    model-registry.py list [tier]")
    print("    model-registry.py get <model>")
    print("    model-registry.py --json")
    print("=" * 60)


if __name__ == "__main__":
    main()
