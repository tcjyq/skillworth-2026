"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function PublicHeader() {
  const pathname = usePathname();
  return <><a href="#main-content" className="fixed left-3 top-3 z-50 -translate-y-16 bg-[var(--sw-accent)] px-3 py-2 text-xs font-medium text-[var(--sw-canvas)] focus:translate-y-0">跳到主要内容</a><header className="sticky top-0 z-40 border-b border-[var(--sw-line)] bg-[color:var(--sw-canvas)]/94 backdrop-blur-md"><div className="mx-auto flex h-14 max-w-[1560px] items-center px-5 sm:px-8 lg:px-12"><Link href="/" className="sw-focus flex items-baseline gap-2" aria-label="SkillWorth 2026 首页"><span className="text-sm font-semibold tracking-[-.025em]">SKILLWORTH</span><span className="font-mono text-[9px] text-[var(--sw-accent)]">2026</span></Link><nav aria-label="公开产品导航" className="ml-auto flex items-center gap-5 text-[11px] text-[var(--sw-muted)] sm:gap-7"><Link href="/methodology" aria-current={pathname === "/methodology" ? "page" : undefined} className="sw-focus hover:text-[var(--sw-text)] aria-[current=page]:text-[var(--sw-accent)]">Methodology</Link><Link href="/#data-scope" className="sw-focus hover:text-[var(--sw-text)]">Data Scope</Link></nav></div></header></>;
}
