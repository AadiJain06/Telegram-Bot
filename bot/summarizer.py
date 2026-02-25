"""
LLM-powered summarization using Google Gemini.
Produces structured summaries with key points, timestamps, and takeaways.
"""

import logging
from typing import Optional

import google.generativeai as genai

from bot.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_OUTPUT_TOKENS, CHUNK_SIZE_CHARS
from bot.language import get_language_instruction

logger = logging.getLogger(__name__)

# ── Configure Gemini ───────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)

_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config=genai.GenerationConfig(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        temperature=0.3,  # lower for factual, structured output
    ),
)


# ── Summary Prompt Templates ──────────────────────────────────────────────────
_SUMMARY_PROMPT = """You are an expert video content analyst. Analyze the following YouTube video transcript and generate a clear, structured summary.

**Video Title:** {title}
**Channel:** {author}
**Duration:** {duration}

**TRANSCRIPT:**
{transcript}

---

**Instructions:**
1. Provide exactly 5 key points from the video, each as a concise bullet point.
2. List 3-5 important timestamps with brief descriptions of what happens at that point.
3. Write a single "Core Takeaway" sentence that captures the essence of the video.
4. Keep the summary concise but meaningful — no paragraph dumps.

{language_instruction}

**Format your response EXACTLY like this:**

🎥 **{title}**
👤 {author} | ⏱️ {duration}

📌 **5 Key Points**
1. [Key point 1]
2. [Key point 2]
3. [Key point 3]
4. [Key point 4]
5. [Key point 5]

⏱️ **Important Timestamps**
• [MM:SS] — [What happens]
• [MM:SS] — [What happens]
• [MM:SS] — [What happens]

🧠 **Core Takeaway**
[One sentence capturing the essence of the video]"""


_DEEPDIVE_PROMPT = """You are an expert video analyst. Provide a detailed, section-by-section breakdown of this YouTube video.

**Video Title:** {title}
**Channel:** {author}
**Duration:** {duration}

**TRANSCRIPT:**
{transcript}

---

**Instructions:**
1. Divide the video into logical sections based on topic changes.
2. For each section, provide:
   - A descriptive title
   - Timestamp range
   - Detailed summary of what's discussed
   - Key quotes or data points mentioned
3. Be thorough but organized.

{language_instruction}

**Format your response with clear section headers and bullet points.**"""


_ACTIONPOINTS_PROMPT = """You are an expert at extracting actionable insights from content. Analyze this YouTube video transcript and extract every actionable item.

**Video Title:** {title}
**Channel:** {author}

**TRANSCRIPT:**
{transcript}

---

**Instructions:**
1. Extract all actionable items, tips, recommendations, or steps mentioned in the video.
2. Categorize them if possible (e.g., "Immediate Actions", "Long-term Strategies", "Resources Mentioned").
3. Each action point should be specific and actionable, not vague.
4. If the video doesn't contain actionable items, say so clearly.

{language_instruction}

**Format your response as:**

✅ **Action Points from: {title}**

🔥 **Immediate Actions**
• [Action 1]
• [Action 2]

📋 **Key Recommendations**
• [Recommendation 1]
• [Recommendation 2]

📚 **Resources Mentioned**
• [Resource 1]
• [Resource 2]"""


# ── Summarization Functions ───────────────────────────────────────────────────
def _format_duration(seconds: int) -> str:
    """Format duration in human-readable form."""
    if seconds <= 0:
        return "Unknown duration"
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m {secs}s"


async def generate_summary(
    transcript_text: str,
    video_info: dict,
    language: str = "english",
) -> str:
    """
    Generate a structured summary of the video.
    Handles long transcripts by chunking if needed.
    """
    duration = _format_duration(video_info.get("duration_seconds", 0))
    lang_instruction = get_language_instruction(language)

    # If transcript is short enough, process directly
    if len(transcript_text) <= CHUNK_SIZE_CHARS * 2:
        prompt = _SUMMARY_PROMPT.format(
            title=video_info.get("title", "Unknown"),
            author=video_info.get("author", "Unknown"),
            duration=duration,
            transcript=transcript_text,
            language_instruction=lang_instruction,
        )
        return await _call_gemini(prompt)

    # For very long transcripts, chunk and summarize
    return await _chunked_summary(transcript_text, video_info, language)


async def generate_deep_dive(
    transcript_text: str,
    video_info: dict,
    language: str = "english",
) -> str:
    """Generate a detailed section-by-section analysis."""
    duration = _format_duration(video_info.get("duration_seconds", 0))
    lang_instruction = get_language_instruction(language)

    prompt = _DEEPDIVE_PROMPT.format(
        title=video_info.get("title", "Unknown"),
        author=video_info.get("author", "Unknown"),
        duration=duration,
        transcript=transcript_text,
        language_instruction=lang_instruction,
    )
    return await _call_gemini(prompt)


async def generate_action_points(
    transcript_text: str,
    video_info: dict,
    language: str = "english",
) -> str:
    """Extract actionable items from the video."""
    lang_instruction = get_language_instruction(language)

    prompt = _ACTIONPOINTS_PROMPT.format(
        title=video_info.get("title", "Unknown"),
        author=video_info.get("author", "Unknown"),
        transcript=transcript_text,
        language_instruction=lang_instruction,
    )
    return await _call_gemini(prompt)


# ── Chunked Processing ────────────────────────────────────────────────────────
async def _chunked_summary(
    transcript_text: str,
    video_info: dict,
    language: str,
) -> str:
    """Summarize a long transcript by chunking, summarizing parts, then merging."""
    chunks = _split_transcript(transcript_text, CHUNK_SIZE_CHARS)
    logger.info("Processing %d transcript chunks", len(chunks))

    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = (
            f"Summarize this section (part {i + 1}/{len(chunks)}) of a video transcript. "
            f"Extract key points and notable timestamps.\n\n"
            f"TRANSCRIPT SECTION:\n{chunk}"
        )
        summary = await _call_gemini(prompt)
        chunk_summaries.append(summary)

    # Merge chunk summaries into final summary
    merged = "\n\n---\n\n".join(chunk_summaries)
    duration = _format_duration(video_info.get("duration_seconds", 0))
    lang_instruction = get_language_instruction(language)

    merge_prompt = _SUMMARY_PROMPT.format(
        title=video_info.get("title", "Unknown"),
        author=video_info.get("author", "Unknown"),
        duration=duration,
        transcript=f"[SECTION SUMMARIES FROM LONG VIDEO]\n\n{merged}",
        language_instruction=lang_instruction,
    )
    return await _call_gemini(merge_prompt)


def _split_transcript(text: str, chunk_size: int) -> list[str]:
    """Split transcript into chunks, preferring paragraph boundaries."""
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    while text:
        if len(text) <= chunk_size:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, chunk_size)
        if split_at == -1 or split_at < chunk_size // 2:
            split_at = chunk_size
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
    return chunks


# ── Gemini API Call ────────────────────────────────────────────────────────────
async def _call_gemini(prompt: str) -> str:
    """Make an async call to Gemini and return the response text."""
    try:
        response = await _model.generate_content_async(prompt)
        if response and response.text:
            return response.text.strip()
        logger.warning("Empty response from Gemini")
        return "⚠️ The AI model returned an empty response. Please try again."
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise RuntimeError(f"AI processing failed: {e}")
