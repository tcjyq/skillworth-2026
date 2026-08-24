"use client";

import { useMemo, useRef, useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { ChinaSkillWorthRecord, Role } from "@/lib/api/types";
import { roleLabel } from "@/features/visual-v2/terminology";
import styles from "../skill-field.module.css";

type SearchResult =
  | { entity: "skill"; id: string; label: string; detail: string }
  | { entity: "role"; id: string; label: string; detail: string; sampleSize: number };

function score(label: string, query: string) {
  const value = label.toLocaleLowerCase();
  const target = query.toLocaleLowerCase();
  if (value === target) return 0;
  if (value.startsWith(target)) return 1;
  const index = value.indexOf(target);
  if (index >= 0) return 2 + index / 100;
  let cursor = 0;
  for (const character of target) {
    cursor = value.indexOf(character, cursor);
    if (cursor < 0) return Number.POSITIVE_INFINITY;
    cursor += 1;
  }
  return 10 + (value.length - target.length) / 100;
}

export function SearchCommand({
  skills,
  roles,
  onSelectSkill,
  onSelectRole,
}: {
  skills: ChinaSkillWorthRecord[];
  roles: Role[];
  onSelectSkill: (skillId: string, label: string) => void;
  onSelectRole: (roleId: string, label: string, sampleSize: number) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => {
    const target = query.trim();
    if (!target) return [];
    const skillResults: SearchResult[] = skills
      .map((item) => ({ item, score: score(`${item.skill} ${item.skill_id}`, target) }))
      .filter((item) => Number.isFinite(item.score))
      .toSorted((left, right) => left.score - right.score)
      .slice(0, 6)
      .map(({ item }) => ({ entity: "skill", id: item.skill_id, label: item.skill, detail: item.skillworth_rank ? `学习性价比第 ${item.skillworth_rank}` : "已观察，当前不进入主排名" }));
    const roleResults: SearchResult[] = roles
      .map((item) => ({ item, label: roleLabel(item.role_id), score: score(`${roleLabel(item.role_id)} ${item.role_id}`, target) }))
      .filter((item) => Number.isFinite(item.score))
      .toSorted((left, right) => left.score - right.score)
      .slice(0, 5)
      .map(({ item, label }) => ({ entity: "role", id: item.role_id, label, detail: `${item.canonical_job_count} 个岗位样本`, sampleSize: item.canonical_job_count }));
    return [...skillResults, ...roleResults];
  }, [query, roles, skills]);

  const select = (result: SearchResult) => {
    if (result.entity === "skill") onSelectSkill(result.id, result.label);
    else onSelectRole(result.id, result.label, result.sampleSize);
    setQuery("");
    setOpen(false);
    inputRef.current?.focus();
  };
  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((value) => Math.min(value + 1, results.length - 1)); }
    if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((value) => Math.max(value - 1, 0)); }
    if (event.key === "Enter" && results[activeIndex]) { event.preventDefault(); select(results[activeIndex]); }
    if (event.key === "Escape") { setOpen(false); setQuery(""); }
  };

  return <div className={styles.search}>
    <MagnifyingGlass aria-hidden="true" size={18} />
    <input
      ref={inputRef}
      type="search"
      role="combobox"
      aria-label="搜索技能或职业"
      aria-expanded={open && results.length > 0}
      aria-controls="skill-field-search-results"
      aria-activedescendant={open && results[activeIndex] ? `search-result-${activeIndex}` : undefined}
      autoComplete="off"
      placeholder="搜索技能或职业，例如 Python / 数据工程 / DevOps"
      value={query}
      onChange={(event) => { setQuery(event.target.value); setOpen(true); setActiveIndex(0); }}
      onFocus={() => setOpen(Boolean(query.trim()))}
      onKeyDown={onKeyDown}
    />
    {open && results.length > 0 && <div id="skill-field-search-results" role="listbox" className={styles.searchResults}>
      {results.map((result, index) => <div key={`${result.entity}:${result.id}`}>
        {(index === 0 || results[index - 1].entity !== result.entity) && <p>{result.entity === "skill" ? "技能" : "职业方向"}</p>}
        <button
          id={`search-result-${index}`}
          type="button"
          role="option"
          aria-selected={index === activeIndex}
          onMouseEnter={() => setActiveIndex(index)}
          onClick={() => select(result)}
        >
          <span>{result.label}</span><small>{result.detail}</small>
        </button>
      </div>)}
    </div>}
  </div>;
}
