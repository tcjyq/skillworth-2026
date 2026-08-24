export const SKILLWORTH_THEME_NAME = "skillworth-terminal";

export const skillWorthTheme = {
  color: ["#C8DC62", "#8EB9A2", "#D7AA72", "#8BA6C7", "#A79AB7", "#72AAA5"],
  backgroundColor: "transparent",
  textStyle: { color: "#929990", fontFamily: "Geist Sans, PingFang SC, Microsoft YaHei, sans-serif", fontSize: 12 },
  title: { textStyle: { color: "#F2F0E9", fontSize: 14, fontWeight: 600 }, subtextStyle: { color: "#697068", fontSize: 11 } },
  line: { itemStyle: { borderWidth: 1 }, lineStyle: { width: 1.5 }, symbolSize: 5, symbol: "circle", smooth: 0.2 },
  bar: { itemStyle: { barBorderRadius: 0 } },
  graph: { itemStyle: { borderColor: "#090909", borderWidth: 1 }, lineStyle: { color: "#303532", width: 1, opacity: 0.7 }, label: { color: "#B8BCB9" } },
  categoryAxis: { axisLine: { show: true, lineStyle: { color: "#242626" } }, axisTick: { show: false }, axisLabel: { color: "#8B918D", fontSize: 11 }, splitLine: { show: false } },
  valueAxis: { axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: "#8B918D", fontSize: 11 }, splitLine: { show: true, lineStyle: { color: "#191B1A", width: 1 } } },
  tooltip: { backgroundColor: "#171A16", borderColor: "#343A32", borderWidth: 1, textStyle: { color: "#F2F0E9", fontSize: 12 }, extraCssText: "border-radius:2px;box-shadow:0 16px 44px rgba(0,0,0,.42);padding:11px 13px;" },
};
