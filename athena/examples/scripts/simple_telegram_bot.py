#!/usr/bin/env python3
"""
Simple Telegram Bot - NXopencode Remote Control
Minimal version that works standalone.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID")

# Debug: print what was loaded
env_path = Path(__file__).parent / ".env"
print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] TOKEN loaded: {'Yes' if TOKEN else 'No'}")
print(f"[DEBUG] ALLOWED_USER_ID loaded: {ALLOWED_USER_ID}")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command."""
    user_id = str(update.effective_user.id)
    logger.info(f"📡 Incoming from ID: {user_id}")

    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(f"⛔ Access Denied. Your ID: {user_id}")
        return

    await update.message.reply_text(
        "🔥 NXopencode Bot Online!\n\n"
        "Available commands:\n"
        "/start - Start session\n"
        "/status - Check status\n"
        "/search <query> - Search the web\n"
        "/log <note> - Save a note\n"
        "/end - End session\n\n"
        "Or just chat normally!"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command."""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(f"⛔ Access Denied. Your ID: {user_id}")
        return

    await update.message.reply_text("✅ Bot is running. System operational.")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo handler - simulates AI response."""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(f"⛔ Access Denied. Your ID: {user_id}")
        return

    # Simple echo for now - placeholder for AI integration
    await update.message.reply_text(
        f"📝 Received: {update.message.text}\n\n🤖 AI integration coming soon!"
    )


async def log_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log a note."""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(f"⛔ Access Denied. Your ID: {user_id}")
        return

    note = " ".join(context.args)
    if not note:
        await update.message.reply_text("Usage: /log <note>")
        return

    # Save to file
    log_file = Path(__file__).parent / "telegram_notes.md"
    with open(log_file, "a") as f:
        f.write(f"- {note}\n")

    await update.message.reply_text(f"✅ Note saved: {note}")


async def search_web(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search the web."""
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER_ID:
        await update.message.reply_text(f"⛔ Access Denied. Your ID: {user_id}")
        return

    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("Usage: /search <query>")
        return

    await update.message.reply_text(
        f"🔍 Searching for: {query}\n\n⏳ AI-powered search coming soon!"
    )


def main():
    """Run the bot."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    if not ALLOWED_USER_ID:
        logger.warning("TELEGRAM_ALLOWED_USER_ID not set - allowing all users")

    logger.info(f"Starting bot with token: {TOKEN[:20]}...")
    logger.info(f"Allowed user: {ALLOWED_USER_ID}")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("log", log_note))
    app.add_handler(CommandHandler("search", search_web))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("🤖 Bot starting... Polling for messages!")
    app.run_polling()


if __name__ == "__main__":
    main()
