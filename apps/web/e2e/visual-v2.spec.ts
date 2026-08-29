import { expect, test } from "@playwright/test";

test("首页首屏直接说明用途、结论和样本边界", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await expect(page.getByText("Python · SQL · Git", { exact: true })).toBeVisible();
  await expect(page.locator('section[aria-labelledby="hero-title"]').getByText("998", { exact: true })).toBeVisible();
  await expect(page.locator('section[aria-labelledby="hero-title"]').getByText("Freehire 中国公开技术岗位补充样本", { exact: false })).toBeVisible();
  await expect(page.getByRole("link", { name: "看看为什么" })).toHaveAttribute("href", "#cpp");
  await expect(page.getByRole("link", { name: "找适合我的方向" })).toHaveAttribute("href", "#roles");
});

test("C++ 场景始终明确两种排名及学习投入", async ({ page }) => {
  await page.goto("/lab/visual-v2#cpp");
  await expect(page.getByRole("heading", { name: /C\+\+ 招聘需求排第 3.*学习性价比只排第 35/ })).toBeVisible();
  const story = page.getByLabel("SkillWorth 研究结论");
  await expect(story.getByText("招聘需求排名", { exact: true })).toBeVisible();
  await expect(story.getByText("学习性价比排名", { exact: true })).toBeVisible();
  await expect(story.getByText("加入学习投入后", { exact: true })).toBeVisible();
  await expect(story.getByText("#3", { exact: true })).toBeVisible();
  await expect(story.getByText("#35", { exact: true })).toBeVisible();
  await expect(story.getByText("92 个岗位 · 48 家公司", { exact: true })).toBeVisible();
  await expect(story.getByText("约 260 小时", { exact: true })).toBeVisible();
});

test("Role First 选择后显示样本、证据状态与全局到岗位排名", async ({ page }) => {
  await page.goto("/lab/visual-v2#roles");
  await expect(page.getByRole("heading", { name: "你想做什么方向？" })).toBeVisible();
  await page.getByRole("button", { name: "运维 / DevOps" }).click();
  await expect(page.getByRole("heading", { name: "运维 / DevOps 工程师" })).toBeVisible();
  await expect(page.getByText("全局学习性价比排名 → 当前方向排名", { exact: true })).toBeVisible();
  await expect(page.getByText("Kubernetes", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "前端" }).click();
  await expect(page.getByText("低样本", { exact: true })).toBeVisible();
  await expect(page.getByText("不宜将精确名次视为稳定结论。", { exact: false })).toBeVisible();
});

test("Explore Mode 可搜索完整 134 项技能并渐进展示详情", async ({ page }) => {
  await page.goto("/lab/visual-v2#explore");
  await expect(page.getByText("134 项可搜索技能")).toBeVisible();
  await expect(page.getByText("110 项进入主排名层")).toBeVisible();
  await expect(page.getByText("24 项仅观察")).toBeVisible();
  await expect(page.getByRole("region", { name: "主排名层" })).toContainText("不等于正式推荐");
  await page.getByPlaceholder(/搜索 Python/).fill("React");
  await expect(page.getByText("1 项匹配搜索")).toBeVisible();
  await page.getByRole("button", { name: /React/ }).click();
  await expect(page.getByRole("heading", { name: "React" })).toBeVisible();
  await page.getByText("查看进阶指标").click();
  await expect(page.getByText("市场支持度（Market Signal）", { exact: true })).toBeVisible();
  await expect(page.locator("#explore").getByText("学习性价比（SkillWorth）", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "按岗位" }).click();
  await expect(page.locator("#explore").getByLabel("岗位方向", { exact: true })).toHaveValue("backend_engineer");
  await page.locator("#explore").getByLabel("技能层", { exact: true }).selectOption("observed");
  await expect(page.getByRole("region", { name: "已观察技能" })).toBeVisible();
});

test("角色样本不足时展示主排名层、已观察技能和分级证据状态", async ({ page }) => {
  await page.goto("/lab/visual-v2#explore");
  await page.locator("#explore").getByLabel("岗位方向", { exact: true }).selectOption("technical_product_manager");
  await expect(page.getByText("0 项进入主排名层")).toBeVisible();
  await expect(page.getByText("6 项仅观察")).toBeVisible();
  await expect(page.getByText("当前岗位样本较少。以下排序仅反映当前开放样本，不构成稳定推荐。")).toBeVisible();
  await expect(page.getByText("3 个岗位", { exact: true })).toBeVisible();
  await expect(page.getByText("极低样本", { exact: true })).toBeVisible();
  await expect(page.getByText("不宜将精确名次视为稳定结论。", { exact: false })).toBeVisible();
  await expect(page.getByRole("button", { name: /Machine Learning/ })).toBeVisible();
});

test("统一公共导航不暴露内部版本并可进入方法页返回首页", async ({ page, isMobile }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "公开产品导航" });
  await expect(nav.getByRole("link", { name: "研究结论" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "方法与数据" })).toBeVisible();
  if (isMobile) {
    await expect(nav.getByRole("link", { name: "选职业方向" })).toBeHidden();
    await expect(nav.getByRole("link", { name: "查技术技能" })).toBeHidden();
  } else {
    await expect(nav.getByRole("link", { name: "选职业方向" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "查技术技能" })).toBeVisible();
  }
  await expect(page.getByText(/返回旧版|退出实验|Production Candidate|Visual V2|\bV1\b|\bV2\b/)).toHaveCount(0);
  await expect(page.getByRole("link", { name: "SkillWorth 2026 首页" })).toHaveAttribute("href", "#top");
  await nav.getByRole("link", { name: "方法与数据" }).click();
  await expect(page).toHaveURL(/\/methodology$/);
  await expect(page.getByRole("heading", { name: "这个排名是怎么算出来的？" })).toBeVisible();
  await expect(page.getByRole("link", { name: "方法与数据" })).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("navigation", { name: "面包屑" }).getByRole("link", { name: "首页" })).toHaveAttribute("href", "/#top");
  await page.getByRole("link", { name: "SkillWorth 2026 首页" }).click();
  await expect(page).toHaveURL(/\/#top$/);
});

test("方法页默认是学生可读层，技术术语仅在附录出现", async ({ page }) => {
  await page.goto("/methodology");
  await expect(page.getByRole("heading", { name: "我们分析了什么？" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "市场价值怎么看？" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "为什么考虑学习时间？" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "学习时间准确吗？" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "现在不能回答什么？" })).toBeVisible();
  await expect(page.getByText("998", { exact: true })).toBeVisible();
  await expect(page.getByText("313", { exact: true })).toBeVisible();
  await expect(page.getByText("134", { exact: true })).toBeVisible();
  await expect(page.getByText("薪资比较")).toBeVisible();
  await expect(page.getByText("市场趋势")).toBeVisible();
  await expect(page.getByText("来源准入门槛（Source Gate）")).toBeHidden();
  await page.getByText("查看技术细节", { exact: true }).click();
  await expect(page.getByText("来源准入门槛（Source Gate）")).toBeVisible();
  await expect(page.getByText("原始、标准化、分析三层（Bronze / Silver / Gold）")).toBeVisible();
});

test("19 个角色筛选均保留主排名层与已观察技能", async ({ page, isMobile }) => {
  test.skip(isMobile);
  await page.goto("/lab/visual-v2#explore");
  const select = page.locator("#explore").getByLabel("岗位方向", { exact: true });
  await select.locator("option").nth(19).waitFor({ state: "attached" });
  const roles = await select.locator("option").evaluateAll((options) => options.slice(1).map((option) => (option as HTMLOptionElement).value));
  expect(roles).toHaveLength(19);
  for (const role of roles) {
    const response = role === "backend_engineer" ? null : page.waitForResponse((item) => item.url().includes(`role=${role}`) && item.ok());
    await select.selectOption(role);
    if (response) await response;
    await expect(select).toHaveValue(role);
    await expect(page.getByRole("region", { name: "主排名层" })).toBeVisible();
    await expect(page.getByRole("region", { name: "已观察技能" })).toBeVisible();
  }
});

test("移动端、Reduced Motion、控制台与请求保持可用", async ({ page, isMobile }) => {
  const messages: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message) => { if (["error", "warning"].includes(message.type())) messages.push(message.text()); });
  page.on("requestfailed", (request) => failedRequests.push(request.url()));
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /2026，学什么/ })).toBeVisible();
  if (isMobile) {
    const nav = page.getByRole("navigation", { name: "公开产品导航" });
    await expect(nav.getByRole("link", { name: "研究结论" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "方法与数据" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "查技术技能" })).toBeHidden();
    await expect(page.getByRole("link", { name: "进入 3D 技能星域" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await page.goto("/methodology");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  }
  expect(messages).toEqual([]);
  expect(failedRequests).toEqual([]);
});
