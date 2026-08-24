import { spawn } from "node:child_process";
import { access, readFile, rm } from "node:fs/promises";
import { delimiter, dirname, relative, resolve } from "node:path";
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
const realMode = process.argv.includes("--real");
const captureReview = process.argv.includes("--capture-3d-review");
const mode = realMode ? "real" : "demo";
const playwrightArgs = process.argv.slice(2).filter((argument) => !["--real", "--capture-3d-review"].includes(argument));
const realManifest = resolve(repositoryRoot, process.env.SKILLWORTH_REAL_MODE_MANIFEST ?? "data/modes/freehire/current.json");
const demoRoot = resolve(repositoryRoot, `.tmp/e2e-demo-${process.pid}`);
const demoManifest = resolve(demoRoot, "manifest.json");
const playwrightBrowsersPath = process.env.PLAYWRIGHT_BROWSERS_PATH ?? resolve(repositoryRoot, ".tmp/playwright-browsers");
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

async function run(command, args, options, label) {
  const child = start(command, args, options);
  const code = await waitForExit(child);
  if (code !== 0) throw new Error(`${label} failed (code ${code})`);
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

async function requireRealManifest() {
  try {
    const payload = JSON.parse(await readFile(realManifest, "utf8"));
    for (const field of ["warehouse_path", "graph_edges_path", "quality_report_path"]) {
      if (!payload[field]) throw new Error(`missing ${field}`);
      await access(resolve(repositoryRoot, payload[field]));
    }
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    throw new Error(
      `Real Mode fixture/manifest not available. Provide the local frozen Freehire v6 artifacts via SKILLWORTH_REAL_MODE_MANIFEST. (${detail})`,
    );
  }
}

async function prepareDemo() {
  const relativeRoot = relative(repositoryRoot, demoRoot);
  if (relativeRoot.startsWith("..") || relativeRoot === "") {
    throw new Error("Refusing to build Demo data outside the repository temporary directory");
  }
  await run(
    python,
    ["-m", "app.cli", "build-demo-dataset", "--output-root", demoRoot],
    {
      cwd: repositoryRoot,
      env: { ...process.env, PYTHONPATH: ["packages/data-pipeline/src", "packages/analytics/src"].join(delimiter) },
    },
    "Demo dataset build",
  );
}

async function main() {
  await access(python);
  if (await portIsOpen(apiPort) || await portIsOpen(webPort)) {
    throw new Error(`E2E ports ${apiPort}/${webPort} are already in use; set SKILLWORTH_E2E_API_PORT and SKILLWORTH_E2E_WEB_PORT to free ports`);
  }
  if (realMode) await requireRealManifest();
  else await prepareDemo();

  const api = start(
    python,
    ["-m", "uvicorn", "skillworth_api.main:app", "--host", "127.0.0.1", "--port", String(apiPort)],
    {
      cwd: repositoryRoot,
      env: {
        ...process.env,
        PYTHONPATH: ["packages/data-pipeline/src", "packages/analytics/src", "apps/api/src"].join(delimiter),
        SKILLWORTH_DATA_MODE: mode,
        ...(realMode
          ? { SKILLWORTH_REAL_MODE_MANIFEST: realManifest }
          : { SKILLWORTH_DEMO_MODE_MANIFEST: demoManifest }),
      },
    },
  );
  await waitFor(`http://127.0.0.1:${apiPort}/health`, api, "FastAPI");

  const nextEnvironment = { ...process.env, SKILLWORTH_API_URL: `http://127.0.0.1:${apiPort}` };
  await run(
    process.execPath,
    [resolve(webRoot, "node_modules/next/dist/bin/next"), "build"],
    { cwd: webRoot, env: nextEnvironment },
    "Next.js production build",
  );
  const web = start(
    process.execPath,
    [resolve(webRoot, "node_modules/next/dist/bin/next"), "start", "-p", String(webPort)],
    { cwd: webRoot, env: nextEnvironment },
  );
  await waitFor(baseURL, web, "Next.js");

  const playwright = start(
    process.execPath,
    captureReview
      ? [resolve(webRoot, "scripts/capture-3d-skill-field-review.mjs")]
      : [resolve(webRoot, "node_modules/@playwright/test/cli.js"), "test", ...playwrightArgs],
    { cwd: webRoot, env: { ...process.env, PLAYWRIGHT_BASE_URL: baseURL, PLAYWRIGHT_BROWSERS_PATH: playwrightBrowsersPath, SKILLWORTH_E2E_MODE: mode } },
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
  if (!realMode) await rm(demoRoot, { recursive: true, force: true });
}
process.exitCode = exitCode;
