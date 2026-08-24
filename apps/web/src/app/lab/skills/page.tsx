import type { Metadata } from "next";
import { SkillExplorer } from "@/features/skills/skill-explorer";
export const metadata: Metadata = { title: "技能探索" };
export default function SkillsLabPage() { return <SkillExplorer />; }
