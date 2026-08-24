import { expect, test } from "@playwright/test";

test("Demo Public Surface follows rebuilt API metadata", async ({ page }) => {
  const responsePromise = page.waitForResponse((response) =>
    response.url().includes("/backend-api/market/china-skillworth")
      && response.url().includes("eligibility=all")
      && response.url().includes("recency_window=180d")
      && !response.url().includes("role=")
      && response.ok(),
  );
  await page.goto("/lab/visual-v2");
  const market = await (await responsePromise).json();

  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await expect(page.getByRole("heading", { name: `探索 ${market.skill_count} 项技能` })).toBeVisible();
  await expect(page.getByText("SkillWorth 公开合成演示样本", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("数据截止 2026-08-08", { exact: false }).first()).toBeVisible();
  await expect(page.getByText("998", { exact: true })).toHaveCount(0);
  await expect(page.getByText("134", { exact: true })).toHaveCount(0);

  const firstSkill = market.records[0]?.skill;
  expect(firstSkill).toBeTruthy();
  await page.getByPlaceholder(/搜索 Python/).fill(firstSkill);
  await expect(page.getByRole("button", { name: new RegExp(firstSkill) }).first()).toBeVisible();

  const allActive = page.waitForResponse((response) => response.url().includes("recency_window=all_active") && response.ok());
  await page.locator("#explore").getByLabel("观察窗口").selectOption("all_active");
  await allActive;
  await expect(page.locator("#explore").getByLabel("观察窗口")).toHaveValue("all_active");
});

test("Demo methodology renders API scope without Real literals", async ({ page }) => {
  const responsePromise = page.waitForResponse((response) => response.url().includes("/backend-api/market/china-skillworth") && response.ok());
  await page.goto("/methodology");
  const market = await (await responsePromise).json();

  await expect(page.getByRole("heading", { name: "这个排名是怎么算出来的？" })).toBeVisible();
  const scope = page.locator("article").filter({ has: page.getByRole("heading", { name: "我们分析了什么？" }) });
  await expect(scope.getByText(String(market.job_count), { exact: true }).first()).toBeVisible();
  await expect(page.getByText(`快照 ${market.snapshot}`, { exact: false })).toBeVisible();
  await expect(page.getByText("薪资比较")).toBeVisible();
  await expect(page.getByText("暂不可用", { exact: true }).first()).toBeVisible();
});

test("Public Surface distinguishes API error from empty", async ({ page }) => {
  await page.route("**/backend-api/market/china-skillworth**", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ error: { code: "DATA_UNAVAILABLE", message: "injected", details: [] } }),
  }));
  await page.goto("/lab/visual-v2");
  await expect(page.getByText("当前数据暂时无法读取", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "重试" }).first()).toBeVisible();
  await expect(page.getByText("998", { exact: true })).toHaveCount(0);
  await expect(page.getByText("134", { exact: true })).toHaveCount(0);

  await page.unroute("**/backend-api/market/china-skillworth**");
  await page.route("**/backend-api/market/china-skillworth**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      market_scope: "demo_dataset",
      source_role: "engineering_validation",
      snapshot: "empty-demo",
      access_date: "2026-08-08",
      recency_window: "180d",
      job_count: 0,
      company_count: 0,
      skill_count: 0,
      source_count: 1,
      disclaimer: "empty fixture",
      salary_signal_status: "unavailable",
      trend_signal_status: "unavailable",
      market_themes: [],
      records: [],
    }),
  }));
  await page.goto("/lab/visual-v2");
  await expect(page.getByText("当前筛选条件下没有可展示的技能", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("当前数据暂时无法读取", { exact: true })).toHaveCount(0);
});

test("Demo mobile/reduced-motion path has no overflow or browser errors", async ({ page, isMobile }) => {
  const messages: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => { if (["error", "warning"].includes(message.type())) messages.push(message.text()); });
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/visual-v2");
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  if (isMobile) await expect(page.getByRole("navigation", { name: "公开产品导航" })).toBeVisible();
  expect(messages).toEqual([]);
  expect(failedRequests).toEqual([]);
});
