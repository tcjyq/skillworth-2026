import { expect, test } from "@playwright/test";

test("首页默认使用 180 天真实样本且只展示稳健候选", async ({ page }) => {
  const response = page.waitForResponse((item) => item.url().includes("robustness=robust") && item.url().includes("recency_window=180d") && item.ok());
  await page.goto("/");
  await response;
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await expect(page.getByText("180 天", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("998", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("313", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("134", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("LIVE SNAPSHOT", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: /SKILLWORTH FRONTIER/ })).toBeVisible();
  await expect(page.getByText("China Open Tech Sample", { exact: true }).last()).toBeVisible();
  await expect(page.getByText("Single Supplementary Source", { exact: true })).toBeVisible();
  await expect(page.getByText("Unavailable · Insufficient evidence", { exact: true })).toBeVisible();
  await expect(page.getByText("Unavailable · Requires independent snapshots", { exact: true })).toBeVisible();
});

test("Final 5 以连续数据故事进入首页并使用 v6 精确证据", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /EFFICIENCY FRONTIER/ })).toBeVisible();
  await expect(page.getByText("Python → SQL → Git", { exact: true })).toBeVisible();
  await expect(page.getByText("Demand #3", { exact: true })).toBeVisible();
  await expect(page.getByText("SkillWorth #35", { exact: true })).toBeVisible();
  await expect(page.getByText(/260h.*学习投入假设/)).toBeVisible();

  await expect(page.getByRole("heading", { name: "YOUR ROLE CHANGES THE ANSWER" })).toBeVisible();
  await expect(page.getByText("n=21", { exact: true })).toBeVisible();
  await expect(page.getByText("n=38", { exact: true })).toBeVisible();
  await expect(page.getByText("#18 → #1", { exact: true })).toBeVisible();
  await expect(page.getByText("#33 → #3", { exact: true })).toBeVisible();
  await expect(page.getByText("#19 → #3", { exact: true })).toBeVisible();
  await expect(page.getByText("#23 → #5", { exact: true })).toBeVisible();

  await expect(page.getByRole("heading", { name: "SKILLS COME IN STACKS" })).toBeVisible();
  await expect(page.getByText("141 co-jobs", { exact: true })).toBeVisible();
  await expect(page.getByText("Jaccard 0.6667", { exact: true })).toBeVisible();
  await expect(page.getByText("PMI 4.1255", { exact: true })).toBeVisible();
  await expect(page.getByText("1,140 all-active canonical jobs", { exact: true })).toBeVisible();
  await expect(page.getByText(/共现是关联，不是因果/)).toBeVisible();

  await expect(page.getByRole("heading", { name: "TRUST THE CORE, NOT EVERY RANK" })).toBeVisible();
  for (const range of ["1–2", "3–4", "7–25", "6–29", "8–27"]) await expect(page.getByText(range, { exact: true }).first()).toBeVisible();
});

test("角色故事入口复用现有筛选并切换到冻结的角色样本", async ({ page }) => {
  await page.goto("/");
  const response = page.waitForResponse((item) => item.url().includes("role=devops_engineer") && item.url().includes("recency_window=180d") && item.ok());
  await page.getByRole("button", { name: "查看 DevOps 排名" }).click();
  await response;
  await expect(page.getByRole("button", { name: "云与 DevOps" })).toHaveAttribute("aria-pressed", "true");
});

test("时间与岗位筛选重新请求真实 API", async ({ page }) => {
  await page.goto("/");
  const recencyResponse = page.waitForResponse((response) => response.url().includes("recency_window=90d") && response.ok());
  await page.getByRole("button", { name: "90 天" }).click();
  await recencyResponse;
  await expect(page.getByText("90 天", { exact: true }).first()).toBeVisible();

  const roleButton = page.getByRole("button", { name: "后端", exact: true });
  if (await roleButton.count()) {
    const roleResponse = page.waitForResponse((response) => response.url().includes("role=backend_engineer") && response.ok());
    await roleButton.click();
    await roleResponse;
    await expect(roleButton).toHaveAttribute("aria-pressed", "true");
  }
});

test("气泡键盘替代入口打开技能详情，并保持不可用信号", async ({ page, isMobile }) => {
  await page.goto("/");
  await page.getByText("使用键盘浏览图表数据", { exact: true }).click();
  const python = page.getByRole("button", { name: /^Python ·/ });
  await python.press("Enter");
  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible();
  await expect(page.getByText("Insufficient evidence", { exact: true })).toBeVisible();
  await expect(page.getByText("Requires multiple independent snapshots", { exact: true })).toBeVisible();
  const sheet = page.locator('[data-slot="sheet-content"]');
  await expect(sheet).toHaveAttribute("data-side", isMobile ? "bottom" : "right");
});

test("市场主题不进入具体技能主榜", async ({ page }) => {
  await page.goto("/");
  const picks = page.locator("section").filter({ has: page.getByRole("heading", { name: "TRUST THE CORE, NOT EVERY RANK" }) });
  await expect(picks.getByRole("button", { name: /^AI(?:\s|$)/ })).toHaveCount(0);
  const themes = page.locator("section").filter({ has: page.getByRole("heading", { name: "MARKET THEMES" }) });
  await expect(themes.getByText(/Market Theme ≠ Learnable Skill Ranking/).first()).toBeVisible();
  const aiTheme = themes.getByRole("button", { name: /^AI / }).first();
  await aiTheme.click();
    await expect(
      page.getByText("正在突出与 AI 相关的具体候选；其他技能保留为对照。", { exact: true }),
    ).toBeVisible();
});

test("Market Board 行 hover 与技能焦点状态联动", async ({ page }) => {
  test.skip(test.info().project.name === "mobile", "Touch projects do not expose a hover affordance.");
  await page.goto("/");
  const board = page.locator("section").filter({ has: page.getByRole("heading", { name: "TRUST THE CORE, NOT EVERY RANK" }) });
  const pythonRow = board.getByRole("button", { name: /^01 Python/ });
  await pythonRow.dispatchEvent("mouseover");
  await expect(pythonRow).toHaveClass(/market-board-row-active/);
  await pythonRow.dispatchEvent("mouseout");
  await expect(pythonRow).not.toHaveClass(/market-board-row-active/);
});

test("首页没有横向溢出", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
});

test("移动端问题标题保持语义断行", async ({ page, isMobile }) => {
  test.skip(!isMobile);
  await page.goto("/");
  const lines = page.locator("#skillworth-question span");
  await expect(lines).toHaveCount(2);
  await expect(lines.nth(0)).toHaveText("2026，学什么");
  await expect(lines.nth(1)).toHaveText("技术最值？");
  const first = await lines.nth(0).boundingBox();
  const second = await lines.nth(1).boundingBox();
  expect(first && second && second.y > first.y + first.height * 0.5).toBe(true);
});

test("移动端 Bottom Sheet 不超出视口", async ({ page, isMobile }) => {
  test.skip(!isMobile);
  await page.goto("/");
  await page.getByText("使用键盘浏览图表数据", { exact: true }).click();
  await page.getByRole("button", { name: /^Python ·/ }).click();
  const sheet = page.locator('[data-slot="sheet-content"]');
  await expect(sheet).toBeVisible();
  expect(await sheet.evaluate((node) => {
    const bounds = node.getBoundingClientRect();
    return bounds.left >= -1 && bounds.right <= document.documentElement.clientWidth + 1 && node.scrollWidth <= node.clientWidth + 1;
  })).toBe(true);
});

test("移动首页关键内容、触控目标与 SVG 图表在常见窄屏下保持完整", async ({ page, isMobile }) => {
  test.skip(!isMobile);
  for (const viewport of [
    { width: 360, height: 800 },
    { width: 375, height: 812 },
    { width: 390, height: 844 },
    { width: 430, height: 932 },
  ]) {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await expect(page.getByText("C++ 的需求很强，学习决策排序不同", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await expect(page.locator("canvas")).toHaveCount(0);
    await expect(page.locator('[role="img"] svg')).toHaveCount(1);

    const headline = page.getByRole("heading", { name: "2026，学什么技术最值？" });
    const headlineBox = await headline.boundingBox();
    expect(headlineBox && headlineBox.x >= 0 && headlineBox.x + headlineBox.width <= viewport.width + 1).toBe(true);

    for (const link of [
      page.getByRole("link", { name: "方法与数据" }),
      page.getByRole("link", { name: "样本范围" }),
      page.getByRole("link", { name: "进入 3D 技能星域" }),
    ]) {
      await link.scrollIntoViewIfNeeded();
      const box = await link.boundingBox();
      expect(box && box.x >= 0 && box.x + box.width <= viewport.width + 1 && box.height >= 44).toBe(true);
    }
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const more = page.getByRole("button", { name: /查看其余 \d+ 项稳健候选/ });
  await expect(more).toHaveAttribute("aria-expanded", "false");
  await more.click();
  await expect(page.getByRole("button", { name: "收起其余候选" })).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("button", { name: /^34 TensorFlow/ })).toBeVisible();
});

test("公开主路径没有控制台告警、错误或失败 API 请求", async ({ page }) => {
  const browserMessages: string[] = [];
  const failedApiRequests: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") browserMessages.push(`${message.type()}: ${message.text()}`);
  });
  page.on("requestfailed", (request) => {
    if (request.url().includes("/backend-api/")) failedApiRequests.push(`${request.method()} ${request.url()}`);
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await page.getByRole("button", { name: "90 天" }).click();
  await expect(page.getByText("90 天", { exact: true }).first()).toBeVisible();
  await page.getByText("使用键盘浏览图表数据", { exact: true }).click();
  await page.getByRole("button", { name: /^Python ·/ }).click();
  await expect(page.getByRole("heading", { name: "Python" })).toBeVisible();

  expect(browserMessages).toEqual([]);
  expect(failedApiRequests).toEqual([]);
});

test("减少动态偏好关闭 Hero 位移和长时动画", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const hero = page.locator(".cinematic-hero");
  await expect(hero).toBeVisible();
  expect(await hero.evaluate((node) => getComputedStyle(node).getPropertyValue("--hero-dx").trim())).toBe("0px");
  const orbit = page.locator(".hero-orbit").first();
  expect(await orbit.evaluate((node) => getComputedStyle(node).transform)).toBe("none");
});
