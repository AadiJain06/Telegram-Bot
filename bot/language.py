"""
Language detection and multi-language support.
"""

import re
from typing import Optional

from bot.config import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE


# ── Language Detection Patterns ────────────────────────────────────────────────
_LANGUAGE_PATTERNS = [
    # "summarize in Hindi", "explain in Kannada", "respond in Tamil"
    re.compile(
        r"(?:summarize|summary|explain|respond|answer|translate|write|give|tell)\s+"
        r"(?:(?:it|this|me|the\s+summary|the\s+answer)\s+)?in\s+(\w+)",
        re.IGNORECASE,
    ),
    # "in Hindi please", "in Tamil"
    re.compile(r"\bin\s+(\w+)\s*(?:please|pls)?\s*$", re.IGNORECASE),
    # "Hindi mein", "Hindi me"  (informal requests)
    re.compile(r"(\w+)\s+(?:mein|me|mẽ)\b", re.IGNORECASE),
    # Just the language name as the entire message
    re.compile(r"^(\w+)$", re.IGNORECASE),
]


def detect_language_request(text: str) -> Optional[str]:
    """
    Detect if the user is requesting a specific language.
    Returns the language key (e.g., 'hindi') or None.
    """
    text = text.strip()

    for pattern in _LANGUAGE_PATTERNS:
        match = pattern.search(text)
        if match:
            word = match.group(1).lower()
            if word in SUPPORTED_LANGUAGES:
                return word
    return None


def get_language_display_name(lang_key: str) -> str:
    """Get the display name for a language key."""
    return SUPPORTED_LANGUAGES.get(lang_key, lang_key.title())


def get_language_instruction(lang_key: str) -> str:
    """
    Build a prompt instruction for generating content in the specified language.
    """
    if lang_key == DEFAULT_LANGUAGE:
        return "Respond in English."

    display = get_language_display_name(lang_key)
    return (
        f"Respond entirely in {display}. "
        f"Use the {display} script/alphabet. "
        f"Keep technical terms or proper nouns in their original form if needed."
    )


def get_supported_languages_text() -> str:
    """Format supported languages for display."""
    lines = []
    for key, display in SUPPORTED_LANGUAGES.items():
        marker = " ✅ (default)" if key == DEFAULT_LANGUAGE else ""
        lines.append(f"  • `{key}` — {display}{marker}")
    return "\n".join(lines)
