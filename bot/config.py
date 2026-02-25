"""
Application configuration — loads environment variables and exposes settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Required API Keys ──────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Gemini Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_MAX_OUTPUT_TOKENS = 4096

# ── Transcript Settings ───────────────────────────────────────────────────────
MAX_TRANSCRIPT_CHARS = 80_000          # ~20k tokens — fits in Gemini context
TRANSCRIPT_CACHE_TTL_SECONDS = 3600    # 1 hour
CHUNK_SIZE_CHARS = 15_000              # for chunked processing of long transcripts

# ── Session Settings ───────────────────────────────────────────────────────────
SESSION_TTL_SECONDS = 7200             # 2 hours
MAX_CHAT_HISTORY = 10                  # keep last N Q&A turns per user

# ── Supported Languages ───────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "english": "English",
    "hindi": "हिन्दी (Hindi)",
    "kannada": "ಕನ್ನಡ (Kannada)",
    "tamil": "தமிழ் (Tamil)",
    "telugu": "తెలుగు (Telugu)",
    "marathi": "मराठी (Marathi)",
}
DEFAULT_LANGUAGE = "english"


def validate_config() -> list[str]:
    """Return a list of missing configuration issues."""
    issues = []
    if not TELEGRAM_BOT_TOKEN:
        issues.append("TELEGRAM_BOT_TOKEN is not set in .env")
    if not GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY is not set in .env")
    return issues
