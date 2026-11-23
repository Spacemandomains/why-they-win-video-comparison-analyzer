#!/usr/bin/env python3
"""Smoke driver for the youtube-digest-videos-mcp fork.

Calls the fork's own Meta backend exactly as its CLI/server dispatch
does when DIGEST_PROVIDER=meta: yt_digester.meta.digest_video(url).
A direct mp4 URL is used because Meta's Responses API expects a
directly reachable video URL (the repo's CLI canonicalizes YouTube
URLs to watch pages, which the Meta API may reject — see meta.py).

Env:
  TARGET_DIR        checkout of Spacemandomains/youtube-digest-videos-mcp
  DIGEST_PROVIDER   must be "meta" (set by the per-repo shell script)

Exit 0 + "SMOKE PASS: youtube-digest-videos-mcp" on success;
"SMOKE FAIL: ..." + exit 1 otherwise. With MODEL_API_KEY unset it
fails cleanly on the config check before any network call.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = "youtube-digest-videos-mcp"
SAMPLE_URL = "https://download.samplelib.com/mp4/sample-5s.mp4"


def fail(msg: str) -> int:
    print(f"SMOKE FAIL: {REPO}: {msg}")
    return 1


def main() -> int:
    target = Path(os.environ.get("TARGET_DIR", ".")).resolve()
    if not (target / "yt_digester" / "meta.py").exists():
        return fail(f"fork sources not found under {target}")
    sys.path.insert(0, str(target))

    from yt_digester import config

    if config.digest_provider() != "meta":
        return fail("DIGEST_PROVIDER is not 'meta'")
    if not config.meta_api_key():
        return fail(
            "MODEL_API_KEY is not set (config.meta_api_key() is empty); "
            "export MODEL_API_KEY from https://dev.meta.ai/"
        )
    print(
        f"meta config: base_url={config.meta_base_url()} "
        f"model={config.meta_model()}"
    )

    from yt_digester import meta

    try:
        result = meta.digest_video(SAMPLE_URL)
    except Exception as exc:  # noqa: BLE001 - report as smoke failure
        return fail(f"Meta digest call failed: {exc}")

    text = (
        (result.get("full_text") or "")
        or (result.get("summary") or "")
    ).strip()
    if not text:
        return fail(f"digest returned no full_text/summary: {result!r:.300}")
    print("model response excerpt:", text[:400])
    print(f"SMOKE PASS: {REPO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
