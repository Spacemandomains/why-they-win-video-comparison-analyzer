"""Smart frame extraction using ffmpeg. Scene-change detection + uniform sampling."""

import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def extract_frames(
    video_path: str,
    output_dir: Optional[str] = None,
    mode: str = "smart",
    interval: float = 5.0,
    max_frames: int = 50,
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
        quality: JPEG quality (2=highest, 31=lowest)
    
    Returns:
        List of dicts: {path, timestamp, frame_number, type}
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="frames_")
    os.makedirs(output_dir, exist_ok=True)

    duration = _get_duration(video_path)
    
    if mode == "smart":
        frames = _scene_detect_extract(video_path, output_dir, scene_threshold, max_frames, quality, duration)
    elif mode == "uniform":
        frames = _uniform_extract(video_path, output_dir, interval, max_frames, quality, duration)
    elif mode == "both":
        smart_frames = _scene_detect_extract(video_path, output_dir, scene_threshold, max_frames // 2, quality, duration)
        uniform_frames = _uniform_extract(video_path, output_dir, interval, max_frames // 2, quality, duration, offset=len(smart_frames))
        frames = _merge_and_dedup(smart_frames + uniform_frames, max_frames)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    # Sort by timestamp
    frames.sort(key=lambda f: f["timestamp"])
    
    # If too many, subsample
    if len(frames) > max_frames:
        step = len(frames) / max_frames
        frames = [frames[int(i * step)] for i in range(max_frames)]

    return frames


def _get_duration(video_path: str) -> float:
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


def _scene_detect_extract(
    video_path: str, output_dir: str,
    threshold: float, max_frames: int, quality: int, duration: float,
) -> list[dict]:
    """Extract frames at scene changes using ffmpeg's scene filter."""
    # First pass: detect scene changes
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    # Parse scene change timestamps from showinfo output
    timestamps = []
    import re
    for line in result.stderr.split("\n"):
        match = re.search(r"pts_time:(\d+\.?\d*)", line)
        if match:
            timestamps.append(float(match.group(1)))

    # Always include first frame
    if not timestamps or timestamps[0] > 1.0:
        timestamps.insert(0, 0.0)

    # If too many scene changes, subsample
    if len(timestamps) > max_frames:
        step = len(timestamps) / max_frames
        timestamps = [timestamps[int(i * step)] for i in range(max_frames)]

    # Second pass: extract frames at detected timestamps
    frames = []
    for i, ts in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"scene_{i:04d}_{ts:.1f}s.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", str(quality),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        if os.path.exists(output_path):
            frames.append({
                "path": output_path,
                "timestamp": ts,
                "frame_number": i,
                "type": "scene_change",
            })

    return frames


def _uniform_extract(
    video_path: str, output_dir: str,
    interval: float, max_frames: int, quality: int, duration: float,
    offset: int = 0,
) -> list[dict]:
    """Extract frames at uniform intervals."""
    if duration <= 0:
        duration = _get_duration(video_path)
    
    # Adjust interval if too short for max_frames
    if duration / interval > max_frames:
        interval = duration / max_frames

    timestamps = []
    t = 0.0
    while t < duration and len(timestamps) < max_frames:
        timestamps.append(t)
        t += interval

    frames = []
    for i, ts in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"uniform_{offset + i:04d}_{ts:.1f}s.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(ts),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", str(quality),
            output_path,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        if os.path.exists(output_path):
            frames.append({
                "path": output_path,
                "timestamp": ts,
                "frame_number": offset + i,
                "type": "uniform",
            })

    return frames


def _merge_and_dedup(frames: list[dict], max_frames: int) -> list[dict]:
    """Merge smart + uniform frames, remove near-duplicates."""
    if not frames:
        return frames
    
    frames.sort(key=lambda f: f["timestamp"])
    merged = [frames[0]]
    
    for frame in frames[1:]:
        # Skip if too close to previous frame (within 1 second)
        if frame["timestamp"] - merged[-1]["timestamp"] > 1.0:
            merged.append(frame)

    if len(merged) > max_frames:
        step = len(merged) / max_frames
        merged = [merged[int(i * step)] for i in range(max_frames)]

    return merged
