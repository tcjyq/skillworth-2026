from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from skillworth_analytics import (
    AdvancedAnalyticsRepository,
    AnalyticsFilters,
    build_china_skillworth_summary,
    build_china_skillworth_visual_ready,
    load_china_skillworth_config,
    load_data_confidence_config,
)

from app.dedup_pipeline import deduplicate_silver
from app.pipeline import build_silver
from app.skill_pipeline import extract_skills
from app.warehouse import build_warehouse


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class DemoDatasetBuildResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    output_root: Path
    manifest_path: Path
    warehouse_path: Path
    graph_edges_path: Path
    job_count: int
    company_count: int
    skill_count: int


def build_demo_dataset(*, output_root: Path) -> DemoDatasetBuildResult:
    """Rebuild the synthetic Demo Mode artifacts through the production pipeline."""
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"Demo output root already exists: {output_root}")

    fixture = REPOSITORY_ROOT / "data/demo/bronze_jobs.csv"
    source_manifest = json.loads(
        (REPOSITORY_ROOT / "data/demo/source_manifest.json").read_text(encoding="utf-8")
    )
    fixture_hash = sha256(fixture.read_bytes()).hexdigest()
    if fixture_hash != source_manifest["raw_artifact_sha256"]:
        raise ValueError("Demo fixture SHA-256 does not match its versioned source manifest")
    snapshot_at = datetime.fromisoformat(source_manifest["imported_at"])
    snapshot_id = f"demo-{snapshot_at.date().isoformat()}"

    silver_dir = output_root / "silver"
    gold_dir = output_root / "gold"
    warehouse_dir = output_root / "warehouse"
    silver_jobs = silver_dir / "silver_jobs.parquet"
    quality_report = silver_dir / "silver_jobs.quality.json"
    skills = silver_dir / "skills.parquet"
    job_skills = silver_dir / "job_skills.parquet"
    canonical_jobs = gold_dir / "canonical_jobs.parquet"
    job_source_map = gold_dir / "job_source_map.parquet"
    dedup_report = gold_dir / "dedup_report.json"
    graph_nodes = gold_dir / "skill_graph_nodes.parquet"
    graph_edges = gold_dir / "skill_graph_edges.parquet"
    warehouse = warehouse_dir / "skillworth.duckdb"
    query_benchmark = warehouse_dir / "query_benchmark.json"

    build_silver(
        input_path=fixture,
        output_path=silver_jobs,
        quality_report_path=quality_report,
        role_taxonomy_path=REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json",
        city_taxonomy_path=REPOSITORY_ROOT / "data/reference/city_taxonomy.v1.json",
    )
    deduplicate_silver(
        input_path=silver_jobs,
        canonical_output_path=canonical_jobs,
        source_map_output_path=job_source_map,
        report_path=dedup_report,
    )
    extract_skills(
        input_path=silver_jobs,
        taxonomy_path=REPOSITORY_ROOT / "data/taxonomy/skills.yml",
        skills_output_path=skills,
        job_skills_output_path=job_skills,
    )
    build_warehouse(
        database_path=warehouse,
        canonical_jobs=canonical_jobs,
        job_source_map=job_source_map,
        skills=skills,
        job_skills=job_skills,
        benchmark_path=query_benchmark,
    )
    AdvancedAnalyticsRepository(warehouse).build_skill_network(
        nodes_output_path=graph_nodes,
        edges_output_path=graph_edges,
        filters=AnalyticsFilters(market_scope="all", source_scope="all"),
    )

    china_config = load_china_skillworth_config(
        REPOSITORY_ROOT / "data/reference/china_skillworth.v1.yml"
    )
    confidence_config = load_data_confidence_config(
        REPOSITORY_ROOT / "data/reference/data_confidence.v1.yml"
    )
    summary = build_china_skillworth_summary(
        database_path=warehouse,
        graph_nodes_path=graph_nodes,
        graph_edges_path=graph_edges,
        snapshot_id=snapshot_id,
        snapshot_completed_at=snapshot_at,
        config=china_config,
        confidence_config=confidence_config,
    )
    build_china_skillworth_visual_ready(
        database_path=warehouse,
        snapshot_id=snapshot_id,
        snapshot_completed_at=snapshot_at,
        config=china_config,
        confidence_config=confidence_config,
    )

    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "data_mode": "demo",
                "warehouse_path": str(warehouse),
                "graph_edges_path": str(graph_edges),
                "quality_report_path": str(quality_report),
                "market_scope": "demo_dataset",
                "source_role": "engineering_validation",
                "snapshot": snapshot_id,
                "access_date": snapshot_at.date().isoformat(),
                "job_count": summary.job_count,
                "company_count": summary.company_count,
                "source_count": summary.source_count,
                "disclaimer": "仅用于工程验证的公开合成数据，不代表真实招聘市场。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return DemoDatasetBuildResult(
        output_root=output_root,
        manifest_path=manifest_path,
        warehouse_path=warehouse,
        graph_edges_path=graph_edges,
        job_count=summary.job_count,
        company_count=summary.company_count,
        skill_count=summary.skill_count,
    )
