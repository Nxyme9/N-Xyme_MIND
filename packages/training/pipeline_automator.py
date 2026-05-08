#!/usr/bin/env python3
"""Training Pipeline Automator.

Automates the full training pipeline:
- Generate → Train → Validate → Deploy

Usage:
    python pipeline_automator.py --run              # Full pipeline
    python pipeline_automator.py --generate-only     # Generate only
    python pipeline_automator.py --train-only        # Train only
    python pipeline_automator.py --status            # Check status
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).parent.parent
DATASETS_DIR = PROJECT_ROOT / "datasets"
ADAPTERS_DIR = PROJECT_ROOT / "frankenstein_engine" / "adapters"
PIPELINE_CONFIG = PROJECT_ROOT / ".sisyphus" / "pipeline_config.json"


class PipelineAutomator:
    """Automated training pipeline orchestrator."""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load pipeline configuration."""
        if PIPELINE_CONFIG.exists():
            with open(PIPELINE_CONFIG) as f:
                return json.load(f)
        return {
            "stages": {
                "generate": {"enabled": True, "timeout": 300},
                "train": {"enabled": True, "timeout": 1800},
                "validate": {"enabled": True, "timeout": 60},
                "deploy": {"enabled": True, "timeout": 30},
            },
            "adapter_name": "auto-generated-lora",
            "validation_threshold": 0.90,
            "auto_deploy": True,
            "max_retries": 2,
        }

    def _save_config(self):
        """Save pipeline configuration."""
        with open(PIPELINE_CONFIG, "w") as f:
            json.dump(self.config, f, indent=2)

    def _record_stage(self, stage: str, status: str, details: Dict = None):
        """Record stage result."""
        if "stages_history" not in self.config:
            self.config["stages_history"] = []

        self.config["stages_history"].append(
            {
                "stage": stage,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "details": details or {},
            }
        )

        # Keep only last 20 runs
        if len(self.config["stages_history"]) > 20:
            self.config["stages_history"] = self.config["stages_history"][-20:]

        self._save_config()

    def generate(self) -> Dict:
        """Stage 1: Generate training data."""
        print("[Pipeline] Stage 1: Generate training data...")

        generate_script = (
            PROJECT_ROOT / "packages" / "training" / "generate_training_from_system.py"
        )
        output_file = DATASETS_DIR / "auto_generated.jsonl"
        DATASETS_DIR.mkdir(exist_ok=True)

        if not generate_script.exists():
            self._record_stage("generate", "failed", {"error": "Script not found"})
            return {"status": "failed", "error": f"Script not found: {generate_script}"}

        try:
            result = subprocess.run(
                ["python3", str(generate_script), "--output", str(output_file)],
                capture_output=True,
                text=True,
                timeout=self.config["stages"]["generate"]["timeout"],
            )

            if result.returncode == 0:
                # Count examples
                examples = 0
                if output_file.exists():
                    with open(output_file) as f:
                        examples = sum(1 for _ in f)

                self._record_stage(
                    "generate",
                    "success",
                    {"output": str(output_file), "examples": examples},
                )

                return {
                    "status": "success",
                    "output": str(output_file),
                    "examples": examples,
                }
            else:
                self._record_stage("generate", "failed", {"error": result.stderr})
                return {"status": "failed", "error": result.stderr}

        except subprocess.TimeoutExpired:
            self._record_stage(
                "generate",
                "timeout",
                {"timeout": self.config["stages"]["generate"]["timeout"]},
            )
            return {"status": "timeout", "error": "Generation timed out"}
        except Exception as e:
            self._record_stage("generate", "error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    def train(self, training_data: str, adapter_name: str = None) -> Dict:
        """Stage 2: Train LoRA adapter."""
        print("[Pipeline] Stage 2: Train LoRA adapter...")

        if adapter_name is None:
            adapter_name = self.config["adapter_name"]

        train_script = PROJECT_ROOT / "frankenstein_engine" / "train.py"

        if not train_script.exists():
            self._record_stage("train", "failed", {"error": "Script not found"})
            return {"status": "failed", "error": f"Script not found: {train_script}"}

        # Ensure adapters dir exists
        ADAPTERS_DIR.mkdir(exist_ok=True)

        try:
            result = subprocess.run(
                ["python3", str(train_script), "--adapter", adapter_name, "--train"],
                capture_output=True,
                text=True,
                timeout=self.config["stages"]["train"]["timeout"],
            )

            if result.returncode == 0:
                # Check if adapter was created
                adapter_path = ADAPTERS_DIR / f"{adapter_name}.gguf"

                self._record_stage(
                    "train",
                    "success",
                    {
                        "adapter": adapter_name,
                        "path": str(adapter_path),
                        "exists": adapter_path.exists(),
                    },
                )

                return {
                    "status": "success",
                    "adapter": adapter_name,
                    "path": str(adapter_path),
                }
            else:
                self._record_stage("train", "failed", {"error": result.stderr})
                return {"status": "failed", "error": result.stderr}

        except subprocess.TimeoutExpired:
            self._record_stage(
                "train",
                "timeout",
                {"timeout": self.config["stages"]["train"]["timeout"]},
            )
            return {"status": "timeout", "error": "Training timed out"}
        except Exception as e:
            self._record_stage("train", "error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    def validate(self, adapter_name: str) -> Dict:
        """Stage 3: Validate trained adapter."""
        print("[Pipeline] Stage 3: Validate adapter...")

        # Basic validation: check adapter exists and has valid size
        adapter_path = ADAPTERS_DIR / f"{adapter_name}.gguf"

        if not adapter_path.exists():
            self._record_stage(
                "validate", "failed", {"error": "Adapter file not found"}
            )
            return {"status": "failed", "error": "Adapter file not found"}

        size = adapter_path.stat().st_size
        if size < 1000:  # Less than 1KB is suspicious
            self._record_stage(
                "validate", "failed", {"error": "Adapter file too small"}
            )
            return {"status": "failed", "error": "Adapter file too small"}

        # Try to import and basic test
        try:
            from frankenstein_engine.adapter_hotswap import validate_adapter

            is_valid, message = validate_adapter(adapter_name)

            if is_valid:
                self._record_stage(
                    "validate", "success", {"adapter": adapter_name, "size": size}
                )
                return {
                    "status": "success",
                    "adapter": adapter_name,
                    "size": size,
                    "message": message,
                }
            else:
                self._record_stage("validate", "failed", {"error": message})
                return {"status": "failed", "error": message}

        except Exception as e:
            self._record_stage("validate", "error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    def deploy(self, adapter_name: str) -> Dict:
        """Stage 4: Deploy (hot-swap) adapter."""
        print("[Pipeline] Stage 4: Deploy adapter...")

        try:
            from frankenstein_engine.adapter_hotswap import swap_adapter

            result = swap_adapter(adapter_name, validate=True)

            if result.get("status") == "success":
                self._record_stage(
                    "deploy",
                    "success",
                    {"adapter": adapter_name, "time_ms": result.get("time_ms")},
                )
                return {
                    "status": "success",
                    "adapter": adapter_name,
                    "time_ms": result.get("time_ms"),
                }
            else:
                self._record_stage("deploy", "failed", {"error": result.get("error")})
                return {"status": "failed", "error": result.get("error")}

        except Exception as e:
            self._record_stage("deploy", "error", {"error": str(e)})
            return {"status": "error", "error": str(e)}

    def run_full_pipeline(self) -> Dict:
        """Run complete pipeline: Generate → Train → Validate → Deploy."""
        print("=" * 60)
        print("TRAINING PIPELINE AUTOMATOR")
        print("=" * 60)

        results = {"started": datetime.now().isoformat(), "stages": {}}

        # Stage 1: Generate
        if self.config["stages"]["generate"]["enabled"]:
            gen_result = self.generate()
            results["stages"]["generate"] = gen_result
            if gen_result["status"] != "success":
                results["status"] = "failed_at_generate"
                results["ended"] = datetime.now().isoformat()
                return results
        else:
            results["stages"]["generate"] = {"status": "skipped"}

        # Stage 2: Train
        if self.config["stages"]["train"]["enabled"]:
            adapter_name = self.config["adapter_name"]
            train_result = self.train(None, adapter_name)
            results["stages"]["train"] = train_result
            if train_result["status"] != "success":
                results["status"] = "failed_at_train"
                results["ended"] = datetime.now().isoformat()
                return results
        else:
            results["stages"]["train"] = {"status": "skipped"}

        # Stage 3: Validate
        if self.config["stages"]["validate"]["enabled"]:
            validate_result = self.validate(adapter_name)
            results["stages"]["validate"] = validate_result
            if validate_result["status"] != "success":
                results["status"] = "failed_at_validate"
                results["ended"] = datetime.now().isoformat()
                return results
        else:
            results["stages"]["validate"] = {"status": "skipped"}

        # Stage 4: Deploy
        if self.config["stages"]["deploy"]["enabled"] and self.config.get(
            "auto_deploy"
        ):
            deploy_result = self.deploy(adapter_name)
            results["stages"]["deploy"] = deploy_result
            if deploy_result["status"] != "success":
                results["status"] = "failed_at_deploy"
                results["ended"] = datetime.now().isoformat()
                return results
        else:
            results["stages"]["deploy"] = {"status": "skipped"}

        results["status"] = "success"
        results["ended"] = datetime.now().isoformat()

        print("=" * 60)
        print(f"PIPELINE COMPLETE: {results['status']}")
        print("=" * 60)

        return results

    def get_status(self) -> Dict:
        """Get pipeline status."""
        return {
            "config": self.config,
            "history": self.config.get("stages_history", [])[-5:],
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Training Pipeline Automator")
    parser.add_argument("--run", action="store_true", help="Run full pipeline")
    parser.add_argument("--generate-only", action="store_true", help="Generate only")
    parser.add_argument("--train-only", action="store_true", help="Train only")
    parser.add_argument("--validate-only", action="store_true", help="Validate only")
    parser.add_argument("--deploy-only", action="store_true", help="Deploy only")
    parser.add_argument("--status", action="store_true", help="Check pipeline status")
    parser.add_argument("--adapter", help="Adapter name for train/deploy")

    args = parser.parse_args()

    automator = PipelineAutomator()

    if args.status:
        print(json.dumps(automator.get_status(), indent=2))
    elif args.generate_only:
        print(json.dumps(automator.generate(), indent=2))
    elif args.train_only:
        print(json.dumps(automator.train(None, args.adapter), indent=2))
    elif args.validate_only:
        print(
            json.dumps(
                automator.validate(args.adapter or "auto-generated-lora"), indent=2
            )
        )
    elif args.deploy_only:
        print(
            json.dumps(
                automator.deploy(args.adapter or "auto-generated-lora"), indent=2
            )
        )
    else:
        result = automator.run_full_pipeline()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
