"""Audio transcription using Whisper (local, free). Extracts audio → transcribes."""

import json
import os
import subprocess
import tempfile
from typing import Optional


def extract_audio(video_path: str, output_path: Optional[str] = None) -> str:
    """Extract audio track from video to WAV format for Whisper."""
    if output_path is None:
        output_path = tempfile.mktemp(prefix="audio_", suffix=".wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",  # no video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",  # 16kHz (Whisper optimal)
        "-ac", "1",  # mono
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg not found. Install: apt install ffmpeg / brew install ffmpeg")
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr.strip()}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError("Audio extraction produced empty file — video may have no audio track")

    return output_path


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
    task: str = "transcribe",
) -> dict:
    """
    Transcribe audio file using Whisper.

    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        model_size: Whisper model size: tiny, base, small, medium, large
        language: Language code (e.g., 'en', 'id'). Auto-detect if None.
        task: 'transcribe' (original language) or 'translate' (to English)

    Returns:
        dict with keys: text, segments, language, duration
    """
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "openai-whisper not installed. Install: pip install openai-whisper\n"
            "Note: Requires ffmpeg (apt install ffmpeg)"
        )

    model = whisper.load_model(model_size)
    options = {"task": task}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, **options)

    # Format segments with timestamps
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
        "language": result.get("language", "unknown"),
        "duration": segments[-1]["end"] if segments else 0,
    }


def transcribe_video(
    video_path: str,
    model_size: str = "base",
    language: Optional[str] = None,
) -> dict:
    """
    Extract audio from video and transcribe it.

    Args:
        video_path: Path to video file
        model_size: Whisper model size
        language: Language code or None for auto-detect

    Returns:
        dict with keys: text, segments, language, audio_path
    """
    audio_path = extract_audio(video_path)
    try:
        result = transcribe_audio(audio_path, model_size, language)
        result["audio_path"] = audio_path
        return result
    finally:
        # Clean up temp audio
        try:
            os.unlink(audio_path)
        except OSError:
            pass


def format_transcript(transcription: dict, include_timestamps: bool = True) -> str:
    """Format transcription into readable text."""
    if not transcription.get("segments"):
        return transcription.get("text", "")

    lines = []
    for seg in transcription["segments"]:
        if include_timestamps:
            mins, secs = divmod(int(seg["start"]), 60)
            lines.append(f"[{mins:02d}:{secs:02d}] {seg['text']}")
        else:
            lines.append(seg["text"])

    return "\n".join(lines)
