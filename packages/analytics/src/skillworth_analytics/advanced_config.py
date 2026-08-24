from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrendConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    rolling_window_months: int = Field(ge=2)
    minimum_observed_months: int = Field(ge=2)
    minimum_monthly_sample_size: int = Field(ge=1)
    minimum_total_sample_size: int = Field(ge=1)
    minimum_posting_date_coverage: float = Field(ge=0, le=1)
    emerging_max_coverage_3m_ago: float = Field(ge=0, le=1)
    emerging_min_change_3m: float = Field(gt=0, le=1)
    growing_min_slope: float = Field(gt=0, le=1)
    growing_min_change_3m: float = Field(gt=0, le=1)
    mature_min_latest_coverage: float = Field(ge=0, le=1)
    mature_max_abs_slope: float = Field(ge=0, le=1)
    mature_max_volatility: float = Field(ge=0, le=1)
    stable_max_abs_slope: float = Field(ge=0, le=1)
    stable_max_volatility: float = Field(ge=0, le=1)
    declining_max_slope: float = Field(lt=0, ge=-1)
    declining_max_change_3m: float = Field(lt=0, ge=-1)
    niche_max_latest_coverage: float = Field(ge=0, le=1)
    niche_max_abs_slope: float = Field(ge=0, le=1)


class SalaryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_sample_size: int = Field(ge=3)
    minimum_skill_jobs: int = Field(ge=1)
    minimum_non_skill_jobs: int = Field(ge=1)
    minimum_salary_monthly: float = Field(gt=0)
    maximum_salary_monthly: float = Field(gt=0)
    confidence_level: float = Field(gt=0, lt=1)
    covariance_type: Literal["HC3"]
    maximum_condition_number: float = Field(gt=1)

    @model_validator(mode="after")
    def validate_salary_range(self) -> "SalaryConfig":
        if self.minimum_salary_monthly >= self.maximum_salary_monthly:
            raise ValueError("minimum_salary_monthly must be below maximum_salary_monthly")
        return self


class NetworkConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_cooccurrence_count: int = Field(ge=1)
    minimum_jaccard: float = Field(ge=0, le=1)
    edge_weight: Literal["jaccard", "cooccurrence_count"]


class AdvancedAnalyticsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    trend: TrendConfig
    salary: SalaryConfig
    network: NetworkConfig


def load_advanced_analytics_config(path: Path) -> AdvancedAnalyticsConfig:
    if not path.is_file():
        raise FileNotFoundError(f"Advanced analytics config does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Advanced analytics config root must be an object")
    return AdvancedAnalyticsConfig.model_validate(payload)
