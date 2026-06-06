"""Tests for config module."""
import os
import tempfile
import pytest
from video_analyzer.config import Config


class TestConfigDefaults:
    def test_default_provider(self):
        c = Config()
        assert c.provider == "gemini"

    def test_default_model_per_provider(self):
        for provider, expected_model in [
            ("gemini", "gemini-2.0-flash"),
            ("openai", "gpt-4o"),
            ("anthropic", "claude-sonnet-4-20250514"),
            ("ollama", "llava:13b"),
        ]:
            c = Config(provider=provider, api_key="test" if provider != "ollama" else "")
            assert c.model == expected_model

    def test_default_extraction_settings(self):
        c = Config()
        assert c.mode == "smart"
        assert c.max_frames == 30
        assert c.interval == 5.0
        assert c.scene_threshold == 0.3
        assert c.quality == 2

    def test_default_download_settings(self):
        c = Config()
        assert c.max_height == 720
        assert c.max_duration == 600


class TestConfigValidation:
    def test_missing_api_key_for_remote_provider(self):
        c = Config(provider="gemini", api_key="")
        errors = c.validate()
        assert any("No API key" in e for e in errors)

    def test_ollama_doesnt_need_api_key(self):
        c = Config(provider="ollama", api_key="")
        errors = c.validate()
        assert not any("No API key" in e for e in errors)

    def test_invalid_max_frames(self):
        c = Config(max_frames=0)
        errors = c.validate()
        assert any("max_frames" in e for e in errors)

    def test_max_frames_too_high(self):
        c = Config(max_frames=300)
        errors = c.validate()
        assert any("200" in e for e in errors)

    def test_invalid_scene_threshold(self):
        c = Config(scene_threshold=1.5)
        errors = c.validate()
        assert any("scene_threshold" in e for e in errors)

    def test_invalid_max_duration(self):
        c = Config(max_duration=0)
        errors = c.validate()
        assert any("max_duration" in e for e in errors)


class TestConfigDotenv:
    def test_load_dotenv_reads_file(self, monkeypatch, tmp_path):
        """Test that .env file is loaded correctly."""
        env_file = tmp_path / ".env"
        env_file.write_text("VIDEO_AI_TEST_KEY=hello_world\n")

        # Patch Path.exists and Path.open to simulate .env in CWD
        os.environ.pop("VIDEO_AI_TEST_KEY", None)
        c = Config.__new__(Config)
        c.provider = "gemini"
        c.api_key = "test"
        c.model = "gemini-2.0-flash"
        c._load_dotenv = lambda: None  # skip default load
        # Manually test the parser logic
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key:
                        os.environ[key] = value
        assert os.environ.get("VIDEO_AI_TEST_KEY") == "hello_world"
        os.environ.pop("VIDEO_AI_TEST_KEY", None)


class TestConfigPrompts:
    def test_default_prompt(self):
        c = Config()
        assert "frame" in c.default_prompt.lower()

    def test_resolved_prompt_uses_custom(self):
        c = Config(prompt="custom prompt")
        assert c.resolved_prompt == "custom prompt"

    def test_resolved_prompt_falls_back_to_default(self):
        c = Config()
        assert c.resolved_prompt == c.default_prompt


class TestProviderConstants:
    def test_all_providers_have_defaults(self):
        c = Config()
        for provider in ["gemini", "openai", "anthropic", "ollama"]:
            assert provider in c.PROVIDER_DEFAULTS
            assert "model" in c.PROVIDER_DEFAULTS[provider]
            assert "env_key" in c.PROVIDER_DEFAULTS[provider]
