import type { Metadata } from "next";
import { MarketPulse } from "@/features/market/market-pulse";
export const metadata: Metadata = { title: "市场研究" };
export default function MarketLabPage() { return <MarketPulse />; }
