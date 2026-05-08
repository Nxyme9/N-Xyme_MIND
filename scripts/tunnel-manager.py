#!/usr/bin/env python3
"""Tunnel Manager - Auto-updates Telegram bot when tunnel URL changes"""

import subprocess
import time
import json
import re
import sys
import os
from pathlib import Path

TOKEN = "8397949824:AAEkYzjVwIVUQAfTiFL2UcsGVC4Dgr7lXDw"
STATE_FILE = Path.home() / ".config" / "tunnel-state.json"
LOG_FILE = Path.home() / "N-Xyme_CODE" / "N-Xyme_MIND" / "tunnel-manager.log"
CLOUDFLARED_PATH = "/tmp/cloudflared"


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def get_stored_url():
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f).get("tunnel_url")
        except:
            pass
    return None


def save_url(url):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump({"tunnel_url": url, "updated": time.time()}, f)
    log(f"Saved URL: {url}")


def extract_url(output):
    match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", output)
    return match.group(0) if match else None


def api_request(method, data):
    cmd = [
        "curl",
        "-s",
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        "-H",
        "Content-Type: application/json",
        "-d",
        json.dumps(data),
    ]
    return json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)


def update_telegram(url):
    log(f"Updating bot with URL: {url}")
    api_request(
        "setChatMenuButton",
        {
            "menu_button": {
                "type": "web_app",
                "text": "🚀 Open MIND Dashboard",
                "web_app": {"url": url},
            }
        },
    )
    bot_file = Path.home() / "N-Xyme_CODE" / "N-Xyme_MIND" / "telegram-bot.py"
    if bot_file.exists():
        content = bot_file.read_text()
        new_content = re.sub(
            r'url="https://[^"]+\.trycloudflare\.com"', f'url="{url}"', content
        )
        if content != new_content:
            bot_file.write_text(new_content)
            subprocess.run(["systemctl", "--user", "restart", "telegram-bot"])
            log("Bot restarted with new URL")


def start_tunnel():
    log("Starting cloudflared...")
    subprocess.run(["pkill", "-f", "cloudflared"], capture_output=True)

    proc = subprocess.Popen(
        [CLOUDFLARED_PATH, "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    url = None
    deadline = time.time() + 30

    while time.time() < deadline:
        line = proc.stdout.readline()
        if line:
            log(line.strip())
            url = extract_url(line)
            if url:
                break
        time.sleep(0.5)

    if not url:
        proc.kill()
        log("Failed to get tunnel URL")
        return None

    return url


def main():
    log("=" * 50)
    log("Tunnel Manager Started")
    log("=" * 50)

    if not os.path.exists(CLOUDFLARED_PATH):
        log("Installing cloudflared...")
        subprocess.run(
            [
                "curl",
                "-sL",
                "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
                "-o",
                CLOUDFLARED_PATH,
            ],
            check=True,
        )
        os.chmod(CLOUDFLARED_PATH, 0o755)

    prev_url = get_stored_url()
    if prev_url:
        log(f"Previous URL: {prev_url}")

    url = start_tunnel()
    if not url:
        sys.exit(1)

    log(f"Current URL: {url}")

    if url != prev_url:
        log("URL changed! Updating bot...")
        update_telegram(url)
        save_url(url)
    else:
        log("URL unchanged")

    log(f"Tunnel active: {url}")

    while True:
        time.sleep(60)
        result = subprocess.run(["pgrep", "-f", "cloudflared"], capture_output=True)
        if result.returncode != 0:
            log("cloudflared died, restarting...")
            url = start_tunnel()
            if url:
                if url != get_stored_url():
                    update_telegram(url)
                    save_url(url)


if __name__ == "__main__":
    main()
