import { describe, expect, it } from "vitest";
import type { SceneMode } from "../state/scene-machine";
import { CAMERA_LIMITS, cameraPresetFor, idleRotationEnabled } from "./camera-director";

describe("scene-specific default camera", () => {
  it("defines a stable, distinct preset for all five scene states", () => {
    const modes: SceneMode[] = ["GLOBAL_VALUE", "GLOBAL_DEMAND", "ROLE_VALUE", "RELATION_GLOBAL", "RELATION_ROLE"];
    const presets = modes.map((mode) => cameraPresetFor(mode));
    expect(new Set(presets.map((preset) => preset.position.join(","))).size).toBe(5);
    expect(modes.map((mode) => cameraPresetFor(mode))).toEqual(presets);
  });

  it("uses a closer global value framing while retaining the full exploration range", () => {
    const global = cameraPresetFor("GLOBAL_VALUE");
    expect(Math.hypot(...global.position)).toBeLessThan(22);
    expect(CAMERA_LIMITS.maxDistance).toBe(34);
  });
});

describe("starfield camera interaction", () => {
  it("allows unlimited horizontal orbit while keeping a bounded vertical view", () => {
    expect(CAMERA_LIMITS.minAzimuthAngle).toBe(-Infinity);
    expect(CAMERA_LIMITS.maxAzimuthAngle).toBe(Infinity);
    expect(CAMERA_LIMITS.minPolarAngle).toBeGreaterThan(0);
    expect(CAMERA_LIMITS.maxPolarAngle).toBeLessThan(Math.PI);
  });

  it("only enables idle rotation for desktop high quality without reduced motion", () => {
    expect(idleRotationEnabled("HIGH", false, false)).toBe(true);
    expect(idleRotationEnabled("BALANCED", false, false)).toBe(false);
    expect(idleRotationEnabled("HIGH", true, false)).toBe(false);
    expect(idleRotationEnabled("HIGH", false, true)).toBe(false);
  });
});
