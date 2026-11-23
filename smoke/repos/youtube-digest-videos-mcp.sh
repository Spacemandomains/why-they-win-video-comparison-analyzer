#!/usr/bin/env bash
# Smoke: youtube-digest-videos-mcp — Python driver calling the fork's own
# Meta backend (yt_digester/meta.py digest_video, the DIGEST_PROVIDER=meta
# path) with a direct mp4 URL. The repo's CLI only accepts YouTube URLs
# and canonicalizes them to watch URLs, which the Meta API may reject;
# meta.digest_video is the exact code path the CLI/server dispatch to.
set -euo pipefail

cd "$TARGET_DIR"
python3 -m pip install --quiet -r requirements.txt

DIGEST_PROVIDER=meta TARGET_DIR="$TARGET_DIR" \
  python3 "$SMOKE_DIR/drivers/youtube_digest_smoke.py"
