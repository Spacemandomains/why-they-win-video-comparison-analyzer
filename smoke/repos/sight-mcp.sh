#!/usr/bin/env bash
# Smoke: sight-mcp — starts the fork's real MCP server (index.ts) with
# PROVIDER=meta and drives it over stdio JSON-RPC: initialize, tools/list,
# and a real tools/call to analyze_image on a local frame, which routes
# through its ProviderConfig-resolved Meta endpoint (ChatService).
# With MODEL_API_KEY unset the server exits at startup with
# "MODEL_API_KEY environment variable is required" — the expected
# clean failure, which the driver reports.
set -euo pipefail

cd "$TARGET_DIR"
bun install --silent

CLIP="$(fetch_sample_clip)"
FRAME="$SMOKE_WORK/frame.jpg"
ffmpeg -y -loglevel error -ss 1 -i "$CLIP" -frames:v 1 "$FRAME"

cp "$SMOKE_DIR/drivers/sight_mcp_smoke.mjs" ./smoke_driver.mjs
SMOKE_FRAME="$FRAME" node smoke_driver.mjs
