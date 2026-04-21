#!/usr/bin/env python3
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

NATURAL_LANGUAGE_TESTS = [
    ("read", "Show me the contents of main.py"),
    ("write", "Create a new file called app.py with hello world"),
    ("grep", "Find all lines matching 'def.*auth' in src folder"),
    ("glob", "Find all Python files in the project"),
    ("bash", "List files in the home directory"),
    ("task", "Delegate to hephaestus to fix the auth bug"),
    ("skill", "Run the bmad-quick-dev skill"),
    ("lsp_diagnostics", "Get diagnostics for main.py"),
    ("lsp_rename", "Rename handleLogin function to authenticateUser"),
    ("lsp_goto_definition", "Go to definition of auth function"),
    ("github_create_issue", "Create a GitHub issue about the bug"),
    ("github_list_issues", "List open issues in vscode repo"),
    ("websearch", "Search the web for python async best practices"),
    ("fetch_fetch_readable", "Fetch readable content from python docs"),
    ("context7_query_docs", "Query supabase docs for auth setup"),
    ("sqlite_query", "Run SQL query to get all sessions"),
    ("playwright_navigate", "Navigate browser to example.com"),
    ("playwright_click", "Click the login button"),
    ("playwright_fill", "Fill email field with user@test.com"),
    ("telegram_send_message", "Send a message to telegram"),
    ("notion_API-post-page", "Create a new page in notion"),
    ("nx_delegate_nx_delegate", "Delegate the task of fixing authentication"),
    ("nx_brain_mind_get_mind_state", "Get current mind state"),
    ("nx_brain_memory_memory_write", "Write to memory"),
    ("session_list", "List all sessions"),
    ("session_search", "Search sessions for authentication"),
    ("ast_grep_search", "Search code with ast-grep for console.log"),
    ("look_at", "Look at architecture diagram"),
    ("github_create_pull_request", "Create a PR"),
    ("websearch_web_search_exa", "Web search for React 19 features"),
]

print("\n" + "="*60)
print("TESTING NATURAL LANGUAGE PROMPTS")
print("="*60)

correct = 0
failed = []
total = len(NATURAL_LANGUAGE_TESTS)

for i, (expected_tool, prompt) in enumerate(NATURAL_LANGUAGE_TESTS):
    full_prompt = f'''You are interacting with OpenCode. Available tools:

- tool: {expected_tool}
- args: {{}}

The user said: "{prompt}"

Generate the tool call in JSON format:'''
    
    messages = [{"role": "user", "content": full_prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    
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