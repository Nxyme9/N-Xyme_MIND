#!/usr/bin/env python3
"""
EXTENSIVE TESTING - Unseen prompts, edge cases, robustness
"""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import json
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
    # Completely new phrasing for existing tools
    ("read", "I need to see what's inside config.yaml"),
    ("read", "what's in the README file?"),
    ("write", "please make a new file named test.py with some test code"),
    ("grep", "search through all files for the word PASSWORD"),
    ("glob", "show me every javascript file"),
    ("bash", "run ls -la to see file details"),
    ("task", "ask hephaestus to implement the login feature"),
    ("skill", "use the refactor skill please"),
    ("lsp_diagnostics", "check for errors in auth.ts"),
    ("github_list_issues", "what bugs are open?"),
    ("websearch", "find information about rust async"),
    ("sqlite_query", "show me all users from the database"),
    ("playwright_navigate", "go to https://github.com"),
    ("notion_API-post-page", "add a new note to notion"),
    ("nx_delegate_nx_delegate", "assign the refactoring task"),
    ("session_list", "what sessions do we have?"),
    ("ast_grep_search", "find all uses of useState"),
    
    # Edge cases
    ("read", "READ the file called secrets.txt"),
    ("write", "WRITE this content: hello world to /tmp/test.txt"),
    ("grep", "GREP for 'TODO' in src/"),
    ("glob", "GLOB *.md files"),
    ("bash", "BASH: echo 'hello'"),
    ("task", "TASK: delegate to oracle for architecture review"),
    ("skill", "SKILL: execute bmad-quick-dev"),
    ("lsp_diagnostics", "LSP: check errors"),
    
    # Typos and variations
    ("read", "reed the file"),  # typo
    ("write", "wite a file"),   # typo
    ("grep", "gerp pattern"),   # typo
    
    # Longer more complex prompts
    ("read", "Please open and display the contents of the configuration file located at /etc/app/config.json"),
    ("write", "Create a new Python file at /home/user/project/main.py that contains a simple Flask application with routes for home and about pages"),
    ("grep", "Search recursively through the entire src directory and all subdirectories for any occurrences of the string 'async def' and display the matching line numbers"),
    ("task", "Delegate the task of refactoring the authentication module to use JWT tokens instead of sessions to the hephaestus agent"),
    ("github_create_issue", "Create a GitHub issue in the facebook/react repository reporting that useEffect cleanup is not working properly in version 19"),
    ("sqlite_query", "Execute a SQL query to find all users who have logged in within the last 24 hours and order them by login time descending"),
    ("websearch", "Search the web for the latest best practices for implementing authentication in Next.js 14 applications with server components"),
    ("notion_API-post-page", "Create a new page in my Notion workspace under the 'Projects' database with the title 'Q4 Development Plan'"),
    ("nx_delegate_nx_delegate", "I need to delegate the complex task of implementing a new feature to the appropriate agent"),
    ("playwright_navigate", "Open the browser and navigate to the login page at https://app.example.com/login"),
    ("session_search", "Search through all past sessions to find any previous work related to OAuth implementation"),
]

print("\n" + "="*60)
print("EXTENSIVE TESTING - UNSEEN PROMPTS & EDGE CASES")
print("="*60)

correct = 0
failed = []
total = len(UNSEEN_TESTS)

for i, (expected_tool, prompt) in enumerate(UNSEEN_TESTS):
    full_prompt = f'''You are interacting with OpenCode. Generate a tool call.

The user said: "{prompt}"

Generate the tool call in JSON format with "tool" and "args":'''
    
    messages = [{"role": "user", "content": full_prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=250, do_sample=False)
    
    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    
    if expected_tool.lower() in response.lower() and "tool" in response:
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
else:
    print("\n🎉 ALL TESTS PASSED - MODEL IS ROBUST!")