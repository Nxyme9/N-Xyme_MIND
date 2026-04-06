#!/usr/bin/env python3
"""
Simple working Telegram bot
"""

import os
import requests

TOKEN = "8397949824:AAEkYzjVwIVUQAfTiFL2UcsGVC4Dgr7lXDw"
ALLOWED_USER_ID = "1546806138"


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text})


def main():
    print("Bot started! Polling...")
    offset = None

    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset

            resp = requests.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params=params,
                timeout=35,
            )
            data = resp.json()

            if data.get("ok") and data.get("result"):
                for u in data["result"]:
                    offset = u["update_id"] + 1
                    msg = u.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    user_id = str(msg.get("from", {}).get("id", ""))

                    print(f"From {user_id}: {text}")

                    if user_id == ALLOWED_USER_ID:
                        if text == "/start":
                            send_message(
                                chat_id, "🔥 NXopencode Bot online! Type /status"
                            )
                        elif text == "/status":
                            send_message(
                                chat_id,
                                "✅ Bot operational - ready to control N-Xyme_MIND!",
                            )
                        else:
                            send_message(
                                chat_id,
                                f"📝 Got: {text}\n\nBot is working! More features coming soon.",
                            )

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
