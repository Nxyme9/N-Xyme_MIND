"""
Curriculum Learning Phases for RosEnna Trainer.
Defines 4-phase training curriculum with progressive difficulty.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class PhaseConfig:
    """Single curriculum phase configuration."""
    name: str
    epochs: int
    negatives_per_anchor: int
    temperature: float
    hard_negatives_only: bool
    description: str


# Curriculum phases - progressive difficulty training
PHASES: List[PhaseConfig] = [
    PhaseConfig(
        name="warmup",
        epochs=2,
        negatives_per_anchor=1,
        temperature=0.1,
        hard_negatives_only=False,
        description="Easy pairs, 1 random negative"
    ),
    PhaseConfig(
        name="medium",
        epochs=3,
        negatives_per_anchor=3,
        temperature=0.05,
        hard_negatives_only=False,
        description="All data, 3 random negatives"
    ),
    PhaseConfig(
        name="hard",
        epochs=3,
        negatives_per_anchor=3,
        temperature=0.05,
        hard_negatives_only=True,
        description="3 hard negatives + in-batch"
    ),
    PhaseConfig(
        name="sharpening",
        epochs=2,
        negatives_per_anchor=5,
        temperature=0.03,
        hard_negatives_only=True,
        description="5 hard negatives, sharp temp"
    ),
]


def get_phase(epoch: int) -> PhaseConfig:
    """
    Return which phase we're in based on current epoch.

    Args:
        epoch: Current epoch number (0-indexed)

    Returns:
        PhaseConfig for the current phase
    """
    cumulative = 0
    for phase in PHASES:
        cumulative += phase.epochs
        if epoch < cumulative:
            return phase
    # Fallback to last phase if beyond total
    return PHASES[-1]


def total_epochs() -> int:
    """
    Sum of all phase epochs.

    Returns:
        Total number of training epochs
    """
    return sum(p.epochs for p in PHASES)


def get_phase_for_epoch(epoch: int) -> tuple:
    """
    Get phase name and description for the given epoch.

    Args:
        epoch: Current epoch number (0-indexed)

    Returns:
        Tuple of (phase_name, description)
    """
    phase = get_phase(epoch)
    return phase.name, phase.description


def get_curriculum_summary() -> dict:
    """
    Get a summary of the curriculum configuration.

    Returns:
        Dictionary with curriculum info
    """
    return {
        "total_epochs": total_epochs(),
        "phases": [
            {
                "name": p.name,
                "epochs": p.epochs,
                "negatives": p.negatives_per_anchor,
                "temperature": p.temperature,
                "hard_negatives": p.hard_negatives_only,
                "description": p.description,
            }
            for p in PHASES
        ]
    }


# Compatibility with config.py's CurriculumConfig
def to_config_phases():
    """Convert PHASES to config.py PhaseConfig format."""
    from config import PhaseConfig as ConfigPhaseConfig

    return [
        ConfigPhaseConfig(
            name=p.name,
            epochs=p.epochs,
            num_negatives=p.negatives_per_anchor,
            temperature=p.temperature,
            hard_negatives=p.hard_negatives_only,
            use_in_batch=(p.negatives_per_anchor > 1),
        )
        for p in PHASES
    ]