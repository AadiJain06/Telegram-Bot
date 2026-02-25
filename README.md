# 🤖 YouTube Summarizer & Q&A Telegram Bot

A smart Telegram bot that acts as your personal AI research assistant for YouTube videos. Send a YouTube link and get structured summaries, ask follow-up questions, and consume content in your preferred language.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?logo=telegram)
![Gemini](https://img.shields.io/badge/Google-Gemini-orange?logo=google)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📝 **Structured Summaries** | 5 key points, timestamps, and core takeaway |
| ❓ **Context-Aware Q&A** | Ask follow-up questions grounded in the video transcript |
| 🌐 **Multi-Language** | English, Hindi, Kannada, Tamil, Telugu, Marathi |
| 🔬 **Deep Dive** | Section-by-section detailed analysis |
| ✅ **Action Points** | Extract actionable items and recommendations |
| 💾 **Smart Caching** | Transcript caching with TTL to reduce API calls |
| 🛡️ **Error Handling** | Graceful handling of invalid URLs, missing transcripts, rate limiting |
| 👥 **Multi-User** | Concurrent session management with auto-cleanup |

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Telegram   │────▶│   Bot Handlers   │────▶│  YouTube API    │
│    User      │◀────│   (handlers.py)  │     │  (youtube.py)   │
└─────────────┘     └──────┬───────────┘     └────────┬────────┘
                           │                          │
                    ┌──────▼───────────┐     ┌────────▼────────┐
                    │ Session Manager  │     │ Transcript Cache │
                    │  (session.py)    │     │  (in-memory TTL) │
                    └──────┬───────────┘     └─────────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼────┐ ┌─────▼──────┐
       │ Summarizer  │ │  Q&A  │ │  Language   │
       │(summarizer) │ │(qa.py)│ │(language.py)│
       └──────┬──────┘ └──┬────┘ └────────────┘
              │            │
        ┌─────▼────────────▼─────┐
        │   Google Gemini API    │
        │   (gemini-2.0-flash)   │
        └────────────────────────┘
```

### Design Decisions & Trade-Offs

| Decision | Rationale |
|----------|-----------|
| **Standalone Python bot** (not OpenClaw) | Full control over transcript processing, session management, caching logic, and error handling. Better alignment with evaluation criteria. |
| **Google Gemini Flash** | Free tier with generous limits. Low latency. Excellent multilingual support for Indian languages. |
| **In-memory caching** | Simple, fast, no external dependencies. Trade-off: cache lost on restart. For production, swap to Redis. |
| **In-memory sessions** | Sufficient for bot-scale workloads. No database overhead. Trade-off: sessions lost on restart. |
| **youtube-transcript-api** | Reliable, no API key needed. Falls back through manual → auto-generated → any language transcripts. |
| **Chunked processing** | Long videos (>30 min) are split into chunks, each summarized, then merged into a final summary. |
| **Low temperature (0.2-0.3)** | Prioritizes factual accuracy over creativity. Critical for Q&A grounding. |
| **Anti-hallucination prompt** | System instruction explicitly forbids making up information not in the transcript. |

---

## 🚀 Setup

### Prerequisites

- Python 3.10+
- A Telegram account
- A Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/youtube-summarizer-bot.git
cd youtube-summarizer-bot
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Create Your Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token provided by BotFather

### Step 5: Configure Environment

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

Edit `.env` and fill in your keys:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 6: Run the Bot

```bash
python -m bot.main
```

You should see:
```
🤖 YouTube Summarizer Bot is running!
   Send /start to your bot in Telegram to begin.
```

---

## 📱 Usage

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and getting started |
| `/help` | Full help with all features |
| `/summary` | Re-display the last generated summary |
| `/deepdive` | Detailed section-by-section analysis |
| `/actionpoints` | Extract actionable items from the video |
| `/language <lang>` | Set response language (e.g., `/language hindi`) |

### Example Interactions

**Step 1 — Send a YouTube Link:**
```
User: https://youtube.com/watch?v=dQw4w9WgXcQ

Bot:
🎥 Never Gonna Give You Up - Rick Astley
👤 Rick Astley | ⏱️ 3m 33s

📌 5 Key Points
1. The song is about unwavering commitment...
2. ...

⏱️ Important Timestamps
• [00:00] — Intro with iconic drum beat
• [00:18] — First verse begins
• ...

🧠 Core Takeaway
A classic love song about absolute loyalty and devotion.
```

**Step 2 — Ask a Follow-up Question:**
```
User: What instruments are used?

Bot: Based on the video, the track features a prominent drum machine,
     synthesizers, and bass guitar. At [00:00], the iconic drum intro...
```

**Step 3 — Switch Language:**
```
User: Summarize in Hindi

Bot:
🎥 Never Gonna Give You Up - Rick Astley
📌 5 मुख्य बिंदु
1. यह गाना अटूट प्रतिबद्धता के बारे में है...
...
```

---

## 🛡️ Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| Invalid YouTube URL | Clear error message with correct format example |
| No transcript available | Explains possible reasons (disabled captions, live stream) |
| Private/deleted video | Informs user to check the URL |
| Very long video (>1hr) | Chunks transcript, summarizes parts, merges results |
| Non-English transcript | Falls back to any available language |
| Rate limiting | Prevents concurrent processing per user |
| Telegram 4096 char limit | Auto-splits long messages |
| Q&A about uncovered topic | Responds with "This topic is not covered" |

---

## 📁 Project Structure

```
Bot/
├── .env.example          # Environment variable template
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── bot/
│   ├── __init__.py       # Package init
│   ├── main.py           # Entry point — bot initialization
│   ├── config.py         # Configuration loading
│   ├── handlers.py       # Telegram command & message handlers
│   ├── youtube.py        # YouTube transcript fetching + caching
│   ├── summarizer.py     # LLM-powered summarization
│   ├── qa.py             # Context-aware Q&A engine
│   ├── session.py        # Per-user session management
│   ├── language.py       # Multi-language support
│   └── utils.py          # Utilities (formatting, validation)
└── tests/
    └── test_utils.py     # Unit tests for utility functions
```

---

## 🔧 Configuration

All settings are in `bot/config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model to use |
| `MAX_TRANSCRIPT_CHARS` | 80,000 | Max transcript length before truncation |
| `TRANSCRIPT_CACHE_TTL_SECONDS` | 3600 | Transcript cache lifetime (1 hour) |
| `SESSION_TTL_SECONDS` | 7200 | User session lifetime (2 hours) |
| `MAX_CHAT_HISTORY` | 10 | Q&A turns kept per session |
| `CHUNK_SIZE_CHARS` | 15,000 | Chunk size for long transcript processing |

---

## 🧪 Running Tests

```bash
python -m pytest tests/ -v
```

---

## 📊 Token Efficiency

The bot optimizes token usage through:
- **Transcript caching**: Same video = zero re-fetching
- **Low temperature**: Shorter, more focused responses
- **Chunked Q&A context**: Only recent chat history sent to LLM
- **Gemini Flash model**: High speed, lower cost per token

---

## 📜 License

MIT License — feel free to use and modify.
