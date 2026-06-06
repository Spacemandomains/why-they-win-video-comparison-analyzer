"""Video downloader using yt-dlp. Supports YouTube, TikTok, Twitter, and 1000+ sites."""

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def get_video_info(url: str) -> dict:
    """Get video metadata without downloading."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp error: {result.stderr.strip()}")
    return json.loads(result.stdout)


def download_video(
    url: str,
    output_dir: Optional[str] = None,
    max_height: int = 720,
    max_duration: int = 600,
) -> dict:
    """
    Download video from URL.
    
    Args:
        url: Video URL (YouTube, TikTok, Twitter, etc.)
        output_dir: Where to save. Defaults to temp dir.
        max_height: Max resolution height (720p default to save bandwidth)
        max_duration: Max video length in seconds (10 min default)
    
    Returns:
        dict with keys: path, title, duration, width, height, fps
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_ai_")
    
    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title).50s.%(ext)s")

    # First check duration
    info = get_video_info(url)
    duration = info.get("duration", 0)
    if duration > max_duration:
        raise ValueError(
            f"Video too long: {duration}s (max {max_duration}s). "
            f"Use --max-duration to override."
        )

    cmd = [
        "yt-dlp",
        "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-warnings",
        "--progress",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.strip()}")

    # Find downloaded file
    files = sorted(Path(output_dir).glob("*.mp4"), key=os.path.getmtime, reverse=True)
    if not files:
        # Try any video file
        for ext in ["*.webm", "*.mkv", "*.avi"]:
            files = sorted(Path(output_dir).glob(ext), key=os.path.getmtime, reverse=True)
            if files:
                break
    if not files:
        raise RuntimeError("Download succeeded but no video file found")

    video_path = str(files[0])

    # Get video properties with ffprobe
    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        video_path,
    ]
    probe = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=30)
    probe_data = json.loads(probe.stdout) if probe.returncode == 0 else {}

    video_stream = next(
        (s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"),
        {},
    )

    return {
        "path": video_path,
        "title": info.get("title", "Unknown"),
        "duration": float(probe_data.get("format", {}).get("duration", duration)),
        "width": int(video_stream.get("width", info.get("width", 0))),
        "height": int(video_stream.get("height", info.get("height", 0))),
        "fps": eval_fps(video_stream.get("r_frame_rate", "30/1")),
        "description": info.get("description", ""),
        "uploader": info.get("uploader", ""),
        "upload_date": info.get("upload_date", ""),
        "view_count": info.get("view_count", 0),
        "url": url,
    }


def eval_fps(fps_str: str) -> float:
    """Evaluate frame rate string like '30000/1001'."""
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/")
            return round(int(num) / int(den), 2)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 30.0
