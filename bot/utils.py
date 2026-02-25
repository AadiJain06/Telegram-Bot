"""
Shared utility helpers — formatting, validation, Telegram message splitting.
"""

import re
from typing import Optional


# ── YouTube URL Patterns ───────────────────────────────────────────────────────
_YT_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})"),
]


def extract_video_id(text: str) -> Optional[str]:
    """Extract a YouTube video ID from a message string. Returns None if not found."""
    for pattern in _YT_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def is_valid_youtube_url(text: str) -> bool:
    """Quick check whether text contains a YouTube URL."""
    return extract_video_id(text) is not None


def extract_youtube_url(text: str) -> Optional[str]:
    """Extract the full YouTube URL from text."""
    url_pattern = re.compile(
        r"(https?://(?:www\.)?(?:youtube\.com/watch\?[^\s]+|youtu\.be/[^\s]+|youtube\.com/shorts/[^\s]+))"
    )
    match = url_pattern.search(text)
    return match.group(1) if match else None


# ── Telegram Formatting ───────────────────────────────────────────────────────
TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """
    Split a long message into chunks that fit within Telegram's message limit.
    Tries to split on paragraph boundaries first, then on newlines.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break

        # Find a good split point
        split_at = text.rfind("\n\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind("\n", 0, max_length)
        if split_at == -1:
            split_at = text.rfind(" ", 0, max_length)
        if split_at == -1:
            split_at = max_length

        chunks.append(text[:split_at].rstrip())
        text = text[split_at:].lstrip()

    return chunks


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2, but preserve intentional formatting."""
    # Characters to escape in MarkdownV2
    special_chars = r"_[]()~`>#+-=|{}.!"
    escaped = ""
    i = 0
    while i < len(text):
        char = text[i]
        if char == "*" and i + 1 < len(text) and text[i + 1] == "*":
            # Bold — keep it
            escaped += "**"
            i += 2
            continue
        if char in special_chars:
            escaped += f"\\{char}"
        else:
            escaped += char
        i += 1
    return escaped


# ── Error Messages ─────────────────────────────────────────────────────────────
ERROR_INVALID_URL = (
    "❌ *That doesn't look like a valid YouTube URL.*\n\n"
    "Please send a link like:\n"
    "`https://youtube.com/watch?v=XXXXX`"
)

ERROR_NO_TRANSCRIPT = (
    "⚠️ *No transcript available for this video.*\n\n"
    "This might happen because:\n"
    "• The video has no captions/subtitles\n"
    "• Captions are disabled by the uploader\n"
    "• The video is a live stream or premiere\n\n"
    "Try a different video!"
)

ERROR_VIDEO_NOT_FOUND = (
    "❌ *Video not found.*\n\n"
    "The video may be private, deleted, or age-restricted.\n"
    "Please check the URL and try again."
)

ERROR_PROCESSING = (
    "⚙️ *Something went wrong while processing your request.*\n\n"
    "Please try again in a moment. If the issue persists, "
    "try a different video."
)

ERROR_RATE_LIMIT = (
    "⏳ *Too many requests!*\n\n"
    "Please wait a moment before sending another video.\n"
    "I'm still processing your previous request."
)

ERROR_NO_SESSION = (
    "💡 *No video loaded yet!*\n\n"
    "Send me a YouTube link first, and then you can ask questions about it."
)
