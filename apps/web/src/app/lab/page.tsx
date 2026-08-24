import Link from "next/link";

const researchRoutes = [
  ["/lab/market", "技术技能市场", "传统市场概览与来源平衡分析"],
  ["/lab/skills", "技能探索", "单项技能的需求、关联与证据"],
  ["/lab/roles", "岗位洞察", "岗位方向的技能结构"],
  ["/lab/graph", "技能图谱", "完整技能共现网络"],
  ["/lab/portfolio", "我的技能组合", "个人技能覆盖分析"],
  ["/lab/optimizer", "学习优化器", "学习时间分配实验"],
  ["/lab/data-quality", "数据质量", "管道、覆盖率与置信度"],
  ["/methodology", "方法说明", "指标定义、边界与局限"],
] as const;

export default function LabPage() {
  return <div className="mx-auto max-w-5xl px-5 py-12 sm:px-8"><p className="label-caps">Secondary Research Area</p><h1 className="mt-3 text-3xl font-semibold tracking-[-.04em]">SkillWorth Lab</h1><p className="mt-3 max-w-xl text-sm leading-6 text-[var(--text-secondary)]">这里保留完整研究工具与历史视图。它们不属于公开产品的核心叙事，但底层功能没有被删除。</p><div className="mt-10 divide-y divide-[var(--border-subtle)] border-y border-[var(--border-subtle)]">{researchRoutes.map(([href, title, description], index) => <Link key={href} href={href} className="grid gap-2 py-5 hover:bg-[var(--surface-hover)] sm:grid-cols-[52px_180px_1fr] sm:px-3"><span className="font-mono text-xs text-[var(--text-muted)]">{String(index + 1).padStart(2, "0")}</span><span className="text-sm text-[var(--foreground)]">{title}</span><span className="text-xs text-[var(--text-secondary)]">{description}</span></Link>)}</div></div>;
}
