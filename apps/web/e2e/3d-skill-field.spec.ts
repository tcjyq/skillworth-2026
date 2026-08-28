import { expect, test, type Page } from "@playwright/test";

const realMode = process.env.SKILLWORTH_E2E_MODE === "real";

type TransitionProbe = {
  camera: number[];
  target: number[];
  nodes: Record<string, number[]>;
  phase: string;
  morph: number;
};

async function readTransitionProbe(page: Page): Promise<TransitionProbe> {
  return page.getByTestId("skill-field-canvas").evaluate((element) => ({
    camera: (element.getAttribute("data-camera-position") ?? "").split(",").map(Number),
    target: (element.getAttribute("data-camera-target") ?? "").split(",").map(Number),
    nodes: JSON.parse(element.getAttribute("data-node-probe") ?? "{}") as Record<string, number[]>,
    phase: element.getAttribute("data-transition-phase") ?? "",
    morph: Number(element.getAttribute("data-node-morph-progress") ?? "0"),
  }));
}

function distance(left: number[], right: number[]) {
  return Math.hypot(...left.map((value, index) => value - right[index]));
}

async function chooseSkill(page: Page, label: string) {
  const search = page.getByRole("combobox", { name: "搜索技能或职业" });
  await search.fill(label);
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await page.getByRole("option", { name: new RegExp(escaped) }).first().click();
}

async function expectAnalysisHashNavigation(page: Page) {
  await expect(page.locator("#analysis-results")).toBeInViewport({ timeout: realMode ? 10_000 : 5_000 });
}

test("分析结果与 3D 技能星域通过正常 history 双向切换", async ({ page, isMobile }) => {
  await page.goto("/lab/visual-v2#analysis-results");

  const analysisNavigation = page.getByRole("navigation", { name: "分析结果与 3D 技能星域" });
  await expect(analysisNavigation.getByRole("link", { name: "分析结果", exact: true })).toHaveAttribute("aria-current", "page");
  await expect(analysisNavigation.getByRole("link", { name: "3D 技能星域", exact: true })).toHaveAttribute("href", "/skill-field");
  await expect(page.getByRole("link", { name: "进入 3D 技能星域" })).toHaveAttribute("href", "/skill-field");
  await expectAnalysisHashNavigation(page);

  await analysisNavigation.getByRole("link", { name: "3D 技能星域", exact: true }).click();
  await expect(page).toHaveURL(/\/skill-field$/);
  const fieldNavigation = page.getByRole("navigation", { name: "分析结果与 3D 技能星域" });
  await expect(fieldNavigation.getByRole("link", { name: "3D 技能星域", exact: true })).toHaveAttribute("aria-current", "page");

  await page.goBack();
  await expect(page).toHaveURL(/\/lab\/visual-v2#analysis-results$/);
  await expectAnalysisHashNavigation(page);
  await page.goForward();
  await expect(page).toHaveURL(/\/skill-field$/);

  const analysisLink = fieldNavigation.getByRole("link", { name: "分析结果", exact: true });
  await analysisLink.focus();
  await expect(analysisLink).toBeFocused();
  await analysisLink.press("Enter");
  await expect(page).toHaveURL(/\/lab\/visual-v2#analysis-results$/);
  await expectAnalysisHashNavigation(page);

  if (isMobile) {
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  }
});

test("正式 3D 路由可直接打开，公开界面不显示 Lab 或版本标记", async ({ page }) => {
  await page.goto("/skill-field");

  await expect(page).toHaveTitle(/3D 技能星域/);
  await expect(page.getByRole("heading", { name: "3D 技能星域" })).toBeVisible();
  await expect(page.getByTestId("skill-field-frame")).toBeVisible();
  await expect(page.getByText(/\bLab\b|Visual V2|V2\.3|Prototype|Experiment/i)).toHaveCount(0);
});

test("回到全景仅在离开 GLOBAL_VALUE Home 后显示，并在重置后隐藏", async ({ page }) => {
  await page.goto("/skill-field");
  const resetHome = page.getByRole("button", { name: "回到全景" });
  const canvas = page.getByTestId("skill-field-canvas");
  await expect(resetHome).toHaveCount(0);

  const demandMode = page.getByRole("button", { name: "只看招聘需求" });
  await demandMode.click();
  await expect(demandMode).toHaveAttribute("aria-pressed", "true");
  await expect(canvas).toHaveAttribute("data-transition-phase", "IDLE");
  await expect(resetHome).toBeVisible();
  await resetHome.click();
  await expect(page.getByRole("button", { name: "学习优先" })).toHaveAttribute("aria-pressed", "true");
  await expect(canvas).toHaveAttribute("data-transition-phase", "IDLE");
  await expect(resetHome).toHaveCount(0);
});

test("分析首页入口不创建 WebGL context，也不挂载 3D Canvas", async ({ page }) => {
  await page.addInitScript(() => {
    let webglContexts = 0;
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, contextId: string, options?: unknown) {
      if (contextId === "webgl" || contextId === "webgl2" || contextId === "experimental-webgl") webglContexts += 1;
      return original.call(this, contextId as never, options as never);
    } as typeof HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(window, "__skillworthWebglContextCount", { get: () => webglContexts });
  });
  await page.goto("/");

  await expect(page.getByRole("link", { name: "进入 3D 技能星域" })).toHaveAttribute("href", "/skill-field");
  await expect(page.locator('[data-testid="skill-field-canvas"]')).toHaveCount(0);
  expect(await page.evaluate(() => Reflect.get(window, "__skillworthWebglContextCount") as number)).toBe(0);
});

test("3D 技能星域支持搜索、职业、需求模式、移动端与 Reduced Motion", async ({ page, isMobile }) => {
  const consoleMessages: string[] = [];
  page.on("console", (message) => {
    if (!["error", "warning"].includes(message.type())) return;
    const text = message.text();
    if (!text.includes("Automatic fallback to software WebGL has been deprecated")) consoleMessages.push(text);
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/lab/3d-skill-field");
  await expect(page.getByRole("link", { name: "返回 SkillWorth 2026" })).toContainText("SkillWorth 2026");
  await expect(page.getByRole("link", { name: "SkillWorth Lab 首页" })).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "主导航" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "市场" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "我的技能组合" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "组合", exact: true })).toHaveCount(0);
  await expect(page.getByText(/\bLab\b|Visual V2|V2\.3|Prototype|Experiment/i)).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "3D 技能星域" })).toBeVisible();
  await expect(page.getByTestId("skill-field-frame")).toBeVisible();
  await expect(page.getByTestId("skill-field-canvas")).toBeVisible();
  await expect(page.getByText("价值核心", { exact: true })).toBeVisible();
  await expect(page.getByTestId("value-core-annotation")).toContainText("只看远近，不看方向");
  const canvasProbe = page.getByTestId("skill-field-canvas");
  await expect(canvasProbe).toHaveAttribute("data-quality-profile", isMobile ? "LOW" : "HIGH");
  await expect(canvasProbe).toHaveAttribute("data-background-star-count", isMobile ? "130" : "380");
  await expect(canvasProbe).toHaveAttribute("data-atmosphere-variant", "B");
  await expect(canvasProbe).toHaveAttribute("data-background-motion", "static");
  await expect(canvasProbe).toHaveAttribute("data-skill-motion-enabled", "false");
  await expect(canvasProbe).toHaveAttribute("data-star-material", "A");
  await expect(canvasProbe).toHaveAttribute("data-reduced-motion", "true");
  await expect(canvasProbe).toHaveAttribute("data-idle-rotation", "false");
  await expect(canvasProbe).toHaveAttribute("data-camera-min-azimuth", "-Infinity");
  await expect(canvasProbe).toHaveAttribute("data-camera-max-azimuth", "Infinity");

  const search = page.getByRole("combobox", { name: "搜索技能或职业" });
  await search.fill(realMode ? "Python" : "SQL");
  const searchResults = page.getByRole("listbox");
  await expect(searchResults).toBeVisible();
  const searchBox = await search.boundingBox();
  const searchResultsBox = await searchResults.boundingBox();
  const initialFrameBox = await page.getByTestId("skill-field-frame").boundingBox();
  expect(searchBox && searchResultsBox && initialFrameBox).toBeTruthy();
  expect(searchResultsBox!.y + searchResultsBox!.height).toBeLessThanOrEqual(initialFrameBox!.y);
  await page.getByRole("option", { name: new RegExp(realMode ? "Python" : "SQL") }).first().click();
  await expect(page.getByTestId("skill-field-frame")).toContainText(new RegExp(`${realMode ? "Python" : "SQL"}，通常和哪些技能`));
  await expect(page.getByRole("heading", { name: realMode ? "Python" : "SQL", exact: true })).toBeVisible();
  const frameBox = await page.getByTestId("skill-field-frame").boundingBox();
  const canvasBox = await page.getByTestId("skill-field-canvas").boundingBox();
  const detailBox = await page.getByTestId("skill-field-detail").boundingBox();
  expect(frameBox && canvasBox && detailBox).toBeTruthy();
  expect(canvasBox!.y).toBeGreaterThanOrEqual(frameBox!.y);
  expect(canvasBox!.y + canvasBox!.height).toBeLessThanOrEqual(frameBox!.y + frameBox!.height);
  expect(detailBox!.y).toBeGreaterThanOrEqual(frameBox!.y + frameBox!.height);
  if (isMobile) {
    expect(canvasBox!.height).toBeGreaterThanOrEqual(420);
    expect(canvasBox!.height).toBeLessThanOrEqual(500);
    await expect(page.getByTestId("skill-field-touch-hint")).toBeVisible();
  }

  await page.getByRole("button", { name: "回到全局" }).click();
  await page.getByRole("button", { name: "只看招聘需求" }).click();
  await expect(page.getByTestId("skill-field-frame")).toContainText("如果只看招聘需求，答案会怎么变？");

  await search.fill(realMode ? "DevOps" : "数据分析");
  const roleOption = page.getByRole("option", { name: new RegExp(realMode ? "DevOps" : "数据分析") }).last();
  await roleOption.click();
  await expect(page.getByTestId("skill-field-frame")).toContainText(/答案会怎么变/);
  await expect(page.getByText(/个岗位样本/).first()).toBeVisible();
  if (isMobile) expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await expect(page.getByTestId("skill-field-canvas")).toHaveAttribute("data-relation-particle-count", "0");
  expect(consoleMessages).toEqual([]);
});

test("相机可见技能驱动有限且会变化的浏览标签", async ({ page, isMobile }) => {
  await page.goto("/lab/3d-skill-field");
  const canvas = page.getByTestId("skill-field-canvas");
  await expect(canvas).toHaveAttribute("data-label-refresh-cadence-hz", "8");
  await expect(canvas).toHaveAttribute("data-dynamic-label-count", /[1-9]/);
  const budget = isMobile ? 5 : 8;
  expect(Number(await canvas.getAttribute("data-dynamic-label-count"))).toBeLessThanOrEqual(budget);
  expect(await canvas.getByTestId("skill-field-label").count()).toBeLessThanOrEqual(budget);
  if (isMobile) return;

  const first = await canvas.getAttribute("data-dynamic-label-ids");
  const box = await canvas.boundingBox();
  expect(box).toBeTruthy();
  await page.mouse.move(box!.x + box!.width * 0.82, box!.y + box!.height * 0.56);
  await page.mouse.down();
  await page.mouse.move(box!.x + box!.width * 0.22, box!.y + box!.height * 0.56, { steps: 18 });
  await page.mouse.up();
  await page.waitForTimeout(500);
  const second = await canvas.getAttribute("data-dynamic-label-ids");
  if (realMode) expect(second).not.toBe(first);
  expect((second ?? "").split(",").filter(Boolean).length).toBeLessThanOrEqual(budget);
});

test("技能聚焦保持节点身份、原位识别、相机连续与丝滑返回", async ({ page, isMobile }) => {
  test.skip(isMobile);
  await page.goto("/lab/3d-skill-field");
  const canvas = page.getByTestId("skill-field-canvas");
  await expect(canvas).toHaveAttribute("data-node-probe", /database_sql/);
  const originalCanvas = await canvas.elementHandle();
  const initial = await readTransitionProbe(page);
  const coreLabel = realMode ? "Python" : "SQL";
  const coreId = realMode ? "programming_python" : "database_sql";
  const neighborId = realMode ? "database_sql" : "programming_python";

  await chooseSkill(page, coreLabel);
  await expect(page.getByRole("listbox")).toHaveCount(0);
  const recognized = await readTransitionProbe(page);
  expect(distance(recognized.nodes[coreId], initial.nodes[coreId])).toBeLessThan(0.02);
  await expect(canvas).toHaveAttribute("data-transition-phase", /CAMERA_FLY|CONSTELLATION_MORPH/);

  const cameraSamples: number[][] = [];
  for (let index = 0; index < 5; index += 1) {
    cameraSamples.push((await readTransitionProbe(page)).camera);
    await page.waitForTimeout(110);
  }
  await expect(canvas).toHaveAttribute("data-transition-phase", "SETTLED", { timeout: 3_000 });
  const settled = await readTransitionProbe(page);
  await expect(canvas).toHaveAttribute("data-node-morph-observed-intermediate", "true");
  const midwayNodes = JSON.parse(await canvas.getAttribute("data-node-morph-intermediate-probe") ?? "{}") as Record<string, number[]>;
  expect(distance(settled.nodes[coreId], initial.nodes[coreId])).toBeLessThan(0.02);
  if (realMode) {
    expect(distance(midwayNodes[neighborId], initial.nodes[neighborId])).toBeGreaterThan(0.02);
    expect(distance(midwayNodes[neighborId], settled.nodes[neighborId])).toBeGreaterThan(0.02);
  }
  expect(await originalCanvas?.evaluate((element) => element.isConnected)).toBe(true);
  await expect(canvas).toHaveAttribute("data-unique-skill-count", await canvas.getAttribute("data-skill-star-count") ?? "");
  const finalCamera = settled.camera;
  const pathDistances = cameraSamples.map((sample) => distance(sample, finalCamera));
  expect(pathDistances.at(-1)!).toBeLessThan(pathDistances[0]);
  expect(pathDistances.slice(1).every((value, index) => value <= pathDistances[index] + 0.08)).toBe(true);

  await page.getByRole("button", { name: "回到全局" }).click();
  await expect(canvas).toHaveAttribute("data-transition-phase", "IDLE", { timeout: 3_000 });
  const returned = await readTransitionProbe(page);
  expect(distance(returned.nodes[coreId], initial.nodes[coreId])).toBeLessThan(0.02);
  if (realMode) expect(distance(returned.nodes[neighborId], initial.nodes[neighborId])).toBeLessThan(0.02);
  expect(await originalCanvas?.evaluate((element) => element.isConnected)).toBe(true);
});

test("快速换目标只允许最新 generation 完成", async ({ page, isMobile }) => {
  test.skip(isMobile);
  const response = await page.request.get("/backend-api/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d");
  const payload = await response.json() as { records: Array<{ skill_id: string; skill: string }> };
  const first = realMode ? { skill_id: "programming_python", skill: "Python" } : payload.records[0];
  const second = realMode ? { skill_id: "database_sql", skill: "SQL" } : payload.records[1];
  expect(first && second).toBeTruthy();
  await page.goto("/lab/3d-skill-field");
  await chooseSkill(page, first.skill);
  await page.waitForTimeout(190);
  await chooseSkill(page, second.skill);
  const canvas = page.getByTestId("skill-field-canvas");
  await expect(canvas).toHaveAttribute("data-transition-phase", "SETTLED", { timeout: 3_000 });
  await expect(canvas).toHaveAttribute("data-active-skill", second.skill_id);
  await expect(page.getByRole("heading", { name: second.skill, exact: true })).toBeVisible();
  const probe = await readTransitionProbe(page);
  expect(distance(probe.target, probe.nodes[second.skill_id])).toBeLessThan(0.05);
});

test("拖拽和滚轮都立即中断自动相机且不继续 relation morph", async ({ page, isMobile }) => {
  test.skip(isMobile);
  const interrupt = async (kind: "drag" | "wheel") => {
    await page.goto("/lab/3d-skill-field");
    await chooseSkill(page, realMode ? "Python" : "SQL");
    const canvas = page.getByTestId("skill-field-canvas");
    await expect(canvas).toHaveAttribute("data-transition-phase", "CAMERA_FLY", { timeout: 1_500 });
    const webglCanvas = canvas.locator("canvas");
    const box = await webglCanvas.boundingBox();
    expect(box).toBeTruthy();
    await webglCanvas.hover();
    if (kind === "drag") {
      await page.mouse.down();
      await page.mouse.move(box!.x + box!.width * 0.7, box!.y + box!.height * 0.46, { steps: 6 });
      await page.mouse.up();
    } else {
      await page.mouse.wheel(0, -420);
    }
    await expect(canvas).toHaveAttribute("data-transition-phase", "IDLE");
    await page.waitForTimeout(650);
    await expect(canvas).toHaveAttribute("data-transition-phase", "IDLE");
    await expect(page.getByLabel("一级技能关系")).toHaveCount(0);
  };
  await interrupt("drag");
  await interrupt("wheel");
});

test("WebGL 初始化失败时保留 2D 搜索与技能列表", async ({ page }) => {
  await page.goto("/lab/3d-skill-field?fallback=1");
  await expect(page.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "分析结果", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "已切换到 2D 技能视图" })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "搜索技能或职业" })).toBeVisible();
  await expect(page.getByRole("region", { name: "2D 技能列表" })).toBeVisible();
  if (realMode) await expect(page.getByRole("region", { name: "2D 技能列表" })).toContainText("招聘需求 #3 → 学习性价比 #35");
});

test("3D 数据失败时仍可返回分析结果", async ({ page }) => {
  await page.route("**/backend-api/market/china-skillworth**", (route) => route.abort());
  await page.goto("/lab/3d-skill-field");

  await expect(page.getByRole("heading", { name: "技能星域暂时无法加载" })).toBeVisible();
  const analysisLink = page.getByRole("navigation", { name: "分析结果与 3D 技能星域" }).getByRole("link", { name: "分析结果", exact: true });
  await expect(analysisLink).toHaveAttribute("href", "/lab/visual-v2#analysis-results");
  await expect(analysisLink).toBeVisible();
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
  await expect(page.getByRole("heading", { name: "3D 技能星域" })).toBeVisible();
  await expect(page.getByLabel("数据范围")).toContainText("998 个岗位");
  await expect(page.getByLabel("数据范围")).toContainText("313 家公司");
  await expect(page.getByTestId("skill-field-canvas")).toHaveAttribute("data-skill-star-count", "134");
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
  await expect(page.getByTestId("skill-field-detail")).toContainText("128 个岗位一起出现 · 近 180 天");
});
