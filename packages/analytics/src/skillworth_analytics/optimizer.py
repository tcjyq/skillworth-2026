from __future__ import annotations

from datetime import date
from math import isfinite
from pathlib import Path
from typing import Literal

import duckdb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .analytics import _fetch_rows
from .confidence_config import DataConfidenceConfig
from .decision import LearningHoursEstimate, LearningHoursReport
from .decision_config import DecisionScoreConfig
from .opportunity import (
    OpportunityRequest,
    PersonalSkillOpportunityEngine,
    SkillOpportunityRecord,
)


METHODOLOGY_VERSION = "phase10_iterative_greedy_optimizer_v1"


class LearningOptimizerRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_skills: tuple[str, ...] = Field(default=(), max_length=256)
    target_role: str = Field(min_length=1, max_length=128)
    hour_budget: float = Field(gt=0)
    city: str | None = Field(default=None, min_length=1, max_length=64)
    experience: str | None = Field(default=None, min_length=1, max_length=64)
    match_threshold: float | None = Field(default=None, ge=0, le=1)
    learning_hours_overrides: dict[str, float] = Field(default_factory=dict, max_length=256)

    @field_validator("hour_budget")
    @classmethod
    def validate_hour_budget(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("hour_budget must be finite")
        return value

    @field_validator("current_skills")
    @classmethod
    def validate_current_skills(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not skill_id.strip() for skill_id in value):
            raise ValueError("current_skills cannot contain blank values")
        if len(value) != len(set(value)):
            raise ValueError("current_skills cannot contain duplicates")
        if any(len(skill_id) > 128 for skill_id in value):
            raise ValueError("current_skills values cannot exceed 128 characters")
        return value

    @field_validator("learning_hours_overrides")
    @classmethod
    def validate_overrides(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not skill_id.strip() for skill_id in value):
            raise ValueError("learning_hours_overrides keys cannot be blank")
        if any(len(skill_id) > 128 for skill_id in value):
            raise ValueError("learning_hours_overrides keys cannot exceed 128 characters")
        if any(not isfinite(hours) or hours <= 0 for hours in value.values()):
            raise ValueError("learning_hours_overrides values must be positive and finite")
        return value

    @model_validator(mode="after")
    def validate_filters(self) -> "LearningOptimizerRequest":
        if not self.target_role.strip():
            raise ValueError("target_role cannot be blank")
        if self.city is not None and not self.city.strip():
            raise ValueError("city cannot be blank")
        if self.experience is not None and not self.experience.strip():
            raise ValueError("experience cannot be blank")
        return self


class LearningOptimizerStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step: int = Field(ge=1)
    skill_id: str
    canonical_name: str
    category: str
    estimated_hours: float = Field(gt=0)
    cumulative_hours: float = Field(gt=0)
    marginal_fit_gain: float = Field(ge=0, le=1)
    cumulative_fit: float = Field(ge=0, le=1)
    threshold_coverage: float = Field(ge=0, le=1)
    reason: str
    learning_hours: LearningHoursReport


class LearningOptimizerResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["ok", "no_target_jobs", "no_skill_evidence"]
    strategy: Literal["iterative_greedy_marginal_gain"]
    beam_search_used: bool = False
    hour_budget: float = Field(gt=0)
    cumulative_hours: float = Field(ge=0)
    remaining_hours: float = Field(ge=0)
    initial_fit: float | None = Field(default=None, ge=0, le=1)
    final_fit: float | None = Field(default=None, ge=0, le=1)
    final_threshold_coverage: float | None = Field(default=None, ge=0, le=1)
    steps: tuple[LearningOptimizerStep, ...]
    warnings: tuple[str, ...]
    methodology_version: str = METHODOLOGY_VERSION
    config_version: str


class LearningOptimizer:
    def __init__(
        self,
        database_path: Path,
        *,
        decision_config: DecisionScoreConfig,
        confidence_config: DataConfidenceConfig,
    ) -> None:
        self._database_path = database_path.resolve()
        if not self._database_path.is_file():
            raise FileNotFoundError(
                f"Analytics warehouse does not exist: {self._database_path}"
            )
        self.config = decision_config
        self._opportunity = PersonalSkillOpportunityEngine(
            self._database_path, confidence_config
        )

    def optimize(
        self,
        request: LearningOptimizerRequest,
        *,
        as_of_date: date | None = None,
    ) -> LearningOptimizerResult:
        evaluation_date = as_of_date or date.today()
        threshold = (
            request.match_threshold
            if request.match_threshold is not None
            else self.config.optimizer.default_match_threshold
        )
        estimates = self._learning_hours_catalog()
        current_skills = list(request.current_skills)
        opportunity = self._opportunity.analyze(
            OpportunityRequest(
                current_skills=tuple(current_skills),
                target_role=request.target_role,
                city=request.city,
                experience=request.experience,
                match_threshold=threshold,
            ),
            as_of_date=evaluation_date,
        )
        initial_fit = opportunity.current_average_fit
        cumulative_hours = 0.0
        steps: list[LearningOptimizerStep] = []
        warnings: set[str] = set()

        while opportunity.status == "ok":
            remaining_hours = request.hour_budget - cumulative_hours
            ranked: list[
                tuple[
                    float,
                    float,
                    str,
                    SkillOpportunityRecord,
                    LearningHoursEstimate,
                    float,
                ]
            ] = []
            for candidate in opportunity.candidates:
                estimate = estimates.get(candidate.skill_id)
                if estimate is None:
                    warnings.add(f"learning_hours_unavailable:{candidate.skill_id}")
                    continue
                effective_hours = request.learning_hours_overrides.get(
                    candidate.skill_id, estimate.learning_hours_expected
                )
                if effective_hours > remaining_hours + 1e-9:
                    continue
                marginal_gain = (
                    self.config.optimizer.average_fit_gain_weight
                    * candidate.average_fit_gain
                    + self.config.optimizer.threshold_coverage_gain_weight
                    * candidate.threshold_coverage_gain
                )
                if marginal_gain < self.config.optimizer.minimum_marginal_gain:
                    continue
                gain_per_hour = marginal_gain / effective_hours
                ranked.append(
                    (
                        gain_per_hour,
                        marginal_gain,
                        candidate.skill_id,
                        candidate,
                        estimate,
                        effective_hours,
                    )
                )
            if not ranked:
                break

            ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
            gain_per_hour, marginal_gain, skill_id, candidate, estimate, hours = ranked[0]
            current_skills.append(skill_id)
            cumulative_hours += hours
            opportunity = self._opportunity.analyze(
                OpportunityRequest(
                    current_skills=tuple(current_skills),
                    target_role=request.target_role,
                    city=request.city,
                    experience=request.experience,
                    match_threshold=threshold,
                ),
                as_of_date=evaluation_date,
            )
            steps.append(
                LearningOptimizerStep(
                    step=len(steps) + 1,
                    skill_id=skill_id,
                    canonical_name=candidate.canonical_name,
                    category=candidate.category,
                    estimated_hours=hours,
                    cumulative_hours=cumulative_hours,
                    marginal_fit_gain=candidate.average_fit_gain,
                    cumulative_fit=opportunity.current_average_fit,
                    threshold_coverage=opportunity.current_threshold_coverage,
                    reason=(
                        "基于更新后的当前技能集合重新计算全部剩余候选；"
                        f"配置化边际收益为 {marginal_gain:.6f}，"
                        f"单位学习小时收益为 {gain_per_hour:.6f}。"
                    ),
                    learning_hours=_learning_hours_report(
                        estimate,
                        hours,
                        candidate.skill_id in request.learning_hours_overrides,
                    ),
                )
            )

        return LearningOptimizerResult(
            status=opportunity.status,
            strategy="iterative_greedy_marginal_gain",
            hour_budget=request.hour_budget,
            cumulative_hours=cumulative_hours,
            remaining_hours=max(0.0, request.hour_budget - cumulative_hours),
            initial_fit=initial_fit,
            final_fit=opportunity.current_average_fit,
            final_threshold_coverage=opportunity.current_threshold_coverage,
            steps=tuple(steps),
            warnings=tuple(sorted(warnings)),
            config_version=self.config.version,
        )

    def _learning_hours_catalog(self) -> dict[str, LearningHoursEstimate]:
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            rows = _fetch_rows(
                connection,
                """
                SELECT
                    skill_id,
                    learning_hours_min,
                    learning_hours_expected,
                    learning_hours_max,
                    learning_cost_source
                FROM skills
                """,
                [],
            )
        finally:
            connection.close()
        return {row["skill_id"]: LearningHoursEstimate(**row) for row in rows}


def _learning_hours_report(
    estimate: LearningHoursEstimate,
    effective_hours: float,
    is_user_override: bool,
) -> LearningHoursReport:
    return LearningHoursReport(
        **estimate.model_dump(),
        effective_expected_hours=effective_hours,
        is_user_override=is_user_override,
    )
