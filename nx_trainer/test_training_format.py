#!/usr/bin/env python3
"""
TRAINING FORMAT TEST - Exact format from v4_real.jsonl training data
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import json
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

BASE_MODEL = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-1.5b-instruct"
ADAPTER_PATH = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/nx_trainer/outputs/rosetta_1.5b/final"

print("Loading model...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
)
model = PeftModel.from_pretrained(base_model, ADAPTER_PATH)
model = model.eval()
print("Model loaded!")

UNSEEN_TESTS = [
    ("read", "I need to see what's inside config.yaml"),
    ("read", "what's in the README file?"),
    ("write", "please make a new file named test.py with some test code"),
    ("grep", "search through all files for the word PASSWORD"),
    ("glob", "show me every javascript file"),
    ("bash", "run ls -la to see file details"),
    ("task", "ask hephaestus to fix the login bug"),
    ("skill", "use the refactor skill please"),
    ("lsp_diagnostics", "check for errors in auth.ts"),
    ("github_list_issues", "what bugs are open?"),
    ("websearch", "find information about rust async"),
    ("sqlite_query", "show me all users from the database"),
    ("playwright_navigate", "go to https://github.com"),
    ("notion_API-post-page", "add a new note to notion"),
    ("nx_delegate_nx_delegate", "delegate the refactoring task"),
    ("session_list", "what sessions do we have?"),
    ("ast_grep_search", "find code with ast-grep for useState"),
    ("github_create_issue", "create issue about the bug"),
    ("webfetch", "fetch the python docs"),
    ("context7_query_docs", "query docs for react hooks"),
]

print("\n" + "="*60)
print("TRAINING FORMAT TEST - EXACT PROMPT STYLE")
print("="*60)

correct = 0
total = len(UNSEEN_TESTS)
failed = []

for i, (expected_tool, prompt) in enumerate(UNSEEN_TESTS):
    full_prompt = f'''<|im_start|>system
You are a tool calling assistant. Given a user request, output a JSON tool call.
Available tools:
- tool: read
- args: {{"path": "str"}}
- tool: write
- args: {{"path": "str", "content": "str"}}
- tool: grep
- args: {{"path": "str", "pattern": "str"}}
- tool: glob
- args: {{"pattern": "str"}}
- tool: bash
- args: {{"command": "str"}}
- tool: task
- args: {{"description": "str"}}
- tool: skill
- args: {{"name": "str"}}
- tool: lsp_diagnostics
- args: {{"filePath": "str"}}
- tool: github_list_issues
- args: {{"owner": "str", "repo": "str"}}
- tool: websearch
- args: {{"query": "str"}}
- tool: sqlite_query
- args: {{"sql": "str"}}
- tool: playwright_navigate
- args: {{"url": "str"}}
- tool: notion_API-post-page
- args: {{"parent": "dict", "properties": "dict"}}
- tool: nx_delegate_nx_delegate
- args: {{"task_description": "str"}}
- tool: session_list
- args: {{}}
- tool: ast_grep_search
- args: {{"pattern": "str", "lang": "str"}}
- tool: github_create_issue
- args: {{"owner": "str", "repo": "str", "title": "str"}}
- tool: webfetch
- args: {{"url": "str"}}
- tool: context7_query_docs
- args: {{"libraryId": "str", "query": "str"}}

The user request: "{prompt}"

Output only the JSON tool call, nothing else:<|im_end|>
<|im_start|>assistant
'''

    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=200, do_sample=False)
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    
    if expected_tool in response and "tool" in response:
        print(f"✓ [{i+1}/{total}] {expected_tool}: MATCH")
        correct += 1
    else:
        print(f"✗ [{i+1}/{total}] Expected {expected_tool}")
        print(f"   Got: {response[:80]}...")
        failed.append((expected_tool, response[:100]))

print("\n" + "="*60)
print(f"RESULTS: {correct}/{total} correct ({100*correct/total:.1f}%)")
print("="*60)

if failed:
    print(f"\nFAILED ({len(failed)}):")
    for tool, resp in failed:
        print(f"  - {tool}: {resp}")