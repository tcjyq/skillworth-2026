import { expect, test } from "@playwright/test";

test("岗位请求晚到或失败时不会把旧岗位数据放在新标题下", async ({ page }) => {
  test.skip(test.info().project.name.includes("mobile"));
  await page.goto("/lab/visual-v2#roles");
  const result = page.locator("#roles article");
  await expect(result.getByRole("heading", { name: /后端/ })).toBeVisible();
  let releaseAnalyst!: () => void;
  const analystGate = new Promise<void>((resolve) => { releaseAnalyst = resolve; });
  await page.route("**/backend-api/market/china-skillworth?*role=data_analyst", async (route) => {
    await analystGate;
    await route.continue();
  });
  await page.getByRole("button", { name: "数据分析" }).click();
  await expect(result).toContainText("正在读取该方向的当前样本");
  await expect(result.getByRole("heading", { name: /后端/ })).toHaveCount(0);
  await page.getByRole("button", { name: "前端", exact: true }).click();
  await expect(result.getByRole("heading", { name: /前端/ })).toBeVisible();
  releaseAnalyst();
  await expect(result.getByRole("heading", { name: /前端/ })).toBeVisible();
  await page.getByRole("button", { name: "后端", exact: true }).click();
  await expect(result.getByRole("heading", { name: /后端/ })).toBeVisible();
  await page.route("**/backend-api/market/china-skillworth?*role=ml_engineer", (route) => route.abort());
  await page.getByRole("button", { name: "AI / 机器学习" }).click();
  await expect(result).toContainText("当前数据暂时无法读取");
  await expect(result.getByRole("heading", { name: /后端/ })).toHaveCount(0);
});

test("production-safe artifact drives the frozen public release candidate without Real local files", async ({ page }) => {
  await page.goto("/");
  const scopeResponse = await page.request.get("/backend-api/market/china-skillworth?eligibility=main&robustness=robust&recency_window=180d");
  expect(scopeResponse.ok()).toBe(true);
  const scope = await scopeResponse.json();

  expect(scope.snapshot).toBe("freehire_china_tech_2026_08");
  expect(scope.job_count).toBe(998);
  expect(scope.company_count).toBe(313);
  expect(scope.skill_count).toBe(134);
  const metadataResponse = await page.request.get("/backend-api/release-metadata");
  expect(metadataResponse.ok()).toBe(true);
  const metadata = await metadataResponse.json();
  expect(metadata.classification).toBe("PUBLIC_SAFE");
  expect(metadata.source_snapshot).toBe(scope.snapshot);
  expect(metadata.access_date).toBe(scope.access_date);
  expect(metadata.job_count).toBe(scope.job_count);
  expect(metadata.company_count).toBe(scope.company_count);
  expect(metadata.skill_count).toBe(scope.skill_count);
  const qualityResponse = await page.request.get("/backend-api/data-quality");
  expect(qualityResponse.ok()).toBe(true);
  const quality = await qualityResponse.json();
  expect(quality.silver_row_count).toBeGreaterThan(scope.job_count);
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await expect(page.getByText("998", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("313", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("134", { exact: true }).first()).toBeVisible();

  const relation = await page.request.get("/backend-api/market/china-skill-relations?core_skill_id=programming_python&recency_window=180d");
  expect(relation.ok()).toBe(true);
  const relationPayload = await relation.json();
  expect(relationPayload.records.find((record: { related_skill_id: string; cooccurrence_count: number }) => record.related_skill_id === "database_sql")?.cooccurrence_count).toBe(128);

  for (const path of ["/backend-data/artifact_metadata.json", "/backend-data/skill_aggregates.json", "/backend-data/quality_snapshot.json"]) {
    const blocked = await page.request.get(path);
    expect(blocked.status()).toBe(404);
    expect((await blocked.json()).error.code).toBe("RESOURCE_NOT_FOUND");
  }
});

test("方法页在相同安全产物中展示质量、案例与敏感性范围", async ({ page }) => {
  await page.goto("/methodology");
  await expect(page.getByText("2026-08-29", { exact: false }).first()).toBeVisible();
  await expect(page.getByText(/547 \/ 1142/)).toBeVisible();
  await expect(page.getByText(/902 \/ 1142/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "三个可以复核的问题" })).toBeVisible();
  await expect(page.getByText(/Kubernetes 与 Terraform 共同出现于 11 个岗位/)).toBeVisible();
  await expect(page.getByText(/技术产品经理方向只有 3 个岗位/)).toBeVisible();
  await expect(page.getByText(/C\+\+：基准第 35 名；预设参数情景中第 18–50 名/)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
});

test("公开 Worker 拒绝岗位级操作与写入", async ({ page }) => {
  const portfolio = await page.request.post("/backend-api/portfolio/analyze", {
    data: { current_skills: [], target_role: "data_engineer", match_threshold: 0.7 },
  });
  expect(portfolio.status()).toBe(503);
  expect((await portfolio.json()).error.code).toBe("DATA_UNAVAILABLE");
  const write = await page.request.post("/backend-api/market/china-skillworth", { data: {} });
  expect(write.status()).toBe(503);
  expect((await write.json()).error.code).toBe("DATA_UNAVAILABLE");
});
