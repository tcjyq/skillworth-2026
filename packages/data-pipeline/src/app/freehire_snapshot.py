from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from app.freehire import (
    FreehirePublicApiConnector,
    FreehireSnapshotConfig,
    FreehireSnapshotResult,
)
from app.source_import import import_source
from app.source_models import SourceImportResult
from app.dedup_pipeline import deduplicate_silver
from app.warehouse import build_warehouse
from skillworth_analytics import AdvancedAnalyticsRepository, AnalyticsFilters
from skillworth_analytics.china_skillworth import (
    DISCLAIMER,
    ChinaSkillWorthBuildReport,
    build_china_skillworth_summary,
    build_china_skillworth_visual_ready,
    load_china_skillworth_config,
)
from skillworth_analytics.confidence_config import load_data_confidence_config


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
FREEHIRE_SOURCE_ID = "freehire"
AUDIT_DECISIONS_PATH = (
    REPOSITORY_ROOT / "data/reference/freehire_dedup_audit_2026_08.v1.yml"
)


class FreehireChinaSnapshotBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    market_scope: str = "china_open_tech_sample"
    source_role: str = "china_supplementary"
    source_id: str = FREEHIRE_SOURCE_ID
    pipeline_version: str = "6"
    acquired_at: datetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_job_count: int = Field(ge=0)
    valid_job_count: int = Field(ge=0)
    pipeline_job_count: int = Field(ge=0)
    rejected_job_count: int = Field(ge=0)
    canonical_job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    source_count: int = Field(default=1, ge=1)
    upstream_source_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)
    salary_signal_status: str = "unavailable"
    trend_signal_status: str = "unavailable"
    qarera_validation_status: str = "unavailable"
    disclaimer: str = DISCLAIMER
    artifact_path: Path
    acquisition_metadata_path: Path
    integration_manifest_path: Path
    silver_path: Path
    quality_report_path: Path
    canonical_jobs_path: Path
    job_source_map_path: Path
    skills_path: Path
    job_skills_path: Path
    graph_nodes_path: Path
    graph_edges_path: Path
    warehouse_path: Path
    top_skills: tuple[dict[str, Any], ...]


def build_freehire_china_snapshot(
    *,
    output_root: Path = REPOSITORY_ROOT / "data/modes/freehire",
    sources_config: Path = REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    connector: FreehirePublicApiConnector | None = None,
    snapshot_config: FreehireSnapshotConfig | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    publish_current: bool = True,
) -> FreehireChinaSnapshotBuildResult:
    """Acquire one immutable Freehire month snapshot and run the standard pipeline."""
    config = snapshot_config or FreehireSnapshotConfig(
        snapshot_id="freehire_china_tech_2026_08"
    )
    output_root = output_root.resolve()
    snapshot_root = output_root / "snapshots" / config.snapshot_id
    integration_manifest = snapshot_root / "integration_manifest.v6.json"
    if integration_manifest.is_file():
        result = FreehireChinaSnapshotBuildResult.model_validate_json(
            integration_manifest.read_text(encoding="utf-8")
        )
        _validate_completed_result(result)
        if publish_current:
            _write_current_pointer(output_root / "current.json", result)
        return result

    connector = connector or FreehirePublicApiConnector()
    acquisition = connector.acquire_snapshot(
        output_root / "snapshots", config=config, now=now
    )
    v4_manifest = snapshot_root / "integration_manifest.v4.json"
    if v4_manifest.is_file():
        base = FreehireChinaSnapshotBuildResult.model_validate_json(
            v4_manifest.read_text(encoding="utf-8")
        )
        _validate_completed_result(base)
        audit_snapshot = snapshot_root / "pipeline_v6/snapshots/dedup_audit_v1"
        canonical_jobs_path = audit_snapshot / "gold/canonical_jobs.parquet"
        job_source_map_path = audit_snapshot / "gold/job_source_map.parquet"
        dedup_report_path = audit_snapshot / "gold/dedup_report.json"
        warehouse_path = audit_snapshot / "warehouse/skillworth.duckdb"
        benchmark_path = audit_snapshot / "warehouse/query_benchmark.json"
        if not warehouse_path.is_file():
            deduplicate_silver(
                input_path=base.silver_path,
                canonical_output_path=canonical_jobs_path,
                source_map_output_path=job_source_map_path,
                report_path=dedup_report_path,
                audited_decisions_path=AUDIT_DECISIONS_PATH,
            )
            build_warehouse(
                database_path=warehouse_path,
                canonical_jobs=canonical_jobs_path,
                job_source_map=job_source_map_path,
                skills=base.skills_path,
                job_skills=base.job_skills_path,
                benchmark_path=benchmark_path,
            )
        graph_nodes_path = snapshot_root / "gold/skill_graph_nodes.parquet"
        graph_edges_path = snapshot_root / "gold/skill_graph_edges.parquet"
        AdvancedAnalyticsRepository(warehouse_path).build_skill_network(
            nodes_output_path=graph_nodes_path,
            edges_output_path=graph_edges_path,
            filters=AnalyticsFilters(market_scope="all", source_scope="all"),
        )
        china_config = load_china_skillworth_config(
            REPOSITORY_ROOT / "data/reference/china_skillworth.v1.yml"
        )
        confidence_config = load_data_confidence_config(
            REPOSITORY_ROOT / "data/reference/data_confidence.v1.yml"
        )
        summary = build_china_skillworth_summary(
            database_path=warehouse_path,
            graph_nodes_path=graph_nodes_path,
            graph_edges_path=graph_edges_path,
            snapshot_id=config.snapshot_id,
            snapshot_completed_at=acquisition.snapshot_completed_at,
            config=china_config,
            confidence_config=confidence_config,
        )
        build_china_skillworth_visual_ready(
            database_path=warehouse_path,
            snapshot_id=config.snapshot_id,
            snapshot_completed_at=acquisition.snapshot_completed_at,
            config=china_config,
            confidence_config=confidence_config,
        )
        top = sorted(
            summary.records, key=lambda item: (-item.skillworth_score, item.skill_id)
        )[:20]
        result = FreehireChinaSnapshotBuildResult(
            snapshot_id=config.snapshot_id,
            acquired_at=acquisition.snapshot_completed_at,
            content_sha256=acquisition.content_sha256,
            raw_job_count=acquisition.raw_count,
            valid_job_count=acquisition.valid_count,
            pipeline_job_count=base.pipeline_job_count,
            rejected_job_count=acquisition.rejected_count,
            canonical_job_count=summary.job_count,
            company_count=summary.company_count,
            upstream_source_count=acquisition.source_count,
            skill_count=summary.skill_count,
            artifact_path=acquisition.artifact_path,
            acquisition_metadata_path=acquisition.metadata_path,
            integration_manifest_path=integration_manifest,
            silver_path=base.silver_path,
            quality_report_path=base.quality_report_path,
            canonical_jobs_path=canonical_jobs_path,
            job_source_map_path=job_source_map_path,
            skills_path=base.skills_path,
            job_skills_path=base.job_skills_path,
            graph_nodes_path=graph_nodes_path,
            graph_edges_path=graph_edges_path,
            warehouse_path=warehouse_path,
            top_skills=tuple(item.model_dump(mode="json") for item in top),
        )
        _write_text_atomic(integration_manifest, result.model_dump_json(indent=2))
        if publish_current:
            _write_current_pointer(output_root / "current.json", result)
        return result

    pipeline_root = _available_pipeline_root(snapshot_root)
    imported = _completed_import(pipeline_root) or import_source(
        FREEHIRE_SOURCE_ID,
        acquisition.artifact_path,
        data_root=pipeline_root,
        config_path=sources_config.resolve(),
        dedup_decisions_path=AUDIT_DECISIONS_PATH,
    )

    graph_nodes_path = snapshot_root / "gold/skill_graph_nodes.parquet"
    graph_edges_path = snapshot_root / "gold/skill_graph_edges.parquet"
    network = AdvancedAnalyticsRepository(imported.warehouse_path).build_skill_network(
        nodes_output_path=graph_nodes_path,
        edges_output_path=graph_edges_path,
        filters=AnalyticsFilters(market_scope="all", source_scope="all"),
    )
    if network.node_count == 0:
        raise ValueError("Freehire snapshot produced no normalized skill graph nodes")

    summary = build_china_skillworth_summary(
        database_path=imported.warehouse_path,
        graph_nodes_path=graph_nodes_path,
        graph_edges_path=graph_edges_path,
        snapshot_id=config.snapshot_id,
        snapshot_completed_at=acquisition.snapshot_completed_at,
        config=load_china_skillworth_config(
            REPOSITORY_ROOT / "data/reference/china_skillworth.v1.yml"
        ),
        confidence_config=load_data_confidence_config(
            REPOSITORY_ROOT / "data/reference/data_confidence.v1.yml"
        ),
    )
    build_china_skillworth_visual_ready(
        database_path=imported.warehouse_path,
        snapshot_id=config.snapshot_id,
        snapshot_completed_at=acquisition.snapshot_completed_at,
        config=load_china_skillworth_config(
            REPOSITORY_ROOT / "data/reference/china_skillworth.v1.yml"
        ),
        confidence_config=load_data_confidence_config(
            REPOSITORY_ROOT / "data/reference/data_confidence.v1.yml"
        ),
    )
    result = _result(
        acquisition=acquisition,
        imported=imported,
        summary=summary,
        graph_nodes_path=graph_nodes_path,
        graph_edges_path=graph_edges_path,
        integration_manifest=integration_manifest,
    )
    _write_text_atomic(integration_manifest, result.model_dump_json(indent=2))
    if publish_current:
        _write_current_pointer(output_root / "current.json", result)
    return result


def _result(
    *,
    acquisition: FreehireSnapshotResult,
    imported: SourceImportResult,
    summary: ChinaSkillWorthBuildReport,
    graph_nodes_path: Path,
    graph_edges_path: Path,
    integration_manifest: Path,
) -> FreehireChinaSnapshotBuildResult:
    top = sorted(summary.records, key=lambda item: (-item.skillworth_score, item.skill_id))[:20]
    return FreehireChinaSnapshotBuildResult(
        snapshot_id=acquisition.snapshot_id,
        acquired_at=acquisition.snapshot_completed_at,
        content_sha256=acquisition.content_sha256,
        raw_job_count=acquisition.raw_count,
        valid_job_count=acquisition.valid_count,
        pipeline_job_count=imported.record_count,
        rejected_job_count=acquisition.rejected_count,
        canonical_job_count=summary.job_count,
        company_count=summary.company_count,
        upstream_source_count=acquisition.source_count,
        skill_count=summary.skill_count,
        artifact_path=acquisition.artifact_path,
        acquisition_metadata_path=acquisition.metadata_path,
        integration_manifest_path=integration_manifest,
        silver_path=imported.silver_path,
        quality_report_path=imported.quality_report_path,
        canonical_jobs_path=imported.canonical_jobs_path,
        job_source_map_path=imported.job_source_map_path,
        skills_path=imported.skills_path,
        job_skills_path=imported.job_skills_path,
        graph_nodes_path=graph_nodes_path,
        graph_edges_path=graph_edges_path,
        warehouse_path=imported.warehouse_path,
        top_skills=tuple(item.model_dump(mode="json") for item in top),
    )


def _completed_import(data_root: Path) -> SourceImportResult | None:
    manifests = sorted((data_root / "bronze/manifests").glob(f"*_{FREEHIRE_SOURCE_ID}.json"))
    if not manifests:
        return None
    payload = json.loads(manifests[-1].read_text(encoding="utf-8"))
    run_id = str(payload["ingestion_run_id"])
    snapshot = data_root / "snapshots" / run_id
    paths = {
        "silver_path": snapshot / "silver/silver_jobs.parquet",
        "quality_report_path": snapshot / "silver/silver_jobs.quality.json",
        "canonical_jobs_path": snapshot / "gold/canonical_jobs.parquet",
        "job_source_map_path": snapshot / "gold/job_source_map.parquet",
        "dedup_report_path": snapshot / "gold/dedup_report.json",
        "skills_path": snapshot / "silver/skills.parquet",
        "job_skills_path": snapshot / "silver/job_skills.parquet",
        "warehouse_path": snapshot / "warehouse/skillworth.duckdb",
        "benchmark_path": snapshot / "warehouse/query_benchmark.json",
    }
    if not all(path.is_file() for path in paths.values()):
        return None
    return SourceImportResult(
        source_id=FREEHIRE_SOURCE_ID,
        ingestion_run_id=run_id,
        raw_record_count=int(payload["raw_record_count"]),
        record_count=int(payload["record_count"]),
        rejected_record_count=int(payload["rejected_record_count"]),
        connector_warnings=tuple(payload.get("connector_warnings", ())),
        stored_raw_artifact_path=Path(payload["stored_raw_artifact_path"]),
        bronze_path=Path(payload["bronze_path"]),
        manifest_path=manifests[-1],
        **paths,
    )


def _available_pipeline_root(snapshot_root: Path) -> Path:
    """Reuse a completed derivation or select a clean retry directory.

    Raw acquisition artifacts remain immutable. A process interruption after a
    Bronze manifest must not force deletion or make the snapshot unrecoverable.
    """
    base = snapshot_root / "pipeline_v6"
    if _completed_import(base) is not None:
        return base
    if not (base / "bronze/manifests").exists():
        return base
    attempt = 2
    while True:
        candidate = snapshot_root / f"pipeline_v6_attempt_{attempt}"
        if _completed_import(candidate) is not None or not candidate.exists():
            return candidate
        attempt += 1


def _validate_completed_result(result: FreehireChinaSnapshotBuildResult) -> None:
    required = (
        result.artifact_path,
        result.acquisition_metadata_path,
        result.silver_path,
        result.canonical_jobs_path,
        result.job_source_map_path,
        result.graph_nodes_path,
        result.graph_edges_path,
        result.warehouse_path,
    )
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("Completed Freehire snapshot manifest references missing artifacts")


def _write_current_pointer(path: Path, result: FreehireChinaSnapshotBuildResult) -> None:
    payload = result.model_dump(mode="json")
    payload["snapshot"] = "2026-08"
    payload["graph_edges_path"] = str(result.graph_edges_path)
    payload["quality_report_path"] = str(result.quality_report_path)
    _write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _write_text_atomic(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)
