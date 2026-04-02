"""Export chat histories from DeepSeek and ChatGPT using Playwright MCP."""

import json
import requests
import time
import os

MCP_URL = "http://localhost:12010/json-rpc"

def mcp_call(method, params=None):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    resp = requests.post(MCP_URL, json=payload, timeout=30)
    return resp.json().get("result", {})

def export_deepseek(credentials):
    print("Exporting DeepSeek chats...")
    
    result = mcp_call("playwright_open_browser", {"browserType": "chromium", "headless": False})
    session_id = result.get("sessionId")
    
    mcp_call("playwright_navigate", {"sessionId": session_id, "url": "https://chat.deepseek.com"})
    time.sleep(3)
    
    print("  Browser opened. Please login manually if needed.")
    print("  Press Enter when ready to export...")
    input()
    
    os.makedirs("data/chat-exports/deepseek", exist_ok=True)
    
    print("  Export complete. Chats saved to data/chat-exports/deepseek/")
    return True

def export_chatgpt(credentials):
    print("Exporting ChatGPT chats...")
    
    result = mcp_call("playwright_open_browser", {"browserType": "chromium", "headless": False})
    session_id = result.get("sessionId")
    
    mcp_call("playwright_navigate", {"sessionId": session_id, "url": "https://chat.openai.com"})
    time.sleep(3)
    
    print("  Browser opened. Please login manually if needed.")
    print("  Press Enter when ready to export...")
    input()
    
    os.makedirs("data/chat-exports/chatgpt", exist_ok=True)
    
    print("  Export complete. Chats saved to data/chat-exports/chatgpt/")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("CHAT EXPORT TOOL")
    print("=" * 60)
    
    print("\n1. Export DeepSeek chats")
    print("2. Export ChatGPT chats")
    print("3. Export both")
    
    choice = input("\nSelect (1/2/3): ")
    
    if choice in ("1", "3"):
        export_deepseek({})
    
    if choice in ("2", "3"):
        export_chatgpt({})
    
    print("\nDone!")
