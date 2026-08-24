"use client";

import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChartsChart } from "@/components/charts/echarts-chart";
import { EmptyState, LowConfidenceBanner } from "@/components/states/data-states";
import type { SkillDemand, TrendRecord } from "@/lib/api/types";

export function MarketMap({ skills, trends }: { skills: SkillDemand[]; trends: TrendRecord[] }) {
  const trendMap = useMemo(() => new Map(trends.map((item) => [item.skill_id, item])), [trends]);
  const points = skills.flatMap((skill) => {
    const trend = trendMap.get(skill.skill_id);
    if (skill.job_coverage == null || trend?.change_6m == null || trend.conclusion_strength !== "qualified") return [];
    return [{ name: skill.canonical_name, value: [skill.job_coverage * 100, trend.change_6m * 100, skill.job_count], skill }];
  });
  const option: EChartsOption = useMemo(() => ({
    animationDurationUpdate: 180,
    grid: { left: 54, right: 24, top: 26, bottom: 46 },
    tooltip: { trigger: "item", formatter: (p: unknown) => { const item = p as { data: { name: string; value: number[] } }; return `<b>${item.data.name}</b><br/>岗位覆盖率 ${item.data.value[0].toFixed(1)}%<br/>6M 变化 ${item.data.value[1].toFixed(1)}%<br/>岗位数 ${item.data.value[2]}`; } },
    xAxis: { type: "value", name: "岗位覆盖率 →", nameLocation: "middle", nameGap: 32, axisLabel: { formatter: "{value}%" } },
    yAxis: { type: "value", name: "6M 变化", axisLabel: { formatter: "{value}%" } },
    series: [{ type: "scatter", data: points, symbolSize: (value: number[]) => Math.max(18, Math.min(62, 14 + Math.sqrt(value[2]) * 10)), itemStyle: { color: "#D8A54A", borderColor: "#E9C781", borderWidth: 1, opacity: .86 }, label: { show: true, position: "top", color: "#C8CBC8", fontSize: 10, formatter: "{b}" }, emphasis: { scale: 1.08, itemStyle: { opacity: 1 } } }],
  }), [points]);
  if (!points.length) return <div className="relative min-h-[460px]"><EChartsChart option={option} className="h-[460px] w-full opacity-30" ariaLabel="技能市场地图暂无足够的六个月趋势数据" /><div className="absolute inset-x-6 top-1/2 -translate-y-1/2"><EmptyState bare title="暂无可靠的 6 个月技能趋势" description="当前数据仍可用于需求观察，但样本月份不足，不能生成真实的纵轴位置。" /></div></div>;
  return <div><EChartsChart option={option} className="h-[460px] w-full" ariaLabel="技能市场地图，横轴为岗位覆盖率，纵轴为六个月变化，气泡大小为岗位数" /><LowConfidenceBanner title="请结合置信度解读市场位置" reasons={["气泡仅展示满足趋势样本规则的技能"]} /></div>;
}
