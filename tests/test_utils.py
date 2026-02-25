"""
Unit tests for utility functions.
"""

import pytest
from bot.utils import extract_video_id, is_valid_youtube_url, split_message, format_timestamp
from bot.language import detect_language_request, get_language_instruction


# ── extract_video_id Tests ─────────────────────────────────────────────────────
class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120") == "dQw4w9WgXcQ"

    def test_url_in_message(self):
        assert extract_video_id("Check this out https://youtu.be/dQw4w9WgXcQ cool right?") == "dQw4w9WgXcQ"

    def test_no_protocol(self):
        assert extract_video_id("youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        assert extract_video_id("https://google.com") is None

    def test_empty_string(self):
        assert extract_video_id("") is None

    def test_random_text(self):
        assert extract_video_id("hello world") is None

    def test_partial_url(self):
        assert extract_video_id("youtube.com/watch") is None


# ── is_valid_youtube_url Tests ─────────────────────────────────────────────────
class TestIsValidYoutubeUrl:
    def test_valid(self):
        assert is_valid_youtube_url("https://youtube.com/watch?v=abc12345678") is True

    def test_invalid(self):
        assert is_valid_youtube_url("not a url") is False


# ── format_timestamp Tests ─────────────────────────────────────────────────────
class TestFormatTimestamp:
    def test_seconds_only(self):
        assert format_timestamp(45) == "00:45"

    def test_minutes(self):
        assert format_timestamp(125) == "02:05"

    def test_hours(self):
        assert format_timestamp(3661) == "01:01:01"

    def test_zero(self):
        assert format_timestamp(0) == "00:00"


# ── split_message Tests ───────────────────────────────────────────────────────
class TestSplitMessage:
    def test_short_message(self):
        assert split_message("hello") == ["hello"]

    def test_exact_limit(self):
        msg = "x" * 4096
        assert split_message(msg) == [msg]

    def test_long_message(self):
        msg = "word " * 2000  # ~10000 chars
        chunks = split_message(msg, max_length=4096)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 4096


# ── detect_language_request Tests ──────────────────────────────────────────────
class TestDetectLanguageRequest:
    def test_summarize_in_hindi(self):
        assert detect_language_request("summarize in hindi") == "hindi"

    def test_explain_in_kannada(self):
        assert detect_language_request("explain in kannada") == "kannada"

    def test_respond_in_tamil(self):
        assert detect_language_request("respond in tamil") == "tamil"

    def test_no_language(self):
        assert detect_language_request("what is the price?") is None

    def test_unsupported_language(self):
        assert detect_language_request("summarize in french") is None

    def test_just_language_name(self):
        assert detect_language_request("hindi") == "hindi"


# ── get_language_instruction Tests ─────────────────────────────────────────────
class TestGetLanguageInstruction:
    def test_english(self):
        result = get_language_instruction("english")
        assert "English" in result

    def test_hindi(self):
        result = get_language_instruction("hindi")
        assert "Hindi" in result or "हिन्दी" in result
