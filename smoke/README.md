# Meta Smoke Tests — all 7 video-analyzer forks

One manually-triggered GitHub Actions workflow
(`.github/workflows/meta-smoke.yml`) that live-tests the Meta Model API
(Muse Spark 1.3) integration in each of Wilfred's 7 video-analyzer forks.
Every job makes the **smallest real live call** through that fork's **own**
Meta code path — no re-implementations, no mocks — and prints
`SMOKE PASS: <repo>` or `SMOKE FAIL: <repo>: <reason>`.

Why GitHub Actions? The forks read the key from the `MODEL_API_KEY`
environment variable and call `https://api.meta.ai/v1`. That call cannot
originate from the Muse VM (egress-blocked), so the tests run on GitHub's
runners, which have normal internet access.

## Setup (one time)

Add the Meta Model API key as a repository secret **in this repo**
(`Spacemandomains/video-ai-analyzer`):

1. Open **Settings → Secrets and variables → Actions**.
2. **New repository secret**
   - Name: `MODEL_API_KEY`
   - Value: the Meta Model API key from https://dev.meta.ai/
     (the "Playground" key; it is never stored in any file in any repo).

## Running

Actions tab → **Meta Smoke Tests** → **Run workflow**. All 7 jobs run in
parallel (`fail-fast: false`), each capped at 15 minutes (most finish in
a few). A green job means that fork's Meta code path completed a real
call to Muse Spark; a red job's log ends with `SMOKE FAIL: <repo>: ...`.

## Reading results

- The workflow run page shows one job per fork with its full log inline.
- Each job also uploads its log as a downloadable artifact named
  `smoke-<repo>` (e.g. `smoke-mcp-video`).
- Inside a log, look for the `meta config:` line (base URL + model the
  fork resolved), the `model response excerpt:` (the first ~400 chars of
  Muse Spark's actual reply), and the final `SMOKE PASS` / `SMOKE FAIL`
  line.

## What each job tests

| Job | Fork code path exercised | Input |
| --- | --- | --- |
| video-ai-analyzer | Its own CLI: `video-ai analyze <url> --provider meta` (first-class `meta` provider, Chat Completions via the OpenAI client) | Wilfred's public video `y6EnqWGYJVU`, capped at 3 frames / 480p |
| mcp-video | `src/mcp_video/meta.py` `analyze_frames_with_meta()` + frames from its own `src/mcp_video/video.py` `extract_uniform_frames()` | 2 frames from a 5-second sample clip |
| visualizer | `skills/va/scripts/meta_watch.sh` — local-file branch: Meta **Files API** upload (`purpose=user_data`) → Responses API with `input_file` | The 5-second sample mp4 as a local file |
| youtube-mcp | `src/meta.ts` `analyzeFramesWithMeta()` + frames from its own `src/youtube.ts` `extractFrames()` (the `analyze_with_meta` tool's pipeline) | Frames at 1s and 3s of the local sample mp4, fed via `extractFrames`' own `streamUrl` option — a substitution for the YouTube URL used before run #2: GitHub runners hit YouTube's bot-wall in `yt-dlp` (`getStreamUrl`), which failed run #1 with the real error swallowed. `analyzeFramesWithMeta()` remains the call under test; the driver falls back to the YouTube URL when no local clip is provided, and now prints the full underlying error (message, stack, shell exit code + stderr) on failure |
| vision-tool | Its own CLI: `vision_proxy.py <frame> --model "meta/muse-spark-1.3"` → `call_meta()` backend | One frame (1s) of the sample clip |
| youtube-digest-videos-mcp | `yt_digester/meta.py` `digest_video()` — the exact backend its CLI/server dispatch to when `DIGEST_PROVIDER=meta` (Responses API, `input_video`) | Direct mp4 URL of the sample clip (Meta needs a directly reachable video URL; the repo CLI only accepts YouTube watch URLs, which Meta may reject) |
| sight-mcp | The real MCP server (`index.ts`) started with `PROVIDER=meta`, driven over stdio JSON-RPC: `initialize` → `tools/list` → `tools/call analyze_image`, routing through its `ProviderConfig`-resolved Meta endpoint + `ChatService` | One frame (1s) of the sample clip, as a local file |

Sample clip used by several jobs:
`https://download.samplelib.com/mp4/sample-5s.mp4` (5 s, ~2.8 MB).

## Results

### Run #1 — 2026-11-22 (workflow run 45115744444): 3 pass / 4 fail

| Job | Result | Cause |
| --- | --- | --- |
| mcp-video | ✅ PASS | — |
| visualizer | ✅ PASS | — |
| youtube-digest-videos-mcp | ✅ PASS | — |
| video-ai-analyzer | ❌ FAIL | The harness `smoke/` folder sits in this repo's root, so setuptools flat-layout discovery found `['smoke', 'video_analyzer']` and the pip build of the target checkout failed |
| vision-tool | ❌ FAIL | `ffmpeg: command not found` on the runner during frame extraction |
| sight-mcp | ❌ FAIL | `ffmpeg: command not found` on the runner (exit 127) |
| youtube-mcp | ❌ FAIL | `yt-dlp`/YouTube step failed with the real error swallowed — the log showed only "Failed with exit code 1" |

Fixes landed after run #1, targeting run #2 (harness only — no fork
source was changed):

- **video-ai-analyzer:** its smoke script now pip-installs from a clean
  copy of the target checkout with `smoke/` and `.github/` removed.
- **vision-tool / sight-mcp / youtube-mcp:** the workflow jobs now
  install `ffmpeg` via apt before running the smoke script.
- **youtube-mcp:** frames are extracted from the local sample mp4 via
  `extractFrames`' `streamUrl` option (no yt-dlp/YouTube round-trip),
  and the driver prints the full caught error — message, stack, and
  any shell exit code/stdout/stderr — before exiting non-zero.

### Run #2 — workflow run 45116540576: 5 pass / 2 fail

| Job | Result | Cause |
| --- | --- | --- |
| mcp-video | ✅ PASS | — |
| visualizer | ✅ PASS | — |
| youtube-mcp | ✅ PASS | — |
| youtube-digest-videos-mcp | ✅ PASS | — |
| sight-mcp | ✅ PASS | — |
| video-ai-analyzer | ❌ FAIL | The clean-copy pip build fix worked, but the CLI's own dependency check then failed: `Missing dependencies: ffmpeg, ffprobe` — its workflow job had no ffmpeg install step |
| vision-tool | ❌ FAIL | ffmpeg fix worked and a frame was extracted; the backend race selected ☆ Meta Muse Spark 1.3 (the only backend with a key; 30/31 skipped), but it failed with `Backend timed out after 4s` |

Fix applied after run #2, targeting run #3 (harness only):

- **video-ai-analyzer:** its workflow job now installs `ffmpeg` via apt
  before running the smoke script (the same "Install ffmpeg" step the
  vision-tool / sight-mcp / youtube-mcp jobs already had), which also
  provides `ffprobe`.

No harness fix was applied for **vision-tool**: the 4-second limit is
hardcoded in the fork's own source, with no supported configuration.
In `vision_proxy.py`, `analyze()` sets the local timeout variables at
lines 2012–2014 — `PER_CALL_TIMEOUT = 12`, `TOTAL_TIMEOUT = 25`,
`FAST_TIMEOUT = 4` — and line 2029 runs the first sequential backend
attempts through `_call_with_timeout(fn, FAST_TIMEOUT)`.
`load_config()` only reads a fixed list of keys (API keys, endpoints,
`DEFAULT_MODEL`); neither it, `config.json.example`, nor the CLI
argument parser (`file`, `prompt`, `--model`, `--models`,
`--refresh-profile`) exposes any timeout setting. The smallest source
change — **not applied; it needs Wilfred's decision** — is one line in
the vision-tool fork: `vision_proxy.py:2014`, change
`FAST_TIMEOUT = 4` to `FAST_TIMEOUT = 60`.

## Layout

```
.github/workflows/meta-smoke.yml   # the workflow (workflow_dispatch only)
smoke/run_smoke.sh                 # dispatcher: env contract + sample-clip fetch
smoke/repos/<repo>.sh              # per-fork setup + invocation
smoke/drivers/                     # small drivers for forks without a CLI entry point
  mcp_video_smoke.py
  youtube_digest_smoke.py
  youtube_mcp_smoke.ts             # copied into the target checkout, run with bun
  sight_mcp_smoke.mjs              # copied into the target checkout, run with node
```

## Local dry-run (no key)

With `MODEL_API_KEY` unset, every job fails cleanly with a
"MODEL_API_KEY is not set"-style message instead of crashing — that is
the expected behaviour and how the harness was validated locally:

```bash
git clone https://github.com/Spacemandomains/video-ai-analyzer harness
git clone https://github.com/Spacemandomains/mcp-video target
TARGET_DIR=$PWD/target bash harness/smoke/run_smoke.sh mcp-video
# -> SMOKE FAIL: mcp-video: MODEL_API_KEY is not set ...
```

## Cost

Each run is a handful of small Spark calls (a few frames / one 5-second
clip per fork) — on the order of a few US cents total per full workflow
run at Muse Spark 1.3 list prices.
