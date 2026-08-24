from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import polars as pl
import pytest

from app.source_import import DuplicateSourceArtifactError, import_source
from app.source_models import SourceImportManifest
from app.source_registry import source_status


ROOT = Path(__file__).resolve().parents[2]
SOURCE_CONFIG = ROOT / "data/reference/sources.v1.yml"


def _write_export(path: Path) -> None:
    pl.DataFrame(
        {
            "source_id": ["untrusted-input-source"],
            "source_record_id": ["untrusted-record"],
            "ingestion_run_id": ["untrusted-run"],
            "observed_at": ["2020-01-01T00:00:00Z"],
            "job_id": ["native-1"],
            "company_name": ["示例科技有限公司"],
            "job_title": ["数据分析师"],
            "city": ["北京"],
            "education": ["本科"],
            "experience": ["1-3年"],
            "salary": ["15-25K"],
            "published_at": ["2026-08-01"],
            "job_description": ["负责 SQL、Python 和 Power BI 分析"],
        }
    ).write_csv(path)


def test_import_source_runs_only_through_complete_data_pipeline(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    boss_export = tmp_path / "boss.csv"
    zhilian_export = tmp_path / "zhilian.csv"
    _write_export(boss_export)
    _write_export(zhilian_export)

    first = import_source("boss", boss_export, data_root=data_root, config_path=SOURCE_CONFIG)
    second = import_source("zhilian", zhilian_export, data_root=data_root, config_path=SOURCE_CONFIG)

    assert first.bronze_path.exists()
    assert first.stored_raw_artifact_path.exists()
    assert first.stored_raw_artifact_path.read_bytes() == boss_export.read_bytes()
    assert first.raw_record_count == 1
    assert first.record_count == 1
    assert first.rejected_record_count == 0
    first_bronze = pl.read_parquet(first.bronze_path)
    assert first_bronze["source_id"].to_list() == ["boss"]
    assert first_bronze["raw_input__source_id"].to_list() == ["untrusted-input-source"]
    assert first_bronze["raw_input__observed_at"].to_list() == ["2020-01-01T00:00:00Z"]
    assert second.silver_path.exists()
    assert second.canonical_jobs_path.exists()
    assert second.job_source_map_path.exists()
    assert second.skills_path.exists()
    assert second.job_skills_path.exists()
    assert second.warehouse_path.exists()
    assert pl.read_parquet(second.canonical_jobs_path).height == 1
    assert pl.read_parquet(second.job_source_map_path).height == 2
    manifest = json.loads(second.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_name"] == "智联招聘"
    assert manifest["acquisition_method"] == "manual_export"
    assert manifest["record_count"] == 1
    assert manifest["raw_record_count"] == 1
    assert manifest["rejected_record_count"] == 0
    assert manifest["raw_artifact_sha256"]
    assert Path(manifest["stored_raw_artifact_path"]).is_file()

    statuses = {item.source_id: item for item in source_status(SOURCE_CONFIG, data_root)}
    assert statuses["boss"].record_count == 1
    assert statuses["boss"].last_sync is not None
    assert statuses["zhilian"].freshness in {"fresh", "stale"}


def test_same_source_artifact_cannot_be_imported_twice(tmp_path: Path) -> None:
    export = tmp_path / "jobs.csv"
    _write_export(export)
    data_root = tmp_path / "data"

    import_source("boss", export, data_root=data_root, config_path=SOURCE_CONFIG)

    with pytest.raises(DuplicateSourceArtifactError):
        import_source("boss", export, data_root=data_root, config_path=SOURCE_CONFIG)


def test_source_status_includes_current_real_mode_manifest(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    run_id = "real-run-1"
    manifest_dir = data_root / "modes/real/snapshot/bronze/manifests"
    manifest_dir.mkdir(parents=True)
    manifest = SourceImportManifest(
        source_id="techsalerator_china_jobs_v1",
        source_name="Techsalerator — Job Posting Data in China v1",
        source_type="public_dataset",
        acquisition_method="kaggle_public_download",
        enabled=True,
        mode="public_dataset",
        terms_url="https://www.kaggle.com/datasets/techsalerator/job-posting-data-in-china",
        connector="techsalerator_china_jobs_v1",
        connector_version="1.0.0",
        schema_mapping_version="techsalerator_china_jobs_v1",
        ingestion_run_id=run_id,
        imported_at=datetime.now(UTC),
        raw_artifact_path="dataset.zip",
        raw_artifact_sha256="0" * 64,
        stored_raw_artifact_path="raw/dataset.zip",
        bronze_path="bronze/jobs.parquet",
        raw_record_count=9_919,
        record_count=451,
        rejected_record_count=9_468,
    )
    (manifest_dir / f"{run_id}_{manifest.source_id}.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    current_dir = data_root / "modes/real"
    (current_dir / "current.json").write_text(
        json.dumps(
            {
                "data_mode": "real",
                "source_id": manifest.source_id,
                "ingestion_run_id": run_id,
            }
        ),
        encoding="utf-8",
    )

    statuses = {item.source_id: item for item in source_status(SOURCE_CONFIG, data_root)}

    assert statuses[manifest.source_id].record_count == 451
    assert statuses[manifest.source_id].last_sync is not None
    assert statuses[manifest.source_id].freshness == "fresh"


def test_placeholder_dataset_adapter_cannot_import_before_license_review(tmp_path: Path) -> None:
    export = tmp_path / "public.csv"
    _write_export(export)

    with pytest.raises(ValueError, match="terms or license"):
        import_source("public_dataset", export, data_root=tmp_path / "data", config_path=SOURCE_CONFIG)


def test_reviewed_public_dataset_rejects_unexpected_artifact_hash(tmp_path: Path) -> None:
    artifact = tmp_path / "dataset.zip"
    artifact.write_bytes(b"not-the-reviewed-version")

    with pytest.raises(ValueError, match="SHA-256"):
        import_source(
            "techsalerator_china_jobs_v1",
            artifact,
            data_root=tmp_path / "data",
            config_path=SOURCE_CONFIG,
        )

    assert not (tmp_path / "data/bronze").exists()


def test_ncss_import_is_blocked_until_data_permission_is_recorded(tmp_path: Path) -> None:
    artifact = tmp_path / "ncss.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "source_job_id": "ncss-1",
                "job_name": "数据分析师",
                "company_name": "示例科技有限公司",
                "city": "北京",
                "salary_text": "15K-25K/月",
                "education_text": "本科",
                "experience_text": "经验不限",
                "job_description": "SQL Python",
                "publish_time": "2026-07-10",
                "source_url": "https://www.ncss.cn/student/jobs/ncss-1/detail.html",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="data usage permission"):
        import_source(
            "ncss_public_jobs",
            artifact,
            data_root=tmp_path / "data",
            config_path=SOURCE_CONFIG,
        )

    assert not (tmp_path / "data/bronze").exists()


def test_reviewed_ncss_export_uses_the_complete_existing_pipeline(tmp_path: Path) -> None:
    artifact = tmp_path / "ncss.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "source_job_id": "ncss-1",
                "job_name": "数据分析师",
                "company_name": "示例科技有限公司",
                "city": "北京",
                "salary_text": "15K-25K/月",
                "education_text": "本科",
                "experience_text": "经验不限",
                "job_description": "负责数据分析。",
                "job_responsibility": "使用 SQL 建模。",
                "job_requirement": "熟悉 Python 与 Power BI。",
                "publish_time": "2026-07-10",
                "source_url": "https://www.ncss.cn/student/jobs/ncss-1/detail.html",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    config = tmp_path / "sources.yml"
    config.write_text(
        """version: 'test'
freshness_days: 30
sources:
  - source_id: ncss_public_jobs
    source_name: NCSS authorized fixture
    source_type: official_employment_platform
    analysis_role: core_market_candidate
    acquisition_method: authorized_manual_export
    enabled: false
    mode: manual_import
    connector: ncss_public_export
    terms_url: https://job.ncss.cn/student/connectUser.html
    data_usage_status: reviewed
    schema_mapping_version: '1.0.0'
""",
        encoding="utf-8",
    )

    result = import_source(
        "ncss_public_jobs",
        artifact,
        data_root=tmp_path / "data",
        config_path=config,
    )

    assert result.bronze_path.is_file()
    assert result.silver_path.is_file()
    assert result.canonical_jobs_path.is_file()
    assert result.job_skills_path.is_file()
    assert result.warehouse_path.is_file()
    bronze = pl.read_parquet(result.bronze_path)
    assert bronze["responsibility"].to_list() == ["使用 SQL 建模。"]
    assert "Power BI" in bronze["job_description"].item()
    assert pl.read_parquet(result.job_skills_path).height >= 3
