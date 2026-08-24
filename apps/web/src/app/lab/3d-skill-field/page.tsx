import { Noto_Sans_SC } from "next/font/google";
import { SkillFieldPage } from "@/features/3d-skill-field/skill-field-page";

const notoSansSC = Noto_Sans_SC({
  variable: "--font-noto-sans-sc",
  weight: "variable",
  subsets: ["latin"],
  display: "swap",
  preload: false,
  fallback: ["Microsoft YaHei UI", "PingFang SC", "Microsoft YaHei"],
});

export default function SkillFieldRoute() {
  return <div className={notoSansSC.variable}><SkillFieldPage /></div>;
}
