"use client";

import { Warning, ArrowClockwise, Database } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingState({ label = "正在读取市场数据" }: { label?: string }) {
  return <div className="terminal-panel min-h-[280px] p-5" role="status"><div className="mb-8 flex items-center justify-between"><Skeleton className="h-4 w-40 bg-[#202322]" /><Skeleton className="h-3 w-20 bg-[#202322]" /></div><div className="space-y-5"><Skeleton className="h-px w-full bg-[#202322]" /><Skeleton className="h-28 w-full bg-[#151717]" /><Skeleton className="h-px w-full bg-[#202322]" /></div><p className="mt-6 text-[11px] text-[var(--text-muted)]">{label}</p></div>;
}

export function ErrorState({ message, retry }: { message?: string; retry?: () => void }) {
  const displayMessage = !message || /failed to fetch/i.test(message) ? "无法从 FastAPI 读取数据，请确认后端服务正在运行。" : message;
  return <div className="terminal-panel flex min-h-[220px] flex-col items-center justify-center border-[var(--negative)]/40 p-6 text-center"><Warning size={24} className="mb-3 text-[var(--negative)]" /><h2 className="text-[14px] font-medium">数据连接失败</h2><p className="mt-1 max-w-md text-[12px] text-[var(--text-secondary)]">{displayMessage}</p>{retry && <Button variant="outline" size="sm" className="mt-4" onClick={retry}><ArrowClockwise size={14} />重试</Button>}</div>;
}

export function EmptyState({ title = "当前筛选下暂无数据", description = "调整筛选条件后再试。", action, bare = false }: { title?: string; description?: string; action?: React.ReactNode; bare?: boolean }) {
  return <div className={`${bare ? "" : "terminal-panel"} flex min-h-[220px] flex-col items-center justify-center p-6 text-center`}><Database size={23} className="mb-3 text-[var(--text-muted)]" /><h2 className="text-[14px] font-medium">{title}</h2><p className="mt-1 max-w-md text-[12px] leading-5 text-[var(--text-secondary)]">{description}</p>{action}</div>;
}

export function LowConfidenceBanner({ title = "当前结论置信度较低", reasons }: { title?: string; reasons: string[] }) {
  return <div className="flex items-start gap-3 border-l-2 border-[var(--warning)] bg-[#17130d] px-3 py-2.5"><Warning size={16} className="mt-0.5 shrink-0 text-[var(--warning)]" /><div><p className="text-[12px] font-medium text-[#dec18a]">{title}</p><p className="mt-0.5 text-[11px] leading-[17px] text-[#99896b]">{reasons.join("；")}</p></div></div>;
}
