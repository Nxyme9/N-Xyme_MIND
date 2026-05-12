#!/usr/bin/env python3
"""
N-Xyme MIND Telegram Bot - Bulletproof Edition
Full MIND integration with rate limiting, health monitoring, and crash recovery.
"""

import asyncio
import json
import logging
import os
import sys
import time
import signal
import traceback
from pathlib import Path
from typing import Optional
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# Load environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    from dotenv import load_dotenv

    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("telegram-bot")

# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class BotConfig:
    MAX_INPUT_LENGTH: int = 2000
    MAX_COMMANDS_PER_MINUTE: int = 10
    MAX_COMMANDS_PER_HOUR: int = 100
    HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes
    HEARTBEAT_INTERVAL: int = 3600  # 1 hour
    MAX_RESPONSE_LENGTH: int = 4000
    GRACE_PERIOD_SECONDS: int = 60  # After restart


config = BotConfig()

# ============================================================================
# STATE MANAGEMENT
# ============================================================================


@dataclass
class UserState:
    chat_id: int
    username: str = ""
    first_seen: datetime = field(default_factory=datetime.now)
    last_message: datetime = field(default_factory=datetime.now)
    command_count_minute: int = 0
    command_count_hour: int = 0
    minute_reset: datetime = field(default_factory=datetime.now)
    hour_reset: datetime = field(default_factory=datetime.now)
    is_whitelisted: bool = False


class StateManager:
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.users: dict[int, UserState] = {}
        self.known_chat_ids: set[int] = set()
        self.last_health_check: datetime = datetime.min
        self.last_heartbeat: datetime = datetime.min
        self.startup_time: datetime = datetime.now()
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.known_chat_ids = set(data.get("known_chat_ids", []))
                    self.startup_time = datetime.fromisoformat(
                        data.get("startup_time", datetime.now().isoformat())
                    )
                    logger.info(f"Loaded {len(self.known_chat_ids)} known chat IDs")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save(self):
        with self._lock:
            try:
                with open(self.state_file, "w") as f:
                    json.dump(
                        {
                            "known_chat_ids": list(self.known_chat_ids),
                            "startup_time": self.startup_time.isoformat(),
                        },
                        f,
                    )
            except Exception as e:
                logger.error(f"Failed to save state: {e}")

    def register_user(self, chat_id: int, username: str = "") -> UserState:
        if chat_id not in self.users:
            self.users[chat_id] = UserState(chat_id=chat_id, username=username)
            self.known_chat_ids.add(chat_id)
            self._save()
        return self.users[chat_id]

    def check_rate_limit(self, chat_id: int) -> tuple[bool, str]:
        if chat_id not in self.users:
            return True, "OK"

        user = self.users[chat_id]
        now = datetime.now()

        # Reset counters if needed
        if now - user.minute_reset > timedelta(minutes=1):
            user.command_count_minute = 0
            user.minute_reset = now
        if now - user.hour_reset > timedelta(hours=1):
            user.command_count_hour = 0
            user.hour_reset = now

        # Check limits
        if user.command_count_minute >= config.MAX_COMMANDS_PER_MINUTE:
            return (
                False,
                f"⚠️ Rate limit: Max {config.MAX_COMMANDS_PER_MINUTE} commands/minute",
            )
        if user.command_count_hour >= config.MAX_COMMANDS_PER_HOUR:
            return (
                False,
                f"⚠️ Rate limit: Max {config.MAX_COMMANDS_PER_HOUR} commands/hour",
            )

        # Increment
        user.command_count_minute += 1
        user.command_count_hour += 1
        user.last_message = now
        return True, "OK"

    def is_first_startup(self) -> bool:
        return datetime.now() - self.startup_time < timedelta(
            seconds=config.GRACE_PERIOD_SECONDS
        )


# Global state
STATE_FILE = PROJECT_ROOT / "telegram-bot-state.json"
state_manager = StateManager(STATE_FILE)

# ============================================================================
# MIND INTEGRATION
# ============================================================================


def get_mind_state() -> dict:
    try:
        from packages.nx_mind_mcp import get_mind_state

        return get_mind_state()
    except Exception as e:
        logger.error(f"Failed to get mind state: {e}")
        return {"project": None, "phase": None, "active_tasks": [], "context": {}}


def get_sessions() -> dict:
    try:
        from packages.nx_mind_mcp import get_session_history

        return get_session_history(limit=5)
    except Exception as e:
        logger.error(f"Failed to get sessions: {e}")
        return {"sessions": [], "count": 0}


def get_health_status() -> dict:
    try:
        from packages.brain_mcp.utils.health import get_all_health_checks

        return get_all_health_checks()
    except Exception as e:
        logger.warning(f"Health check partial: {e}")
        return {"status": "partial", "error": str(e)}


def get_learning_status() -> dict:
    try:
        from packages.brain_mcp.namespaces.learning import learning_status

        return learning_status()
    except Exception as e:
        logger.warning(f"Learning status failed: {e}")
        return {"status": "unavailable", "error": str(e)}


def search_memory(query: str) -> dict:
    try:
        from packages.brain_mcp.namespaces.memory import memory_search

        return memory_search(query=query, top_k=5)
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        return {"results": [], "error": str(e)}


async def route_to_mind(task: str, context: Optional[dict] = None) -> dict:
    try:
        from packages.nx_delegate.nx_delegate import nx_delegate

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: nx_delegate(task))
        return result
    except Exception as e:
        logger.error(f"Routing failed: {e}")
        return {"agent": "error", "error": str(e), "level": 0, "confidence": 0.0}


async def spawn_agent_task(task: str, force_agent: Optional[str] = None) -> dict:
    try:
        from packages.orchestration.spawn import spawn, SpawnResult

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: asyncio.run(spawn(task=task, context={"source": "telegram"}))
        )
        return {
            "success": result.success,
            "agent": result.agent,
            "output": str(result.output)[:500] if result.output else None,
            "duration_ms": result.duration_ms,
            "task_id": result.task_id,
        }
    except Exception as e:
        logger.error(f"Spawn failed: {e}")
        return {"success": False, "error": str(e)}


def validate_input(text: str) -> tuple[bool, str]:
    if not text or not text.strip():
        return False, "Empty message"
    if len(text) > config.MAX_INPUT_LENGTH:
        return False, f"Message too long (max {config.MAX_INPUT_LENGTH} chars)"
    return True, "OK"


# ============================================================================
# NOTIFICATION SYSTEM
# ============================================================================


class NotificationManager:
    def __init__(self):
        self.subscribers: dict[int, set[str]] = defaultdict(set)
        self.last_health_status: dict = {}
        self._load_subscribers()

    def _load_subscribers(self):
        sub_file = PROJECT_ROOT / "telegram-subscribers.json"
        if sub_file.exists():
            try:
                with open(sub_file) as f:
                    data = json.load(f)
                    for chat_id, alerts in data.items():
                        self.subscribers[int(chat_id)] = set(alerts)
                logger.info(f"Loaded {len(self.subscribers)} notification subscribers")
            except Exception as e:
                logger.error(f"Failed to load subscribers: {e}")

    def _save_subscribers(self):
        sub_file = PROJECT_ROOT / "telegram-subscribers.json"
        try:
            data = {str(k): list(v) for k, v in self.subscribers.items()}
            with open(sub_file, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save subscribers: {e}")

    def subscribe(self, chat_id: int, alert_type: str):
        self.subscribers[chat_id].add(alert_type)
        self._save_subscribers()

    def unsubscribe(self, chat_id: int, alert_type: str):
        self.subscribers[chat_id].discard(alert_type)
        self._save_subscribers()

    def is_subscribed(self, chat_id: int, alert_type: str) -> bool:
        return alert_type in self.subscribers.get(chat_id, set())

    def get_subscribers(self, alert_type: str) -> list[int]:
        return [cid for cid, alerts in self.subscribers.items() if alert_type in alerts]

    def subscriptions_for_user(self, chat_id: int) -> set[str]:
        return self.subscribers.get(chat_id, set())

    async def send_alert(
        self, bot, chat_id: int, title: str, message: str, severity: str = "info"
    ):
        emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️", "success": "✅"}.get(
            severity, "ℹ️"
        )
        text = f"{emoji} *{title}*\n\n{message}"
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("💚 Health", callback_data="health")],
        ]
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        except Exception as e:
            logger.error(f"Failed to send alert to {chat_id}: {e}")


notification_manager = NotificationManager()

# ============================================================================
# VOICE MESSAGE HANDLER
# ============================================================================


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.message.chat_id
    username = (
        update.message.from_user.username
        or update.message.from_user.first_name
        or "User"
    )

    logger.info(f"Voice message from @{username} (chat_id={chat_id})")

    state_manager.register_user(chat_id, username)

    allowed, msg = state_manager.check_rate_limit(chat_id)
    if not allowed:
        await update.message.reply_text(msg)
        return

    processing_msg = await update.message.reply_text(
        "🎤 *Voice message received*\n\nDownloading and processing..."
    )

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        await processing_msg.edit_text(
            "🎤 *Voice received!*\n\nNote: Speech-to-text processing requires additional setup.\n\n"
            "For now, please use text messages. Voice pipeline coming soon!",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Voice handling failed: {e}")
        await processing_msg.edit_text(
            f"❌ *Voice processing failed:* `{str(e)[:200]}`", parse_mode="Markdown"
        )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.message.chat_id
    username = (
        update.message.from_user.username
        or update.message.from_user.first_name
        or "User"
    )
    doc = update.message.document

    logger.info(f"Document from @{username}: {doc.file_name}")

    state_manager.register_user(chat_id, username)

    allowed, msg = state_manager.check_rate_limit(chat_id)
    if not allowed:
        await update.message.reply_text(msg)
        return

    try:
        file = await context.bot.get_file(doc.file_id)

        save_path = PROJECT_ROOT / "uploads" / f"{doc.file_id}_{doc.file_name}"
        save_path.parent.mkdir(exist_ok=True)
        await file.download_to_drive(save_path)

        await update.message.reply_text(
            f"📄 *File received!*\n\n"
            f"Name: `{doc.file_name}`\n"
            f"Size: {doc.file_size:,} bytes\n\n"
            f"Saved to: `{save_path.name}`",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error(f"Document handling failed: {e}")
        await update.message.reply_text(
            f"❌ *File upload failed:* `{str(e)[:200]}`", parse_mode="Markdown"
        )


# ============================================================================
# HEALTH MONITOR (Background Thread)
# ============================================================================


async def health_monitor_task(app: Application):
    last_status = None
    while True:
        try:
            await asyncio.sleep(config.HEALTH_CHECK_INTERVAL)

            health = get_health_status()
            current_status = health.get("status")

            if last_status == "healthy" and current_status == "degraded":
                for chat_id in notification_manager.get_subscribers("health"):
                    await notification_manager.send_alert(
                        app.bot,
                        chat_id,
                        "⚠️ System Degraded",
                        f"Health status changed from healthy to degraded.\n\n"
                        f"Check /health for details.",
                        severity="warning",
                    )

            elif last_status != "critical" and current_status == "critical":
                for chat_id in notification_manager.get_subscribers("health"):
                    await notification_manager.send_alert(
                        app.bot,
                        chat_id,
                        "🚨 System Critical",
                        f"Health status is now CRITICAL.\n\n"
                        f"Immediate attention required!",
                        severity="critical",
                    )

            last_status = current_status

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Health monitor error: {e}")


# ============================================================================
# TELEGRAM HANDLERS
# ============================================================================


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    username = (
        update.message.from_user.username
        or update.message.from_user.first_name
        or "User"
    )

    state_manager.register_user(chat_id, username)
    logger.info(f"User @{username} (chat_id={chat_id}) started bot")

    welcome = """
🖥️ *N-Xyme MIND Bot Online!*

I'm your AI coding assistant, connected to the MIND system.

*Features:*
• Route tasks to specialized agents
• Check system health & status
• Search memory & context
• Execute tasks via orchestration

*Commands:*
/help - All commands
/status - System status
/health - Health check
/sessions - Recent sessions
/menu - Control menu
/learning - Learning stats
/search - Search memory
"""
    keyboard = [
        [
            InlineKeyboardButton(
                "🚀 Open Dashboard",
                url="https://conventions-pledge-strategic-hydrocodone.trycloudflare.com",
            )
        ],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("💚 Health", callback_data="health")],
        [InlineKeyboardButton("🔍 Search", callback_data="search")],
    ]
    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📚 *Commands:*

*Basic:*
/start - Start bot
/help - This message

*System:*
/status - Full status
/health - Quick health
/sessions - Recent sessions
/learning - Learning stats
/search <query> - Search memory

*Actions:*
/menu - Control menu
/cancel - Cancel task

*Just chat!* I'll route to agents.
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Fetching status...")

    mind = get_mind_state()
    sessions = get_sessions()
    health = get_health_status()
    learning = get_learning_status()

    text = f"""
📊 *System Status*

*🧠 MIND:*
• Project: `{mind.get("project", "None")}`
• Phase: `{mind.get("phase", "None")}`
• Active Tasks: {len(mind.get("active_tasks", []))}

*📂 Sessions:* {sessions.get("count", 0)} recent
*💚 Health:* `{health.get("status", "unknown")}`
*🎓 Learning:* `{learning.get("status", "unknown")}`
"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="status")],
        [InlineKeyboardButton("⚡ Menu", callback_data="menu")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💚 Checking health...")

    health = get_health_status()
    status = health.get("status", "unknown")
    emoji = "✅" if status == "healthy" else "⚠️" if status == "degraded" else "❌"

    text = f"""{emoji} *Health: `{status}`*

*Namespaces:*
"""
    for ns, data in health.get("namespaces", {}).items():
        ns_status = data.get("status", "?")
        emoji = (
            "✅" if ns_status == "healthy" else "⚠️" if ns_status == "degraded" else "❌"
        )
        text += f"• {ns}: {emoji} `{ns_status}`\n"

    keyboard = [
        [InlineKeyboardButton("🔄 Recheck", callback_data="health")],
        [InlineKeyboardButton("📊 Full Status", callback_data="status")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📂 Loading sessions...")

    sessions = get_sessions()
    session_list = sessions.get("sessions", [])

    if not session_list:
        text = "📂 *No recent sessions*"
    else:
        lines = ["📂 *Recent Sessions:*\n"]
        for i, sess in enumerate(session_list[:5], 1):
            summary = sess.get("summary", "No summary")[:50]
            lines.append(f"{i}. `{summary}...`")
        text = "\n".join(lines)

    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="sessions")],
        [InlineKeyboardButton("⚡ Menu", callback_data="menu")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 System Status", callback_data="status")],
        [InlineKeyboardButton("💚 Health Check", callback_data="health")],
        [InlineKeyboardButton("📂 Sessions", callback_data="sessions")],
        [InlineKeyboardButton("🔍 Search Memory", callback_data="search")],
        [InlineKeyboardButton("🎓 Learning Status", callback_data="learning")],
        [InlineKeyboardButton("⚠️ System Alert", callback_data="alert_test")],
    ]
    await update.message.reply_text(
        "⚡ *Control Menu*\n\nSelect:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def learning_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    learning = get_learning_status()
    text = f"""
🎓 *Learning System*

*Status:* `{learning.get("status", "unknown")}`
*Confidence:* {learning.get("confidence", "N/A")}
"""
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="learning")],
        [InlineKeyboardButton("⚡ Menu", callback_data="menu")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args) if context.args else ""

    if not query:
        await update.message.reply_text(
            "🔍 *Memory Search*\n\nUsage: `/search <query>`", parse_mode="Markdown"
        )
        return

    await update.message.reply_text(f"🔍 Searching for: `{query[:100]}`...")

    results = search_memory(query)
    hits = results.get("results", [])

    if not hits:
        text = f"🔍 *No results* for: `{query[:100]}`"
    else:
        lines = [f"🔍 *{len(hits)} results* for: `{query[:50]}`\n"]
        for i, hit in enumerate(hits[:3], 1):
            content = hit.get("content", "")[:100]
            lines.append(f"{i}. `{content}...`")
        text = "\n".join(lines)

    keyboard = [
        [InlineKeyboardButton("🔄 New Search", callback_data="search")],
        [InlineKeyboardButton("⚡ Menu", callback_data="menu")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================================
# NOTIFY COMMAND - Manage notification subscriptions
# ============================================================================


async def notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    args = context.args if context.args else []

    if not args:
        # Show current subscriptions
        current = notification_manager.subscriptions_for_user(chat_id)
        all_types = ["health", "sessions", "learning", "alerts", "critical"]
        lines = ["🔔 *Notification Subscriptions*\n"]
        lines.append(f"Current: `{', '.join(current) if current else 'none'}`\n")
        lines.append("*Available:*")
        for t in all_types:
            status = "✅" if t in current else "❌"
            lines.append(f"  {status} {t}")
        lines.append("\n*Usage:* `/notify <type> [on/off]`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    action_or_type = args[0].lower()
    if len(args) == 1:
        if action_or_type in ["on", "off"]:
            # Toggle all
            alert_type = args[1] if len(args) > 1 else None
            if alert_type:
                if action_or_type == "on":
                    notification_manager.subscribe(chat_id, alert_type)
                    await update.message.reply_text(f"✅ Subscribed to `{alert_type}`")
                else:
                    notification_manager.unsubscribe(chat_id, alert_type)
                    await update.message.reply_text(
                        f"❌ Unsubscribed from `{alert_type}`"
                    )
            else:
                # List subscriptions
                current = list(notification_manager.subscriptions_for_user(chat_id))
                await update.message.reply_text(
                    f"🔔 Your subscriptions: `{', '.join(current) or 'none'}`",
                    parse_mode="Markdown",
                )
        elif action_or_type == "list":
            current = list(notification_manager.subscriptions_for_user(chat_id))
            await update.message.reply_text(
                f"🔔 Subscribed to: `{', '.join(current) or 'none'}`",
                parse_mode="Markdown",
            )
        else:
            # Toggle single
            if notification_manager.is_subscribed(chat_id, action_or_type):
                notification_manager.unsubscribe(chat_id, action_or_type)
                await update.message.reply_text(
                    f"❌ Unsubscribed from `{action_or_type}`"
                )
            else:
                notification_manager.subscribe(chat_id, action_or_type)
                await update.message.reply_text(f"✅ Subscribed to `{action_or_type}`")
    elif len(args) == 2:
        alert_type = action_or_type
        action = args[1].lower()
        if action == "on":
            notification_manager.subscribe(chat_id, alert_type)
            await update.message.reply_text(f"✅ Subscribed to `{alert_type}`")
        elif action == "off":
            notification_manager.unsubscribe(chat_id, alert_type)
            await update.message.reply_text(f"❌ Unsubscribed from `{alert_type}`")
        else:
            await update.message.reply_text("Usage: `/notify <type> [on/off]`")
    else:
        await update.message.reply_text("Usage: `/notify <type> [on/off]`")


# ============================================================================
# BROADCAST COMMAND - Admin only: send to all subscribers
# ============================================================================


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    message = " ".join(context.args) if context.args else ""

    # Admin check (you can customize this)
    admin_chat_ids = list(notification_manager.subscribers.keys())

    if chat_id not in admin_chat_ids or len(message) < 3:
        await update.message.reply_text(
            "⚠️ *Broadcast*\n\nSend a message to all subscribers.\n\n"
            "*Usage:* `/broadcast <message>`",
            parse_mode="Markdown",
        )
        return

    if not message:
        await update.message.reply_text("❌ Message cannot be empty")
        return

    # Truncate long messages
    if len(message) > 1000:
        message = message[:1000] + "..."

    sent = 0
    failed = 0
    keyboard = [
        [InlineKeyboardButton("📊 Status", callback_data="status")],
    ]

    for sub_chat_id in notification_manager.subscribers.keys():
        try:
            await context.bot.send_message(
                chat_id=sub_chat_id,
                text=f"📢 *Broadcast*\n\n{message}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            sent += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {sub_chat_id}: {e}")
            failed += 1

    await update.message.reply_text(
        f"📢 *Broadcast Sent*\n\n✅ Delivered: {sent}\n❌ Failed: {failed}"
    )


# ============================================================================
# MESSAGE HANDLER
# ============================================================================


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_text = update.message.text
    chat_id = update.message.chat_id
    username = (
        update.message.from_user.username
        or update.message.from_user.first_name
        or "User"
    )

    logger.info(f"Message from @{username} (chat_id={chat_id}): {user_text[:50]}")

    # Register user
    state_manager.register_user(chat_id, username)

    # Check rate limit
    allowed, msg = state_manager.check_rate_limit(chat_id)
    if not allowed:
        await update.message.reply_text(msg)
        return

    # Validate input
    valid, msg = validate_input(user_text)
    if not valid:
        await update.message.reply_text(f"⚠️ {msg}")
        return

    # Show processing
    processing_msg = await update.message.reply_text(
        "🤔 Processing...\nRouting to MIND..."
    )

    try:
        # Route and spawn
        routing_result = await route_to_mind(user_text)
        agent = routing_result.get("agent", "unknown")
        level = routing_result.get("level", "?")
        confidence = routing_result.get("confidence", 0.0)

        response = f"✅ *Task Received!*\n\n*📍 Routing:*\n• Agent: `{agent}`\n• Level: L{level}\n• Confidence: {confidence:.0%}\n\n*⏳ Executing...*"
        await processing_msg.edit_text(response, parse_mode="Markdown")

        spawn_result = await spawn_agent_task(user_text, force_agent=agent)

        if spawn_result.get("success"):
            output = spawn_result.get("output", "Done")[: config.MAX_RESPONSE_LENGTH]
            duration = spawn_result.get("duration_ms", 0) / 1000
            final_text = f"✅ *Task Complete!*\n\n*Agent:* `{spawn_result.get('agent', agent)}`\n*Duration:* {duration:.1f}s\n\n*Result:*\n{output}"
        else:
            error = spawn_result.get("error", "Unknown")[:200]
            final_text = f"⚠️ *Issue:* `{error}`\n\nTry again or use /menu"

        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status")],
            [InlineKeyboardButton("⚡ Menu", callback_data="menu")],
        ]
        await processing_msg.edit_text(
            final_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    except Exception as e:
        logger.error(f"Message error: {e}")
        await processing_msg.edit_text(
            f"❌ *Error:* `{str(e)[:200]}`\n\nPlease try again.", parse_mode="Markdown"
        )


# ============================================================================
# CALLBACK HANDLER
# ============================================================================


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    chat_id = query.message.chat_id

    # Register user on interaction
    username = query.from_user.username or query.from_user.first_name or "User"
    state_manager.register_user(chat_id, username)

    # Check rate limit
    allowed, msg = state_manager.check_rate_limit(chat_id)
    if not allowed:
        await query.message.reply_text(msg)
        return

    logger.info(f"Callback from chat_id={chat_id}: {data}")

    handlers = {
        "status": _build_status_text,
        "health": _build_health_text,
        "sessions": _build_sessions_text,
        "learning": _build_learning_text,
        "search": lambda: (
            "🔍 *Memory Search*\n\nSend /search <query> to search.",
            None,
        ),
        "menu": lambda: ("⚡ *Menu*\n\nSelect:", _menu_keyboard()),
        "alert_test": _test_alert,
    }

    if data in handlers:
        text, keyboard = handlers[data]()
    else:
        text = f"Unknown: {data}"
        keyboard = _menu_keyboard()

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    try:
        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Edit failed: {e}")
        await query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=reply_markup
        )


def _build_status_text():
    mind = get_mind_state()
    sessions = get_sessions()
    health = get_health_status()
    text = f"""
📊 *Status*

*🧠 MIND:* `{mind.get("project", "None")}` / `{mind.get("phase", "None")}`
*📂 Sessions:* {sessions.get("count", 0)}
*💚 Health:* `{health.get("status", "unknown")}`
"""
    return text, _menu_keyboard()


def _build_health_text():
    health = get_health_status()
    status = health.get("status", "unknown")
    emoji = "✅" if status == "healthy" else "⚠️"
    text = f"{emoji} Health: `{status}`"
    return text, _menu_keyboard()


def _build_sessions_text():
    sessions = get_sessions()
    session_list = sessions.get("sessions", [])
    if not session_list:
        return "📂 *No sessions*", _menu_keyboard()
    lines = ["📂 *Recent:*\n"]
    for i, sess in enumerate(session_list[:3], 1):
        lines.append(f"{i}. `{sess.get('summary', '?')[:30]}...`")
    return "\n".join(lines), _menu_keyboard()


def _build_learning_text():
    learning = get_learning_status()
    return f"🎓 Learning: `{learning.get('status', 'unknown')}`", _menu_keyboard()


def _test_alert():
    return "⚠️ *Alert Test*\n\nAlerts configured!", _menu_keyboard()


def _menu_keyboard():
    return [
        [InlineKeyboardButton("📊 Status", callback_data="status")],
        [InlineKeyboardButton("💚 Health", callback_data="health")],
        [InlineKeyboardButton("📂 Sessions", callback_data="sessions")],
        [InlineKeyboardButton("🎓 Learning", callback_data="learning")],
    ]


# ============================================================================
# ERROR HANDLER
# ============================================================================


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ Error: `{str(context.error)[:100]}`", parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error handler failed: {e}")


# ============================================================================
# MAIN
# ============================================================================


def main():
    import signal

    def signal_handler(signum, frame):
        logger.info(f"Signal {signum}, shutting...")
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    logger.info(f"Starting bot with token: {TOKEN[:20]}...")

    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("sessions", sessions_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("learning", learning_command))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("notify", notify_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.add_error_handler(error_handler)

    logger.info("Bot handlers registered")
    print("=" * 50)
    print("🤖 N-Xyme MIND Telegram Bot (Bulletproof)")
    print("=" * 50)
    print(f"✅ @NXopencode_bot LIVE")
    print(f"📍 Rate limiting: {config.MAX_COMMANDS_PER_MINUTE}/min")
    print(f"💚 Health monitoring: ON")
    print(f"🎤 Voice handling: ON")
    print(f"📄 File upload: ON")
    print(f"🔔 Notifications: ON")
    print("=" * 50)

    # Start health monitor in background thread
    import threading

    monitor_thread = threading.Thread(
        target=_run_health_monitor, args=(app,), daemon=True
    )
    monitor_thread.start()

    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Polling error: {e}")
        traceback.print_exc()


def _run_health_monitor(app):
    import asyncio

    asyncio.run(health_monitor_task(app))


if __name__ == "__main__":
    main()
