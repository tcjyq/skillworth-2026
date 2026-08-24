"use client";

import { useState } from "react";
import { Check, X } from "@phosphor-icons/react";
import type { SkillDemand } from "@/lib/api/types";

export function SkillPicker({ skills, value, onChange }: { skills: SkillDemand[]; value: string[]; onChange: (value: string[]) => void }) {
  const [query, setQuery] = useState("");
  const selected = skills.filter((item) => value.includes(item.skill_id));
  const visible = skills.filter((item) => item.canonical_name.toLowerCase().includes(query.toLowerCase())).slice(0, 30);
  const toggle = (id: string) => onChange(value.includes(id) ? value.filter((item) => item !== id) : [...value, id]);
  return <div className="border border-[var(--border)] bg-[#0b0c0c]"><div className="flex min-h-9 flex-wrap gap-1 border-b border-[var(--border-subtle)] p-1.5">{selected.map((item) => <button type="button" key={item.skill_id} onClick={() => toggle(item.skill_id)} className="flex items-center gap-1 border border-[#4a3b22] bg-[#19160f] px-1.5 py-1 text-[10px] text-[var(--accent)]">{item.canonical_name}<X size={10} /></button>)}<input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={selected.length ? "继续添加…" : "输入技能名称"} className="min-w-[120px] flex-1 bg-transparent px-1 text-[11px] outline-none" /></div>{query && <div className="scrollbar-thin max-h-44 overflow-y-auto">{visible.map((item) => <button type="button" key={item.skill_id} onClick={() => toggle(item.skill_id)} className="flex w-full items-center justify-between border-b border-[var(--border-subtle)] px-3 py-2 text-left text-[11px] hover:bg-[var(--surface-hover)]"><span>{item.canonical_name}</span>{value.includes(item.skill_id) && <Check size={13} className="text-[var(--accent)]" />}</button>)}</div>}</div>;
}
