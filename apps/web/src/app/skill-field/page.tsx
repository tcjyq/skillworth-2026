import type { Metadata } from "next";
import { Noto_Sans_SC } from "next/font/google";
import { SkillFieldClientEntry } from "@/features/3d-skill-field/skill-field-client-entry";

const notoSansSC = Noto_Sans_SC({
  variable: "--font-noto-sans-sc",
  weight: "variable",
  subsets: ["latin"],
  display: "swap",
  preload: false,
  fallback: ["Microsoft YaHei UI", "PingFang SC", "Microsoft YaHei"],
});

export const metadata: Metadata = {
  title: "3D 技能星域",
  description: "SkillWorth 2026 的 3D 技能星域：基于中国公开技术岗位补充样本，探索技术技能的学习优先级与关联关系。",
};

export default function SkillFieldRoute() {
  return <div className={notoSansSC.variable}><SkillFieldClientEntry /></div>;
}
