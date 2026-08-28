"use client";

import { useEffect, useState } from "react";
import { Navigation } from "./navigation";
import { CommandPalette } from "./command-palette";
import { MobileNavigation } from "./mobile-navigation";
import { PublicHeader } from "./public-header";
import { usePathname } from "next/navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [commandOpen, setCommandOpen] = useState(false);
  useEffect(() => {
    const handler = (event: KeyboardEvent) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setCommandOpen((value) => !value); } };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);
  if (pathname === "/lab/visual-v2" || pathname === "/lab/3d-skill-field" || pathname === "/skill-field" || pathname === "/methodology") return children;
  if (pathname === "/") return <div className="min-h-screen"><PublicHeader /><main>{children}</main></div>;
  return <div className="min-h-screen"><Navigation openCommand={() => setCommandOpen(true)} /><main className="min-h-[calc(100vh-60px)] pb-[calc(66px+env(safe-area-inset-bottom))] md:pb-0">{children}</main><MobileNavigation /><CommandPalette open={commandOpen} onOpenChange={setCommandOpen} /></div>;
}
