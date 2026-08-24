"use client";

import { useEffect, useRef } from "react";
import type { ECharts, EChartsOption } from "echarts";
import { skillWorthTheme, SKILLWORTH_THEME_NAME } from "./skillworth-theme";

let registered = false;

type ChartEventHandler = (params: Record<string, unknown>) => void;

export function EChartsChart({ option, className, ariaLabel, onClick, onMouseOver, onMouseOut }: { option: EChartsOption; className?: string; ariaLabel: string; onClick?: ChartEventHandler; onMouseOver?: ChartEventHandler; onMouseOut?: ChartEventHandler }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<ECharts | null>(null);
  const optionRef = useRef(option);
  const onClickRef = useRef(onClick);
  const onMouseOverRef = useRef(onMouseOver);
  const onMouseOutRef = useRef(onMouseOut);
  useEffect(() => {
    let disposed = false;
    let observer: ResizeObserver | null = null;
    const node = ref.current;
    if (!node) return;
    void import("echarts").then((echarts) => {
      if (disposed) return;
      if (!registered) { echarts.registerTheme(SKILLWORTH_THEME_NAME, skillWorthTheme); registered = true; }
      const chart = echarts.init(node, SKILLWORTH_THEME_NAME, { renderer: "canvas" });
      chartRef.current = chart;
      chart.setOption(optionRef.current, { notMerge: false, lazyUpdate: true });
      chart.on("click", (params) => onClickRef.current?.(params as unknown as Record<string, unknown>));
      chart.on("mouseover", (params) => onMouseOverRef.current?.(params as unknown as Record<string, unknown>));
      chart.on("mouseout", (params) => onMouseOutRef.current?.(params as unknown as Record<string, unknown>));
      observer = new ResizeObserver(() => chart.resize());
      observer.observe(node);
    });
    return () => { disposed = true; observer?.disconnect(); chartRef.current?.dispose(); chartRef.current = null; };
  }, []);
  useEffect(() => { optionRef.current = option; chartRef.current?.setOption(option, { notMerge: false, lazyUpdate: true }); }, [option]);
  useEffect(() => { onClickRef.current = onClick; }, [onClick]);
  useEffect(() => { onMouseOverRef.current = onMouseOver; }, [onMouseOver]);
  useEffect(() => { onMouseOutRef.current = onMouseOut; }, [onMouseOut]);
  return <div ref={ref} className={className ?? "h-[360px] w-full"} role="img" aria-label={ariaLabel} />;
}
