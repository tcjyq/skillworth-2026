import { Noto_Sans_SC } from "next/font/google";
import { VisualV2Page } from "@/features/visual-v2/visual-v2-page";

const notoSansSC = Noto_Sans_SC({
  variable: "--font-noto-sans-sc",
  weight: "variable",
  subsets: ["latin"],
  display: "swap",
  preload: false,
  fallback: ["Microsoft YaHei UI", "PingFang SC", "Microsoft YaHei"],
});

export default function VisualV2Route() {
  return <div className={notoSansSC.variable}><VisualV2Page /></div>;
}
