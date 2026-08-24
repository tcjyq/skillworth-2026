from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import polars as pl
import pytest

from app.connectors import (
    CsvConnector,
    ManualExportConnector,
    ParquetConnector,
    PublicDatasetConnector,
    TechsaleratorChinaJobsConnector,
    HkCsbGovernmentVacanciesConnector,
    NextGigJune2026Connector,
    NcssPublicExportConnector,
    connector_for,
)
from app.source_models import SourceAdapterConfig
from app.source_registry import load_source_registry
from skillworth_analytics.guardrails import load_metric_guardrail_config


ROOT = Path(__file__).resolve().parents[2]


def test_source_analysis_roles_match_metric_guardrail_config() -> None:
    registry = load_source_registry(ROOT / "data/reference/sources.v1.yml")
    guardrails = load_metric_guardrail_config(ROOT / "data/reference/metric_guardrails.v1.yml")
    assert {source.source_id: source.analysis_role for source in registry.sources} == guardrails.source_roles


def test_platform_adapters_are_disabled_manual_import_by_default() -> None:
    registry = load_source_registry(ROOT / "data/reference/sources.v1.yml")

    for source_id in ("boss", "zhilian", "51job", "guopin"):
        source = registry.get(source_id)
        assert source.enabled is False
        assert source.mode == "manual_import"
        assert source.acquisition_method == "manual_export"
        assert source.terms_url


def test_csv_and_parquet_connectors_read_only_local_supported_files(tmp_path: Path) -> None:
    frame = pl.DataFrame({"职位名称": ["数据分析师"], "公司名称": ["示例科技"]})
    csv_path = tmp_path / "jobs.csv"
    parquet_path = tmp_path / "jobs.parquet"
    frame.write_csv(csv_path)
    frame.write_parquet(parquet_path)

    assert CsvConnector().read(csv_path).to_dicts() == frame.to_dicts()
    assert ParquetConnector().read(parquet_path).to_dicts() == frame.to_dicts()
    assert ManualExportConnector().read(csv_path).height == 1
    assert PublicDatasetConnector().read(parquet_path).height == 1

    with pytest.raises(ValueError, match="local CSV"):
        CsvConnector().read(Path("https://example.test/jobs.csv"))
    with pytest.raises(ValueError, match="Unsupported manual export"):
        ManualExportConnector().read(tmp_path / "jobs.json")


def test_source_adapter_rejects_non_https_terms_reference() -> None:
    with pytest.raises(ValueError, match="terms_url"):
        SourceAdapterConfig(
            source_id="unsafe",
            source_name="Unsafe",
            source_type="test",
            acquisition_method="manual_export",
            mode="manual_import",
            connector="manual_export",
            terms_url="file:///tmp/terms.txt",
            schema_mapping_version="1.0.0",
        )


def _write_techsalerator_zip(path: Path) -> None:
    columns = [
        "Website Domain",
        "Ticker",
        "Job Opening Title",
        "Job Opening URL",
        "First Seen At",
        "Last Seen At",
        "Location",
        "Location Data",
        "Category",
        "Seniority",
        "Keywords",
        "Description",
        "Salary",
        "Salary Data",
        "Contract Types",
        "Job Status",
        "Job Language",
        "Job Last Processed At",
        "O*NET Code",
        "O*NET Family",
        "O*NET Occupation Name",
    ]
    rows = [
        {
            "Website Domain": "example.cn",
            "Job Opening Title": "Data Analyst",
            "Job Opening URL": "https://example.cn/jobs/1",
            "First Seen At": "2024-05-01T00:00:00Z",
            "Location Data": '[{"city":"Shanghai","country":"China"}]',
            "Description": "Use Python and SQL",
        },
        {
            "Website Domain": "example.cn",
            "Job Opening Title": "Backend Engineer",
            "Job Opening URL": "https://example.cn/jobs/2",
            "First Seen At": "2024-05-02T00:00:00Z",
            "Location Data": '[{"city":null,"country":"China"}]',
            "Description": "Build Java services",
        },
        {
            "Website Domain": "example.us",
            "Job Opening Title": "Data Scientist",
            "Job Opening URL": "https://example.us/jobs/3",
            "First Seen At": "2024-05-03T00:00:00Z",
            "Location Data": '[{"city":"Boston","country":"United States"}]',
            "Description": "Use Python",
        },
    ]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("Job Posting.csv", buffer.getvalue().encode("utf-8"))


def test_techsalerator_connector_maps_only_structured_china_records(tmp_path: Path) -> None:
    artifact = tmp_path / "dataset.zip"
    _write_techsalerator_zip(artifact)

    result = TechsaleratorChinaJobsConnector().read_result(artifact)

    assert result.raw_record_count == 3
    assert result.accepted_record_count == 2
    assert result.rejected_record_count == 1
    assert result.frame.select(
        "company_name",
        "job_title",
        "source_url",
        "city",
        "published_at",
        "job_description",
    ).to_dicts() == [
        {
            "company_name": "example.cn",
            "job_title": "Data Analyst",
            "source_url": "https://example.cn/jobs/1",
            "city": "Shanghai",
            "published_at": "2024-05-01T00:00:00Z",
            "job_description": "Use Python and SQL",
        },
        {
            "company_name": "example.cn",
            "job_title": "Backend Engineer",
            "source_url": "https://example.cn/jobs/2",
            "city": None,
            "published_at": "2024-05-02T00:00:00Z",
            "job_description": "Build Java services",
        },
    ]
    assert connector_for("techsalerator_china_jobs_v1").read(artifact).height == 2


def test_real_dataset_registry_records_license_version_and_integrity() -> None:
    source = load_source_registry(ROOT / "data/reference/sources.v1.yml").get(
        "techsalerator_china_jobs_v1"
    )

    assert source.enabled is True
    assert source.mode == "public_dataset"
    assert source.analysis_role == "core_market"
    assert source.license_name == "Apache-2.0"
    assert source.license_url == "https://www.apache.org/licenses/LICENSE-2.0"
    assert source.dataset_version == "1"
    assert len(source.expected_sha256 or "") == 64


def test_hk_csb_connector_maps_official_json_without_converting_hkd(tmp_path: Path) -> None:
    artifact = tmp_path / "vacancies.json"
    artifact.write_text(
        json.dumps(
            {
                "common": {
                    "timestamp": "2026-07-29 10:10:00",
                    "vacancies": [
                        {
                            "jobid": 50144,
                            "jobname": "Statistician",
                            "deptnamejve": "Census and Statistics Department",
                            "division": "Social Statistics",
                            "duties": "Analyse official statistics with SQL.",
                            "entreq": "Candidates should hold a degree.",
                            "academic": ["Degree"],
                            "expfrom": 3,
                            "expto": 5,
                            "entrypay": "HK$63,100 to HK$122,045 per month",
                            "minpaym": 63100,
                            "minpayh": None,
                            "minpayd": None,
                            "ccym": "HKD$",
                            "ccyh": None,
                            "ccyd": None,
                            "pubdate": "2026-07-20",
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = HkCsbGovernmentVacanciesConnector().read_result(artifact)

    assert result.raw_record_count == result.accepted_record_count == 1
    row = result.frame.row(0, named=True)
    assert row["source_job_id"] == "50144"
    assert row["company_name"] == "Census and Statistics Department"
    assert row["city"] == "Hong Kong"
    assert row["education"] == "本科"
    assert row["experience"] == "3-5年"
    assert row["salary"] == "HK$63,100 to HK$122,045 per month"
    assert row["salary_currency"] == "HKD"
    assert row["salary_native_min_monthly"] == 63100.0
    assert "SQL" in row["job_description"]
    assert row["source_snapshot_at"] == "2026-07-29 10:10:00"


def test_hk_csb_registry_is_reviewed_and_hash_pinned() -> None:
    source = load_source_registry(ROOT / "data/reference/sources.v1.yml").get(
        "hk_csb_gov_vacancies"
    )

    assert source.enabled is True
    assert source.mode == "public_dataset"
    assert source.analysis_role == "engineering_validation"
    assert source.license_name == "DATA.GOV.HK Terms and Conditions of Use"
    assert len(source.expected_sha256 or "") == 64


def test_ncss_connector_maps_authorized_local_jsonl_export(tmp_path: Path) -> None:
    artifact = tmp_path / "ncss.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "source_job_id": "ncss-1",
                "job_name": "数据分析师",
                "company_name": "示例科技有限公司",
                "city": "北京市",
                "district": "海淀区",
                "industry": "互联网",
                "company_size": "100-499人",
                "company_type": "民营企业",
                "salary_text": "15K-25K/月",
                "education_text": "大学本科",
                "experience_text": "经验不限",
                "job_description": "负责业务数据分析。",
                "job_responsibility": "使用 SQL 建模。",
                "job_requirement": "熟悉 Python 与 Power BI。",
                "publish_time": "2026-07-10 09:00:00",
                "source_url": "https://www.ncss.cn/student/jobs/ncss-1/detail.html",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = NcssPublicExportConnector().read_result(artifact)

    assert result.raw_record_count == result.accepted_record_count == 1
    row = result.frame.row(0, named=True)
    assert row["source_job_id"] == "ncss-1"
    assert row["job_title"] == "数据分析师"
    assert row["salary"] == "15K-25K/月"
    assert row["description"] == "负责业务数据分析。"
    assert row["responsibility"] == "使用 SQL 建模。"
    assert row["requirements"] == "熟悉 Python 与 Power BI。"
    assert "SQL" in row["job_description"]
    assert "Power BI" in row["job_description"]


def test_ncss_connector_rejects_records_without_identity(tmp_path: Path) -> None:
    artifact = tmp_path / "ncss.csv"
    pl.DataFrame(
        {
            "source_job_id": [""],
            "job_name": ["后端工程师"],
            "company_name": ["示例科技有限公司"],
            "city": ["上海"],
        }
    ).write_csv(artifact)

    result = NcssPublicExportConnector().read_result(artifact)

    assert result.raw_record_count == 1
    assert result.accepted_record_count == 0
    assert result.rejected_record_count == 1


def test_ncss_registry_is_candidate_and_requires_permission() -> None:
    source = load_source_registry(ROOT / "data/reference/sources.v1.yml").get("ncss_public_jobs")

    assert source.enabled is False
    assert source.mode == "manual_import"
    assert source.connector == "ncss_public_export"
    assert source.analysis_role == "core_market_candidate"
    assert source.data_usage_status == "permission_required"


def test_nextgig_connector_preserves_semantic_provenance_and_native_currency(tmp_path: Path) -> None:
    artifact = tmp_path / "nextgig.parquet"
    pl.DataFrame(
        {
            "title": ["Senior Machine Learning Engineer"],
            "company_name": ["Example AI"],
            "ats_name": ["Greenhouse"],
            "skills_required": ['["Python", "Postgres", "Unknown Skill"]'],
            "minimum_qualifications": ["Five years of Python experience."],
            "preferred_qualifications": ["Experience with Kubernetes."],
            "responsibilities": ["Build production ML systems."],
            "salary_min": [120000.0],
            "salary_max": [180000.0],
            "salary_currency": ["USD"],
            "salary_rate_unit": ["year"],
            "city": ["Shanghai"],
            "country": ["China"],
            "experience_level": ["Senior"],
            "education_level": ["Bachelor"],
            "date_posted": ["06/01/2026"],
            "job_description": ["LLM generated summary that must not be treated as original JD."],
        }
    ).write_parquet(artifact)

    result = NextGigJune2026Connector().read_result(artifact)

    assert result.raw_record_count == result.accepted_record_count == 1
    row = result.frame.row(0, named=True)
    assert row["source_job_id"].startswith("nextgig:")
    assert row["published_at"] == "2026-06-01"
    assert row["description_type"] == "llm_summary"
    assert row["geography_source"] == "derived"
    assert row["source_job_description"] == "LLM generated summary that must not be treated as original JD."
    assert "LLM generated summary" not in row["job_description"]
    assert row["structured_skills_raw"] == '["Python", "Postgres", "Unknown Skill"]'
    assert row["salary"] is None
    assert row["salary_currency"] == "USD"
    assert row["salary_currency_original"] == "USD"
    assert row["salary_rate_unit_original"] == "year"
    assert row["salary_min_normalized"] == 10000.0
    assert row["salary_max_normalized"] == 15000.0
    assert row["salary_mid_normalized"] == 12500.0
    assert row["salary_normalization_method"] == "native_currency_monthly_from_year"
    assert row["fx_rate"] is None


def test_nextgig_registry_is_hash_pinned_candidate_and_qarera_is_external_benchmark() -> None:
    registry = load_source_registry(ROOT / "data/reference/sources.v1.yml")
    nextgig = registry.get("nextgig_global_jobs_2026_06")
    qarera = registry.get("qarera_skills_2026")

    assert nextgig.enabled is True
    assert nextgig.analysis_role == "core_market_candidate"
    assert nextgig.license_name == "CC BY 4.0"
    assert len(nextgig.expected_sha256 or "") == 64
    assert qarera.enabled is False
    assert qarera.mode == "external_benchmark"
    assert qarera.analysis_role == "external_market_benchmark"


def test_nextgig_connector_rejects_posting_dates_after_pinned_snapshot(tmp_path: Path) -> None:
    artifact = tmp_path / "nextgig.parquet"
    pl.DataFrame(
        {
            "title": ["Software Engineer"], "company_name": ["Example"],
            "ats_name": ["Workday"], "skills_required": [None],
            "salary_min": [None], "salary_max": [None], "salary_currency": [None],
            "salary_rate_unit": [None], "city": ["New York"], "country": ["USA"],
            "date_posted": ["08/05/2026"], "job_description": ["Generated summary"],
        }
    ).write_parquet(artifact)

    row = NextGigJune2026Connector().read(artifact).row(0, named=True)

    assert row["published_at"] is None
