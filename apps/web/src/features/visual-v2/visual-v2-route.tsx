import { Noto_Sans_SC } from "next/font/google";
import { VisualV2ClientEntry } from "./visual-v2-client-entry";

const notoSansSC = Noto_Sans_SC({
  variable: "--font-noto-sans-sc",
  weight: "variable",
  subsets: ["latin"],
  display: "swap",
  preload: false,
  fallback: ["Microsoft YaHei UI", "PingFang SC", "Microsoft YaHei"],
});

export function VisualV2Route() {
  return <div className={notoSansSC.variable}><VisualV2ClientEntry /></div>;
}
