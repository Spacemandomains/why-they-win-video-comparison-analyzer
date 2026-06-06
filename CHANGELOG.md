# Changelog

## [2.0.0] - 2026-06-07

### Added
- **Multi-provider support**: Gemini, OpenAI (GPT-4o), Anthropic (Claude), Ollama (local)
- **Audio transcription**: Whisper integration (tiny/base/small/medium/large models)
- **Smart scene detection**: ffmpeg scene-change filter for intelligent frame selection
- **Both mode**: Combines scene detection + uniform sampling for best coverage
- **Rolling context memory**: Frame analyses include context from previous frames
- **Chapter detection**: AI-powered video chapter/section detection
- **Custom prompts**: Override default analysis prompt via --prompt
- **.env file support**: Auto-loads API keys from .env file
- **providers command**: Check which providers are configured and ready
- **Config module**: Centralized configuration with validation
- **Docker support**: Dockerfile + docker-compose.yml
- **CI/CD**: GitHub Actions with pytest on Python 3.10/3.11/3.12
- **Tests**: 50+ unit tests covering all modules
- **Demo output**: Example JSON output for reference

### Changed
- Complete rewrite of analyzer with provider abstraction
- Improved error messages with actionable install instructions
- Better frame deduplication algorithm
- Progress callbacks during batch analysis

### Fixed
- Scene detection fallback when too few scenes found
- FPS parsing for fractional frame rates (e.g., 29.97)
- Empty audio track detection

## [1.0.0] - 2026-06-07

### Added
- Initial release
- YouTube/TikTok/Twitter video download via yt-dlp
- Frame extraction (scene detection + uniform)
- Gemini vision analysis
- Video summarization
- CLI with analyze/extract/ask commands
