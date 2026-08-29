import app from "vinext/server/fetch-handler";

interface WorkerEnv {
  ASSETS: {
    fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>;
  };
}

type Json = Record<string, unknown>;
const jsonCache = new Map<string, Promise<Json>>();

const worker = {
  async fetch(
    request: Request,
    env: WorkerEnv,
    ctx: Parameters<typeof app.fetch>[2],
  ): Promise<Response> {
    const requestUrl = new URL(request.url);
    if (requestUrl.pathname.startsWith("/backend-data/")) {
      return apiError(404, "RESOURCE_NOT_FOUND", "Resource not found");
    }
    if (requestUrl.pathname.startsWith("/backend-api/")) {
      return handleApi(request, env);
    }
    return app.fetch(request, env, ctx);
  },
};

export default worker;

async function handleApi(request: Request, env: WorkerEnv): Promise<Response> {
  if (request.method !== "GET") {
    return apiError(503, "DATA_UNAVAILABLE", "Job-level operations are unavailable in production-safe mode");
  }
  const url = new URL(request.url);
  const path = url.pathname.slice("/backend-api".length);
  if (path === "/health") return jsonResponse({ status: "ok", service_version: "production_safe_aggregate_v1", warehouse_available: true });
  if (path === "/market/china-skillworth") return chinaSkillWorth(url, env);
  if (path === "/market/china-skill-relations") return chinaSkillRelations(url, env);
  if (path === "/roles") return jsonResponse((await artifact(env, request, "role_aggregates.json")).roles);
  if (path === "/data-quality") return jsonResponse((await artifact(env, request, "quality_snapshot.json")).data_quality);
  if (path === "/market/summary" || path === "/market/trends" || path === "/skills") return aggregateScope(path, url, env, request);
  if (path === "/sources") return apiError(503, "DATA_UNAVAILABLE", "Source-level data is intentionally excluded from the production-safe artifact");

  const roleMatch = path.match(/^\/roles\/([^/]+)$/);
  if (roleMatch) return roleDetail(roleMatch[1], env, request);
  const relatedMatch = path.match(/^\/skills\/([^/]+)\/related$/);
  if (relatedMatch) return relatedSkill(relatedMatch[1], env, request);
  const detailMatch = path.match(/^\/skills\/([^/]+)(?:\/(trend|salary))?$/);
  if (detailMatch) return skillDetail(detailMatch[1], detailMatch[2], env, request);
  return apiError(404, "RESOURCE_NOT_FOUND", "Resource not found");
}

async function chinaSkillWorth(url: URL, env: WorkerEnv): Promise<Response> {
  const payload = await artifact(env, new Request(url), "skill_aggregates.json");
  const recency = url.searchParams.get("recency_window") ?? "180d";
  const role = url.searchParams.get("role") ?? "__global__";
  const scope = (payload.china_skillworth_scopes as Record<string, Json>)[`${recency}:${role}`];
  if (!scope) return apiError(503, "DATA_UNAVAILABLE", "Requested China SkillWorth aggregate scope is unavailable");
  const eligibility = url.searchParams.get("eligibility") ?? "main";
  const robustness = url.searchParams.get("robustness") ?? "robust";
  const skillType = url.searchParams.get("skill_type");
  const records = (scope.records as Json[]).filter((record) =>
    (eligibility === "all" || record.skillworth_eligibility === eligibility)
      && (robustness === "all" || record.robustness_level === robustness)
      && (!skillType || record.skill_type === skillType),
  );
  return jsonResponse({ ...scope, records });
}

async function chinaSkillRelations(url: URL, env: WorkerEnv): Promise<Response> {
  const coreSkillId = url.searchParams.get("core_skill_id");
  if (!coreSkillId) return apiError(422, "VALIDATION_ERROR", "core_skill_id is required");
  if ((url.searchParams.get("recency_window") ?? "180d") !== "180d") return apiError(503, "DATA_UNAVAILABLE", "Requested relation aggregate is unavailable");
  const roleId = url.searchParams.get("role_id") ?? "__global__";
  const payload = await artifact(env, new Request(url), "relation_aggregates.json");
  const scope = (payload.scopes as Record<string, Json>)[`${coreSkillId}:${roleId}`];
  return scope ? jsonResponse(scope) : apiError(503, "DATA_UNAVAILABLE", "Requested relation aggregate is unavailable");
}

async function aggregateScope(path: string, url: URL, env: WorkerEnv, request: Request): Promise<Response> {
  const payload = await artifact(env, request, "skill_aggregates.json");
  const section = path === "/market/summary" ? "market_summary" : path === "/market/trends" ? "market_trends" : "skill_demand";
  const role = url.searchParams.get("role_id") ?? "global";
  const scope = (payload[section] as Record<string, Json>)[role];
  return scope ? jsonResponse(scope) : apiError(503, "DATA_UNAVAILABLE", "Requested aggregate scope is unavailable");
}

async function roleDetail(roleId: string, env: WorkerEnv, request: Request): Promise<Response> {
  const payload = await artifact(env, request, "role_aggregates.json");
  const detail = (payload.role_details as Record<string, Json>)[roleId];
  return detail ? jsonResponse(detail) : apiError(404, "RESOURCE_NOT_FOUND", "Resource not found");
}

async function relatedSkill(skillId: string, env: WorkerEnv, request: Request): Promise<Response> {
  const payload = await artifact(env, request, "skill_aggregates.json");
  const related = (payload.related_skills as Record<string, Json>)[skillId];
  return related ? jsonResponse(related) : apiError(404, "RESOURCE_NOT_FOUND", "Resource not found");
}

async function skillDetail(skillId: string, suffix: string | undefined, env: WorkerEnv, request: Request): Promise<Response> {
  const payload = await artifact(env, request, "skill_aggregates.json");
  const detail = (payload.skill_details as Record<string, Json>)[skillId];
  if (!detail) return apiError(404, "RESOURCE_NOT_FOUND", "Resource not found");
  if (suffix === "trend") return jsonResponse(detail.trend);
  if (suffix === "salary") return jsonResponse({ salary_distribution: detail.salary_distribution, adjusted_salary_association: detail.adjusted_salary_association });
  return jsonResponse(detail);
}

function artifact(env: WorkerEnv, request: Request, name: string): Promise<Json> {
  const existing = jsonCache.get(name);
  if (existing) return existing;
  const loading = env.ASSETS.fetch(new URL(`/backend-data/${name}`, request.url)).then(async (response: Response) => {
    if (!response.ok) throw new Error(`Missing production-safe asset: ${name}`);
    return response.json() as Promise<Json>;
  });
  jsonCache.set(name, loading);
  return loading;
}

function jsonResponse(payload: unknown): Response {
  return Response.json(payload, { headers: { "cache-control": "public, max-age=300" } });
}

function apiError(status: number, code: string, message: string): Response {
  return Response.json({ error: { code, message, details: [] } }, { status, headers: { "cache-control": "no-store" } });
}
