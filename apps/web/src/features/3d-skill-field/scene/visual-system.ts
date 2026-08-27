import { stableHash } from "../layout";

export type QualityProfileName = "HIGH" | "BALANCED" | "LOW";
export type AtmosphereVariant = "A" | "B";

export function nextQualityProfile(current: QualityProfileName): QualityProfileName {
  return current === "HIGH" ? "BALANCED" : "LOW";
}

export const DECORATIVE_PARTICLE_POLICY = {
  pickable: false,
  countsAsSkillNode: false,
} as const;

export const QUALITY_PROFILES = {
  HIGH: {
    dpr: [1, 1.7] as const,
    particleCount: 380,
    visibleLabelCount: 6,
    bloomMode: "off" as const,
    aaMode: "msaa" as const,
    haloIntensity: 1,
    renderDataNodes: true,
    preserveLayout: true,
    ambientCadenceFps: 8,
  },
  BALANCED: {
    dpr: [1, 1.45] as const,
    particleCount: 260,
    visibleLabelCount: 6,
    bloomMode: "off" as const,
    aaMode: "msaa" as const,
    haloIntensity: 0.72,
    renderDataNodes: true,
    preserveLayout: true,
    ambientCadenceFps: 6,
  },
  LOW: {
    dpr: [1, 1.1] as const,
    particleCount: 130,
    visibleLabelCount: 3,
    bloomMode: "off" as const,
    aaMode: "msaa" as const,
    haloIntensity: 0.42,
    renderDataNodes: true,
    preserveLayout: true,
    ambientCadenceFps: 4,
  },
} satisfies Record<QualityProfileName, {
  dpr: readonly [number, number];
  particleCount: number;
  visibleLabelCount: number;
  bloomMode: "off";
  aaMode: "msaa";
  haloIntensity: number;
  renderDataNodes: true;
  preserveLayout: true;
  ambientCadenceFps: number;
}>;

export const ATMOSPHERE_VARIANTS = {
  A: { label: "保持数量，降低视觉权重", particleCounts: { HIGH: 720, BALANCED: 480, LOW: 220 } },
  B: { label: "减少数量，降低视觉权重", particleCounts: { HIGH: 380, BALANCED: 260, LOW: 130 } },
} as const satisfies Record<AtmosphereVariant, {
  label: string;
  particleCounts: Record<QualityProfileName, number>;
}>;

export function resolveAtmosphereVariant(value?: string | null): AtmosphereVariant {
  return value?.toUpperCase() === "A" ? "A" : "B";
}

export function atmosphereParticleCount(quality: QualityProfileName, variant: AtmosphereVariant) {
  return ATMOSPHERE_VARIANTS[variant].particleCounts[quality];
}

export const SKILL_STAR_MATERIAL = {
  label: "A · Soft Point Star",
  pointScale: 402,
  coreRadius: 0.42,
  haloFalloff: 2.55,
  haloStrength: 0.72,
  whiteCore: 0.9,
} as const satisfies {
  label: string;
  pointScale: number;
  coreRadius: number;
  haloFalloff: number;
  haloStrength: number;
  whiteCore: number;
};

export function skillStarMotion(skillId: string) {
  const hash = stableHash(skillId);
  return {
    phase: (hash % 6283) / 1000,
    speed: 0.72 + ((hash >>> 8) % 1000) / 1000 * 0.28,
    amplitude: 0.045 + ((hash >>> 18) % 1000) / 1000 * 0.025,
  };
}

export function starPointerShouldSelect(pointerDelta: number) {
  return pointerDelta <= 6;
}

const CATEGORY_FAMILIES = {
  code: { hue: 207, saturation: 34, lightness: 61 },
  data: { hue: 174, saturation: 29, lightness: 61 },
  intelligence: { hue: 278, saturation: 23, lightness: 64 },
  web: { hue: 24, saturation: 40, lightness: 62 },
  infrastructure: { hue: 91, saturation: 26, lightness: 58 },
  evidence: { hue: 47, saturation: 29, lightness: 63 },
  assurance: { hue: 348, saturation: 28, lightness: 62 },
  other: { hue: 126, saturation: 10, lightness: 59 },
} as const;

type CategoryFamily = keyof typeof CATEGORY_FAMILIES;

function categoryFamily(category: string): CategoryFamily {
  if (["programming", "backend"].includes(category)) return "code";
  if (["database", "data_analysis", "data_engineering"].includes(category)) return "data";
  if (category === "ai_ml") return "intelligence";
  if (category === "frontend") return "web";
  if (["cloud", "devops"].includes(category)) return "infrastructure";
  if (category === "visualization") return "evidence";
  if (["testing", "security"].includes(category)) return "assurance";
  return "other";
}

export function skillColor(skillId: string, category: string) {
  const family = categoryFamily(category);
  const base = CATEGORY_FAMILIES[family];
  const hash = stableHash(skillId);
  const hueShift = (hash % 9) - 4;
  const saturationShift = ((hash >>> 5) % 7) - 3;
  const lightnessShift = ((hash >>> 9) % 7) - 3;
  return {
    family,
    color: `hsl(${base.hue + hueShift}, ${base.saturation + saturationShift}%, ${base.lightness + lightnessShift}%)`,
  };
}

export function relationFlowParticleCount(
  quality: QualityProfileName,
  reducedMotion: boolean,
  relationSelected: boolean,
) {
  if (reducedMotion || !relationSelected || quality === "LOW") return 0;
  return quality === "HIGH" ? 6 : 4;
}

export function formatRelationEvidence(count: number, recencyWindow: string) {
  const recency = recencyWindow === "180d" ? "近 180 天" : recencyWindow === "90d" ? "近 90 天" : recencyWindow === "365d" ? "近 365 天" : "全部在招";
  return `${count} 个岗位一起出现 · ${recency}`;
}
