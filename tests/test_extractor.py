"""Tests for extractor module."""
import os
import tempfile
import pytest
from unittest.mock import patch
from video_analyzer.extractor import (
    get_video_duration,
    extract_frames,
    _scene_detect,
    _uniform_extract,
    _extract_at_timestamps,
    _merge_and_dedup,
)


class TestEvalFps:
    def test_integer_fps(self):
        from video_analyzer.downloader import _eval_fps
        assert _eval_fps("30") == 30.0

    def test_fraction_fps(self):
        from video_analyzer.downloader import _eval_fps
        result = _eval_fps("30000/1001")
        assert abs(result - 29.97) < 0.01

    def test_invalid_fps(self):
        from video_analyzer.downloader import _eval_fps
        assert _eval_fps("invalid") == 30.0


class TestExtractAtTimestamps:
    def test_creates_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = os.path.join(tmpdir, "nonexistent")
            result = _extract_at_timestamps("/dev/null", out, [0.0], 2, "test")
            assert isinstance(result, list)


class TestMergeAndDedup:
    def test_empty_input(self):
        assert _merge_and_dedup([], 10) == []

    def test_dedup_close_frames(self):
        frames = [
            {"timestamp": 0.0, "path": "a.jpg", "frame_number": 0, "type": "s"},
            {"timestamp": 0.5, "path": "b.jpg", "frame_number": 1, "type": "s"},
            {"timestamp": 5.0, "path": "c.jpg", "frame_number": 2, "type": "u"},
        ]
        result = _merge_and_dedup(frames, 10)
        assert len(result) == 2

    def test_max_frames_cap(self):
        frames = [
            {"timestamp": float(i), "path": f"{i}.jpg", "frame_number": i, "type": "s"}
            for i in range(20)
        ]
        result = _merge_and_dedup(frames, 5)
        assert len(result) == 5

    def test_sorted_output(self):
        frames = [
            {"timestamp": 5.0, "path": "b.jpg", "frame_number": 1, "type": "s"},
            {"timestamp": 0.0, "path": "a.jpg", "frame_number": 0, "type": "s"},
        ]
        result = _merge_and_dedup(frames, 10)
        assert result[0]["timestamp"] <= result[1]["timestamp"]


class TestExtractFrames:
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_frames("/nonexistent/video.mp4")

    def test_invalid_mode(self):
        """Mode validation happens before any file operations."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video content")
            f.flush()
            try:
                with pytest.raises(ValueError, match="Unknown mode"):
                    extract_frames(f.name, mode="invalid_mode")
            finally:
                os.unlink(f.name)


class TestGetVideoDuration:
    def test_nonexistent_file(self):
        result = get_video_duration("/nonexistent/file.mp4")
        assert result == 0.0
