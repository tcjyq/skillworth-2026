export type FrontierPoint = {
  learning_hours_expected: number;
  market_signal: number;
};

export function paretoFrontier<T extends FrontierPoint>(points: T[]): T[] {
  return points
    .filter(
      (point) =>
        !points.some(
          (candidate) =>
            candidate !== point &&
            candidate.learning_hours_expected <= point.learning_hours_expected &&
            candidate.market_signal >= point.market_signal &&
            (candidate.learning_hours_expected < point.learning_hours_expected ||
              candidate.market_signal > point.market_signal),
        ),
    )
    .sort(
      (left, right) =>
        left.learning_hours_expected - right.learning_hours_expected ||
        right.market_signal - left.market_signal,
    );
}
