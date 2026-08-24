from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarketValueWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    demand: float = Field(ge=0, le=1)
    adjusted_salary_association: float = Field(ge=0, le=1)
    trend: float = Field(ge=0, le=1)
    skill_synergy: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> "MarketValueWeights":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("market value weights must sum to 1")
        return self


class PersonalROIWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    marginal_skill_coverage_gain: float = Field(ge=0, le=1)
    market_value: float = Field(ge=0, le=1)
    learning_cost_efficiency: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_total(self) -> "PersonalROIWeights":
        if abs(sum(self.model_dump().values()) - 1.0) > 1e-9:
            raise ValueError("personal ROI weights must sum to 1")
        return self


class MarketValueConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    weights: MarketValueWeights
    salary_association_min_pct: float
    salary_association_max_pct: float
    trend_slope_min: float
    trend_slope_max: float
    missing_component_policy: Literal["exclude_and_reweight"]

    @model_validator(mode="after")
    def validate_ranges(self) -> "MarketValueConfig":
        if self.salary_association_min_pct >= self.salary_association_max_pct:
            raise ValueError("salary association minimum must be below maximum")
        if self.trend_slope_min >= self.trend_slope_max:
            raise ValueError("trend slope minimum must be below maximum")
        return self


class PersonalROIConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    weights: PersonalROIWeights
    learning_hours_half_value: float = Field(gt=0)


class SensitivityConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    sensitive_rank_range: int = Field(ge=1)
    market_value_scenarios: dict[str, MarketValueWeights]
    personal_roi_scenarios: dict[str, PersonalROIWeights]

    @model_validator(mode="after")
    def validate_scenarios(self) -> "SensitivityConfig":
        if not self.market_value_scenarios or not self.personal_roi_scenarios:
            raise ValueError("sensitivity scenarios cannot be empty")
        if any(not name.strip() for name in self.market_value_scenarios):
            raise ValueError("market value scenario names cannot be blank")
        if any(not name.strip() for name in self.personal_roi_scenarios):
            raise ValueError("personal ROI scenario names cannot be blank")
        return self


class OptimizerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    average_fit_gain_weight: float = Field(ge=0, le=1)
    threshold_coverage_gain_weight: float = Field(ge=0, le=1)
    default_match_threshold: float = Field(ge=0, le=1)
    minimum_marginal_gain: float = Field(ge=0, le=1)
    selection_mode: Literal["gain_per_expected_hour"]

    @model_validator(mode="after")
    def validate_weights(self) -> "OptimizerConfig":
        total = self.average_fit_gain_weight + self.threshold_coverage_gain_weight
        if abs(total - 1.0) > 1e-9:
            raise ValueError("optimizer marginal gain weights must sum to 1")
        return self


class DecisionScoreConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    market_value: MarketValueConfig
    personal_roi: PersonalROIConfig
    sensitivity: SensitivityConfig
    optimizer: OptimizerConfig


def load_decision_score_config(path: Path) -> DecisionScoreConfig:
    if not path.is_file():
        raise FileNotFoundError(f"Decision score config does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Decision score config root must be an object")
    return DecisionScoreConfig.model_validate(payload)
