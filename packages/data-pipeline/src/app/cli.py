from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from app.pipeline import build_silver
from app.annotation_batches import prepare_annotation_batches
from app.annotation_launcher import launch_annotation_workspace
from app.benchmark_status import benchmark_readiness_status
from app.dedup_pipeline import deduplicate_silver
from app.demo_dataset import build_demo_dataset
from app.dedup_benchmark import evaluate_dedup_benchmark
from app.config import load_role_taxonomy
from app.role_benchmark import evaluate_role_benchmark
from app.skill_benchmark import evaluate_benchmark
from app.skill_extraction import RuleSkillExtractor
from app.skill_gold_benchmark import evaluate_skill_gold_benchmark
from app.skill_pipeline import extract_skills
from app.skill_taxonomy import load_skill_taxonomy
from app.source_import import import_source
from app.real_dataset import build_real_dataset
from app.freehire import FreehireSnapshotConfig
from app.freehire_snapshot import build_freehire_china_snapshot
from app.source_registry import list_sources, source_status
from app.warehouse import build_warehouse


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-silver", help="Build Silver Parquet from append-only Bronze data")
    build.add_argument("--input", type=Path, default=REPOSITORY_ROOT / "data/bronze")
    build.add_argument("--output", type=Path)
    build.add_argument("--quality-report", type=Path)
    build.add_argument(
        "--role-taxonomy",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json",
    )
    build.add_argument(
        "--city-taxonomy",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/city_taxonomy.v1.json",
    )
    extract = subparsers.add_parser(
        "extract-skills",
        help="Extract taxonomy skills from Silver jobs with deterministic rules",
    )
    extract.add_argument("--input", type=Path)
    extract.add_argument(
        "--taxonomy",
        type=Path,
        default=REPOSITORY_ROOT / "data/taxonomy/skills.yml",
    )
    extract.add_argument(
        "--benchmark",
        type=Path,
        default=REPOSITORY_ROOT / "data/benchmark/jd_skill_extraction.yml",
    )
    extract.add_argument(
        "--skills-output",
        type=Path,
        default=REPOSITORY_ROOT / "data/silver/skills.parquet",
    )
    extract.add_argument(
        "--job-skills-output",
        type=Path,
        default=REPOSITORY_ROOT / "data/silver/job_skills.parquet",
    )
    extract.add_argument(
        "--benchmark-report",
        type=Path,
        default=REPOSITORY_ROOT / "data/silver/skill_extraction_benchmark.json",
    )
    deduplicate = subparsers.add_parser(
        "deduplicate",
        help="Build conservative Gold canonical jobs and source mappings from Silver jobs",
    )
    deduplicate.add_argument("--input", type=Path)
    deduplicate.add_argument(
        "--canonical-output",
        type=Path,
        default=REPOSITORY_ROOT / "data/gold/canonical_jobs.parquet",
    )
    deduplicate.add_argument(
        "--source-map-output",
        type=Path,
        default=REPOSITORY_ROOT / "data/gold/job_source_map.parquet",
    )
    deduplicate.add_argument(
        "--report",
        type=Path,
        default=REPOSITORY_ROOT / "data/gold/dedup_report.json",
    )
    warehouse = subparsers.add_parser("build-warehouse", help="Build the idempotent DuckDB analytics warehouse")
    warehouse.add_argument(
        "--database",
        type=Path,
        default=REPOSITORY_ROOT / "data/warehouse/skillworth.duckdb",
    )
    warehouse.add_argument(
        "--canonical-jobs",
        type=Path,
        default=REPOSITORY_ROOT / "data/gold/canonical_jobs.parquet",
    )
    warehouse.add_argument(
        "--job-source-map",
        type=Path,
        default=REPOSITORY_ROOT / "data/gold/job_source_map.parquet",
    )
    warehouse.add_argument(
        "--skills",
        type=Path,
        default=REPOSITORY_ROOT / "data/silver/skills.parquet",
    )
    warehouse.add_argument(
        "--job-skills",
        type=Path,
        default=REPOSITORY_ROOT / "data/silver/job_skills.parquet",
    )
    warehouse.add_argument(
        "--benchmark-report",
        type=Path,
        default=REPOSITORY_ROOT / "data/warehouse/query_benchmark.json",
    )
    demo_parser = subparsers.add_parser(
        "build-demo-dataset",
        help="Rebuild deterministic Demo Mode artifacts from the versioned synthetic fixture",
    )
    demo_parser.add_argument("--output-root", type=Path, required=True)
    list_source_parser = subparsers.add_parser("list-sources", help="List configured recruitment data sources")
    list_source_parser.add_argument(
        "--sources-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    )
    source_status_parser = subparsers.add_parser("source-status", help="Show source sync and freshness status")
    source_status_parser.add_argument(
        "--sources-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    )
    source_status_parser.add_argument("--data-root", type=Path, default=REPOSITORY_ROOT / "data")
    import_parser = subparsers.add_parser(
        "import-source",
        help="Import an authorized local export through Bronze, Silver, Dedup, Skills and Warehouse",
    )
    import_parser.add_argument("source_id")
    import_parser.add_argument("artifact", type=Path)
    import_parser.add_argument(
        "--sources-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    )
    import_parser.add_argument("--data-root", type=Path, default=REPOSITORY_ROOT / "data")
    real_parser = subparsers.add_parser(
        "build-real-dataset",
        help="Build an isolated Real Dataset Mode snapshot from a reviewed public dataset",
    )
    real_parser.add_argument("artifact", type=Path)
    real_parser.add_argument("--source-id", default="techsalerator_china_jobs_v1")
    real_parser.add_argument(
        "--sources-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    )
    real_parser.add_argument(
        "--data-root",
        type=Path,
        default=REPOSITORY_ROOT / "data/modes/real",
    )
    freehire_parser = subparsers.add_parser(
        "build-freehire-snapshot",
        help="Build the immutable 2026-08 Freehire China technical snapshot",
    )
    freehire_parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "data/modes/freehire",
    )
    freehire_parser.add_argument(
        "--sources-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/sources.v1.yml",
    )
    freehire_parser.add_argument("--page-size", type=int, default=100)
    freehire_parser.add_argument("--delay-seconds", type=float, default=0.5)
    freehire_parser.add_argument("--maximum-retries", type=int, default=4)

    benchmark_roles = subparsers.add_parser("benchmark-roles", help="Evaluate role rules against split Gold labels")
    benchmark_roles.add_argument("--gold", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/roles/gold.yml")
    benchmark_roles.add_argument("--taxonomy", type=Path, default=REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json")
    benchmark_roles.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    benchmark_roles.add_argument("--report", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/reports/roles.json")

    benchmark_skills = subparsers.add_parser("benchmark-skills", help="Evaluate skill extraction against split Gold labels")
    benchmark_skills.add_argument("--gold", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/skills/gold.yml")
    benchmark_skills.add_argument("--taxonomy", type=Path, default=REPOSITORY_ROOT / "data/taxonomy/skills.yml")
    benchmark_skills.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    benchmark_skills.add_argument("--report", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/reports/skills.json")

    benchmark_dedup = subparsers.add_parser("benchmark-dedup", help="Evaluate dedup pair decisions against split Gold labels")
    benchmark_dedup.add_argument("--gold", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/dedup/gold.yml")
    benchmark_dedup.add_argument("--silver", type=Path)
    benchmark_dedup.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    benchmark_dedup.add_argument("--report", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/reports/dedup.json")

    benchmark_all = subparsers.add_parser("benchmark-all", help="Run all Gold benchmark evaluators without tuning rules")
    benchmark_all.add_argument("--silver", type=Path)
    benchmark_all.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    benchmark_all.add_argument("--report-dir", type=Path, default=REPOSITORY_ROOT / "data/benchmarks/reports")
    benchmark_status = subparsers.add_parser(
        "benchmark-status",
        help="Check annotation batch integrity and human Gold label completeness",
    )
    benchmark_status.add_argument(
        "--benchmark-root",
        type=Path,
        default=REPOSITORY_ROOT / "data/benchmarks",
    )
    benchmark_status.add_argument(
        "--quality-config",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml",
    )
    benchmark_annotate = subparsers.add_parser(
        "benchmark-annotate",
        help="Launch the local human Gold annotation workspace",
    )
    benchmark_annotate.add_argument(
        "--benchmark-root",
        type=Path,
        default=REPOSITORY_ROOT / "data/benchmarks",
    )
    benchmark_annotate.add_argument(
        "--skill-taxonomy",
        type=Path,
        default=REPOSITORY_ROOT / "data/taxonomy/skills.yml",
    )
    benchmark_annotate.add_argument(
        "--role-taxonomy",
        type=Path,
        default=REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json",
    )
    benchmark_annotate.add_argument("--silver", type=Path)
    benchmark_annotate.add_argument("--port", type=int, default=8501)
    prepare_benchmarks = subparsers.add_parser(
        "prepare-benchmark-batches",
        help="Create deterministic unlabeled annotation batches from Silver data",
    )
    prepare_benchmarks.add_argument("--silver", type=Path)
    prepare_benchmarks.add_argument("--output-root", type=Path, default=REPOSITORY_ROOT / "data/benchmarks")
    prepare_benchmarks.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    prepare_benchmarks.add_argument("--role-count", type=int, default=120)
    prepare_benchmarks.add_argument("--skill-count", type=int, default=120)
    prepare_benchmarks.add_argument("--dedup-pair-count", type=int, default=120)
    prepare_batch = subparsers.add_parser(
        "prepare-annotation-batch",
        help="Create one stratified, unlabeled JSONL annotation batch",
    )
    prepare_batch.add_argument("--type", choices=("skills", "roles", "dedup"), required=True)
    prepare_batch.add_argument("--size", type=int, default=100)
    prepare_batch.add_argument("--seed", type=int, default=42)
    prepare_batch.add_argument("--output", type=Path, required=True)
    prepare_batch.add_argument("--silver", type=Path)
    prepare_batch.add_argument("--quality-config", type=Path, default=REPOSITORY_ROOT / "data/reference/benchmark_quality.v1.yml")
    return parser


def _latest_silver_jobs() -> Path:
    silver_dir = REPOSITORY_ROOT / "data/silver"
    excluded = {"skills.parquet", "job_skills.parquet"}
    candidates = [
        path for path in silver_dir.glob("*.parquet")
        if path.name not in excluded and "silver" in path.stem
    ]
    if not candidates:
        raise FileNotFoundError("No Silver job Parquet found; pass --input explicitly")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _latest_real_silver_jobs() -> Path:
    current = REPOSITORY_ROOT / "data/modes/real/current.json"
    if current.is_file():
        path = Path(json.loads(current.read_text(encoding="utf-8"))["silver_path"])
        if path.is_file():
            return path
    snapshot_root = REPOSITORY_ROOT / "data/modes/real/snapshots"
    candidates = list(snapshot_root.glob("*/silver/silver_jobs.parquet"))
    if not candidates:
        raise FileNotFoundError("No Real Dataset Silver snapshot found; pass --silver explicitly")
    return max(candidates, key=lambda path: path.parent.parent.name)


def _annotation_silver_jobs() -> Path | None:
    current = REPOSITORY_ROOT / "data/modes/freehire/current.json"
    if current.is_file():
        path = Path(json.loads(current.read_text(encoding="utf-8"))["silver_path"])
        if path.is_file():
            return path
    candidates = list(
        (REPOSITORY_ROOT / "data/modes/freehire/snapshots").glob(
            "*/pipeline*/snapshots/*/silver/silver_jobs.parquet"
        )
    )
    return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    if args.command == "build-silver":
        run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output_path = args.output or REPOSITORY_ROOT / "data/silver" / f"silver_jobs_{run_stamp}.parquet"
        quality_path = args.quality_report or output_path.with_suffix(".quality.json")
        report = build_silver(
            input_path=args.input,
            output_path=output_path,
            quality_report_path=quality_path,
            role_taxonomy_path=args.role_taxonomy,
            city_taxonomy_path=args.city_taxonomy,
        )
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"silver_output={output_path}")
        print(f"quality_report={quality_path}")
        return 0

    if args.command == "extract-skills":
        input_path = args.input or _latest_silver_jobs()
        if args.benchmark_report.exists():
            raise FileExistsError(f"Benchmark report already exists: {args.benchmark_report}")
        taxonomy = load_skill_taxonomy(args.taxonomy)
        benchmark = evaluate_benchmark(args.benchmark, RuleSkillExtractor(taxonomy))
        extraction_report = extract_skills(
            input_path=input_path,
            taxonomy_path=args.taxonomy,
            skills_output_path=args.skills_output,
            job_skills_output_path=args.job_skills_output,
        )
        benchmark.write_json(args.benchmark_report)
        payload = {
            "input": str(input_path),
            **extraction_report.model_dump(mode="json"),
            **benchmark.model_dump(mode="json"),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"skills_output={args.skills_output}")
        print(f"job_skills_output={args.job_skills_output}")
        print(f"benchmark_report={args.benchmark_report}")
        return 0

    if args.command == "deduplicate":
        input_path = args.input or _latest_silver_jobs()
        report = deduplicate_silver(
            input_path=input_path,
            canonical_output_path=args.canonical_output,
            source_map_output_path=args.source_map_output,
            report_path=args.report,
        )
        print(json.dumps({"input": str(input_path), **report.model_dump(mode="json")}, ensure_ascii=False, indent=2))
        print(f"canonical_output={args.canonical_output}")
        print(f"source_map_output={args.source_map_output}")
        print(f"dedup_report={args.report}")
        return 0

    if args.command == "build-warehouse":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
        report = build_warehouse(
            database_path=args.database,
            canonical_jobs=args.canonical_jobs,
            job_source_map=args.job_source_map,
            skills=args.skills,
            job_skills=args.job_skills,
            benchmark_path=args.benchmark_report,
        )
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"warehouse_database={args.database}")
        print(f"benchmark_report={args.benchmark_report}")
        return 0

    if args.command == "build-demo-dataset":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
        result = build_demo_dataset(output_root=args.output_root)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "list-sources":
        payload = [item.model_dump(mode="json") for item in list_sources(args.sources_config)]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "source-status":
        payload = [item.model_dump(mode="json") for item in source_status(args.sources_config, args.data_root)]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "import-source":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
        result = import_source(
            args.source_id,
            args.artifact,
            data_root=args.data_root,
            config_path=args.sources_config,
        )
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "build-real-dataset":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
        result = build_real_dataset(
            args.artifact,
            source_id=args.source_id,
            data_root=args.data_root,
            config_path=args.sources_config,
        )
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "build-freehire-snapshot":
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
        result = build_freehire_china_snapshot(
            output_root=args.output_root,
            sources_config=args.sources_config,
            snapshot_config=FreehireSnapshotConfig(
                snapshot_id="freehire_china_tech_2026_08",
                page_size=args.page_size,
                delay_seconds=args.delay_seconds,
                maximum_retries=args.maximum_retries,
            ),
        )
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "benchmark-roles":
        result = evaluate_role_benchmark(args.gold, load_role_taxonomy(args.taxonomy), args.quality_config)
        result.write_json(args.report)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"benchmark_status={result.gate.status}")
        print(f"benchmark_report={args.report}")
        return 0

    if args.command == "benchmark-skills":
        taxonomy = load_skill_taxonomy(args.taxonomy)
        result = evaluate_skill_gold_benchmark(args.gold, RuleSkillExtractor(taxonomy), args.quality_config)
        result.write_json(args.report)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"benchmark_status={result.gate.status}")
        print(f"benchmark_report={args.report}")
        return 0

    if args.command == "benchmark-dedup":
        silver = args.silver or _latest_real_silver_jobs()
        result = evaluate_dedup_benchmark(args.gold, silver, args.quality_config)
        result.write_json(args.report)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"benchmark_status={result.gate.status}")
        print(f"benchmark_report={args.report}")
        return 0

    if args.command == "benchmark-all":
        silver = args.silver or _latest_real_silver_jobs()
        args.report_dir.mkdir(parents=True, exist_ok=True)
        roles = evaluate_role_benchmark(
            REPOSITORY_ROOT / "data/benchmarks/roles/gold.yml",
            load_role_taxonomy(REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json"),
            args.quality_config,
        )
        skills = evaluate_skill_gold_benchmark(
            REPOSITORY_ROOT / "data/benchmarks/skills/gold.yml",
            RuleSkillExtractor(load_skill_taxonomy(REPOSITORY_ROOT / "data/taxonomy/skills.yml")),
            args.quality_config,
        )
        dedup = evaluate_dedup_benchmark(
            REPOSITORY_ROOT / "data/benchmarks/dedup/gold.yml",
            silver,
            args.quality_config,
        )
        results = {"roles": roles, "skills": skills, "dedup": dedup}
        for name, result in results.items():
            result.write_json(args.report_dir / f"{name}.json")
        payload = {name: result.model_dump(mode="json") for name, result in results.items()}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print("benchmark_status=" + ",".join(f"{name}:{result.gate.status}" for name, result in results.items()))
        return 0

    if args.command == "benchmark-status":
        result = benchmark_readiness_status(args.benchmark_root, args.quality_config)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        print(f"benchmark_status={result.status}")
        return 0

    if args.command == "benchmark-annotate":
        return launch_annotation_workspace(
            benchmark_root=args.benchmark_root,
            skill_taxonomy_path=args.skill_taxonomy,
            role_taxonomy_path=args.role_taxonomy,
            silver_path=args.silver or _annotation_silver_jobs(),
            port=args.port,
        )

    if args.command == "prepare-benchmark-batches":
        report = prepare_annotation_batches(
            args.silver or _latest_real_silver_jobs(),
            args.output_root,
            args.quality_config,
            role_count=args.role_count,
            skill_count=args.skill_count,
            dedup_pair_count=args.dedup_pair_count,
        )
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    if args.command == "prepare-annotation-batch":
        counts = {"roles": 0, "skills": 0, "dedup": 0}
        counts[args.type] = args.size
        report = prepare_annotation_batches(
            args.silver or _latest_real_silver_jobs(),
            REPOSITORY_ROOT / "data/benchmarks",
            args.quality_config,
            role_count=counts["roles"],
            skill_count=counts["skills"],
            dedup_pair_count=counts["dedup"],
            split_seed=args.seed,
            annotation_type=args.type,
            output=args.output,
        )
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return 0

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
