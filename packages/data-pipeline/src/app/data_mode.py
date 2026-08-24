from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import duckdb
import polars as pl
from pydantic import BaseModel, ConfigDict, Field
from skillworth_analytics import AnalyticsFilters, AnalyticsRepository

from app.source_models import SourceImportResult


Availability = Literal["available", "unavailable"]
DataMode = Literal["demo", "real"]


class ReportMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Availability
    value: Any = None
    reason: str | None = None
    available_rows: int | None = Field(default=None, ge=0)
    sample_size: int | None = Field(default=None, ge=0)


class DatasetModeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    mode: DataMode
    source_id: str
    ingestion_run_id: str
    generated_at: datetime
    raw_rows: int = Field(ge=0)
    in_scope_rows: int = Field(ge=0)
    excluded_out_of_scope_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    canonical_rows: int = Field(ge=0)
    date_range: ReportMetric
    salary_coverage: ReportMetric
    skill_coverage: ReportMetric
    role_distribution: ReportMetric
    city_distribution: ReportMetric
    source_distribution: ReportMetric
    analytics_check: ReportMetric
    logic_fingerprint: dict[str, Any]
    limitations: tuple[str, ...]


class ConsistencyCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    demo_value: Any
    real_value: Any
    matches: bool


class ModeComparisonReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    business_logic_consistent: bool
    consistency_checks: tuple[ConsistencyCheck, ...]
    demo: DatasetModeReport
    real: DatasetModeReport


def _write_json(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)


def _distribution(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    *,
    reason: str,
    sample_size: int,
) -> ReportMetric:
    rows = connection.execute(sql).fetchall()
    values = {str(key): int(count) for key, count in rows if key is not None}
    if not values:
        return ReportMetric(status="unavailable", reason=reason, sample_size=sample_size)
    return ReportMetric(
        status="available",
        value=values,
        available_rows=sum(values.values()),
        sample_size=sample_size,
    )


def _unique_values(frame: pl.DataFrame, column: str) -> list[str]:
    if column not in frame.columns:
        return []
    return sorted(str(value) for value in frame[column].drop_nulls().unique().to_list())


def build_dataset_mode_report(
    *,
    mode: DataMode,
    imported: SourceImportResult,
    output_path: Path,
) -> DatasetModeReport:
    silver = pl.read_parquet(imported.silver_path)
    skills = pl.read_parquet(imported.skills_path)
    valid_rows = silver.filter(pl.col("record_status") == "valid").height
    analytics = AnalyticsRepository(imported.warehouse_path).skill_demand(
        AnalyticsFilters(market_scope="all")
    )
    manifests = []
    manifest_dir = imported.bronze_path.parent / "manifests"
    if manifest_dir.is_dir():
        manifests = [json.loads(path.read_text(encoding="utf-8")) for path in manifest_dir.glob("*.json")]
    raw_rows = sum(int(item.get("raw_record_count", 0)) for item in manifests) if manifests else imported.raw_record_count
    in_scope_rows = sum(int(item.get("record_count", 0)) for item in manifests) if manifests else imported.record_count
    rejected_rows = sum(int(item.get("rejected_record_count", 0)) for item in manifests) if manifests else imported.rejected_record_count
    source_ids = sorted({str(item.get("source_id")) for item in manifests if item.get("source_id")})

    connection = duckdb.connect(str(imported.warehouse_path), read_only=True)
    try:
        canonical_rows = int(connection.execute("SELECT count(*) FROM jobs").fetchone()[0])
        published_from, published_to = connection.execute(
            "SELECT min(published_at), max(published_at) FROM jobs WHERE published_at IS NOT NULL"
        ).fetchone()
        published_rows = int(
            connection.execute("SELECT count(*) FROM jobs WHERE published_at IS NOT NULL").fetchone()[0]
        )
        salary_rows = int(
            connection.execute("SELECT count(*) FROM jobs WHERE salary_mid_monthly IS NOT NULL").fetchone()[0]
        )
        skilled_rows = int(
            connection.execute("SELECT count(DISTINCT canonical_job_id) FROM job_skills").fetchone()[0]
        )
        role_distribution = _distribution(
            connection,
            "SELECT role_id, count(*) FROM jobs WHERE role_id IS NOT NULL GROUP BY role_id ORDER BY role_id",
            reason="source_has_no_role_values",
            sample_size=canonical_rows,
        )
        city_distribution = _distribution(
            connection,
            "SELECT city_code, count(*) FROM jobs WHERE city_code IS NOT NULL GROUP BY city_code ORDER BY city_code",
            reason="source_has_no_parseable_city_values",
            sample_size=canonical_rows,
        )
        source_distribution = _distribution(
            connection,
            "SELECT source_id, count(DISTINCT canonical_job_id) FROM job_source_map "
            "GROUP BY source_id ORDER BY source_id",
            reason="source_provenance_is_unavailable",
            sample_size=canonical_rows,
        )
        warehouse_objects = [
            f"{name}:{kind}"
            for name, kind in connection.execute(
                "SELECT table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = 'main' ORDER BY table_name"
            ).fetchall()
        ]
    finally:
        connection.close()

    date_range = (
        ReportMetric(
            status="available",
            value={"from": published_from.isoformat(), "to": published_to.isoformat()},
            available_rows=published_rows,
            sample_size=canonical_rows,
        )
        if published_from is not None and published_to is not None
        else ReportMetric(
            status="unavailable",
            reason="source_has_no_parseable_published_dates",
            sample_size=canonical_rows,
        )
    )
    salary_coverage = (
        ReportMetric(
            status="available",
            value=salary_rows / canonical_rows,
            available_rows=salary_rows,
            sample_size=canonical_rows,
        )
        if canonical_rows and salary_rows
        else ReportMetric(
            status="unavailable",
            reason="source_has_no_parseable_salary_values",
            available_rows=salary_rows,
            sample_size=canonical_rows,
        )
    )
    skill_coverage = (
        ReportMetric(
            status="available",
            value=skilled_rows / canonical_rows,
            available_rows=skilled_rows,
            sample_size=canonical_rows,
        )
        if canonical_rows
        else ReportMetric(status="unavailable", reason="no_canonical_jobs", sample_size=0)
    )
    logic_fingerprint = {
        "pipeline_version": _unique_values(silver, "pipeline_version"),
        "role_taxonomy_version": _unique_values(silver, "role_taxonomy_version"),
        "city_taxonomy_version": _unique_values(silver, "city_taxonomy_version"),
        "skill_taxonomy_version": _unique_values(skills, "taxonomy_version"),
        "warehouse_objects": warehouse_objects,
        "analytics_methodology_version": analytics.metadata.methodology_version,
    }
    limitations = list(imported.connector_warnings)
    if salary_coverage.status == "unavailable":
        limitations.append("salary_metrics_unavailable")
    if analytics.metadata.source_count < 2:
        limitations.append("cross_source_metrics_unavailable_or_low_confidence")
    report = DatasetModeReport(
        mode=mode,
        source_id="multi_source:" + ",".join(source_ids) if len(source_ids) > 1 else imported.source_id,
        ingestion_run_id=imported.ingestion_run_id,
        generated_at=datetime.now(UTC),
        raw_rows=raw_rows,
        in_scope_rows=in_scope_rows,
        excluded_out_of_scope_rows=rejected_rows,
        valid_rows=valid_rows,
        canonical_rows=canonical_rows,
        date_range=date_range,
        salary_coverage=salary_coverage,
        skill_coverage=skill_coverage,
        role_distribution=role_distribution,
        city_distribution=city_distribution,
        source_distribution=source_distribution,
        analytics_check=ReportMetric(
            status="available",
            value={
                "methodology_version": analytics.metadata.methodology_version,
                "sample_size": analytics.metadata.sample_size,
                "source_count": analytics.metadata.source_count,
                "skill_record_count": len(analytics.records),
            },
            sample_size=analytics.metadata.sample_size,
        ),
        logic_fingerprint=logic_fingerprint,
        limitations=tuple(dict.fromkeys(limitations)),
    )
    _write_json(output_path, report)
    return report


def compare_mode_reports(
    demo: DatasetModeReport,
    real: DatasetModeReport,
    output_path: Path,
) -> ModeComparisonReport:
    keys = sorted(set(demo.logic_fingerprint) | set(real.logic_fingerprint))
    checks = tuple(
        ConsistencyCheck(
            name=key,
            demo_value=demo.logic_fingerprint.get(key),
            real_value=real.logic_fingerprint.get(key),
            matches=demo.logic_fingerprint.get(key) == real.logic_fingerprint.get(key),
        )
        for key in keys
    )
    comparison = ModeComparisonReport(
        generated_at=datetime.now(UTC),
        business_logic_consistent=all(check.matches for check in checks),
        consistency_checks=checks,
        demo=demo,
        real=real,
    )
    _write_json(output_path, comparison)
    return comparison
