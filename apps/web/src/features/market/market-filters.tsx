"use client";

import type { MarketFilters } from "@/lib/api/types";
import type { Role } from "@/lib/api/types";
import { categoryName, roleName } from "@/lib/format";

const control = "h-8 border border-[var(--border)] bg-transparent px-2 text-[11px] text-[var(--text-secondary)] outline-none transition-colors focus:border-[var(--accent)]";

export function MarketFiltersBar({ filters, category, roles, categories, onFilters, onCategory }: { filters: MarketFilters; category: string; roles: Role[]; categories: string[]; onFilters: (filters: MarketFilters) => void; onCategory: (category: string) => void }) {
  return <div className="mb-4 grid gap-2 border-y border-[var(--border-subtle)] bg-[var(--surface)] px-3 py-2 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_1fr_1fr_1fr]">
    <label className="grid gap-1"><span className="label-caps">目标岗位</span><select className={control} value={filters.role_id ?? ""} onChange={(e) => onFilters({ ...filters, role_id: e.target.value || undefined })}><option value="">全部岗位</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{roleName(role.role_id)}</option>)}</select></label>
    <label className="grid gap-1"><span className="label-caps">城市代码</span><input className={control} value={filters.city_code ?? ""} placeholder="全部城市" onChange={(e) => onFilters({ ...filters, city_code: e.target.value || undefined })} /></label>
    <label className="grid gap-1"><span className="label-caps">开始日期</span><input className={control} type="date" value={filters.published_from ?? ""} onChange={(e) => onFilters({ ...filters, published_from: e.target.value || undefined })} /></label>
    <label className="grid gap-1"><span className="label-caps">结束日期</span><input className={control} type="date" value={filters.published_to ?? ""} onChange={(e) => onFilters({ ...filters, published_to: e.target.value || undefined })} /></label>
    <label className="grid gap-1"><span className="label-caps">技能类别</span><select className={control} value={category} onChange={(e) => onCategory(e.target.value)}><option value="">全部类别</option>{categories.map((item) => <option key={item} value={item}>{categoryName(item)}</option>)}</select></label>
  </div>;
}
