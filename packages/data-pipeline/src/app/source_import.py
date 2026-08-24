from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import logging
from pathlib import Path
import shutil
from uuid import uuid4

import polars as pl

from app.connectors import CONNECTOR_VERSION, connector_for
from app.dedup_pipeline import deduplicate_silver
from app.pipeline import build_silver
from app.skill_pipeline import extract_skills
from app.source_models import SourceAdapterConfig, SourceImportManifest, SourceImportResult
from app.source_registry import load_source_registry
from app.warehouse import build_warehouse


LOGGER = logging.getLogger(__name__)
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class DuplicateSourceArtifactError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapped_column(frame: pl.DataFrame, source: SourceAdapterConfig, canonical: str) -> str | None:
    aliases = source.column_mapping.get(canonical, (canonical,))
    return next((alias for alias in aliases if alias in frame.columns), None)


def _to_bronze(
    frame: pl.DataFrame,
    source: SourceAdapterConfig,
    ingestion_run_id: str,
    imported_at: datetime,
    artifact_hash: str,
) -> pl.DataFrame:
    if frame.height == 0:
        raise ValueError("Source artifact contains no records")
    reserved_provenance = ("source_id", "source_record_id", "ingestion_run_id", "observed_at")
    raw_renames = {
        column: f"raw_input__{column}"
        for column in reserved_provenance
        if column in frame.columns
    }
    bronze = frame.rename(raw_renames).with_row_index("_source_row_number", offset=1)
    canonical_fields = (
        "source_job_id", "source_url", "company_name", "job_title", "city", "education",
        "experience", "salary", "published_at", "job_description",
    )
    expressions: list[pl.Expr] = []
    for canonical in canonical_fields:
        if canonical in bronze.columns:
            continue
        column = _mapped_column(bronze, source, canonical)
        expressions.append(
            (pl.col(column).cast(pl.String, strict=False) if column else pl.lit(None, dtype=pl.String)).alias(canonical)
        )
    source_record_id = pl.concat_str(
        [pl.lit(f"{source.source_id}:{artifact_hash[:16]}:"), pl.col("_source_row_number").cast(pl.String)]
    )
    return bronze.with_columns(
        expressions
        + [
            source_record_id.alias("source_record_id"),
            pl.lit(source.source_id).alias("source_id"),
            pl.lit(ingestion_run_id).alias("ingestion_run_id"),
            pl.lit(imported_at.isoformat()).alias("observed_at"),
        ]
    ).drop("_source_row_number")


def _existing_artifact(data_root: Path, source_id: str, artifact_hash: str) -> bool:
    manifest_dir = data_root / "bronze/manifests"
    if not manifest_dir.is_dir():
        return False
    for path in manifest_dir.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("source_id") == source_id and payload.get("raw_artifact_sha256") == artifact_hash:
            return True
    return False


def _write_manifest(path: Path, manifest: SourceImportManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(path)


def _store_raw_artifact(
    artifact_path: Path,
    *,
    data_root: Path,
    source_id: str,
    artifact_hash: str,
) -> Path:
    # The complete digest remains in the manifest and is always revalidated. A
    # 32-character filename avoids Windows MAX_PATH failures in deep snapshot trees.
    target = data_root / "raw_artifacts" / source_id / f"{artifact_hash[:32]}{artifact_path.suffix.lower()}"
    if target.exists():
        if _sha256(target) != artifact_hash:
            raise ValueError(f"Stored raw artifact hash conflict: {target}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".raw-{uuid4().hex[:8]}.tmp{target.suffix}")
    shutil.copyfile(artifact_path, temporary)
    if _sha256(temporary) != artifact_hash:
        temporary.unlink(missing_ok=True)
        raise ValueError("Stored raw artifact failed SHA-256 verification")
    temporary.replace(target)
    return target


def import_source(
    source_id: str,
    artifact_path: Path,
    *,
    data_root: Path,
    config_path: Path,
    dedup_decisions_path: Path | None = None,
) -> SourceImportResult:
    artifact_path = artifact_path.resolve()
    source = load_source_registry(config_path).get(source_id)
    accepted_usage_statuses = {"reviewed"}
    if source.mode == "public_api":
        accepted_usage_statuses.add("no_explicit_block_found")
    if source.data_usage_status not in accepted_usage_statuses:
        raise ValueError(
            f"Source data usage permission is not approved for import: {source_id} "
            f"({source.data_usage_status})"
        )
    if "example.invalid" in source.terms_url:
        raise ValueError(f"Source terms or license must be reviewed before import: {source_id}")
    if source.mode == "authorized_http":
        raise ValueError("Authorized HTTP sources cannot be imported with a local artifact")
    if source.mode == "external_benchmark":
        raise ValueError("External market benchmarks cannot be imported into the jobs pipeline")
    connector = connector_for(source.connector)
    artifact_hash = _sha256(artifact_path)
    if source.expected_sha256 and artifact_hash.lower() != source.expected_sha256.lower():
        raise ValueError(
            f"Source artifact SHA-256 does not match reviewed dataset version: {source_id}"
        )
    if _existing_artifact(data_root, source_id, artifact_hash):
        raise DuplicateSourceArtifactError(f"Artifact was already imported for source {source_id}")
    stored_raw_artifact_path = _store_raw_artifact(
        artifact_path,
        data_root=data_root,
        source_id=source_id,
        artifact_hash=artifact_hash,
    )

    imported_at = datetime.now(UTC)
    ingestion_run_id = f"{imported_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    connector_result = connector.read_result(artifact_path)
    bronze = _to_bronze(connector_result.frame, source, ingestion_run_id, imported_at, artifact_hash)
    bronze_dir = data_root / "bronze"
    bronze_path = bronze_dir / f"bronze_{ingestion_run_id}_{source_id}.parquet"
    if bronze_path.exists():
        raise FileExistsError(f"Bronze output already exists: {bronze_path}")
    bronze_dir.mkdir(parents=True, exist_ok=True)
    temporary_bronze = bronze_path.with_name(f".bronze-{uuid4().hex[:8]}.tmp.parquet")
    bronze.write_parquet(temporary_bronze)
    temporary_bronze.replace(bronze_path)

    manifest_path = bronze_dir / "manifests" / f"{ingestion_run_id}_{source_id}.json"
    manifest = SourceImportManifest(
        source_id=source.source_id,
        source_name=source.source_name,
        source_type=source.source_type,
        analysis_role=source.analysis_role,
        acquisition_method=source.acquisition_method,
        enabled=source.enabled,
        mode=source.mode,
        terms_url=source.terms_url,
        data_usage_status=source.data_usage_status,
        connector=source.connector,
        connector_version=CONNECTOR_VERSION,
        schema_mapping_version=source.schema_mapping_version,
        ingestion_run_id=ingestion_run_id,
        imported_at=imported_at,
        raw_artifact_path=str(artifact_path),
        raw_artifact_sha256=artifact_hash,
        stored_raw_artifact_path=str(stored_raw_artifact_path),
        bronze_path=str(bronze_path),
        raw_record_count=connector_result.raw_record_count,
        record_count=bronze.height,
        rejected_record_count=connector_result.rejected_record_count,
        connector_warnings=connector_result.warnings,
        notes=source.notes,
    )
    _write_manifest(manifest_path, manifest)

    snapshot = data_root / "snapshots" / ingestion_run_id
    silver_path = snapshot / "silver/silver_jobs.parquet"
    quality_report_path = snapshot / "silver/silver_jobs.quality.json"
    canonical_jobs_path = snapshot / "gold/canonical_jobs.parquet"
    job_source_map_path = snapshot / "gold/job_source_map.parquet"
    dedup_report_path = snapshot / "gold/dedup_report.json"
    skills_path = snapshot / "silver/skills.parquet"
    job_skills_path = snapshot / "silver/job_skills.parquet"
    warehouse_path = snapshot / "warehouse/skillworth.duckdb"
    benchmark_path = snapshot / "warehouse/query_benchmark.json"

    LOGGER.info("source_import_stage stage=silver run=%s", ingestion_run_id)
    build_silver(
        input_path=bronze_dir,
        output_path=silver_path,
        quality_report_path=quality_report_path,
        role_taxonomy_path=REPOSITORY_ROOT / "data/reference/role_taxonomy.v1.json",
        city_taxonomy_path=REPOSITORY_ROOT / "data/reference/city_taxonomy.v1.json",
    )
    LOGGER.info("source_import_stage stage=dedup run=%s", ingestion_run_id)
    deduplicate_silver(
        input_path=silver_path,
        canonical_output_path=canonical_jobs_path,
        source_map_output_path=job_source_map_path,
        report_path=dedup_report_path,
        audited_decisions_path=dedup_decisions_path,
    )
    LOGGER.info("source_import_stage stage=skill_extraction run=%s", ingestion_run_id)
    extract_skills(
        input_path=silver_path,
        taxonomy_path=REPOSITORY_ROOT / "data/taxonomy/skills.yml",
        skills_output_path=skills_path,
        job_skills_output_path=job_skills_path,
    )
    LOGGER.info("source_import_stage stage=warehouse run=%s", ingestion_run_id)
    build_warehouse(
        database_path=warehouse_path,
        canonical_jobs=canonical_jobs_path,
        job_source_map=job_source_map_path,
        skills=skills_path,
        job_skills=job_skills_path,
        benchmark_path=benchmark_path,
    )
    return SourceImportResult(
        source_id=source_id,
        ingestion_run_id=ingestion_run_id,
        raw_record_count=connector_result.raw_record_count,
        record_count=bronze.height,
        rejected_record_count=connector_result.rejected_record_count,
        connector_warnings=connector_result.warnings,
        stored_raw_artifact_path=stored_raw_artifact_path,
        bronze_path=bronze_path,
        manifest_path=manifest_path,
        silver_path=silver_path,
        quality_report_path=quality_report_path,
        canonical_jobs_path=canonical_jobs_path,
        job_source_map_path=job_source_map_path,
        dedup_report_path=dedup_report_path,
        skills_path=skills_path,
        job_skills_path=job_skills_path,
        warehouse_path=warehouse_path,
        benchmark_path=benchmark_path,
    )
