export function Metric({ label, value, note, tone }: { label: string; value: string; note?: string; tone?: "positive" | "negative" | "warning" }) {
  const color = tone === "positive" ? "text-[var(--positive)]" : tone === "negative" ? "text-[var(--negative)]" : tone === "warning" ? "text-[var(--warning)]" : "text-[var(--foreground)]";
  return <div className="min-w-0 border-r border-[var(--border-subtle)] px-4 py-3 last:border-r-0"><p className="label-caps truncate">{label}</p><p className={`mono mt-2 text-[20px] leading-6 ${color}`}>{value}</p>{note && <p className="mt-1 truncate text-[10px] text-[var(--text-muted)]">{note}</p>}</div>;
}
