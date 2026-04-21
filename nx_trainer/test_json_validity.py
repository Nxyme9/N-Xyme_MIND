#!/usr/bin/env python3
"""
JSON VALIDITY & SEMANTIC ACCURACY TEST
Tests that model produces valid JSON with correct tool INTENTS
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

TOOL_INTENT_MAP = {
    "read": ["read", "file", "contents", "display", "show"],
    "write": ["write", "create", "file", "save", "make"],
    "grep": ["grep", "search", "find", "match", "pattern"],
    "glob": ["glob", "find_files", "list_files", "*.py", "*.js"],
    "bash": ["bash", "command", "execute", "run", "shell"],
    "task": ["task", "delegate", "assign", "agent"],
    "skill": ["skill", "execute", "run_skill"],
    "lsp_diagnostics": ["diagnostics", "lint", "errors", "check"],
    "lsp_rename": ["rename", "refactor", "rename_symbol"],
    "lsp_goto_definition": ["goto", "definition", "jump", "navigate"],
    "github_create_issue": ["issue", "create_issue", "bug_report"],
    "github_list_issues": ["issues", "list", "open_issues"],
    "websearch": ["search", "web", "find_info"],
    "sqlite_query": ["sql", "query", "database"],
    "playwright_navigate": ["navigate", "goto", "open", "browser"],
    "notion_API-post-page": ["notion", "page", "create_page"],
    "nx_delegate": ["delegate", "route", "task"],
    "session_list": ["session", "list", "history"],
}

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
    ("nx_delegate", "delegate the refactoring task"),
    ("session_list", "what sessions do we have?"),
]

print("\n" + "="*60)
print("JSON VALIDITY & SEMANTIC INTENT TESTING")
print("="*60)

json_valid = 0
semantic_correct = 0
total = len(UNSEEN_TESTS)
failed_json = []
failed_semantic = []

for i, (expected_tool, prompt) in enumerate(UNSEEN_TESTS):
    full_prompt = f'''User: {prompt}

Generate a JSON tool call with "tool" and "args":'''
    
    messages = [{"role": "user", "content": full_prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=250, do_sample=False)
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    
    try:
        json_match = re.search(r'\{[^{}]*"tool"[^{}]*\}', response)
        if json_match:
            tool_call = json.loads(json_match.group())
            json_valid += 1
            
            tool_name = tool_call.get("tool", "").lower()
            intent_keywords = TOOL_INTENT_MAP.get(expected_tool, [expected_tool])
            
            if any(kw in tool_name for kw in intent_keywords):
                print(f"✓ [{i+1}/{total}] {expected_tool}: VALID JSON + CORRECT INTENT ({tool_name})")
                semantic_correct += 1
            else:
                print(f"~ [{i+1}/{total}] {expected_tool}: VALID JSON but intent mismatch ({tool_name})")
                failed_semantic.append((expected_tool, tool_name, response[:80]))
        else:
            print(f"✗ [{i+1}/{total}] {expected_tool}: NO VALID JSON")
            failed_json.append((expected_tool, response[:80]))
    except Exception as e:
        print(f"✗ [{i+1}/{total}] {expected_tool}: JSON PARSE ERROR ({e})")
        failed_json.append((expected_tool, response[:80]))

print("\n" + "="*60)
print(f"JSON VALIDITY: {json_valid}/{total} ({100*json_valid/total:.1f}%)")
print(f"SEMANTIC ACCURACY: {semantic_correct}/{total} ({100*semantic_correct/total:.1f}%)")
print("="*60)

if failed_json:
    print(f"\nJSON ERRORS ({len(failed_json)}):")
    for tool, resp in failed_json[:3]:
        print(f"  - {tool}: {resp}")
        
if failed_semantic:
    print(f"\nINTENT MISMATCHES ({len(failed_semantic)}):")
    for expected, got, _ in failed_semantic[:3]:
        print(f"  - Expected {expected}, got: {got}")

if json_valid == total and semantic_correct == total:
    print("\n🎉 PERFECT: 100% JSON VALID + 100% SEMANTIC ACCURACY!")