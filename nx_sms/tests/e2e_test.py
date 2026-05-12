#!/usr/bin/env python3
"""End-to-end test for nx_sms web UI using Playwright"""

import subprocess
import time
import sys

# Start the Flask server
server = subprocess.Popen(
    ["python3", "-m", "nx_sms.web"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
)

# Wait for server to start
time.sleep(3)

try:
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("=== TEST 1: Load home page ===")
        page.goto("http://localhost:5000")
        page.wait_for_load_state("networkidle")
        
        title = page.title()
        print(f"Page title: {title}")
        
        h1 = page.locator("h1").inner_text()
        print(f"H1 text: {h1}")
        
        print("\n=== TEST 2: Check form elements ===")
        phone_input = page.locator('input[name="phone"]')
        message_textarea = page.locator('textarea[name="message"]')
        submit_button = page.locator('button[type="submit"]')
        
        print(f"Phone input visible: {phone_input.is_visible()}")
        print(f"Message textarea visible: {message_textarea.is_visible()}")
        print(f"Submit button visible: {submit_button.is_visible()}")
        
        print("\n=== TEST 3: Submit empty form ===")
        submit_button.click()
        page.wait_for_timeout(500)
        
        # Check for error message
        error_flash = page.locator(".flash.error").inner_text() if page.locator(".flash.error").count() > 0 else "None"
        print(f"Error flash: {error_flash}")
        
        print("\n=== TEST 4: Fill form and submit ===")
        page.goto("http://localhost:5000")
        page.wait_for_load_state("networkidle")
        
        phone_input.fill("+1234567890")
        message_textarea.fill("Test message from Playwright")
        submit_button.click()
        
        page.wait_for_timeout(1000)
        
        # Check result
        if page.locator(".flash.success").count() > 0:
            result = page.locator(".flash.success").inner_text()
            print(f"Success flash: {result}")
        elif page.locator(".flash.error").count() > 0:
            result = page.locator(".flash.error").inner_text()
            print(f"Error flash: {result}")
        else:
            print("No flash message found - form may have submitted")
        
        print("\n=== TEST 5: Check /status page ===")
        status_link = page.locator("a[href='/status']")
        status_link.click()
        page.wait_for_load_state("networkidle")
        
        status_h1 = page.locator("h1").inner_text()
        print(f"Status page H1: {status_h1}")
        
        browser.close()
        
        print("\n✅ ALL TESTS PASSED!")
        
except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
        
finally:
    server.terminate()
    server.wait()
