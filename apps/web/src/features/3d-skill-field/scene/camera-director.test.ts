import { describe, expect, it } from "vitest";
import type { SceneMode } from "../state/scene-machine";
import { cameraPresetFor } from "./camera-director";

describe("scene-specific default camera", () => {
  it("defines a stable, distinct preset for all five scene states", () => {
    const modes: SceneMode[] = ["GLOBAL_VALUE", "GLOBAL_DEMAND", "ROLE_VALUE", "RELATION_GLOBAL", "RELATION_ROLE"];
    const presets = modes.map((mode) => cameraPresetFor(mode));
    expect(new Set(presets.map((preset) => preset.position.join(","))).size).toBe(5);
    expect(modes.map((mode) => cameraPresetFor(mode))).toEqual(presets);
  });

  it("uses a closer relation view than the global ranking field", () => {
    const global = cameraPresetFor("GLOBAL_VALUE");
    const relation = cameraPresetFor("RELATION_GLOBAL");
    expect(Math.hypot(...relation.position)).toBeLessThan(Math.hypot(...global.position));
  });
});
