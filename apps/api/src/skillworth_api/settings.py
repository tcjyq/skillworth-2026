from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class ApiSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    data_mode: Literal["demo", "real"] = "demo"
    warehouse_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/warehouse/skillworth.duckdb"
    graph_edges_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/gold/skill_graph_edges.parquet"
    quality_report_path: Path = REPOSITORY_ROOT / "data/modes/demo/current/silver/silver_jobs.quality.json"
    cache_ttl_seconds: float = Field(default=60, gt=0, le=3600)
    service_version: str = "phase11_fastapi_v1.1"
    market_scope: str = "demo_dataset"
    source_role: str = "engineering_validation"
    snapshot: str = "demo"
    job_count: int = Field(default=0, ge=0)
    company_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    disclaimer: str = "Demo data only."

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        mode = os.getenv("SKILLWORTH_DATA_MODE", "demo").strip().lower()
        if mode == "demo":
            return cls()
        if mode != "real":
            raise ValueError("SKILLWORTH_DATA_MODE must be demo or real")
        manifest_path = Path(
            os.getenv(
                "SKILLWORTH_REAL_MODE_MANIFEST",
                str(REPOSITORY_ROOT / "data/modes/real/current.json"),
            )
        )
        if not manifest_path.is_file():
            raise FileNotFoundError(f"Real Dataset Mode manifest does not exist: {manifest_path}")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return cls(
            data_mode="real",
            warehouse_path=Path(payload["warehouse_path"]),
            graph_edges_path=Path(payload["graph_edges_path"]),
            quality_report_path=Path(payload["quality_report_path"]),
            market_scope=payload.get("market_scope", "real_dataset"),
            source_role=payload.get("source_role", "unknown"),
            snapshot=payload.get("snapshot", payload.get("snapshot_id", "unknown")),
            job_count=payload.get("job_count", payload.get("canonical_job_count", 0)),
            company_count=payload.get("company_count", 0),
            source_count=payload.get("source_count", 0),
            disclaimer=payload.get("disclaimer", "Real dataset scope is documented in its manifest."),
        )
