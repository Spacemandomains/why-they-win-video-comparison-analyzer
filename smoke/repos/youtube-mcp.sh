#!/usr/bin/env bash
# Smoke: youtube-mcp — TypeScript driver importing the fork's own
# src/meta.ts (analyzeFramesWithMeta) with frames pulled by its own
# src/youtube.ts extractFrames() from Wilfred's public video.
# The driver is copied into the target checkout so its relative imports
# and node_modules resolve exactly as the fork's own code expects.
set -euo pipefail

cd "$TARGET_DIR"
bun install --silent
python3 -m pip install --quiet yt-dlp  # extractFrames shells out to yt-dlp

cp "$SMOKE_DIR/drivers/youtube_mcp_smoke.ts" ./smoke_driver.ts
bun run smoke_driver.ts
