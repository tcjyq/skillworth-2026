import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppShell } from "@/components/app-shell/app-shell";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "SKILLWORTH 2026｜2026，学什么技术最值？", template: "%s｜SKILLWORTH 2026" },
  description: "从市场价值与学习投入重新看技术技能的性价比。基于当前可观察的中国公开技术岗位样本。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <body>
        <TooltipProvider delay={250}><AppShell>{children}</AppShell></TooltipProvider>
      </body>
    </html>
  );
}
