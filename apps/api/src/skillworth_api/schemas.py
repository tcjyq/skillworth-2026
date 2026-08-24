from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from skillworth_analytics.advanced import (
    AdjustedSalaryAssociationRecord,
    SkillTrendRecord,
)
from skillworth_analytics.analytics import (
    AnalyticsFilters,
    AnalyticsMetadata,
    PlatformBalancedDemandRecord,
    SalaryBySkillRecord,
    SkillDemandRecord,
    SkillDemandResult,
)
from skillworth_analytics.guardrails import SourceEligibilityEvidence
from skillworth_analytics.china_skillworth import ChinaSkillWorthVisualRecord


class ApiModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ErrorBody(ApiModel):
    code: str
    message: str
    details: tuple[dict[str, Any], ...] = ()


class ErrorResponse(ApiModel):
    error: ErrorBody


class HealthResponse(ApiModel):
    status: str
    service_version: str
    warehouse_available: bool


class ProductScopeMetadata(ApiModel):
    market_scope: str
    source_role: str
    snapshot: str
    job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    disclaimer: str


class ChinaSkillWorthSummaryResponse(ApiModel):
    market_scope: str
    source_role: str
    snapshot: str
    access_date: date | None = None
    recency_window: Literal["90d", "180d", "365d", "all_active"]
    job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    disclaimer: str
    salary_signal_status: Literal["unavailable"] = "unavailable"
    trend_signal_status: Literal["unavailable"] = "unavailable"
    market_themes: tuple["ChinaMarketThemeRecord", ...] = ()
    records: tuple[ChinaSkillWorthVisualRecord, ...]


class ChinaMarketThemeRecord(ApiModel):
    market_theme: str
    job_count: int = Field(ge=0)
    job_coverage: float = Field(ge=0, le=1)
    company_count: int = Field(ge=0)
    company_coverage: float = Field(ge=0, le=1)
    role_count: int = Field(ge=0)
    snapshot_id: str
    recency_window: Literal["90d", "180d", "365d", "all_active"]


class ChinaSkillWorthQuery(ApiModel):
    eligibility: Literal["main", "secondary", "excluded", "all"] = "main"
    robustness: Literal["robust", "moderate", "sensitive", "all"] = "robust"
    role: str | None = Field(default=None, min_length=1)
    skill_type: str | None = Field(default=None, min_length=1)
    recency_window: Literal["90d", "180d", "365d", "all_active"] = "180d"


class MarketQuery(ApiModel):
    role_id: str | None = Field(default=None, min_length=1)
    city_code: str | None = Field(default=None, min_length=1)
    experience_band: str | None = Field(default=None, min_length=1)
    education_band: str | None = Field(default=None, min_length=1)
    source_id: tuple[str, ...] = Field(default=(), max_length=32)
    published_from: date | None = None
    published_to: date | None = None
    market_scope: Literal["target", "all"] = "target"
    source_scope: Literal["core", "all"] = "core"

    def to_filters(self) -> AnalyticsFilters:
        return AnalyticsFilters(
            role_id=self.role_id,
            city_code=self.city_code,
            experience_band=self.experience_band,
            education_band=self.education_band,
            source_ids=self.source_id,
            published_from=self.published_from,
            published_to=self.published_to,
            market_scope=self.market_scope,
            source_scope=self.source_scope,
        )


class MarketSummaryResponse(ApiModel):
    metadata: AnalyticsMetadata
    top_skills: tuple[SkillDemandRecord, ...]
    platform_balanced_top_skills: tuple[PlatformBalancedDemandRecord, ...]
    platform_balanced_eligible_source_count: int = Field(ge=0)
    platform_balanced_ineligible_sources: tuple[SourceEligibilityEvidence, ...]
    platform_balanced_methodology_version: str
    salary_by_skill: tuple[SalaryBySkillRecord, ...]


class SkillDetailResponse(ApiModel):
    demand: SkillDemandRecord
    salary_distribution: SalaryBySkillRecord | None
    adjusted_salary_association: AdjustedSalaryAssociationRecord | None
    trend: SkillTrendRecord | None


class SkillSalaryResponse(ApiModel):
    salary_distribution: SalaryBySkillRecord | None
    adjusted_salary_association: AdjustedSalaryAssociationRecord


class RelatedSkillRecord(ApiModel):
    skill_id: str
    canonical_name: str
    category: str
    cooccurrence_count: int = Field(ge=0)
    jaccard: float = Field(ge=0, le=1)
    pmi: float
    weight: float = Field(ge=0)


class RelatedSkillsResponse(ApiModel):
    skill_id: str
    records: tuple[RelatedSkillRecord, ...]
    methodology_version: str
    config_version: str


class RoleRecord(ApiModel):
    role_id: str
    canonical_job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    city_count: int = Field(ge=0)
    salary_mid_median: float | None = Field(default=None, ge=0)


class RolesResponse(ApiModel):
    records: tuple[RoleRecord, ...]


class RoleDetailResponse(ApiModel):
    role: RoleRecord
    skill_demand: SkillDemandResult


class SourceRecord(ApiModel):
    source_id: str
    source_name: str | None = None
    dataset_version: str | None = None
    dataset_url: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    data_usage_status: str | None = None
    source_job_count: int = Field(ge=0)
    canonical_job_count: int = Field(ge=0)
    first_observed_at: str | None = None
    last_observed_at: str | None = None
    analysis_role: Literal[
        "core_market",
        "core_market_candidate",
        "supplementary_market",
        "engineering_validation",
        "historical_reference",
        "external_market_benchmark",
    ]
    core_market_eligible: bool
    ineligibility_reasons: tuple[str, ...] = ()
    target_sample_size: int = Field(ge=0)


class PipelineFreshness(ApiModel):
    latest_observed_at: date | None
    pipeline_age_days: int | None = Field(default=None, ge=0)


class MarketFreshness(ApiModel):
    latest_posted_at: date | None
    median_posting_age_days: float | None = Field(default=None, ge=0)
    p75_posting_age_days: float | None = Field(default=None, ge=0)
    posting_date_coverage: float = Field(ge=0, le=1)


class SourcesResponse(ApiModel):
    records: tuple[SourceRecord, ...]


class DataQualityResponse(ApiModel):
    raw_row_count: int = Field(ge=0)
    silver_row_count: int = Field(ge=0)
    missing_rate: float = Field(ge=0, le=1)
    missing_rate_by_field: dict[str, float]
    salary_parse_rate: float = Field(ge=0, le=1)
    role_parse_rate: float = Field(ge=0, le=1)
    city_parse_rate: float = Field(ge=0, le=1)
    invalid_record_rate: float = Field(ge=0, le=1)
    pipeline_freshness: PipelineFreshness
    market_freshness: MarketFreshness
    source_roles: dict[str, str]
