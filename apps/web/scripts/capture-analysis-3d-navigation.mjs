import { chromium } from "@playwright/test";
import { mkdir, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const outputRoot = resolve(webRoot, "../../output/analysis-3d-navigation");
const videoRoot = resolve(outputRoot, ".video");
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:13001";
const consoleIssues = [];

function trackConsole(page) {
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) consoleIssues.push(`${message.type()}: ${message.text()}`);
  });
}

async function screenshot(page, name, locator) {
  const target = locator ?? page;
  await target.screenshot({ path: resolve(outputRoot, `${name}.png`), scale: "css" });
}

async function settle(page, milliseconds = 650) {
  await page.waitForTimeout(milliseconds);
}

await rm(outputRoot, { recursive: true, force: true });
await mkdir(videoRoot, { recursive: true });

const browser = await chromium.launch({ channel: "msedge" });

const desktopContext = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 1,
  recordVideo: { dir: videoRoot, size: { width: 1440, height: 900 } },
});
const desktop = await desktopContext.newPage();
trackConsole(desktop);
await desktop.goto(`${baseURL}/lab/visual-v2`, { waitUntil: "networkidle" });
await screenshot(desktop, "01-desktop-hero-top");
await desktop.locator("#cpp").scrollIntoViewIfNeeded();
await settle(desktop, 900);
await screenshot(desktop, "02-desktop-cpp-section");
await desktop.locator("#analysis-results").evaluate((element) => element.scrollIntoView({ block: "start" }));
await settle(desktop);
await screenshot(desktop, "03-desktop-analysis-results-start");
await screenshot(desktop, "04-desktop-3d-cta", desktop.getByText("自己探索其他技术").locator(".."));
await screenshot(desktop, "05-desktop-analysis-active", desktop.getByRole("navigation", { name: "分析结果与 3D 技能星域" }));
await desktop.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "3D 技能星域", exact: true }).click();
await desktop.getByTestId("skill-field-canvas").waitFor();
await settle(desktop, 1200);
await screenshot(desktop, "06-desktop-3d-active", desktop.getByTestId("skill-field-frame"));
await desktop.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "分析结果", exact: true }).click();
await desktop.locator("#analysis-results").waitFor();
await settle(desktop);
await screenshot(desktop, "07-desktop-return-position");
const desktopVideo = desktop.video();
await desktopContext.close();
if (desktopVideo) await desktopVideo.saveAs(resolve(outputRoot, "recording-a-desktop-analysis-to-3d-and-back.webm"));

const mobileContext = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 1,
  isMobile: true,
  hasTouch: true,
  recordVideo: { dir: videoRoot, size: { width: 390, height: 844 } },
});
const mobile = await mobileContext.newPage();
trackConsole(mobile);
await mobile.goto(`${baseURL}/lab/visual-v2#analysis-results`, { waitUntil: "networkidle" });
await settle(mobile);
await screenshot(mobile, "08-mobile-analysis-entry");
await mobile.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "3D 技能星域", exact: true }).click();
await mobile.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).waitFor();
await settle(mobile, 900);
await screenshot(mobile, "09-mobile-3d-page-top");
await screenshot(mobile, "10-mobile-bidirectional-navigation", mobile.getByRole("navigation", { name: "分析结果与 3D 技能星域" }));
await mobile.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "分析结果", exact: true }).click();
await mobile.locator("#analysis-results").waitFor();
await settle(mobile);
const mobileVideo = mobile.video();
await mobileContext.close();
if (mobileVideo) await mobileVideo.saveAs(resolve(outputRoot, "recording-b-mobile-analysis-to-3d-and-back.webm"));

await browser.close();
await rm(videoRoot, { recursive: true, force: true });

if (consoleIssues.length > 0) throw new Error(`Browser console issues:\n${consoleIssues.join("\n")}`);
console.log(`Navigation review artifacts written to ${outputRoot}`);
