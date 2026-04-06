#!/usr/bin/env python3
"""
Ultra-simple Telegram bot - debug version
"""

import os
import json
import time
import requests

TOKEN = "8397949824:AAEkYzjVwIVUQAfTiFL2UcsGVC4Dgr7lXDw"
ALLOWED_USER_ID = "1546806138"


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    resp = requests.post(url, json=data)
    print(f"Sent: {resp.status_code}")
    return resp.json()


def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    resp = requests.get(url, params=params)
    return resp.json()


print("Starting simple bot...")
print(f"Token: {TOKEN[:20]}...")
print(f"Allowed user: {ALLOWED_USER_ID}")

# Test bot info
me = requests.get(f"https://api.telegram.org/bot{TOKEN}/getMe").json()
print(f"Bot info: {me}")

# Send test message to user
try:
    result = send_message(ALLOWED_USER_ID, "🔥 NXopencode Bot test message!")
    print(f"Message sent: {result}")
except Exception as e:
    print(f"Error sending: {e}")

# Now poll for updates
offset = None
print("\nPolling for messages...")
while True:
    try:
        updates = get_updates(offset)
        if updates.get("ok") and updates.get("result"):
            for u in updates["result"]:
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                text = msg.get("text", "")
                chat_id = msg.get("chat", {}).get("id")
                user_id = str(msg.get("from", {}).get("id", ""))

                print(f"Message: {text} from {user_id}")

                if user_id == ALLOWED_USER_ID:
                    if text == "/start":
                        send_message(chat_id, "🔥 Bot is working! Send /status")
                    elif text == "/status":
                        send_message(chat_id, "✅ Bot operational")
                    else:
                        send_message(chat_id, f"Got: {text}")
        time.sleep(1)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
