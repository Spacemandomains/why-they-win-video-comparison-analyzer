#!/usr/bin/env bash
# Smoke: vision-tool — its own CLI (vision_proxy.py) with
# --model "meta/muse-spark-1.3" on a single frame image, which routes
# through its call_meta backend (Meta Model API, Chat Completions).
set -u

python3 -m pip install --quiet -r "$TARGET_DIR/requirements.txt" || {
  echo "SMOKE FAIL: vision-tool: dependency install failed"; exit 1; }

CLIP="$(fetch_sample_clip)" || { echo "SMOKE FAIL: vision-tool: could not download sample clip"; exit 1; }
FRAME="$SMOKE_WORK/frame.jpg"
ffmpeg -y -loglevel error -ss 1 -i "$CLIP" -frames:v 1 "$FRAME" || {
  echo "SMOKE FAIL: vision-tool: ffmpeg frame extraction failed"; exit 1; }

cd "$TARGET_DIR"
OUT="$(python3 vision_proxy.py "$FRAME" \
  "Describe this image in one or two sentences." \
  --model "meta/muse-spark-1.3" 2>&1)"
STATUS=$?
echo "$OUT"
if [ $STATUS -ne 0 ]; then
  echo "SMOKE FAIL: vision-tool: vision_proxy.py exited $STATUS"
  exit 1
fi
if [ -z "${OUT//[[:space:]]/}" ]; then
  echo "SMOKE FAIL: vision-tool: empty output"
  exit 1
fi
echo "SMOKE PASS: vision-tool"
