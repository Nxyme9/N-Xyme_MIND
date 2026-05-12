# -*- coding: utf-8 -*-
"""
Adapter Registry - Version Control for LoRA Adapters
===================================================

Tracks, manages, and versions LoRA adapter checkpoints.

Usage:
    from nx_trainer.adapter_registry import Registry, AdapterRecord

    registry = Registry()
    adapter_id = registry.register("models/rosetta-lora/checkpoint-100", {
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
        "lora_rank": 16,
        "lora_alpha": 32,
    })
    record = registry.get(adapter_id)
    best = registry.get_best()
    all_adapters = registry.list_all()
    registry.rollback(adapter_id)
    better = registry.compare(adapter_id_a, adapter_id_b)
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("trainer.adapter_registry")

TRAINER_ROOT = Path(__file__).parent.parent
MODELS_DIR = TRAINER_ROOT / "models"
REGISTRY_FILE = MODELS_DIR / "adapter_registry.json"


# ============================================================================
# ADAPTER STATUS
# ============================================================================

ADAPTER_STATUS = [
    "training",  # Currently being trained
    "validating",  # Being validated/tested
    "deployed",  # Currently in production
    "archived",  # Old version, archived
]


# ============================================================================
# ADAPTER RECORD
# ============================================================================


@dataclass
class AdapterRecord:
    """
    Single adapter checkpoint record.

    Attributes:
        adapter_id: Unique identifier for this adapter
        checkpoint_path: Path to the adapter checkpoint
        target_modules: List of LoRA target modules
        lora_rank: LoRA rank (r)
        lora_alpha: LoRA alpha scaling
        training_config: Training hyperparameters used
        metrics: Performance metrics (accuracy, loss, etc.)
        status: Current status (training/validating/deployed/archived)
        parent_id: Parent adapter ID for versioning
    """

    adapter_id: str
    checkpoint_path: str
    target_modules: List[str]
    lora_rank: int
    lora_alpha: int
    training_config: Dict[str, Any]
    metrics: Dict[str, Any]
    status: str
    parent_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdapterRecord":
        """Create from dictionary."""
        return cls(**data)

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update metrics and set updated_at timestamp."""
        self.metrics = metrics
        self.updated_at = datetime.utcnow().isoformat()

    def update_status(self, status: str) -> None:
        """Update status with validation."""
        if status not in ADAPTER_STATUS:
            raise ValueError(f"Invalid status: {status}. Must be one of {ADAPTER_STATUS}")
        self.status = status
        self.updated_at = datetime.utcnow().isoformat()


# ============================================================================
# REGISTRY
# ============================================================================


class Registry:
    """
    LoRA adapter version control registry.

    Manages adapter lifecycle including registration, retrieval,
    comparison, and rollback.
    """

    def __init__(
        self,
        registry_file: Path = REGISTRY_FILE,
        models_dir: Path = MODELS_DIR,
    ):
        self.registry_file = registry_file
        self.models_dir = models_dir
        self.records: Dict[str, AdapterRecord] = {}
        self._load()

    def _generate_adapter_id(self) -> str:
        """Generate unique adapter ID."""
        return f"adapter_{uuid.uuid4().hex[:12]}"

    def _load(self) -> None:
        """Load registry from JSON file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)

                self.records = {
                    k: AdapterRecord.from_dict(v) for k, v in data.get("adapters", {}).items()
                }
                logger.info(f"Loaded {len(self.records)} adapter records from registry")
            except Exception as e:
                logger.warning(f"Failed to load registry: {e}. Starting fresh.")
                self.records = {}
        else:
            logger.info("No existing registry found. Starting fresh.")
            self.records = {}

    def _save(self) -> None:
        """Save registry to JSON file."""
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "adapters": {k: v.to_dict() for k, v in self.records.items()},
            "metadata": {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "total_adapters": len(self.records),
            },
        }

        with open(self.registry_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Registry saved to {self.registry_file}")

    def register(
        self,
        checkpoint_path: str,
        config: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> str:
        """
        Register a new adapter checkpoint.

        Args:
            checkpoint_path: Path to the adapter checkpoint
            config: Configuration including:
                - target_modules: List of LoRA target modules
                - lora_rank: LoRA rank
                - lora_alpha: LoRA alpha
                - training_config: Training hyperparameters
            parent_id: Optional parent adapter ID for versioning

        Returns:
            Generated adapter_id
        """
        adapter_id = self._generate_adapter_id()

        target_modules = config.get("target_modules", ["q_proj", "k_proj", "v_proj", "o_proj"])
        lora_rank = config.get("lora_rank", 16)
        lora_alpha = config.get("lora_alpha", 32)
        training_config = config.get("training_config", {})
        metrics = config.get("metrics", {})

        record = AdapterRecord(
            adapter_id=adapter_id,
            checkpoint_path=checkpoint_path,
            target_modules=target_modules,
            lora_rank=lora_rank,
            lora_alpha=lora_alpha,
            training_config=training_config,
            metrics=metrics,
            status="training",
            parent_id=parent_id,
        )

        self.records[adapter_id] = record
        self._save()

        logger.info(f"Registered adapter {adapter_id} from {checkpoint_path} (parent: {parent_id})")

        return adapter_id

    def get(self, adapter_id: str) -> Optional[AdapterRecord]:
        """
        Get adapter record by ID.

        Args:
            adapter_id: The adapter ID to retrieve

        Returns:
            AdapterRecord if found, None otherwise
        """
        record = self.records.get(adapter_id)

        if record is None:
            logger.warning(f"Adapter not found: {adapter_id}")

        return record

    def get_best(self) -> Optional[AdapterRecord]:
        """
        Get the best performing adapter based on metrics.

        Returns:
            AdapterRecord with highest accuracy, or None if no records
        """
        deployed = [r for r in self.records.values() if r.status == "deployed"]

        if not deployed:
            logger.info("No deployed adapters. Finding best by metrics.")
            deployed = list(self.records.values())

        if not deployed:
            logger.warning("No adapters in registry")
            return None

        best_record = None
        best_accuracy = -1

        for record in deployed:
            accuracy = record.metrics.get("accuracy", 0)
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                best_record = record

        if best_record:
            logger.info(f"Best adapter: {best_record.adapter_id} (accuracy: {best_accuracy:.1%})")
        else:
            logger.warning("No adapter records with metrics found")

        return best_record

    def list_all(self) -> List[AdapterRecord]:
        """
        List all adapter records.

        Returns:
            List of all AdapterRecord objects sorted by creation time
        """
        records = list(self.records.values())
        records.sort(key=lambda r: r.created_at, reverse=True)

        logger.debug(f"Listing {len(records)} adapters")
        return records

    def rollback(self, adapter_id: str) -> bool:
        """
        Rollback to parent adapter (mark parent as deployed).

        Args:
            adapter_id: The adapter to rollback from

        Returns:
            True if rollback successful, False otherwise
        """
        record = self.get(adapter_id)

        if record is None:
            return False

        record.update_status("archived")

        if record.parent_id:
            parent = self.get(record.parent_id)
            if parent:
                parent.update_status("deployed")
                logger.info(f"Rolled back to parent: {parent.adapter_id}")
                self._save()
                return True
            else:
                logger.warning(f"Parent adapter not found: {record.parent_id}")

        self._save()
        return False

    def compare(self, adapter_id_a: str, adapter_id_b: str) -> str:
        """
        Compare two adapters and return which is better.

        Args:
            adapter_id_a: First adapter ID
            adapter_id_b: Second adapter ID

        Returns:
            The adapter_id that is better, or "tie" if equal
        """
        record_a = self.get(adapter_id_a)
        record_b = self.get(adapter_id_b)

        if not record_a or not record_b:
            logger.error("One or both adapters not found")
            return ""

        accuracy_a = record_a.metrics.get("accuracy", 0)
        accuracy_b = record_b.metrics.get("accuracy", 0)

        if accuracy_a > accuracy_b:
            logger.info(f"Adapter {adapter_id_a} is better ({accuracy_a:.1%} vs {accuracy_b:.1%})")
            return adapter_id_a
        elif accuracy_b > accuracy_a:
            logger.info(f"Adapter {adapter_id_b} is better ({accuracy_b:.1%} vs {accuracy_a:.1%})")
            return adapter_id_b
        else:
            logger.info(f"Adapters are equal ({accuracy_a:.1%})")
            return "tie"

    def update_status(self, adapter_id: str, status: str) -> bool:
        """
        Update adapter status.

        Args:
            adapter_id: The adapter ID
            status: New status (training/validating/deployed/archived)

        Returns:
            True if update successful
        """
        record = self.get(adapter_id)

        if record is None:
            return False

        record.update_status(status)
        self._save()

        logger.info(f"Updated adapter {adapter_id} status to {status}")
        return True

    def update_metrics(self, adapter_id: str, metrics: Dict[str, Any]) -> bool:
        """
        Update adapter metrics.

        Args:
            adapter_id: The adapter ID
            metrics: New metrics dictionary

        Returns:
            True if update successful
        """
        record = self.get(adapter_id)

        if record is None:
            return False

        record.update_metrics(metrics)
        self._save()

        logger.info(f"Updated adapter {adapter_id} metrics")
        return True

    def export(self, output_file: Optional[Path] = None) -> Path:
        """
        Export registry to JSON file.

        Args:
            output_file: Optional custom output path

        Returns:
            Path to exported file
        """
        if output_file is None:
            output_file = self.registry_file.with_suffix(".json")

        data = {
            "adapters": {k: v.to_dict() for k, v in self.records.items()},
            "metadata": {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "total_adapters": len(self.records),
            },
        }

        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Registry exported to {output_file}")
        return output_file


# ============================================================================
# CLI
# ============================================================================


def main():
    """CLI for adapter registry."""
    import argparse

    parser = argparse.ArgumentParser(description="Adapter Registry")
    parser.add_argument("--list", action="store_true", help="List all adapters")
    parser.add_argument("--get", help="Get adapter by ID")
    parser.add_argument("--best", action="store_true", help="Show best adapter")
    parser.add_argument("--register", help="Register new adapter from path")
    parser.add_argument("--status", help="Update adapter status")
    parser.add_argument("--id", help="Adapter ID for status update")
    parser.add_argument("--rollback", help="Rollback adapter")
    parser.add_argument("--compare", nargs=2, help="Compare two adapters")
    parser.add_argument("--export", help="Export registry to file")

    args = parser.parse_args()

    registry = Registry()

    if args.list:
        adapters = registry.list_all()
        print(f"\nTotal adapters: {len(adapters)}")
        for a in adapters:
            print(
                f"\n{a.adapter_id}:"
                f"\n  Path: {a.checkpoint_path}"
                f"\n  Status: {a.status}"
                f"\n  Created: {a.created_at}"
                f"\n  Accuracy: {a.metrics.get('accuracy', 'N/A')}"
                f"\n  Parent: {a.parent_id or 'none'}"
            )

    elif args.get:
        record = registry.get(args.get)
        if record:
            print(json.dumps(record.to_dict(), indent=2))
        else:
            print(f"Adapter not found: {args.get}")

    elif args.best:
        best = registry.get_best()
        if best:
            print(f"Best: {best.adapter_id}")
            print(json.dumps(best.to_dict(), indent=2))
        else:
            print("No best adapter found")

    elif args.register:
        config = {
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
            "lora_rank": 16,
            "lora_alpha": 32,
            "training_config": {"epochs": 3},
            "metrics": {"accuracy": 0.85},
        }
        adapter_id = registry.register(args.register, config)
        print(f"Registered: {adapter_id}")

    elif args.status and args.id:
        success = registry.update_status(args.id, args.status)
        if success:
            print(f"Updated status to {args.status}")
        else:
            print(f"Failed: {args.id}")

    elif args.rollback:
        success = registry.rollback(args.rollback)
        if success:
            print("Rolled back successfully")
        else:
            print("Rollback failed")

    elif args.compare:
        winner = registry.compare(args.compare[0], args.compare[1])
        print(f"Better adapter: {winner}")

    elif args.export:
        output = registry.export(args.export)
        print(f"Exported to: {output}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
