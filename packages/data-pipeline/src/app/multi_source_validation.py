from __future__ import annotations

from math import log2
from statistics import pstdev
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field


class CompositionDifferenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    divergence: float = Field(ge=0, le=1)
    sample_sizes: dict[str, int]
    eligibility: dict[str, bool]
    warning: str | None


def jensen_shannon_divergence(
    left: Mapping[str, float], right: Mapping[str, float]
) -> float:
    """Base-2 JSD in [0, 1] over the union of transparent category shares."""
    keys = sorted(set(left) | set(right))
    left_total = sum(max(0.0, float(left.get(key, 0.0))) for key in keys)
    right_total = sum(max(0.0, float(right.get(key, 0.0))) for key in keys)
    if left_total <= 0 or right_total <= 0:
        return 1.0 if left_total != right_total else 0.0
    p = [max(0.0, float(left.get(key, 0.0))) / left_total for key in keys]
    q = [max(0.0, float(right.get(key, 0.0))) / right_total for key in keys]
    m = [(a + b) / 2 for a, b in zip(p, q, strict=True)]

    def kl(values: list[float], midpoint: list[float]) -> float:
        return sum(value * log2(value / middle) for value, middle in zip(values, midpoint, strict=True) if value)

    return round((kl(p, m) + kl(q, m)) / 2, 12)


def guarded_jensen_shannon_divergence(
    left: Mapping[str, float],
    right: Mapping[str, float],
    *,
    left_source_id: str,
    right_source_id: str,
    left_eligible: bool,
    right_eligible: bool,
) -> CompositionDifferenceResult:
    return CompositionDifferenceResult(
        divergence=jensen_shannon_divergence(left, right),
        sample_sizes={
            left_source_id: int(sum(left.values())),
            right_source_id: int(sum(right.values())),
        },
        eligibility={left_source_id: left_eligible, right_source_id: right_eligible},
        warning=None if left_eligible and right_eligible else "INSUFFICIENT_COMPARABLE_SOURCES",
    )


def agreement_status(cross_source_variance: float) -> str:
    """Classify the population variance of source coverage values."""
    if cross_source_variance <= 0.0025:
        return "High Agreement"
    if cross_source_variance <= 0.0225:
        return "Medium Agreement"
    return "Low Agreement"


def coverage_variance(values: Mapping[str, float]) -> float | None:
    return None if len(values) < 2 else round(pstdev(values.values()) ** 2, 12)


def rank_changes(
    *, pooled: Mapping[str, float], balanced: Mapping[str, float]
) -> list[dict[str, int | float | str]]:
    skills = sorted(set(pooled) | set(balanced))
    pooled_order = sorted(skills, key=lambda skill: (-float(pooled.get(skill, 0.0)), skill))
    balanced_order = sorted(skills, key=lambda skill: (-float(balanced.get(skill, 0.0)), skill))
    pooled_rank = {skill: index + 1 for index, skill in enumerate(pooled_order)}
    balanced_rank = {skill: index + 1 for index, skill in enumerate(balanced_order)}
    rows = [
        {
            "skill_id": skill,
            "pooled_rank": pooled_rank[skill],
            "balanced_rank": balanced_rank[skill],
            "rank_change": pooled_rank[skill] - balanced_rank[skill],
            "absolute_rank_change": abs(pooled_rank[skill] - balanced_rank[skill]),
        }
        for skill in skills
    ]
    return sorted(rows, key=lambda row: (-int(row["absolute_rank_change"]), str(row["skill_id"])))
