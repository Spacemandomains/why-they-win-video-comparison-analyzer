/**
 * Smoke driver for the sight-mcp fork.
 *
 * Copied into the target checkout and run with `node smoke_driver.mjs`.
 * It spawns the fork's REAL MCP server (index.ts, via bun) with
 * PROVIDER=meta, then speaks newline-delimited JSON-RPC over stdio:
 *   1. initialize
 *   2. notifications/initialized
 *   3. tools/list            (asserts analyze_image is offered)
 *   4. tools/call analyze_image on a local frame image
 * Step 4 routes through the server's own ProviderConfig-resolved Meta
 * endpoint + ChatService, i.e. a real live Meta Model API call made by
 * the fork's own code.
 *
 * Env:
 *   SMOKE_FRAME   absolute path to a local .jpg frame to analyze
 *
 * With MODEL_API_KEY unset the server exits at startup with
 * "MODEL_API_KEY environment variable is required ..." — the driver
 * reports that as a clean SMOKE FAIL (expected in dry-runs).
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

const REPO = "sight-mcp";
const frame = process.env.SMOKE_FRAME || "";
const INIT_TIMEOUT_MS = 60_000;
const CALL_TIMEOUT_MS = 240_000;

function fail(msg) {
  console.error(`SMOKE FAIL: ${REPO}: ${msg}`);
  process.exit(1);
}

if (!frame || !existsSync(frame)) {
  fail("SMOKE_FRAME is unset or the file does not exist");
}

const child = spawn("bun", ["run", "index.ts"], {
  cwd: process.cwd(),
  env: { ...process.env, PROVIDER: "meta" },
  stdio: ["pipe", "pipe", "pipe"],
});

let stderrBuf = "";
child.stderr.on("data", (d) => {
  stderrBuf += d.toString();
});

/** Most informative line of the server's stderr (bun prints a code frame
 * and a version footer around the actual error line). */
function stderrExcerpt() {
  const lines = stderrBuf
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return "";
  const informative = lines.find((l) =>
    /environment variable is required|MODEL_API_KEY|^error:/i.test(l),
  );
  return `: ${(informative ?? lines[lines.length - 1]).slice(0, 300)}`;
}

let stdoutBuf = "";
const pending = new Map();
child.stdout.on("data", (d) => {
  stdoutBuf += d.toString();
  let idx;
  while ((idx = stdoutBuf.indexOf("\n")) >= 0) {
    const line = stdoutBuf.slice(0, idx).trim();
    stdoutBuf = stdoutBuf.slice(idx + 1);
    if (!line) continue;
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      continue; // ignore non-JSON noise on stdout
    }
    if (msg.id !== undefined && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});

let childExited = null;
child.on("exit", (code) => {
  childExited = code;
  for (const [, resolve] of pending) resolve(null);
  pending.clear();
});

function send(obj) {
  child.stdin.write(JSON.stringify(obj) + "\n");
}

function request(id, method, params, timeoutMs) {
  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      pending.delete(id);
      resolve(undefined); // timeout marker
    }, timeoutMs);
    pending.set(id, (msg) => {
      clearTimeout(timer);
      resolve(msg);
    });
    send({ jsonrpc: "2.0", id, method, params });
  });
}

try {
  const init = await request(
    1,
    "initialize",
    {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "meta-smoke", version: "1.0.0" },
    },
    INIT_TIMEOUT_MS,
  );
  if (init === null) {
    fail("server exited before initialize completed" + stderrExcerpt());
  }
  if (init === undefined) fail("initialize timed out");
  if (init.error) fail(`initialize error: ${JSON.stringify(init.error)}`);
  console.log(
    `initialized: server=${init.result?.serverInfo?.name ?? "?"} ` +
      `protocol=${init.result?.protocolVersion ?? "?"}`,
  );

  send({ jsonrpc: "2.0", method: "notifications/initialized" });

  const list = await request(2, "tools/list", {}, INIT_TIMEOUT_MS);
  if (!list || list.error) {
    fail(`tools/list failed: ${JSON.stringify(list?.error ?? list)}`);
  }
  const toolNames = (list.result?.tools ?? []).map((t) => t.name);
  console.log(`tools offered: ${toolNames.join(", ") || "(none)"}`);
  if (!toolNames.includes("analyze_image")) {
    fail("analyze_image tool not offered by the server");
  }

  const call = await request(
    3,
    "tools/call",
    {
      name: "analyze_image",
      arguments: {
        image: path.resolve(frame),
        prompt: "Describe this image in one sentence.",
      },
    },
    CALL_TIMEOUT_MS,
  );
  if (call === null) {
    fail("server exited during tools/call" + stderrExcerpt());
  }
  if (call === undefined) fail("tools/call analyze_image timed out");
  if (call.error) fail(`tools/call error: ${JSON.stringify(call.error)}`);

  const text = (call.result?.content ?? [])
    .filter((c) => c.type === "text")
    .map((c) => c.text)
    .join("\n")
    .trim();
  if (!text) fail("analyze_image returned no text");
  if (text.startsWith("Error:")) fail(`analyze_image returned: ${text.slice(0, 300)}`);

  console.log("model response excerpt:", text.slice(0, 400));
  console.log(`SMOKE PASS: ${REPO}`);
  child.kill();
  process.exit(0);
} catch (err) {
  child.kill();
  fail(err instanceof Error ? err.message : String(err));
}
