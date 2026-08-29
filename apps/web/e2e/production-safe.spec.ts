import { expect, test } from "@playwright/test";

test("production-safe artifact drives the frozen public release candidate without Real local files", async ({ page }) => {
  await page.goto("/");
  const scopeResponse = await page.request.get("/backend-api/market/china-skillworth?eligibility=main&robustness=robust&recency_window=180d");
  expect(scopeResponse.ok()).toBe(true);
  const scope = await scopeResponse.json();

  expect(scope.snapshot).toBe("freehire_china_tech_2026_08");
  expect(scope.job_count).toBe(998);
  expect(scope.company_count).toBe(313);
  expect(scope.skill_count).toBe(134);
  await expect(page.getByRole("heading", { name: "2026，学什么技术最值？" })).toBeVisible();
  await expect(page.getByText("998", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("313", { exact: true }).first()).toBeVisible();
  await expect(page.getByText("134", { exact: true }).first()).toBeVisible();

  const relation = await page.request.get("/backend-api/market/china-skill-relations?core_skill_id=programming_python&recency_window=180d");
  expect(relation.ok()).toBe(true);
  const relationPayload = await relation.json();
  expect(relationPayload.records.find((record: { related_skill_id: string; cooccurrence_count: number }) => record.related_skill_id === "database_sql")?.cooccurrence_count).toBe(128);

  const portfolio = await page.request.post("/backend-api/portfolio/analyze", {
    data: { current_skills: [], target_role: "data_engineer", match_threshold: 0.7 },
  });
  expect(portfolio.status()).toBe(503);
  expect((await portfolio.json()).error.code).toBe("DATA_UNAVAILABLE");
});
