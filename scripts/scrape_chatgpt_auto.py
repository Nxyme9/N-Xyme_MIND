"""Scrape ChatGPT - automatic, no input required."""

from playwright.sync_api import sync_playwright
import time
import os
import json

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"

def main():
    print("=" * 60)
    print("CHATGPT SCRAPER - AUTOMATIC")
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
        time.sleep(8)
        
        print("\nWaiting for login (60 seconds)...")
        print("If not logged in, login now with saved credentials.")
        time.sleep(60)
        
        print("\nScraping chat list...")
        
        chats = []
        last_count = 0
        
        for scroll in range(100):
            chat_elements = page.query_selector_all('a[href*="/c/"]')
            current_count = len(chat_elements)
            
            if current_count == last_count and scroll > 10:
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
            
            if scroll % 10 == 0:
                print(f"  Found {len(chats)} chats...")
            
            page.mouse.wheel(0, 2000)
            time.sleep(0.3)
        
        print(f"\nTotal chats found: {len(chats)}")
        
        with open("data/chat-exports/chatgpt/chat_list.json", "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2, ensure_ascii=False)
        
        print("\nCapturing conversations (first 100)...")
        conversations = []
        
        for i, chat in enumerate(chats[:100]):
            try:
                if i % 10 == 0:
                    print(f"  [{i+1}/100] {chat['title'][:50]}...")
                
                page.goto(f"https://chat.openai.com{chat['href']}")
                time.sleep(2)
                
                messages = page.query_selector_all('[data-message-author-role]')
                conv_text = f"CHAT: {chat['title']}\n\n"
                
                for msg in messages:
                    try:
                        role = msg.get_attribute('data-message-author-role')
                        content = msg.inner_text()
                        conv_text += f"{role}: {content[:2000]}\n\n"
                    except:
                        pass
                
                conversations.append({
                    'title': chat['title'],
                    'text': conv_text
                })
                
            except Exception as e:
                pass
        
        print(f"\nCaptured {len(conversations)} conversations")
        
        with open("data/chat-exports/chatgpt/conversations.json", "w", encoding="utf-8") as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("SCRAPING COMPLETE")
    print("=" * 60)
    print(f"Saved {len(conversations)} conversations")

if __name__ == "__main__":
    main()
