import { expect, test } from "@playwright/test";

const pages = [
  ["/lab/market", "技术技能市场"],
  ["/lab/skills", "技能探索"],
  ["/lab/roles", "岗位洞察"],
  ["/lab/graph", "技能图谱"],
  ["/lab/portfolio", "我的技能组合"],
  ["/lab/optimizer", "学习优化器"],
  ["/lab/data-quality", "数据质量"],
  ["/methodology", "这个排名是怎么算出来的？"],
] as const;

for (const [path, heading] of pages) {
  test(`${heading} renders without horizontal overflow`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
    expect(overflow).toBe(false);
  });
}

test("Ctrl+K opens command palette and navigates", async ({ page }) => {
  await page.goto("/lab/market");
  await expect(page.getByText("数据源账本", { exact: true })).toBeVisible();
  await page.evaluate(() => document.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true })));
  await expect(page.getByPlaceholder(/搜索市场/)).toBeVisible();
  await page.getByPlaceholder(/搜索市场/).fill("方法说明");
  await page.getByText("方法说明", { exact: true }).last().click();
  await expect(page).toHaveURL(/methodology/);
});

test("market role filter is controlled and refreshes API data", async ({ page }) => {
  await page.goto("/lab/market");
  const role = page.getByLabel("目标岗位");
  await expect(role.locator("option").nth(1)).toBeAttached();
  const value = await role.locator("option").nth(1).getAttribute("value");
  expect(value).toBeTruthy();

  const response = page.waitForResponse((item) =>
    item.url().includes("/backend-api/market/summary?role_id=") && item.ok(),
  );
  await role.selectOption(value!);
  await response;
  await expect(role).toHaveValue(value!);
});

test("API failures render an explicit error state", async ({ page }) => {
  await page.route("**/backend-api/skills", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "DATA_UNAVAILABLE", message: "审计注入的不可用状态", details: [] } }),
    }),
  );

  await page.goto("/lab/skills");
  await expect(page.getByRole("heading", { name: "数据连接失败" })).toBeVisible();
  await expect(page.getByText("审计注入的不可用状态")).toBeVisible();
});
