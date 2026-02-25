"""
Per-user session management — stores transcript context for follow-up Q&A.
Thread-safe via asyncio (single-threaded event loop).
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from bot.config import SESSION_TTL_SECONDS, MAX_CHAT_HISTORY, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """Holds context for one user's active video session."""

    user_id: int
    video_id: str
    video_info: dict
    transcript_text: str
    transcript_language: str
    summary: str = ""
    language: str = DEFAULT_LANGUAGE
    chat_history: list[dict] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    is_processing: bool = False

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def add_chat_turn(self, question: str, answer: str) -> None:
        """Add a Q&A turn to history, trimming old entries if needed."""
        self.chat_history.append({"role": "user", "content": question})
        self.chat_history.append({"role": "assistant", "content": answer})
        # Keep only the last N turns (N*2 messages)
        max_messages = MAX_CHAT_HISTORY * 2
        if len(self.chat_history) > max_messages:
            self.chat_history = self.chat_history[-max_messages:]
        self.touch()

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return (time.time() - self.last_activity) > SESSION_TTL_SECONDS


# ── Session Store ──────────────────────────────────────────────────────────────
_sessions: dict[int, UserSession] = {}


def get_session(user_id: int) -> Optional[UserSession]:
    """Retrieve a user's active session, or None if expired/missing."""
    session = _sessions.get(user_id)
    if session is None:
        return None
    if session.is_expired():
        logger.info("Session expired for user %d", user_id)
        del _sessions[user_id]
        return None
    session.touch()
    return session


def create_session(
    user_id: int,
    video_id: str,
    video_info: dict,
    transcript_text: str,
    transcript_language: str,
) -> UserSession:
    """Create (or replace) a session for a user."""
    session = UserSession(
        user_id=user_id,
        video_id=video_id,
        video_info=video_info,
        transcript_text=transcript_text,
        transcript_language=transcript_language,
    )
    _sessions[user_id] = session
    logger.info("Created session for user %d, video %s", user_id, video_id)
    return session


def set_session_language(user_id: int, language: str) -> bool:
    """Set preferred language for a user's session. Returns False if no session."""
    session = get_session(user_id)
    if session is None:
        return False
    session.language = language
    return True


def set_session_summary(user_id: int, summary: str) -> None:
    """Store the generated summary in the user's session."""
    session = get_session(user_id)
    if session:
        session.summary = summary


def cleanup_expired_sessions() -> int:
    """Remove all expired sessions. Returns count of removed sessions."""
    expired = [uid for uid, s in _sessions.items() if s.is_expired()]
    for uid in expired:
        del _sessions[uid]
    if expired:
        logger.info("Cleaned up %d expired sessions", len(expired))
    return len(expired)
