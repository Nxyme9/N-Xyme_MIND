#!/usr/bin/env python3
"""
Model-Specific GGUF Config Manager
Stores and retrieves optimized configs for each model.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any

CONFIG_DIR = Path.home() / ".config" / "nxyme-gguf"
MODELS_CONFIG = CONFIG_DIR / "models.json"

DEFAULT_CONFIGS = {
    # OPTIMIZED for RTX 3080 Ti (12.5GB VRAM) - Tool calling <50ms target
    "qwen2.5-coder-7b-q4_k_m": {
        "threads": 16,
        "threads_batch": 16,
        "context_size": 8192,  # 4096 -> 8192 for larger context tasks
        "gpu_layers": 99,  # All layers to GPU (10-50x speedup)
        "parallel": 16,  # 8 -> 16 concurrent slots (RTX 3080 Ti can handle)
        "batch_size": 4096,  # Max throughput
        "ubatch_size": 2048,  # Micro batch for low latency
        "extra_flags": "--flash-attn on --flash-attn-type 2 --no-mmap -ctk q4_0 -ctv q4_0",  # KV cache Q for 2x context
        "priority": "high",
        "description": "Code generation - RTX 3080 Ti OPTIMIZED (<50ms)",
    },
    "qwen2.5-0.5b-instruct-q4_k_m": {
        "threads": 16,
        "threads_batch": 16,
        "context_size": 8192,
        "gpu_layers": 99,
        "parallel": 16,
        "batch_size": 4096,
        "ubatch_size": 2048,
        "extra_flags": "--flash-attn on --flash-attn-type 2 --no-mmap -ctk q4_0 -ctv q4_0",  # KV cache Q
        "priority": "low",
        "description": "Fast instruction following - RTX 3080 Ti OPTIMIZED",
    },
    "qwen2.5-0.5b-instruct-q4_k_m": {
        "threads": 16,
        "context_size": 4096,
        "gpu_layers": 99,
        "extra_flags": "--flash-attn on",
        "priority": "low",
        "description": "Fast instruction following",
    },
    "nomic-embed-text-v1.5-Q4_K_M": {
        "threads": 16,  # 8 -> 16 for embedding throughput
        "context_size": 4096,  # 2048 -> 4096 for longer texts
        "gpu_layers": 99,
        "parallel": 8,
        "batch_size": 4096,
        "extra_flags": "--flash-attn on --embeddings -ctk q4_0 -ctv q4_0",
        "priority": "medium",
        "description": "Text embeddings - RTX 3080 Ti OPTIMIZED",
    },
    "llama3.2": {
        "threads": 16,
        "context_size": 4096,
        "gpu_layers": 99,
        "extra_flags": "--flash-attn on",
        "priority": "high",
        "description": "General purpose",
    },
    "rosetta-lora": {
        "threads": 16,
        "context_size": 4096,
        "gpu_layers": 99,
        "extra_flags": "",
        "priority": "high",
        "description": "Custom LoRA adapter",
    },
}


class ModelConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.configs = self._load_configs()

    def _load_configs(self) -> Dict:
        if MODELS_CONFIG.exists():
            with open(MODELS_CONFIG) as f:
                return json.load(f)
        return {"models": DEFAULT_CONFIGS.copy()}

    def _save_configs(self):
        with open(MODELS_CONFIG, "w") as f:
            json.dump(self.configs, f, indent=2)

    def get_model_key(self, model_path: str) -> str:
        """Extract model key from path"""
        name = Path(model_path).stem
        for known in self.configs["models"]:
            if known.lower() in name.lower():
                return known
        return name

    def get_config(self, model_path: str) -> Dict:
        """Get optimal config for model"""
        key = self.get_model_key(model_path)

        if key in self.configs["models"]:
            return self.configs["models"][key]

        for known_key, config in self.configs["models"].items():
            if known_key.lower() in key.lower():
                return config

        return {
            "threads": 16,
            "context_size": 4096,
            "gpu_layers": 99,
            "extra_flags": "",
            "priority": "medium",
            "description": "Auto-detected",
        }

    def set_config(self, model_path: str, config: Dict):
        """Save config for model"""
        key = self.get_model_key(model_path)
        self.configs["models"][key] = config
        self._save_configs()

    def generate_launcher_flags(self, model_path: str) -> str:
        """Generate llama-server flags"""
        cfg = self.get_config(model_path)

        flags = [
            f"-t {cfg.get('threads', 16)}",
            f"-c {cfg.get('context_size', 4096)}",
            f"-ngl {cfg.get('gpu_layers', 99)}",
        ]

        extra = cfg.get("extra_flags", "")
        if extra:
            flags.append(extra)

        return " ".join(flags)

    def list_models(self) -> Dict:
        """List all configured models"""
        return self.configs["models"]

    def benchmark_and_update(self, model_path: str, speed: float):
        """Update config with new benchmark result"""
        key = self.get_model_key(model_path)
        if key in self.configs["models"]:
            self.configs["models"][key]["last_speed"] = speed
            self._save_configs()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--model", help="Model path")
    parser.add_argument("--list", action="store_true", help="List all configs")
    parser.add_argument(
        "--set", nargs=2, metavar=("KEY", "VALUE"), help="Set config value"
    )
    args = parser.parse_args()

    mgr = ModelConfigManager()

    if args.list:
        print("📋 Model Configs:")
        for name, cfg in mgr.list_models().items():
            print(f"\n  [{name}]")
            for k, v in cfg.items():
                print(f"    {k}: {v}")
        return

    if args.model:
        config = mgr.get_config(args.model)
        print(f"Config for {args.model}:")
        print(json.dumps(config, indent=2))
        print(f"\n🚀 Flags: {mgr.generate_launcher_flags(args.model)}")


if __name__ == "__main__":
    main()
