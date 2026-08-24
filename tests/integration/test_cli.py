from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import polars as pl


ROOT = Path(__file__).resolve().parents[2]


def test_build_silver_cli_runs_end_to_end(tmp_path: Path) -> None:
    output_path = tmp_path / "silver.parquet"
    quality_path = tmp_path / "quality.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli",
            "build-silver",
            "--input",
            str(ROOT / "data/demo/bronze_jobs.csv"),
            "--output",
            str(output_path),
            "--quality-report",
            str(quality_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert output_path.exists()
    assert quality_path.exists()
    assert pl.read_parquet(output_path).height == 8
    assert '"raw_row_count": 8' in completed.stdout


def test_extract_skills_cli_runs_end_to_end(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-1"],
            "job_title_raw": ["后端开发工程师"],
            "job_description_raw": ["Python, FastAPI, PostgreSQL and Docker"],
            "record_status": ["valid"],
        }
    ).write_parquet(silver_path)
    skills_path = tmp_path / "skills.parquet"
    relations_path = tmp_path / "job_skills.parquet"
    benchmark_path = tmp_path / "benchmark.json"

    completed = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "extract-skills",
            "--input", str(silver_path),
            "--skills-output", str(skills_path),
            "--job-skills-output", str(relations_path),
            "--benchmark-report", str(benchmark_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert skills_path.exists() and relations_path.exists() and benchmark_path.exists()
    assert "\"precision\"" in completed.stdout


def test_deduplicate_cli_runs_end_to_end(tmp_path: Path) -> None:
    input_path = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-a", "job-b"],
            "source_record_id": ["record-a", "record-b"],
            "source_id": ["platform_a", "platform_b"],
            "company_name_normalized": ["示例科技有限公司", "示例科技有限公司"],
            "job_title_normalized": ["数据分析师", "数据分析师"],
            "city_code": ["CN-110000", "CN-110000"],
            "role_id": ["data_analyst", "data_analyst"],
            "experience_band": ["mid", "mid"],
            "job_description_raw": ["指标建设", "指标建设"],
            "record_status": ["valid", "valid"],
        }
    ).write_parquet(input_path)
    canonical_path = tmp_path / "canonical_jobs.parquet"
    map_path = tmp_path / "job_source_map.parquet"
    report_path = tmp_path / "dedup_report.json"

    completed = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "deduplicate",
            "--input", str(input_path),
            "--canonical-output", str(canonical_path),
            "--source-map-output", str(map_path),
            "--report", str(report_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert canonical_path.exists() and map_path.exists() and report_path.exists()
    assert '"canonical_job_count": 1' in completed.stdout


def test_build_warehouse_cli_runs_end_to_end(tmp_path: Path) -> None:
    from tests.integration.test_warehouse import _write_inputs

    inputs = _write_inputs(tmp_path)
    database_path = tmp_path / "warehouse.duckdb"
    benchmark_path = tmp_path / "benchmark.json"
    completed = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "build-warehouse",
            "--database", str(database_path),
            "--canonical-jobs", str(inputs["canonical_jobs"]),
            "--job-source-map", str(inputs["job_source_map"]),
            "--skills", str(inputs["skills"]),
            "--job-skills", str(inputs["job_skills"]),
            "--benchmark-report", str(benchmark_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert database_path.exists() and benchmark_path.exists()
    assert '"jobs_row_count": 3' in completed.stdout


def test_source_cli_lists_status_and_imports_through_warehouse(tmp_path: Path) -> None:
    source_config = ROOT / "data/reference/sources.v1.yml"
    data_root = tmp_path / "data"
    export = tmp_path / "jobs.csv"
    pl.DataFrame(
        {
            "job_id": ["cli-1"],
            "company_name": ["示例科技有限公司"],
            "job_title": ["后端工程师"],
            "city": ["上海"],
            "education": ["本科"],
            "experience": ["3-5年"],
            "salary": ["20-30K·13薪"],
            "published_at": ["2026-08-02"],
            "job_description": ["Python FastAPI PostgreSQL Docker"],
        }
    ).write_csv(export)

    listed = subprocess.run(
        [sys.executable, "-m", "app.cli", "list-sources", "--sources-config", str(source_config)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert listed.returncode == 0, listed.stderr
    assert '"source_id": "boss"' in listed.stdout
    assert '"enabled": false' in listed.stdout

    imported = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "import-source", "boss", str(export),
            "--sources-config", str(source_config), "--data-root", str(data_root),
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert imported.returncode == 0, imported.stderr
    assert '"pipeline_stage": "warehouse"' in imported.stdout

    status = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "source-status",
            "--sources-config", str(source_config), "--data-root", str(data_root),
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
    )
    assert status.returncode == 0, status.stderr
    assert '"record_count": 1' in status.stdout


def test_benchmark_all_cli_reports_insufficient_data_without_fake_metrics(tmp_path: Path) -> None:
    silver = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-1"],
            "company_name_normalized": ["example"],
            "job_title_normalized": ["data analyst"],
            "job_title_raw": ["Data Analyst"],
            "city_code": ["CN-110000"],
            "city_raw": ["Beijing"],
            "role_id": ["data_analyst"],
            "experience_band": ["mid"],
            "job_description_raw": ["SQL"],
        }
    ).write_parquet(silver)
    report_dir = tmp_path / "reports"

    completed = subprocess.run(
        [
            sys.executable, "-m", "app.cli", "benchmark-all",
            "--silver", str(silver), "--report-dir", str(report_dir),
        ],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "INSUFFICIENT BENCHMARK DATA" in completed.stdout
    assert {path.name for path in report_dir.glob("*.json")} == {
        "roles.json", "skills.json", "dedup.json"
    }
