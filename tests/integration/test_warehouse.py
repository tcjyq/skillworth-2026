from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import pytest

from app.warehouse import WarehouseDataQualityError, build_warehouse


def _write_inputs(base: Path) -> dict[str, Path]:
    paths = {
        "canonical_jobs": base / "canonical_jobs.parquet",
        "job_source_map": base / "job_source_map.parquet",
        "skills": base / "skills.parquet",
        "job_skills": base / "job_skills.parquet",
    }
    pl.DataFrame(
        {
            "canonical_job_id": ["job-1", "job-2", "job-3"],
            "canonical_silver_job_id": ["silver-1", "silver-3", "silver-4"],
            "company_name_normalized": ["示例科技", "示例科技", "另一科技"],
            "job_title_normalized": ["数据分析师", "后端工程师", "数据分析师"],
            "role_id": ["data_analyst", "backend_engineer", "data_analyst"],
            "city_code": ["CN-110000", "CN-110000", "CN-310000"],
            "experience_band": ["mid", "senior", "entry"],
            "education_band": ["bachelor", "master", "bachelor"],
            "published_at": ["2026-08-01", "2026-08-15", "2026-09-01"],
            "salary_mid_monthly": [20000.0, 30000.0, None],
            "salary_parse_status": ["parsed_monthly", "parsed_monthly", "unparseable"],
            "group_size": [2, 1, 1],
            "deduplication_status": ["merged", "unique", "unique"],
            "canonicalization_method": ["level_1_exact", "unique", "unique"],
            "deduplication_rule_version": ["1.0.0"] * 3,
        }
    ).write_parquet(paths["canonical_jobs"])
    pl.DataFrame(
        {
            "canonical_job_id": ["job-1", "job-1", "job-2", "job-3"],
            "silver_job_id": ["silver-1", "silver-2", "silver-3", "silver-4"],
            "source_record_id": ["record-1", "record-2", "record-3", "record-4"],
            "source_id": ["source_a", "source_b", "source_a", "source_b"],
            "source_job_id": ["native-1", "native-2", "native-3", "native-4"],
            "source_url": ["https://a.test/1", "https://b.test/2", "https://a.test/3", "https://b.test/4"],
            "observed_at": ["2026-08-08T08:00:00+08:00"] * 4,
            "match_method": ["unique", "level_1_exact", "unique", "unique"],
            "match_score": [None, 100.0, None, None],
            "match_reason": ["unique", "exact", "unique", "unique"],
            "deduplication_rule_version": ["1.0.0"] * 4,
        }
    ).write_parquet(paths["job_source_map"])
    pl.DataFrame(
        {
            "skill_id": ["programming_python", "database_sql", "programming_java"],
            "canonical_name": ["Python", "SQL", "Java"],
            "category": ["programming", "database", "programming"],
            "aliases": [[], [], []],
            "learning_hours_min": [80, 40, 100],
            "learning_hours_expected": [160, 100, 220],
            "learning_hours_max": [320, 220, 420],
            "learning_cost_source": ["fixture"] * 3,
            "notes": ["fixture"] * 3,
            "skill_type": ["programming_language", "database", "programming_language"],
            "skillworth_eligibility": ["main"] * 3,
            "skillworth_reason": ["specific"] * 3,
            "taxonomy_version": ["1.0.0"] * 3,
        }
    ).write_parquet(paths["skills"])
    pl.DataFrame(
        {
            "silver_job_id": ["silver-1", "silver-1", "silver-2", "silver-3", "silver-4"],
            "skill_id": ["programming_python", "database_sql", "programming_python", "programming_java", "programming_python"],
            "canonical_skill": ["Python", "SQL", "Python", "Java", "Python"],
            "matched_text": ["Python", "SQL", "Python", "Java", "Python"],
            "extraction_method": ["rule_canonical"] * 5,
            "confidence": [0.98] * 5,
            "taxonomy_version": ["1.0.0"] * 5,
        }
    ).write_parquet(paths["job_skills"])
    return paths


def test_build_warehouse_creates_core_tables_views_data_tests_and_benchmark(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    benchmark_path = tmp_path / "benchmark.json"

    report = build_warehouse(database_path=database_path, benchmark_path=benchmark_path, **inputs)

    assert report.jobs_row_count == 3
    assert report.job_skills_row_count == 5
    assert report.data_test_count > 0
    assert benchmark_path.exists()
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        tables = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}
        assert {"jobs", "companies", "skills", "job_skills", "sources", "job_source_map"} <= tables
        assert connection.execute("SELECT job_count FROM skill_demand WHERE skill_id = 'programming_python'").fetchone() == (2,)
        assert connection.execute("SELECT job_coverage_rate FROM skill_demand WHERE skill_id = 'programming_python'").fetchone() == (2 / 3,)
        assert connection.execute("SELECT COUNT(*) FROM monthly_skill_demand").fetchone()[0] >= 3
        assert connection.execute("SELECT COUNT(*) FROM salary_distribution").fetchone()[0] == 2
    finally:
        connection.close()


def test_build_warehouse_is_idempotent_for_the_same_input_snapshot(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    first = build_warehouse(database_path=database_path, benchmark_path=tmp_path / "first.json", **inputs)
    second = build_warehouse(database_path=database_path, benchmark_path=tmp_path / "second.json", **inputs)

    assert first.model_dump() == second.model_dump()


def test_build_warehouse_backfills_missing_education_for_pre_phase_six_gold_snapshot(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path)
    canonical = pl.read_parquet(inputs["canonical_jobs"]).drop("education_band")
    canonical.write_parquet(inputs["canonical_jobs"])
    database_path = tmp_path / "warehouse.duckdb"

    build_warehouse(database_path=database_path, benchmark_path=tmp_path / "benchmark.json", **inputs)

    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        assert connection.execute("SELECT count(*) FROM jobs WHERE education_band IS NULL").fetchone() == (3,)
    finally:
        connection.close()


def test_build_warehouse_fails_data_tests_for_duplicate_canonical_job_ids(tmp_path: Path) -> None:
    inputs = _write_inputs(tmp_path)
    jobs = pl.read_parquet(inputs["canonical_jobs"])
    pl.concat([jobs, jobs.head(1)]).write_parquet(inputs["canonical_jobs"])

    with pytest.raises(WarehouseDataQualityError, match="jobs_canonical_job_id_unique"):
        build_warehouse(
            database_path=tmp_path / "warehouse.duckdb",
            benchmark_path=tmp_path / "benchmark.json",
            **inputs,
        )
