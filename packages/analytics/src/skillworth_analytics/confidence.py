from __future__ import annotations

from datetime import date
from math import isfinite, log1p
from statistics import pstdev
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .confidence_config import DataConfidenceConfig


ConfidenceLevel = Literal["High", "Medium", "Low"]


class ConfidenceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_size: int = Field(ge=0)
    source_sample_sizes: dict[str, int]
    source_eligibility: dict[str, bool] = Field(default_factory=dict)
    latest_observation_date: date | None = None
    latest_posted_date: date | None = None
    median_posting_age_days: float | None = Field(default=None, ge=0)
    p75_posting_age_days: float | None = Field(default=None, ge=0)
    posting_date_coverage: float = Field(default=0, ge=0, le=1)
    as_of_date: date
    metric_eligible_count: int | None = Field(default=None, ge=0)
    is_salary_metric: bool = False
    salary_eligible_count: int | None = Field(default=None, ge=0)
    platform_metric_values: dict[str, float] = Field(default_factory=dict)
    gold_benchmark_available: bool = False

    @field_validator("source_sample_sizes")
    @classmethod
    def validate_source_sample_sizes(cls, value: dict[str, int]) -> dict[str, int]:
        if any(not key.strip() or count < 0 for key, count in value.items()):
            raise ValueError("source_sample_sizes must contain nonblank keys and nonnegative values")
        return value

    @field_validator("platform_metric_values")
    @classmethod
    def validate_platform_values(cls, value: dict[str, float]) -> dict[str, float]:
        if any(not key.strip() or not isfinite(metric) or not 0 <= metric <= 1 for key, metric in value.items()):
            raise ValueError("platform_metric_values values must be finite and within [0, 1]")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> "ConfidenceEvidence":
        if self.is_salary_metric and self.salary_eligible_count is None:
            raise ValueError("salary_eligible_count is required for salary metrics")
        if not self.is_salary_metric and self.salary_eligible_count is not None:
            raise ValueError("salary_eligible_count is only valid for salary metrics")
        if self.salary_eligible_count is not None and self.salary_eligible_count > self.sample_size:
            raise ValueError("salary_eligible_count cannot exceed sample_size")
        if self.metric_eligible_count is not None and self.metric_eligible_count > self.sample_size:
            raise ValueError("metric_eligible_count cannot exceed sample_size")
        unknown = set(self.source_eligibility) - set(self.source_sample_sizes)
        if unknown:
            raise ValueError(f"source_eligibility references unknown sources: {sorted(unknown)}")
        return self

    def is_source_eligible(self, source_id: str) -> bool:
        return self.source_eligibility.get(source_id, True)


class ConfidenceComponent(BaseModel):
    model_config = ConfigDict(frozen=True)
    component_score: float | None = Field(ge=0, le=100)
    raw_value: float | int | None
    weight: float = Field(gt=0, le=1)
    effective_weight: float = Field(ge=0, le=1)
    applicable: bool
    available: bool
    explanation: str


class ConfidenceWarning(BaseModel):
    model_config = ConfigDict(frozen=True)
    code: str
    component: str
    message: str


class DataConfidenceResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    confidence_score: float = Field(ge=0, le=100)
    confidence_level: ConfidenceLevel
    confidence_cap: float = Field(ge=0, le=100)
    raw_source_count: int = Field(ge=0)
    eligible_source_count: int = Field(ge=0)
    effective_source_count: float = Field(ge=0)
    latest_observed_at: date | None
    pipeline_age_days: int | None = Field(default=None, ge=0)
    latest_posted_at: date | None
    median_posting_age_days: float | None = Field(default=None, ge=0)
    p75_posting_age_days: float | None = Field(default=None, ge=0)
    posting_date_coverage: float = Field(ge=0, le=1)
    confidence_components: dict[str, ConfidenceComponent]
    warnings: tuple[ConfidenceWarning, ...]
    methodology_version: str
    config_version: str


class DataConfidenceEngine:
    def __init__(self, config: DataConfidenceConfig) -> None:
        self.config = config

    def level_for_score(self, score: float) -> ConfidenceLevel:
        if score >= self.config.levels.high_min_score:
            return "High"
        if score >= self.config.levels.medium_min_score:
            return "Medium"
        return "Low"

    def evaluate(self, evidence: ConfidenceEvidence) -> DataConfidenceResult:
        warnings: list[ConfidenceWarning] = []
        effective_sources = self._effective_source_count(evidence)
        components = {
            "sample_strength": self._sample_strength(evidence, warnings),
            "effective_source_diversity": self._source_diversity(evidence, effective_sources, warnings),
            "market_freshness": self._market_freshness(evidence, warnings),
            "metric_specific_coverage": self._metric_coverage(evidence, warnings),
            "cross_source_agreement": self._agreement(evidence, warnings),
        }
        applicable_weight = sum(item.weight for item in components.values() if item.applicable)
        weighted = 0.0
        normalized: dict[str, ConfidenceComponent] = {}
        for name, component in components.items():
            effective_weight = component.weight / applicable_weight if component.applicable else 0.0
            normalized[name] = component.model_copy(update={"effective_weight": effective_weight})
            if component.component_score is not None:
                weighted += component.component_score * effective_weight

        eligible_count = sum(
            count > 0 and evidence.is_source_eligible(source)
            for source, count in evidence.source_sample_sizes.items()
        )
        cap = 100.0
        if not evidence.gold_benchmark_available:
            cap = min(cap, self.config.confidence_caps.no_gold_benchmark)
            warnings.append(self._warning("confidence_capped_no_gold_benchmark", "confidence_cap", "缺少达到门禁的人工 Gold Benchmark，置信度已封顶。"))
        if eligible_count < self.config.effective_source_diversity.required_eligible_sources:
            cap = min(cap, self.config.confidence_caps.insufficient_eligible_sources)
            warnings.append(self._warning("confidence_capped_insufficient_sources", "confidence_cap", "可比较来源不足，置信度已封顶。"))
        if evidence.sample_size < self.config.sample_strength.severe_below:
            cap = min(cap, self.config.confidence_caps.severe_sample_size)
            warnings.append(self._warning("confidence_capped_severe_sample_size", "confidence_cap", "样本量极低，置信度已封顶。"))
        score = round(min(cap, max(0.0, weighted)), 2)
        pipeline_age = (
            max(0, (evidence.as_of_date - evidence.latest_observation_date).days)
            if evidence.latest_observation_date else None
        )
        return DataConfidenceResult(
            confidence_score=score,
            confidence_level=self.level_for_score(score),
            confidence_cap=cap,
            raw_source_count=sum(count > 0 for count in evidence.source_sample_sizes.values()),
            eligible_source_count=eligible_count,
            effective_source_count=round(effective_sources, 6),
            latest_observed_at=evidence.latest_observation_date,
            pipeline_age_days=pipeline_age,
            latest_posted_at=evidence.latest_posted_date,
            median_posting_age_days=evidence.median_posting_age_days,
            p75_posting_age_days=evidence.p75_posting_age_days,
            posting_date_coverage=evidence.posting_date_coverage,
            confidence_components=normalized,
            warnings=tuple(warnings),
            methodology_version=f"data-confidence-{self.config.version}",
            config_version=self.config.version,
        )

    def _effective_source_count(self, evidence: ConfidenceEvidence) -> float:
        counts = [count for source, count in evidence.source_sample_sizes.items() if count > 0 and evidence.is_source_eligible(source)]
        total = sum(counts)
        return 1 / sum((count / total) ** 2 for count in counts) if total else 0.0

    def _sample_strength(self, evidence: ConfidenceEvidence, warnings: list[ConfidenceWarning]) -> ConfidenceComponent:
        config = self.config.sample_strength
        score = 100 * min(1.0, log1p(evidence.sample_size) / log1p(config.target_sample_size))
        if evidence.sample_size < config.warning_below:
            warnings.append(self._warning("sample_size_below_threshold", "sample_strength", f"样本量 {evidence.sample_size} 低于门槛 {config.warning_below}。"))
        return self._component(score, evidence.sample_size, self.config.weights.sample_strength, "样本量按 log1p 缩放，达到目标样本量后封顶。")

    def _source_diversity(self, evidence: ConfidenceEvidence, effective: float, warnings: list[ConfidenceWarning]) -> ConfidenceComponent:
        config = self.config.effective_source_diversity
        if effective < config.warning_below_effective_sources:
            warnings.append(self._warning("effective_source_count_below_threshold", "effective_source_diversity", f"有效来源数 {effective:.2f} 低于门槛 {config.warning_below_effective_sources}。"))
        score = 100 * min(1.0, effective / config.target_effective_sources)
        return self._component(score, effective, self.config.weights.effective_source_diversity, "仅纳入 eligible source，并以 1 / Σ(wᵢ²) 计算有效来源数。")

    def _market_freshness(self, evidence: ConfidenceEvidence, warnings: list[ConfidenceWarning]) -> ConfidenceComponent:
        config = self.config.market_freshness
        age = evidence.p75_posting_age_days
        if age is None and evidence.latest_posted_date is not None:
            age = max(0, (evidence.as_of_date - evidence.latest_posted_date).days)
        if age is None:
            warnings.append(self._warning("market_freshness_missing", "market_freshness", "缺少岗位发布日期，市场时效性按 0 分处理。"))
            score = 0.0
        elif age <= config.full_score_days:
            score = 100.0
        elif age >= config.zero_score_days:
            score = 0.0
        else:
            score = 100 * (config.zero_score_days - age) / (config.zero_score_days - config.full_score_days)
        score *= evidence.posting_date_coverage
        if age is not None and age > config.warning_after_days:
            warnings.append(self._warning("market_data_older_than_threshold", "market_freshness", f"P75 岗位年龄 {age:.0f} 天超过门槛。"))
        if evidence.posting_date_coverage < config.minimum_posting_date_coverage:
            warnings.append(self._warning("posting_date_coverage_below_threshold", "market_freshness", "岗位发布日期覆盖不足。"))
        return self._component(score, age, self.config.weights.market_freshness, "以岗位发布时间 P75 年龄评分，并乘以 posting date coverage；导入时间不替代市场时效。")

    def _metric_coverage(self, evidence: ConfidenceEvidence, warnings: list[ConfidenceWarning]) -> ConfidenceComponent:
        count = evidence.salary_eligible_count if evidence.is_salary_metric else evidence.metric_eligible_count
        if count is None:
            return self._component(None, None, self.config.weights.metric_specific_coverage, "该指标未提供专属覆盖率。", applicable=False, available=False)
        coverage = count / evidence.sample_size if evidence.sample_size else 0.0
        if coverage < self.config.metric_specific_coverage.warning_below:
            code = "salary_coverage_below_threshold" if evidence.is_salary_metric else "metric_coverage_below_threshold"
            warnings.append(self._warning(code, "metric_specific_coverage", f"指标覆盖率 {coverage:.1%} 低于门槛。"))
        return self._component(coverage * 100, coverage, self.config.weights.metric_specific_coverage, "指标可用记录数除以分析样本量。")

    def _agreement(self, evidence: ConfidenceEvidence, warnings: list[ConfidenceWarning]) -> ConfidenceComponent:
        config = self.config.cross_source_agreement
        values = [
            value for source, value in evidence.platform_metric_values.items()
            if evidence.is_source_eligible(source)
            and evidence.source_sample_sizes.get(source, 0) >= config.minimum_sample_per_source
        ]
        if len(values) < config.minimum_sources:
            warnings.append(self._warning("cross_source_agreement_unavailable", "cross_source_agreement", "INSUFFICIENT_COMPARABLE_SOURCES"))
            return self._component(0, None, self.config.weights.cross_source_agreement, "只有至少两个 eligible 且达到最小样本量的来源才计算。", available=False)
        disagreement = pstdev(values)
        score = 100 * max(0.0, 1 - disagreement / config.zero_score_std)
        if disagreement > config.warning_std:
            warnings.append(self._warning("platform_disagreement_above_threshold", "cross_source_agreement", "来源指标分歧超过门槛。"))
        return self._component(score, disagreement, self.config.weights.cross_source_agreement, "使用可比较来源指标值的总体标准差。")

    @staticmethod
    def _warning(code: str, component: str, message: str) -> ConfidenceWarning:
        return ConfidenceWarning(code=code, component=component, message=message)

    @staticmethod
    def _component(score: float | None, raw: float | int | None, weight: float, explanation: str, *, applicable: bool = True, available: bool = True) -> ConfidenceComponent:
        return ConfidenceComponent(
            component_score=None if score is None else round(score, 6),
            raw_value=None if raw is None else round(raw, 6) if isinstance(raw, float) else raw,
            weight=weight,
            effective_weight=0,
            applicable=applicable,
            available=available,
            explanation=explanation,
        )
