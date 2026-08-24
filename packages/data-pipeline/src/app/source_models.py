from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SourceMode = Literal[
    "manual_import", "public_dataset", "research_dataset", "external_benchmark", "public_api",
    "authorized_http",
]
Freshness = Literal["fresh", "stale", "never"]
SourceAnalysisRole = Literal[
    "core_market",
    "core_market_candidate",
    "supplementary_market",
    "engineering_validation",
    "historical_reference",
    "external_market_benchmark",
]
DataUsageStatus = Literal[
    "reviewed", "no_explicit_block_found", "permission_required", "restricted"
]


class SourceAdapterConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_name: str
    source_type: str
    analysis_role: SourceAnalysisRole = "engineering_validation"
    acquisition_method: str
    enabled: bool = False
    mode: SourceMode
    connector: Literal[
        "csv",
        "parquet",
        "manual_export",
        "public_dataset",
        "techsalerator_china_jobs_v1",
        "hk_csb_gov_vacancies",
        "ncss_public_export",
        "nextgig_june_2026",
        "freehire_public_api",
        "external_benchmark",
        "authorized_http",
    ]
    terms_url: str
    notes: str = ""
    schema_mapping_version: str
    column_mapping: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    dataset_url: str | None = None
    dataset_version: str | None = None
    download_url: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    expected_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    data_usage_status: DataUsageStatus = "reviewed"

    @field_validator("terms_url")
    @classmethod
    def terms_reference_must_use_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("terms_url must use HTTPS")
        return value

    @model_validator(mode="after")
    def authorized_http_requires_explicit_enablement(self) -> "SourceAdapterConfig":
        if self.mode == "authorized_http" and not self.enabled:
            raise ValueError("authorized_http sources must be explicitly enabled")
        if self.mode == "public_dataset" and self.enabled:
            required = {
                "dataset_url": self.dataset_url,
                "dataset_version": self.dataset_version,
                "download_url": self.download_url,
                "license_name": self.license_name,
                "license_url": self.license_url,
                "expected_sha256": self.expected_sha256,
            }
            missing = sorted(name for name, value in required.items() if not value)
            if missing:
                raise ValueError(f"enabled public_dataset is missing reviewed metadata: {missing}")
            urls = (self.dataset_url, self.download_url, self.license_url)
            if any(url is not None and not url.startswith("https://") for url in urls):
                raise ValueError("public dataset URLs must use HTTPS")
        if self.data_usage_status == "no_explicit_block_found" and self.mode != "public_api":
            raise ValueError("no_explicit_block_found is restricted to reviewed public_api sources")
        if self.mode == "public_api":
            if not self.enabled:
                raise ValueError("public_api sources must be explicitly enabled")
            if self.connector != "freehire_public_api":
                raise ValueError("public_api mode currently permits only freehire_public_api")
        return self


class SourceRegistry(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    freshness_days: int = Field(default=30, ge=1)
    sources: tuple[SourceAdapterConfig, ...]

    @model_validator(mode="after")
    def source_ids_are_unique(self) -> "SourceRegistry":
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source registry contains duplicate source ids")
        return self

    def get(self, source_id: str) -> SourceAdapterConfig:
        try:
            return next(source for source in self.sources if source.source_id == source_id)
        except StopIteration as error:
            raise KeyError(f"Unknown source: {source_id}") from error


class SourceMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_name: str
    acquisition_method: str
    analysis_role: SourceAnalysisRole
    enabled: bool
    mode: SourceMode
    terms_url: str
    data_usage_status: DataUsageStatus = "reviewed"
    last_sync: datetime | None = None
    record_count: int = Field(default=0, ge=0)
    freshness: Freshness = "never"
    notes: str = ""


class SourceImportManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_name: str
    source_type: str
    analysis_role: SourceAnalysisRole = "engineering_validation"
    acquisition_method: str
    enabled: bool
    mode: SourceMode
    terms_url: str
    data_usage_status: DataUsageStatus = "reviewed"
    connector: str
    connector_version: str
    schema_mapping_version: str
    ingestion_run_id: str
    imported_at: datetime
    raw_artifact_path: str
    raw_artifact_sha256: str
    stored_raw_artifact_path: str | None = None
    bronze_path: str
    raw_record_count: int = Field(default=0, ge=0)
    record_count: int = Field(ge=0)
    rejected_record_count: int = Field(default=0, ge=0)
    connector_warnings: tuple[str, ...] = ()
    notes: str = ""


class SourceImportResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    ingestion_run_id: str
    pipeline_stage: Literal["warehouse"] = "warehouse"
    raw_record_count: int = Field(ge=0)
    record_count: int = Field(ge=0)
    rejected_record_count: int = Field(ge=0)
    connector_warnings: tuple[str, ...] = ()
    stored_raw_artifact_path: Path | None = None
    bronze_path: Path
    manifest_path: Path
    silver_path: Path
    quality_report_path: Path
    canonical_jobs_path: Path
    job_source_map_path: Path
    dedup_report_path: Path
    skills_path: Path
    job_skills_path: Path
    warehouse_path: Path
    benchmark_path: Path
