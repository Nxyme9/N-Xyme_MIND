#!/usr/bin/env python3
"""
ProtonVPN WireGuard Config Downloader - Fully Automated.
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/vpn/providers/protonvpn/configs")
PROTON_URL = "https://account.protonvpn.com/downloads"


async def download_configs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("ProtonVPN Config Downloader - Fully Automated")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"\nNavigating to {PROTON_URL}...")
        await page.goto(PROTON_URL, timeout=30000)

        # Wait for content to load
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(3)

        print("\nWaiting for page to fully load...")
        await page.wait_for_load_state("networkidle", timeout=30000)

        # Get page state
        url = page.url
        title = await page.title()
        print(f"Current URL: {url}")
        print(f"Page title: {title}")

        # Check if logged in by looking for account elements
        page_html = await page.content()

        if "login" in page_html.lower() and "sign in" in page_html.lower():
            print("\n⚠️ NOT LOGGED IN!")
            print("Please login in the browser, then come back here.")
            print("Press ENTER after you've logged in...")
            input()

        # Now try to find WireGuard download section
        print("\nLooking for WireGuard download section...")

        # Try different selectors
        selectors = [
            "text=WireGuard",
            "text=wireguard",
            'a[href*="wireguard"]',
            'button:has-text("Download")',
            '[class*="wireguard"]',
        ]

        found = False
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    print(f"✓ Found: {sel}")
                    found = True
            except:
                pass

        # Get ARIA snapshot for better understanding
        print("\nGetting page snapshot...")
        try:
            snapshot = await page.accessibility.snapshot()
            print(f"Page has {len(str(snapshot))} chars of accessibility data")
        except:
            pass

        # Screenshot
        await page.screenshot(path="/tmp/proton_page.png")
        print("Screenshot: /tmp/proton_page.png")

        print("\n" + "=" * 60)
        print("AUTOMATION COMPLETE - Manual steps needed:")
        print("=" * 60)
        print("The browser is open. Please:")
        print("1. Login if not logged in")
        print("2. Find 'WireGuard' download section")
        print("3. Click 'Download' button")
        print("4. Wait for download to complete")
        print("5. Close the browser when done")
        print("\nI'll detect the files automatically...")

        # Create a task to wait for close
        close_task = asyncio.create_task(context.wait_for_event("close"))

        # Also wait a bit for download
        await asyncio.sleep(5)

        # Check if closed
        if close_task.done():
            print("Browser closed")
        else:
            print("\nWaiting for you to complete download...")
            print(
                "The browser is open. Click 'Download', wait for file, then close browser."
            )

            # Wait for browser close with timeout
            try:
                await asyncio.wait_for(close_task, timeout=180)
            except asyncio.TimeoutError:
                print("Timeout - checking for files anyway...")

        # Look for downloaded files

        # Look for downloaded files
        downloads = Path.home() / "Downloads"
        patterns = ["*.conf", "*proton*.conf", "*wg*.conf", "*wireguard*.conf"]

        conf_files = []
        for pattern in patterns:
            conf_files.extend(downloads.glob(pattern))

        # Also check recent files
        import os

        now = os.path.getmtime(str(downloads)) if downloads.exists() else 0

        if conf_files:
            print(f"\n✓ Found {len(conf_files)} conf files:")
            for f in conf_files:
                print(f"  - {f.name}")
                dest = OUTPUT_DIR / f.name
                import shutil

                shutil.copy2(f, dest)
                print(f"    → Copied to {dest}")
        else:
            print("\n⚠️ No conf files found")
            print(f"Please manually save to: {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(download_configs())
