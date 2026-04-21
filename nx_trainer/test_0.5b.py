#!/usr/bin/env python3
"""
Test Rosetta 0.5B model accuracy
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-0.5b-instruct"
ADAPTER_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/outputs/rosetta_0.5b/final"

print("Loading 0.5B model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
)
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
model = model.eval()
print("Model loaded!")

print("\nLoading training data...")
tools_data = []
with open("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/data/v4_real.jsonl") as f:
    for line in f:
        d = json.loads(line)
        msg = d.get("messages", [])
        if len(msg) >= 2:
            user_content = msg[0]["content"]
            assistant_content = msg[1]["content"]
            
            resp_json = json.loads(assistant_content)
            tool_name = resp_json.get("tool", "")
            tools_data.append((tool_name, user_content))

print(f"Loaded {len(tools_data)} tools for testing")

print("\n" + "="*60)
print("TESTING ROSETTA 0.5B MODEL")
print("="*60)

correct = 0
failed = []
total = len(tools_data)

for i, (expected_tool, prompt) in enumerate(tools_data):
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200, do_sample=False)
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    
    if expected_tool in response and "tool" in response:
        print(f"✓ [{i+1}/{total}] {expected_tool}: MATCH")
        correct += 1
    else:
        print(f"✗ [{i+1}/{total}] Expected {expected_tool}, got: {response[:60]}...")
        failed.append((expected_tool, response[:100]))

print("\n" + "="*60)
print(f"RESULTS: {correct}/{total} correct ({100*correct/total:.1f}%)")
print("="*60)

if failed:
    print(f"\nFAILED TOOLS ({len(failed)}):")
    for tool, resp in failed:
        print(f"  - {tool}: {resp}")
else:
    print("\n🎉 100% ACCURACY ON 0.5B MODEL!")