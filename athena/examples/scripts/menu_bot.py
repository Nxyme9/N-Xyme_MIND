#!/usr/bin/env python3
"""
N-Xyme_MIND Telegram Control Bot
ADHD-friendly: ZERO typing - all via button clicks!
Max 2 taps to any action.
"""

import os
import json
import requests
import subprocess
import threading
import time
import tempfile
import urllib.request
from pathlib import Path

TOKEN = "8397949824:AAEkYzjVwIVUQAfTiFL2UcsGVC4Dgr7lXDw"
ALLOWED_USER_ID = "1546806138"

# Paths
MIND_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
SESSION_FILE = f"{MIND_DIR}/.sisyphus/session-state.json"
OPENCODE_JSON = f"{MIND_DIR}/opencode.json"


# ============ KEYBOARD BUILDER ============


def build_main_menu():
    """Build ADHD-friendly main menu - 6 buttons in 2x3 grid"""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "📂 Sessions", "callback_data": "menu_sessions"},
                {"text": "🎯 New Task", "callback_data": "menu_newtask"},
            ],
            [
                {"text": "📊 Status", "callback_data": "menu_status"},
                {"text": "⚙️ Settings", "callback_data": "menu_settings"},
            ],
            [
                {"text": "📜 History", "callback_data": "menu_history"},
                {"text": "💡 Help", "callback_data": "menu_help"},
            ],
        ]
    }
    return keyboard


def build_sessions_menu():
    """Build session list menu"""
    sessions = get_active_sessions()

    keyboard = {"inline_keyboard": []}

    # Add each session as a button
    for session in sessions[:8]:  # Max 8 buttons
        # Show more useful info in the button
        label = session.get("id", "unknown")[:12]
        if "current_task" in session:
            task = str(session.get("current_task", ""))[:20]
            label = f"{label}: {task}"

        keyboard["inline_keyboard"].append(
            [
                {
                    "text": f"📄 {label}",
                    "callback_data": f"session_{session.get('id', 'unknown')}",
                }
            ]
        )

    # Back button
    keyboard["inline_keyboard"].append(
        [{"text": "⬅️ Back", "callback_data": "menu_main"}]
    )
    return keyboard


def build_back_menu(callback_data="menu_main"):
    """Build a simple back button"""
    keyboard = {
        "inline_keyboard": [[{"text": "⬅️ Back", "callback_data": callback_data}]]
    }
    return keyboard


# ============ DATA FETCHERS ============


def get_active_sessions():
    """Get active OpenCode sessions from real session files"""
    sessions = []
    try:
        # Read from session-state.json
        if Path(SESSION_FILE).exists():
            with open(SESSION_FILE) as f:
                state = json.load(f)

            # Create a session entry from current state
            session_info = {
                "id": state.get("last_agent", "unknown"),
                "current_task": state.get("current_task", "No active task"),
                "last_active": state.get("last_updated", ""),
                "messages": state.get("memory_stats", {}).get("files_indexed", 0),
            }
            sessions.append(session_info)

        # Also check mind-state.json for additional context
        mind_file = f"{MIND_DIR}/.context/mind-state.json"
        if Path(mind_file).exists():
            with open(mind_file) as f:
                mind = json.load(f)

            if mind.get("phase"):
                sessions.append(
                    {
                        "id": "MIND",
                        "current_task": f"Phase: {mind.get('phase')}",
                        "last_active": mind.get("last_updated", ""),
                        "messages": mind.get("context", {}).get("tests_passed", 0),
                    }
                )

    except Exception as e:
        print(f"Session read error: {e}")

    # Always have at least one entry for the UI
    if not sessions:
        sessions = [
            {
                "id": "No sessions",
                "current_task": "Start a new session",
                "last_active": "Now",
                "messages": 0,
            }
        ]

    return sessions


def get_opencode_status():
    """Get OpenCode status"""
    try:
        # Check if MCP is running
        result = subprocess.run(
            ["pgrep", "-f", "opencode"], capture_output=True, text=True
        )
        running = bool(result.stdout.strip())

        # Check config
        config_exists = Path(OPENCODE_JSON).exists()

        return {
            "opencode_running": running,
            "config_exists": config_exists,
            "mcp_count": 4,
        }
    except Exception as e:
        return {"error": str(e)}


def get_system_status():
    """Get system status for display"""
    status = get_opencode_status()

    if "error" in status:
        return "⚠️ Status unavailable"

    indicators = []
    if status.get("opencode_running"):
        indicators.append("🟢 OpenCode")
    else:
        indicators.append("🔴 OpenCode")

    if status.get("config_exists"):
        indicators.append("🟢 Config")
    else:
        indicators.append("🔴 Config")

    indicators.append(f"🔵 {status.get('mcp_count', 0)} MCPs")

    return " | ".join(indicators)


# ============ TELEGRAM API ============


def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    """Send a message with optional keyboard"""
    import json
    import urllib.parse

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        # Convert dict to JSON string for form-encoded request
        data["reply_markup"] = (
            json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
        )
    if parse_mode:
        data["parse_mode"] = parse_mode
    # Always use data= (form-encoded) for reliable keyboard + markdown
    requests.post(url, data=data, timeout=10)


def answer_callback(callback_id, text, show_alert=False):
    """Answer a callback query"""
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    data = {"callback_query_id": callback_id, "text": text, "show_alert": show_alert}
    requests.post(url, json=data, timeout=10)


def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """Edit an existing message - faster than sending new ones"""
    import json

    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
    }
    if reply_markup:
        data["reply_markup"] = (
            json.dumps(reply_markup) if isinstance(reply_markup, dict) else reply_markup
        )
    if parse_mode:
        data["parse_mode"] = parse_mode
    requests.post(url, data=data, timeout=10)


# ============ VOICE HANDLING ============


def download_voice_file(file_id: str) -> str:
    """Download Telegram voice file and return local path"""
    # Get file path
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    resp = requests.get(url, timeout=10)
    data = resp.json()

    if not data.get("ok"):
        raise Exception("Failed to get file info")

    file_path = data["result"]["file_path"]
    file_url = f"https://api.telegram.org/bot{TOKEN}/{file_path}"

    # Download to temp file
    temp_file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
    urllib.request.urlretrieve(file_url, temp_file.name)
    temp_file.close()

    return temp_file.name


def transcribe_voice(voice_path: str) -> dict:
    """Transcribe voice file using faster-whisper"""
    import sys

    sys.path.insert(0, MIND_DIR)

    # Check if faster-whisper is available
    try:
        import faster_whisper
    except ImportError:
        # Fallback: return error without crashing
        return {
            "text": "",
            "error": "faster-whisper not installed. Voice transcription unavailable.",
            "success": False,
            "installed": False,
        }

    try:
        from src.infrastructure.whisper_transcription import WhisperTranscription

        whisper = WhisperTranscription(model_name="base")
        result = whisper.transcribe(voice_path)
        return {
            "text": result.text,
            "language": result.language,
            "duration": result.duration,
            "success": True,
        }
    except Exception as e:
        return {"text": "", "error": str(e), "success": False}


def parse_voice_command(text: str) -> dict:
    """Parse voice text into actionable commands"""
    text = text.lower().strip()

    # Intent patterns
    intents = [
        ("status", ["status", "how are you", "working", "health", "check"]),
        ("sessions", ["sessions", "conversations", "chats", "list sessions"]),
        ("new task", ["new task", "create task", "start task", "help me"]),
        ("help", ["help", "what can you do", "commands"]),
        ("history", ["history", "past", "what did we do"]),
        ("settings", ["settings", "configure", "preferences"]),
    ]

    for intent, keywords in intents:
        if any(kw in text for kw in keywords):
            return {"intent": intent, "text": text, "action": f"menu_{intent}"}

    # Default: treat as task request
    return {"intent": "task", "text": text, "action": "menu_newtask"}


def handle_voice_message(chat_id: str, voice: dict):
    """Handle incoming voice message"""
    send_message(
        chat_id, "🎤 *Receiving voice...*\n\nDecoding with Whisper...", "markdown"
    )

    try:
        # Download voice file
        file_id = voice.get("file_id", "")
        if not file_id:
            send_message(chat_id, "❌ No voice file found", parse_mode="markdown")
            return

        voice_path = download_voice_file(file_id)

        # Transcribe
        send_message(chat_id, "🧠 *Transcribing...*", parse_mode="markdown")
        result = transcribe_voice(voice_path)

        # Clean up
        try:
            os.unlink(voice_path)
        except:
            pass

        # Check if faster-whisper is installed
        if not result.get("success") and not result.get("installed", True):
            send_message(
                chat_id,
                "⚠️ *Voice transcription not available*\n\nfaster-whisper is not installed.\n\nTo enable voice commands, run:\n`pip install faster-whisper`\n\nUse buttons instead!",
                parse_mode="markdown",
                reply_markup=build_main_menu(),
            )
            return

        if not result.get("success"):
            send_message(
                chat_id,
                f"❌ Transcription failed: {result.get('error')}",
                parse_mode="markdown",
            )
            return

        transcript = result.get("text", "")
        if not transcript:
            send_message(
                chat_id,
                "😕 Could not understand audio. Try again?",
                parse_mode="markdown",
            )
            return

        # Show transcript
        send_message(
            chat_id, f"📝 *You said:*\n\n_{transcript}_", parse_mode="markdown"
        )

        # Parse command
        parsed = parse_voice_command(transcript)
        action = parsed.get("action", "menu_main")

        # Execute action
        if action == "menu_status":
            send_message(
                chat_id,
                f"📊 *Status*\n\n{get_system_status()}",
                parse_mode="markdown",
                reply_markup=build_back_menu(),
            )
        elif action == "menu_sessions":
            sessions = get_active_sessions()
            session_list = "\n".join(
                [
                    f"• {s.get('id', 'unknown')[:20]} — {s.get('messages', 0)} items"
                    for s in sessions
                ]
            )
            send_message(
                chat_id,
                f"📂 *Sessions*\n\n{session_list or 'No sessions'}",
                parse_mode="markdown",
                reply_markup=build_sessions_menu(),
            )
        elif action == "menu_newtask":
            send_message(
                chat_id,
                f"🎯 *New Task*\n\nI'll help you create a task!\n\n_Topic: {transcript[:100]}..._",
                parse_mode="markdown",
                reply_markup=build_back_menu(),
            )
        elif action == "menu_help":
            help_text = """💡 *Voice Commands:*

• "Check status" → System status
• "Show sessions" → Active sessions  
• "New task [description]" → Create task
• "Help" → Show this help

Or just speak naturally - I'll understand!"""
            send_message(
                chat_id,
                help_text,
                parse_mode="markdown",
                reply_markup=build_main_menu(),
            )
        else:
            send_message(
                chat_id,
                f"✅ Understood: {parsed.get('intent')}\n\nUse buttons for more control!",
                parse_mode="markdown",
                reply_markup=build_main_menu(),
            )

    except Exception as e:
        print(f"Voice error: {e}")
        send_message(chat_id, f"❌ Error: {str(e)}", parse_mode="markdown")


# ============ CALLBACK HANDLERS ============


def handle_callback(callback_data, chat_id, callback_id, message_id=None):
    """Handle callback query button presses"""

    # Answer immediately for snappy feel
    answer_callback(callback_id, "Loading...")

    if callback_data == "menu_main":
        # Show main menu - single consolidated message
        status = get_system_status()
        send_message(
            chat_id,
            f"🧠 *N-Xyme_MIND Control*\n\n{status}\n\nSelect an option:",
            parse_mode="markdown",
            reply_markup=build_main_menu(),
        )

    elif callback_data == "menu_sessions":
        # Show sessions
        sessions = get_active_sessions()
        session_list = "\n".join(
            [
                f"• {s.get('id', 'unknown')[:20]} — {s.get('messages', 0)} items"
                for s in sessions
            ]
        )
        send_message(
            chat_id,
            f"📂 *Active Sessions*\n\n{session_list or 'No active sessions'}",
            parse_mode="markdown",
            reply_markup=build_sessions_menu(),
        )

    elif callback_data == "menu_status":
        # Show status
        status = get_system_status()
        send_message(
            chat_id,
            f"📊 *System Status*\n\n{status}",
            parse_mode="markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data == "menu_newtask":
        # New task wizard - start
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔍 Research", "callback_data": "task_research"},
                    {"text": "💻 Code", "callback_data": "task_code"},
                ],
                [
                    {"text": "📝 Write", "callback_data": "task_write"},
                    {"text": "🔧 Fix", "callback_data": "task_fix"},
                ],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}],
            ]
        }
        send_message(
            chat_id,
            "🎯 *New Task*\n\nWhat type of task?",
            parse_mode="markdown",
            reply_markup=keyboard,
        )

    elif callback_data == "menu_settings":
        # Settings menu
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "🔔 Notifications", "callback_data": "settings_notif"},
                    {"text": "🎨 Theme", "callback_data": "settings_theme"},
                ],
                [{"text": "⬅️ Back", "callback_data": "menu_main"}],
            ]
        }
        send_message(
            chat_id,
            "⚙️ *Settings*\n\nConfigure your bot preferences",
            parse_mode="markdown",
            reply_markup=keyboard,
        )

    elif callback_data == "menu_history":
        # Show recent history
        send_message(
            chat_id,
            "📜 *Recent Activity*\n\nComing soon - view your recent actions and sessions",
            parse_mode="markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data == "menu_help":
        # Help info
        help_text = """💡 *N-Xyme_MIND Bot Help*

• This bot lets you control your AI coding workspace WITHOUT typing!
• Tap buttons to: view sessions, create tasks, check status
• Max 2 taps to any action
• All interactions are button-based

*Quick Start:*
1. Tap 📂 Sessions to see active work
2. Tap 🎯 New Task to start something new
3. Tap 📊 Status to check system health

Need more help? Just type /help but try buttons first!"""
        send_message(
            chat_id, help_text, parse_mode="markdown", reply_markup=build_back_menu()
        )

    elif callback_data.startswith("task_"):
        # Task type selected
        task_type = callback_data.replace("task_", "")
        send_message(
            chat_id,
            f"✅ Task type: *{task_type.upper()}*\n\nThis will open a new task in OpenCode. Continue?",
            parse_mode="markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data.startswith("session_"):
        # Session selected - show details
        session_id = callback_data.replace("session_", "")

        # Find the session data
        sessions = get_active_sessions()
        session_data = None
        for s in sessions:
            if s.get("id") == session_id:
                session_data = s
                break

        if session_data:
            details = f"""📄 *Session: {session_data.get("id", "unknown")}*

📝 *Current Task:*
{session_data.get("current_task", "None")}

⏰ *Last Active:*
{session_data.get("last_active", "Unknown")}

📊 *Stats:*
{session_data.get("messages", 0)} files indexed"""
        else:
            details = f"📄 Session: `{session_id}`\n\nNo additional details."

        send_message(
            chat_id,
            details,
            parse_mode="markdown",
            reply_markup=build_back_menu(),
        )

    else:
        send_message(chat_id, "Unknown action", reply_markup=build_back_menu())


# ============ MAIN POLLING LOOP ============


def main():
    import sys

    print("🤖 N-Xyme_MIND Bot started! (ADHD-friendly menu mode)", flush=True)
    print("   Zero typing - all via button clicks!", flush=True)

    # Get latest offset to catch any pending updates
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates", timeout=10
        )
        data = resp.json()
        offset = None
        if data.get("ok") and data.get("result"):
            if data["result"]:
                offset = data["result"][-1]["update_id"] + 1
                print(f"📡 Catching up: starting from offset {offset}", flush=True)
    except Exception as e:
        print(f"⚠️ Init error: {e}", flush=True)
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

                    # Check for messages
                    msg = u.get("message", {})
                    if msg:
                        text = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        user_id = str(msg.get("from", {}).get("id", ""))

                        print(f"Message from {user_id}: {text}")

                        if user_id == ALLOWED_USER_ID:
                            if text == "/start":
                                send_message(
                                    chat_id,
                                    "🧠 *N-Xyme_MIND Control*\n\nYour ADHD-friendly remote control!",
                                    parse_mode="markdown",
                                )
                                send_message(
                                    chat_id,
                                    get_system_status(),
                                    reply_markup=build_main_menu(),
                                )
                            elif text == "/status":
                                send_message(
                                    chat_id,
                                    f"📊 *Status*\n\n{get_system_status()}",
                                    parse_mode="markdown",
                                    reply_markup=build_back_menu(),
                                )
                            elif text == "/menu":
                                send_message(
                                    chat_id,
                                    "🧠 *N-Xyme_MIND Control*\n\nSelect:",
                                    reply_markup=build_main_menu(),
                                )
                            else:
                                send_message(
                                    chat_id,
                                    "📝 Use buttons instead of typing!\n\nTap /menu for the main menu.",
                                    reply_markup=build_main_menu(),
                                )

                    # Check for callback queries (button presses)
                    callback = u.get("callback_query", {})
                    if callback:
                        callback_id = callback.get("id")
                        callback_data = callback.get("data", "")
                        chat_id = callback.get("message", {}).get("chat", {}).get("id")

                        print(f"Callback: {callback_data}")
                        handle_callback(callback_data, chat_id, callback_id)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
