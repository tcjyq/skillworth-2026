export type ScreenRect = { left: number; top: number; right: number; bottom: number };

export type LabelCandidate = {
  id: string;
  anchor: readonly [number, number];
  width: number;
  height: number;
  priority: number;
};

export type LabelPlacement = {
  visible: boolean;
  offset: readonly [number, number];
  rect: ScreenRect;
};

export type BrowsableLabelCandidate = Omit<LabelCandidate, "priority"> & {
  score: number;
  locked?: boolean;
};

type LabelLayoutOptions = {
  width: number;
  height: number;
  maxVisible: number;
  protectedRects?: ScreenRect[];
};

const OFFSETS = [
  [0, -58], [82, -18], [-82, -18], [0, 58],
  [92, 36], [-92, 36], [128, -52], [-128, -52],
  [0, -94], [0, 94], [148, 24], [-148, 24],
] as const;

export function rectanglesOverlap(left: ScreenRect, right: ScreenRect) {
  return left.left < right.right && left.right > right.left
    && left.top < right.bottom && left.bottom > right.top;
}

function rectFor(candidate: LabelCandidate, offset: readonly [number, number]): ScreenRect {
  const centerX = candidate.anchor[0] + offset[0];
  const centerY = candidate.anchor[1] + offset[1];
  return {
    left: centerX - candidate.width / 2,
    top: centerY - candidate.height / 2,
    right: centerX + candidate.width / 2,
    bottom: centerY + candidate.height / 2,
  };
}

function withinViewport(rect: ScreenRect, width: number, height: number) {
  const margin = 8;
  return rect.left >= margin && rect.top >= margin
    && rect.right <= width - margin && rect.bottom <= height - margin;
}

export function resolveLabelPlacements(candidates: LabelCandidate[], options: LabelLayoutOptions) {
  const placements = new Map<string, LabelPlacement>();
  const occupied = [...(options.protectedRects ?? [])];
  let visibleCount = 0;

  for (const candidate of candidates.toSorted((left, right) => right.priority - left.priority || left.id.localeCompare(right.id))) {
    let placement: LabelPlacement | null = null;
    if (visibleCount < options.maxVisible) {
      for (const offset of OFFSETS) {
        const rect = rectFor(candidate, offset);
        if (!withinViewport(rect, options.width, options.height)) continue;
        if (occupied.some((item) => rectanglesOverlap(rect, item))) continue;
        placement = { visible: true, offset, rect };
        occupied.push(rect);
        visibleCount += 1;
        break;
      }
    }
    placements.set(candidate.id, placement ?? {
      visible: false,
      offset: [0, 0],
      rect: rectFor(candidate, [0, 0]),
    });
  }
  return placements;
}

export function rankBrowsableLabelCandidates(
  candidates: BrowsableLabelCandidate[],
  previousIds: ReadonlySet<string>,
  width: number,
  height: number,
) {
  const cellWidth = Math.max(width / 3, 1);
  const cellHeight = Math.max(height / 3, 1);
  const bestInCell = new Map<string, string>();
  for (const candidate of candidates.toSorted((left, right) => right.score - left.score || left.id.localeCompare(right.id))) {
    const cell = `${Math.min(2, Math.floor(candidate.anchor[0] / cellWidth))}:${Math.min(2, Math.floor(candidate.anchor[1] / cellHeight))}`;
    bestInCell.set(cell, bestInCell.get(cell) ?? candidate.id);
  }
  return candidates
    .map((candidate) => ({
      ...candidate,
      // Retaining a viable label needs roughly a 15% advantage to be displaced.
      // The small cell bonus makes the normal budget read as a field, not a ranking.
      priority: candidate.locked
        ? 10_000 + candidate.score
        : candidate.score
          + (bestInCell.get(`${Math.min(2, Math.floor(candidate.anchor[0] / cellWidth))}:${Math.min(2, Math.floor(candidate.anchor[1] / cellHeight))}`) === candidate.id ? 12 : 0)
          + (previousIds.has(candidate.id) ? candidate.score * 0.15 + 12 : 0),
    }))
    .toSorted((left, right) => right.priority - left.priority || left.id.localeCompare(right.id));
}
