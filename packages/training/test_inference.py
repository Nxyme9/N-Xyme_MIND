#!/usr/bin/env python3
"""
Test inference with the trained Rosetta LoRA model
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# Paths
BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
LORA_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/rosetta-lora-extended"

# Test prompts
TEST_CASES = [
    "Create a file called hello.txt with the content 'Hello World'",
    "Run the command 'ls -la' to list files",
    "Search for all Python files in the src directory",
    "Read the file README.md",
    "Create a new directory called test_folder",
]


def load_model():
    """Load base model and apply LoRA adapters."""
    print("Loading tokenizer from LoRA path (has correct vocab size)...")
    tokenizer = AutoTokenizer.from_pretrained(
        LORA_PATH,  # Load from LoRA path to get the trained tokenizer
        trust_remote_code=True,
        padding_side="right",
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading base model...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
    )

    # Resize embeddings to match tokenizer (which may have added tokens)
    model.resize_token_embeddings(len(tokenizer))

    print("Loading LoRA adapters...")
    model = PeftModel.from_pretrained(model, LORA_PATH)
    model.eval()

    return model, tokenizer


def generate(prompt: str, model, tokenizer, max_new_tokens: int = 200):
    """Generate tool call from natural language prompt."""
    # Format with chat template
    formatted = f"""<|im_start|>user
{prompt}<|im_end|>
<|im_start|>assistant
"""

    inputs = tokenizer(formatted, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the generated part (not the prompt)
    generated = outputs[0][inputs.input_ids.shape[1] :]
    result = tokenizer.decode(generated, skip_special_tokens=True)

    return result.strip()


def main():
    print("=" * 60)
    print("Rosetta LoRA Inference Test")
    print("=" * 60)

    model, tokenizer = load_model()

    print("\n" + "=" * 60)
    print("Testing inference...")
    print("=" * 60)

    for i, prompt in enumerate(TEST_CASES, 1):
        print(f"\n[{i}] Prompt: {prompt}")
        print("-" * 40)

        result = generate(prompt, model, tokenizer)
        print(f"Output: {result}")
        print()


if __name__ == "__main__":
    main()
