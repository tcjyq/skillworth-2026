from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Literal

import duckdb
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .guardrails import (
    MetricGuardrailConfig,
    SourceEligibilityEvidence,
    evaluate_source_eligibility,
    load_metric_guardrail_config,
)


METHODOLOGY_VERSION = "phase6_market_basics_v2"
SQL_DIRECTORY = Path(__file__).parent / "sql"
DEFAULT_GUARDRAIL_CONFIG = Path(__file__).resolve().parents[4] / "data/reference/metric_guardrails.v1.yml"


class AnalyticsFilters(BaseModel):
    """A single, validated market slice shared by every Phase 6 metric."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    role_id: str | None = Field(default=None, min_length=1, max_length=128)
    city_code: str | None = Field(default=None, min_length=1, max_length=64)
    experience_band: str | None = Field(default=None, min_length=1, max_length=64)
    education_band: str | None = Field(default=None, min_length=1, max_length=64)
    source_ids: tuple[str, ...] = Field(default=(), max_length=32)
    published_from: date | None = None
    published_to: date | None = None
    market_scope: Literal["target", "all"] = "target"
    source_scope: Literal["core", "all"] = "core"

    @model_validator(mode="after")
    def validate_dates(self) -> "AnalyticsFilters":
        if self.published_from and self.published_to and self.published_from > self.published_to:
            raise ValueError("published_from must be on or before published_to")
        if any(not source_id.strip() for source_id in self.source_ids):
            raise ValueError("source_ids cannot contain blank values")
        if any(len(source_id) > 128 for source_id in self.source_ids):
            raise ValueError("source_ids values cannot exceed 128 characters")
        return self


class AnalyticsMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_name: str
    methodology_version: str = METHODOLOGY_VERSION
    data_version: str = "warehouse_snapshot"
    filters: AnalyticsFilters
    sample_size: int = Field(ge=0)
    source_count: int = Field(ge=0)
    published_from: date | None = None
    published_to: date | None = None


class SkillDemandRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    job_count: int = Field(ge=0)
    job_coverage: float | None = Field(default=None, ge=0, le=1)
    source_count: int = Field(ge=0)
    sample_size: int = Field(ge=0)


class PlatformBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    job_count: int = Field(ge=0)
    job_coverage: float | None = Field(default=None, ge=0, le=1)
    sample_size: int = Field(ge=0)


class PlatformBalancedDemandRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    pooled_coverage: float | None = Field(default=None, ge=0, le=1)
    platform_balanced_coverage: float | None = Field(default=None, ge=0, le=1)
    reliability_weighted_coverage: float | None = Field(default=None, ge=0, le=1)
    platform_breakdown: tuple[PlatformBreakdown, ...]
    source_count: int = Field(ge=0)
    sample_size: int = Field(ge=0)


class SalaryBySkillRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    median: float | None
    p25: float | None
    p75: float | None
    sample_size: int = Field(ge=0)
    salary_coverage: float | None = Field(default=None, ge=0, le=1)
    status: Literal["available", "unavailable"]


class SkillDimensionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension: Literal["role", "city", "experience"]
    dimension_value: str
    skill_id: str
    canonical_name: str
    category: str
    job_count: int = Field(ge=0)
    job_coverage: float | None = Field(default=None, ge=0, le=1)
    sample_size: int = Field(ge=0)


class SourceBiasRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension: Literal["role", "skill", "city", "experience"]
    source_id: str
    value: str
    job_count: int = Field(ge=0)
    job_coverage: float | None = Field(default=None, ge=0, le=1)
    sample_size: int = Field(ge=0)


class SkillDemandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    records: tuple[SkillDemandRecord, ...]


class PlatformBalancedDemandResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    records: tuple[PlatformBalancedDemandRecord, ...]
    eligible_source_count: int = Field(ge=0)
    ineligible_sources: tuple[SourceEligibilityEvidence, ...]
    source_eligibility: tuple[SourceEligibilityEvidence, ...]
    methodology_version: str = "platform-balanced-demand-2.0.0"
    guardrail_config_version: str
    reliability_weighting_status: Literal["not_implemented"] = "not_implemented"


class SalaryBySkillResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    records: tuple[SalaryBySkillRecord, ...]


class SkillDimensionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    records: tuple[SkillDimensionRecord, ...]


class SourceBiasResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    records: tuple[SourceBiasRecord, ...]


class AnalyticsRepository:
    """Read-only analytical queries over a completed SkillWorth DuckDB warehouse."""

    def __init__(self, database_path: Path, *, guardrail_config_path: Path | None = None) -> None:
        self._database_path = database_path.resolve()
        if not self._database_path.is_file():
            raise FileNotFoundError(f"Analytics warehouse does not exist: {self._database_path}")
        self._market_scope_available = _jobs_has_market_scope(self._database_path)
        self._guardrails = load_metric_guardrail_config(
            guardrail_config_path or DEFAULT_GUARDRAIL_CONFIG
        )
        self._default_core_source_ids = _configured_core_sources_present(
            self._database_path, self._guardrails
        )

    def skill_demand(self, filters: AnalyticsFilters | None = None) -> SkillDemandResult:
        filters = self._scope_filters(filters or AnalyticsFilters())
        rows, metadata = self._run("skill_demand.sql", "skill_demand", filters, source_filter_references=1)
        records = tuple(SkillDemandRecord(**row) for row in rows)
        return SkillDemandResult(metadata=metadata, records=records)

    def platform_balanced_demand(self, filters: AnalyticsFilters | None = None) -> PlatformBalancedDemandResult:
        filters = filters or AnalyticsFilters()
        rows, metadata = self._run(
            "platform_balanced_demand.sql",
            "platform_balanced_demand",
            filters,
            source_filter_references=1,
        )
        eligibility = self._source_eligibility(filters)
        eligible_ids = {item.source_id for item in eligibility if item.eligible}
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            record = grouped.setdefault(
                row["skill_id"],
                {
                    "skill_id": row["skill_id"],
                    "canonical_name": row["canonical_name"],
                    "category": row["category"],
                    "pooled_coverage": row["pooled_coverage"],
                    "platform_balanced_coverage": None,
                    "reliability_weighted_coverage": None,
                    "platform_breakdown": [],
                    "source_count": row["source_count"],
                    "sample_size": row["sample_size"],
                },
            )
            record["platform_breakdown"].append(
                PlatformBreakdown(
                    source_id=row["source_id"],
                    job_count=row["job_count"],
                    job_coverage=row["job_coverage"],
                    sample_size=row["source_sample_size"],
                )
            )
        required = self._guardrails.eligibility.required_eligible_sources
        if len(eligible_ids) >= required:
            for record in grouped.values():
                eligible_values = [
                    item.job_coverage
                    for item in record["platform_breakdown"]
                    if item.source_id in eligible_ids and item.job_coverage is not None
                ]
                record["platform_balanced_coverage"] = (
                    sum(eligible_values) / len(eligible_values) if eligible_values else None
                )
        records = tuple(PlatformBalancedDemandRecord(**record) for record in grouped.values())
        return PlatformBalancedDemandResult(
            metadata=metadata,
            records=records,
            eligible_source_count=len(eligible_ids),
            ineligible_sources=tuple(item for item in eligibility if not item.eligible),
            source_eligibility=eligibility,
            guardrail_config_version=self._guardrails.version,
        )

    def _source_eligibility(self, filters: AnalyticsFilters) -> tuple[SourceEligibilityEvidence, ...]:
        target_filters = filters.model_copy(update={"market_scope": "target"})
        all_filters = filters.model_copy(update={"market_scope": "all"})
        target_jobs, target_parameters = _filtered_jobs(target_filters, self._market_scope_available)
        all_jobs, all_parameters = _filtered_jobs(all_filters, self._market_scope_available)
        sql = f"""
        WITH target_jobs AS ({target_jobs}), all_jobs AS ({all_jobs}),
        target_source AS (
          SELECT DISTINCT m.source_id, m.silver_job_id, m.canonical_job_id
          FROM job_source_map m JOIN target_jobs t USING (canonical_job_id)
        ), all_source AS (
          SELECT DISTINCT m.source_id, m.silver_job_id
          FROM job_source_map m JOIN all_jobs a USING (canonical_job_id)
        ), target_stats AS (
          SELECT ts.source_id,
            count(DISTINCT ts.silver_job_id) target_sample_size,
            count(DISTINCT CASE WHEN js.silver_job_id IS NOT NULL THEN ts.silver_job_id END) skilled_count,
            max(t.published_at) latest_posted_at
          FROM target_source ts JOIN target_jobs t USING (canonical_job_id)
          LEFT JOIN job_skills js USING (silver_job_id)
          GROUP BY ts.source_id
        ), all_stats AS (
          SELECT source_id, count(DISTINCT silver_job_id) all_sample_size
          FROM all_source GROUP BY source_id
        )
        SELECT coalesce(a.source_id, t.source_id) source_id,
          coalesce(t.target_sample_size, 0) target_sample_size,
          coalesce(a.all_sample_size, 0) all_sample_size,
          coalesce(t.skilled_count, 0) skilled_count,
          t.latest_posted_at
        FROM all_stats a FULL OUTER JOIN target_stats t USING (source_id)
        ORDER BY source_id
        """
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            rows = _fetch_rows(connection, sql, target_parameters + all_parameters)
        finally:
            connection.close()
        as_of = filters.published_to or date.today()
        return tuple(
            evaluate_source_eligibility(
                source_id=row["source_id"],
                source_role=self._guardrails.source_role(row["source_id"]),
                target_sample_size=row["target_sample_size"],
                all_sample_size=row["all_sample_size"],
                skilled_target_sample_size=row["skilled_count"],
                latest_posted_at=row["latest_posted_at"],
                as_of_date=as_of,
                config=self._guardrails.eligibility,
            )
            for row in rows
        )

    def salary_by_skill(self, filters: AnalyticsFilters | None = None) -> SalaryBySkillResult:
        filters = self._scope_filters(filters or AnalyticsFilters())
        rows, metadata = self._run("salary_by_skill.sql", "salary_by_skill", filters, source_filter_references=1)
        records: list[SalaryBySkillRecord] = []
        for row in rows:
            payload = dict(row)
            if payload["sample_size"] == 0:
                payload["salary_coverage"] = None
                payload["status"] = "unavailable"
            else:
                payload["status"] = "available"
            records.append(SalaryBySkillRecord(**payload))
        return SalaryBySkillResult(metadata=metadata, records=tuple(records))

    def skill_by_role(self, filters: AnalyticsFilters | None = None) -> SkillDimensionResult:
        return self._skill_by_dimension("role", "role_id", filters)

    def skill_by_city(self, filters: AnalyticsFilters | None = None) -> SkillDimensionResult:
        return self._skill_by_dimension("city", "city_code", filters)

    def skill_by_experience(self, filters: AnalyticsFilters | None = None) -> SkillDimensionResult:
        return self._skill_by_dimension("experience", "experience_band", filters)

    def source_bias_analysis(self, filters: AnalyticsFilters | None = None) -> SourceBiasResult:
        filters = (filters or AnalyticsFilters()).model_copy(update={"source_scope": "all"})
        rows, metadata = self._run("source_bias.sql", "source_bias_analysis", filters, source_filter_references=1)
        return SourceBiasResult(metadata=metadata, records=tuple(SourceBiasRecord(**row) for row in rows))

    def _skill_by_dimension(
        self,
        dimension: Literal["role", "city", "experience"],
        column: Literal["role_id", "city_code", "experience_band"],
        filters: AnalyticsFilters | None,
    ) -> SkillDimensionResult:
        filters = self._scope_filters(filters or AnalyticsFilters())
        rows, metadata = self._run(
            "skill_by_dimension.sql",
            f"skill_by_{dimension}",
            filters,
            source_filter_references=1,
            dimension=dimension,
            dimension_column=column,
        )
        return SkillDimensionResult(metadata=metadata, records=tuple(SkillDimensionRecord(**row) for row in rows))

    def _scope_filters(self, filters: AnalyticsFilters) -> AnalyticsFilters:
        if filters.source_scope == "all" or filters.source_ids or not self._default_core_source_ids:
            return filters
        return filters.model_copy(update={"source_ids": self._default_core_source_ids})

    def _run(
        self,
        filename: str,
        metric_name: str,
        filters: AnalyticsFilters,
        *,
        source_filter_references: int = 0,
        **template_values: str,
    ) -> tuple[list[dict[str, Any]], AnalyticsMetadata]:
        filtered_jobs, parameters = _filtered_jobs(filters, self._market_scope_available)
        source_filter, source_parameters = _source_filter(filters, "mapping")
        sql = _sql_text(filename).format(
            filtered_jobs=filtered_jobs,
            source_filter=source_filter,
            **template_values,
        )
        all_parameters = parameters + source_parameters * source_filter_references
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            rows = _fetch_rows(connection, sql, all_parameters)
            metadata = _metadata(
                connection,
                filters,
                metric_name,
                market_scope_available=self._market_scope_available,
            )
        finally:
            connection.close()
        return rows, metadata


def _sql_text(filename: str) -> str:
    path = SQL_DIRECTORY / filename
    if not path.is_file():
        raise FileNotFoundError(f"Analytics SQL file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def _filtered_jobs(
    filters: AnalyticsFilters, market_scope_available: bool = True
) -> tuple[str, list[object]]:
    predicates = ["1 = 1"]
    parameters: list[object] = []
    if filters.market_scope == "target" and market_scope_available:
        predicates.append("jobs.market_scope = 'target'")
    for column, value in (
        ("role_id", filters.role_id),
        ("city_code", filters.city_code),
        ("experience_band", filters.experience_band),
        ("education_band", filters.education_band),
    ):
        if value is not None:
            predicates.append(f"jobs.{column} = ?")
            parameters.append(value)
    if filters.published_from is not None:
        predicates.append("jobs.published_at >= ?")
        parameters.append(filters.published_from)
    if filters.published_to is not None:
        predicates.append("jobs.published_at <= ?")
        parameters.append(filters.published_to)
    if filters.source_ids:
        placeholders = ", ".join("?" for _ in filters.source_ids)
        predicates.append(
            "EXISTS (SELECT 1 FROM job_source_map AS source_filter "
            "WHERE source_filter.canonical_job_id = jobs.canonical_job_id "
            f"AND source_filter.source_id IN ({placeholders}))"
        )
        parameters.extend(filters.source_ids)
    return "SELECT jobs.* FROM jobs WHERE " + " AND ".join(predicates), parameters


def _source_filter(filters: AnalyticsFilters, alias: str) -> tuple[str, list[object]]:
    if not filters.source_ids:
        return "TRUE", []
    placeholders = ", ".join("?" for _ in filters.source_ids)
    return f"{alias}.source_id IN ({placeholders})", list(filters.source_ids)


def _fetch_rows(connection: duckdb.DuckDBPyConnection, sql: str, parameters: list[object]) -> list[dict[str, Any]]:
    cursor = connection.execute(sql, parameters)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _metadata(
    connection: duckdb.DuckDBPyConnection,
    filters: AnalyticsFilters,
    metric_name: str,
    *,
    market_scope_available: bool = True,
) -> AnalyticsMetadata:
    filtered_jobs, parameters = _filtered_jobs(filters, market_scope_available)
    source_filter, source_parameters = _source_filter(filters, "mapping")
    row = _fetch_rows(
        connection,
        _sql_text("metadata.sql").format(filtered_jobs=filtered_jobs, source_filter=source_filter),
        parameters + source_parameters,
    )[0]
    return AnalyticsMetadata(metric_name=metric_name, filters=filters, **row)


def _jobs_has_market_scope(database_path: Path) -> bool:
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        columns = connection.execute("SELECT name FROM pragma_table_info('jobs')").fetchall()
    finally:
        connection.close()
    return any(name == "market_scope" for (name,) in columns)


def _configured_core_sources_present(
    database_path: Path, config: MetricGuardrailConfig
) -> tuple[str, ...]:
    allowed = {
        source_id for source_id, role in config.source_roles.items()
        if role in {"core_market", "supplementary_market"}
    }
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        present = {row[0] for row in connection.execute("SELECT DISTINCT source_id FROM job_source_map").fetchall()}
    finally:
        connection.close()
    return tuple(sorted(allowed & present))
