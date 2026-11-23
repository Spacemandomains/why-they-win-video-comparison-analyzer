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
| youtube-mcp | `src/meta.ts` `analyzeFramesWithMeta()` + frames from its own `src/youtube.ts` `extractFrames()` (the `analyze_with_meta` tool's pipeline) | Frames at 1s and 3s of Wilfred's public video `y6EnqWGYJVU` |
| vision-tool | Its own CLI: `vision_proxy.py <frame> --model "meta/muse-spark-1.3"` → `call_meta()` backend | One frame (1s) of the sample clip |
| youtube-digest-videos-mcp | `yt_digester/meta.py` `digest_video()` — the exact backend its CLI/server dispatch to when `DIGEST_PROVIDER=meta` (Responses API, `input_video`) | Direct mp4 URL of the sample clip (Meta needs a directly reachable video URL; the repo CLI only accepts YouTube watch URLs, which Meta may reject) |
| sight-mcp | The real MCP server (`index.ts`) started with `PROVIDER=meta`, driven over stdio JSON-RPC: `initialize` → `tools/list` → `tools/call analyze_image`, routing through its `ProviderConfig`-resolved Meta endpoint + `ChatService` | One frame (1s) of the sample clip, as a local file |

Sample clip used by several jobs:
`https://download.samplelib.com/mp4/sample-5s.mp4` (5 s, ~2.8 MB).

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
