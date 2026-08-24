from __future__ import annotations

from pathlib import Path
from statistics import correlation
from typing import Iterable

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from app.skill_taxonomy import load_skill_taxonomy


class ExternalSkillComparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_skill: str
    internal_demand_rank: int = Field(ge=1)
    external_benchmark_rank: int = Field(ge=1)
    rank_difference: int
    internal_coverage: float = Field(ge=0, le=1)
    external_coverage: float = Field(ge=0, le=1)
    divergence_warning: bool


class QareraBenchmarkReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str = "qarera_skills_2026"
    source_role: str = "external_market_benchmark"
    external_row_count: int = Field(ge=0)
    mapped_external_skill_count: int = Field(ge=0)
    overlap_skill_count: int = Field(ge=0)
    rank_correlation: float | None = Field(default=None, ge=-1, le=1)
    agreement_status: str
    comparisons: tuple[ExternalSkillComparison, ...]
    limitations: tuple[str, ...]


def compare_qarera_benchmark(
    *,
    internal_skill_demand: Iterable[dict[str, object]],
    qarera_overall_path: Path,
    taxonomy_path: Path,
    divergence_rank_threshold: int = 20,
) -> QareraBenchmarkReport:
    """Compare ranks only; Qarera aggregates never enter SkillWorth denominators."""
    external = pl.read_csv(qarera_overall_path)
    required = {"skill", "pct_of_all_postings"}
    missing = required - set(external.columns)
    if missing:
        raise ValueError(f"Qarera benchmark is missing columns: {sorted(missing)}")
    taxonomy = load_skill_taxonomy(taxonomy_path)
    mapped: list[dict[str, object]] = []
    for source_rank, row in enumerate(external.iter_rows(named=True), start=1):
        raw_skill = str(row["skill"]).strip()
        definition = taxonomy.alias_index.get(raw_skill.casefold())
        if definition is None:
            continue
        mapped.append(
            {
                "skill_id": definition.skill_id,
                "canonical_skill": definition.canonical_name,
                "external_rank": source_rank,
                "external_coverage": float(row["pct_of_all_postings"]) / 100,
            }
        )
    external_by_id = {str(row["skill_id"]): row for row in mapped}
    ordered_internal = sorted(
        internal_skill_demand,
        key=lambda row: (-float(row.get("job_coverage") or 0), str(row.get("skill_id") or "")),
    )
    comparisons: list[ExternalSkillComparison] = []
    for internal_rank, row in enumerate(ordered_internal, start=1):
        external_row = external_by_id.get(str(row.get("skill_id")))
        if external_row is None:
            continue
        difference = internal_rank - int(external_row["external_rank"])
        comparisons.append(
            ExternalSkillComparison(
                skill_id=str(row["skill_id"]),
                canonical_skill=str(external_row["canonical_skill"]),
                internal_demand_rank=internal_rank,
                external_benchmark_rank=int(external_row["external_rank"]),
                rank_difference=difference,
                internal_coverage=float(row.get("job_coverage") or 0),
                external_coverage=float(external_row["external_coverage"]),
                divergence_warning=abs(difference) >= divergence_rank_threshold,
            )
        )
    coefficient = None
    if len(comparisons) >= 2:
        coefficient = correlation(
            [item.internal_demand_rank for item in comparisons],
            [item.external_benchmark_rank for item in comparisons],
        )
    if coefficient is None:
        status = "INSUFFICIENT_OVERLAP"
    elif coefficient >= 0.70:
        status = "HIGH_AGREEMENT"
    elif coefficient >= 0.40:
        status = "MEDIUM_AGREEMENT"
    else:
        status = "LOW_AGREEMENT"
    return QareraBenchmarkReport(
        external_row_count=external.height,
        mapped_external_skill_count=len(external_by_id),
        overlap_skill_count=len(comparisons),
        rank_correlation=coefficient,
        agreement_status=status,
        comparisons=tuple(comparisons),
        limitations=(
            "Qarera is an external aggregate with a different collection frame and denominator.",
            "Agreement is descriptive cross-dataset rank comparison, not validation of representativeness.",
            "Qarera rows are not imported into SkillWorth jobs or demand denominators.",
        ),
    )
