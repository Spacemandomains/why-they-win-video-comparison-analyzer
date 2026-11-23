#!/usr/bin/env python3
"""Smoke driver for the mcp-video fork.

Smallest real Meta call through the fork's OWN code:
  1. src/mcp_video/meta.py    -> meta_config() / analyze_frames_with_meta()
  2. src/mcp_video/video.py   -> extract_uniform_frames() (its own code)

The modules are loaded by file path so the driver does not need the MCP
server (or its mcp/pydantic pins) to exercise the Meta path.

Env:
  TARGET_DIR   checkout of Spacemandomains/mcp-video
  SMOKE_CLIP   path to a short local mp4 (the 5s sample clip)

Exit 0 + "SMOKE PASS: mcp-video" on success; "SMOKE FAIL: ..." + exit 1
otherwise. With MODEL_API_KEY unset it fails cleanly on the config check
before any network or video work happens.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO = "mcp-video"


def fail(msg: str) -> int:
    print(f"SMOKE FAIL: {REPO}: {msg}")
    return 1


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    target = Path(os.environ.get("TARGET_DIR", ".")).resolve()
    meta_path = target / "src" / "mcp_video" / "meta.py"
    video_path = target / "src" / "mcp_video" / "video.py"
    if not meta_path.exists() or not video_path.exists():
        return fail(f"fork sources not found under {target}")

    meta = load_module("mcp_video_meta", meta_path)
    cfg = meta.meta_config()
    if not cfg["api_key"]:
        return fail(
            "MODEL_API_KEY is not set (meta_config() resolved no key); "
            "export MODEL_API_KEY from https://dev.meta.ai/"
        )
    print(f"meta config: base_url={cfg['base_url']} model={cfg['model']}")

    clip = os.environ.get("SMOKE_CLIP", "")
    if not clip or not Path(clip).exists():
        return fail("SMOKE_CLIP is unset or the file does not exist")

    try:
        video = load_module("mcp_video_video", video_path)
        frames = video.extract_uniform_frames(clip, num_frames=2)
    except Exception as exc:  # noqa: BLE001 - report as smoke failure
        return fail(f"frame extraction failed: {exc}")
    if not frames:
        return fail("extract_uniform_frames returned no frames")
    print(f"extracted {len(frames)} frame(s) with mcp-video's own code")

    try:
        text = meta.analyze_frames_with_meta(
            frames,
            "In one or two sentences, describe what is visible in these "
            "video frames.",
        )
    except Exception as exc:  # noqa: BLE001 - report as smoke failure
        return fail(f"Meta API call failed: {exc}")
    if not text or not text.strip():
        return fail("Meta API returned an empty response")

    print("model response excerpt:", text.strip()[:400])
    print(f"SMOKE PASS: {REPO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
