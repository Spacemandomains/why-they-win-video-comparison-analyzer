#!/usr/bin/env bash
# Smoke: video-ai-analyzer — its own CLI with the first-class meta provider.
# Analyzes a video with only 3 frames to keep the call tiny.
# With MODEL_API_KEY unset the CLI exits 1 with "No API key. Set
# MODEL_API_KEY or use --api-key" — the expected clean failure.
#
# Input: the direct mp4 URL of the harness sample clip — NOT a YouTube
# URL and NOT a local file path:
# - Runs #1-#3 fed the CLI Wilfred's public YouTube video; on GitHub
#   runners yt-dlp hits YouTube's bot-wall ("Sign in to confirm you're
#   not a bot") — run #3 failed at the CLI's download step, after the
#   pip build and ffmpeg steps had both passed. No cookies will be
#   supplied, so YouTube input is out.
# - The CLI's `analyze` argument goes straight to yt-dlp
#   (video_analyzer/downloader.py: get_video_info/download_video), and
#   yt-dlp rejects a plain local path: "[generic] '<path>' is not a
#   valid URL" (verified locally). The `extract`/`transcribe`
#   subcommands accept local files but never call the AI, so they
#   cannot stand in.
# - A direct media URL is handled by yt-dlp's generic extractor with
#   no bot-wall. Verified locally through the downloader's exact
#   yt-dlp invocations (dump-json + the same format selector): the
#   sample mp4 downloads cleanly. The Meta provider call
#   (analyze_batch via Chat Completions) remains the code under test;
#   the frames are extracted from the downloaded sample by the CLI's
#   own extractor, exactly as with a YouTube input.
set -euo pipefail

# The harness lives in THIS repo, so the target checkout contains the
# top-level smoke/ folder next to video_analyzer/. setuptools' flat-layout
# auto-discovery refuses to build that ("Multiple top-level packages
# discovered in a flat-layout: ['smoke', 'video_analyzer']" — run #1
# failure). Install from a clean copy with the harness folders removed;
# the fork's own packaging is NOT modified.
CLEAN_DIR="$SMOKE_WORK/vaa-clean"
rm -rf "$CLEAN_DIR"
mkdir -p "$CLEAN_DIR"
cp -a "$TARGET_DIR/." "$CLEAN_DIR/"
rm -rf "$CLEAN_DIR/smoke" "$CLEAN_DIR/.github"

cd "$CLEAN_DIR"
python3 -m pip install --quiet --upgrade pip
# Package deps are light (yt-dlp, Pillow, click, rich); the meta provider
# branch imports `openai` lazily, so install it explicitly.
python3 -m pip install --quiet . openai

OUT_JSON="$SMOKE_WORK/vaa-result.json"
video-ai analyze "https://download.samplelib.com/mp4/sample-5s.mp4" \
  --provider meta \
  --max-frames 3 \
  --mode uniform \
  --interval 20 \
  --max-height 480 \
  --no-transcribe \
  --output "$OUT_JSON"

python3 - "$OUT_JSON" <<'PY'
import json
import sys

with open(sys.argv[1]) as fh:
    data = json.load(fh)
print("analysis excerpt:", json.dumps(data)[:400])
print("SMOKE PASS: video-ai-analyzer")
PY
