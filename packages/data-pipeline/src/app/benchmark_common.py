from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


INSUFFICIENT_BENCHMARK_DATA = "INSUFFICIENT BENCHMARK DATA"
PASSED = "PASSED"
FAILED = "FAILED"


class BenchmarkMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    created_at: datetime
    label_count: int = Field(ge=0)
    split_seed: int
    taxonomy_version: str
    dedup_version: str
    role_taxonomy_version: str


class QualityGateResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    portfolio_ready: bool
    checks: dict[str, bool]
    warnings: tuple[str, ...]


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def write_json_model(model: BaseModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
