from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, ConfigDict
from skillworth_analytics import AdvancedAnalyticsRepository

from app.data_mode import (
    DatasetModeReport,
    ModeComparisonReport,
    build_dataset_mode_report,
    compare_mode_reports,
)
from app.source_import import REPOSITORY_ROOT, import_source
from app.source_models import SourceImportResult
from app.source_registry import load_source_registry


class RealDatasetBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    imported: SourceImportResult
    real_report: DatasetModeReport
    demo_report: DatasetModeReport
    comparison: ModeComparisonReport
    graph_nodes_path: Path
    graph_edges_path: Path
    current_manifest_path: Path


def _demo_import_result() -> SourceImportResult:
    demo_root = REPOSITORY_ROOT / "data/modes/demo/current"
    quality_path = demo_root / "silver/silver_jobs.quality.json"
    silver_path = demo_root / "silver/silver_jobs.parquet"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    return SourceImportResult(
        source_id="demo_dataset",
        ingestion_run_id="demo_snapshot",
        raw_record_count=int(quality["raw_row_count"]),
        record_count=pl.read_parquet(silver_path).height,
        rejected_record_count=0,
        bronze_path=REPOSITORY_ROOT / "data/demo/bronze_jobs.csv",
        manifest_path=REPOSITORY_ROOT / "data/demo/source_manifest.json",
        silver_path=silver_path,
        quality_report_path=quality_path,
        canonical_jobs_path=demo_root / "gold/canonical_jobs.parquet",
        job_source_map_path=demo_root / "gold/job_source_map.parquet",
        dedup_report_path=demo_root / "gold/dedup_report.json",
        skills_path=demo_root / "silver/skills.parquet",
        job_skills_path=demo_root / "silver/job_skills.parquet",
        warehouse_path=demo_root / "warehouse/skillworth.duckdb",
        benchmark_path=demo_root / "warehouse/query_benchmark.json",
    )


def _write_current_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_real_dataset(
    artifact_path: Path,
    *,
    source_id: str = "techsalerator_china_jobs_v1",
    data_root: Path = REPOSITORY_ROOT / "data/modes/real",
    config_path: Path = REPOSITORY_ROOT / "data/reference/sources.v1.yml",
) -> RealDatasetBuildResult:
    source = load_source_registry(config_path).get(source_id)
    if source.mode not in {"public_dataset", "research_dataset"}:
        raise ValueError("Real Dataset Mode accepts only reviewed public or research datasets")
    if data_root.resolve() == (REPOSITORY_ROOT / "data").resolve():
        raise ValueError("Real Dataset Mode must use an isolated data root")

    imported = import_source(
        source_id,
        artifact_path,
        data_root=data_root,
        config_path=config_path,
    )
    snapshot_root = imported.warehouse_path.parents[1]
    graph_nodes_path = snapshot_root / "gold/skill_graph_nodes.parquet"
    graph_edges_path = snapshot_root / "gold/skill_graph_edges.parquet"
    AdvancedAnalyticsRepository(imported.warehouse_path).build_skill_network(
        nodes_output_path=graph_nodes_path,
        edges_output_path=graph_edges_path,
    )

    report_dir = data_root / "reports"
    real_report = build_dataset_mode_report(
        mode="real",
        imported=imported,
        output_path=report_dir / "real_dataset_report.json",
    )
    demo_report = build_dataset_mode_report(
        mode="demo",
        imported=_demo_import_result(),
        output_path=report_dir / "demo_dataset_report.json",
    )
    comparison = compare_mode_reports(
        demo_report,
        real_report,
        report_dir / "demo_vs_real.json",
    )
    current_manifest_path = data_root / "current.json"
    _write_current_manifest(
        current_manifest_path,
        {
            "data_mode": "real",
            "source_id": real_report.source_id,
            "ingestion_run_id": imported.ingestion_run_id,
            "warehouse_path": str(imported.warehouse_path.resolve()),
            "stored_raw_artifact_path": (
                str(imported.stored_raw_artifact_path.resolve())
                if imported.stored_raw_artifact_path is not None
                else None
            ),
            "silver_path": str(imported.silver_path.resolve()),
            "canonical_jobs_path": str(imported.canonical_jobs_path.resolve()),
            "job_source_map_path": str(imported.job_source_map_path.resolve()),
            "skills_path": str(imported.skills_path.resolve()),
            "job_skills_path": str(imported.job_skills_path.resolve()),
            "graph_nodes_path": str(graph_nodes_path.resolve()),
            "graph_edges_path": str(graph_edges_path.resolve()),
            "quality_report_path": str(imported.quality_report_path.resolve()),
            "dataset_report_path": str((report_dir / "real_dataset_report.json").resolve()),
            "comparison_report_path": str((report_dir / "demo_vs_real.json").resolve()),
        },
    )
    return RealDatasetBuildResult(
        imported=imported,
        real_report=real_report,
        demo_report=demo_report,
        comparison=comparison,
        graph_nodes_path=graph_nodes_path,
        graph_edges_path=graph_edges_path,
        current_manifest_path=current_manifest_path,
    )
