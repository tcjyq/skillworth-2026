import { ChartScatter, CirclesThreePlus, Database, Graph, GraduationCap, Pulse, Target, TrendUp } from "@phosphor-icons/react";

export const primaryRoutes = [
  { href: "/lab/market", label: "市场", icon: Pulse },
  { href: "/lab/skills", label: "技能", icon: ChartScatter },
  { href: "/lab/roles", label: "岗位", icon: Target },
  { href: "/lab/graph", label: "技能图谱", icon: Graph },
  { href: "/lab/portfolio", label: "我的技能组合", icon: CirclesThreePlus },
] as const;

export const secondaryRoutes = [
  { href: "/lab/optimizer", label: "学习优化器", icon: TrendUp },
  { href: "/lab/data-quality", label: "数据质量", icon: Database },
  { href: "/methodology", label: "方法说明", icon: GraduationCap },
] as const;

export const allRoutes = [...primaryRoutes, ...secondaryRoutes];
