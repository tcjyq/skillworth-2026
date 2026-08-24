"use client";

import { useMemo, useSyncExternalStore } from "react";
import type { EChartsOption } from "echarts";
import { EChartsChart } from "@/components/charts/echarts-chart";
import type { ChinaSkillWorthRecord } from "@/lib/api/types";
import { fallbackSkillColor, SKILL_TYPE_COLORS } from "./config";
import { paretoFrontier } from "./pareto";
import { percentValue, rankRange, scoreValue, titleCase } from "./format";
import { isSkillInTheme } from "./selection";

type FrontierChartProps = {
  records: ChinaSkillWorthRecord[];
  selectedId?: string;
  focusedId?: string | null;
  highlightedTheme?: string | null;
  onFocus?: (skillId: string | null) => void;
  onSelect: (record: ChinaSkillWorthRecord) => void;
};

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const COMPACT_QUERY = "(max-width: 639px)";
type LabelPosition = "top" | "right" | "bottom" | "left";
type Domain = { xMin: number; xMax: number; yMin: number; yMax: number; xMid: number; yMid: number };

function subscribeReducedMotion(callback: () => void) {
  const media = window.matchMedia(REDUCED_MOTION_QUERY);
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}

function reducedMotionSnapshot() { return window.matchMedia(REDUCED_MOTION_QUERY).matches; }
function reducedMotionServerSnapshot() { return false; }
function subscribeCompact(callback: () => void) {
  const media = window.matchMedia(COMPACT_QUERY);
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
function compactSnapshot() { return window.matchMedia(COMPACT_QUERY).matches; }
function compactServerSnapshot() { return false; }

function escapeHtml(value: string) {
  return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] ?? character);
}

function hexToRgba(hex: string, alpha: number) {
  const value = hex.replace("#", "");
  const normalized = value.length === 3 ? value.split("").map((character) => character + character).join("") : value;
  const number = Number.parseInt(normalized, 16);
  return `rgba(${(number >> 16) & 255},${(number >> 8) & 255},${number & 255},${alpha})`;
}

function nodeMaterial(color: string) {
  return {
    type: "radial" as const,
    x: 0.34,
    y: 0.28,
    r: 0.78,
    colorStops: [
      { offset: 0, color: "rgba(255,255,255,.96)" },
      { offset: 0.18, color: hexToRgba(color, 0.94) },
      { offset: 0.72, color: hexToRgba(color, 0.58) },
      { offset: 1, color: hexToRgba(color, 0.18) },
    ],
  };
}

type LabelBox = { left: number; right: number; bottom: number; top: number };

function overlapArea(left: LabelBox, right: LabelBox) {
  return Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left))
    * Math.max(0, Math.min(left.top, right.top) - Math.max(left.bottom, right.bottom));
}

function labelBox(position: LabelPosition, x: number, y: number, width: number, height: number, offsetX: number, offsetY: number): LabelBox {
  if (position === "top") return { left: x - width / 2, right: x + width / 2, bottom: y + offsetY, top: y + offsetY + height };
  if (position === "bottom") return { left: x - width / 2, right: x + width / 2, bottom: y - offsetY - height, top: y - offsetY };
  if (position === "left") return { left: x - offsetX - width, right: x - offsetX, bottom: y - height / 2, top: y + height / 2 };
  return { left: x + offsetX, right: x + offsetX + width, bottom: y - height / 2, top: y + height / 2 };
}

function labelPlacements(records: ChinaSkillWorthRecord[], bubbleSizes: Map<string, number>, domain: Domain, compact: boolean) {
  const placements = new Map<string, LabelPosition>();
  const occupied: LabelBox[] = [];
  const pointBoxes = records.map((record) => {
    const x = (record.learning_hours_expected - domain.xMin) / Math.max(domain.xMax - domain.xMin, 1);
    const y = (record.market_signal - domain.yMin) / Math.max(domain.yMax - domain.yMin, 1);
    const radius = (bubbleSizes.get(record.skill_id) ?? 28) / 2;
    return { id: record.skill_id, x, y, box: { left: x - radius / 1000, right: x + radius / 1000, bottom: y - radius / 620, top: y + radius / 620 } };
  });
  const pointMap = new Map(pointBoxes.map((point) => [point.id, point]));
  const visible = records
    .toSorted((left, right) => (left.skillworth_rank ?? Number.MAX_SAFE_INTEGER) - (right.skillworth_rank ?? Number.MAX_SAFE_INTEGER) || right.job_count - left.job_count)
    .slice(0, compact ? 6 : 12);

  for (const record of visible) {
    const point = pointMap.get(record.skill_id);
    if (!point) continue;
    const size = bubbleSizes.get(record.skill_id) ?? 28;
    const width = Math.min(0.15, Math.max(0.046, record.skill.length * 0.009 + 0.018));
    const height = compact ? 0.034 : 0.028;
    const offsetX = size / 2000 + 0.012;
    const offsetY = size / 1240 + 0.014;
    const preferred: LabelPosition[] = point.x > 0.76 ? ["left", "top", "bottom", "right"] : point.x < 0.2 ? ["right", "top", "bottom", "left"] : point.y > 0.82 ? ["bottom", "right", "left", "top"] : ["top", "right", "left", "bottom"];
    let best = preferred[0];
    let bestPenalty = Number.POSITIVE_INFINITY;
    for (const [preferenceIndex, position] of preferred.entries()) {
      const box = labelBox(position, point.x, point.y, width, height, offsetX, offsetY);
      const boundaryPenalty = Math.max(0, -box.left) + Math.max(0, box.right - 1) + Math.max(0, -box.bottom) + Math.max(0, box.top - 1);
      const labelPenalty = occupied.reduce((sum, other) => sum + overlapArea(box, other) * 1800, 0);
      const pointPenalty = pointBoxes.reduce((sum, other) => other.id === record.skill_id ? sum : sum + overlapArea(box, other.box) * 2200, 0);
      const penalty = boundaryPenalty * 300 + labelPenalty + pointPenalty + preferenceIndex * 0.02;
      if (penalty < bestPenalty) { best = position; bestPenalty = penalty; }
    }
    const box = labelBox(best, point.x, point.y, width, height, offsetX, offsetY);
    occupied.push(box);
    placements.set(record.skill_id, best);
  }
  return placements;
}

export function FrontierChart({ records, selectedId, focusedId, highlightedTheme, onFocus, onSelect }: FrontierChartProps) {
  const reducedMotion = useSyncExternalStore(subscribeReducedMotion, reducedMotionSnapshot, reducedMotionServerSnapshot);
  const compact = useSyncExternalStore(subscribeCompact, compactSnapshot, compactServerSnapshot);
  const recordMap = useMemo(() => new Map(records.map((record) => [record.skill_id, record])), [records]);
  const frontier = useMemo(() => paretoFrontier(records), [records]);
  const bubbleSizes = useMemo(() => {
    const jobCounts = records.map((record) => record.job_count);
    const minJobs = Math.min(...jobCounts, 0);
    const maxJobs = Math.max(...jobCounts, 1);
    return new Map(records.map((record) => {
      const normalized = (Math.sqrt(record.job_count) - Math.sqrt(minJobs)) / Math.max(Math.sqrt(maxJobs) - Math.sqrt(minJobs), 1);
      return [record.skill_id, 26 + normalized * 36];
    }));
  }, [records]);

  const domain = useMemo(() => {
    const xValues = records.map((record) => record.learning_hours_expected);
    const yValues = records.map((record) => record.market_signal);
    const rawXMin = Math.min(...xValues, 0);
    const rawXMax = Math.max(...xValues, 1);
    const rawYMin = Math.min(...yValues, 0);
    const rawYMax = Math.max(...yValues, 1);
    const xPad = Math.max(18, (rawXMax - rawXMin) * 0.08);
    const yPad = Math.max(2.5, (rawYMax - rawYMin) * 0.1);
    const xMin = Math.max(0, Math.floor((rawXMin - xPad) / 10) * 10);
    const xMax = Math.ceil((rawXMax + xPad) / 10) * 10;
    const yMin = Math.max(0, Math.floor((rawYMin - yPad) / 5) * 5);
    const yMax = Math.ceil((rawYMax + yPad) / 5) * 5;
    return { xMin, xMax, yMin, yMax, xMid: (xMin + xMax) / 2, yMid: (yMin + yMax) / 2 };
  }, [records]);

  const activeId = selectedId ?? focusedId ?? null;
  const placements = useMemo(() => labelPlacements(records, bubbleSizes, domain, compact), [bubbleSizes, compact, domain, records]);
  const option = useMemo<EChartsOption>(() => ({
    animationDuration: reducedMotion ? 0 : 620,
    animationDurationUpdate: reducedMotion ? 0 : 380,
    animationEasing: "quarticOut",
    animationEasingUpdate: "cubicOut",
    grid: { left: 22, right: 28, top: 54, bottom: 24, containLabel: true },
    tooltip: {
      trigger: "item",
      confine: true,
      borderWidth: 1,
      borderColor: "rgba(200,220,98,.28)",
      backgroundColor: "rgba(16,20,17,.96)",
      padding: [14, 16],
      extraCssText: "box-shadow:0 12px 34px rgba(0,0,0,.36);backdrop-filter:blur(12px);border-radius:2px",
      formatter: (params: unknown) => {
        const item = params as { seriesName?: string; data?: { skill_id?: string } };
        if (item.seriesName?.includes("EFFICIENCY FRONTIER")) return "<b style='color:#c8dc62'>EFFICIENCY FRONTIER</b><br><span style='color:#899187'>当前候选中不存在市场信号更高且学习投入更低的另一项技能。</span>";
        const record = item.data?.skill_id ? recordMap.get(item.data.skill_id) : undefined;
        if (!record) return "";
        return `<div style="min-width:230px"><div style="font:600 15px/1.2 var(--font-geist-sans);margin-bottom:5px;color:#f2f0e9">${escapeHtml(record.skill)}</div><div style="font:10px/1.4 var(--font-geist-mono);color:#c8dc62;margin-bottom:11px">#${String(record.skillworth_rank ?? "—").padStart(2, "0")} · ${escapeHtml(titleCase(record.robustness_level))}</div><div style="display:grid;grid-template-columns:1fr auto;gap:6px 20px;font:11px/1.5 var(--font-geist-sans);color:#8f988e"><span>SKILLWORTH</span><b style="font-family:var(--font-geist-mono);color:#f2f0e9">${scoreValue(record.skillworth_score)}</b><span>MARKET SIGNAL</span><b style="font-family:var(--font-geist-mono);color:#f2f0e9">${scoreValue(record.market_signal)}</b><span>LEARNING EFFORT</span><b style="font-family:var(--font-geist-mono);color:#f2f0e9">${record.learning_hours_expected}h</b><span>JOB COVERAGE</span><b style="font-family:var(--font-geist-mono);color:#f2f0e9">${percentValue(record.job_coverage)}</b><span>RANK RANGE</span><b style="font-family:var(--font-geist-mono);color:#c8dc62">${rankRange(record.sensitivity_rank_min, record.sensitivity_rank_max)}</b><span>CONFIDENCE</span><b style="font-family:var(--font-geist-mono);color:#f2f0e9">${record.confidence.toFixed(0)} · ${record.confidence_level}</b></div></div>`;
      },
    },
    xAxis: {
      type: "value",
      name: "LEARNING EFFORT · HOURS  →",
      nameLocation: "middle",
      nameGap: 44,
      min: domain.xMin,
      max: domain.xMax,
      splitNumber: 5,
      axisLabel: { formatter: "{value}h" },
    },
    yAxis: {
      type: "value",
      name: "MARKET SIGNAL  ↑",
      nameLocation: "middle",
      nameGap: 50,
      min: domain.yMin,
      max: domain.yMax,
      splitNumber: 5,
    },
    series: [
      {
        name: "EFFICIENCY FRONTIER GLOW",
        type: "line",
        data: frontier.map((record) => [record.learning_hours_expected, record.market_signal]),
        smooth: 0.28,
        symbol: "none",
        lineStyle: { color: "#c8dc62", width: 8, opacity: 0.055, shadowBlur: 22, shadowColor: "rgba(200,220,98,.5)" },
        emphasis: { disabled: true },
        silent: true,
        z: 1,
      },
      {
        name: "EFFICIENCY FRONTIER",
        type: "line",
        data: frontier.map((record) => [record.learning_hours_expected, record.market_signal]),
        smooth: 0.28,
        symbol: "none",
        lineStyle: { color: "#c8dc62", width: 1.35, opacity: 0.8, shadowBlur: 9, shadowColor: "rgba(200,220,98,.55)" },
        emphasis: { disabled: true },
        z: 2,
      },
      {
        name: "Skills",
        type: "scatter",
        universalTransition: true,
        data: records.map((record) => {
          const themeMatch = isSkillInTheme(record, highlightedTheme ?? null);
          const isActive = activeId === record.skill_id;
          const isDimmed = (activeId != null && !isActive) || (highlightedTheme != null && !themeMatch);
          const color = SKILL_TYPE_COLORS[record.skill_type] ?? fallbackSkillColor;
          return {
            id: record.skill_id,
            value: [record.learning_hours_expected, record.market_signal, record.job_count],
            skill_id: record.skill_id,
            name: record.skill,
            symbolSize: bubbleSizes.get(record.skill_id) ?? 28,
            itemStyle: {
              color: nodeMaterial(color),
              opacity: isDimmed ? 0.12 : record.robustness_level === "moderate" ? 0.42 : 0.94,
              borderColor: isActive ? "#edf5b7" : hexToRgba(color, 0.9),
              borderWidth: isActive ? 2 : 1,
              shadowBlur: isActive ? 30 : 13,
              shadowColor: isActive ? "rgba(200,220,98,.5)" : hexToRgba(color, 0.24),
            },
            label: { show: !isDimmed && (isActive || placements.has(record.skill_id)), position: placements.get(record.skill_id) ?? "top" },
          };
        }),
        label: {
          formatter: "{b}",
          distance: 9,
          color: "#ecebe4",
          fontSize: 11,
          fontWeight: 600,
          textBorderColor: "#101410",
          textBorderWidth: 4,
        },
        labelLayout: { hideOverlap: true, moveOverlap: "shiftY" },
        emphasis: { scale: 1.06, focus: "self", label: { show: true } },
        markArea: {
          silent: true,
          label: { color: "rgba(218,224,214,.56)", fontFamily: "monospace", fontSize: 10, fontWeight: 500, position: "insideTopLeft", padding: [10, 9], textBorderColor: "rgba(9,13,11,.7)", textBorderWidth: 3 },
          data: [
            [{ name: "HIGH LEVERAGE", xAxis: domain.xMin, yAxis: domain.yMid, itemStyle: { color: "rgba(200,220,98,.032)" }, label: { color: "rgba(200,220,98,.58)" } }, { xAxis: domain.xMid, yAxis: domain.yMax }],
            [{ name: "LONG-TERM BET", xAxis: domain.xMid, yAxis: domain.yMid, itemStyle: { color: "rgba(116,190,200,.025)" }, label: { color: "rgba(131,188,193,.56)" } }, { xAxis: domain.xMax, yAxis: domain.yMax }],
            [{ name: "QUICK WIN", xAxis: domain.xMin, yAxis: domain.yMin, itemStyle: { color: "rgba(210,163,111,.022)" }, label: { color: "rgba(210,163,111,.54)" } }, { xAxis: domain.xMid, yAxis: domain.yMid }],
            [{ name: "SELECTIVE BET", xAxis: domain.xMid, yAxis: domain.yMin, itemStyle: { color: "rgba(155,139,186,.025)" }, label: { color: "rgba(158,142,183,.54)" } }, { xAxis: domain.xMax, yAxis: domain.yMid }],
          ],
        },
        z: 4,
      },
      {
        name: "SELECTED SKILL",
        type: "scatter",
        data: selectedId && recordMap.has(selectedId) ? [{
          value: [recordMap.get(selectedId)!.learning_hours_expected, recordMap.get(selectedId)!.market_signal],
          symbolSize: (bubbleSizes.get(selectedId) ?? 28) + 16,
        }] : [],
        itemStyle: { color: "transparent", borderColor: "rgba(200,220,98,.8)", borderWidth: 1, shadowBlur: 24, shadowColor: "rgba(200,220,98,.42)" },
        silent: true,
        z: 5,
      },
    ],
  }), [activeId, bubbleSizes, domain, frontier, highlightedTheme, placements, recordMap, records, reducedMotion, selectedId]);

  return (
    <div className="frontier-stage">
      <div className="frontier-key" aria-hidden="true"><span /> EFFICIENCY FRONTIER</div>
      <EChartsChart
        option={option}
        className="h-[430px] w-full sm:h-[560px] lg:h-[650px]"
        ariaLabel="SkillWorth 技值前沿空间图，横轴为学习投入，纵轴为市场信号，气泡大小为岗位数量"
        onClick={(params) => {
          const data = params.data as { skill_id?: string } | undefined;
          const record = data?.skill_id ? recordMap.get(data.skill_id) : undefined;
          if (record) onSelect(record);
        }}
        onMouseOver={(params) => {
          const data = params.data as { skill_id?: string } | undefined;
          if (data?.skill_id) onFocus?.(data.skill_id);
        }}
        onMouseOut={() => onFocus?.(null)}
      />
      <details className="border-t border-[var(--sw-line)] px-1 py-3 text-xs text-[var(--sw-muted)]">
        <summary className="w-fit cursor-pointer select-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--sw-accent)]">使用键盘浏览图表数据</summary>
        <div className="mt-3 flex flex-wrap gap-2" aria-label="图表数据键盘列表">
          {records.map((record) => <button className="border border-[var(--sw-line-strong)] px-2.5 py-1.5 text-[var(--sw-text-secondary)] hover:border-[var(--sw-accent)] hover:text-[var(--sw-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--sw-accent)]" key={record.skill_id} onFocus={() => onFocus?.(record.skill_id)} onBlur={() => onFocus?.(null)} onClick={() => onSelect(record)}>{record.skill} · {record.market_signal.toFixed(1)} · {record.learning_hours_expected}h</button>)}
        </div>
      </details>
    </div>
  );
}
