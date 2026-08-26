import { expect, test, type Page } from "@playwright/test";

const desktopViewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
];

type StoryRange = {
  start: number;
  end: number;
  viewportHeight: number;
};

async function openCppStory(page: Page, waitForScrollStory = true): Promise<StoryRange | undefined> {
  await page.goto("/lab/visual-v2");
  await expect(page.locator("[data-cpp-ranks]")).toBeVisible({ timeout: 20_000 });
  await expect(page.locator("[data-cpp-moment]")).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);
  return waitForScrollStory ? waitForCppScrollStoryReady(page) : undefined;
}

async function storyRange(page: Page): Promise<StoryRange> {
  return page.evaluate(() => {
    const chapter = document.querySelector<HTMLElement>("[data-cpp-moment]");
    const analysis = document.querySelector<HTMLElement>("#analysis-results");
    if (!chapter || !analysis) throw new Error("C++ story geometry is unavailable");
    const spacer = chapter.parentElement?.classList.contains("pin-spacer") ? chapter.parentElement : chapter;
    const chapterTop = spacer.getBoundingClientRect().top + window.scrollY;
    const analysisTop = analysis.getBoundingClientRect().top + window.scrollY;
    return {
      start: chapterTop,
      end: analysisTop - window.innerHeight,
      viewportHeight: window.innerHeight,
    };
  });
}

async function waitForCppScrollStoryReady(page: Page): Promise<StoryRange> {
  await expect.poll(() => page.evaluate(() => (
    document.querySelector("[data-cpp-moment]")?.parentElement?.classList.contains("pin-spacer-cpp-scroll-story") ?? false
  ))).toBe(true);

  await expect.poll(async () => {
    const range = await storyRange(page);
    return range.end - range.start >= range.viewportHeight * 1.5;
  }).toBe(true);

  const initialRange = await storyRange(page);
  await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
  await expect.poll(async () => {
    const range = await storyRange(page);
    return Math.abs(range.start - initialRange.start) < 1
      && Math.abs(range.end - initialRange.end) < 1;
  }).toBe(true);
  return storyRange(page);
}

async function scrollToStoryProgress(page: Page, progress: number) {
  const range = await storyRange(page);
  const scrollY = range.start + Math.max(0, range.end - range.start) * progress;
  await page.evaluate((top) => window.scrollTo(0, top), scrollY);
  await expect.poll(() => page.evaluate((top) => Math.abs(window.scrollY - top) < 1, scrollY), { timeout: 10_000 }).toBe(true);
  return range;
}

async function visualState(page: Page) {
  return page.evaluate(() => {
    const style = (selector: string) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing C++ story element: ${selector}`);
      const computed = getComputedStyle(element);
      return {
        opacity: Number(computed.opacity),
        visibility: computed.visibility,
        transform: computed.transform,
        filter: computed.filter,
      };
    };
    const chapter = document.querySelector<HTMLElement>("[data-cpp-moment]");
    const analysis = document.querySelector<HTMLElement>("#analysis-results");
    if (!chapter || !analysis) throw new Error("C++ story bounds are unavailable");
    return {
      demand: style("[data-cpp-sequence='demand']"),
      investment: style("[data-cpp-sequence='investment']"),
      result: style("[data-cpp-sequence='result']"),
      support: style("[data-cpp-support]"),
      chapter: chapter.getBoundingClientRect().toJSON(),
      analysis: analysis.getBoundingClientRect().toJSON(),
    };
  });
}

test("C++ #35 在约 78% 完成，并在分析结果进入前保留结果 Hold", async ({ page, isMobile }) => {
  test.skip(isMobile);
  const range = await openCppStory(page);
  if (!range) throw new Error("C++ scroll story did not become ready");
  expect(range.end - range.start).toBeGreaterThanOrEqual(range.viewportHeight * 1.5);

  await scrollToStoryProgress(page, 0.25);
  const demandState = await visualState(page);
  expect(demandState.demand.opacity).toBeGreaterThanOrEqual(0.98);

  await scrollToStoryProgress(page, 0.5);
  const investmentState = await visualState(page);
  expect(investmentState.investment.opacity).toBeGreaterThanOrEqual(0.5);

  await scrollToStoryProgress(page, 0.78);
  const resultState = await visualState(page);
  expect(resultState.result.opacity).toBeGreaterThanOrEqual(0.98);
  expect(Number(resultState.result.filter.match(/blur\(([\d.]+)px\)/)?.[1])).toBeLessThan(0.05);
  expect(resultState.analysis.top).toBeGreaterThanOrEqual(range.viewportHeight);

  await scrollToStoryProgress(page, 0.9);
  const holdState = await visualState(page);
  expect(holdState.result.opacity).toBeGreaterThanOrEqual(0.98);
  expect(Number(holdState.result.filter.match(/blur\(([\d.]+)px\)/)?.[1])).toBeLessThan(0.05);
  expect(holdState.analysis.top).toBeGreaterThanOrEqual(range.viewportHeight);
});

test("C++ 快速滚动、反向滚动和桌面 resize 均同步到对应状态", async ({ page, isMobile }) => {
  test.skip(isMobile);

  for (const viewport of desktopViewports) {
    await page.setViewportSize(viewport);
    await openCppStory(page);
    const range = await scrollToStoryProgress(page, 1);
    const finalState = await visualState(page);
    expect(finalState.result.opacity).toBeGreaterThanOrEqual(0.98);
    expect(Number(finalState.result.filter.match(/blur\(([\d.]+)px\)/)?.[1])).toBeLessThan(0.05);
    expect(finalState.analysis.top).toBeGreaterThanOrEqual(range.viewportHeight - 1);

    await scrollToStoryProgress(page, 0.5);
    const reverseMiddle = await visualState(page);
    expect(reverseMiddle.investment.opacity).toBeGreaterThanOrEqual(0.5);
    expect(reverseMiddle.result.opacity).toBeLessThan(0.98);

    await scrollToStoryProgress(page, 0.25);
    const reverseDemand = await visualState(page);
    expect(reverseDemand.demand.opacity).toBeGreaterThanOrEqual(0.98);
    expect(reverseDemand.investment.opacity).toBeLessThan(0.9);
  }
});

test("移动端与 Reduced Motion 不依赖滚动动画才能读到完整结论", async ({ page, isMobile }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openCppStory(page, false);
  const state = await visualState(page);
  expect(state.demand.opacity).toBe(1);
  expect(state.investment.opacity).toBe(1);
  expect(state.result.opacity).toBe(1);
  expect(state.support.opacity).toBe(1);

  if (isMobile) {
    await page.locator("[data-cpp-sequence='result']").scrollIntoViewIfNeeded();
    const mobileState = await visualState(page);
    expect(mobileState.chapter.bottom).toBeGreaterThan(0);
    expect(mobileState.analysis.top).toBeGreaterThan(0);
  }
});
