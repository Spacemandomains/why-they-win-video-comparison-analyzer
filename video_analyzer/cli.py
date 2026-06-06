"""CLI interface for video-ai-analyzer."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from . import __version__

console = Console()


def _get_api_key(provider: str, api_key: str) -> str:
    """Resolve API key from arg, env, or .env file."""
    if api_key:
        return api_key
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(provider, "")
    return os.environ.get(env_var, "")


@click.group()
@click.version_option(version=__version__, prog_name="video-ai")
def main():
    """🎬 Video AI Analyzer — Understand any video with AI vision."""
    pass


@main.command()
@click.argument("url")
@click.option("--provider", "-p", default="gemini",
              type=click.Choice(["gemini", "openai", "anthropic", "ollama", "custom"]),
              help="Vision LLM provider")
@click.option("--api-key", "-k", default="", help="API key (or set env variable)")
@click.option("--base-url", "-b", default="", help="Base URL for custom OpenAI-compatible provider")
@click.option("--model", "-m", default=None, help="Model name (uses provider default)")
@click.option("--mode", default="smart",
              type=click.Choice(["smart", "uniform", "both"]),
              help="Frame extraction mode")
@click.option("--max-frames", "-n", default=30, help="Maximum frames to extract")
@click.option("--interval", "-i", default=5.0, help="Seconds between frames (uniform mode)")
@click.option("--scene-threshold", default=0.3, help="Scene change threshold (0.0-1.0)")
@click.option("--max-height", default=720, help="Max video resolution height")
@click.option("--max-duration", default=600, help="Max video duration in seconds")
@click.option("--prompt", default=None, help="Custom analysis prompt")
@click.option("--summarize/--no-summarize", default=True, help="Generate video summary")
@click.option("--chapters/--no-chapters", default=False, help="Detect video chapters")
@click.option("--transcribe/--no-transcribe", default=False, help="Transcribe audio with Whisper")
@click.option("--whisper-model", default="base",
              type=click.Choice(["tiny", "base", "small", "medium", "large"]),
              help="Whisper model size")
@click.option("--output", "-o", default=None, help="Save results to JSON file")
@click.option("--keep-frames", is_flag=True, help="Keep extracted frames after analysis")
def analyze(url, provider, api_key, base_url, model, mode, max_frames, interval, scene_threshold,
            max_height, max_duration, prompt, summarize, chapters, transcribe,
            whisper_model, output, keep_frames):
    """Analyze a video from URL (YouTube, TikTok, Twitter, etc.)."""
    from .downloader import download_video, check_dependencies
    from .extractor import extract_frames
    from .analyzer import VisionAnalyzer, summarize_frames, detect_chapters
    from .transcriber import transcribe_video, format_transcript

    # Check dependencies
    deps = check_dependencies()
    missing = [k for k, v in deps.items() if not v]
    if missing:
        console.print(f"[red]Missing dependencies: {', '.join(missing)}[/red]")
        if "ffmpeg" in missing:
            console.print("  Install: [bold]apt install ffmpeg[/bold] or [bold]brew install ffmpeg[/bold]")
        if "yt-dlp" in missing:
            console.print("  Install: [bold]pip install yt-dlp[/bold]")
        sys.exit(1)

    # Resolve API key
    resolved_key = _get_api_key(provider, api_key)
    if provider != "ollama" and not resolved_key:
        env_map = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "custom": "CUSTOM_API_KEY"}
        console.print(f"[red]No API key. Set {env_map.get(provider, '?')} or use --api-key[/red]")
        sys.exit(1)

    # Step 1: Download
    with console.status("[bold green]Downloading video..."):
        try:
            video_info = download_video(url, max_height=max_height, max_duration=max_duration)
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            sys.exit(1)

    has_audio = video_info.get("has_audio", False)
    audio_info = "✓ Yes" if has_audio else "✗ No"

    console.print(Panel(
        f"[bold]{video_info['title']}[/bold]\n"
        f"Duration: {video_info['duration']:.0f}s | "
        f"Resolution: {video_info['width']}x{video_info['height']} | "
        f"FPS: {video_info['fps']} | "
        f"Audio: {audio_info}",
        title="📹 Video Info",
    ))

    result_data = {"video": {k: v for k, v in video_info.items() if k != "path"}}

    # Step 2: Transcribe audio (if requested and available)
    if transcribe and has_audio:
        with console.status("[bold cyan]Transcribing audio with Whisper..."):
            try:
                transcript = transcribe_video(video_info["path"], whisper_model)
                result_data["transcription"] = transcript
                formatted = format_transcript(transcript)
                console.print(Panel(
                    formatted[:2000] + ("..." if len(formatted) > 2000 else ""),
                    title=f"🎙️ Transcript ({transcript['language']})",
                ))
            except Exception as e:
                console.print(f"[yellow]Transcription failed: {e}[/yellow]")
    elif transcribe and not has_audio:
        console.print("[yellow]No audio track found — skipping transcription[/yellow]")

    # Step 3: Extract frames
    frame_dir = tempfile.mkdtemp(prefix="vai_frames_") if not keep_frames else f"/tmp/vai_frames_{os.getpid()}"

    with console.status("[bold yellow]Extracting key frames..."):
        frames = extract_frames(
            video_info["path"],
            output_dir=frame_dir,
            mode=mode,
            interval=interval,
            max_frames=max_frames,
            scene_threshold=scene_threshold,
        )

    console.print(f"[green]✓ Extracted {len(frames)} frames ({mode} mode)[/green]")

    # Step 4: Analyze frames
    try:
        analyzer = VisionAnalyzer(provider=provider, api_key=resolved_key, model=model, base_url=base_url or None)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)
    console.print(f"[dim]Using {provider} / {analyzer.model}[/dim]")

    def progress_fn(current, total, result):
        ts = result.get("timestamp", 0)
        analysis_preview = result["analysis"][:60].replace("\n", " ")
        console.print(f"  [dim]{current}/{total}[/dim] [{ts:.1f}s] {analysis_preview}...")

    with console.status("[bold blue]Analyzing frames with AI..."):
        frame_analyses = analyzer.analyze_batch(
            frames,
            prompt or (
                "Describe what's happening in this frame in detail. "
                "Include: people, objects, text on screen, actions, setting, mood. "
                "Be specific and concise."
            ),
            context_window=3,
            delay=1.0,
            progress_callback=progress_fn,
        )

    console.print(f"[green]✓ Analyzed {len(frame_analyses)} frames[/green]")

    result_data["frames"] = [
        {
            "timestamp": fa.get("timestamp", 0),
            "analysis": fa["analysis"],
            "type": fa.get("type", ""),
        }
        for fa in frame_analyses
    ]

    # Step 5: Summary
    if summarize:
        with console.status("[bold magenta]Generating summary..."):
            summary = summarize_frames(frame_analyses, analyzer)
        result_data["summary"] = summary
        console.print()
        console.print(Panel(Markdown(summary), title="📝 Video Summary"))

    # Step 6: Chapters
    if chapters:
        with console.status("[bold cyan]Detecting chapters..."):
            chapter_list = detect_chapters(frame_analyses, analyzer)
        result_data["chapters"] = chapter_list

        table = Table(title="📑 Chapters")
        table.add_column("Time", style="cyan")
        table.add_column("Title", style="bold")
        table.add_column("Description")
        for ch in chapter_list:
            start = ch.get("start", 0)
            mins, secs = divmod(int(start), 60)
            table.add_row(f"{mins}:{secs:02d}", ch.get("title", ""), ch.get("description", ""))
        console.print(table)

    # Save results
    if output:
        with open(output, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✓ Results saved to {output}[/green]")

    # Cleanup
    if not keep_frames:
        shutil.rmtree(frame_dir, ignore_errors=True)
    try:
        os.remove(video_info["path"])
        parent = os.path.dirname(video_info["path"])
        if parent and os.path.isdir(parent):
            os.rmdir(parent)
    except OSError:
        pass


@main.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--mode", default="smart", type=click.Choice(["smart", "uniform", "both"]))
@click.option("--max-frames", "-n", default=30)
@click.option("--interval", "-i", default=5.0)
@click.option("--scene-threshold", default=0.3)
@click.option("--output", "-o", default="./frames", help="Output directory for frames")
def extract(video_path, mode, max_frames, interval, scene_threshold, output):
    """Extract frames from a local video file (no AI analysis)."""
    from .extractor import extract_frames

    frames = extract_frames(
        video_path,
        output_dir=output,
        mode=mode,
        interval=interval,
        max_frames=max_frames,
        scene_threshold=scene_threshold,
    )

    table = Table(title=f"Extracted {len(frames)} frames → {output}")
    table.add_column("#", style="dim")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Type")
    table.add_column("File")
    for i, f in enumerate(frames):
        mins, secs = divmod(int(f["timestamp"]), 60)
        table.add_row(str(i + 1), f"{mins}:{secs:02d}", f["type"], Path(f["path"]).name)
    console.print(table)


@main.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--model", default="base", type=click.Choice(["tiny", "base", "small", "medium", "large"]))
@click.option("--language", default=None, help="Language code (e.g., en, id). Auto-detect if omitted.")
@click.option("--output", "-o", default=None, help="Save transcript to file")
def transcribe(video_path, model, language, output):
    """Transcribe audio from a video/audio file using Whisper."""
    from .transcriber import transcribe_video, format_transcript

    with console.status("[bold cyan]Transcribing..."):
        result = transcribe_video(video_path, model, language)

    formatted = format_transcript(result)
    console.print(Panel(
        formatted,
        title=f"🎙️ Transcript ({result['language']})",
    ))

    if output:
        with open(output, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        console.print(f"[green]✓ Saved to {output}[/green]")


@main.command()
@click.argument("image_paths", nargs=-1, type=click.Path(exists=True))
@click.option("--provider", "-p", default="gemini",
              type=click.Choice(["gemini", "openai", "anthropic", "ollama", "custom"]))
@click.option("--api-key", "-k", default="")
@click.option("--base-url", "-b", default="", help="Base URL for custom OpenAI-compatible provider")
@click.option("--model", "-m", default=None)
@click.option("--prompt", default="Describe this image in detail.")
def ask(image_paths, provider, api_key, base_url, model, prompt):
    """Ask a question about one or more images."""
    from .analyzer import VisionAnalyzer

    resolved_key = _get_api_key(provider, api_key)
    if provider != "ollama" and not resolved_key:
        console.print("[red]No API key.[/red]")
        sys.exit(1)

    try:
        analyzer = VisionAnalyzer(provider=provider, api_key=resolved_key, model=model, base_url=base_url or None)
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    for img_path in image_paths:
        result = analyzer.analyze_frame(img_path, prompt)
        console.print(Panel(result, title=f"🖼️ {Path(img_path).name}"))


@main.command()
def providers():
    """Show supported providers and their status."""
    table = Table(title="Supported Providers")
    table.add_column("Provider", style="bold cyan")
    table.add_column("Default Model")
    table.add_column("Env Variable")
    table.add_column("Status")

    providers_info = [
        ("gemini", "gemini-2.0-flash", "GEMINI_API_KEY"),
        ("openai", "gpt-4o", "OPENAI_API_KEY"),
        ("anthropic", "claude-sonnet-4-20250514", "ANTHROPIC_API_KEY"),
        ("ollama", "llava:13b", "(local, no key needed)"),
        ("custom", "(any model)", "CUSTOM_API_KEY + --base-url"),
    ]

    for name, model, env_var in providers_info:
        key = os.environ.get(env_var, "")
        if name == "ollama":
            import shutil as sh
            has_ollama = sh.which("ollama") is not None
            status = "[green]✓ Ready[/green]" if has_ollama else "[red]✗ Not installed[/red]"
        else:
            status = "[green]✓ Key set[/green]" if key else "[yellow]✗ No key[/yellow]"
        table.add_row(name, model, env_var, status)

    console.print(table)


if __name__ == "__main__":
    main()
