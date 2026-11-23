/**
 * Smoke driver for the youtube-mcp fork.
 *
 * Copied into the target checkout and run with `bun run smoke_driver.ts`,
 * so its relative imports resolve against the fork's own sources:
 *   ./src/meta.ts    -> resolveMetaConfig() / analyzeFramesWithMeta()
 *   ./src/youtube.ts -> extractFrames() (the same pipeline the fork's
 *                       analyze_with_meta MCP tool uses)
 *
 * Frame source: when SMOKE_SAMPLE_CLIP is set (the harness exports it),
 * frames are extracted from that LOCAL sample mp4 via extractFrames'
 * own `streamUrl` option, which skips the yt-dlp round-trip
 * (getStreamUrl). GitHub-hosted runners routinely hit YouTube's
 * bot-wall for yt-dlp, which is what failed run #1 — and the old
 * driver swallowed the real error, printing only Bun's terse
 * "Failed with exit code 1". When SMOKE_SAMPLE_CLIP is unset the
 * driver falls back to the original YouTube-URL path. Either way,
 * analyzeFramesWithMeta() is the call under test.
 *
 * Errors are reported in full: message, stack, and — for Bun `$`
 * ShellErrors — exit code plus captured stdout/stderr, so a failure
 * is diagnosable from the job log alone.
 *
 * With MODEL_API_KEY unset it fails cleanly on the config check before
 * any download or network work happens.
 */
import { analyzeFramesWithMeta, resolveMetaConfig } from "./src/meta.ts";
import { extractFrames } from "./src/youtube.ts";

const REPO = "youtube-mcp";
const VIDEO_URL = "https://www.youtube.com/watch?v=y6EnqWGYJVU";
const SAMPLE_URL = "https://download.samplelib.com/mp4/sample-5s.mp4";

function describeError(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  const parts: string[] = [`${err.name}: ${err.message}`];
  // Bun's $ throws a ShellError whose message is just
  // "Failed with exit code N"; the useful detail lives on the object.
  const anyErr = err as unknown as Record<string, unknown>;
  if (typeof anyErr.exitCode === "number") {
    parts.push(`exit code: ${anyErr.exitCode}`);
  }
  for (const key of ["stderr", "stdout"] as const) {
    const val = anyErr[key];
    if (val === undefined || val === null) continue;
    const text =
      val instanceof Uint8Array
        ? new TextDecoder().decode(val)
        : String(val);
    if (text.trim()) parts.push(`${key}:\n${text.trim()}`);
  }
  if (err.stack) parts.push(`stack:\n${err.stack}`);
  return parts.join("\n");
}

function fail(msg: string): never {
  console.log(`SMOKE FAIL: ${REPO}: ${msg}`);
  process.exit(1);
}

const cfg = resolveMetaConfig();
if (!cfg.apiKey) {
  fail(
    "MODEL_API_KEY is not set (resolveMetaConfig() resolved no key); " +
      "export MODEL_API_KEY from https://dev.meta.ai/",
  );
}
console.log(`meta config: base_url=${cfg.baseUrl} model=${cfg.model}`);

try {
  const sampleClip = process.env.SMOKE_SAMPLE_CLIP;
  const frames = sampleClip
    ? await extractFrames(SAMPLE_URL, [1, 3], { streamUrl: sampleClip })
    : await extractFrames(VIDEO_URL, [1, 3]);
  if (!frames.length) {
    fail(
      "extractFrames returned no frames" +
        (sampleClip
          ? ` (local sample clip: ${sampleClip})`
          : ` (YouTube URL: ${VIDEO_URL})`),
    );
  }
  console.log(
    `extracted ${frames.length} frame(s) with youtube-mcp's own code` +
      (sampleClip ? " from the local sample clip" : " from the YouTube URL"),
  );

  const text = await analyzeFramesWithMeta(
    frames,
    "In one or two sentences, describe what is visible in these video frames.",
  );
  if (!text || !text.trim()) fail("Meta API returned an empty response");

  console.log("model response excerpt:", text.trim().slice(0, 400));
  console.log(`SMOKE PASS: ${REPO}`);
} catch (err) {
  console.log("underlying error (full):");
  console.log(describeError(err));
  fail(err instanceof Error ? err.message : String(err));
}
