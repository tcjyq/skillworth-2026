import { describe, expect, it } from "vitest";
import {
  QUALITY_PROFILES,
  ATMOSPHERE_VARIANTS,
  resolveAtmosphereVariant,
  DECORATIVE_PARTICLE_POLICY,
  atmosphereParticleCount,
  formatRelationEvidence,
  nextQualityProfile,
  relationFlowParticleCount,
  skillStarMotion,
  skillColor,
  starPointerShouldSelect,
  SKILL_STAR_MATERIAL,
} from "./visual-system";

describe("semantic skill color system", () => {
  it("keeps the same skill on the same deterministic category tint", () => {
    expect(skillColor("programming_python", "programming")).toEqual(
      skillColor("programming_python", "programming"),
    );
    expect(skillColor("programming_python", "programming").color).not.toBe(skillColor("programming_cpp", "programming").color);
  });

  it("uses a limited category family instead of a random color per skill", () => {
    const categories = [
      "programming", "database", "data_analysis", "data_engineering", "ai_ml",
      "frontend", "backend", "devops", "cloud", "visualization", "testing", "other",
    ];
    const hues = new Set(categories.map((category) => skillColor(`${category}_example`, category).family));
    expect(hues.size).toBeLessThanOrEqual(8);
  });

  it("does not accept score, confidence, robustness, or demand as hue inputs", () => {
    const lowEvidence = skillColor("programming_python", "programming");
    const highEvidence = skillColor("programming_python", "programming");
    expect(lowEvidence).toEqual(highEvidence);
  });
});

describe("adaptive rendering profiles", () => {
  it("keeps data-bearing nodes and layout enabled in every profile", () => {
    for (const profile of Object.values(QUALITY_PROFILES)) {
      expect(profile.renderDataNodes).toBe(true);
      expect(profile.preserveLayout).toBe(true);
    }
  });

  it("uses conservative mobile and low-quality budgets", () => {
    expect(QUALITY_PROFILES.HIGH.particleCount).toBe(380);
    expect(QUALITY_PROFILES.BALANCED.particleCount).toBe(260);
    expect(QUALITY_PROFILES.LOW.particleCount).toBe(130);
    expect(QUALITY_PROFILES.HIGH.visibleLabelCount).toBeGreaterThanOrEqual(7);
    expect(QUALITY_PROFILES.HIGH.visibleLabelCount).toBeLessThanOrEqual(9);
    expect(QUALITY_PROFILES.LOW.visibleLabelCount).toBeGreaterThanOrEqual(4);
    expect(QUALITY_PROFILES.LOW.visibleLabelCount).toBeLessThanOrEqual(5);
    expect(QUALITY_PROFILES.LOW.bloomMode).toBe("off");
    expect(QUALITY_PROFILES.HIGH.ambientCadenceFps).toBeGreaterThanOrEqual(8);
    expect(QUALITY_PROFILES.HIGH.ambientCadenceFps).toBeLessThanOrEqual(15);
    expect(QUALITY_PROFILES.LOW.ambientCadenceFps).toBeGreaterThan(0);
    expect(QUALITY_PROFILES.LOW.ambientCadenceFps).toBeLessThanOrEqual(4);
  });

  it("keeps relation evidence non-directional without moving particles", () => {
    expect(relationFlowParticleCount("HIGH", true, true)).toBe(0);
    expect(relationFlowParticleCount("BALANCED", false, false)).toBe(0);
    expect(relationFlowParticleCount("BALANCED", false, true)).toBe(0);
  });

  it("only downgrades one quality level and never bounces upward", () => {
    expect(nextQualityProfile("HIGH")).toBe("BALANCED");
    expect(nextQualityProfile("BALANCED")).toBe("LOW");
    expect(nextQualityProfile("LOW")).toBe("LOW");
  });
});

describe("data versus atmosphere separation", () => {
  it("keeps the review alternatives bounded and makes option B materially quieter", () => {
    expect(atmosphereParticleCount("HIGH", "A")).toBe(720);
    expect(atmosphereParticleCount("LOW", "A")).toBe(220);
    expect(atmosphereParticleCount("HIGH", "B")).toBe(380);
    expect(atmosphereParticleCount("LOW", "B")).toBe(130);
    expect(ATMOSPHERE_VARIANTS.B.particleCounts.HIGH).toBeLessThan(ATMOSPHERE_VARIANTS.A.particleCounts.HIGH);
  });

  it("uses B by default and retains A only as an explicit Lab URL override", () => {
    expect(resolveAtmosphereVariant()).toBe("B");
    expect(resolveAtmosphereVariant("A")).toBe("A");
  });
});

describe("star material and motion", () => {
  it("freezes the accepted Soft Point Star material", () => {
    expect(SKILL_STAR_MATERIAL.label).toBe("A · Soft Point Star");
  });

  it("derives deterministic unsynchronised breathing from skill id", () => {
    expect(skillStarMotion("programming_python")).toEqual(skillStarMotion("programming_python"));
    expect(skillStarMotion("programming_python").phase).not.toBe(skillStarMotion("database_sql").phase);
    expect(skillStarMotion("programming_python").amplitude).toBeLessThanOrEqual(0.12);
  });

  it("does not turn a camera drag across a star into a skill click", () => {
    expect(starPointerShouldSelect(2)).toBe(true);
    expect(starPointerShouldSelect(18)).toBe(false);
  });
});

describe("relation evidence presentation", () => {
  it("includes the recency scope next to the evidence count", () => {
    expect(formatRelationEvidence(128, "180d")).toBe("128 个岗位一起出现 · 近 180 天");
  });
});

describe("decorative particle semantics", () => {
  it("never makes atmospheric particles pickable", () => {
    expect(DECORATIVE_PARTICLE_POLICY.pickable).toBe(false);
  });

  it("never counts atmospheric particles as skill nodes", () => {
    expect(DECORATIVE_PARTICLE_POLICY.countsAsSkillNode).toBe(false);
  });
});
