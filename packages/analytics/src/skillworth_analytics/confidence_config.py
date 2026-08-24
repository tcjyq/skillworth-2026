from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConfidenceWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_strength: float = Field(gt=0, le=1)
    effective_source_diversity: float = Field(gt=0, le=1)
    market_freshness: float = Field(gt=0, le=1)
    metric_specific_coverage: float = Field(gt=0, le=1)
    cross_source_agreement: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> "ConfidenceWeights":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("confidence weights must sum to 1")
        return self


class ConfidenceLevels(BaseModel):
    model_config = ConfigDict(frozen=True)
    high_min_score: float = Field(gt=0, le=100)
    medium_min_score: float = Field(ge=0, lt=100)

    @model_validator(mode="after")
    def validate_order(self) -> "ConfidenceLevels":
        if self.medium_min_score >= self.high_min_score:
            raise ValueError("medium_min_score must be below high_min_score")
        return self


class SampleStrengthConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    target_sample_size: int = Field(ge=1)
    warning_below: int = Field(ge=1)
    severe_below: int = Field(ge=1)


class SourceDiversityConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    target_effective_sources: float = Field(ge=1)
    warning_below_effective_sources: float = Field(ge=1)
    required_eligible_sources: int = Field(ge=2)


class MarketFreshnessConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    full_score_days: int = Field(ge=0)
    warning_after_days: int = Field(ge=0)
    zero_score_days: int = Field(ge=1)
    minimum_posting_date_coverage: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_order(self) -> "MarketFreshnessConfig":
        if not self.full_score_days <= self.warning_after_days < self.zero_score_days:
            raise ValueError("invalid market freshness thresholds")
        return self


class MetricCoverageConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    warning_below: float = Field(ge=0, le=1)


class AgreementConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    minimum_sources: int = Field(ge=2)
    minimum_sample_per_source: int = Field(ge=1)
    warning_std: float = Field(ge=0, le=1)
    zero_score_std: float = Field(gt=0, le=1)


class ConfidenceCapsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    no_gold_benchmark: float = Field(ge=0, le=100)
    insufficient_eligible_sources: float = Field(ge=0, le=100)
    severe_sample_size: float = Field(ge=0, le=100)


class DataConfidenceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    version: str
    weights: ConfidenceWeights
    levels: ConfidenceLevels
    sample_strength: SampleStrengthConfig
    effective_source_diversity: SourceDiversityConfig
    market_freshness: MarketFreshnessConfig
    metric_specific_coverage: MetricCoverageConfig
    cross_source_agreement: AgreementConfig
    confidence_caps: ConfidenceCapsConfig


def load_data_confidence_config(path: Path) -> DataConfidenceConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return DataConfidenceConfig.model_validate(payload)
