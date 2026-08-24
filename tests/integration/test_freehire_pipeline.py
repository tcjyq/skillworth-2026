from __future__ import annotations

import json
from pathlib import Path

import duckdb
import polars as pl
import pytest

from app.source_import import import_source
from app.source_registry import load_source_registry


def _artifact(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "public_slug": "data-engineer-example-1",
                "source": "greenhouse",
                "external_id": "gh-1",
                "url": "https://example.com/jobs/1",
                "title": "Data Engineer",
                "company": "Example Technology",
                "company_slug": "example-technology",
                "location": "Shanghai, China",
                "cities": ["Shanghai"],
                "countries": ["cn"],
                "description": "Build Python and SQL pipelines on Kubernetes.",
                "skills": ["python", "sql", "kubernetes"],
                "posted_at": "2026-08-01T00:00:00Z",
                "enrichment": {
                    "category": ["data_engineering"],
                    "salary_min": 300000,
                    "salary_max": 500000,
                    "salary_currency": "CNY",
                    "salary_period": "year",
                },
                "_skillworth_api_accessed_at": "2026-08-10T10:00:00Z",
                "_skillworth_payload_sha256": "a" * 64,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _config(path: Path, *, mode: str = "public_api", usage: str = "no_explicit_block_found") -> None:
    path.write_text(
        f"""version: 'test'
freshness_days: 30
sources:
  - source_id: freehire_china_tech
    source_name: Freehire China Technical Snapshot
    source_type: public_api_catalogue
    analysis_role: supplementary_market
    acquisition_method: public_unauthenticated_read_api_snapshot
    enabled: true
    mode: {mode}
    connector: freehire_public_api
    terms_url: https://freehire.me/docs/api
    data_usage_status: {usage}
    schema_mapping_version: '1.0.0'
""",
        encoding="utf-8",
    )


def test_freehire_snapshot_uses_complete_pipeline_and_preserves_provenance(tmp_path: Path) -> None:
    artifact = tmp_path / "freehire.jsonl"
    config = tmp_path / "sources.yml"
    _artifact(artifact)
    _config(config)

    result = import_source(
        "freehire_china_tech",
        artifact,
        data_root=tmp_path / "data",
        config_path=config,
    )

    silver = pl.read_parquet(result.silver_path)
    assert silver["upstream_source"].to_list() == ["greenhouse"]
    assert silver["upstream_external_id"].to_list() == ["gh-1"]
    assert silver["source_company_slug"].to_list() == ["example-technology"]
    assert silver["api_accessed_at"].to_list() == ["2026-08-10T10:00:00Z"]
    assert silver["source_payload_sha256"].to_list() == ["a" * 64]
    assert silver["salary_mid_monthly"].null_count() == 1

    source_map = pl.read_parquet(result.job_source_map_path)
    assert source_map.select(
        "source_id", "upstream_source", "upstream_external_id", "source_url"
    ).to_dicts() == [
        {
            "source_id": "freehire_china_tech",
            "upstream_source": "greenhouse",
            "upstream_external_id": "gh-1",
            "source_url": "https://example.com/jobs/1",
        }
    ]
    connection = duckdb.connect(str(result.warehouse_path), read_only=True)
    try:
        warehouse_row = connection.execute(
            "SELECT upstream_source, upstream_external_id, source_company_slug, api_accessed_at "
            "FROM job_source_map"
        ).fetchone()
    finally:
        connection.close()
    assert warehouse_row == (
        "greenhouse",
        "gh-1",
        "example-technology",
        "2026-08-10T10:00:00Z",
    )


def test_no_explicit_block_status_is_restricted_to_public_api_mode(tmp_path: Path) -> None:
    config = tmp_path / "sources.yml"
    _config(config, mode="manual_import")

    with pytest.raises(ValueError, match="no_explicit_block_found"):
        load_source_registry(config)
