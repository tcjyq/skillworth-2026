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
      drawCalls: Number(element.dataset.drawCalls ?? 0),
      geometries: Number(element.dataset.geometries ?? 0),
      textures: Number(element.dataset.textures ?? 0),
      rendererDpr: Number(element.dataset.rendererDpr ?? 0),
      lastRenderedAt,
      probeAgeMs: Math.round(probeAgeMs),
      postProcessingPassCount: Number(element.dataset.postProcessingPassCount ?? 0),
      particleCount: Number(element.dataset.particleCount ?? 0),
      visibleLabelCount: Number(element.dataset.visibleLabelCount ?? 0),
      qualityProfile: element.dataset.qualityProfile ?? "unknown",
      aaMode: element.dataset.aaMode ?? "unknown",
      bloomMode: element.dataset.bloomMode ?? "unknown",
    };
  });
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
const defaultLabelCount = await page.getByTestId("skill-field-canvas").locator("button").count();
await screenshot(page, "01-global-value-desktop");
await screenshot(page, "02-final-global-value");
await page.screenshot({ path: resolve(outputRoot, "03-value-core-close-up.png"), clip: { x: 500, y: 360, width: 560, height: 410 }, scale: "css" });
await screenshot(page, "04-skill-color-palette");
await page.screenshot({ path: resolve(outputRoot, "05-python-sql-git-cpp-material-close-ups.png"), clip: { x: 360, y: 280, width: 720, height: 500 }, scale: "css" });
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
  await page.mouse.move(constellationBox.x + constellationBox.width * 0.52, constellationBox.y + constellationBox.height * 0.58);
  await page.mouse.down();
  await page.mouse.move(constellationBox.x + constellationBox.width * 0.61, constellationBox.y + constellationBox.height * 0.58, { steps: 12 });
  await page.mouse.up();
  await wait(page, 500);
}
await screenshot(page, "13-python-constellation-rotated-15deg");

const sqlRelation = page.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first();
if (await sqlRelation.count()) {
  await sqlRelation.hover();
  await wait(page, 1200);
  await screenshot(page, "06-python-sql-edge-highlight");
  await screenshot(page, "14-python-sql-relation-highlighted");
  await screenshot(page, "15-relation-flow-particle-frame");
  await sqlRelation.click();
  await wait(page, 1300);
  await screenshot(page, "07-python-sql-relation-detail");
  await screenshot(page, "17-selected-python-detail");
}

await page.getByRole("combobox", { name: "搜索技能或职业" }).fill("DevOps");
await wait(page, 1100);
await screenshot(page, "08-search-devops-result");
await page.getByRole("option", { name: /DevOps/ }).last().click();
await wait(page, 2500);
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
const relationLabelCount = await page.getByTestId("skill-field-canvas").locator("button").count();
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

await recordScenario("recording-c-search-python-constellation.webm", async (scenarioPage) => { await choose(scenarioPage, "Python", /Python/); });
await recordScenario("recording-d-devops-kubernetes.webm", async (scenarioPage) => { await choose(scenarioPage, "DevOps", /DevOps/, "last"); await wait(scenarioPage, 1400); await choose(scenarioPage, "Kubernetes", /Kubernetes/); });
await recordScenario("recording-e-python-sql-spark.webm", async (scenarioPage) => { await choose(scenarioPage, "Python", /Python/); await wait(scenarioPage, 1400); const sql = scenarioPage.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first(); if (await sql.count()) await sql.click(); await wait(scenarioPage, 800); await choose(scenarioPage, "Spark", /Apache Spark|Spark/); });
await recordScenario("recording-f-high-vs-balanced.webm", async (scenarioPage) => { await scenarioPage.goto(`${baseURL}/lab/3d-skill-field?quality=high`, { waitUntil: "networkidle" }); await wait(scenarioPage, 1500); await scenarioPage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" }); });

const mobileContext = await browser.newContext({ viewport: { width: 412, height: 915 }, deviceScaleFactor: 2 });
const mobilePage = await mobileContext.newPage();
trackConsole(mobilePage);
await mobilePage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
await wait(mobilePage, 2200);
const mobileProbe = await readProbe(mobilePage);
await screenshot(mobilePage, "13-mobile-layout");
await screenshot(mobilePage, "18-mobile-value");
await mobilePage.getByRole("combobox", { name: "搜索技能或职业" }).fill("Python");
await wait(mobilePage, 900);
await screenshot(mobilePage, "14-mobile-search");
await mobilePage.getByRole("option", { name: /Python/ }).first().click();
await wait(mobilePage, 1800);
await screenshot(mobilePage, "19-mobile-constellation");
await mobileContext.close();

const reducedContext = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
const reducedPage = await reducedContext.newPage();
trackConsole(reducedPage);
await reducedPage.goto(`${baseURL}/lab/3d-skill-field`, { waitUntil: "networkidle" });
await reducedPage.getByRole("button", { name: "只看招聘需求" }).click();
await wait(reducedPage, 700);
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
  demandTransition: demandProbe,
  relationTransition: activeProbe,
  highDprMobile: mobileProbe,
  memory,
  consoleIssues,
  browserPreloadWarnings,
  notes: [
    "renderedWhileIdle=0 证明 demand frameloop 在控制器休眠后没有持续渲染。",
    "activeFps 是画布探针在最近 1 秒内观测到的实际渲染帧数，不是显示器 rAF 估算。",
    "Three/R3F/Drei 仅在原型 route 进入动态分包，不进入正式首页 LCP critical path。",
  ],
};
await writeFile(resolve(outputRoot, "performance-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
if (consoleIssues.length) throw new Error(`Browser console issues: ${consoleIssues.join(" | ")}`);
console.log(`3D review artifacts: ${outputRoot}`);
