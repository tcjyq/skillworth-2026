from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class ApiSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_mode: Literal["demo", "real", "production_safe"] = "demo"
    warehouse_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/warehouse/skillworth.duckdb"
    graph_edges_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/gold/skill_graph_edges.parquet"
    quality_report_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/silver/silver_jobs.quality.json"
    production_safe_artifact_path: Path = REPOSITORY_ROOT / "data/production-safe/current"
    cache_ttl_seconds: float = Field(default=60, gt=0, le=3600)
    service_version: str = "phase11_fastapi_v1.1"
    market_scope: str = "demo_dataset"
    source_role: str = "engineering_validation"
    snapshot: str = "demo"
    access_date: date | None = None
    job_count: int = Field(default=0, ge=0)
    company_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    disclaimer: str = "Demo data only."

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        mode = os.getenv("SKILLWORTH_DATA_MODE", "demo").strip().lower()
        if mode == "demo":
            demo_manifest = os.getenv("SKILLWORTH_DEMO_MODE_MANIFEST")
            if demo_manifest:
                return cls._from_manifest(Path(demo_manifest), data_mode="demo")
            fixture_manifest = REPOSITORY_ROOT / "data/demo/source_manifest.json"
            payload = json.loads(fixture_manifest.read_text(encoding="utf-8"))
            return cls(access_date=_date_from_value(payload.get("imported_at")))
        if mode == "production_safe":
            artifact_root = Path(
                os.getenv(
                    "SKILLWORTH_PRODUCTION_SAFE_ARTIFACT_DIR",
                    str(REPOSITORY_ROOT / "data/production-safe/current"),
                )
            )
            metadata_path = artifact_root / "artifact_metadata.json"
            if not metadata_path.is_file():
                raise FileNotFoundError("Production-safe aggregate artifact is unavailable")
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
            return cls(
                data_mode="production_safe",
                production_safe_artifact_path=artifact_root,
                market_scope=payload["market_scope"],
                source_role=payload["source_role"],
                snapshot=payload["source_snapshot"],
                access_date=_date_from_value(payload.get("access_date")),
                job_count=payload["job_count"],
                company_count=payload["company_count"],
                source_count=payload["source_count"],
                disclaimer=payload["disclaimer"],
            )
        if mode != "real":
            raise ValueError("SKILLWORTH_DATA_MODE must be demo, real or production_safe")
        manifest_path = Path(
            os.getenv(
                "SKILLWORTH_REAL_MODE_MANIFEST",
                str(REPOSITORY_ROOT / "data/modes/real/current.json"),
            )
        )
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Real Dataset Mode manifest does not exist: {manifest_path}")
        return cls._from_manifest(manifest_path, data_mode="real")

    @classmethod
    def _from_manifest(
        cls, manifest_path: Path, *, data_mode: Literal["demo", "real"]
    ) -> "ApiSettings":
        if not manifest_path.is_file():
            raise FileNotFoundError(
                f"{data_mode.title()} Dataset Mode manifest does not exist: {manifest_path}"
            )
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return cls(
            data_mode=data_mode,
            warehouse_path=Path(payload["warehouse_path"]),
            graph_edges_path=Path(payload["graph_edges_path"]),
            quality_report_path=Path(payload["quality_report_path"]),
            market_scope=payload.get("market_scope", f"{data_mode}_dataset"),
            source_role=payload.get("source_role", "unknown"),
            snapshot=payload.get("snapshot", payload.get("snapshot_id", "unknown")),
            access_date=_date_from_value(
                payload.get("access_date") or payload.get("acquired_at")
            ),
            job_count=payload.get("job_count", payload.get("canonical_job_count", 0)),
            company_count=payload.get("company_count", 0),
            source_count=payload.get("source_count", 0),
            disclaimer=payload.get("disclaimer", "Real dataset scope is documented in its manifest."),
        )


def _date_from_value(value: object) -> date | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
