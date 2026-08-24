from __future__ import annotations

from pathlib import Path
from typing import Literal

import polars as pl
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.benchmark_common import (
    FAILED,
    INSUFFICIENT_BENCHMARK_DATA,
    PASSED,
    QualityGateResult,
    BenchmarkMetadata,
    f1_score,
    load_yaml_mapping,
    safe_ratio,
    write_json_model,
)
from app.deduplication import DEDUPLICATION_RULE_VERSION, match_pair


VALID_SPLITS = {"development", "held_out_test"}


class DedupGoldPair(BaseModel):
    model_config = ConfigDict(frozen=True)

    pair_id: str | None = None
    left_job_id: str
    right_job_id: str
    gold_duplicate: bool
    difficulty: Literal["easy", "medium", "hard"]
    reason: str
    source_pair: str
    annotator: str = ""
    annotation_notes: str = Field(default="", validation_alias=AliasChoices("annotation_notes", "notes"))
    split: str


class DedupGoldSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str | None = None
    metadata: BenchmarkMetadata | None = None
    pairs: tuple[DedupGoldPair, ...]

    @model_validator(mode="after")
    def require_version(self) -> "DedupGoldSet":
        if self.version is None and self.metadata is None:
            raise ValueError("benchmark version metadata is required")
        if self.metadata is not None and self.metadata.label_count != len(self.pairs):
            raise ValueError("benchmark metadata label_count does not match pairs")
        return self

    @property
    def benchmark_version(self) -> str:
        return self.metadata.benchmark_version if self.metadata else str(self.version)


class DedupFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    left_job_id: str
    right_job_id: str
    difficulty: str
    reason: str
    predicted_method: str | None


class DedupSplitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    pair_count: int
    positive_pair_count: int
    negative_pair_count: int
    precision: float | None
    recall: float | None
    f1: float | None
    false_merge_rate: float | None
    miss_rate: float | None
    false_merges: tuple[DedupFailure, ...]
    misses: tuple[DedupFailure, ...]
    difficulty_counts: dict[str, int]


class DedupBenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    deduplication_rule_version: str
    total_pair_count: int
    development: DedupSplitResult
    held_out_test: DedupSplitResult
    gate: QualityGateResult

    def write_json(self, path: Path) -> None:
        write_json_model(self, path)


def _evaluate_split(
    pairs: list[DedupGoldPair], jobs: dict[str, dict[str, object]]
) -> DedupSplitResult:
    true_positive = false_positive = false_negative = 0
    false_merges: list[DedupFailure] = []
    misses: list[DedupFailure] = []
    difficulty_counts = {difficulty: 0 for difficulty in ("easy", "medium", "hard")}
    for pair in pairs:
        difficulty_counts[pair.difficulty] += 1
        prediction = match_pair(jobs[pair.left_job_id], jobs[pair.right_job_id])
        predicted_duplicate = prediction is not None
        if pair.gold_duplicate and predicted_duplicate:
            true_positive += 1
        elif not pair.gold_duplicate and predicted_duplicate:
            false_positive += 1
            false_merges.append(
                DedupFailure(
                    left_job_id=pair.left_job_id,
                    right_job_id=pair.right_job_id,
                    difficulty=pair.difficulty,
                    reason=pair.reason,
                    predicted_method=prediction.method if prediction else None,
                )
            )
        elif pair.gold_duplicate and not predicted_duplicate:
            false_negative += 1
            misses.append(
                DedupFailure(
                    left_job_id=pair.left_job_id,
                    right_job_id=pair.right_job_id,
                    difficulty=pair.difficulty,
                    reason=pair.reason,
                    predicted_method=None,
                )
            )

    precision = safe_ratio(true_positive, true_positive + false_positive)
    recall = safe_ratio(true_positive, true_positive + false_negative)
    return DedupSplitResult(
        pair_count=len(pairs),
        positive_pair_count=sum(pair.gold_duplicate for pair in pairs),
        negative_pair_count=sum(not pair.gold_duplicate for pair in pairs),
        precision=precision,
        recall=recall,
        f1=f1_score(precision, recall),
        false_merge_rate=safe_ratio(false_positive, true_positive + false_positive),
        miss_rate=safe_ratio(false_negative, true_positive + false_negative),
        false_merges=tuple(false_merges),
        misses=tuple(misses),
        difficulty_counts=difficulty_counts,
    )


def evaluate_dedup_benchmark(
    gold_path: Path,
    silver_path: Path,
    quality_config_path: Path,
) -> DedupBenchmarkResult:
    gold = DedupGoldSet.model_validate(load_yaml_mapping(gold_path))
    invalid_splits = sorted({pair.split for pair in gold.pairs} - VALID_SPLITS)
    if invalid_splits:
        raise ValueError(f"Unknown benchmark splits: {invalid_splits}")
    pair_keys = [tuple(sorted((pair.left_job_id, pair.right_job_id))) for pair in gold.pairs]
    if any(left == right for left, right in pair_keys) or len(pair_keys) != len(set(pair_keys)):
        raise ValueError("Dedup benchmark pairs must be unique and reference two different jobs")

    rows = pl.read_parquet(silver_path).to_dicts()
    jobs = {str(row["silver_job_id"]): row for row in rows}
    required_ids = {job_id for pair in gold.pairs for job_id in (pair.left_job_id, pair.right_job_id)}
    missing_ids = sorted(required_ids - jobs.keys())
    if missing_ids:
        raise ValueError(f"Dedup benchmark references missing Silver jobs: {missing_ids}")

    development = _evaluate_split(
        [pair for pair in gold.pairs if pair.split == "development"], jobs
    )
    held_out = _evaluate_split(
        [pair for pair in gold.pairs if pair.split == "held_out_test"], jobs
    )
    gate_config = load_yaml_mapping(quality_config_path)["quality_gates"]["dedup"]
    checks = {
        "minimum_gold_pairs": len(gold.pairs) >= gate_config["minimum_gold_pairs"],
        "minimum_held_out_pairs": held_out.pair_count >= gate_config["minimum_held_out_pairs"],
        "minimum_hard_pairs": sum(pair.difficulty == "hard" for pair in gold.pairs) >= gate_config["minimum_hard_pairs"],
        "minimum_precision": held_out.precision is not None
        and held_out.precision >= gate_config["minimum_precision"],
        "minimum_recall": held_out.recall is not None
        and held_out.recall >= gate_config["minimum_recall"],
        "maximum_false_merge_rate": held_out.false_merge_rate is not None
        and held_out.false_merge_rate <= gate_config["maximum_false_merge_rate"],
    }
    enough_data = checks["minimum_gold_pairs"] and checks["minimum_held_out_pairs"] and checks["minimum_hard_pairs"]
    status = INSUFFICIENT_BENCHMARK_DATA if not enough_data else PASSED if all(checks.values()) else FAILED
    return DedupBenchmarkResult(
        benchmark_version=gold.benchmark_version,
        deduplication_rule_version=DEDUPLICATION_RULE_VERSION,
        total_pair_count=len(gold.pairs),
        development=development,
        held_out_test=held_out,
        gate=QualityGateResult(
            status=status,
            portfolio_ready=status == PASSED,
            checks=checks,
            warnings=tuple(name for name, passed in checks.items() if not passed),
        ),
    )
    pair_id: str | None = None
