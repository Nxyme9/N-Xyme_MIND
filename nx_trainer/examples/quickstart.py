"""Quickstart example for Rosetta Stone Trainer."""

from pathlib import Path

from nx_trainer.data_generator import DataGenerator
from nx_trainer.trainer import Trainer
from nx_trainer.config import LoRAConfig, TrainingConfig
from nx_trainer.evaluator import Evaluator


def main():
    """Run a quickstart demonstration."""
    print("=" * 50)
    print("Rosetta Stone Trainer - Quickstart")
    print("=" * 50)
    print()

    # Step 1: Generate training data
    print("Step 1: Generating training data...")
    generator = DataGenerator()
    data_path = Path("quickstart_data.jsonl")
    training_data = generator.generate(
        num_variations=5,  # Just 5 for quick demo
        output_path=data_path,
    )
    print(f"  Generated {len(training_data)} training pairs")
    print(f"  Saved to: {data_path}")
    print()

    # Step 2: Prepare for fine-tuning
    print("Step 2: Preparing for fine-tuning...")
    formatted_path = Path("quickstart_formatted.json")
    formatted = generator.prepare_for_fine_tuning(data_path, formatted_path)
    print(f"  Prepared {len(formatted)} examples")
    print(f"  Saved to: {formatted_path}")
    print()

    # Step 3: Check what's available
    print("Step 3: Checking available training methods...")
    unsloth_available = Trainer.check_unsloth_available()
    ollama_available = Trainer.check_ollama_available()

    print(f"  Unsloth available: {unsloth_available}")
    print(f"  Ollama available: {ollama_available}")
    print()

    # Step 4: Show how to train
    print("Step 4: Training command examples...")
    print()
    print("  # With Unsloth (recommended - 2x faster):")
    print(f"  rosetta-train train --method unsloth --data {data_path} --epochs 3")
    print()
    print("  # With Ollama:")
    print(f"  rosetta-train train --method ollama --data {data_path}")
    print()
    print("  # Custom LoRA settings:")
    print("  rosetta-train train --method unsloth --data data.jsonl \\")
    print("    --lora-r 8 --lora-alpha 16 --learning-rate 1e-4")
    print()

    # Step 5: Show test command
    print("Step 5: Testing command...")
    print("  rosetta-train test --ollama-model rosetta")
    print()

    # Step 6: Show evaluator usage
    print("Step 6: Using the Evaluator...")
    evaluator = Evaluator()

    # Example output
    example_output = '[TOOL_CALL]{tool => "memory_search", args => { --query "security" }}[/TOOL_CALL]'
    result = evaluator.evaluate_output(example_output, "memory_search")

    print(f"  Input: 'search memory for security'")
    print(f"  Parsed tool: {result['parsed']['tool']}")
    print(f"  Parsed args: {result['parsed']['args']}")
    print(f"  Correct: {result['correct']}")
    print()

    print("=" * 50)
    print("Quickstart complete! Ready to train.")
    print("=" * 50)


if __name__ == "__main__":
    main()
