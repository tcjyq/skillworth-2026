from __future__ import annotations

from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .decision_config import (
    DecisionScoreConfig,
    MarketValueWeights,
    PersonalROIWeights,
)


METHODOLOGY_VERSION = "phase10_decision_scores_v1"


class MarketValueInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(min_length=1)
    demand: float = Field(ge=0, le=1)
    adjusted_salary_association_pct: float | None = None
    trend_slope: float | None = None
    skill_synergy: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=100)

    @field_validator("adjusted_salary_association_pct", "trend_slope")
    @classmethod
    def validate_finite_optional(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("score inputs must be finite")
        return value


class ScoreComponent(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_value: float | None
    normalized_score: float | None = Field(default=None, ge=0, le=100)
    configured_weight: float = Field(ge=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=100)
    available: bool
    explanation: str


class MarketValueResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    market_value_score: float = Field(ge=0, le=100)
    components: dict[str, ScoreComponent]
    warnings: tuple[str, ...]
    methodology_version: str = METHODOLOGY_VERSION
    config_version: str


class LearningHoursEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(min_length=1)
    learning_hours_min: float = Field(ge=0)
    learning_hours_expected: float = Field(gt=0)
    learning_hours_max: float = Field(gt=0)
    learning_cost_source: str = Field(min_length=1)

    @field_validator(
        "learning_hours_min",
        "learning_hours_expected",
        "learning_hours_max",
    )
    @classmethod
    def validate_finite_hours(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("learning hours must be finite")
        return value

    @model_validator(mode="after")
    def validate_order(self) -> "LearningHoursEstimate":
        if not (
            self.learning_hours_min
            <= self.learning_hours_expected
            <= self.learning_hours_max
        ):
            raise ValueError("learning hours must satisfy min <= expected <= max")
        return self


class LearningHoursReport(LearningHoursEstimate):
    effective_expected_hours: float = Field(gt=0)
    is_user_override: bool
    is_estimate: bool = True
    disclaimer: str = "Learning Hours 是估算，不是课程时长、掌握承诺或就业承诺。"


class PersonalROIInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(min_length=1)
    marginal_skill_coverage_gain: float = Field(ge=0, le=1)
    market_value: float = Field(ge=0, le=100)
    learning_hours: LearningHoursEstimate
    learning_hours_override: float | None = Field(default=None, gt=0)
    confidence: float = Field(ge=0, le=100)

    @field_validator("learning_hours_override")
    @classmethod
    def validate_finite_override(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("learning_hours_override must be finite")
        return value

    @model_validator(mode="after")
    def validate_skill(self) -> "PersonalROIInput":
        if self.learning_hours.skill_id != self.skill_id:
            raise ValueError("learning hours skill_id must match ROI skill_id")
        return self


class PersonalROIResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    personal_roi_score: float = Field(ge=0, le=100)
    components: dict[str, ScoreComponent]
    learning_hours: LearningHoursReport
    methodology_version: str = METHODOLOGY_VERSION
    config_version: str


class SensitivitySkillRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    baseline_rank: int = Field(ge=1)
    rank_min: int = Field(ge=1)
    rank_max: int = Field(ge=1)
    rank_range: int = Field(ge=0)
    rank_stability: float = Field(ge=0, le=1)
    scenario_ranks: dict[str, int]
    warning: Literal["Sensitive Ranking Warning"] | None = None


class SensitivityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    score_type: Literal["market_value", "personal_roi"]
    scenario_names: tuple[str, ...]
    overall_rank_stability: float = Field(ge=0, le=1)
    records: tuple[SensitivitySkillRecord, ...]
    config_version: str


class DecisionScoreEngine:
    def __init__(self, config: DecisionScoreConfig) -> None:
        self.config = config

    def market_value(
        self,
        evidence: MarketValueInput,
        *,
        weights: MarketValueWeights | None = None,
    ) -> MarketValueResult:
        configured_weights = weights or self.config.market_value.weights
        raw_components: dict[str, tuple[float | None, float | None, str]] = {
            "demand": (
                evidence.demand,
                evidence.demand * 100,
                "目标市场切片中的岗位覆盖率。",
            ),
            "adjusted_salary_association": (
                evidence.adjusted_salary_association_pct,
                self._range_score(
                    evidence.adjusted_salary_association_pct,
                    self.config.market_value.salary_association_min_pct,
                    self.config.market_value.salary_association_max_pct,
                ),
                "Adjusted Salary Association 百分比按配置上下界线性缩放。",
            ),
            "trend": (
                evidence.trend_slope,
                self._range_score(
                    evidence.trend_slope,
                    self.config.market_value.trend_slope_min,
                    self.config.market_value.trend_slope_max,
                ),
                "月度 Skill Coverage 趋势斜率按配置上下界线性缩放。",
            ),
            "skill_synergy": (
                evidence.skill_synergy,
                evidence.skill_synergy * 100,
                "技能协同输入，范围 [0,1]。",
            ),
            "confidence": (
                evidence.confidence,
                evidence.confidence,
                "Phase 8 Data Confidence，范围 [0,100]。",
            ),
        }
        weight_values = configured_weights.model_dump()
        available_weight = sum(
            weight_values[name]
            for name, (_, score, _) in raw_components.items()
            if score is not None
        )
        if available_weight <= 0:
            raise ValueError("no weighted Market Value component is available")
        components: dict[str, ScoreComponent] = {}
        warnings: list[str] = []
        total = 0.0
        for name, (raw_value, normalized_score, explanation) in raw_components.items():
            available = normalized_score is not None
            effective_weight = (
                weight_values[name] / available_weight if available else 0.0
            )
            contribution = (
                normalized_score * effective_weight if normalized_score is not None else 0.0
            )
            if not available:
                warnings.append(f"{name}_unavailable")
            components[name] = ScoreComponent(
                raw_value=raw_value,
                normalized_score=self._rounded(normalized_score),
                configured_weight=weight_values[name],
                effective_weight=effective_weight,
                contribution=round(contribution, 6),
                available=available,
                explanation=explanation,
            )
            total += contribution
        return MarketValueResult(
            skill_id=evidence.skill_id,
            market_value_score=round(total, 2),
            components=components,
            warnings=tuple(warnings),
            config_version=self.config.version,
        )

    def personal_roi(
        self,
        evidence: PersonalROIInput,
        *,
        weights: PersonalROIWeights | None = None,
    ) -> PersonalROIResult:
        configured_weights = weights or self.config.personal_roi.weights
        effective_hours = (
            evidence.learning_hours_override
            or evidence.learning_hours.learning_hours_expected
        )
        half_value = self.config.personal_roi.learning_hours_half_value
        normalized_scores = {
            "marginal_skill_coverage_gain": evidence.marginal_skill_coverage_gain
            * 100,
            "market_value": evidence.market_value,
            "learning_cost_efficiency": 100 * half_value / (half_value + effective_hours),
            "confidence": evidence.confidence,
        }
        raw_values = {
            "marginal_skill_coverage_gain": evidence.marginal_skill_coverage_gain,
            "market_value": evidence.market_value,
            "learning_cost_efficiency": effective_hours,
            "confidence": evidence.confidence,
        }
        explanations = {
            "marginal_skill_coverage_gain": "Phase 9 Average Skill Fit Gain。",
            "market_value": "配置化 Market Value Score。",
            "learning_cost_efficiency": "按 half_value / (half_value + hours) 衰减。",
            "confidence": "候选技能的 Phase 8 Data Confidence。",
        }
        weight_values = configured_weights.model_dump()
        components: dict[str, ScoreComponent] = {}
        total = 0.0
        for name, normalized_score in normalized_scores.items():
            contribution = normalized_score * weight_values[name]
            total += contribution
            components[name] = ScoreComponent(
                raw_value=raw_values[name],
                normalized_score=round(normalized_score, 6),
                configured_weight=weight_values[name],
                effective_weight=weight_values[name],
                contribution=round(contribution, 6),
                available=True,
                explanation=explanations[name],
            )
        hours = evidence.learning_hours
        return PersonalROIResult(
            skill_id=evidence.skill_id,
            personal_roi_score=round(total, 2),
            components=components,
            learning_hours=LearningHoursReport(
                **hours.model_dump(),
                effective_expected_hours=effective_hours,
                is_user_override=evidence.learning_hours_override is not None,
            ),
            config_version=self.config.version,
        )

    @staticmethod
    def _range_score(value: float | None, minimum: float, maximum: float) -> float | None:
        if value is None:
            return None
        return 100 * min(1.0, max(0.0, (value - minimum) / (maximum - minimum)))

    @staticmethod
    def _rounded(value: float | None) -> float | None:
        return None if value is None else round(value, 6)


class SensitivityAnalyzer:
    def __init__(self, score_engine: DecisionScoreEngine) -> None:
        self._score_engine = score_engine

    def market_value(
        self,
        inputs: tuple[MarketValueInput, ...],
    ) -> SensitivityResult:
        self._validate_unique([item.skill_id for item in inputs])
        baseline = {
            item.skill_id: self._score_engine.market_value(item).market_value_score
            for item in inputs
        }
        scenarios = {
            name: {
                item.skill_id: self._score_engine.market_value(
                    item, weights=weights
                ).market_value_score
                for item in inputs
            }
            for name, weights in self._score_engine.config.sensitivity.market_value_scenarios.items()
        }
        return self._summarize("market_value", baseline, scenarios)

    def personal_roi(
        self,
        inputs: tuple[PersonalROIInput, ...],
    ) -> SensitivityResult:
        self._validate_unique([item.skill_id for item in inputs])
        baseline = {
            item.skill_id: self._score_engine.personal_roi(item).personal_roi_score
            for item in inputs
        }
        scenarios = {
            name: {
                item.skill_id: self._score_engine.personal_roi(
                    item, weights=weights
                ).personal_roi_score
                for item in inputs
            }
            for name, weights in self._score_engine.config.sensitivity.personal_roi_scenarios.items()
        }
        return self._summarize("personal_roi", baseline, scenarios)

    def _summarize(
        self,
        score_type: Literal["market_value", "personal_roi"],
        baseline_scores: dict[str, float],
        scenario_scores: dict[str, dict[str, float]],
    ) -> SensitivityResult:
        rank_maps = {"baseline": _ordinal_ranks(baseline_scores)}
        rank_maps.update(
            {name: _ordinal_ranks(scores) for name, scores in scenario_scores.items()}
        )
        skill_count = len(baseline_scores)
        records: list[SensitivitySkillRecord] = []
        for skill_id in baseline_scores:
            scenario_ranks = {
                name: ranks[skill_id] for name, ranks in rank_maps.items()
            }
            rank_min = min(scenario_ranks.values())
            rank_max = max(scenario_ranks.values())
            rank_range = rank_max - rank_min
            stability = (
                1.0 if skill_count == 1 else 1 - rank_range / (skill_count - 1)
            )
            records.append(
                SensitivitySkillRecord(
                    skill_id=skill_id,
                    baseline_rank=scenario_ranks["baseline"],
                    rank_min=rank_min,
                    rank_max=rank_max,
                    rank_range=rank_range,
                    rank_stability=round(stability, 6),
                    scenario_ranks=scenario_ranks,
                    warning=(
                        "Sensitive Ranking Warning"
                        if rank_range
                        >= self._score_engine.config.sensitivity.sensitive_rank_range
                        else None
                    ),
                )
            )
        records.sort(key=lambda record: (record.baseline_rank, record.skill_id))
        overall = sum(record.rank_stability for record in records) / len(records)
        return SensitivityResult(
            score_type=score_type,
            scenario_names=tuple(rank_maps),
            overall_rank_stability=round(overall, 6),
            records=tuple(records),
            config_version=self._score_engine.config.version,
        )

    @staticmethod
    def _validate_unique(skill_ids: list[str]) -> None:
        if not skill_ids:
            raise ValueError("sensitivity inputs cannot be empty")
        if len(skill_ids) != len(set(skill_ids)):
            raise ValueError("sensitivity skill_ids must be unique")


def _ordinal_ranks(scores: dict[str, float]) -> dict[str, int]:
    ordered = sorted(scores, key=lambda skill_id: (-scores[skill_id], skill_id))
    return {skill_id: index for index, skill_id in enumerate(ordered, start=1)}
