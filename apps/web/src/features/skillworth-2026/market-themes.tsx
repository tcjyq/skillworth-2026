"use client";

import type { ChinaMarketTheme } from "@/lib/api/types";
import { memo } from "react";
import { percentValue } from "./format";

export const MarketThemes = memo(function MarketThemes({ themes, selected, onSelect }: { themes: ChinaMarketTheme[]; selected: string | null; onSelect: (theme: string | null) => void }) {
  return (
    <div className="theme-field" aria-label="市场主题列表">
      {themes.map((theme) => {
        const active = selected === theme.market_theme;
        return (
          <button
            key={theme.market_theme}
            aria-pressed={active}
            onClick={() => onSelect(active ? null : theme.market_theme)}
            className={`theme-item group min-w-0 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--sw-accent)] ${active ? "theme-item-active" : ""}`}
          >
            <span className="theme-name">{theme.market_theme}</span>
            <span className="theme-rule" aria-hidden="true" />
            <span className="theme-stats">
              <ThemeMetric label="JOBS" value={theme.job_count.toLocaleString("zh-CN")} />
              <ThemeMetric label="COMPANIES" value={theme.company_count.toLocaleString("zh-CN")} />
              <ThemeMetric label="COVERAGE" value={percentValue(theme.job_coverage)} />
            </span>
            <span className="mt-4 block text-[10px] text-[var(--sw-muted)]">Market Theme ≠ Learnable Skill Ranking</span>
          </button>
        );
      })}
    </div>
  );
});

function ThemeMetric({ label, value }: { label: string; value: string }) {
  return <span><small>{label}</small><strong>{value}</strong></span>;
}
