"""Tests for analyzer module."""
import pytest
from unittest.mock import patch, MagicMock
from video_analyzer.analyzer import (
    VisionAnalyzer,
    summarize_frames,
    detect_chapters,
    _image_to_base64,
)


class TestVisionAnalyzerInit:
    def test_invalid_provider(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            VisionAnalyzer(provider="invalid_provider", api_key="test")

    def test_supported_providers(self):
        for p in ["gemini", "openai", "anthropic", "ollama"]:
            assert p in VisionAnalyzer.SUPPORTED_PROVIDERS

    @patch("video_analyzer.analyzer.genai", create=True)
    def test_gemini_init(self, mock_genai):
        """Test Gemini provider initialization."""
        pytest.importorskip("google.generativeai")


class TestImageToBase64:
    def test_encodes_image(self, tmp_path):
        from PIL import Image
        img_path = str(tmp_path / "test.jpg")
        Image.new("RGB", (10, 10), color="red").save(img_path)
        result = _image_to_base64(img_path)
        assert isinstance(result, str)
        assert len(result) > 0
        import base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0

    def test_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            _image_to_base64("/nonexistent/image.jpg")


class TestSummarizeFrames:
    def test_empty_frames(self):
        result = summarize_frames([], None)
        assert "No frames" in result


class TestDetectChapters:
    def test_too_few_frames(self):
        result = detect_chapters([{"timestamp": 0, "analysis": "test"}], None)
        assert len(result) == 1
        assert "Too few" in result[0]["description"]


class TestAnalyzeBatch:
    def test_progress_callback_called(self):
        analyzer = MagicMock(spec=VisionAnalyzer)
        analyzer.analyze_frame.return_value = "Test analysis"
        analyzer.provider = "ollama"

        callback = MagicMock()
        frames = [
            {"path": "f1.jpg", "timestamp": 0.0, "frame_number": 0, "type": "s"},
            {"path": "f2.jpg", "timestamp": 5.0, "frame_number": 1, "type": "s"},
        ]

        from video_analyzer.analyzer import VisionAnalyzer as RealVA
        results = RealVA.analyze_batch(
            analyzer, frames, "describe", context_window=2, delay=0,
            progress_callback=callback,
        )
        assert callback.call_count == 2

    def test_context_rolling(self):
        call_args = []

        def capture_analyze(image_path, prompt, context=""):
            call_args.append({"prompt": prompt, "context": context})
            return f"Analysis for {image_path}"

        analyzer = MagicMock(spec=VisionAnalyzer)
        analyzer.analyze_frame.side_effect = capture_analyze
        analyzer.provider = "ollama"

        frames = [
            {"path": "f1.jpg", "timestamp": 0.0, "frame_number": 0, "type": "s"},
            {"path": "f2.jpg", "timestamp": 5.0, "frame_number": 1, "type": "s"},
            {"path": "f3.jpg", "timestamp": 10.0, "frame_number": 2, "type": "s"},
        ]

        from video_analyzer.analyzer import VisionAnalyzer as RealVA
        RealVA.analyze_batch(
            analyzer, frames, "describe", context_window=2, delay=0,
        )
        assert call_args[0]["context"] == ""
        assert len(call_args[1]["context"]) > 0
