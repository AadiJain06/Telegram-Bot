"""
Telegram bot command and message handlers.
Routes user interactions to the appropriate processing pipelines.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils import (
    extract_video_id,
    split_message,
    ERROR_INVALID_URL,
    ERROR_NO_TRANSCRIPT,
    ERROR_VIDEO_NOT_FOUND,
    ERROR_PROCESSING,
    ERROR_RATE_LIMIT,
    ERROR_NO_SESSION,
)
from bot.youtube import get_video_info, get_transcript, TranscriptError
from bot.summarizer import generate_summary, generate_deep_dive, generate_action_points
from bot.qa import answer_question
from bot.session import (
    get_session,
    create_session,
    set_session_language,
    set_session_summary,
    cleanup_expired_sessions,
)
from bot.language import (
    detect_language_request,
    get_language_display_name,
    get_supported_languages_text,
)

logger = logging.getLogger(__name__)


# ── Welcome & Help ─────────────────────────────────────────────────────────────
WELCOME_MSG = """🤖 *Welcome to YouTube Summarizer Bot!*

I'm your personal AI research assistant for YouTube videos. Here's what I can do:

📎 *Send me a YouTube link* — I'll generate a structured summary
❓ *Ask follow-up questions* — I'll answer based on the video content
🌐 *Multi-language support* — Request summaries in Hindi, Kannada, Tamil, and more!

*Commands:*
/help — Show this help message
/summary — Re-display last summary
/deepdive — Detailed section-by-section analysis
/actionpoints — Extract actionable items
/language — Change response language

Just paste a YouTube link to get started! 🚀"""

HELP_MSG = """📚 *YouTube Summarizer Bot — Help*

*How to use:*
1️⃣ Send a YouTube link → Get a structured summary
2️⃣ Ask questions → Get answers grounded in the video
3️⃣ Change language → Say "summarize in Hindi" or use /language

*Commands:*
• /start — Welcome message
• /help — This help message
• /summary — Re-display the last summary
• /deepdive — Detailed breakdown of the video
• /actionpoints — Extract action items & tips
• /language `<lang>` — Set response language

*Supported Languages:*
{languages}

*Tips:*
• I can handle follow-up questions about the video
• Say "explain in Hindi" to switch language mid-conversation
• If a topic isn't in the video, I'll tell you honestly

*Edge Cases:*
• Videos without captions/subtitles can't be summarized
• Very long videos are processed in chunks
• Private or age-restricted videos can't be accessed"""


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    await update.message.reply_text(WELCOME_MSG, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    languages = get_supported_languages_text()
    msg = HELP_MSG.format(languages=languages)
    await update.message.reply_text(msg, parse_mode="Markdown")


# ── Video Processing ──────────────────────────────────────────────────────────
async def handle_youtube_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process a YouTube link — fetch transcript and generate summary."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Check if user is already being processed
    session = get_session(user_id)
    if session and session.is_processing:
        await update.message.reply_text(ERROR_RATE_LIMIT, parse_mode="Markdown")
        return

    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text(ERROR_INVALID_URL, parse_mode="Markdown")
        return

    # Send "processing" indicator
    processing_msg = await update.message.reply_text(
        "⏳ *Processing your video...*\n\n"
        "🔍 Fetching transcript...",
        parse_mode="Markdown",
    )

    try:
        # Step 1: Get video info
        video_info = get_video_info(video_id)

        await processing_msg.edit_text(
            f"⏳ *Processing:* {video_info.get('title', 'Unknown')}\n\n"
            f"📝 Fetching transcript...",
            parse_mode="Markdown",
        )

        # Step 2: Get transcript
        try:
            transcript_data = get_transcript(video_id)
        except TranscriptError as e:
            error_msg = {
                "disabled": ERROR_NO_TRANSCRIPT,
                "not_found": ERROR_NO_TRANSCRIPT,
                "unavailable": ERROR_VIDEO_NOT_FOUND,
            }.get(e.error_type, ERROR_PROCESSING)
            await processing_msg.edit_text(error_msg, parse_mode="Markdown")
            return

        # Step 3: Create session
        session = create_session(
            user_id=user_id,
            video_id=video_id,
            video_info=video_info,
            transcript_text=transcript_data["transcript_text"],
            transcript_language=transcript_data.get("language", "en"),
        )

        # Check if user requested a language in the same message
        lang_request = detect_language_request(text)
        if lang_request:
            session.language = lang_request

        session.is_processing = True

        await processing_msg.edit_text(
            f"⏳ *Processing:* {video_info.get('title', 'Unknown')}\n\n"
            f"🤖 Generating summary...",
            parse_mode="Markdown",
        )

        # Step 4: Generate summary
        summary = await generate_summary(
            transcript_text=transcript_data["transcript_text"],
            video_info=video_info,
            language=session.language,
        )

        session.is_processing = False
        set_session_summary(user_id, summary)

        # Step 5: Send summary
        await processing_msg.delete()

        for chunk in split_message(summary):
            await update.message.reply_text(chunk, parse_mode="Markdown")

        # Follow-up hint
        await update.message.reply_text(
            "💬 *You can now ask me questions about this video!*\n"
            "Or try /deepdive for a detailed analysis, or /actionpoints for action items.",
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.error("Error processing video %s: %s", video_id, e, exc_info=True)
        if session:
            session.is_processing = False
        try:
            await processing_msg.edit_text(ERROR_PROCESSING, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(ERROR_PROCESSING, parse_mode="Markdown")


# ── Q&A Handler ────────────────────────────────────────────────────────────────
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a follow-up question about the loaded video."""
    user_id = update.effective_user.id
    question = update.message.text.strip()

    session = get_session(user_id)
    if not session:
        await update.message.reply_text(ERROR_NO_SESSION, parse_mode="Markdown")
        return

    if session.is_processing:
        await update.message.reply_text(ERROR_RATE_LIMIT, parse_mode="Markdown")
        return

    # Check for language switch request
    lang_request = detect_language_request(question)
    if lang_request:
        session.language = lang_request
        display_name = get_language_display_name(lang_request)

        # If it's just a language switch, re-generate summary
        if len(question.split()) <= 4:
            session.is_processing = True
            processing_msg = await update.message.reply_text(
                f"🌐 Switching to *{display_name}*...\nRegenerating summary...",
                parse_mode="Markdown",
            )
            try:
                summary = await generate_summary(
                    transcript_text=session.transcript_text,
                    video_info=session.video_info,
                    language=session.language,
                )
                set_session_summary(user_id, summary)
                session.is_processing = False
                await processing_msg.delete()
                for chunk in split_message(summary):
                    await update.message.reply_text(chunk, parse_mode="Markdown")
                return
            except Exception as e:
                session.is_processing = False
                logger.error("Error regenerating summary: %s", e)
                await processing_msg.edit_text(ERROR_PROCESSING, parse_mode="Markdown")
                return

    # Regular Q&A
    session.is_processing = True
    typing_msg = await update.message.reply_text("🤔 *Thinking...*", parse_mode="Markdown")

    try:
        answer = await answer_question(
            question=question,
            transcript_text=session.transcript_text,
            video_info=session.video_info,
            chat_history=session.chat_history,
            language=session.language,
        )

        session.add_chat_turn(question, answer)
        session.is_processing = False

        await typing_msg.delete()
        for chunk in split_message(answer):
            await update.message.reply_text(chunk, parse_mode="Markdown")

    except Exception as e:
        session.is_processing = False
        logger.error("Error answering question: %s", e, exc_info=True)
        try:
            await typing_msg.edit_text(ERROR_PROCESSING, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(ERROR_PROCESSING, parse_mode="Markdown")


# ── Bonus Commands ─────────────────────────────────────────────────────────────
async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /summary — re-display the last summary."""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session or not session.summary:
        await update.message.reply_text(ERROR_NO_SESSION, parse_mode="Markdown")
        return

    for chunk in split_message(session.summary):
        await update.message.reply_text(chunk, parse_mode="Markdown")


async def deepdive_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /deepdive — detailed section-by-section analysis."""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session:
        await update.message.reply_text(ERROR_NO_SESSION, parse_mode="Markdown")
        return

    if session.is_processing:
        await update.message.reply_text(ERROR_RATE_LIMIT, parse_mode="Markdown")
        return

    session.is_processing = True
    processing_msg = await update.message.reply_text(
        "🔬 *Generating deep dive analysis...*", parse_mode="Markdown"
    )

    try:
        analysis = await generate_deep_dive(
            transcript_text=session.transcript_text,
            video_info=session.video_info,
            language=session.language,
        )
        session.is_processing = False
        await processing_msg.delete()
        for chunk in split_message(analysis):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        session.is_processing = False
        logger.error("Error generating deep dive: %s", e)
        await processing_msg.edit_text(ERROR_PROCESSING, parse_mode="Markdown")


async def actionpoints_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /actionpoints — extract actionable items."""
    user_id = update.effective_user.id
    session = get_session(user_id)

    if not session:
        await update.message.reply_text(ERROR_NO_SESSION, parse_mode="Markdown")
        return

    if session.is_processing:
        await update.message.reply_text(ERROR_RATE_LIMIT, parse_mode="Markdown")
        return

    session.is_processing = True
    processing_msg = await update.message.reply_text(
        "✅ *Extracting action points...*", parse_mode="Markdown"
    )

    try:
        actions = await generate_action_points(
            transcript_text=session.transcript_text,
            video_info=session.video_info,
            language=session.language,
        )
        session.is_processing = False
        await processing_msg.delete()
        for chunk in split_message(actions):
            await update.message.reply_text(chunk, parse_mode="Markdown")
    except Exception as e:
        session.is_processing = False
        logger.error("Error generating action points: %s", e)
        await processing_msg.edit_text(ERROR_PROCESSING, parse_mode="Markdown")


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /language <lang> — set response language."""
    user_id = update.effective_user.id
    args = context.args

    if not args:
        languages = get_supported_languages_text()
        await update.message.reply_text(
            f"🌐 *Set your preferred language*\n\n"
            f"Usage: `/language hindi`\n\n"
            f"*Supported languages:*\n{languages}",
            parse_mode="Markdown",
        )
        return

    lang_key = args[0].lower()
    from bot.config import SUPPORTED_LANGUAGES

    if lang_key not in SUPPORTED_LANGUAGES:
        languages = get_supported_languages_text()
        await update.message.reply_text(
            f"❌ Language `{args[0]}` is not supported.\n\n"
            f"*Supported languages:*\n{languages}",
            parse_mode="Markdown",
        )
        return

    session = get_session(user_id)
    if session:
        session.language = lang_key
        display_name = get_language_display_name(lang_key)
        await update.message.reply_text(
            f"✅ Language set to *{display_name}*.\n"
            f"Future responses will be in {display_name}.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"✅ Language preference noted: *{get_language_display_name(lang_key)}*.\n"
            f"Send a YouTube link to get started!",
            parse_mode="Markdown",
        )


# ── Main Message Router ───────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main message router — determines if a message is a YouTube link or a question.
    """
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # Periodic cleanup of expired sessions
    cleanup_expired_sessions()

    # Check if it contains a YouTube URL
    if extract_video_id(text):
        await handle_youtube_link(update, context)
    else:
        await handle_question(update, context)


# ── Error Handler ──────────────────────────────────────────────────────────────
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global error handler for the bot."""
    logger.error("Update %s caused error: %s", update, context.error, exc_info=context.error)
    if update and update.message:
        await update.message.reply_text(ERROR_PROCESSING, parse_mode="Markdown")
