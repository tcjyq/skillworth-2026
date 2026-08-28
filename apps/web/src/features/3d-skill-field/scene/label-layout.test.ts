import { describe, expect, it } from "vitest";
import { rankBrowsableLabelCandidates, rectanglesOverlap, resolveLabelPlacements } from "./label-layout";

const candidates = [
  { id: "selected", anchor: [500, 300] as const, width: 92, height: 34, priority: 600 },
  { id: "cpp", anchor: [505, 302] as const, width: 96, height: 34, priority: 500 },
  { id: "python", anchor: [510, 304] as const, width: 88, height: 30, priority: 300 },
  { id: "sql", anchor: [512, 306] as const, width: 76, height: 30, priority: 290 },
  { id: "git", anchor: [514, 308] as const, width: 72, height: 30, priority: 280 },
  { id: "hover", anchor: [516, 310] as const, width: 80, height: 30, priority: 200 },
];

describe("screen-space label avoidance", () => {
  it("keeps the browsing order deterministic while distributing initial picks across screen cells", () => {
    const browsing = [
      { id: "north-west", anchor: [160, 120] as const, width: 80, height: 30, score: 80 },
      { id: "north-east", anchor: [840, 120] as const, width: 80, height: 30, score: 79 },
      { id: "south-west", anchor: [160, 520] as const, width: 80, height: 30, score: 78 },
      { id: "south-east", anchor: [840, 520] as const, width: 80, height: 30, score: 77 },
    ];
    const first = rankBrowsableLabelCandidates(browsing, new Set(), 1000, 640);
    expect(first).toEqual(rankBrowsableLabelCandidates(browsing, new Set(), 1000, 640));
    expect(new Set(first.slice(0, 4).map((item) => item.id))).toEqual(new Set(browsing.map((item) => item.id)));
  });

  it("gives a safe existing label a modest hysteresis advantage without locking the candidate pool", () => {
    const browsing = [
      { id: "existing", anchor: [200, 180] as const, width: 80, height: 30, score: 80 },
      { id: "new", anchor: [210, 180] as const, width: 80, height: 30, score: 90 },
    ];
    expect(rankBrowsableLabelCandidates(browsing, new Set(["existing"]), 1000, 640)[0]?.id).toBe("existing");
    expect(rankBrowsableLabelCandidates([{ ...browsing[0], score: 70 }, browsing[1]], new Set(["existing"]), 1000, 640)[0]?.id).toBe("new");
  });

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
