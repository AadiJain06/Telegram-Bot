"""
Entry point — initializes the Telegram bot and starts polling.
"""

import logging
import sys

from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from bot.config import TELEGRAM_BOT_TOKEN, validate_config
from bot.handlers import (
    start_command,
    help_command,
    summary_command,
    deepdive_command,
    actionpoints_command,
    language_command,
    handle_message,
    error_handler,
)

# ── Logging Setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s",
    level=logging.INFO,
)
# Quiet down noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the bot."""
    # Validate configuration
    issues = validate_config()
    if issues:
        for issue in issues:
            logger.error("CONFIG ERROR: %s", issue)
        print("\n❌ Configuration errors found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\nPlease create a .env file (copy from .env.example) and fill in your API keys.")
        sys.exit(1)

    logger.info("Starting YouTube Summarizer Bot...")

    # Build application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("summary", summary_command))
    app.add_handler(CommandHandler("deepdive", deepdive_command))
    app.add_handler(CommandHandler("actionpoints", actionpoints_command))
    app.add_handler(CommandHandler("language", language_command))

    # Register message handler (catches all text messages)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    app.add_error_handler(error_handler)

    # Start polling
    logger.info("Bot is running! Press Ctrl+C to stop.")
    print("\n🤖 YouTube Summarizer Bot is running!")
    print("   Send /start to your bot in Telegram to begin.")
    print("   Press Ctrl+C to stop.\n")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
