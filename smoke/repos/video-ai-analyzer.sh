#!/usr/bin/env bash
# Smoke: video-ai-analyzer — its own CLI with the first-class meta provider.
# Analyzes Wilfred's public video with only 3 frames to keep the call tiny.
# With MODEL_API_KEY unset the CLI exits 1 with "No API key. Set
# MODEL_API_KEY or use --api-key" — the expected clean failure.
set -euo pipefail

cd "$TARGET_DIR"
python3 -m pip install --quiet --upgrade pip
# Package deps are light (yt-dlp, Pillow, click, rich); the meta provider
# branch imports `openai` lazily, so install it explicitly.
python3 -m pip install --quiet . openai

OUT_JSON="$SMOKE_WORK/vaa-result.json"
video-ai analyze "https://www.youtube.com/watch?v=y6EnqWGYJVU" \
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
