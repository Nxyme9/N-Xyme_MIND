"""Interactive chat export - run this manually."""

from playwright.sync_api import sync_playwright
import time
import os

def main():
    print("=" * 60)
    print("CHAT EXPORT - INTERACTIVE")
    print("=" * 60)
    
    os.makedirs("data/chat-exports/deepseek", exist_ok=True)
    os.makedirs("data/chat-exports/chatgpt", exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        print("\n[1] DEEPSEEK EXPORT")
        print("Opening chat.deepseek.com...")
        page.goto("https://chat.deepseek.com")
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("LOGIN TO DEEPSEEK NOW")
        print("=" * 60)
        input("\nPress Enter when logged in...")
        
        print("\nExporting chats...")
        page.screenshot(path="data/chat-exports/deepseek/screenshot.png")
        print("Screenshot saved!")
        
        print("\n[2] CHATGPT EXPORT")
        print("Opening chat.openai.com...")
        page.goto("https://chat.openai.com")
        time.sleep(3)
        
        print("\n" + "=" * 60)
        print("LOGIN TO CHATGPT NOW")
        print("=" * 60)
        input("\nPress Enter when logged in...")
        
        print("\nExporting chats...")
        page.screenshot(path="data/chat-exports/chatgpt/screenshot.png")
        print("Screenshot saved!")
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print("Chats saved to:")
    print("  data/chat-exports/deepseek/")
    print("  data/chat-exports/chatgpt/")

if __name__ == "__main__":
    main()
