# 🎬 Video AI Analyzer

> AI-powered video understanding — extract frames with ffmpeg, analyze with vision LLMs. Runs on any VPS, no GPU needed.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## ✨ Features

- **Smart Frame Extraction** — Scene-change detection via ffmpeg, not just random sampling
- **Vision AI Analysis** — Gemini (free) or OpenAI for frame-by-frame understanding
- **Context Memory** — Rolling context window so AI understands video flow
- **Auto Summary** — Coherent video summary from all frame analyses
- **Chapter Detection** — AI identifies distinct sections/topics
- **1000+ Sites** — YouTube, TikTok, Twitter/X, Instagram, Reddit, and more via yt-dlp
- **Lightweight** — No GPU required, runs on any VPS with 1GB+ RAM
- **CLI + Python API** — Use from command line or import in your code

## 🚀 Quick Start

```bash
# Install
pip install -e .

# Set API key (Gemini is free!)
export GEMINI_API_KEY="your-key-here"

# Analyze a YouTube video
video-ai analyze "https://youtube.com/watch?v=xxxxx"

# With chapters
video-ai analyze "https://youtube.com/watch?v=xxxxx" --chapters

# Custom prompt
video-ai analyze "https://youtube.com/watch?v=xxxxx" --prompt "Explain this tutorial step by step"

# Save results to JSON
video-ai analyze "https://youtube.com/watch?v=xxxxx" -o results.json
```

## 📖 Usage

### Analyze Video
```bash
video-ai analyze <URL> [options]

Options:
  -p, --provider [gemini|openai]    Vision LLM provider (default: gemini)
  -k, --api-key TEXT                API key (or set GEMINI_API_KEY)
  -m, --model TEXT                  Model name
  --mode [smart|uniform|both]       Frame extraction mode (default: smart)
  -n, --max-frames INT              Max frames to extract (default: 30)
  -i, --interval FLOAT              Seconds between frames (uniform mode)
  --scene-threshold FLOAT           Scene detection sensitivity (0.0-1.0)
  --max-height INT                  Max video resolution (default: 720)
  --max-duration INT                Max video length in seconds (default: 600)
  --prompt TEXT                     Custom analysis prompt
  --summarize/--no-summarize        Generate summary (default: yes)
  --chapters/--no-chapters          Detect chapters (default: no)
  -o, --output FILE                 Save results to JSON file
  --keep-frames                     Keep extracted frames
```

### Extract Frames Only
```bash
video-ai extract <video_file> --mode smart --max-frames 20 -o ./frames/
```

### Ask About Images
```bash
video-ai ask image1.jpg image2.png --prompt "What's happening here?"
```

### Python API
```python
from video_analyzer.downloader import download_video
from video_analyzer.extractor import extract_frames
from video_analyzer.analyzer import VisionAnalyzer, summarize_frames

# Download
video = download_video("https://youtube.com/watch?v=xxxxx")

# Extract frames (scene detection)
frames = extract_frames(video["path"], mode="smart", max_frames=20)

# Analyze with Gemini
analyzer = VisionAnalyzer(provider="gemini", api_key="your-key")
results = analyzer.analyze_batch(frames, "Describe what's happening")

# Generate summary
summary = summarize_frames(results, provider="gemini", api_key="your-key")
print(summary)
```

## 🔧 Frame Extraction Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `smart` | Scene-change detection | Movies, vlogs, presentations |
| `uniform` | Fixed interval | Slow-paced content, lectures |
| `both` | Combined + dedup | Maximum coverage |

## 🆓 Free Tier

**Gemini API** (recommended):
- Free tier: 15 requests/minute, 1M tokens/day
- Perfect for video analysis
- Get key: [Google AI Studio](https://aistudio.google.com/apikey)

**OpenAI**:
- Pay-per-use (~$0.01-0.03 per image)
- Better for complex visual understanding

## 📁 Project Structure

```
video-ai-analyzer/
├── video_analyzer/
│   ├── __init__.py
│   ├── cli.py          # Click CLI interface
│   ├── downloader.py   # yt-dlp video downloader
│   ├── extractor.py    # ffmpeg frame extraction
│   └── analyzer.py     # Vision LLM integration
├── tests/
├── docs/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

PRs welcome! Some ideas:
- Add Whisper for audio transcription
- Support subtitle extraction
- Add more vision providers (Claude, local models)
- Frame deduplication with perceptual hashing
- Real-time video stream analysis

## 📄 License

MIT — do whatever you want with it.
