"""Video downloader using yt-dlp. Supports YouTube, TikTok, Twitter, and 1000+ sites."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def check_dependencies() -> dict[str, bool]:
    """Check if required tools are installed."""
    deps = {}
    for tool in ["yt-dlp", "ffmpeg", "ffprobe"]:
        try:
            subprocess.run([tool, "--version"], capture_output=True, timeout=5)
            deps[tool] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            deps[tool] = False
    return deps


def get_video_info(url: str) -> dict:
    """Get video metadata without downloading."""
    cmd = ["yt-dlp", "--dump-json", "--no-download", "--no-warnings", url]
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
        dict with keys: path, title, duration, width, height, fps, description, etc.
    """
    deps = check_dependencies()
    if not deps.get("yt-dlp"):
        raise RuntimeError("yt-dlp not installed. Install: pip install yt-dlp")
    if not deps.get("ffmpeg"):
        raise RuntimeError("ffmpeg not installed. Install: apt install ffmpeg / brew install ffmpeg")

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_ai_")

    os.makedirs(output_dir, exist_ok=True)
    output_template = os.path.join(output_dir, "%(title).50s.%(ext)s")

    # Get metadata first
    info = get_video_info(url)
    duration = info.get("duration", 0) or 0
    if duration > max_duration:
        raise ValueError(
            f"Video too long: {duration:.0f}s (max {max_duration}s). "
            f"Use --max-duration to override."
        )

    # Download
    cmd = [
        "yt-dlp",
        "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--no-warnings",
        url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Download failed: {result.stderr.strip()}")

    # Find downloaded file
    video_path = _find_video_file(output_dir)
    if not video_path:
        raise RuntimeError("Download succeeded but no video file found")

    # Probe video properties
    probe = _probe_video(video_path)
    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"),
        {},
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"),
        {},
    )

    return {
        "path": video_path,
        "title": info.get("title", "Unknown"),
        "duration": float(probe.get("format", {}).get("duration", duration)),
        "width": int(video_stream.get("width", info.get("width", 0) or 0)),
        "height": int(video_stream.get("height", info.get("height", 0) or 0)),
        "fps": _eval_fps(video_stream.get("r_frame_rate", "30/1")),
        "codec": video_stream.get("codec_name", "unknown"),
        "has_audio": bool(audio_stream),
        "description": info.get("description", "") or "",
        "uploader": info.get("uploader", "") or "",
        "upload_date": info.get("upload_date", "") or "",
        "view_count": info.get("view_count", 0) or 0,
        "url": url,
    }


def _find_video_file(directory: str) -> Optional[str]:
    """Find the most recent video file in directory."""
    extensions = ["*.mp4", "*.webm", "*.mkv", "*.avi", "*.mov"]
    files = []
    for ext in extensions:
        files.extend(Path(directory).glob(ext))
    if files:
        return str(max(files, key=os.path.getmtime))
    return None


def _probe_video(video_path: str) -> dict:
    """Get video properties with ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {}


def _eval_fps(fps_str: str) -> float:
    """Evaluate frame rate string like '30000/1001'."""
    try:
        if "/" in str(fps_str):
            num, den = str(fps_str).split("/")
            return round(int(num) / int(den), 2)
        return float(fps_str)
    except (ValueError, ZeroDivisionError, AttributeError):
        return 30.0
