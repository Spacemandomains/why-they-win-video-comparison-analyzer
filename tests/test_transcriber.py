"""Tests for transcriber module."""
import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from video_analyzer.transcriber import (
    extract_audio,
    transcribe_audio,
    transcribe_video,
    format_transcript,
)


class TestExtractAudio:
    def test_missing_ffmpeg(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("ffmpeg not found")):
            with pytest.raises(RuntimeError, match="ffmpeg not found"):
                extract_audio("/nonexistent/video.mp4")

    def test_ffmpeg_error(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "No such file or directory"
        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="extraction failed"):
                extract_audio("/fake/video.mp4")


class TestTranscribeAudio:
    def test_missing_whisper(self):
        with patch.dict("sys.modules", {"whisper": None}):
            with pytest.raises(RuntimeError, match="openai-whisper not installed"):
                transcribe_audio("/fake/audio.wav")


class TestFormatTranscript:
    def test_empty_segments(self):
        result = format_transcript({"text": "hello", "segments": []})
        assert result == "hello"

    def test_with_timestamps(self):
        transcript = {
            "text": "hello world",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "hello"},
                {"start": 2.5, "end": 5.0, "text": "world"},
            ],
        }
        result = format_transcript(transcript, include_timestamps=True)
        assert "[00:00]" in result
        assert "[00:02]" in result
        assert "hello" in result
        assert "world" in result

    def test_without_timestamps(self):
        transcript = {
            "text": "hello world",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "hello"},
                {"start": 2.5, "end": 5.0, "text": "world"},
            ],
        }
        result = format_transcript(transcript, include_timestamps=False)
        assert "[" not in result
        assert "hello" in result
        assert "world" in result


class TestTranscribeVideo:
    def test_calls_extract_and_transcribe(self):
        with patch("video_analyzer.transcriber.extract_audio", return_value="/tmp/audio.wav") as mock_extract, \
             patch("video_analyzer.transcriber.transcribe_audio", return_value={
                 "text": "test", "segments": [], "language": "en", "duration": 0
             }) as mock_transcribe:
            result = transcribe_video("/fake/video.mp4", "base", "en")
            mock_extract.assert_called_once_with("/fake/video.mp4")
            mock_transcribe.assert_called_once_with("/tmp/audio.wav", "base", "en")
            assert result["text"] == "test"
