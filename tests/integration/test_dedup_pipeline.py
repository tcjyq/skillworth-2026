from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from app.dedup_pipeline import deduplicate_silver


ROOT = Path(__file__).resolve().parents[2]


def test_deduplicate_silver_writes_canonical_jobs_maps_and_report(tmp_path: Path) -> None:
    input_path = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-a", "job-b", "job-c"],
            "source_record_id": ["record-a", "record-b", "record-c"],
            "source_id": ["platform_a", "platform_b", "platform_b"],
            "source_job_id": ["native-a", "native-b", "native-c"],
            "source_url": ["https://a.test/1", "https://b.test/2", "https://b.test/3"],
            "observed_at": ["2026-08-08T08:00:00+08:00"] * 3,
            "company_name_normalized": ["示例科技有限公司"] * 3,
            "job_title_normalized": ["数据分析师", "数据分析师", "高级数据分析师"],
            "job_title_raw": ["数据分析师", "数据分析师", "高级数据分析师"],
            "city_code": ["CN-110000"] * 3,
            "city_raw": ["北京"] * 3,
            "role_id": ["data_analyst"] * 3,
            "experience_band": ["mid", "mid", "senior"],
            "education_band": ["bachelor"] * 3,
            "published_at": [date(2026, 8, 1), date(2026, 8, 1), date(2026, 8, 2)],
            "salary_mid_monthly": [20000.0, 20000.0, 28000.0],
            "salary_parse_status": ["parsed_monthly"] * 3,
            "job_description_raw": ["负责指标建设"] * 3,
            "record_status": ["valid"] * 3,
        }
    ).write_parquet(input_path)
    canonical_path = tmp_path / "canonical_jobs.parquet"
    map_path = tmp_path / "job_source_map.parquet"
    report_path = tmp_path / "dedup_report.json"

    report = deduplicate_silver(
        input_path=input_path,
        canonical_output_path=canonical_path,
        source_map_output_path=map_path,
        report_path=report_path,
    )

    assert report.canonical_job_count == 2
    assert report.dedup_rate == 1 / 3
    assert canonical_path.exists() and map_path.exists() and report_path.exists()
    source_map = pl.read_parquet(map_path)
    assert source_map.height == 3
    assert source_map["canonical_job_id"].n_unique() == 2
    assert set(source_map.columns) >= {
        "canonical_job_id", "silver_job_id", "source_id", "source_job_id", "source_url", "observed_at"
    }
    canonical = pl.read_parquet(canonical_path)
    assert {"education_band", "published_at", "salary_mid_monthly", "salary_parse_status"} <= set(canonical.columns)


def test_canonical_job_merges_fields_and_salary_observations(tmp_path: Path) -> None:
    input_path = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-a", "job-b"],
            "source_record_id": ["record-a", "record-b"],
            "source_id": ["platform_a", "platform_b"],
            "source_job_id": ["native-a", "native-b"],
            "source_url": ["https://a.test/1", "https://b.test/2"],
            "observed_at": ["2026-08-08T08:00:00+08:00", "2026-08-10T08:00:00+08:00"],
            "company_name_normalized": ["example company", "example company"],
            "job_title_normalized": ["data analyst", "data analyst"],
            "job_title_raw": ["Data Analyst", "Data Analyst · Growth Analytics Team"],
            "title_normalization_confidence": [0.8, 0.95],
            "role_id": ["data_analyst", "data_analyst"],
            "role_parse_status": ["parsed", "parsed"],
            "city_code": ["CN-110000", "CN-110000"],
            "city_raw": ["Beijing", "Beijing"],
            "experience_band": ["mid", "mid"],
            "education_band": ["bachelor", "bachelor"],
            "published_at": [date(2026, 8, 5), date(2026, 8, 3)],
            "date_parse_status": ["parsed", "parsed"],
            "salary_raw": [None, "20-22K"],
            "salary_min_monthly": [None, 20000.0],
            "salary_max_monthly": [None, 22000.0],
            "salary_mid_monthly": [None, 21000.0],
            "salary_annualized": [None, 252000.0],
            "salary_months": [None, 12],
            "salary_parse_status": ["missing_at_source", "parsed_monthly"],
            "job_description_raw": ["SQL reporting", "SQL reporting, stakeholder analysis and dashboard ownership."],
            "record_status": ["valid", "valid"],
        }
    ).write_parquet(input_path)

    deduplicate_silver(
        input_path=input_path,
        canonical_output_path=tmp_path / "canonical.parquet",
        source_map_output_path=tmp_path / "map.parquet",
        report_path=tmp_path / "report.json",
    )
    row = pl.read_parquet(tmp_path / "canonical.parquet").to_dicts()[0]

    assert row["job_title_raw"] == "Data Analyst · Growth Analytics Team"
    assert row["job_description_raw"].endswith("dashboard ownership.")
    assert row["canonical_salary"] == 21000.0
    assert row["salary_mid_monthly"] == 21000.0
    assert row["salary_source_count"] == 1
    assert row["salary_conflict_flag"] is False
    assert len(row["salary_observations"]) == 2
    assert row["first_posted_at"] == "2026-08-03"
    assert row["first_seen_at"].startswith("2026-08-08")
    assert row["last_seen_at"].startswith("2026-08-10")


def test_canonical_salary_conflict_is_not_forced(tmp_path: Path) -> None:
    input_path = tmp_path / "silver.parquet"
    rows = []
    for job_id, source, salary in (("a", "platform_a", 10000.0), ("b", "platform_b", 30000.0)):
        rows.append(
            {
                "silver_job_id": job_id,
                "source_record_id": f"record-{job_id}",
                "source_id": source,
                "source_job_id": job_id,
                "source_url": f"https://example.test/{job_id}",
                "observed_at": "2026-08-08T08:00:00+08:00",
                "company_name_normalized": "example company",
                "job_title_normalized": "backend engineer",
                "job_title_raw": "Backend Engineer",
                "role_id": "backend_engineer",
                "city_code": "CN-110000",
                "city_raw": "Beijing",
                "experience_band": "mid",
                "education_band": "bachelor",
                "published_at": date(2026, 8, 1),
                "salary_raw": str(salary),
                "salary_mid_monthly": salary,
                "salary_parse_status": "parsed_monthly",
                "job_description_raw": "Build APIs and services",
                "record_status": "valid",
            }
        )
    pl.DataFrame(rows).write_parquet(input_path)
    deduplicate_silver(
        input_path=input_path,
        canonical_output_path=tmp_path / "canonical.parquet",
        source_map_output_path=tmp_path / "map.parquet",
        report_path=tmp_path / "report.json",
    )
    row = pl.read_parquet(tmp_path / "canonical.parquet").to_dicts()[0]

    assert row["canonical_salary"] is None
    assert row["salary_mid_monthly"] is None
    assert row["salary_source_count"] == 2
    assert row["salary_conflict_flag"] is True
    assert row["salary_parse_status"] == "conflict"


def test_audited_pair_decisions_only_override_exact_source_job_pairs(tmp_path: Path) -> None:
    input_path = tmp_path / "silver.parquet"
    rows = []
    for job_id, title, source_job_id in (
        ("a", "Data Engineer AOP Central Data Engineer Team", "posting-a"),
        ("b", "Data Engineer II AOP Central Data Engineer Team", "posting-b"),
        ("c", "Product Manager", "posting-c"),
        ("d", "Product Manager", "posting-d"),
        ("e", "Platform Engineer", "posting-e"),
        ("f", "Platform Engineer!", "posting-f"),
    ):
        rows.append(
            {
                "silver_job_id": job_id,
                "source_record_id": f"record-{job_id}",
                "source_id": "freehire",
                "source_job_id": source_job_id,
                "source_url": f"https://example.test/{source_job_id}",
                "observed_at": "2026-08-10T08:00:00+08:00",
                "company_name_normalized": "control company" if job_id in {"e", "f"} else "example company",
                "job_title_normalized": title.casefold(),
                "job_title_raw": title,
                "role_id": "data_engineer" if "Engineer" in title else "product_manager",
                "city_code": "CN-110000",
                "city_raw": "Beijing",
                "experience_band": "mid",
                "education_band": None,
                "published_at": date(2026, 8, 1),
                "salary_mid_monthly": None,
                "salary_parse_status": "missing_at_source",
                "job_description_raw": "Identical audited description.",
                "record_status": "valid",
            }
        )
    pl.DataFrame(rows).write_parquet(input_path)
    decisions_path = tmp_path / "decisions.yml"
    decisions_path.write_text(
        """version: '1.0.0'
snapshot_id: test
decisions:
  - decision: different
    left: {source_id: freehire, source_job_id: posting-a}
    right: {source_id: freehire, source_job_id: posting-b}
    reason: distinct requisitions and explicit level variant
  - decision: same
    left: {source_id: freehire, source_job_id: posting-c}
    right: {source_id: freehire, source_job_id: posting-d}
    reason: shared audited requisition
""",
        encoding="utf-8",
    )

    report = deduplicate_silver(
        input_path=input_path,
        canonical_output_path=tmp_path / "canonical.parquet",
        source_map_output_path=tmp_path / "map.parquet",
        report_path=tmp_path / "report.json",
        audited_decisions_path=decisions_path,
    )

    source_map = pl.read_parquet(tmp_path / "map.parquet")
    by_native = {
        row["source_job_id"]: row
        for row in source_map.select(
            "source_job_id", "canonical_job_id", "match_reason"
        ).to_dicts()
    }
    assert by_native["posting-a"]["canonical_job_id"] != by_native["posting-b"]["canonical_job_id"]
    assert "audited distinct" in by_native["posting-a"]["match_reason"]
    assert by_native["posting-c"]["canonical_job_id"] == by_native["posting-d"]["canonical_job_id"]
    assert "audited same" in by_native["posting-d"]["match_reason"]
    assert by_native["posting-e"]["canonical_job_id"] == by_native["posting-f"]["canonical_job_id"]
    assert report.canonical_job_count == 4
