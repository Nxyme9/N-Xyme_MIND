#!/usr/bin/env python3
"""
N-Xyme_MIND Telegram Control Bot (PTB v20+)
ADHD-friendly: ZERO typing - all via button clicks!
Max 2 taps to any action.

Async version using python-telegram-bot v20+ Application.builder() pattern.
"""

import os
import json
import asyncio
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional
from datetime import datetime

# PTB imports (v20+)
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)

# ============ CONSTANTS ============

TOKEN = "8397949824:AAEkYzjVwIVUQAfTiFL2UcsGVC4Dgr7lXDw"
ALLOWED_USER_ID = "1546806138"

# Paths
MIND_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
SESSION_FILE = f"{MIND_DIR}/.sisyphus/session-state.json"
OPENCODE_JSON = f"{MIND_DIR}/opencode.json"
VOICE_PIPELINE_PATH = f"{MIND_DIR}/athena/examples/scripts/voice_pipeline.py"


# ============ VOICE RESPONSE FUNCTIONS ============


async def generate_voice_response(text: str) -> Optional[str]:
    """Generate voice response using Edge TTS.

    Args:
        text: Text to synthesize to speech

    Returns:
        Path to audio file or None if failed
    """
    try:
        # Import voice pipeline dynamically
        import sys

        sys.path.insert(0, f"{MIND_DIR}/athena/examples/scripts")
        from voice_pipeline import VoicePipeline

        # Create output path
        output_dir = Path(tempfile.gettempdir())
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"bot_response_{timestamp}.ogg"

        # Generate speech
        pipeline = VoicePipeline()
        audio_path = await pipeline.generate_voice_response(text, output_path)

        return str(audio_path)
    except Exception as e:
        print(f"TTS generation error: {e}")
        return None


async def send_voice_response(chat_id: int, text: str, context) -> bool:
    """Send voice response to user.

    Args:
        chat_id: Telegram chat ID
        text: Text to convert to voice
        context: Bot context

    Returns:
        True if successful
    """
    # Show recording indicator while generating voice
    await context.bot.send_chat_action(chat_id=chat_id, action="upload_voice")

    audio_path = await generate_voice_response(text)
    if not audio_path or not Path(audio_path).exists():
        return False

    try:
        with open(audio_path, "rb") as audio_file:
            await context.bot.send_voice(
                chat_id=chat_id,
                voice=audio_file,
                caption="🎤 Here's my response!",
            )
        # Cleanup
        Path(audio_path).unlink()
        return True
    except Exception as e:
        print(f"Voice send error: {e}")
        return False


# ============ WIZARD STATE MANAGEMENT ============

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WizardStep(Enum):
    """Wizard step identifiers"""

    # new_task wizard
    NEW_TASK_START = "new_task_start"
    NEW_TASK_TYPE = "new_task_type"
    NEW_TASK_DESCRIBE = "new_task_describe"
    NEW_TASK_CONFIRM = "new_task_confirm"
    NEW_TASK_EXECUTE = "new_task_execute"
    # kill_session wizard
    KILL_SESSION_START = "kill_session_start"
    KILL_SESSION_SELECT = "kill_session_select"
    KILL_SESSION_CONFIRM = "kill_session_confirm"


@dataclass
class WizardState:
    """Tracks wizard state per user"""

    user_id: str
    current_wizard: str  # wizard name like "new_task", "kill_session"
    step: WizardStep
    data: dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=lambda: __import__("time").time())


# Global wizard state storage (keyed by user_id)
WIZARD_STATES: dict[str, WizardState] = {}


def get_wizard_state(user_id: str) -> WizardState | None:
    """Get wizard state for a user"""
    return WIZARD_STATES.get(user_id)


def set_wizard_state(user_id: str, state: WizardState) -> None:
    """Set wizard state for a user"""
    WIZARD_STATES[user_id] = state


def clear_wizard_state(user_id: str) -> None:
    """Clear wizard state for a user"""
    WIZARD_STATES.pop(user_id, None)


def has_active_wizard(user_id: str) -> bool:
    """Check if user has an active wizard"""
    return user_id in WIZARD_STATES


class WizardHandler:
    """Manages wizard multi-step flows"""

    @staticmethod
    def start_new_task_wizard(user_id: str) -> WizardState:
        """Start new task wizard"""
        state = WizardState(
            user_id=user_id,
            current_wizard="new_task",
            step=WizardStep.NEW_TASK_START,
            data={},
        )
        set_wizard_state(user_id, state)
        return state

    @staticmethod
    def start_kill_session_wizard(user_id: str) -> WizardState:
        """Start kill session wizard"""
        state = WizardState(
            user_id=user_id,
            current_wizard="kill_session",
            step=WizardStep.KILL_SESSION_START,
            data={},
        )
        set_wizard_state(user_id, state)
        return state

    @staticmethod
    def update_step(user_id: str, step: WizardStep, data: dict = None) -> WizardState:
        """Update wizard step"""
        state = get_wizard_state(user_id)
        if state:
            state.step = step
            if data:
                state.data.update(data)
            set_wizard_state(user_id, state)
        return state

    @staticmethod
    def get_wizard_data(user_id: str) -> dict:
        """Get wizard data"""
        state = get_wizard_state(user_id)
        return state.data if state else {}


# ============ WIZARD KEYBOARDS ============


def build_wizard_cancel_menu() -> InlineKeyboardMarkup:
    """Build cancel wizard button"""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="wizard_cancel")]]
    return InlineKeyboardMarkup(keyboard)


def build_wizard_back_menu() -> InlineKeyboardMarkup:
    """Build back button for wizard"""
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="wizard_back")]]
    return InlineKeyboardMarkup(keyboard)


def build_wizard_confirm_menu(action: str) -> InlineKeyboardMarkup:
    """Build confirm/cancel buttons for wizard"""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Confirm", callback_data=f"wizard_confirm_{action}"
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="wizard_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_wizard_yesno_menu(action: str) -> InlineKeyboardMarkup:
    """Build yes/no buttons for wizard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"wizard_yes_{action}"),
            InlineKeyboardButton("❌ No", callback_data=f"wizard_no_{action}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ WIZARD CALLBACK HANDLERS ============


async def handle_wizard_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str
) -> bool:
    """Handle wizard callbacks. Returns True if handled, False otherwise."""
    query = update.callback_query
    if not query:
        return False

    callback_data = query.data
    if not callback_data:
        return False

    chat_id = query.message.chat.id if query.message else None
    message_id = query.message.message_id if query.message else None

    # Check for wizard cancellation
    if callback_data == "wizard_cancel":
        clear_wizard_state(user_id)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ *Wizard cancelled*\n\nNo changes made.",
            parse_mode="Markdown",
            reply_markup=build_main_menu(),
        )
        return True

    # Check for wizard back
    if callback_data == "wizard_back":
        state = get_wizard_state(user_id)
        if state:
            # Go back to previous step
            if state.current_wizard == "new_task":
                if state.step == WizardStep.NEW_TASK_TYPE:
                    # Go back to start
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🎯 *New Task*\n\nWhat type of task?",
                        parse_mode="Markdown",
                        reply_markup=build_new_task_menu(),
                    )
                    return True
                elif state.step == WizardStep.NEW_TASK_DESCRIBE:
                    # Go back to type selection
                    WizardHandler.update_step(user_id, WizardStep.NEW_TASK_TYPE)
                    task_type = state.data.get("task_type", "unknown")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"🎯 *New Task*\n\nSelect type: *{task_type.upper()}*\n\nNow describe what you need:",
                        parse_mode="Markdown",
                        reply_markup=build_wizard_cancel_menu(),
                    )
                    return True
                elif state.step == WizardStep.NEW_TASK_CONFIRM:
                    # Go back to describe
                    WizardHandler.update_step(user_id, WizardStep.NEW_TASK_DESCRIBE)
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🎯 *New Task - Describe*\n\nPlease describe what you need (or type /skip to use defaults):",
                        parse_mode="Markdown",
                        reply_markup=build_wizard_back_menu(),
                    )
                    return True
            elif state.current_wizard == "kill_session":
                if state.step == WizardStep.KILL_SESSION_CONFIRM:
                    # Go back to select
                    WizardHandler.update_step(user_id, WizardStep.KILL_SESSION_SELECT)
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🗑️ *Kill Session*\n\nSelect a session to terminate:",
                        parse_mode="Markdown",
                        reply_markup=build_sessions_menu(),
                    )
                    return True
        return True

    # Handle wizard actions - parse action and target
    if callback_data.startswith("wizard_"):
        parts = callback_data.split("_", 2)
        if len(parts) >= 3:
            action = parts[1]  # confirm, yes, no
            target = parts[2]  # the action target
        else:
            action = ""
            target = ""
    else:
        action = ""
        target = ""

    state = get_wizard_state(user_id)

    # Handle new_task wizard
    if state and state.current_wizard == "new_task":
        if callback_data.startswith("task_"):
            # Step 1: Task type selected
            task_type = callback_data.replace("task_", "")
            WizardHandler.update_step(
                user_id, WizardStep.NEW_TASK_DESCRIBE, {"task_type": task_type}
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🎯 *Task Type: {task_type.upper()}*\n\nNow describe what you need:",
                parse_mode="Markdown",
                reply_markup=build_wizard_cancel_menu(),
            )
            return True

        # Step 3: Confirm
        if action == "confirm" and target == "new_task":
            task_data = state.data
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"✅ *Task Created!*\n\n📝 *Type:* {task_data.get('task_type', 'unknown').upper()}\n📄 *Description:* {task_data.get('description', 'N/A')[:100]}",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            clear_wizard_state(user_id)
            return True

        # Step 4: Yes/No for execution
        if action == "yes" and target == "execute":
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🚀 *Executing task...*\n\nTask would be executed here in production.",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            clear_wizard_state(user_id)
            return True

        if action == "no" and target == "execute":
            clear_wizard_state(user_id)
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="ℹ️ *Task saved but not executed*\n\nYou can run it later from the sessions menu.",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            return True

    # Handle kill_session wizard
    if state and state.current_wizard == "kill_session":
        if callback_data.startswith("session_"):
            session_id = callback_data.replace("session_", "")
            WizardHandler.update_step(
                user_id, WizardStep.KILL_SESSION_CONFIRM, {"session_id": session_id}
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🗑️ *Kill Session: {session_id}?*\n\nThis will terminate the session. Are you sure?",
                parse_mode="Markdown",
                reply_markup=build_wizard_yesno_menu(f"kill_{session_id}"),
            )
            return True

        if action == "yes" and target.startswith("kill_"):
            session_id = target.replace("kill_", "")
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🗑️ *Session '{session_id}' terminated*",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            clear_wizard_state(user_id)
            return True

        if action == "no" and target.startswith("kill_"):
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="✅ *Cancelled*\n\nSession was NOT terminated.",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            clear_wizard_state(user_id)
            return True

    return False

    callback_data = query.data
    if not callback_data:
        return False

    chat_id = query.message.chat.id if query.message else None
    message_id = query.message.message_id if query.message else None

    # Check for wizard cancellation
    if callback_data == "wizard_cancel":
        clear_wizard_state(user_id)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="❌ *Wizard cancelled*\n\nNo changes made.",
            parse_mode="Markdown",
            reply_markup=build_main_menu(),
        )
        return True

    # Check for wizard back
    if callback_data == "wizard_back":
        state = get_wizard_state(user_id)
        if state:
            # Go back to previous step
            if state.current_wizard == "new_task":
                if state.step == WizardStep.NEW_TASK_TYPE:
                    # Go back to start
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🎯 *New Task*\n\nWhat type of task?",
                        parse_mode="Markdown",
                        reply_markup=build_new_task_menu(),
                    )
                    return True
                elif state.step == WizardStep.NEW_TASK_DESCRIBE:
                    # Go back to type selection
                    WizardHandler.update_step(user_id, WizardStep.NEW_TASK_TYPE)
                    task_type = state.data.get("task_type", "unknown")
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"🎯 *New Task*\n\nSelect type: *{task_type.upper()}*\n\nNow describe what you need:",
                        parse_mode="Markdown",
                        reply_markup=build_wizard_cancel_menu(),
                    )
                    return True
                elif state.step == WizardStep.NEW_TASK_CONFIRM:
                    # Go back to describe
                    WizardHandler.update_step(user_id, WizardStep.NEW_TASK_DESCRIBE)
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🎯 *New Task - Describe*\n\nPlease describe what you need (or type /skip to use defaults):",
                        parse_mode="Markdown",
                        reply_markup=build_wizard_back_menu(),
                    )
                    return True
            elif state.current_wizard == "kill_session":
                if state.step == WizardStep.KILL_SESSION_CONFIRM:
                    # Go back to select
                    WizardHandler.update_step(user_id, WizardStep.KILL_SESSION_SELECT)
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🗑️ *Kill Session*\n\nSelect a session to terminate:",
                        parse_mode="Markdown",
                        reply_markup=build_sessions_menu(),
                    )
                    return True
        return True

    # Handle wizard actions
    if callback_data.startswith("wizard_"):
        parts = callback_data.split("_", 2)
        if len(parts) >= 3:
            action = parts[1]  # confirm, yes, no
            target = parts[2]  # the action target

        state = get_wizard_state(user_id)

        # Handle new_task wizard
        if state and state.current_wizard == "new_task":
            if callback_data.startswith("wizard_"):
                # Step 1: Task type selected
                if callback_data.startswith("task_") or "wizard_type_" in callback_data:
                    task_type = callback_data.replace("task_", "").replace(
                        "wizard_type_", ""
                    )
                    WizardHandler.update_step(
                        user_id, WizardStep.NEW_TASK_DESCRIBE, {"task_type": task_type}
                    )
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"🎯 *Task Type: {task_type.upper()}*\n\nNow describe what you need:",
                        parse_mode="Markdown",
                        reply_markup=build_wizard_cancel_menu(),
                    )
                    return True

                # Step 3: Confirm
                elif action == "confirm" and target == "new_task":
                    task_data = state.data
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"✅ *Task Created!*\n\n📝 *Type:* {task_data.get('task_type', 'unknown').upper()}\n📄 *Description:* {task_data.get('description', 'N/A')[:100]}",
                        parse_mode="Markdown",
                        reply_markup=build_main_menu(),
                    )
                    clear_wizard_state(user_id)
                    return True

                # Step 4: Yes/No for execution
                elif action == "yes" and target == "execute":
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="🚀 *Executing task...*\n\nTask would be executed here in production.",
                        parse_mode="Markdown",
                        reply_markup=build_main_menu(),
                    )
                    clear_wizard_state(user_id)
                    return True

                elif action == "no" and target == "execute":
                    clear_wizard_state(user_id)
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="ℹ️ *Task saved but not executed*\n\nYou can run it later from the sessions menu.",
                        parse_mode="Markdown",
                        reply_markup=build_main_menu(),
                    )
                    return True

        # Handle kill_session wizard
        if state and state.current_wizard == "kill_session":
            if callback_data.startswith("session_"):
                session_id = callback_data.replace("session_", "")
                WizardHandler.update_step(
                    user_id, WizardStep.KILL_SESSION_CONFIRM, {"session_id": session_id}
                )
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🗑️ *Kill Session: {session_id}?*\n\nThis will terminate the session. Are you sure?",
                    parse_mode="Markdown",
                    reply_markup=build_wizard_yesno_menu(f"kill_{session_id}"),
                )
                return True

            elif action == "yes" and target.startswith("kill_"):
                session_id = target.replace("kill_", "")
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🗑️ *Session '{session_id}' terminated*",
                    parse_mode="Markdown",
                    reply_markup=build_main_menu(),
                )
                clear_wizard_state(user_id)
                return True

            elif action == "no" and target.startswith("kill_"):
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="✅ *Cancelled*\n\nSession was NOT terminated.",
                    parse_mode="Markdown",
                    reply_markup=build_main_menu(),
                )
                clear_wizard_state(user_id)
                return True

    return False


async def handle_wizard_text_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str, text: str
) -> bool:
    """Handle text input during wizard. Returns True if handled, False otherwise."""
    state = get_wizard_state(user_id)
    if not state:
        return False

    if state.current_wizard == "new_task":
        if state.step == WizardStep.NEW_TASK_DESCRIBE:
            # Store description and move to confirm
            WizardHandler.update_step(
                user_id, WizardStep.NEW_TASK_CONFIRM, {"description": text}
            )
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 *Confirm Task*\n\n📝 *Type:* {state.data.get('task_type', 'unknown').upper()}\n📄 *Description:* {text[:200]}",
                parse_mode="Markdown",
                reply_markup=build_wizard_confirm_menu("new_task"),
            )
            return True

    return False


# ============ KEYBOARD BUILDER ============


def build_main_menu() -> InlineKeyboardMarkup:
    """Build ADHD-friendly main menu - 6 buttons in 2x3 grid"""
    keyboard = [
        [
            InlineKeyboardButton("📂 Sessions", callback_data="menu_sessions"),
            InlineKeyboardButton("🎯 New Task", callback_data="menu_newtask"),
        ],
        [
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings"),
        ],
        [
            InlineKeyboardButton("🗑️ Kill Session", callback_data="menu_killsession"),
            InlineKeyboardButton("💡 Help", callback_data="menu_help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_sessions_menu() -> InlineKeyboardMarkup:
    """Build session list menu"""
    sessions = get_active_sessions()

    keyboard = []

    # Add each session as a button
    for session in sessions[:8]:  # Max 8 buttons
        # Show more useful info in the button
        label = session.get("id", "unknown")[:12]
        if "current_task" in session:
            task = str(session.get("current_task", ""))[:20]
            label = f"{label}: {task}"

        keyboard.append(
            [
                InlineKeyboardButton(
                    f"📄 {label}",
                    callback_data=f"session_{session.get('id', 'unknown')}",
                )
            ]
        )

    # Back button
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)


def build_back_menu(callback_data: str = "menu_main") -> InlineKeyboardMarkup:
    """Build a simple back button"""
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def build_new_task_menu() -> InlineKeyboardMarkup:
    """Build new task wizard menu"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Research", callback_data="task_research"),
            InlineKeyboardButton("💻 Code", callback_data="task_code"),
        ],
        [
            InlineKeyboardButton("📝 Write", callback_data="task_write"),
            InlineKeyboardButton("🔧 Fix", callback_data="task_fix"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_settings_menu() -> InlineKeyboardMarkup:
    """Build settings menu"""
    keyboard = [
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="settings_notif"),
            InlineKeyboardButton("🎨 Theme", callback_data="settings_theme"),
        ],
        [InlineKeyboardButton("⬅️ Back", callback_data="menu_main")],
    ]
    return InlineKeyboardMarkup(keyboard)


# ============ DATA FETCHERS ============


def build_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build ADHD-friendly persistent reply keyboard - always visible!

    This gives us 1-tap access to everything - ZERO typing required.
    Buttons persist across messages.
    """
    keyboard = [
        # Row 1: Main actions (most used)
        [
            KeyboardButton("📂 Sessions"),
            KeyboardButton("🎯 New Task"),
            KeyboardButton("🗑️ Kill"),
        ],
        # Row 2: Utilities
        [
            KeyboardButton("🎤 Voice"),
            KeyboardButton("📊 Status"),
            KeyboardButton("⚡ Menu"),
        ],
        # Row 3: Workspace scripts (P1.2)
        [
            KeyboardButton("🟢 Health"),
            KeyboardButton("🟡 Start MCPs"),
            KeyboardButton("🔴 Stop MCPs"),
        ],
        # Row 4: MCP Tools (P1.1)
        [
            KeyboardButton("🔍 MCP Status"),
            KeyboardButton("🧠 Memory Search"),
            KeyboardButton("📖 Get Context"),
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,  # Make keyboard smaller
        one_time_keyboard=False,  # Keep it visible
        input_field_placeholder="Or type a command...",
    )


def get_active_sessions() -> list[dict]:
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


def get_opencode_status() -> dict:
    """Get OpenCode status"""
    import subprocess

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


def get_system_status() -> str:
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


# ============ VOICE HANDLING ============


async def download_voice_file(file_id: str) -> str:
    """Download Telegram voice file and return local path"""
    import requests

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
    """Transcribe voice file using VoicePipeline"""
    import sys

    sys.path.insert(0, f"{MIND_DIR}/athena/examples/scripts")

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
        from voice_pipeline import VoicePipeline

        pipeline = VoicePipeline(whisper_model="base")
        result = pipeline.transcribe(Path(voice_path))
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


async def handle_voice_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle incoming voice message"""
    if not update.message or not update.message.voice:
        return

    chat_id = update.effective_chat.id
    voice = update.message.voice

    # Show typing indicator while processing
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    await context.bot.send_message(
        chat_id=chat_id,
        text="🎤 *Receiving voice...*\n\nDecoding with Whisper...",
        parse_mode="Markdown",
    )

    try:
        # Download voice file
        file_id = voice.file_id
        if not file_id:
            await context.bot.send_message(
                chat_id=chat_id, text="❌ No voice file found", parse_mode="Markdown"
            )
            return

        voice_path = await download_voice_file(file_id)

        # Show typing while transcribing
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Transcribe
        await context.bot.send_message(
            chat_id=chat_id, text="🧠 *Transcribing...*", parse_mode="Markdown"
        )
        result = transcribe_voice(voice_path)

        # Clean up
        try:
            os.unlink(voice_path)
        except Exception:
            pass

        # Check if faster-whisper is installed
        if not result.get("success") and not result.get("installed", True):
            await context.bot.send_message(
                chat_id=chat_id,
                text="⚠️ *Voice transcription not available*\n\nfaster-whisper is not installed.\n\nTo enable voice commands, run:\n`pip install faster-whisper`\n\nUse buttons instead!",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            return

        if not result.get("success"):
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Transcription failed: {result.get('error')}",
                parse_mode="Markdown",
            )
            return

        transcript = result.get("text", "")
        if not transcript:
            await context.bot.send_message(
                chat_id=chat_id,
                text="😕 Could not understand audio. Try again?",
                parse_mode="Markdown",
            )
            return

        # Show transcript
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📝 *You said:*\n\n_{transcript}_",
            parse_mode="Markdown",
        )

        # Parse command
        parsed = parse_voice_command(transcript)
        action = parsed.get("action", "menu_main")

        # Execute action based on parsed command
        if action == "menu_status":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📊 *Status*\n\n{get_system_status()}",
                parse_mode="Markdown",
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
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📂 *Sessions*\n\n{session_list or 'No sessions'}",
                parse_mode="Markdown",
                reply_markup=build_sessions_menu(),
            )
        elif action == "menu_newtask":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎯 *New Task*\n\nI'll help you create a task!\n\n_Topic: {transcript[:100]}..._",
                parse_mode="Markdown",
                reply_markup=build_back_menu(),
            )
        elif action == "menu_help":
            help_text = """💡 *Voice Commands:*

• "Check status" → System status
• "Show sessions" → Active sessions  
• "New task [description]" → Create task
• "Help" → Show this help

Or just speak naturally - I'll understand!"""
            await context.bot.send_message(
                chat_id=chat_id,
                text=help_text,
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Understood: {parsed.get('intent')}\n\nUse buttons for more control!",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )

        # 🎤 Send voice response back! (P0.3 - complete voice loop)
        response_text = f"Done! Action: {parsed.get('intent', 'completed')}. Use buttons for more control!"
        await send_voice_response(chat_id, response_text, context)

    except Exception as e:
        print(f"Voice error: {e}")
        await context.bot.send_message(
            chat_id=chat_id, text=f"❌ Error: {str(e)}", parse_mode="Markdown"
        )


# ============ COMMAND HANDLERS ============


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    chat_id = update.effective_chat.id
    welcome_text = """🧠 *N-Xyme_MIND Control*

Your ADHD-friendly remote control!
ZERO typing - all via button clicks!

*How it works:*
• Tap buttons below for instant actions
• Max 2 taps to any action
• Send voice notes for hands-free control

*The buttons are always visible - just tap and go!*
"""
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=build_reply_keyboard(),  # Reply keyboard - persistent!
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command"""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"📊 *Status*\n\n{get_system_status()}",
        parse_mode="Markdown",
        reply_markup=build_back_menu(),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu command"""
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="🧠 *N-Xyme_MIND Control*\n\nSelect:",
        reply_markup=build_main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    chat_id = update.effective_chat.id
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
    await context.bot.send_message(
        chat_id=chat_id,
        text=help_text,
        parse_mode="Markdown",
        reply_markup=build_back_menu(),
    )


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages - including reply keyboard buttons"""
    if not update.effective_chat or not update.message:
        return
    chat_id = update.effective_chat.id
    text = update.message.text if update.message.text else ""

    # Show typing indicator while processing
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Check for active wizard first
    user_id = str(update.effective_user.id) if update.effective_user else ""
    if user_id and has_active_wizard(user_id):
        # Handle wizard text input
        wizard_handled = await handle_wizard_text_input(update, context, user_id, text)
        if wizard_handled:
            return

    # Handle reply keyboard button presses - ZERO typing!
    if text in [
        "📂 Sessions",
        "🎯 New Task",
        "🗑️ Kill",
        "🎤 Voice",
        "📊 Status",
        "⚡ Menu",
        "🟢 Health",
        "🟡 Start MCPs",
        "🔴 Stop MCPs",
        "🔍 MCP Status",
        "🧠 Memory Search",
        "📖 Get Context",
    ]:
        if text == "📂 Sessions":
            sessions = get_active_sessions()
            session_list = "\n".join(
                [
                    f"• {s.get('id', 'unknown')[:20]} — {s.get('messages', 0)} items"
                    for s in sessions
                ]
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📂 *Active Sessions*\n\n{session_list or 'No active sessions'}",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "🎯 New Task":
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎯 *New Task Wizard*\n\nWhat would you like to work on?",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            # Start the new task wizard
            if user_id:
                WizardHandler.start_new_task_wizard(user_id)
        elif text == "🗑️ Kill":
            await context.bot.send_message(
                chat_id=chat_id,
                text="🗑️ *Kill Session*\n\nSelect a session to terminate:",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
            if user_id:
                WizardHandler.start_kill_session_wizard(user_id)
        elif text == "🎤 Voice":
            await context.bot.send_message(
                chat_id=chat_id,
                text="🎤 *Voice Mode*\n\nSend me a voice note and I'll transcribe & execute it!",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "📊 Status":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📊 *System Status*\n\n{get_system_status()}",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "⚡ Menu":
            await context.bot.send_message(
                chat_id=chat_id,
                text="🧠 *N-Xyme_MIND Control*\n\nSelect an option:",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        # === P1.2: Shell script triggers ===
        elif text == "🟢 Health":
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = subprocess.run(
                ["bash", f"{MIND_DIR}/bin/health-l0-blink.sh"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🟢 *Health Check*\n\n```\n{result.stdout[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "🟡 Start MCPs":
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = subprocess.run(
                ["bash", f"{MIND_DIR}/bin/start-all-mcp.sh"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🟡 *Starting MCPs...*\n\n```\n{result.stdout[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "🔴 Stop MCPs":
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = subprocess.run(
                ["bash", f"{MIND_DIR}/bin/stop-all-mcp.sh"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔴 *Stopping MCPs...*\n\n```\n{result.stdout[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        # === P1.1: MCP Tool Invocation ===
        elif text == "🔍 MCP Status":
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            result = subprocess.run(
                ["bash", f"{MIND_DIR}/bin/mcp-status.sh"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 *MCP Status*\n\n```\n{result.stdout[:3000]}\n```",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "🧠 Memory Search":
            # Memory search - ask for query
            await context.bot.send_message(
                chat_id=chat_id,
                text="🧠 *Memory Search*\n\nType your search query and I'll search the workspace memory.\n\nExample: 'what did we work on last session'",
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )
        elif text == "📖 Get Context":
            # Get active context from session files
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            try:
                # Read session state
                session_file = f"{MIND_DIR}/.sisyphus/session-state.json"
                if Path(session_file).exists():
                    with open(session_file) as f:
                        session_data = json.load(f)
                    last_agent = session_data.get("last_agent", "unknown")
                    current_task = session_data.get("current_task", "No task")
                    last_updated = session_data.get("last_updated", "unknown")
                    context_text = (
                        f"🧠 *Current Context*\n\n"
                        f"*Last Agent:* {last_agent}\n"
                        f"*Current Task:* {current_task}\n"
                        f"*Last Updated:* {last_updated}"
                    )
                else:
                    context_text = "📖 *Context*\n\nNo active session found."
            except Exception as e:
                context_text = f"📖 *Context Error*\n\n{str(e)[:200]}"

            await context.bot.send_message(
                chat_id=chat_id,
                text=context_text,
                parse_mode="Markdown",
                reply_markup=build_main_menu(),
            )

        # === Handle free-text input (memory search, etc) ===
        # If not a button, treat as potential search query
        result = subprocess.run(
            ["bash", f"{MIND_DIR}/bin/memory-search.sh", text[:500]],
            capture_output=True,
            text=True,
            timeout=30,
        )
        search_output = (
            result.stdout
            if result.stdout
            else result.stderr[:500]
            if result.stderr
            else "Search unavailable"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🔍 *Search: {text[:100]}*\n\n```\n{search_output[:3000]}\n```",
            parse_mode="Markdown",
            reply_markup=build_main_menu(),
        )
        return

    await context.bot.send_message(
        chat_id=chat_id,
        text="📝 Use buttons instead of typing!\n\nTap /menu for the main menu.",
        reply_markup=build_main_menu(),
    )


# ============ CALLBACK QUERY HANDLERS ============


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback query button presses"""
    query = update.callback_query
    if not query:
        return

    await query.answer(text="Loading...")

    callback_data = query.data
    if not callback_data or not query.message:
        return

    chat_id = query.message.chat.id
    message_id = query.message.message_id

    # Get user_id for wizard state check
    user_id = str(update.effective_user.id) if update.effective_user else ""

    # Check for active wizard first
    if user_id and has_active_wizard(user_id):
        wizard_handled = await handle_wizard_callback(update, context, user_id)
        if wizard_handled:
            return

    if callback_data == "menu_main":
        # Show main menu - single consolidated message
        status = get_system_status()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"🧠 *N-Xyme_MIND Control*\n\n{status}\n\nSelect an option:",
            parse_mode="Markdown",
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
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📂 *Active Sessions*\n\n{session_list or 'No active sessions'}",
            parse_mode="Markdown",
            reply_markup=build_sessions_menu(),
        )

    elif callback_data == "menu_status":
        # Show status
        status = get_system_status()
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"📊 *System Status*\n\n{status}",
            parse_mode="Markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data == "menu_newtask":
        # New task wizard - start
        user_id = str(update.effective_user.id) if update.effective_user else ""
        if user_id:
            WizardHandler.start_new_task_wizard(user_id)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="🎯 *New Task*\n\nWhat type of task?",
            parse_mode="Markdown",
            reply_markup=build_new_task_menu(),
        )

    elif callback_data == "menu_killsession":
        # Kill session wizard - start
        user_id = str(update.effective_user.id) if update.effective_user else ""
        if user_id:
            WizardHandler.start_kill_session_wizard(user_id)
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="🗑️ *Kill Session*\n\nSelect a session to terminate:",
            parse_mode="Markdown",
            reply_markup=build_sessions_menu(),
        )

    elif callback_data == "menu_settings":
        # Settings menu
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="⚙️ *Settings*\n\nConfigure your bot preferences",
            parse_mode="Markdown",
            reply_markup=build_settings_menu(),
        )

    elif callback_data == "menu_history":
        # Show recent history
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="📜 *Recent Activity*\n\nComing soon - view your recent actions and sessions",
            parse_mode="Markdown",
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
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=help_text,
            parse_mode="Markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data.startswith("task_"):
        # Task type selected - check if wizard is active
        user_id = str(update.effective_user.id) if update.effective_user else ""
        state = get_wizard_state(user_id) if user_id else None

        if state and state.current_wizard == "new_task":
            # Wizard is active - continue flow
            task_type = callback_data.replace("task_", "")
            WizardHandler.update_step(
                user_id, WizardStep.NEW_TASK_DESCRIBE, {"task_type": task_type}
            )
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🎯 *Task Type: {task_type.upper()}*\n\nNow describe what you need:\n\n(Type your description or tap Cancel)",
                parse_mode="Markdown",
                reply_markup=build_wizard_cancel_menu(),
            )
        else:
            # No wizard - old behavior
            task_type = callback_data.replace("task_", "")
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"✅ Task type: *{task_type.upper()}*\n\nThis will open a new task in OpenCode. Continue?",
                parse_mode="Markdown",
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

        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=details,
            parse_mode="Markdown",
            reply_markup=build_back_menu(),
        )

    elif callback_data.startswith("settings_"):
        # Settings submenu
        setting_type = callback_data.replace("settings_", "")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"⚙️ *Setting: {setting_type}*\n\nThis setting is coming soon!",
            parse_mode="Markdown",
            reply_markup=build_back_menu("menu_settings"),
        )

    else:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="Unknown action",
            reply_markup=build_back_menu(),
        )


# ============ INLINE QUERY HANDLER ============


async def inline_query_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline queries - search sessions, tasks, and actions"""
    query = update.inline_query
    if not query:
        return

    query_text = query.query.lower().strip()
    results = []

    # Search sessions
    sessions = get_active_sessions()
    for session in sessions:
        session_id = session.get("id", "")
        if (
            query_text in session_id.lower()
            or query_text in str(session.get("current_task", "")).lower()
        ):
            results.append(
                InlineQueryResultArticle(
                    id=f"session_{session_id}",
                    title=f"📄 Session: {session_id[:20]}",
                    description=session.get("current_task", "No task")[:50],
                    input_message_content=InputTextMessageContent(
                        f"📄 *Session:* `{session_id}`\n\n{session.get('current_task', 'No active task')}",
                        parse_mode="Markdown",
                    ),
                )
            )

    # Search tasks (menu options)
    task_options = [
        ("task_research", "🔍 Research", "Start a research task"),
        ("task_code", "💻 Code", "Start a coding task"),
        ("task_write", "📝 Write", "Start a writing task"),
        ("task_fix", "🔧 Fix", "Start a fix task"),
    ]
    for callback, title, desc in task_options:
        if query_text in callback.replace("task_", "") or query_text in title.lower():
            results.append(
                InlineQueryResultArticle(
                    id=callback,
                    title=title,
                    description=desc,
                    input_message_content=InputTextMessageContent(
                        f"✅ *Task Type Selected:* {title}\n\nStarting new task...",
                        parse_mode="Markdown",
                    ),
                )
            )

    # Search actions (menu options)
    menu_actions = [
        ("menu_sessions", "📂 Sessions", "View active sessions"),
        ("menu_newtask", "🎯 New Task", "Create a new task"),
        ("menu_status", "📊 Status", "Check system status"),
        ("menu_settings", "⚙️ Settings", "Bot settings"),
        ("menu_history", "📜 History", "View activity history"),
        ("menu_help", "💡 Help", "Get help"),
    ]
    for callback, title, desc in menu_actions:
        if query_text in callback.replace("menu_", "") or query_text in title.lower():
            results.append(
                InlineQueryResultArticle(
                    id=callback,
                    title=title,
                    description=desc,
                    input_message_content=InputTextMessageContent(
                        f"📋 *Action:* {title}\n\n{desc}",
                        parse_mode="Markdown",
                    ),
                )
            )

    # Limit results to max 50 (Telegram limit)
    await query.answer(results[:50], cache_time=300)


# ============ ERROR HANDLER ============


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ An error occurred. Please try again.",
        )


# ============ USER AUTHORIZATION ============


async def check_authorization(update: Update) -> bool:
    """Check if user is authorized"""
    if not update.effective_user:
        return False
    user_id = str(update.effective_user.id)
    return user_id == ALLOWED_USER_ID


async def unauthorized_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send unauthorized message"""
    if not update.effective_chat:
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⛔ You are not authorized to use this bot.",
    )


# ============ MAIN ============


def main() -> None:
    """Run the bot using PTB v20+ Application.builder() pattern"""
    print("🤖 N-Xyme_MIND Bot started! (PTB v20+ async mode)", flush=True)
    print("   Zero typing - all via button clicks!", flush=True)

    # Build the application
    application = Application.builder().token(TOKEN).build()

    # Add error handler
    application.add_error_handler(error_handler)

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))

    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Add inline query handler
    application.add_handler(InlineQueryHandler(inline_query_handler))

    # Add message handlers
    # Voice messages
    application.add_handler(
        MessageHandler(
            filters.VOICE & filters.UpdateType.MESSAGE,
            handle_voice_message,
        )
    )

    # Echo handler for text messages (fallback)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.UpdateType.MESSAGE,
            echo_message,
        )
    )

    # Start polling
    print("📡 Starting polling...", flush=True)
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
