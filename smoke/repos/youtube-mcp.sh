#!/usr/bin/env bash
# Smoke: youtube-mcp — TypeScript driver importing the fork's own
# src/meta.ts (analyzeFramesWithMeta) with frames pulled by its own
# src/youtube.ts extractFrames().
# The driver is copied into the target checkout so its relative imports
# and node_modules resolve exactly as the fork's own code expects.
#
# Frames come from the harness's local sample mp4 (exported as
# SMOKE_SAMPLE_CLIP): extractFrames' streamUrl option reads it directly
# with ffmpeg, skipping the yt-dlp/YouTube round-trip that GitHub
# runners bot-wall (run #1 failure). ffmpeg is installed by the
# workflow job; yt-dlp is installed here for the driver's fallback
# YouTube-URL path (used when SMOKE_SAMPLE_CLIP is unset).
set -euo pipefail

cd "$TARGET_DIR"
bun install --silent
python3 -m pip install --quiet yt-dlp  # fallback path shells out to yt-dlp

CLIP="$(fetch_sample_clip)"
export SMOKE_SAMPLE_CLIP="$CLIP"

cp "$SMOKE_DIR/drivers/youtube_mcp_smoke.ts" ./smoke_driver.ts
bun run smoke_driver.ts
