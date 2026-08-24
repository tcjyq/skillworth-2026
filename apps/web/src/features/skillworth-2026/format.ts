export const compactNumber = (value: number) => new Intl.NumberFormat("zh-CN", { notation: "compact", maximumFractionDigits: 1 }).format(value);
export const percentValue = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
export const scoreValue = (value: number) => value.toFixed(1);
export const rankRange = (min: number | null, max: number | null) => min == null || max == null ? "证据不足" : min === max ? `${min}` : `${min}–${max}`;
export const titleCase = (value: string) => value.split("_").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
