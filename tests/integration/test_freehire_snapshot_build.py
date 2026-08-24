from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import duckdb

from app.freehire import FreehirePublicApiConnector, FreehireSnapshotConfig
from app.freehire_snapshot import _available_pipeline_root, build_freehire_china_snapshot


def _job(slug: str, title: str, company: str, skills: list[str]) -> dict[str, object]:
    return {
        "public_slug": slug,
        "source": "greenhouse",
        "external_id": f"external-{slug}",
        "url": f"https://example.com/jobs/{slug}",
        "title": title,
        "company": company,
        "company_slug": company.casefold().replace(" ", "-"),
        "location": "Beijing, China",
        "countries": ["cn"],
        "cities": ["Beijing"],
        "description": "Python SQL PostgreSQL Docker Kubernetes",
        "skills": skills,
        "posted_at": "2026-08-05T00:00:00Z",
        "enrichment": {"category": ["backend"], "seniority": "mid"},
    }


def test_fixed_snapshot_runs_existing_pipeline_and_is_reproducible(tmp_path: Path) -> None:
    jobs = [
        _job("job-a", "Backend Engineer", "Alpha Tech", ["Python", "PostgreSQL"]),
        _job("job-b", "Data Engineer", "Beta Tech", ["Python", "SQL"]),
    ]

    def http_get(url: str, _: dict[str, str]):
        query = parse_qs(urlparse(url).query)
        offset = int(query["offset"][0])
        page = jobs[offset : offset + 1]
        body = json.dumps(
            {"data": page, "meta": {"total": len(jobs), "limit": 1, "offset": offset}}
        ).encode()
        return 200, {"date": "Mon, 10 Aug 2026 10:00:00 GMT"}, body

    connector = FreehirePublicApiConnector(http_get=http_get, sleeper=lambda _: None)
    config = FreehireSnapshotConfig(
        snapshot_id="freehire_china_tech_2026_08",
        page_size=1,
        delay_seconds=0.1,
    )
    now = lambda: datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
    first = build_freehire_china_snapshot(
        output_root=tmp_path / "freehire",
        sources_config=Path("data/reference/sources.v1.yml"),
        connector=connector,
        snapshot_config=config,
        now=now,
        publish_current=True,
    )
    second = build_freehire_china_snapshot(
        output_root=tmp_path / "freehire",
        sources_config=Path("data/reference/sources.v1.yml"),
        connector=connector,
        snapshot_config=config,
        now=now,
        publish_current=True,
    )

    assert first == second
    assert first.raw_job_count == 2
    assert first.rejected_job_count == 0
    assert first.pipeline_job_count == 2
    assert first.canonical_job_count == 2
    assert first.market_scope == "china_open_tech_sample"
    assert first.source_role == "china_supplementary"
    assert first.salary_signal_status == "unavailable"
    assert first.trend_signal_status == "unavailable"
    assert first.content_sha256 == second.content_sha256
    assert first.integration_manifest_path.is_file()
    assert (tmp_path / "freehire/current.json").is_file()

    connection = duckdb.connect(str(first.warehouse_path), read_only=True)
    try:
        count = connection.execute("SELECT count(*) FROM china_skillworth_summary").fetchone()[0]
        invalid = connection.execute(
            "SELECT count(*) FROM china_skillworth_summary "
            "WHERE salary_signal IS NOT NULL OR trend_signal IS NOT NULL"
        ).fetchone()[0]
    finally:
        connection.close()
    assert count > 0
    assert invalid == 0


def test_interrupted_derived_pipeline_uses_clean_retry_without_deleting_raw(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    interrupted = snapshot_root / "pipeline_v6/bronze/manifests"
    interrupted.mkdir(parents=True)
    (interrupted / "partial.json").write_text("{}", encoding="utf-8")

    selected = _available_pipeline_root(snapshot_root)

    assert selected == snapshot_root / "pipeline_v6_attempt_2"
    assert (interrupted / "partial.json").is_file()


def test_freehire_snapshot_applies_scoped_audited_dedup_decisions(tmp_path: Path) -> None:
    jobs = [
        _job(
            "operative-product-manager-2-flextronics-international-z6rcbu7k",
            "Operative Product Manager-2",
            "Flextronics International",
            ["Python"],
        ),
        _job(
            "operative-product-manager-1-flextronics-international-hzqrwa2z",
            "Operative Product Manager-1",
            "Flextronics International",
            ["SQL"],
        ),
    ]

    def http_get(url: str, _: dict[str, str]):
        query = parse_qs(urlparse(url).query)
        offset = int(query["offset"][0])
        page = jobs[offset : offset + 1]
        body = json.dumps(
            {"data": page, "meta": {"total": len(jobs), "limit": 1, "offset": offset}}
        ).encode()
        return 200, {"date": "Mon, 10 Aug 2026 10:00:00 GMT"}, body

    result = build_freehire_china_snapshot(
        output_root=tmp_path / "freehire",
        sources_config=Path("data/reference/sources.v1.yml"),
        connector=FreehirePublicApiConnector(http_get=http_get, sleeper=lambda _: None),
        snapshot_config=FreehireSnapshotConfig(
            snapshot_id="freehire_china_tech_2026_08",
            page_size=1,
            delay_seconds=0.1,
        ),
        now=lambda: datetime(2026, 8, 10, 18, 0, tzinfo=UTC),
        publish_current=False,
    )

    assert result.canonical_job_count == 2
    source_map = duckdb.connect().execute(
        "SELECT source_job_id, match_reason FROM read_parquet(?) ORDER BY source_job_id",
        [str(result.job_source_map_path)],
    ).fetchall()
    assert len(source_map) == 2
    assert all("audited distinct" in row[1] for row in source_map)
