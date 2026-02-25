"""
YouTube transcript retrieval with caching and error handling.
"""

import logging
import time
from typing import Optional

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from bot.config import MAX_TRANSCRIPT_CHARS, TRANSCRIPT_CACHE_TTL_SECONDS
from bot.utils import format_timestamp

logger = logging.getLogger(__name__)


# ── Transcript Cache ───────────────────────────────────────────────────────────
_transcript_cache: dict[str, dict] = {}


def _cache_get(video_id: str) -> Optional[dict]:
    """Retrieve cached transcript if still valid."""
    entry = _transcript_cache.get(video_id)
    if entry and (time.time() - entry["cached_at"]) < TRANSCRIPT_CACHE_TTL_SECONDS:
        logger.info("Cache hit for video %s", video_id)
        return entry
    if entry:
        del _transcript_cache[video_id]
    return None


def _cache_set(video_id: str, data: dict) -> None:
    """Store transcript data in cache."""
    data["cached_at"] = time.time()
    _transcript_cache[video_id] = data


# ── Video Info ─────────────────────────────────────────────────────────────────
def get_video_info(video_id: str) -> dict:
    """
    Get basic video metadata.
    Uses pytubefix to fetch title, author, duration.
    Falls back to defaults if the library fails.
    """
    info = {
        "video_id": video_id,
        "title": "Unknown Title",
        "author": "Unknown Channel",
        "duration_seconds": 0,
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }
    try:
        from pytubefix import YouTube

        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        info["title"] = yt.title or info["title"]
        info["author"] = yt.author or info["author"]
        info["duration_seconds"] = yt.length or 0
    except Exception as e:
        logger.warning("Could not fetch video metadata for %s: %s", video_id, e)
    return info


# ── Transcript Fetching ───────────────────────────────────────────────────────
class TranscriptError(Exception):
    """Custom exception for transcript retrieval issues."""

    def __init__(self, message: str, error_type: str = "generic"):
        super().__init__(message)
        self.error_type = error_type  # "disabled", "not_found", "unavailable", "generic"


def get_transcript(video_id: str) -> dict:
    """
    Fetch the transcript for a YouTube video.

    Returns dict with keys:
        - transcript_text: str  (full plain text)
        - segments: list[dict]  (with 'text', 'start', 'duration')
        - language: str
        - is_auto_generated: bool

    Raises TranscriptError on failure.
    """
    # Check cache first
    cached = _cache_get(video_id)
    if cached:
        return cached

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    except TranscriptsDisabled:
        raise TranscriptError(
            "Transcripts are disabled for this video.", error_type="disabled"
        )
    except VideoUnavailable:
        raise TranscriptError(
            "Video is unavailable.", error_type="unavailable"
        )
    except Exception as e:
        logger.error("Error listing transcripts for %s: %s", video_id, e)
        raise TranscriptError(f"Could not access video: {e}", error_type="generic")

    # Priority: manual English → auto English → any manual → any auto
    transcript = None
    lang = "en"
    is_auto = False

    try:
        transcript = transcript_list.find_transcript(["en"])
        lang = "en"
        is_auto = transcript.is_generated
    except NoTranscriptFound:
        try:
            transcript = transcript_list.find_generated_transcript(["en"])
            lang = "en"
            is_auto = True
        except NoTranscriptFound:
            # Try any available transcript
            try:
                for t in transcript_list:
                    transcript = t
                    lang = t.language_code
                    is_auto = t.is_generated
                    break
            except Exception:
                pass

    if transcript is None:
        raise TranscriptError(
            "No transcript found for this video.", error_type="not_found"
        )

    try:
        segments = transcript.fetch()
    except Exception as e:
        logger.error("Error fetching transcript for %s: %s", video_id, e)
        raise TranscriptError(f"Failed to fetch transcript: {e}", error_type="generic")

    # Build plain text with timestamps
    transcript_lines = []
    for seg in segments:
        ts = format_timestamp(seg.get("start", 0))
        text = seg.get("text", "").strip()
        if text:
            transcript_lines.append(f"[{ts}] {text}")

    full_text = "\n".join(transcript_lines)

    # Truncate if too long to fit in LLM context
    if len(full_text) > MAX_TRANSCRIPT_CHARS:
        full_text = full_text[:MAX_TRANSCRIPT_CHARS] + "\n\n[... transcript truncated due to length ...]"
        logger.info("Transcript for %s truncated to %d chars", video_id, MAX_TRANSCRIPT_CHARS)

    result = {
        "transcript_text": full_text,
        "segments": [dict(s) for s in segments],
        "language": lang,
        "is_auto_generated": is_auto,
    }

    _cache_set(video_id, result)
    return result
