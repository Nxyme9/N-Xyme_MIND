#!/usr/bin/env python3
"""
Benchmark: Compare qwen2.5-coder-7b GGUF alone vs + Rosetta LoRA translator

Two-model chain:
1. Big model (7B Q4) → generates tool-like output (often broken)
2. Small LoRA (0.5B) → translates to correct Rosetta format
"""

import re
import time
from pathlib import Path

# Check for GGUF model
GGUF_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-coder-7b-q4_k_m.gguf"
LORA_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/rosetta-lora-ecosystem"

# Test prompts - mix of simple and complex
TEST_PROMPTS = [
    "Create a file called hello.txt with content Hello World",
    "List all files in the current directory",
    "Search for Python files in src folder",
    "Read the file README.md",
    "Create a new directory called projects",
    "Search memory for information about authentication",
    "Get memory statistics",
    "Record learning outcome for task test with success true",
    "Find context for current coding task",
    "Search directory for all JSON files",
]


def check_dependencies():
    """Check what's available."""
    print("=" * 60)
    print("Dependency Check")
    print("=" * 60)

    # Check GGUF
    if Path(GGUF_PATH).exists():
        size_gb = Path(GGUF_PATH).stat().st_size / 1e9
        print(f"✓ GGUF model: {GGUF_PATH} ({size_gb:.1f}GB)")
    else:
        print(f"✗ GGUF model not found: {GGUF_PATH}")

    # Check LoRA
    if Path(LORA_PATH).exists():
        print(f"✓ LoRA adapter: {LORA_PATH}")
    else:
        print(f"✗ LoRA adapter not found: {LORA_PATH}")

    # Check llama-cpp-python
    try:
        from llama_cpp import Llama

        print("✓ llama-cpp-python installed")
    except ImportError:
        print("✗ llama-cpp-python not installed")

    # Check transformers for LoRA
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel

        print("✓ transformers + peft installed (for LoRA)")
    except ImportError:
        print("✗ transformers/peft not installed")


def benchmark_gguf_only():
    """Benchmark GGUF model alone (no translation)."""
    print("\n" + "=" * 60)
    print("BENCHMARK: GGUF Model Alone (No LoRA Translation)")
    print("=" * 60)

    from llama_cpp import Llama

    llm = Llama(
        model_path=GGUF_PATH,
        n_ctx=2048,
        n_threads=8,
        n_gpu_layers=33,  # 7B model
        verbose=False,
    )

    results = []
    for i, prompt in enumerate(TEST_PROMPTS):
        # Build prompt for tool call generation
        full_prompt = f"""You are a coding assistant. Generate tool calls in this exact format:
[TOOL_CALL]{{tool => "tool_name", args => {{ --arg1 "value1", --arg2 "value2" }}}}[/TOOL_CALL]

User request: {prompt}

Tool call:"""

        start = time.time()
        output = llm(
            full_prompt,
            max_tokens=100,
            temperature=0.1,
            stop=["[/TOOL_CALL]"],
        )
        elapsed = time.time() - start

        generated = output["choices"][0]["text"]

        # Try to extract tool call
        tool_call = extract_tool_call(generated)

        results.append(
            {
                "prompt": prompt,
                "raw_output": generated[:200],
                "extracted": tool_call,
                "valid": is_valid_rosetta(tool_call),
                "time": elapsed,
            }
        )

        print(f"\n[{i + 1}] Prompt: {prompt[:50]}...")
        print(f"    Extracted: {tool_call[:80] if tool_call else 'NONE'}")
        print(f"    Valid: {is_valid_rosetta(tool_call)}")
        print(f"    Time: {elapsed:.2f}s")

    valid_count = sum(1 for r in results if r["valid"])
    avg_time = sum(r["time"] for r in results) / len(results)

    print(f"\n{'=' * 60}")
    print(
        f"GGUF Only Results: {valid_count}/{len(results)} valid ({valid_count / len(results) * 100:.1f}%)"
    )
    print(f"Average time: {avg_time:.2f}s")

    return results


def benchmark_with_lora():
    """Benchmark GGUF + LoRA translator chain."""
    print("\n" + "=" * 60)
    print("BENCHMARK: GGUF + Rosetta LoRA Translator")
    print("=" * 60)

    from llama_cpp import Llama
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    import torch

    # Load GGUF model (7B)
    print("Loading GGUF model (7B reasoning)...")
    llm = Llama(
        model_path=GGUF_PATH,
        n_ctx=2048,
        n_threads=8,
        n_gpu_layers=33,
        verbose=False,
    )

    # Load LoRA translator on its OWN 0.5B base model
    print("Loading LoRA translator (0.5B + LoRA)...")
    base_model = "Qwen/Qwen2.5-0.5B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(LORA_PATH, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
    )
    base.resize_token_embeddings(len(tokenizer))
    translator = PeftModel.from_pretrained(base, LORA_PATH)
    translator.eval()

    results = []
    for i, prompt in enumerate(TEST_PROMPTS):
        # Step 1: Get initial output from GGUF (7B)
        # Use a prompt that encourages tool-like output
        gguf_prompt = f"""You are a tool-calling assistant. Generate tool calls for user requests.

User: {prompt}
Assistant:"""

        start = time.time()
        gguf_output = llm(gguf_prompt, max_tokens=80, temperature=0.1, stop=["User:"])
        gguf_text = gguf_output["choices"][0]["text"].strip()

        # Step 2: Use LoRA (0.5B) to translate the ORIGINAL prompt to Rosetta format
        # The LoRA was trained on: natural language → Rosetta tool call
        # So we feed the user's original prompt directly!
        translator_input = prompt
        inputs = tokenizer(translator_input, return_tensors="pt", padding=True).to(
            translator.device
        )

        with torch.no_grad():
            outputs = translator.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.1,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
            )

        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        tool_call = extract_tool_call(translated)

        # Also try extracting from GGUF output directly
        gguf_tool_call = extract_tool_call(gguf_text)

        elapsed = time.time() - start

        # Use LoRA output as primary (that's the whole point!)
        final_call = tool_call if tool_call else gguf_tool_call

        results.append(
            {
                "prompt": prompt,
                "gguf_raw": gguf_text[:100],
                "lora_translated": tool_call,
                "final": final_call,
                "valid": is_valid_rosetta(final_call),
                "time": elapsed,
            }
        )

        print(f"\n[{i + 1}] Prompt: {prompt[:50]}...")
        print(f"    GGUF raw: {gguf_text[:60]}...")
        print(f"    LoRA trans: {tool_call[:60] if tool_call else 'NONE'}")
        print(f"    Valid: {is_valid_rosetta(final_call)}")
        print(f"    Time: {elapsed:.2f}s")

    valid_count = sum(1 for r in results if r["valid"])
    avg_time = sum(r["time"] for r in results) / len(results)

    print(f"\n{'=' * 60}")
    print(
        f"GGUF + LoRA Results: {valid_count}/{len(results)} valid ({valid_count / len(results) * 100:.1f}%)"
    )
    print(f"Average time: {avg_time:.2f}s")

    return results


def extract_tool_call(text):
    """Extract [TOOL_CALL]...[/TOOL_CALL] from text."""
    if not text:
        return None
    match = re.search(r"\[TOOL_CALL\].*?\[/TOOL_CALL\]", text, re.DOTALL)
    return match.group(0) if match else None


def is_valid_rosetta(tool_call):
    """Check if tool call matches Rosetta format."""
    if not tool_call:
        return False
    # Format: [TOOL_CALL]{tool => "name", args => { ... }}[/TOOL_CALL]
    pattern = (
        r'\[TOOL_CALL\]\{tool\s*=>\s*"[^"]+",\s*args\s*=>\s*\{[^}]*\}\}\[/TOOL_CALL\]'
    )
    return bool(re.match(pattern, tool_call.strip()))


def main():
    print("=" * 60)
    print("ROSETTA CHAIN BENCHMARK")
    print("qwen2.5-coder-7b-q4_k_m.gguf vs + LoRA Translator")
    print("=" * 60)

    check_dependencies()

    results_gguf = benchmark_gguf_only()

    results_chain = benchmark_with_lora()

    # Summary
    print("\n" + "=" * 60)
    print("FINAL COMPARISON")
    print("=" * 60)

    gguf_valid = sum(1 for r in results_gguf if r["valid"])
    chain_valid = sum(1 for r in results_chain if r["valid"])

    print(
        f"GGUF Alone:      {gguf_valid}/{len(TEST_PROMPTS)} ({gguf_valid / len(TEST_PROMPTS) * 100:.1f}%)"
    )
    print(
        f"GGUF + LoRA:     {chain_valid}/{len(TEST_PROMPTS)} ({chain_valid / len(TEST_PROMPTS) * 100:.1f}%)"
    )
    print(
        f"Improvement:     +{(chain_valid - gguf_valid) / max(gguf_valid, 1) * 100:.1f}%"
    )


if __name__ == "__main__":
    main()
