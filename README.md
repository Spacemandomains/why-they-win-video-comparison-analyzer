# 🎬 Video AI Analyzer

**AI-powered video understanding** — Download any video, extract key frames, transcribe audio, and analyze with vision AI.

Works with **YouTube, TikTok, Twitter/X, Instagram**, and 1000+ sites.

Supports **Gemini, OpenAI GPT-4o, Anthropic Claude**, and **Ollama (local)**.

## Features

- 🎥 **Smart Frame Extraction** — Scene-change detection + uniform sampling
- 🧠 **Multi-Provider AI** — Gemini, OpenAI, Anthropic, Ollama (local, free)
- 🎙️ **Audio Transcription** — Whisper integration (4 languages supported)
- 📑 **Chapter Detection** — AI identifies video sections automatically
- 🧩 **Rolling Context** — Frame analyses include previous frame context
- 📝 **Video Summarization** — Coherent summary from frame-by-frame analysis
- 🐳 **Docker Ready** — One-command setup with Dockerfile

## Quick Start

### Prerequisites

**ffmpeg** is required (system dependency):

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### Install

```bash
# Basic install (core features only)
pip install .

# Install with specific provider
pip install ".[gemini]"     # Google Gemini
pip install ".[openai]"     # OpenAI GPT-4o
pip install ".[anthropic]"  # Anthropic Claude
pip install ".[ollama]"     # Ollama (local, free)
pip install ".[whisper]"    # Audio transcription

# Install everything
pip install ".[all]"
```

### Setup API Key

```bash
# Option 1: Environment variable
export GEMINI_API_KEY=*** Option 2: .env file (auto-loaded)
echo 'GEMINI_API_KEY=sk-...' > .env

# Option 3: CLI flag
video-ai analyze URL --api-key sk-...
```

### Get Free API Keys

| Provider | Free Tier | Link |
|----------|-----------|------|
| Gemini | 15 RPM, 1M tokens/day | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| OpenAI | Pay-per-use | [platform.openai.com](https://platform.openai.com/api-keys) |
| Anthropic | Pay-per-use | [console.anthropic.com](https://console.anthropic.com/) |
| Ollama | **100% Free** (local) | [ollama.com](https://ollama.com) |

## Usage

### Analyze a Video (Full Pipeline)

```bash
# YouTube video with Gemini (default)
video-ai analyze "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# With OpenAI GPT-4o
video-ai analyze URL --provider openai

# With local Ollama (free, no API key)
video-ai analyze URL --provider ollama

# With audio transcription + chapter detection
video-ai analyze URL --transcribe --chapters

# Custom prompt
video-ai analyze URL --prompt "Focus on the code being written"

# Save results to JSON
video-ai analyze URL --output results.json
```

### Extract Frames Only

```bash
# Smart extraction (scene detection)
video-ai extract video.mp4

# Uniform extraction (every 3 seconds)
video-ai extract video.mp4 --mode uniform --interval 3

# Both modes combined
video-ai extract video.mp4 --mode both --max-frames 50
```

### Transcribe Audio

```bash
# Basic transcription
video-ai transcribe video.mp4

# Use larger model for better accuracy
video-ai transcribe video.mp4 --model medium

# Indonesian language
video-ai transcribe video.mp4 --language id

# Save transcript
video-ai transcribe video.mp4 --output transcript.json
```

### Analyze Single Image

```bash
# Describe an image
video-ai ask screenshot.png

# Custom prompt
video-ai ask photo.jpg --prompt "What's the mood of this photo?"

# Multiple images
video-ai ask img1.jpg img2.jpg img3.jpg --prompt "Compare these"
```

### Check Provider Status

```bash
video-ai providers
```

## Docker

```bash
# Build
docker build -t video-ai .

# Run (pass API key as env)
docker run --rm -e GEMINI_API_KEY=$GEMINI_API_KEY video-ai analyze "URL"

# With docker-compose
export GEMINI_API_KEY=your_key
docker compose run video-ai analyze "URL"
```

## Programmatic Usage

```python
from video_analyzer.downloader import download_video
from video_analyzer.extractor import extract_frames
from video_analyzer.analyzer import VisionAnalyzer, summarize_frames
from video_analyzer.transcriber import transcribe_video

# 1. Download
info = download_video("https://youtube.com/watch?v=...")

# 2. Extract frames
frames = extract_frames(info["path"], mode="smart", max_frames=20)

# 3. Analyze with AI
analyzer = VisionAnalyzer(provider="gemini", api_key="your-key")
results = analyzer.analyze_batch(frames, "Describe each frame")

# 4. Generate summary
summary = summarize_frames(results, analyzer)

# 5. Transcribe audio (optional)
transcript = transcribe_video(info["path"], model_size="base")
```

## CLI Reference

```
video-ai analyze URL    # Full pipeline: download → extract → analyze
video-ai extract FILE   # Extract frames only (no AI)
video-ai transcribe FILE # Transcribe audio with Whisper
video-ai ask IMAGES...   # Analyze single/multiple images
video-ai providers       # Show provider status
```

### Common Options

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | gemini | AI provider: gemini, openai, anthropic, ollama |
| `--api-key` | env | API key (or set env variable) |
| `--model` | auto | Model name (uses provider default) |
| `--max-frames` | 30 | Maximum frames to extract |
| `--mode` | smart | Extraction: smart, uniform, both |
| `--output` | none | Save results to JSON file |
| `--transcribe` | off | Enable Whisper audio transcription |
| `--chapters` | off | Detect video chapters |
| `--summarize` | on | Generate video summary |
| `--prompt` | auto | Custom analysis prompt |

## Example Output

See [examples/demo_output.json](examples/demo_output.json) for a full analysis result.

## Architecture

```
video_analyzer/
├── __init__.py       # Package metadata (__version__)
├── config.py         # Unified configuration + .env loading
├── downloader.py     # yt-dlp video download + ffprobe metadata
├── extractor.py      # Frame extraction (scene detect + uniform)
├── analyzer.py       # Multi-provider vision AI (Gemini/OpenAI/Anthropic/Ollama)
├── transcriber.py    # Whisper audio transcription
└── cli.py            # Click CLI with Rich output
```

## Requirements

- **Python**: 3.10+
- **ffmpeg**: System dependency (install via apt/brew/pacman)
- **yt-dlp**: Video download (auto-installed)
- **API Key**: At least one provider (or Ollama for fully local/free)

## Contributing

```bash
git clone https://github.com/0xN404T/video-ai-analyzer.git
cd video-ai-analyzer
pip install -e ".[dev]"
pytest tests/ -v
```

## License

MIT License — see [LICENSE](LICENSE)

---

**Built by [0xN404T](https://github.com/0xN404T)**
