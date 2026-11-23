/**
 * Smoke driver for the youtube-mcp fork.
 *
 * Copied into the target checkout and run with `bun run smoke_driver.ts`,
 * so its relative imports resolve against the fork's own sources:
 *   ./src/meta.ts    -> resolveMetaConfig() / analyzeFramesWithMeta()
 *   ./src/youtube.ts -> extractFrames() (the same pipeline the fork's
 *                       analyze_with_meta MCP tool uses)
 *
 * With MODEL_API_KEY unset it fails cleanly on the config check before
 * any download or network work happens.
 */
import { analyzeFramesWithMeta, resolveMetaConfig } from "./src/meta.ts";
import { extractFrames } from "./src/youtube.ts";

const REPO = "youtube-mcp";
const VIDEO_URL = "https://www.youtube.com/watch?v=y6EnqWGYJVU";

function fail(msg: string): never {
  console.error(`SMOKE FAIL: ${REPO}: ${msg}`);
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
  const frames = await extractFrames(VIDEO_URL, [1, 3]);
  if (!frames.length) fail("extractFrames returned no frames");
  console.log(`extracted ${frames.length} frame(s) with youtube-mcp's own code`);

  const text = await analyzeFramesWithMeta(
    frames,
    "In one or two sentences, describe what is visible in these video frames.",
  );
  if (!text || !text.trim()) fail("Meta API returned an empty response");

  console.log("model response excerpt:", text.trim().slice(0, 400));
  console.log(`SMOKE PASS: ${REPO}`);
} catch (err) {
  fail(err instanceof Error ? err.message : String(err));
}
