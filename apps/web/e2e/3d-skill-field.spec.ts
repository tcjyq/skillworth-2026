import { expect, test } from "@playwright/test";

const realMode = process.env.SKILLWORTH_E2E_MODE === "real";

test("3D 技能星域支持搜索、职业、需求模式、移动端与 Reduced Motion", async ({ page, isMobile }) => {
  const consoleMessages: string[] = [];
  page.on("console", (message) => { if (["error", "warning"].includes(message.type())) consoleMessages.push(message.text()); });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/3d-skill-field");
  await expect(page.getByRole("link", { name: "返回 SkillWorth 2026" })).toContainText("SkillWorth 2026");
  await expect(page.getByRole("link", { name: "SkillWorth Lab 首页" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "主导航" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "市场" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "我的技能组合" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "组合", exact: true })).toHaveCount(0);
  if (isMobile) await expect(page.getByText("3D 技能星域 · Lab")).toBeHidden();
  else await expect(page.getByText("3D 技能星域 · Lab")).toBeVisible();
  await expect(page.getByRole("heading", { name: /项技术，哪些更值得你先学/ })).toBeVisible();
  await expect(page.getByTestId("skill-field-canvas")).toBeVisible();
  await expect(page.getByText("◎ 价值核心")).toBeVisible();
  await expect(page.getByTestId("value-core-annotation")).toContainText("只看远近，不看方向");
  await expect(page.getByTestId("skill-field-canvas")).toHaveAttribute("data-quality-profile", isMobile ? "LOW" : "BALANCED");

  const search = page.getByRole("combobox", { name: "搜索技能或职业" });
  await search.fill(realMode ? "Python" : "SQL");
  await page.getByRole("option", { name: new RegExp(realMode ? "Python" : "SQL") }).first().click();
  await expect(page.getByRole("heading", { name: new RegExp(`${realMode ? "Python" : "SQL"}，通常和哪些技能`) })).toBeVisible();
  await expect(page.getByRole("heading", { name: realMode ? "Python" : "SQL", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "回到全局" }).click();
  await page.getByRole("button", { name: "只看招聘需求" }).click();
  await expect(page.getByRole("heading", { name: "如果只看招聘需求，答案会怎么变？" })).toBeVisible();

  await search.fill(realMode ? "DevOps" : "数据分析");
  const roleOption = page.getByRole("option", { name: new RegExp(realMode ? "DevOps" : "数据分析") }).last();
  await roleOption.click();
  await expect(page.getByRole("heading", { name: /答案会怎么变/ })).toBeVisible();
  await expect(page.getByText(/个岗位样本/).first()).toBeVisible();
  if (isMobile) expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await expect(page.getByTestId("skill-field-canvas")).toHaveAttribute("data-relation-particle-count", "0");
  expect(consoleMessages).toEqual([]);
});

test("WebGL 初始化失败时保留 2D 搜索与技能列表", async ({ page }) => {
  await page.goto("/lab/3d-skill-field?fallback=1");
  await expect(page.getByRole("heading", { name: "已切换到 2D 技能视图" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "搜索技能或职业" })).toBeVisible();
  await expect(page.getByRole("region", { name: "2D 技能列表" })).toBeVisible();
  if (realMode) await expect(page.getByRole("region", { name: "2D 技能列表" })).toContainText("招聘需求 #3 → 学习性价比 #35");
});

test("WebGL 运行中上下文丢失时自动转为 2D", async ({ page }) => {
  await page.goto("/lab/3d-skill-field");
  await expect(page.getByTestId("skill-field-canvas")).toHaveAttribute("data-context-guard-ready", "true");
  const canvas = page.getByTestId("skill-field-canvas").locator("canvas");
  await expect(canvas).toBeVisible();
  await canvas.dispatchEvent("webglcontextlost", { cancelable: true });
  await expect(page.getByRole("heading", { name: "已切换到 2D 技能视图" })).toBeVisible();
});

test("Real v6 保持冻结样本与关键排名迁移", async ({ page }) => {
  test.skip(!realMode);
  const globalResponse = await page.request.get("/backend-api/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d");
  expect(globalResponse.ok()).toBe(true);
  const globalPayload = await globalResponse.json();
  const globalRank = (skillId: string) => globalPayload.records.find((record: { skill_id: string }) => record.skill_id === skillId)?.skillworth_rank;
  expect(globalRank("devops_kubernetes")).toBe(18);
  expect(globalRank("devops_terraform")).toBe(33);
  expect(globalRank("data_engineering_spark")).toBe(19);
  expect(globalRank("data_engineering_kafka")).toBe(23);
  await page.goto("/lab/3d-skill-field");
  await expect(page.getByRole("heading", { name: "134 项技术，哪些更值得你先学？" })).toBeVisible();
  await expect(page.getByLabel("数据范围").getByText("998 个岗位").first()).toBeVisible();
  await expect(page.getByLabel("数据范围").getByText("313 家公司").first()).toBeVisible();
  await page.getByRole("button", { name: "只看招聘需求" }).click();
  await expect(page.getByRole("status")).toContainText("招聘需求 #3");
  await page.getByRole("button", { name: "学习优先" }).click();
  await expect(page.getByRole("status")).toContainText("#3 → #35");

  const search = page.getByRole("combobox", { name: "搜索技能或职业" });
  await search.fill("DevOps");
  await page.getByRole("option", { name: /DevOps/ }).last().click();
  await expect(page.getByText("21 个岗位样本", { exact: false }).first()).toBeVisible();
  const roleShiftLabels = page.getByTestId("skill-field-canvas").locator('[data-kind="role"]');
  await expect(roleShiftLabels).toHaveCount(3);
  await expect(roleShiftLabels.first()).toHaveAttribute("data-presentation", "explain");
  await expect(page.getByTestId("skill-field-canvas")).toContainText("#18 → #1");
  await expect(page.getByTestId("skill-field-canvas")).toContainText("#33 → #3");
  await expect(roleShiftLabels.first()).toHaveAttribute("data-presentation", "settled", { timeout: 2_200 });
  await search.fill("Kubernetes");
  await page.getByRole("option", { name: /Kubernetes/ }).first().click();
  await expect(page.getByLabel("技能详情")).toContainText("学习性价比第 1");
  await search.fill("Terraform");
  await page.getByRole("option", { name: /Terraform/ }).first().click();
  await expect(page.getByLabel("技能详情")).toContainText("学习性价比第 3");

  await search.fill("数据工程");
  await page.getByRole("option", { name: /数据工程师/ }).last().click();
  await expect(page.getByText("38 个岗位样本", { exact: false }).first()).toBeVisible();
  await search.fill("Apache Spark");
  await page.getByRole("option", { name: /Apache Spark/ }).first().click();
  await expect(page.getByLabel("技能详情")).toContainText("学习性价比第 3");
  await search.fill("Kafka");
  await page.getByRole("option", { name: /Apache Kafka|Kafka/ }).first().click();
  await expect(page.getByLabel("技能详情")).toContainText("学习性价比第 5");

  await page.getByRole("button", { name: "回到全局" }).click();
  await search.fill("Python");
  await page.getByRole("option", { name: /Python/ }).first().click();
  const sqlRelation = page.getByLabel("一级技能关系").getByRole("button", { name: /SQL/ }).first();
  await sqlRelation.click();
  await expect(page.getByTestId("skill-field-canvas")).toContainText("128 个岗位一起出现 · 近 180 天");
});
