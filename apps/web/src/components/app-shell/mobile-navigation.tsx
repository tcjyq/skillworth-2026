"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { primaryRoutes } from "./routes";

export function MobileNavigation() {
  const pathname = usePathname();
  return <nav className="fixed inset-x-0 bottom-0 z-40 grid h-[58px] grid-cols-5 border-t border-[var(--border)] bg-[#0b0c0c] md:hidden">{primaryRoutes.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={cn("flex flex-col items-center justify-center gap-1 text-[9px]", pathname.startsWith(href) ? "text-[var(--accent)]" : "text-[var(--text-secondary)]")}><Icon size={18} weight={pathname.startsWith(href) ? "fill" : "regular"} />{label.replace("我的技能组合", "组合")}</Link>)}</nav>;
}
