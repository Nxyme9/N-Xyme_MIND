#!/usr/bin/env python3
"""Training Auto-Trigger System.

Automatically triggers training when enough new tool_sequences accumulate.
Threshold: 50 new sequences triggers training pipeline.

Usage:
    python training_trigger.py --check          # Check threshold, trigger if met
    python training_trigger.py --status         # Get current training status
    python training_trigger.py --force          # Force training run
"""

import json
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTCOMES_DB = PROJECT_ROOT / ".sisyphus" / "outcomes.db"
CONFIG_FILE = PROJECT_ROOT / ".sisyphus" / "training_trigger_config.json"
DATASETS_DIR = PROJECT_ROOT / "datasets"


def get_sequence_count(since_timestamp: Optional[str] = None) -> int:
    """Get count of tool_sequences since last run."""
    if not OUTCOMES_DB.exists():
        return 0

    conn = sqlite3.connect(str(OUTCOMES_DB))
    cursor = conn.cursor()

    if since_timestamp:
        cursor.execute(
            "SELECT COUNT(*) FROM tool_sequences WHERE timestamp > ?",
            (since_timestamp,),
        )
    else:
        cursor.execute("SELECT COUNT(*) FROM tool_sequences")

    count = cursor.fetchone()[0]
    conn.close()
    return count


def load_config() -> Dict:
    """Load trigger configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {
        "threshold": 50,
        "last_check": None,
        "last_trigger": None,
        "last_run_timestamp": None,
        "total_runs": 0,
        "enabled": True,
    }


def save_config(config: Dict):
    """Save trigger configuration."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def check_and_trigger_training() -> Dict:
    """Check if threshold met, trigger if yes."""
    config = load_config()

    if not config.get("enabled", True):
        return {"status": "disabled", "message": "Training trigger is disabled"}

    last_run = config.get("last_run_timestamp")
    sequence_count = get_sequence_count(since_timestamp=last_run)

    config["last_check"] = datetime.now().isoformat()
    config["pending_sequences"] = sequence_count
    save_config(config)

    if sequence_count >= config.get("threshold", 50):
        return trigger_training_run()

    return {
        "status": "waiting",
        "pending": sequence_count,
        "threshold": config.get("threshold", 50),
        "message": f"{sequence_count} sequences pending, need {config.get('threshold', 50) - sequence_count} more",
    }


def trigger_training_run() -> Dict:
    """Trigger training pipeline."""
    config = load_config()
    config["last_trigger"] = datetime.now().isoformat()
    config["total_runs"] = config.get("total_runs", 0) + 1
    save_config(config)

    output_file = DATASETS_DIR / "auto_generated.jsonl"
    DATASETS_DIR.mkdir(exist_ok=True)

    # Run generate_training_from_system.py
    script_path = (
        PROJECT_ROOT / "packages" / "training" / "generate_training_from_system.py"
    )

    if script_path.exists():
        try:
            result = subprocess.run(
                ["python3", str(script_path), "--output", str(output_file)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Count generated examples
                examples_count = 0
                if output_file.exists():
                    with open(output_file) as f:
                        examples_count = sum(1 for _ in f)

                return {
                    "status": "success",
                    "output_file": str(output_file),
                    "examples_generated": examples_count,
                    "run_number": config["total_runs"],
                }
            else:
                return {
                    "status": "failed",
                    "error": result.stderr,
                    "run_number": config["total_runs"],
                }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "run_number": config["total_runs"]}
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "run_number": config["total_runs"],
            }

    return {"status": "script_not_found", "path": str(script_path)}


def get_training_status() -> Dict:
    """Get current training status."""
    config = load_config()
    sequence_count = get_sequence_count(
        since_timestamp=config.get("last_run_timestamp")
    )

    return {
        "enabled": config.get("enabled", True),
        "threshold": config.get("threshold", 50),
        "pending_sequences": sequence_count,
        "total_runs": config.get("total_runs", 0),
        "last_check": config.get("last_check"),
        "last_trigger": config.get("last_trigger"),
        "last_run_timestamp": config.get("last_run_timestamp"),
    }


def force_training():
    """Force a training run regardless of threshold."""
    result = trigger_training_run()
    if result.get("status") == "success":
        config = load_config()
        config["last_run_timestamp"] = datetime.now().isoformat()
        save_config(config)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Training Auto-Trigger")
    parser.add_argument(
        "--check", action="store_true", help="Check threshold and trigger if met"
    )
    parser.add_argument("--status", action="store_true", help="Get training status")
    parser.add_argument("--force", action="store_true", help="Force training run")
    parser.add_argument("--enable", action="store_true", help="Enable trigger")
    parser.add_argument("--disable", action="store_true", help="Disable trigger")

    args = parser.parse_args()

    if args.status:
        print(json.dumps(get_training_status(), indent=2))
    elif args.force:
        print(json.dumps(force_training(), indent=2))
    elif args.enable:
        config = load_config()
        config["enabled"] = True
        save_config(config)
        print("Trigger enabled")
    elif args.disable:
        config = load_config()
        config["enabled"] = False
        save_config(config)
        print("Trigger disabled")
    else:
        print(json.dumps(check_and_trigger_training(), indent=2))
