#!/usr/bin/env bash
# Smoke: mcp-video — Python driver importing the fork's own
# src/mcp_video/meta.py (analyze_frames_with_meta) plus its own frame
# extraction (src/mcp_video/video.py) on a 5-second sample clip.
set -euo pipefail

python3 -m pip install --quiet opencv-python-headless Pillow

CLIP="$(fetch_sample_clip)"
SMOKE_CLIP="$CLIP" TARGET_DIR="$TARGET_DIR" \
  python3 "$SMOKE_DIR/drivers/mcp_video_smoke.py"
