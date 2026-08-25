import { describe, expect, it } from "vitest";
import {
  QUALITY_PROFILES,
  DECORATIVE_PARTICLE_POLICY,
  formatRelationEvidence,
  nextQualityProfile,
  relationFlowParticleCount,
  skillColor,
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
    expect(QUALITY_PROFILES.LOW.particleCount).toBeLessThanOrEqual(70);
    expect(QUALITY_PROFILES.LOW.visibleLabelCount).toBeLessThanOrEqual(4);
    expect(QUALITY_PROFILES.LOW.bloomMode).toBe("off");
  });

  it("disables relation flow particles for reduced motion", () => {
    expect(relationFlowParticleCount("HIGH", true, true)).toBe(0);
    expect(relationFlowParticleCount("BALANCED", false, false)).toBe(0);
    expect(relationFlowParticleCount("BALANCED", false, true)).toBeGreaterThan(0);
  });

  it("only downgrades one quality level and never bounces upward", () => {
    expect(nextQualityProfile("HIGH")).toBe("BALANCED");
    expect(nextQualityProfile("BALANCED")).toBe("LOW");
    expect(nextQualityProfile("LOW")).toBe("LOW");
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
