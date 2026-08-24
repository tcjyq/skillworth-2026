import type { Metadata } from "next";
import { SkillGraph } from "@/features/graph/skill-graph";
export const metadata: Metadata = { title: "技能图谱" };
export default function GraphLabPage() { return <SkillGraph />; }
