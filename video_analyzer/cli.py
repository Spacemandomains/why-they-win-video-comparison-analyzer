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
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.markdown import Markdown
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """🎬 Video AI Analyzer — Understand any video with AI vision."""
    pass


@main.command()
@click.argument("url")
@click.option("--provider", "-p", default="gemini", type=click.Choice(["gemini", "openai"]), help="Vision LLM provider")
@click.option("--api-key", "-k", envvar=["GEMINI_API_KEY", "OPENAI_API_KEY"], help="API key for vision provider")
@click.option("--model", "-m", default=None, help="Model name (default: gemini-2.0-flash or gpt-4o)")
@click.option("--mode", default="smart", type=click.Choice(["smart", "uniform", "both"]), help="Frame extraction mode")
@click.option("--max-frames", "-n", default=30, help="Maximum frames to extract")
@click.option("--interval", "-i", default=5.0, help="Seconds between frames (uniform mode)")
@click.option("--scene-threshold", default=0.3, help="Scene change threshold (0.0-1.0)")
@click.option("--max-height", default=720, help="Max video resolution height")
@click.option("--max-duration", default=600, help="Max video duration in seconds")
@click.option("--prompt", default=None, help="Custom analysis prompt")
@click.option("--summarize/--no-summarize", default=True, help="Generate video summary")
@click.option("--chapters/--no-chapters", default=False, help="Detect video chapters")
@click.option("--output", "-o", default=None, help="Save results to file (JSON)")
@click.option("--keep-frames", is_flag=True, help="Keep extracted frames after analysis")
def analyze(url, provider, api_key, model, mode, max_frames, interval, scene_threshold,
            max_height, max_duration, prompt, summarize, chapters, output, keep_frames):
    """Analyze a video from URL (YouTube, TikTok, Twitter, etc.)."""
    from .downloader import download_video
    from .extractor import extract_frames
    from .analyzer import VisionAnalyzer, summarize_frames, detect_chapters

    if not api_key:
        env_key = "GEMINI_API_KEY" if provider == "gemini" else "OPENAI_API_KEY"
        console.print(f"[red]Error: No API key. Set {env_key} or use --api-key[/red]")
        sys.exit(1)

    # Step 1: Download
    with console.status("[bold green]Downloading video...") as status:
        try:
            video_info = download_video(url, max_height=max_height, max_duration=max_duration)
        except Exception as e:
            console.print(f"[red]Download failed: {e}[/red]")
            sys.exit(1)

    console.print(Panel(
        f"[bold]{video_info['title']}[/bold]\n"
        f"Duration: {video_info['duration']:.0f}s | "
        f"Resolution: {video_info['width']}x{video_info['height']} | "
        f"FPS: {video_info['fps']}",
        title="📹 Video Info",
    ))

    # Step 2: Extract frames
    frame_dir = tempfile.mkdtemp(prefix="vai_frames_") if not keep_frames else f"/tmp/vai_frames_{os.getpid()}"
    
    with console.status("[bold yellow]Extracting key frames...") as status:
        frames = extract_frames(
            video_info["path"],
            output_dir=frame_dir,
            mode=mode,
            interval=interval,
            max_frames=max_frames,
            scene_threshold=scene_threshold,
        )

    console.print(f"[green]✓ Extracted {len(frames)} frames[/green]")

    # Step 3: Analyze frames
    default_prompt = (
        "Describe what's happening in this frame in detail. "
        "Include: people, objects, text on screen, actions, setting, mood. "
        "Be specific and concise."
    )
    analysis_prompt = prompt or default_prompt

    analyzer = VisionAnalyzer(provider=provider, api_key=api_key, model=model)
    
    def progress_fn(current, total, result):
        console.print(f"  [dim]Frame {current}/{total}[/dim] — {result['analysis'][:80]}...")

    with console.status("[bold blue]Analyzing frames with AI..."):
        frame_analyses = analyzer.analyze_batch(
            frames,
            analysis_prompt,
            context_window=3,
            delay=1.0,
            progress_callback=progress_fn,
        )

    console.print(f"[green]✓ Analyzed {len(frame_analyses)} frames[/green]")

    # Step 4: Summary
    result_data = {
        "video": video_info,
        "frames": [
            {
                "timestamp": fa.get("timestamp", 0),
                "analysis": fa["analysis"],
                "type": fa.get("type", ""),
            }
            for fa in frame_analyses
        ],
    }

    if summarize:
        with console.status("[bold magenta]Generating summary..."):
            summary = summarize_frames(frame_analyses, provider, api_key, model)
        result_data["summary"] = summary
        console.print()
        console.print(Panel(Markdown(summary), title="📝 Video Summary"))

    if chapters:
        with console.status("[bold cyan]Detecting chapters..."):
            chapter_list = detect_chapters(frame_analyses, provider, api_key, model)
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
    
    # Cleanup video
    try:
        os.remove(video_info["path"])
        os.rmdir(os.path.dirname(video_info["path"]))
    except OSError:
        pass


@main.command()
@click.argument("video_path", type=click.Path(exists=True))
@click.option("--mode", default="smart", type=click.Choice(["smart", "uniform", "both"]))
@click.option("--max-frames", "-n", default=30)
@click.option("--interval", "-i", default=5.0)
@click.option("--output", "-o", default="./frames", help="Output directory for frames")
def extract(video_path, mode, max_frames, interval, output):
    """Extract frames from a local video file (no AI analysis)."""
    from .extractor import extract_frames

    frames = extract_frames(
        video_path,
        output_dir=output,
        mode=mode,
        interval=interval,
        max_frames=max_frames,
    )

    table = Table(title=f"Extracted {len(frames)} frames")
    table.add_column("#", style="dim")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Type")
    table.add_column("File")
    for i, f in enumerate(frames):
        mins, secs = divmod(int(f["timestamp"]), 60)
        table.add_row(str(i + 1), f"{mins}:{secs:02d}", f["type"], f["path"])
    console.print(table)


@main.command()
@click.argument("image_paths", nargs=-1, type=click.Path(exists=True))
@click.option("--provider", "-p", default="gemini")
@click.option("--api-key", "-k", envvar=["GEMINI_API_KEY", "OPENAI_API_KEY"])
@click.option("--model", "-m", default=None)
@click.option("--prompt", default="Describe this image in detail.")
def ask(image_paths, provider, api_key, model, prompt):
    """Ask a question about one or more images."""
    from .analyzer import VisionAnalyzer

    if not api_key:
        console.print("[red]Error: No API key.[/red]")
        sys.exit(1)

    analyzer = VisionAnalyzer(provider=provider, api_key=api_key, model=model)
    
    for img_path in image_paths:
        result = analyzer.analyze_frame(img_path, prompt)
        console.print(Panel(result, title=f"🖼️ {Path(img_path).name}"))


if __name__ == "__main__":
    main()
