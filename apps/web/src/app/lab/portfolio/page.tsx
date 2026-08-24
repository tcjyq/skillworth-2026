import type { Metadata } from "next";
import { PortfolioPage } from "@/features/portfolio/portfolio-page";
export const metadata: Metadata = { title: "我的技能组合" };
export default function PortfolioLabPage() { return <PortfolioPage />; }
