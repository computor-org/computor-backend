// Bring the Computor extension in this workspace up to the version the
// instance has approved, in place. See README.md "Extension updates".
//
// The approved version is the newest non-yanked version in the backend's own
// extension registry (/extensions/<id>/versions); the backend registers the
// release pinned in coder/approved_extension.json there at startup. The VSIX is
// fetched from the same
// backend (the only API a workspace can reach), its sha256 is checked against
// the registry entry, and only a version NEWER than the installed one is
// installed: an image built later from a newer commit is never shadowed, and a
// downgrade needs a template push. Every failure leaves the installed
// extension as it is and exits 0, so a workspace without a reachable backend
// starts exactly as before.
//
// Runs with code-server's bundled node (no other runtime is guaranteed in
// every image). Configuration comes from the environment:
//   COMPUTOR_BACKEND_URL              backend base URL (required)
//   COMPUTOR_AUTH_TOKEN               workspace API token (required)
//   COMPUTOR_EXTENSION_ID             default computor-org.computor
//   CODE_SERVER_BIN                   default code-server
//   CODE_SERVER_EXTENSIONS_DIR        default /opt/code-server/extensions
//   COMPUTOR_EXTENSION_UPDATE_MARKER  written after an install, read by the
//                                     running extension to offer a reload

import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";

const run = promisify(execFile);
const env = process.env;
const extensionId = (env.COMPUTOR_EXTENSION_ID || "computor-org.computor").toLowerCase();
const codeServer = env.CODE_SERVER_BIN || "code-server";
const extensionsDir = env.CODE_SERVER_EXTENSIONS_DIR || "/opt/code-server/extensions";
const marker = env.COMPUTOR_EXTENSION_UPDATE_MARKER || "";

function log(message) {
  console.log(`${new Date().toISOString()} extension-sync: ${message}`);
}

// Release versions only (x.y.z); a pre-release never becomes the approved one.
function parse(version) {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(version || "").trim());
  return match ? match.slice(1).map(Number) : null;
}

function newer(a, b) {
  for (let i = 0; i < 3; i++) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return false;
}

async function api(path, timeoutMs) {
  const base = (env.COMPUTOR_BACKEND_URL || "").replace(/\/+$/, "");
  const response = await fetch(`${base}${path}`, {
    headers: { "X-API-Token": env.COMPUTOR_AUTH_TOKEN || "" },
    signal: AbortSignal.timeout(timeoutMs),
  });
  return response;
}

async function installedVersion() {
  const { stdout } = await run(
    codeServer,
    ["--extensions-dir", extensionsDir, "--list-extensions", "--show-versions"],
    { timeout: 60_000 },
  );
  for (const line of stdout.split("\n")) {
    const at = line.trim().lastIndexOf("@");
    if (at > 0 && line.trim().slice(0, at).toLowerCase() === extensionId) {
      return line.trim().slice(at + 1);
    }
  }
  return null;
}

async function approvedVersion() {
  const response = await api(`/extensions/${extensionId}/versions?limit=100`, 30_000);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`version list: HTTP ${response.status}`);
  const payload = await response.json();
  let best = null;
  for (const item of payload.items || []) {
    const parsed = parse(item && item.version);
    if (!parsed || item.yanked || !/^[0-9a-f]{64}$/.test(item.sha256 || "")) continue;
    if (!best || newer(parsed, best.parsed)) best = { ...item, parsed };
  }
  return best;
}

async function main() {
  if (!env.COMPUTOR_BACKEND_URL || !env.COMPUTOR_AUTH_TOKEN) {
    log("no backend URL or workspace token; keeping the installed extension");
    return;
  }
  const approved = await approvedVersion();
  if (!approved) {
    log("the registry approves no version; keeping the installed extension");
    return;
  }
  const installed = await installedVersion();
  const current = parse(installed);
  if (current && !newer(approved.parsed, current)) {
    log(`installed ${installed}, approved ${approved.version}: nothing to do`);
    return;
  }

  const response = await api(
    `/extensions/${extensionId}/download?version=${encodeURIComponent("==" + approved.version)}`,
    300_000,
  );
  if (!response.ok) throw new Error(`download: HTTP ${response.status}`);
  const vsix = Buffer.from(await response.arrayBuffer());
  const digest = createHash("sha256").update(vsix).digest("hex");
  if (digest !== approved.sha256) {
    throw new Error(`sha256 mismatch for ${approved.version}: got ${digest}, registry ${approved.sha256}`);
  }

  const dir = await mkdtemp(join(tmpdir(), "computor-extension-"));
  try {
    const file = join(dir, `${extensionId}-${approved.version}.vsix`);
    await writeFile(file, vsix);
    await run(
      codeServer,
      ["--extensions-dir", extensionsDir, "--install-extension", file, "--force"],
      { timeout: 180_000 },
    );
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
  const now = await installedVersion();
  if (now !== approved.version) {
    throw new Error(`install reported success but ${now || "nothing"} is installed`);
  }
  if (marker) {
    await writeFile(marker, JSON.stringify({
      version: approved.version,
      previous: installed,
      installedAt: new Date().toISOString(),
    }) + "\n");
  }
  log(`installed ${approved.version} (was ${installed || "absent"}, sha256 ${digest})`);
}

main().catch((error) => {
  log(`WARN ${error && error.message ? error.message : error}; keeping the installed extension`);
});
