"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Command, Database, MagnifyingGlass } from "@phosphor-icons/react";
import { cn } from "@/lib/utils";
import { primaryRoutes } from "./routes";

export function Navigation({ openCommand }: { openCommand: () => void }) {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 flex h-[60px] items-center border-b border-[var(--border-subtle)] bg-[#090909]/95 px-5 backdrop-blur-sm">
      <Link href="/lab" className="mr-10 flex items-baseline gap-2 whitespace-nowrap" aria-label="SkillWorth Lab 首页">
        <span className="text-[16px] font-semibold tracking-[-.02em]">技值</span>
        <span className="mono text-[11px] text-[var(--text-secondary)]">SKILLWORTH</span>
      </Link>
      <nav className="hidden h-full items-center gap-7 md:flex" aria-label="主导航">
        {primaryRoutes.map(({ href, label }) => {
          const active = pathname.startsWith(href);
          return <Link key={href} href={href} className={cn("relative flex h-full items-center text-[13px] transition-colors hover:text-white", active ? "text-[var(--accent)] after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-[var(--accent)]" : "text-[var(--text-secondary)]")}>{label}</Link>;
        })}
      </nav>
      <div className="ml-auto flex items-center gap-1">
        <Link href="/lab/data-quality" className={cn("hidden h-8 items-center gap-2 px-2 text-[12px] transition-colors hover:text-white sm:flex", pathname.startsWith("/lab/data-quality") ? "text-[var(--accent)]" : "text-[var(--text-secondary)]")}><Database size={15} />数据</Link>
        <button onClick={openCommand} className="flex h-8 items-center gap-2 border border-[var(--border)] px-2.5 text-[12px] text-[var(--text-secondary)] transition-colors hover:border-[#3a3d3b] hover:text-white" aria-label="打开命令面板">
          <MagnifyingGlass size={14} /><span className="hidden sm:inline">搜索</span><span className="mono ml-1 hidden items-center gap-1 border-l border-[var(--border)] pl-2 text-[10px] lg:flex"><Command size={11} /> K</span>
        </button>
      </div>
    </header>
  );
}
