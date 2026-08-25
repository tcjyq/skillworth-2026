import { describe, expect, it } from "vitest";
import { rectanglesOverlap, resolveLabelPlacements } from "./label-layout";

const candidates = [
  { id: "selected", anchor: [500, 300] as const, width: 92, height: 34, priority: 600 },
  { id: "cpp", anchor: [505, 302] as const, width: 96, height: 34, priority: 500 },
  { id: "python", anchor: [510, 304] as const, width: 88, height: 30, priority: 300 },
  { id: "sql", anchor: [512, 306] as const, width: 76, height: 30, priority: 290 },
  { id: "git", anchor: [514, 308] as const, width: 72, height: 30, priority: 280 },
  { id: "hover", anchor: [516, 310] as const, width: 80, height: 30, priority: 200 },
];

describe("screen-space label avoidance", () => {
  it("is deterministic for the same state and camera projection", () => {
    expect(resolveLabelPlacements(candidates, { width: 1000, height: 640, maxVisible: 5 }))
      .toEqual(resolveLabelPlacements(candidates, { width: 1000, height: 640, maxVisible: 5 }));
  });

  it("keeps higher-priority labels and resolves visible overlaps", () => {
    const placements = resolveLabelPlacements(candidates, { width: 1000, height: 640, maxVisible: 5 });
    expect(placements.get("selected")?.visible).toBe(true);
    expect(placements.get("hover")?.visible).toBe(false);
    const visible = [...placements.values()].filter((item) => item.visible);
    for (let left = 0; left < visible.length; left += 1) {
      for (let right = left + 1; right < visible.length; right += 1) {
        expect(rectanglesOverlap(visible[left].rect, visible[right].rect)).toBe(false);
      }
    }
  });

  it("never places a default label over the protected value-core copy", () => {
    const protectedRect = { left: 450, top: 270, right: 610, bottom: 350 };
    const placements = resolveLabelPlacements(candidates, { width: 1000, height: 640, maxVisible: 5, protectedRects: [protectedRect] });
    for (const placement of [...placements.values()].filter((item) => item.visible)) {
      expect(rectanglesOverlap(placement.rect, protectedRect)).toBe(false);
    }
  });
});
