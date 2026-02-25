"""
Context-aware Q&A engine — answers user questions grounded in the video transcript.
Prevents hallucination by constraining answers to transcript content.
"""

import logging

import google.generativeai as genai

from bot.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_OUTPUT_TOKENS
from bot.language import get_language_instruction

logger = logging.getLogger(__name__)

# ── Configure Gemini ───────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)

_qa_model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config=genai.GenerationConfig(
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        temperature=0.2,  # very low for factual Q&A
    ),
    system_instruction=(
        "You are a helpful AI assistant that answers questions about YouTube videos. "
        "You MUST only answer based on the provided video transcript. "
        "If the answer cannot be found in the transcript, you MUST respond with:\n"
        "'ℹ️ This topic is not covered in the video.'\n"
        "Never make up information. Never hallucinate. "
        "If you're unsure, say so. Always be concise and clear. "
        "When possible, reference timestamps from the transcript."
    ),
)


# ── Q&A Function ──────────────────────────────────────────────────────────────
async def answer_question(
    question: str,
    transcript_text: str,
    video_info: dict,
    chat_history: list[dict],
    language: str = "english",
) -> str:
    """
    Answer a user's question about the video, grounded in the transcript.

    Args:
        question: The user's question
        transcript_text: Full transcript text
        video_info: Video metadata dict
        chat_history: Previous Q&A turns for context
        language: Target response language

    Returns:
        The answer string
    """
    lang_instruction = get_language_instruction(language)

    # Build context from chat history
    history_text = ""
    if chat_history:
        history_lines = []
        for msg in chat_history[-6:]:  # last 3 Q&A turns for context
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content']}")
        history_text = "\n".join(history_lines)

    prompt = f"""**VIDEO CONTEXT**
Title: {video_info.get('title', 'Unknown')}
Channel: {video_info.get('author', 'Unknown')}

**TRANSCRIPT:**
{transcript_text}

"""
    if history_text:
        prompt += f"""**PREVIOUS CONVERSATION:**
{history_text}

"""
    prompt += f"""**USER QUESTION:**
{question}

**Instructions:**
- Answer ONLY based on the transcript above.
- If the information is not in the transcript, respond with: "ℹ️ This topic is not covered in the video."
- Reference timestamps when relevant (e.g., "At [05:23], the speaker mentions...").
- Be concise and direct.
- {lang_instruction}"""

    try:
        response = await _qa_model.generate_content_async(prompt)
        if response and response.text:
            return response.text.strip()
        return "⚠️ I couldn't generate an answer. Please try rephrasing your question."
    except Exception as e:
        logger.error("Q&A Gemini error: %s", e)
        return "⚠️ Something went wrong while processing your question. Please try again."
