"""Smart frame extraction using ffmpeg. Scene-change detection + uniform sampling."""

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0


def extract_frames(
    video_path: str,
    output_dir: Optional[str] = None,
    mode: str = "smart",
    interval: float = 5.0,
    max_frames: int = 30,
    scene_threshold: float = 0.3,
    quality: int = 2,
) -> list[dict]:
    """
    Extract key frames from video.

    Args:
        video_path: Path to video file
        output_dir: Where to save frames. Defaults to temp dir.
        mode: 'smart' (scene detection), 'uniform' (fixed interval), or 'both'
        interval: Seconds between frames for uniform mode
        max_frames: Maximum frames to extract
        scene_threshold: Scene change sensitivity (0.0-1.0, lower = more frames)
        quality: JPEG quality (1=highest, 31=lowest)

    Returns:
        List of dicts: {path, timestamp, frame_number, type}
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    valid_modes = ("smart", "uniform", "both")
    if mode not in valid_modes:
        raise ValueError(f"Unknown mode: {mode}. Use 'smart', 'uniform', or 'both'.")

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="frames_")
    os.makedirs(output_dir, exist_ok=True)

    duration = get_video_duration(video_path)
    if duration <= 0:
        raise ValueError("Could not determine video duration")

    if mode == "smart":
        frames = _scene_detect(video_path, output_dir, scene_threshold, max_frames, quality, duration)
        # Fallback to uniform if scene detection finds too few
        if len(frames) < 3:
            frames = _uniform_extract(video_path, output_dir, interval, max_frames, quality, duration)
    elif mode == "uniform":
        frames = _uniform_extract(video_path, output_dir, interval, max_frames, quality, duration)
    elif mode == "both":
        half = max(max_frames // 2, 5)
        smart_frames = _scene_detect(video_path, output_dir, scene_threshold, half, quality, duration)
        uniform_frames = _uniform_extract(
            video_path, output_dir, interval, half, quality, duration, offset=len(smart_frames)
        )
        frames = _merge_and_dedup(smart_frames + uniform_frames, max_frames)
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'smart', 'uniform', or 'both'.")

    # Sort by timestamp and cap
    frames.sort(key=lambda f: f["timestamp"])
    if len(frames) > max_frames:
        step = len(frames) / max_frames
        frames = [frames[int(i * step)] for i in range(max_frames)]

    return frames


def _scene_detect(
    video_path: str, output_dir: str,
    threshold: float, max_frames: int, quality: int, duration: float,
) -> list[dict]:
    """Extract frames at scene changes using ffmpeg's scene filter."""
    # Detect scene changes
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    # Parse timestamps from showinfo output
    timestamps = []
    for line in result.stderr.split("\n"):
        match = re.search(r"pts_time:(\d+\.?\d*)", line)
        if match:
            timestamps.append(float(match.group(1)))

    # Always include first frame
    if not timestamps or timestamps[0] > 1.0:
        timestamps.insert(0, 0.0)

    # Subsample if too many
    if len(timestamps) > max_frames:
        step = len(timestamps) / max_frames
        timestamps = [timestamps[int(i * step)] for i in range(max_frames)]

    # Extract frames at detected timestamps
    return _extract_at_timestamps(video_path, output_dir, timestamps, quality, "scene")


def _uniform_extract(
    video_path: str, output_dir: str,
    interval: float, max_frames: int, quality: int, duration: float,
    offset: int = 0,
) -> list[dict]:
    """Extract frames at uniform intervals."""
    # Adjust interval to not exceed max_frames
    if duration / interval > max_frames:
        interval = duration / max_frames

    timestamps = []
    t = 0.0
    while t < duration and len(timestamps) < max_frames:
        timestamps.append(t)
        t += interval

    return _extract_at_timestamps(video_path, output_dir, timestamps, quality, "uniform", offset)


def _extract_at_timestamps(
    video_path: str, output_dir: str,
    timestamps: list[float], quality: int, frame_type: str, offset: int = 0,
) -> list[dict]:
    """Extract single frames at given timestamps."""
    frames = []
    for i, ts in enumerate(timestamps):
        idx = offset + i
        output_path = os.path.join(output_dir, f"{frame_type}_{idx:04d}_{ts:.1f}s.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{ts:.3f}",
            "-i", video_path,
            "-vframes", "1",
            "-q:v", str(quality),
            output_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, timeout=30)
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            frames.append({
                "path": output_path,
                "timestamp": round(ts, 2),
                "frame_number": idx,
                "type": frame_type,
            })
    return frames


def _merge_and_dedup(frames: list[dict], max_frames: int) -> list[dict]:
    """Merge smart + uniform frames, remove near-duplicates."""
    if not frames:
        return frames

    frames.sort(key=lambda f: f["timestamp"])
    merged = [frames[0]]

    for frame in frames[1:]:
        if frame["timestamp"] - merged[-1]["timestamp"] > 1.0:
            merged.append(frame)

    if len(merged) > max_frames:
        step = len(merged) / max_frames
        merged = [merged[int(i * step)] for i in range(max_frames)]

    return merged
