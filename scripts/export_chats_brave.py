"""Chat export using Brave browser with saved credentials."""

from playwright.sync_api import sync_playwright
import time
import os

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

def main():
    print("=" * 60)
    print("CHAT EXPORT - BRAVE (Saved Credentials)")
    print("=" * 60)
    
    os.makedirs("data/chat-exports/deepseek", exist_ok=True)
    os.makedirs("data/chat-exports/chatgpt", exist_ok=True)
    
    with sync_playwright() as p:
        print("\nLaunching Brave browser...")
        browser = p.chromium.launch(
            executable_path=BRAVE_PATH,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ]
        )
        
        page = browser.new_page()
        
        print("\n[1] DEEPSEEK EXPORT")
        print("Opening chat.deepseek.com...")
        page.goto("https://chat.deepseek.com")
        time.sleep(5)
        
        page.screenshot(path="data/chat-exports/deepseek/status.png")
        
        print("\n" + "=" * 60)
        print("CHECK BROWSER WINDOW")
        print("=" * 60)
        print("If already logged in, chats should be visible.")
        print("If not, login with your saved credentials.")
        input("\nPress Enter when ready...")
        
        page.screenshot(path="data/chat-exports/deepseek/chats.png")
        print("Saved: data/chat-exports/deepseek/chats.png")
        
        print("\n[2] CHATGPT EXPORT")
        print("Opening chat.openai.com...")
        page.goto("https://chat.openai.com")
        time.sleep(5)
        
        page.screenshot(path="data/chat-exports/chatgpt/status.png")
        
        print("\n" + "=" * 60)
        print("CHECK BROWSER WINDOW")
        print("=" * 60)
        print("If already logged in, chats should be visible.")
        print("If not, login with your saved credentials.")
        input("\nPress Enter when ready...")
        
        page.screenshot(path="data/chat-exports/chatgpt/chats.png")
        print("Saved: data/chat-exports/chatgpt/chats.png")
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print("Screenshots saved to data/chat-exports/")

if __name__ == "__main__":
    main()
