#!/usr/bin/env bash
# Smoke: visualizer — runs the fork's own skills/va/scripts/meta_watch.sh
# against a small LOCAL mp4, which exercises its Meta Files API upload
# path (purpose=user_data) followed by a Responses API call.
# With MODEL_API_KEY unset the script exits 1 with
# "FEHLER: MODEL_API_KEY nicht gesetzt" — the expected clean failure.
set -u

CLIP="$(fetch_sample_clip)" || { echo "SMOKE FAIL: visualizer: could not download sample clip"; exit 1; }

OUT="$(bash "$TARGET_DIR/skills/va/scripts/meta_watch.sh" "$CLIP" \
  "Describe what happens in this video in two sentences." 2>&1)"
STATUS=$?
echo "$OUT"
if [ $STATUS -ne 0 ]; then
  echo "SMOKE FAIL: visualizer: meta_watch.sh exited $STATUS"
  exit 1
fi
if [ -z "${OUT//[[:space:]]/}" ]; then
  echo "SMOKE FAIL: visualizer: empty response from Meta"
  exit 1
fi
echo "SMOKE PASS: visualizer"
