#!/usr/bin/env bash
# Dispatcher for the Meta smoke tests.
#
#   bash smoke/run_smoke.sh <repo-name>
#
# Expects (set by .github/workflows/meta-smoke.yml, or by hand locally):
#   MODEL_API_KEY   Meta Model API key (never written to any file)
#   TARGET_DIR      checkout of the fork under test
#                   (default: ../target relative to this repo's root)
#
# Each per-repo script prints "SMOKE PASS: <repo>" on success, or
# "SMOKE FAIL: <repo>: <reason>" and exits non-zero on failure.
set -u

REPO="${1:-}"
SMOKE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_DIR="$(cd "$SMOKE_DIR/.." && pwd)"
export SMOKE_DIR HARNESS_DIR
export TARGET_DIR="${TARGET_DIR:-$HARNESS_DIR/../target}"
export SMOKE_WORK="${SMOKE_WORK:-$(mktemp -d)}"
mkdir -p "$SMOKE_WORK"

# Shared helper: fetch the 5-second sample clip used by several jobs.
fetch_sample_clip() {
  local clip="$SMOKE_WORK/sample-5s.mp4"
  if [ ! -f "$clip" ]; then
    curl -fsSL "https://download.samplelib.com/mp4/sample-5s.mp4" -o "$clip"
  fi
  echo "$clip"
}
export -f fetch_sample_clip

case "$REPO" in
  video-ai-analyzer|mcp-video|visualizer|youtube-mcp|vision-tool|youtube-digest-videos-mcp|sight-mcp)
    exec bash "$SMOKE_DIR/repos/$REPO.sh"
    ;;
  *)
    echo "usage: run_smoke.sh <video-ai-analyzer|mcp-video|visualizer|youtube-mcp|vision-tool|youtube-digest-videos-mcp|sight-mcp>" >&2
    exit 2
    ;;
esac
