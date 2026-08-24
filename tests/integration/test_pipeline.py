from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl

from app.pipeline import build_silver


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_silver_preserves_bronze_and_writes_parquet(tmp_path: Path) -> None:
    bronze_path = tmp_path / "bronze.parquet"
    silver_path = tmp_path / "silver.parquet"
    quality_path = tmp_path / "quality.json"
    pl.DataFrame(
        {
            "source_record_id": ["one", "two", "three"],
            "source_id": ["demo", "demo", "demo"],
            "source_job_id": ["native-one", "native-two", "native-three"],
            "source_url": ["https://example.test/one", "https://example.test/two", "https://example.test/three"],
            "observed_at": ["2026-08-08T08:00:00+08:00"] * 3,
            "ingestion_run_id": ["run-1", "run-1", "run-1"],
            "company_name": ["示例科技有限公司", "示例智能有限公司", None],
            "job_title": ["数据分析师", "算法工程师", None],
            "city": ["北京", "深圳市南山区", "未知城市"],
            "education": ["本科", "硕士", None],
            "experience": ["1-3年", "3-5年", None],
            "salary": ["15-25K", "30-50K·14薪", "30-20K"],
            "published_at": ["2026-08-01", "2026/08/02", "bad-date"],
            "job_description": ["SQL", "机器学习", None],
        }
    ).write_parquet(bronze_path)
    before = sha256(bronze_path)

    report = build_silver(
        input_path=bronze_path,
        output_path=silver_path,
        quality_report_path=quality_path,
        role_taxonomy_path=ROOT / "data/reference/role_taxonomy.v1.json",
        city_taxonomy_path=ROOT / "data/reference/city_taxonomy.v1.json",
    )

    assert sha256(bronze_path) == before
    assert silver_path.exists()
    silver = pl.read_parquet(silver_path)
    assert silver.height == 3
    assert silver["salary_raw"].to_list() == ["15-25K", "30-50K·14薪", "30-20K"]
    assert silver["source_job_id"].to_list() == ["native-one", "native-two", "native-three"]
    assert silver["source_url"].to_list()[0] == "https://example.test/one"
    assert silver["observed_at"].to_list()[0] == "2026-08-08T08:00:00+08:00"
    assert silver["role_id"].to_list() == ["data_analyst", "ai_engineer", "other"]
    assert silver["record_status"].to_list() == ["valid", "valid", "invalid"]
    assert report.raw_row_count == 3
    assert report.silver_row_count == 3
    assert report.salary_parse_rate == 2 / 3
    assert report.role_parse_rate == 2 / 3
    assert report.city_parse_rate == 2 / 3
    assert report.invalid_record_rate == 1 / 3
    persisted = json.loads(quality_path.read_text(encoding="utf-8"))
    assert persisted["raw_row_count"] == 3
    assert "missing_rate" in persisted


def test_silver_ids_remain_stable_when_new_bronze_rows_are_prepended(tmp_path: Path) -> None:
    common = {
        "source_id": "demo",
        "ingestion_run_id": "run-1",
        "company_name": "示例科技有限公司",
        "job_title": "数据分析师",
        "city": "北京",
        "education": "本科",
        "experience": "1-3年",
        "salary": "15-25K",
        "published_at": "2026-08-01",
        "job_description": "SQL",
    }
    original_rows = [
        {"source_record_id": "one", **common},
        {"source_record_id": "two", **common},
    ]
    prepended_rows = [
        {"source_record_id": "new", **common},
        *original_rows,
    ]
    first_input = tmp_path / "first.parquet"
    second_input = tmp_path / "second.parquet"
    pl.from_dicts(original_rows).write_parquet(first_input)
    pl.from_dicts(prepended_rows).write_parquet(second_input)

    outputs: list[pl.DataFrame] = []
    for label, input_path in (("first", first_input), ("second", second_input)):
        output_path = tmp_path / f"{label}-silver.parquet"
        build_silver(
            input_path=input_path,
            output_path=output_path,
            quality_report_path=tmp_path / f"{label}-quality.json",
            role_taxonomy_path=ROOT / "data/reference/role_taxonomy.v1.json",
            city_taxonomy_path=ROOT / "data/reference/city_taxonomy.v1.json",
        )
        outputs.append(pl.read_parquet(output_path))

    first_ids = dict(outputs[0].select("source_record_id", "silver_job_id").iter_rows())
    second_ids = dict(outputs[1].select("source_record_id", "silver_job_id").iter_rows())
    assert second_ids["one"] == first_ids["one"]
    assert second_ids["two"] == first_ids["two"]
