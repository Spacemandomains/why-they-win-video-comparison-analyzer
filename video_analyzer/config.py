"""Configuration management — loads from env, .env file, or CLI args."""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    """Unified configuration for all providers and settings."""

    # Provider settings
    provider: str = "gemini"
    api_key: str = ""
    model: Optional[str] = None
    base_url: Optional[str] = None

    # Extraction settings
    mode: str = "smart"
    max_frames: int = 30
    interval: float = 5.0
    scene_threshold: float = 0.3
    quality: int = 2

    # Download settings
    max_height: int = 720
    max_duration: int = 600

    # Analysis settings
    context_window: int = 3
    delay: float = 1.0
    prompt: Optional[str] = None
    summarize: bool = True
    chapters: bool = False

    # Audio settings
    transcribe: bool = False
    whisper_model: str = "base"
    whisper_language: Optional[str] = None

    # Output settings
    output: Optional[str] = None
    keep_frames: bool = False

    # Provider defaults
    PROVIDER_DEFAULTS: dict = field(default_factory=lambda: {
        "gemini": {"model": "gemini-2.0-flash", "env_key": "GEMINI_API_KEY"},
        "openai": {"model": "gpt-4o", "env_key": "OPENAI_API_KEY"},
        "anthropic": {"model": "claude-sonnet-4-20250514", "env_key": "ANTHROPIC_API_KEY"},
        "ollama": {"model": "llava:13b", "env_key": ""},
        "custom": {"model": "default", "env_key": "CUSTOM_API_KEY"},
    })

    def __post_init__(self):
        # Load .env if exists
        self._load_dotenv()

        # Auto-detect API key from env if not set
        if not self.api_key:
            defaults = self.PROVIDER_DEFAULTS.get(self.provider, {})
            env_key = defaults.get("env_key", "")
            if env_key:
                self.api_key = os.environ.get(env_key, "")

        # Set default model if not specified
        if not self.model:
            defaults = self.PROVIDER_DEFAULTS.get(self.provider, {})
            self.model = defaults.get("model", "default")

    def _load_dotenv(self):
        """Load .env file if exists."""
        for env_path in [Path(".env"), Path.home() / ".env"]:
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            if key and key not in os.environ:
                                os.environ[key] = value
                break

    def validate(self) -> list[str]:
        """Validate config, return list of errors."""
        errors = []
        if self.provider not in ("ollama",) and not self.api_key:
            env_key = self.PROVIDER_DEFAULTS.get(self.provider, {}).get("env_key", "")
            errors.append(
                f"No API key for {self.provider}. "
                f"Set {env_key} env variable, use --api-key, or add to .env file."
            )
        if self.max_frames < 1:
            errors.append("max_frames must be >= 1")
        if self.max_frames > 200:
            errors.append("max_frames > 200 will be very slow and expensive")
        if self.scene_threshold < 0 or self.scene_threshold > 1:
            errors.append("scene_threshold must be between 0.0 and 1.0")
        if self.max_duration < 1:
            errors.append("max_duration must be >= 1 second")
        return errors

    @property
    def default_prompt(self) -> str:
        return (
            "Describe what's happening in this frame in detail. "
            "Include: people, objects, text on screen, actions, setting, mood. "
            "Be specific and concise."
        )

    @property
    def resolved_prompt(self) -> str:
        return self.prompt or self.default_prompt
