from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path

from app.freehire import (
    FREEHIRE_CHINA_TECH_CATEGORIES,
    FreehirePublicApiConnector,
    FreehireSnapshotConfig,
)


def _job(index: int) -> dict[str, object]:
    return {
        "public_slug": f"job-{index}",
        "source": "greenhouse" if index % 2 else "workday",
        "external_id": f"external-{index}",
        "url": f"https://example.com/jobs/{index}",
        "title": "Senior Data Engineer",
        "company": f"Example {index % 2}",
        "company_slug": f"example-{index % 2}",
        "location": "Shanghai, China",
        "description": "Build pipelines with Python, SQL and Kubernetes.",
        "countries": ["cn"],
        "cities": ["Shanghai"],
        "skills": ["python", "sql", "kubernetes"],
        "posted_at": "2026-08-01T00:00:00Z",
        "enrichment": {
            "category": ["data_engineering"],
            "seniority": "senior",
            "education_level": "bachelor",
            "experience_years_min": 5,
            "salary_min": 300000,
            "salary_max": 500000,
            "salary_currency": "CNY",
            "salary_period": "year",
        },
    }


def test_freehire_connector_maps_public_job_without_promoting_facets_to_gold(tmp_path: Path) -> None:
    artifact = tmp_path / "freehire.jsonl"
    artifact.write_text(
        json.dumps(
            {
                **_job(1),
                "_skillworth_api_accessed_at": "2026-08-10T10:00:00Z",
                "_skillworth_payload_sha256": "a" * 64,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = FreehirePublicApiConnector().read_result(artifact)

    assert result.raw_record_count == result.accepted_record_count == 1
    row = result.frame.row(0, named=True)
    assert row["source_job_id"] == "job-1"
    assert row["source_url"] == "https://example.com/jobs/1"
    assert row["upstream_source"] == "greenhouse"
    assert row["upstream_external_id"] == "external-1"
    assert row["source_company_slug"] == "example-1"
    assert row["job_title"] == "Senior Data Engineer"
    assert row["city"] == "Shanghai"
    assert row["structured_skills_raw"] == '["python", "sql", "kubernetes"]'
    assert row["salary"] is None
    assert row["salary_raw_structured"] is not None
    assert row["salary_currency_original"] == "CNY"
    assert row["api_accessed_at"] == "2026-08-10T10:00:00Z"
    assert "source_structured_skills_require_skillworth_taxonomy_mapping" in result.warnings


def test_freehire_snapshot_is_paginated_cached_and_reproducible(tmp_path: Path) -> None:
    calls: list[dict[str, str]] = []

    def fake_get(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        del headers
        query = dict(item.split("=", 1) for item in url.split("?", 1)[1].split("&"))
        calls.append(query)
        offset = int(query["offset"])
        rows = [_job(index) for index in range(offset, min(offset + 2, 3))]
        return 200, {}, json.dumps(
            {"data": rows, "meta": {"total": 3, "limit": 2, "offset": offset}},
            ensure_ascii=False,
        ).encode("utf-8")

    connector = FreehirePublicApiConnector(http_get=fake_get, sleeper=lambda _: None)
    config = FreehireSnapshotConfig(
        snapshot_id="freehire_china_tech_2026_08",
        page_size=2,
        delay_seconds=0.1,
    )
    now = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)

    first = connector.acquire_snapshot(tmp_path, config=config, now=lambda: now)
    second = connector.acquire_snapshot(tmp_path, config=config, now=lambda: now)

    assert len(calls) == 2
    assert first == second
    assert first.raw_count == 3
    assert first.valid_count == 3
    assert first.company_count == 2
    assert first.source_count == 2
    assert first.query_scope["countries"] == "cn"
    assert tuple(first.query_scope["category"]) == FREEHIRE_CHINA_TECH_CATEGORIES
    assert first.content_sha256 == hashlib.sha256(first.artifact_path.read_bytes()).hexdigest()
    assert first.metadata_path.is_file()
    assert len(list(first.cache_directory.glob("page_*.json"))) == 2


def test_freehire_snapshot_retries_429_with_retry_after(tmp_path: Path) -> None:
    attempts = 0
    sleeps: list[float] = []

    def flaky_get(_: str, __: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return 429, {"retry-after": "2"}, b'{"error":"rate limited"}'
        return 200, {}, json.dumps(
            {"data": [_job(1)], "meta": {"total": 1, "limit": 100, "offset": 0}},
            ensure_ascii=False,
        ).encode("utf-8")

    result = FreehirePublicApiConnector(
        http_get=flaky_get,
        sleeper=sleeps.append,
    ).acquire_snapshot(
        tmp_path,
        config=FreehireSnapshotConfig(
            snapshot_id="freehire_china_tech_2026_08",
            delay_seconds=0.1,
            maximum_retries=2,
        ),
        now=lambda: datetime(2026, 8, 10, 10, 0, tzinfo=UTC),
    )

    assert result.valid_count == 1
    assert attempts == 2
    assert sleeps == [2.0]


def test_freehire_snapshot_counts_invalid_upstream_rows_without_aborting(tmp_path: Path) -> None:
    invalid = {**_job(1), "company": ""}

    def fake_get(_: str, __: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        return 200, {}, json.dumps(
            {"data": [_job(0), invalid], "meta": {"total": 2, "limit": 100, "offset": 0}},
            ensure_ascii=False,
        ).encode("utf-8")

    result = FreehirePublicApiConnector(
        http_get=fake_get, sleeper=lambda _: None
    ).acquire_snapshot(
        tmp_path,
        config=FreehireSnapshotConfig(
            snapshot_id="freehire_china_tech_2026_08", delay_seconds=0.1
        ),
        now=lambda: datetime(2026, 8, 10, 10, 0, tzinfo=UTC),
    )

    assert result.raw_count == 2
    assert result.valid_count == 1
    assert result.rejected_count == 1


def test_freehire_connector_rejects_missing_identity(tmp_path: Path) -> None:
    artifact = tmp_path / "freehire.jsonl"
    artifact.write_text(
        json.dumps({"title": "Data Engineer", "company": "Example"}) + "\n",
        encoding="utf-8",
    )

    result = FreehirePublicApiConnector().read_result(artifact)

    assert result.raw_record_count == 1
    assert result.accepted_record_count == 0
    assert result.rejected_record_count == 1


def test_freehire_jsonl_reader_does_not_split_unicode_line_separator(tmp_path: Path) -> None:
    artifact = tmp_path / "freehire.jsonl"
    artifact.write_text(
        json.dumps({**_job(1), "description": "first\u2028second"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    result = FreehirePublicApiConnector().read_result(artifact)

    assert result.raw_record_count == 1
    assert result.accepted_record_count == 1
