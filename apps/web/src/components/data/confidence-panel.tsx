import type { Confidence } from "@/lib/api/types";
import { integer } from "@/lib/format";

export function ConfidencePanel({ confidence }: { confidence: Confidence }) {
  const tone = confidence.confidence_level === "High" ? "text-[var(--positive)]" : confidence.confidence_level === "Medium" ? "text-[var(--warning)]" : "text-[var(--negative)]";
  return <section className="terminal-panel"><div className="flex items-end justify-between border-b border-[var(--border-subtle)] px-4 py-3"><div><p className="label-caps">DATA CONFIDENCE</p><p className={`mono mt-1 text-[22px] ${tone}`}>{integer(confidence.confidence_score)}<span className="text-[11px]"> / 100</span></p></div><span className={`mono text-[10px] ${tone}`}>{confidence.confidence_level.toUpperCase()}</span></div><div>{Object.entries(confidence.confidence_components).map(([name, item]) => <div key={name} className="grid grid-cols-[1fr_42px] items-center gap-3 border-b border-[var(--border-subtle)] px-4 py-2 last:border-0"><div><p className="text-[11px]">{name.replaceAll("_", " ")}</p><div className="mt-1 h-px bg-[#252826]"><div className="h-px bg-[var(--accent)]" style={{ width: `${item.component_score ?? 0}%` }} /></div></div><span className="mono text-right text-[10px] text-[var(--text-secondary)]">{item.component_score == null ? "N/A" : item.component_score.toFixed(0)}</span></div>)}</div></section>;
}
