from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


BenchmarkName = Literal["skills", "roles", "dedup"]


class BenchmarkCollectionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: BenchmarkName
    pending_count: int = Field(ge=0)
    unlabeled_count: int = Field(ge=0)
    gold_count: int = Field(ge=0)
    development_count: int = Field(ge=0)
    held_out_test_count: int = Field(ge=0)
    minimum_gold_samples: int = Field(ge=0)
    remaining_to_gate: int = Field(ge=0)
    unique_sample_ids: bool
    stable_sample_ids: bool
    deterministic_split: bool
    prediction_gold_separated: bool
    notes_available: bool
    gold_ids_valid: bool
    human_confirmed: bool


class BenchmarkReadinessStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["READY FOR EVALUATION", "NOT READY"]
    pending_sample_count: int = Field(ge=0)
    unlabeled_sample_count: int = Field(ge=0)
    gold_sample_count: int = Field(ge=0)
    collections: list[BenchmarkCollectionStatus]
    warnings: list[str]


_CONFIG = {
    "skills": {
        "rows_key": "records",
        "id_key": "record_id",
        "gold_key": "gold_skills",
        "prediction_key": "predicted_skills",
        "gate_key": "minimum_gold_samples",
    },
    "roles": {
        "rows_key": "records",
        "id_key": "record_id",
        "gold_key": "gold_role",
        "prediction_key": "predicted_role",
        "gate_key": "minimum_gold_samples",
    },
    "dedup": {
        "rows_key": "pairs",
        "id_key": "pair_id",
        "gold_key": "gold_duplicate",
        "prediction_key": "predicted_duplicate",
        "gate_key": "minimum_gold_pairs",
    },
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Benchmark file does not exist: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark file must contain a mapping: {path}")
    return payload


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _expected_split(sample_key: str, seed: int) -> str:
    return "development" if int(_hash(f"{seed}:{sample_key}")[:8], 16) % 10 < 3 else "held_out_test"


def _stable_id(benchmark: BenchmarkName, row: dict[str, Any], sample_id: str) -> bool:
    if not sample_id:
        return False
    if benchmark != "dedup":
        return True
    left_id = str(row.get("left_job_id") or "").strip()
    right_id = str(row.get("right_job_id") or "").strip()
    if not left_id or not right_id:
        return False
    expected = _hash("|".join(sorted((left_id, right_id))))[:24]
    return sample_id == expected


def _split_key(benchmark: BenchmarkName, row: dict[str, Any], sample_id: str) -> str:
    if benchmark != "dedup":
        return sample_id
    return "|".join(sorted((str(row.get("left_job_id") or ""), str(row.get("right_job_id") or ""))))


def benchmark_readiness_status(
    benchmark_root: Path,
    quality_config_path: Path,
) -> BenchmarkReadinessStatus:
    quality = _load_yaml(quality_config_path).get("quality_gates", {})
    collections: list[BenchmarkCollectionStatus] = []
    warnings: list[str] = []

    for benchmark in ("skills", "roles", "dedup"):
        config = _CONFIG[benchmark]
        pending_payload = _load_yaml(benchmark_root / benchmark / "pending" / "batch.yml")
        gold_payload = _load_yaml(benchmark_root / benchmark / "gold.yml")
        pending_rows = pending_payload.get(config["rows_key"], [])
        gold_rows = gold_payload.get(config["rows_key"], [])
        if not isinstance(pending_rows, list) or not isinstance(gold_rows, list):
            raise ValueError(f"{benchmark} benchmark rows must be a list")

        seed = int(pending_payload.get("metadata", {}).get("split_seed", 42))
        ids = [str(row.get(config["id_key"]) or "").strip() for row in pending_rows]
        gold_ids = [str(row.get(config["id_key"]) or "").strip() for row in gold_rows]
        gold_ids_valid = (
            len(gold_ids) == len(set(gold_ids))
            and all(gold_ids)
            and set(gold_ids).issubset(set(ids))
        )
        human_confirmed = all(row.get("human_confirmed") is True for row in gold_rows)
        unlabeled_count = len(set(ids) - set(gold_ids)) if gold_ids_valid else len(ids)
        minimum = int(quality.get(benchmark, {}).get(config["gate_key"], 0))
        development_count = sum(row.get("split") == "development" for row in pending_rows)
        held_out_count = sum(row.get("split") == "held_out_test" for row in pending_rows)
        stable_ids = all(_stable_id(benchmark, row, sample_id) for row, sample_id in zip(pending_rows, ids))
        deterministic_split = all(
            row.get("split") == _expected_split(_split_key(benchmark, row, sample_id), seed)
            for row, sample_id in zip(pending_rows, ids)
        )
        prediction_gold_separated = all(
            config["prediction_key"] in row and config["gold_key"] in row
            for row in pending_rows
        )
        notes_available = all("annotation_notes" in row for row in pending_rows)

        collection = BenchmarkCollectionStatus(
            benchmark=benchmark,
            pending_count=len(pending_rows),
            unlabeled_count=unlabeled_count,
            gold_count=len(gold_rows),
            development_count=development_count,
            held_out_test_count=held_out_count,
            minimum_gold_samples=minimum,
            remaining_to_gate=max(minimum - len(gold_rows), 0),
            unique_sample_ids=bool(ids) and len(ids) == len(set(ids)) and all(ids),
            stable_sample_ids=stable_ids,
            deterministic_split=deterministic_split,
            prediction_gold_separated=prediction_gold_separated,
            notes_available=notes_available,
            gold_ids_valid=gold_ids_valid,
            human_confirmed=human_confirmed,
        )
        collections.append(collection)
        if collection.gold_count < collection.minimum_gold_samples:
            warnings.append(
                f"{benchmark}: {collection.remaining_to_gate} additional human Gold labels required for the configured sample gate"
            )
        for check_name in (
            "unique_sample_ids",
            "stable_sample_ids",
            "deterministic_split",
            "prediction_gold_separated",
            "notes_available",
            "gold_ids_valid",
            "human_confirmed",
        ):
            if not getattr(collection, check_name):
                warnings.append(f"{benchmark}: readiness check failed: {check_name}")

    ready = all(
        item.gold_count == item.pending_count
        and item.unlabeled_count == 0
        and item.unique_sample_ids
        and item.stable_sample_ids
        and item.deterministic_split
        and item.prediction_gold_separated
        and item.notes_available
        and item.gold_ids_valid
        and item.human_confirmed
        for item in collections
    )
    return BenchmarkReadinessStatus(
        status="READY FOR EVALUATION" if ready else "NOT READY",
        pending_sample_count=sum(item.pending_count for item in collections),
        unlabeled_sample_count=sum(item.unlabeled_count for item in collections),
        gold_sample_count=sum(item.gold_count for item in collections),
        collections=collections,
        warnings=warnings,
    )
