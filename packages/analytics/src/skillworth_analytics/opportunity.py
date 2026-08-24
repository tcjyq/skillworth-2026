from __future__ import annotations

from datetime import date
from statistics import median
from pathlib import Path
from typing import Any, Literal

import duckdb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .analytics import _fetch_rows, _sql_text
from .confidence import ConfidenceEvidence, DataConfidenceEngine, DataConfidenceResult
from .confidence_config import DataConfidenceConfig
from .guardrails import load_metric_guardrail_config


GUARDRAIL_CONFIG_PATH = Path(__file__).resolve().parents[4] / "data/reference/metric_guardrails.v1.yml"


METHODOLOGY_VERSION = "phase9_personal_skill_opportunity_v1"


class OpportunityRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_skills: tuple[str, ...] = Field(default=(), max_length=256)
    target_role: str = Field(min_length=1, max_length=128)
    city: str | None = Field(default=None, min_length=1, max_length=64)
    experience: str | None = Field(default=None, min_length=1, max_length=64)
    match_threshold: float = Field(ge=0, le=1)

    @field_validator("current_skills")
    @classmethod
    def validate_current_skills(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not skill_id.strip() for skill_id in value):
            raise ValueError("current_skills cannot contain blank values")
        if len(set(value)) != len(value):
            raise ValueError("current_skills cannot contain duplicates")
        if any(len(skill_id) > 128 for skill_id in value):
            raise ValueError("current_skills values cannot exceed 128 characters")
        return value

    @model_validator(mode="after")
    def validate_filters(self) -> "OpportunityRequest":
        if not self.target_role.strip():
            raise ValueError("target_role cannot be blank")
        if self.city is not None and not self.city.strip():
            raise ValueError("city cannot be blank")
        if self.experience is not None and not self.experience.strip():
            raise ValueError("experience cannot be blank")
        return self


class SkillOpportunityRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    new_average_fit: float = Field(ge=0, le=1)
    new_threshold_coverage: float = Field(ge=0, le=1)
    average_fit_gain: float = Field(ge=0, le=1)
    threshold_coverage_gain: float = Field(ge=0, le=1)
    jobs_crossing_threshold: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    confidence: DataConfidenceResult


class PersonalSkillOpportunityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "no_target_jobs", "no_skill_evidence"]
    request: OpportunityRequest
    current_average_fit: float | None = Field(default=None, ge=0, le=1)
    current_threshold_coverage: float | None = Field(default=None, ge=0, le=1)
    target_job_count: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    jobs_without_extracted_skills: int = Field(ge=0)
    candidates: tuple[SkillOpportunityRecord, ...]
    confidence: DataConfidenceResult
    methodology_version: str = METHODOLOGY_VERSION


class PersonalSkillOpportunityEngine:
    """Compute personal skill-fit opportunity using set-based DuckDB queries."""

    def __init__(
        self,
        database_path: Path,
        confidence_config: DataConfidenceConfig,
    ) -> None:
        self._database_path = database_path.resolve()
        if not self._database_path.is_file():
            raise FileNotFoundError(
                f"Analytics warehouse does not exist: {self._database_path}"
            )
        self._confidence = DataConfidenceEngine(confidence_config)
        self._guardrails = load_metric_guardrail_config(GUARDRAIL_CONFIG_PATH)
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            present = {row[0] for row in connection.execute("SELECT DISTINCT source_id FROM job_source_map").fetchall()}
        finally:
            connection.close()
        self._core_source_ids = tuple(sorted(
            source_id for source_id, role in self._guardrails.source_roles.items()
            if role in {"core_market", "supplementary_market"} and source_id in present
        ))

    def analyze(
        self,
        request: OpportunityRequest,
        *,
        as_of_date: date | None = None,
    ) -> PersonalSkillOpportunityResult:
        evaluation_date = as_of_date or date.today()
        target_jobs, filter_parameters = _target_jobs(request, self._core_source_ids)
        current_skills = list(request.current_skills)
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            opportunity_rows = _fetch_rows(
                connection,
                _sql_text("opportunity.sql").format(target_jobs=target_jobs),
                filter_parameters + [current_skills, request.match_threshold],
            )
            source_rows = _fetch_rows(
                connection,
                _sql_text("opportunity_confidence.sql").format(
                    target_jobs=target_jobs
                ),
                filter_parameters + [current_skills],
            )
            posting_rows = _fetch_rows(
                connection,
                f"SELECT published_at FROM ({target_jobs}) WHERE published_at IS NOT NULL",
                filter_parameters,
            )
        finally:
            connection.close()

        baseline = opportunity_rows[0]
        source_sample_sizes, baseline_platform_values, candidate_platform_values = (
            _confidence_evidence_by_source(source_rows)
        )
        posting_ages = sorted(max(0, (evaluation_date - row["published_at"]).days) for row in posting_rows)
        p75_age = posting_ages[min(len(posting_ages) - 1, int(0.75 * (len(posting_ages) - 1)))] if posting_ages else None
        median_age = float(median(posting_ages)) if posting_ages else None
        source_eligibility = {
            source: self._source_is_eligible(source, count, evaluation_date, baseline["latest_posted_date"])
            for source, count in source_sample_sizes.items()
        }
        freshness_evidence = {
            "latest_posted_date": baseline["latest_posted_date"],
            "median_posting_age_days": median_age,
            "p75_posting_age_days": p75_age,
            "posting_date_coverage": baseline["posting_date_coverage"] or 0,
            "source_eligibility": source_eligibility,
        }
        cohort_confidence = self._confidence.evaluate(
            ConfidenceEvidence(
                sample_size=baseline["sample_size"],
                source_sample_sizes=source_sample_sizes,
                **freshness_evidence,
                as_of_date=evaluation_date,
                platform_metric_values=baseline_platform_values,
            )
        )
        candidates = tuple(
            SkillOpportunityRecord(
                skill_id=row["skill_id"],
                canonical_name=row["canonical_name"],
                category=row["category"],
                new_average_fit=row["new_average_fit"],
                new_threshold_coverage=row["new_threshold_coverage"],
                average_fit_gain=row["average_fit_gain"],
                threshold_coverage_gain=row["threshold_coverage_gain"],
                jobs_crossing_threshold=row["jobs_crossing_threshold"],
                sample_size=baseline["sample_size"],
                confidence=self._confidence.evaluate(
                    ConfidenceEvidence(
                        sample_size=baseline["sample_size"],
                        source_sample_sizes=source_sample_sizes,
                        **freshness_evidence,
                        as_of_date=evaluation_date,
                        platform_metric_values=candidate_platform_values.get(
                            row["skill_id"], {}
                        ),
                    )
                ),
            )
            for row in opportunity_rows
            if row["skill_id"] is not None
        )
        status: Literal["ok", "no_target_jobs", "no_skill_evidence"]
        if baseline["target_job_count"] == 0:
            status = "no_target_jobs"
        elif baseline["sample_size"] == 0:
            status = "no_skill_evidence"
        else:
            status = "ok"
        return PersonalSkillOpportunityResult(
            status=status,
            request=request,
            current_average_fit=baseline["current_average_fit"],
            current_threshold_coverage=baseline["current_threshold_coverage"],
            target_job_count=baseline["target_job_count"],
            sample_size=baseline["sample_size"],
            jobs_without_extracted_skills=baseline["jobs_without_extracted_skills"],
            candidates=candidates,
            confidence=cohort_confidence,
        )

    def _source_is_eligible(self, source_id: str, count: int, as_of: date, latest_posted: date | None) -> bool:
        config = self._guardrails.eligibility
        role = self._guardrails.source_role(source_id)
        age = max(0, (as_of - latest_posted).days) if latest_posted else None
        return (
            role in {"core_market", "supplementary_market"}
            and count >= config.minimum_target_sample_size
            and (config.maximum_market_age_days is None or (age is not None and age <= config.maximum_market_age_days))
        )


def _target_jobs(request: OpportunityRequest, core_source_ids: tuple[str, ...] = ()) -> tuple[str, list[object]]:
    predicates = ["jobs.role_id = ?"]
    parameters: list[object] = [request.target_role]
    if core_source_ids:
        placeholders = ", ".join("?" for _ in core_source_ids)
        predicates.append(
            "EXISTS (SELECT 1 FROM job_source_map scope_map WHERE "
            "scope_map.canonical_job_id = jobs.canonical_job_id AND "
            f"scope_map.source_id IN ({placeholders}))"
        )
        parameters.extend(core_source_ids)
    if request.city is not None:
        predicates.append("jobs.city_code = ?")
        parameters.append(request.city)
    if request.experience is not None:
        predicates.append("jobs.experience_band = ?")
        parameters.append(request.experience)
    return (
        "SELECT jobs.canonical_job_id, jobs.published_at FROM jobs WHERE "
        + " AND ".join(predicates),
        parameters,
    )


def _confidence_evidence_by_source(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, int], dict[str, float], dict[str, dict[str, float]]]:
    source_sample_sizes: dict[str, int] = {}
    baseline_values: dict[str, float] = {}
    candidate_values: dict[str, dict[str, float]] = {}
    for row in rows:
        source_id = row["source_id"]
        source_sample_sizes[source_id] = row["source_sample_size"]
        baseline_values[source_id] = row["current_average_fit"]
        if row["skill_id"] is not None:
            candidate_values.setdefault(row["skill_id"], {})[source_id] = row[
                "candidate_average_fit_gain"
            ]
    return source_sample_sizes, baseline_values, candidate_values
