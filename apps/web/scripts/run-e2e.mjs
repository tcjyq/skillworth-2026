import { spawn } from "node:child_process";
import { delimiter, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createConnection } from "node:net";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = resolve(webRoot, "../..");
const python = process.platform === "win32"
  ? resolve(repositoryRoot, ".venv/Scripts/python.exe")
  : resolve(repositoryRoot, ".venv/bin/python");
const apiPort = Number(process.env.SKILLWORTH_E2E_API_PORT ?? "18011");
const webPort = Number(process.env.SKILLWORTH_E2E_WEB_PORT ?? "13001");
const baseURL = `http://127.0.0.1:${webPort}`;
const children = [];
const childErrors = new WeakMap();

function start(command, args, options) {
  const child = spawn(command, args, { ...options, shell: false, stdio: ["ignore", "inherit", "inherit"] });
  child.once("error", (error) => childErrors.set(child, error));
  children.push(child);
  return child;
}

function portIsOpen(port) {
  return new Promise((resolveResult) => {
    const socket = createConnection({ host: "127.0.0.1", port });
    socket.once("connect", () => { socket.destroy(); resolveResult(true); });
    socket.once("error", () => resolveResult(false));
    socket.setTimeout(1000, () => { socket.destroy(); resolveResult(false); });
  });
}

async function waitFor(url, child, label) {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    if (childErrors.has(child)) throw childErrors.get(child);
    if (child.exitCode !== null) throw new Error(`${label} exited before becoming ready (code ${child.exitCode})`);
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (response.ok) return;
    } catch {}
    await new Promise((resolveWait) => setTimeout(resolveWait, 400));
  }
  throw new Error(`${label} did not become ready within 120 seconds`);
}

function waitForExit(child) {
  if (childErrors.has(child)) return Promise.reject(childErrors.get(child));
  if (child.exitCode !== null) return Promise.resolve(child.exitCode);
  return new Promise((resolveExit, rejectExit) => {
    child.once("error", rejectExit);
    child.once("exit", (code, signal) => resolveExit(code ?? (signal ? 1 : 0)));
  });
}

async function stop(child) {
  if (!child || child.exitCode !== null) return;
  child.kill("SIGTERM");
  await Promise.race([
    waitForExit(child),
    new Promise((resolveWait) => setTimeout(resolveWait, 3000)),
  ]);
  if (child.exitCode === null) child.kill("SIGKILL");
}

async function main() {
  if (await portIsOpen(apiPort) || await portIsOpen(webPort)) {
    throw new Error(`E2E ports ${apiPort}/${webPort} are already in use; set SKILLWORTH_E2E_API_PORT and SKILLWORTH_E2E_WEB_PORT to free ports`);
  }
  const api = start(
    python,
    ["-m", "uvicorn", "skillworth_api.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    {
      cwd: repositoryRoot,
      env: {
        ...process.env,
        PYTHONPATH: ["packages/data-pipeline/src", "packages/analytics/src", "apps/api/src"].join(delimiter),
        SKILLWORTH_DATA_MODE: "real",
        SKILLWORTH_REAL_MODE_MANIFEST: "data/modes/freehire/current.json",
      },
    },
  );
  await waitFor(`http://127.0.0.1:${apiPort}/health`, api, "FastAPI");

  const web = start(
    process.execPath,
    [resolve(webRoot, "node_modules/next/dist/bin/next"), "start", "-p", String(webPort)],
    { cwd: webRoot, env: { ...process.env, SKILLWORTH_API_URL: `http://127.0.0.1:${apiPort}` } },
  );
  await waitFor(baseURL, web, "Next.js");

  const playwright = start(
    process.execPath,
    [resolve(webRoot, "node_modules/@playwright/test/cli.js"), "test", ...process.argv.slice(2)],
    { cwd: webRoot, env: { ...process.env, PLAYWRIGHT_BASE_URL: baseURL } },
  );
  return await waitForExit(playwright);
}

let exitCode = 1;
try {
  exitCode = await main();
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
} finally {
  for (const child of children.toReversed()) await stop(child);
}
process.exitCode = exitCode;
