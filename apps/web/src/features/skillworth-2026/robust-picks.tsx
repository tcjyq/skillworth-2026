"use client";

import { useState } from "react";
import type { ChinaSkillWorthRecord } from "@/lib/api/types";
import { rankRange, scoreValue } from "./format";

type RobustPicksProps = {
  records: ChinaSkillWorthRecord[];
  focusedId?: string | null;
  onFocus?: (skillId: string | null) => void;
  onSelect: (record: ChinaSkillWorthRecord) => void;
};

export function RobustPicks({ records, focusedId, onFocus, onSelect }: RobustPicksProps) {
  const [showAllMobile, setShowAllMobile] = useState(false);
  const rankingScale = Math.max(...records.flatMap((record) => [record.sensitivity_rank_max ?? 0, record.skillworth_rank ?? 0]), 1);
  return (
    <div className="market-board overflow-hidden border-y border-[var(--sw-line)]">
      <div className="market-board-header hidden grid-cols-[58px_1.35fr_repeat(3,minmax(100px,1fr))_1.25fr] border-b border-[var(--sw-line)] px-4 py-3 font-mono text-[9px] uppercase tracking-[.12em] text-[var(--sw-muted)] md:grid">
        <span>Rank</span><span>Skill</span><span>Market Signal</span><span>Effort</span><span>SkillWorth</span><span>Range</span>
      </div>
      {records.map((record, index) => {
        const active = focusedId === record.skill_id;
        return (
          <button
            key={record.skill_id}
            onClick={() => onSelect(record)}
            onMouseEnter={() => onFocus?.(record.skill_id)}
            onMouseLeave={() => onFocus?.(null)}
            onFocus={() => onFocus?.(record.skill_id)}
            onBlur={() => onFocus?.(null)}
            className={`market-board-row group w-full grid-cols-[44px_1fr_auto] items-center border-b border-[var(--sw-line)] px-4 py-[17px] text-left last:border-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[var(--sw-accent)] md:min-h-[58px] md:grid md:grid-cols-[58px_1.35fr_repeat(3,minmax(100px,1fr))_1.25fr] md:py-0 ${index < 4 || showAllMobile ? "grid" : "hidden"} ${active ? "market-board-row-active" : ""}`}
          >
            <span className="font-mono text-xs text-[var(--sw-muted)]">{String(record.skillworth_rank ?? "—").padStart(2, "0")}</span>
            <span className="market-board-skill text-sm font-medium text-[var(--sw-text)] group-hover:text-[var(--sw-accent)] group-focus:text-[var(--sw-accent)]">{record.skill}</span>
            <span className="hidden font-mono text-xs tabular-nums text-[var(--sw-text-secondary)] md:block">{scoreValue(record.market_signal)}</span>
            <span className="hidden font-mono text-xs tabular-nums text-[var(--sw-text-secondary)] md:block">{record.learning_hours_expected}h</span>
            <span className="font-mono text-sm tabular-nums text-[var(--sw-accent)] md:text-xs">{scoreValue(record.skillworth_score)}</span>
            <span className="hidden md:block"><RankRangeMini min={record.sensitivity_rank_min} max={record.sensitivity_rank_max} scale={rankingScale} /></span>
            <span className="col-start-2 mt-1 flex items-center gap-2 font-mono text-[10px] text-[var(--sw-muted)] md:hidden"><span>市场 {scoreValue(record.market_signal)}</span><span>·</span><span>{record.learning_hours_expected}h</span><span>·</span><span>{rankRange(record.sensitivity_rank_min, record.sensitivity_rank_max)}</span></span>
          </button>
        );
      })}
      {records.length > 4 && <button type="button" aria-expanded={showAllMobile} onClick={() => setShowAllMobile((value) => !value)} className="sw-focus flex min-h-11 w-full items-center justify-center border-t border-[var(--sw-line)] px-4 text-sm text-[var(--sw-accent)] md:hidden">{showAllMobile ? "收起其余候选" : `查看其余 ${records.length - 4} 项稳健候选`}</button>}
    </div>
  );
}

function RankRangeMini({ min, max, scale }: { min: number | null; max: number | null; scale: number }) {
  if (min == null || max == null) return <span className="font-mono text-xs text-[var(--sw-muted)]">—</span>;
  const left = ((min - 1) / Math.max(scale - 1, 1)) * 100;
  const width = Math.max(4, ((max - min + 1) / Math.max(scale, 1)) * 100);
  return (
    <span className="flex items-center gap-3" aria-label={`敏感性排名范围 ${min} 到 ${max}`}>
      <span className="font-mono text-[10px] text-[var(--sw-text-secondary)]">{String(min).padStart(2, "0")}</span>
      <span className="market-board-range relative h-px min-w-20 flex-1 bg-[var(--sw-line-strong)]"><span className="absolute -top-px h-[3px] min-w-1 bg-[var(--sw-accent)] shadow-[0_0_8px_rgba(200,220,98,.35)]" style={{ left: `${left}%`, width: `${width}%` }} /></span>
      <span className="font-mono text-[10px] text-[var(--sw-text-secondary)]">{String(max).padStart(2, "0")}</span>
    </span>
  );
}
