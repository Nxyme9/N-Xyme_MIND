"""Scrape ChatGPT conversations using Playwright."""

from playwright.sync_api import sync_playwright
import time
import os
import json

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

def main():
    print("=" * 60)
    print("CHATGPT SCRAPER - BROWSER AUTOMATION")
    print("=" * 60)
    
    os.makedirs("data/chat-exports/chatgpt", exist_ok=True)
    
    with sync_playwright() as p:
        print("\nLaunching Brave...")
        browser = p.chromium.launch(
            executable_path=BRAVE_PATH,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = browser.new_page()
        
        print("\nOpening ChatGPT...")
        page.goto("https://chat.openai.com")
        time.sleep(5)
        
        print("\n" + "=" * 60)
        print("LOGIN TO CHATGPT NOW")
        print("=" * 60)
        print("If not logged in, login with your saved credentials.")
        input("\nPress Enter when logged in and chats are visible...")
        
        print("\nScraping chat list...")
        
        chats = []
        last_count = 0
        
        for scroll in range(50):
            chat_elements = page.query_selector_all('a[href*="/c/"]')
            current_count = len(chat_elements)
            
            if current_count == last_count and scroll > 5:
                break
            
            last_count = current_count
            
            for el in chat_elements:
                try:
                    title = el.inner_text()
                    href = el.get_attribute('href')
                    if title and href and {'title': title, 'href': href} not in chats:
                        chats.append({'title': title, 'href': href})
                except:
                    pass
            
            print(f"  Found {len(chats)} chats...")
            
            page.mouse.wheel(0, 1000)
            time.sleep(0.5)
        
        print(f"\nTotal chats found: {len(chats)}")
        
        print("\nSaving chat list...")
        with open("data/chat-exports/chatgpt/chat_list.json", "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)
        
        print("\nCapturing conversations...")
        conversations = []
        
        for i, chat in enumerate(chats[:20]):
            try:
                print(f"  [{i+1}/{min(20, len(chats))}] {chat['title'][:50]}...")
                
                page.goto(f"https://chat.openai.com{chat['href']}")
                time.sleep(2)
                
                messages = page.query_selector_all('[data-message-author-role]')
                conv_text = f"CHAT: {chat['title']}\n\n"
                
                for msg in messages:
                    try:
                        role = msg.get_attribute('data-message-author-role')
                        content = msg.inner_text()
                        conv_text += f"{role}: {content[:1000]}\n\n"
                    except:
                        pass
                
                conversations.append({
                    'title': chat['title'],
                    'text': conv_text
                })
                
            except Exception as e:
                print(f"    Error: {e}")
        
        print(f"\nCaptured {len(conversations)} conversations")
        
        print("\nSaving...")
        with open("data/chat-exports/chatgpt/conversations.json", "w", encoding="utf-8") as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Saved {len(conversations)} conversations to data/chat-exports/chatgpt/")

if __name__ == "__main__":
    main()
