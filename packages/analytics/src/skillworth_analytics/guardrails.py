from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


SourceAnalysisRole = Literal[
    "core_market",
    "core_market_candidate",
    "supplementary_market",
    "engineering_validation",
    "historical_reference",
    "external_market_benchmark",
]


class SourceEligibilityConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_target_sample_size: int = Field(ge=1)
    minimum_target_market_ratio: float | None = Field(default=None, ge=0, le=1)
    minimum_skill_extraction_coverage: float = Field(ge=0, le=1)
    maximum_market_age_days: int | None = Field(default=None, ge=1)
    minimum_agreement_sample_size: int = Field(ge=1)
    required_eligible_sources: int = Field(default=2, ge=2)


class MetricGuardrailConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    source_roles: dict[str, SourceAnalysisRole]
    eligibility: SourceEligibilityConfig

    def source_role(self, source_id: str) -> SourceAnalysisRole | None:
        return self.source_roles.get(source_id)

    def excluded_from_core(self) -> tuple[str, ...]:
        return tuple(
            source_id
            for source_id, role in self.source_roles.items()
            if role in {
                "core_market_candidate", "engineering_validation", "historical_reference",
                "external_market_benchmark",
            }
        )


class SourceEligibilityEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_role: SourceAnalysisRole | None
    target_sample_size: int = Field(ge=0)
    target_market_ratio: float | None = Field(default=None, ge=0, le=1)
    skill_extraction_coverage: float | None = Field(default=None, ge=0, le=1)
    latest_posted_at: date | None = None
    market_age_days: int | None = Field(default=None, ge=0)
    eligible: bool
    reasons: tuple[str, ...]


def load_metric_guardrail_config(path: Path) -> MetricGuardrailConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MetricGuardrailConfig.model_validate(payload)


def evaluate_source_eligibility(
    *,
    source_id: str,
    source_role: SourceAnalysisRole | None,
    target_sample_size: int,
    all_sample_size: int,
    skilled_target_sample_size: int,
    latest_posted_at: date | None,
    as_of_date: date,
    config: SourceEligibilityConfig,
) -> SourceEligibilityEvidence:
    reasons: list[str] = []
    target_ratio = target_sample_size / all_sample_size if all_sample_size else None
    skill_coverage = (
        skilled_target_sample_size / target_sample_size if target_sample_size else None
    )
    market_age = (
        max(0, (as_of_date - latest_posted_at).days)
        if latest_posted_at is not None
        else None
    )
    if source_role not in {"core_market", "supplementary_market"}:
        reasons.append("SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE")
    if target_sample_size < config.minimum_target_sample_size:
        reasons.append("TARGET_SAMPLE_SIZE_BELOW_MINIMUM")
    if (
        config.minimum_target_market_ratio is not None
        and (target_ratio is None or target_ratio < config.minimum_target_market_ratio)
    ):
        reasons.append("TARGET_MARKET_RATIO_BELOW_MINIMUM")
    if skill_coverage is None or skill_coverage < config.minimum_skill_extraction_coverage:
        reasons.append("SKILL_EXTRACTION_COVERAGE_BELOW_MINIMUM")
    if config.maximum_market_age_days is not None and (
        market_age is None or market_age > config.maximum_market_age_days
    ):
        reasons.append("MARKET_DATA_TOO_OLD")
    return SourceEligibilityEvidence(
        source_id=source_id,
        source_role=source_role,
        target_sample_size=target_sample_size,
        target_market_ratio=target_ratio,
        skill_extraction_coverage=skill_coverage,
        latest_posted_at=latest_posted_at,
        market_age_days=market_age,
        eligible=not reasons,
        reasons=tuple(reasons),
    )
