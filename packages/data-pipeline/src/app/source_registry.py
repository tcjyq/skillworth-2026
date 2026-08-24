from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import yaml

from app.source_models import SourceImportManifest, SourceMetadata, SourceRegistry


def load_source_registry(path: Path) -> SourceRegistry:
    if not path.is_file():
        raise FileNotFoundError(f"Source registry does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return SourceRegistry.model_validate(yaml.safe_load(handle))


def _default_manifests(data_root: Path) -> list[SourceImportManifest]:
    manifest_dir = data_root / "bronze/manifests"
    if not manifest_dir.is_dir():
        return []
    manifests: list[SourceImportManifest] = []
    for path in sorted(manifest_dir.glob("*.json")):
        manifests.append(SourceImportManifest.model_validate(json.loads(path.read_text(encoding="utf-8"))))
    return manifests


def _current_mode_manifests(data_root: Path) -> list[SourceImportManifest]:
    modes_dir = data_root / "modes"
    if not modes_dir.is_dir():
        return []

    manifests: list[SourceImportManifest] = []
    for current_path in sorted(modes_dir.glob("*/current.json")):
        current = json.loads(current_path.read_text(encoding="utf-8"))
        source_id = current.get("source_id")
        ingestion_run_id = current.get("ingestion_run_id")
        if not source_id or not ingestion_run_id:
            raise ValueError(f"Mode pointer is missing source_id or ingestion_run_id: {current_path}")
        if str(source_id).startswith("multi_source:"):
            expected_sources = set(str(source_id).split(":", 1)[1].split(","))
            warehouse_path = Path(str(current.get("warehouse_path", "")))
            dataset_root = warehouse_path.parents[3] if len(warehouse_path.parents) > 3 else current_path.parent
            candidates = list((dataset_root / "bronze/manifests").glob("*.json"))
            selected = []
            for candidate in candidates:
                manifest = SourceImportManifest.model_validate(
                    json.loads(candidate.read_text(encoding="utf-8"))
                )
                if manifest.source_id in expected_sources:
                    selected.append(manifest)
            if {manifest.source_id for manifest in selected} != expected_sources:
                raise FileNotFoundError(
                    f"Current multi-source mode is missing manifests for {sorted(expected_sources)}"
                )
            manifests.extend(selected)
            continue
        candidates = list(current_path.parent.glob(f"**/bronze/manifests/{ingestion_run_id}*.json"))
        if len(candidates) != 1:
            raise FileNotFoundError(
                f"Expected one manifest for current mode run {ingestion_run_id}, found {len(candidates)}"
            )
        manifest = SourceImportManifest.model_validate(
            json.loads(candidates[0].read_text(encoding="utf-8"))
        )
        if manifest.source_id != source_id:
            raise ValueError(f"Mode pointer source does not match manifest: {current_path}")
        manifests.append(manifest)
    return manifests


def _manifests(data_root: Path) -> list[SourceImportManifest]:
    by_run: dict[tuple[str, str], SourceImportManifest] = {}
    for manifest in [*_default_manifests(data_root), *_current_mode_manifests(data_root)]:
        by_run[(manifest.source_id, manifest.ingestion_run_id)] = manifest
    return list(by_run.values())


def source_status(config_path: Path, data_root: Path) -> tuple[SourceMetadata, ...]:
    registry = load_source_registry(config_path)
    manifests = _manifests(data_root)
    now = datetime.now(UTC)
    result: list[SourceMetadata] = []
    for source in registry.sources:
        matching = [manifest for manifest in manifests if manifest.source_id == source.source_id]
        last_sync = max((manifest.imported_at for manifest in matching), default=None)
        freshness = "never"
        if last_sync is not None:
            freshness = "fresh" if now - last_sync <= timedelta(days=registry.freshness_days) else "stale"
        result.append(
            SourceMetadata(
                source_id=source.source_id,
                source_name=source.source_name,
                acquisition_method=source.acquisition_method,
                analysis_role=source.analysis_role,
                enabled=source.enabled,
                mode=source.mode,
                terms_url=source.terms_url,
                data_usage_status=source.data_usage_status,
                last_sync=last_sync,
                record_count=sum(manifest.record_count for manifest in matching),
                freshness=freshness,
                notes=source.notes,
            )
        )
    return tuple(result)


def list_sources(config_path: Path) -> tuple[SourceMetadata, ...]:
    registry = load_source_registry(config_path)
    return tuple(
        SourceMetadata(
            source_id=source.source_id,
            source_name=source.source_name,
            acquisition_method=source.acquisition_method,
            analysis_role=source.analysis_role,
            enabled=source.enabled,
            mode=source.mode,
            terms_url=source.terms_url,
            data_usage_status=source.data_usage_status,
            notes=source.notes,
        )
        for source in registry.sources
    )
