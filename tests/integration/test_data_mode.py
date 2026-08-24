from __future__ import annotations

from pathlib import Path

import polars as pl

from app.data_mode import build_dataset_mode_report, compare_mode_reports
from app.source_import import import_source


ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONFIG = ROOT / "data/reference/sources.v1.yml"


def _write_export(path: Path, *, salary: str | None) -> None:
    pl.DataFrame(
        {
            "job_id": ["native-1"],
            "company_name": ["示例科技有限公司"],
            "job_title": ["数据分析师"],
            "city": ["北京"],
            "education": ["本科"],
            "experience": ["1-3年"],
            "salary": [salary],
            "published_at": ["2024-05-01"],
            "job_description": ["负责 Python、SQL 和 Power BI 分析"],
        }
    ).write_csv(path)


def test_dataset_report_distinguishes_unavailable_from_zero(tmp_path: Path) -> None:
    artifact = tmp_path / "jobs.csv"
    _write_export(artifact, salary=None)
    imported = import_source(
        "boss",
        artifact,
        data_root=tmp_path / "mode",
        config_path=SOURCE_CONFIG,
    )

    report = build_dataset_mode_report(
        mode="real",
        imported=imported,
        output_path=tmp_path / "mode/report.json",
    )

    assert report.raw_rows == 1
    assert report.valid_rows == 1
    assert report.date_range.available_rows == report.canonical_rows
    assert report.salary_coverage.status == "unavailable"
    assert report.salary_coverage.value is None
    assert report.salary_coverage.available_rows == 0
    assert report.skill_coverage.status == "available"
    assert report.skill_coverage.value == 1.0
    assert report.role_distribution.value == {"data_analyst": 1}
    assert report.analytics_check.status == "available"
    assert report.logic_fingerprint["skill_taxonomy_version"] == ["1.1.0"]
    assert (tmp_path / "mode/report.json").exists()


def test_mode_comparison_checks_logic_fingerprint_not_metric_equality(tmp_path: Path) -> None:
    demo_artifact = tmp_path / "demo.csv"
    real_artifact = tmp_path / "real.csv"
    _write_export(demo_artifact, salary="15-25K")
    _write_export(real_artifact, salary=None)
    demo_import = import_source(
        "boss", demo_artifact, data_root=tmp_path / "demo", config_path=SOURCE_CONFIG
    )
    real_import = import_source(
        "zhilian", real_artifact, data_root=tmp_path / "real", config_path=SOURCE_CONFIG
    )
    demo = build_dataset_mode_report(
        mode="demo", imported=demo_import, output_path=tmp_path / "demo/report.json"
    )
    real = build_dataset_mode_report(
        mode="real", imported=real_import, output_path=tmp_path / "real/report.json"
    )

    comparison = compare_mode_reports(demo, real, tmp_path / "comparison.json")

    assert comparison.business_logic_consistent is True
    assert comparison.demo.salary_coverage.status == "available"
    assert comparison.real.salary_coverage.status == "unavailable"
    assert comparison.consistency_checks
