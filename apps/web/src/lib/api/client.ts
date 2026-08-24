import { ApiError, type MarketFilters, type OptimizerRequest, type OptimizerResult, type OpportunityRequest, type OpportunityResult } from "./types";

const API_BASE = "/backend-api";

export function marketQuery(filters: MarketFilters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else if (value) params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(payload?.error?.message ?? `请求失败（${response.status}）`, response.status, payload?.error?.code);
  }
  return response.json() as Promise<T>;
}

export const analyzePortfolio = (request: OpportunityRequest) => apiRequest<OpportunityResult>("/portfolio/analyze", { method: "POST", body: JSON.stringify(request) });
export const optimizePortfolio = (request: OptimizerRequest) => apiRequest<OptimizerResult>("/portfolio/optimize", { method: "POST", body: JSON.stringify(request) });
