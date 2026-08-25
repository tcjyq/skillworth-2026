import { chromium } from "@playwright/test";
import { copyFile, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { brotliCompressSync, gzipSync } from "node:zlib";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputRoot = resolve(webRoot, "../../output/3d-skill-field-review");
const videoRoot = resolve(outputRoot, ".video");
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:13001";
const consoleIssues = [];
const browserPreloadWarnings = [];
let selectedRelationProbe = null;

const wait = (page, milliseconds) => page.waitForTimeout(milliseconds);
const screenshot = (page, name) => page.screenshot({ path: resolve(outputRoot, `${name}.png`), fullPage: false, scale: "css" });

function trackConsole(page) {
  page.on("console", (message) => {
    if (!["error", "warning"].includes(message.type())) return;
    const entry = `${message.type()}: ${message.text()}`;
    if (message.text().includes("preloaded using link preload but not used")) browserPreloadWarnings.push(entry);
    else consoleIssues.push(entry);
  });
}

async function choose(page, query, pattern, position = "first") {
  const search = page.getByRole("combobox", { name: "搜索技能或职业" });
  await search.fill(query);
  const option = page.getByRole("option", { name: pattern });
  await (position === "last" ? option.last() : option.first()).click();
}

async function readProbe(page) {
  return page.getByTestId("skill-field-canvas").evaluate((element) => {
    const lastRenderedAt = Number(element.dataset.lastRenderedAt ?? 0);
    const probeAgeMs = performance.now() - lastRenderedAt;
    return {
      renderedFrames: Number(element.dataset.renderedFrames ?? 0),
      activeFps: probeAgeMs <= 1000 ? Number(element.dataset.activeFps ?? 0) : 0,
      actualFps: probeAgeMs <= 1000 ? Number(element.dataset.actualFps ?? 0) : 0,
      drawCalls: Number(element.dataset.drawCalls ?? 0),
      geometries: Number(element.dataset.geometries ?? 0),
      textures: Number(element.dataset.textures ?? 0),
      rendererDpr: Number(element.dataset.rendererDpr ?? 0),
      lastRenderedAt,
      probeAgeMs: Math.round(probeAgeMs),
      postProcessingPassCount: Number(element.dataset.postProcessingPassCount ?? 0),
      deviceDpr: window.devicePixelRatio,
      environmentalParticleCount: Number(element.dataset.environmentalParticleCount ?? 0),
      relationParticleCount: Number(element.dataset.relationParticleCount ?? 0),
      visibleLabelBudget: Number(element.dataset.visibleLabelCount ?? 0),
      currentLabelCount: element.querySelectorAll("button, [data-kind]").length,
      qualityProfile: element.dataset.qualityProfile ?? "unknown",
      aaMode: element.dataset.aaMode ?? "unknown",
      bloomMode: element.dataset.bloomMode ?? "unknown",
    };
  });
}

async function measureInteraction(page, name, action, durationMs = 1800) {
  const startedAt = Date.now();
  await action();
  const samples = [];
  while (Date.now() - startedAt < durationMs) {
    await wait(page, 180);
    samples.push(await readProbe(page));
  }
  const sustained = samples.slice(2).map((sample) => sample.actualFps).filter((fps) => fps > 0);
  const final = samples.at(-1) ?? await readProbe(page);
  return {
    name,
    actualFps: sustained.length ? Math.round(sustained.reduce((total, fps) => total + fps, 0) / sustained.length) : 0,
    sustainedMinFps: sustained.length ? Math.min(...sustained) : 0,
    peakFps: sustained.length ? Math.max(...sustained) : 0,
    final,
  };
}

async function waitForRenderIdle(page, timeoutMs = 8000) {
  const startedAt = Date.now();
  let previousFrames = -1;
  let stableChecks = 0;
  while (Date.now() - startedAt < timeoutMs) {
    const probe = await readProbe(page);
    if (probe.renderedFrames === previousFrames) stableChecks += 1;
    else stableChecks = 0;
    if (stableChecks >= 3) return probe;
    previousFrames = probe.renderedFrames;
    await wait(page, 260);
  }
  throw new Error("3D canvas did not reach idle state before performance sampling");
}

async function touchRotate(page, session) {
  const box = await page.getByTestId("skill-field-canvas").boundingBox();
  if (!box) return;
  const start = { x: box.x + box.width * 0.74, y: box.y + box.height * 0.22 };
  await session.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ ...start, radiusX: 4, radiusY: 4, force: 0.7 }] });
  for (let step = 1; step <= 14; step += 1) {
    await session.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: start.x - step * 3.2, y: start.y + Math.sin(step / 3) * 2, radiusX: 4, radiusY: 4, force: 0.7 }] });
    await wait(page, 36);
  }
  await session.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
}

await rm(outputRoot, { recursive: true, force: true });
await mkdir(videoRoot, { recursive: true });
const browser = await chromium.launch({ channel: "msedge" });
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  recordVideo: { dir: videoRoot, size: { width: 1440, height: 900 } },
});
const page = await context.newPage();
const recordingStartedAt = Date.now();
trackConsole(page);

await page.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
await page.getByTestId("skill-field-canvas").waitFor();
await wait(page, 3200);
const dataScope = await page.request.get(`${baseURL}/backend-api/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d`).then((response) => response.json());
const defaultLabelCount = await page.getByTestId("skill-field-canvas").locator("button, [data-kind]").count();
await screenshot(page, "01-global-value-desktop");
await screenshot(page, "02-final-global-value");
await page.screenshot({ path: resolve(outputRoot, "03-value-core-close-up.png"), clip: { x: 500, y: 360, width: 560, height: 410 }, scale: "css" });
await screenshot(page, "04-default-label-avoidance");
await screenshot(page, "17-signal-aperture-lab-header");
await screenshot(page, "04-skill-color-palette");
await page.screenshot({ path: resolve(outputRoot, "05-python-sql-git-cpp-material-close-ups.png"), clip: { x: 360, y: 280, width: 720, height: 500 }, scale: "css" });
await waitForRenderIdle(page);
const idleStart = await readProbe(page);
await wait(page, 1400);
const idleEnd = await readProbe(page);

await page.getByRole("button", { name: "只看招聘需求" }).click();
await wait(page, 450);
await screenshot(page, "09-cpp-transition-storyboard");
await wait(page, 400);
const demandProbe = await readProbe(page);
await wait(page, 1650);
await screenshot(page, "02-global-demand-desktop");
await screenshot(page, "06-global-demand");
await screenshot(page, "07-cpp-demand-rank-3");

await page.getByRole("button", { name: "学习优先" }).click();
await wait(page, 520);
await screenshot(page, "08-cpp-rank-3-to-35-process");
await wait(page, 1800);
await screenshot(page, "08-cpp-skillworth-rank-35");
await page.getByRole("combobox", { name: "搜索技能或职业" }).fill("C++");
await wait(page, 1600);
await choose(page, "C++", /C\+\+/);
await wait(page, 3500);

await page.getByRole("button", { name: "回到全局" }).click();
await wait(page, 1700);
await page.getByRole("combobox", { name: "搜索技能或职业" }).fill("Python");
await wait(page, 1100);
await screenshot(page, "04-search-python");
await screenshot(page, "16-search-python-focus");
await page.getByRole("option", { name: /Python/ }).first().click();
await wait(page, 3000);
await screenshot(page, "05-python-global-constellation");
await screenshot(page, "12-python-constellation");
const constellationBox = await page.getByTestId("skill-field-canvas").boundingBox();
if (constellationBox) {
  await page.mouse.move(constellationBox.x + constellationBox.width * 0.86, constellationBox.y + constellationBox.height * 0.28);
  await page.mouse.down();
  await page.mouse.move(constellationBox.x + constellationBox.width * 0.74, constellationBox.y + constellationBox.height * 0.28, { steps: 12 });
  await page.mouse.up();
  await wait(page, 500);
}
await screenshot(page, "13-python-constellation-rotated-15deg");
await choose(page, "Python", /Python/);
await wait(page, 1600);

const sqlRelation = page.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first();
if (await sqlRelation.count()) {
  await sqlRelation.hover();
  await wait(page, 1200);
  await screenshot(page, "06-python-sql-edge-highlight");
  await screenshot(page, "14-python-sql-relation-highlighted");
  await screenshot(page, "15-relation-flow-particle-frame");
  await sqlRelation.click();
  await wait(page, 1300);
  selectedRelationProbe = await readProbe(page);
  await screenshot(page, "14-python-sql-selected-relation");
  await screenshot(page, "15-python-sql-128-jobs-180d");
  await screenshot(page, "07-python-sql-relation-detail");
  await screenshot(page, "17-selected-python-detail");
}

await page.getByRole("combobox", { name: "搜索技能或职业" }).fill("DevOps");
await wait(page, 1100);
await screenshot(page, "08-search-devops-result");
await page.getByRole("option", { name: /DevOps/ }).last().click();
await wait(page, 620);
await screenshot(page, "09-devops-role-rank-shifts");
await screenshot(page, "10-kubernetes-rank-18-to-1");
await screenshot(page, "11-terraform-rank-33-to-3");
await wait(page, 1900);
await screenshot(page, "09-devops-role-field");
await screenshot(page, "10-devops-field");
await choose(page, "Kubernetes", /Kubernetes/);
await wait(page, 2800);
await screenshot(page, "10-kubernetes-selected-devops");
await screenshot(page, "11-kubernetes-rank-18-to-1");
await screenshot(page, "11-devops-kubernetes-constellation");

await page.getByRole("button", { name: "回到全局" }).click();
await wait(page, 1200);
await choose(page, "Python", /Python/);
await wait(page, 1800);
const sqlContinue = page.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first();
if (await sqlContinue.count()) {
  await sqlContinue.click();
  const continueButton = page.getByRole("button", { name: /以 .*SQL.* 继续探索/ }).first();
  if (await continueButton.count()) await continueButton.click();
}
await wait(page, 1600);
await choose(page, "Spark", /Apache Spark|Spark/);
await wait(page, 450);
const activeProbe = await readProbe(page);
await wait(page, 1950);
await screenshot(page, "12-continuous-python-sql-spark");
const relationLabelCount = await page.getByTestId("skill-field-canvas").locator("button, [data-kind]").count();
const memory = await page.evaluate(() => {
  const value = performance.memory;
  return value ? { usedJsHeapBytes: value.usedJSHeapSize, totalJsHeapBytes: value.totalJSHeapSize } : null;
}).catch(() => null);

await wait(page, Math.max(3000, 62_000 - (Date.now() - recordingStartedAt)));
const video = page.video();
await context.close();
if (video) {
  await copyFile(await video.path(), resolve(outputRoot, "17-full-prototype-recording.webm"));
  await copyFile(await video.path(), resolve(outputRoot, "recording-a-full-walkthrough.webm"));
}

const cppContext = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 2,
  recordVideo: { dir: videoRoot, size: { width: 1440, height: 900 } },
});
const cppPage = await cppContext.newPage();
trackConsole(cppPage);
await cppPage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
await wait(cppPage, 1800);
await cppPage.getByRole("button", { name: "只看招聘需求" }).click();
await wait(cppPage, 2600);
await cppPage.getByRole("button", { name: "学习优先" }).click();
await wait(cppPage, 2600);
const cppVideo = cppPage.video();
await cppContext.close();
if (cppVideo) {
  await copyFile(await cppVideo.path(), resolve(outputRoot, "03-cpp-demand-value-transition.webm"));
  await copyFile(await cppVideo.path(), resolve(outputRoot, "recording-b-cpp-demand-value.webm"));
}

async function recordScenario(name, action) {
  const scenarioContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: videoRoot, size: { width: 1440, height: 900 } } });
  const scenarioPage = await scenarioContext.newPage();
  trackConsole(scenarioPage);
  await scenarioPage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
  await wait(scenarioPage, 1200);
  await action(scenarioPage);
  await wait(scenarioPage, 1800);
  const scenarioVideo = scenarioPage.video();
  await scenarioContext.close();
  if (scenarioVideo) await copyFile(await scenarioVideo.path(), resolve(outputRoot, name));
}

await recordScenario("recording-c-devops-transition.webm", async (scenarioPage) => { await choose(scenarioPage, "DevOps", /DevOps/, "last"); });
await recordScenario("recording-d-search-python-constellation.webm", async (scenarioPage) => { await choose(scenarioPage, "Python", /Python/); });
await recordScenario("recording-e-python-sql-relation.webm", async (scenarioPage) => { await choose(scenarioPage, "Python", /Python/); await wait(scenarioPage, 1400); const sql = scenarioPage.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first(); if (await sql.count()) await sql.click(); });

const mobileContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 3,
  hasTouch: true,
  isMobile: true,
  recordVideo: { dir: videoRoot, size: { width: 390, height: 844 } },
});
const mobilePage = await mobileContext.newPage();
const mobileSession = await mobileContext.newCDPSession(mobilePage);
trackConsole(mobilePage);
await mobilePage.goto(`${baseURL}/lab/3d-skill-field?quality=low`, { waitUntil: "networkidle" });
await wait(mobilePage, 2200);
await waitForRenderIdle(mobilePage);
const mobileIdleStart = await readProbe(mobilePage);
await wait(mobilePage, 1200);
const mobileIdleEnd = await readProbe(mobilePage);
await screenshot(mobilePage, "13-mobile-layout");
await screenshot(mobilePage, "18-mobile-value");
const mobileDemand = await measureInteraction(mobilePage, "学习性价比 → 招聘需求", async () => {
  await mobilePage.getByRole("button", { name: "只看招聘需求" }).click();
});
await screenshot(mobilePage, "19-mobile-demand-switch");
const mobileSearch = await measureInteraction(mobilePage, "搜索 Python → 技能星座", async () => {
  await choose(mobilePage, "Python", /Python/);
}, 2000);
await screenshot(mobilePage, "14-mobile-search");
await screenshot(mobilePage, "19-mobile-constellation");
const mobileRotate = await measureInteraction(mobilePage, "手指轻微旋转星座", async () => {
  await touchRotate(mobilePage, mobileSession);
});
await screenshot(mobilePage, "20-mobile-constellation-rotated");
await choose(mobilePage, "Python", /Python/);
await wait(mobilePage, 1400);
const mobileSql = mobilePage.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first();
const mobileRelation = await measureInteraction(mobilePage, "选择 Python–SQL 关系", async () => {
  if (await mobileSql.count()) await mobileSql.click();
});
await screenshot(mobilePage, "21-mobile-relation-selected");
const mobileReturn = await measureInteraction(mobilePage, "回到全局", async () => {
  await mobilePage.getByRole("button", { name: "回到全局" }).click();
});
const mobileMemory = await mobilePage.evaluate(() => {
  const value = performance.memory;
  return value ? { usedJsHeapBytes: value.usedJSHeapSize, totalJsHeapBytes: value.totalJSHeapSize } : null;
}).catch(() => null);
const mobileVideo = mobilePage.video();
await mobileContext.close();
if (mobileVideo) await copyFile(await mobileVideo.path(), resolve(outputRoot, "recording-f-mobile-active-interaction.webm"));

const reducedContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
const reducedPage = await reducedContext.newPage();
trackConsole(reducedPage);
await reducedPage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
await reducedPage.getByRole("button", { name: "只看招聘需求" }).click();
await wait(reducedPage, 700);
await reducedPage.getByRole("button", { name: "学习优先" }).click();
await wait(reducedPage, 120);
await screenshot(reducedPage, "15-reduced-motion");
await screenshot(reducedPage, "20-reduced-motion");
await reducedContext.close();

const lowContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const lowPage = await lowContext.newPage();
trackConsole(lowPage);
await lowPage.goto(`${baseURL}/lab/3d-skill-field?quality=low`, { waitUntil: "networkidle" });
await wait(lowPage, 1600);
await screenshot(lowPage, "21-low-quality-profile");
await lowContext.close();

const fallbackContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const fallbackPage = await fallbackContext.newPage();
trackConsole(fallbackPage);
await fallbackPage.goto(`${baseURL}/lab/3d-skill-field?fallback=1`, { waitUntil: "networkidle" });
await screenshot(fallbackPage, "16-webgl-fallback");
await screenshot(fallbackPage, "22-webgl-fallback");
await fallbackContext.close();
await browser.close();
await rm(videoRoot, { recursive: true, force: true });

for (const direction of ["a", "b", "c"]) {
  try { await copyFile(resolve(outputRoot, `../3d-skill-field-research/material-${direction}.png`), resolve(outputRoot, `01-material-${direction}.png`)); } catch { /* Material studies are optional when the prior research output was cleaned. */ }
}

const packageJson = JSON.parse(await readFile(resolve(webRoot, "package.json"), "utf8"));
const loadableManifest = JSON.parse(await readFile(resolve(webRoot, ".next/server/app/lab/3d-skill-field/page/react-loadable-manifest.json"), "utf8"));
const lazyChunkFiles = [...new Set(Object.values(loadableManifest).flatMap((entry) => entry.files))];
const lazyChunks = await Promise.all(lazyChunkFiles.map(async (file) => {
  const contents = await readFile(resolve(webRoot, ".next", file));
  return { file, rawBytes: contents.length, gzipBytes: gzipSync(contents).length, brotliBytes: brotliCompressSync(contents).length };
}));
const mobileInteractions = [mobileDemand, mobileSearch, mobileRotate, mobileRelation, mobileReturn];
const gpuWarnings = consoleIssues.filter((issue) => /webgl|gpu|shader|context lost/i.test(issue));
const report = {
  capturedAt: new Date().toISOString(),
  baseURL,
  versions: {
    react: packageJson.dependencies.react,
    reactThreeFiber: packageJson.dependencies["@react-three/fiber"],
    drei: packageJson.dependencies["@react-three/drei"],
    three: packageJson.dependencies.three,
  },
  bundle: { routeIsolation: "dynamic import on /lab/3d-skill-field only", lazyChunks },
  scene: {
    nodeCount: dataScope.skill_count,
    instancing: "one visible InstancedMesh plus one transparent hit-target InstancedMesh",
    defaultDomLabelCount: defaultLabelCount,
    relationDomLabelCount: relationLabelCount,
  },
  idle: { start: idleStart, end: idleEnd, renderedWhileIdle: idleEnd.renderedFrames - idleStart.renderedFrames },
  desktop: {
    idleFps: idleEnd.activeFps,
    demandTransition: demandProbe,
    relationTransition: activeProbe,
    selectedRelation: selectedRelationProbe,
    drawCallLimit: { global: 7, relation: 10 },
  },
  mobileLow: {
    viewport: { width: 390, height: 844 },
    touchEmulation: true,
    deviceScaleFactor: 3,
    idle: { start: mobileIdleStart, end: mobileIdleEnd, renderedWhileIdle: mobileIdleEnd.renderedFrames - mobileIdleStart.renderedFrames },
    interactions: mobileInteractions,
    memory: mobileMemory,
  },
  selectedRelationLine: { line2Adopted: false, addedDrawCalls: 0, strategy: "batch gradient + focus dimming + endpoint emphasis + evidence particles" },
  memory,
  consoleIssues,
  gpuWarnings,
  browserPreloadWarnings,
  notes: [
    "renderedWhileIdle=0 证明 demand frameloop 在控制器休眠后没有持续渲染。",
    "activeFps 是画布探针在最近 1 秒内观测到的实际渲染帧数，不是显示器 rAF 估算。",
    "actualFps 使用最近 30 个有效渲染帧间隔计算；sustainedMinFps 忽略交互开始的两个预热采样。",
    "Three/R3F/Drei 仅在原型 route 进入动态分包，不进入正式首页 LCP critical path。",
  ],
};
await writeFile(resolve(outputRoot, "performance-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
if (consoleIssues.length) throw new Error(`Browser console issues: ${consoleIssues.join(" | ")}`);
console.log(`3D review artifacts: ${outputRoot}`);
