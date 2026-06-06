"""Tests for CLI module."""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from video_analyzer.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestCLIBasic:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Video AI Analyzer" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "2.0.0" in result.output

    def test_providers_command(self, runner):
        result = runner.invoke(main, ["providers"])
        assert result.exit_code == 0
        assert "gemini" in result.output
        assert "openai" in result.output
        assert "anthropic" in result.output
        assert "ollama" in result.output


class TestAnalyzeCommand:
    def test_missing_dependencies(self, runner):
        with patch("video_analyzer.downloader.check_dependencies", return_value={
            "yt-dlp": False, "ffmpeg": False, "ffprobe": False
        }):
            result = runner.invoke(main, ["analyze", "https://youtube.com/watch?v=test"])
            assert result.exit_code == 1

    def test_no_api_key(self, runner):
        with patch("video_analyzer.downloader.check_dependencies", return_value={
            "yt-dlp": True, "ffmpeg": True, "ffprobe": True
        }):
            with patch.dict("os.environ", {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
                result = runner.invoke(main, ["analyze", "https://youtube.com/watch?v=test", "--provider", "gemini"])
                assert result.exit_code == 1


class TestExtractCommand:
    def test_nonexistent_video(self, runner):
        result = runner.invoke(main, ["extract", "/nonexistent/video.mp4"])
        assert result.exit_code != 0


class TestAskCommand:
    def test_no_api_key(self, runner):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            result = runner.invoke(main, ["ask", "--provider", "gemini", "nonexistent.jpg"])
            assert result.exit_code != 0
