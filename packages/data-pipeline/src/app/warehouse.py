from __future__ import annotations

import json
import logging
from pathlib import Path
from time import perf_counter

import duckdb
import polars as pl
from pydantic import BaseModel, ConfigDict, Field


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SQL_DIRECTORY = REPOSITORY_ROOT / "backend/app/sql"
LOGGER = logging.getLogger(__name__)

_INPUT_CONTRACTS = {
    "canonical_jobs": {
        "canonical_job_id", "canonical_silver_job_id", "company_name_normalized",
        "job_title_normalized", "role_id", "city_code", "experience_band", "education_band", "published_at",
        "salary_mid_monthly", "salary_parse_status", "group_size", "deduplication_status",
        "canonicalization_method", "deduplication_rule_version", "title_source_silver_job_id",
        "description_source_silver_job_id", "job_title_raw", "job_description_raw", "first_posted_at",
        "first_seen_at", "last_seen_at", "salary_observations", "canonical_salary",
        "salary_source_count", "salary_conflict_flag", "salary_months", "canonical_merge_version",
        "market_scope", "market_scope_method", "market_scope_version",
    },
    "job_source_map": {
        "canonical_job_id", "silver_job_id", "source_record_id", "source_id", "source_job_id",
        "source_url", "observed_at", "match_method", "match_score", "match_reason",
        "deduplication_rule_version", "upstream_source", "upstream_external_id",
        "source_company_slug", "api_accessed_at", "source_payload_sha256",
    },
    "skills": {
        "skill_id", "canonical_name", "category", "aliases", "learning_hours_min",
        "learning_hours_expected", "learning_hours_max", "learning_cost_source", "notes",
        "skill_type", "skillworth_eligibility", "skillworth_reason", "taxonomy_version",
    },
    "job_skills": {
        "silver_job_id", "skill_id", "canonical_skill", "matched_text", "extraction_method",
        "confidence", "taxonomy_version",
    },
}
_OPTIONAL_INPUT_COLUMNS: dict[str, dict[str, str]] = {
    "canonical_jobs": {
        "education_band": "VARCHAR",
        "title_source_silver_job_id": "VARCHAR",
        "description_source_silver_job_id": "VARCHAR",
        "job_title_raw": "VARCHAR",
        "job_description_raw": "VARCHAR",
        "first_posted_at": "VARCHAR",
        "first_seen_at": "VARCHAR",
        "last_seen_at": "VARCHAR",
        "salary_observations": "STRUCT(source VARCHAR, raw_salary VARCHAR, normalized_salary DOUBLE, currency VARCHAR, native_min_monthly DOUBLE, observed_at VARCHAR)[]",
        "canonical_salary": "DOUBLE",
        "salary_source_count": "BIGINT",
        "salary_conflict_flag": "BOOLEAN",
        "salary_months": "BIGINT",
        "canonical_merge_version": "VARCHAR",
        "market_scope": "VARCHAR",
        "market_scope_method": "VARCHAR",
        "market_scope_version": "VARCHAR",
    },
    "job_source_map": {
        "upstream_source": "VARCHAR",
        "upstream_external_id": "VARCHAR",
        "source_company_slug": "VARCHAR",
        "api_accessed_at": "VARCHAR",
        "source_payload_sha256": "VARCHAR",
    },
}


class WarehouseError(RuntimeError):
    pass


class WarehouseDataQualityError(WarehouseError):
    pass


class WarehouseBuildReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    jobs_row_count: int = Field(ge=0)
    companies_row_count: int = Field(ge=0)
    skills_row_count: int = Field(ge=0)
    job_skills_row_count: int = Field(ge=0)
    sources_row_count: int = Field(ge=0)
    job_source_map_row_count: int = Field(ge=0)
    data_test_count: int = Field(ge=0)
    benchmark_query_count: int = Field(ge=0)


def _validate_parquet(path: Path, contract_name: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Warehouse input does not exist: {resolved}")
    columns = set(pl.read_parquet_schema(resolved).names())
    missing = _INPUT_CONTRACTS[contract_name] - columns - _OPTIONAL_INPUT_COLUMNS.get(contract_name, {}).keys()
    if missing:
        raise WarehouseError(f"Warehouse input {contract_name} is missing columns: {sorted(missing)}")
    return resolved


def _sql_text(filename: str) -> str:
    path = SQL_DIRECTORY / filename
    if not path.is_file():
        raise WarehouseError(f"Warehouse SQL file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def _register_parquet_view(
    connection: duckdb.DuckDBPyConnection,
    name: str,
    path: Path,
    *,
    missing_optional_columns: dict[str, str] | None = None,
) -> None:
    escaped_path = str(path).replace("'", "''")
    optional_projection = "".join(
        f", NULL::{sql_type} AS {column}"
        for column, sql_type in sorted((missing_optional_columns or {}).items())
    )
    connection.execute(
        f"CREATE OR REPLACE TEMP VIEW {name} AS "
        f"SELECT *{optional_projection} FROM read_parquet('{escaped_path}')"
    )


def _run_data_tests(connection: duckdb.DuckDBPyConnection) -> int:
    results = connection.execute(_sql_text("03_data_tests.sql")).fetchall()
    violations = {str(name): int(count) for name, count in results if count}
    if violations:
        detail = ", ".join(f"{name}={count}" for name, count in sorted(violations.items()))
        raise WarehouseDataQualityError(f"Warehouse data tests failed: {detail}")
    return len(results)


def _run_benchmarks(connection: duckdb.DuckDBPyConnection, benchmark_path: Path) -> int:
    measurements: list[dict[str, object]] = []
    for filename in ("benchmark_skill_demand.sql", "benchmark_salary_distribution.sql"):
        started = perf_counter()
        rows = connection.execute(_sql_text(filename)).fetchall()
        measurements.append(
            {
                "query_name": filename.removesuffix(".sql"),
                "elapsed_ms": round((perf_counter() - started) * 1000, 3),
                "row_count": len(rows),
            }
        )
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_path.write_text(json.dumps({"queries": measurements}, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(measurements)


def build_warehouse(
    *,
    database_path: Path,
    canonical_jobs: Path,
    job_source_map: Path,
    skills: Path,
    job_skills: Path,
    benchmark_path: Path,
) -> WarehouseBuildReport:
    inputs = {
        "canonical_jobs": _validate_parquet(canonical_jobs, "canonical_jobs"),
        "job_source_map": _validate_parquet(job_source_map, "job_source_map"),
        "skills": _validate_parquet(skills, "skills"),
        "job_skills": _validate_parquet(job_skills, "job_skills"),
    }
    database_path = database_path.resolve()
    benchmark_path = benchmark_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        for name, path in inputs.items():
            columns = set(pl.read_parquet_schema(path).names())
            _register_parquet_view(
                connection,
                f"input_{name}",
                path,
                missing_optional_columns={
                    column: sql_type
                    for column, sql_type in _OPTIONAL_INPUT_COLUMNS.get(name, {}).items()
                    if column not in columns
                },
            )
        connection.begin()
        for filename in ("00_drop_analysis_views.sql", "01_core_tables.sql", "02_analysis_views.sql"):
            LOGGER.info("warehouse_sql_start file=%s", filename)
            connection.execute(_sql_text(filename))
        data_test_count = _run_data_tests(connection)
        connection.commit()
        benchmark_query_count = _run_benchmarks(connection, benchmark_path)
        counts = {
            name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
            for name in ("jobs", "companies", "skills", "job_skills", "sources", "job_source_map")
        }
        LOGGER.info("warehouse_build_complete database=%s jobs=%s", database_path, counts["jobs"])
        return WarehouseBuildReport(
            jobs_row_count=counts["jobs"],
            companies_row_count=counts["companies"],
            skills_row_count=counts["skills"],
            job_skills_row_count=counts["job_skills"],
            sources_row_count=counts["sources"],
            job_source_map_row_count=counts["job_source_map"],
            data_test_count=data_test_count,
            benchmark_query_count=benchmark_query_count,
        )
    except Exception:
        try:
            connection.rollback()
        except duckdb.Error:
            pass
        LOGGER.exception("warehouse_build_failed database=%s", database_path)
        raise
    finally:
        connection.close()
