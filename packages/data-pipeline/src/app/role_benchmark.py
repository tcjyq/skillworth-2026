from __future__ import annotations

from pathlib import Path

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
from app.config import RoleTaxonomy
from app.normalization import normalize_role


VALID_SPLITS = {"development", "held_out_test"}


class RoleGoldRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_id: str
    title: str
    description_excerpt: str
    source: str
    gold_role: str
    difficulty: str = "medium"
    annotator: str = ""
    annotation_notes: str = Field(default="", validation_alias=AliasChoices("annotation_notes", "annotator_notes"))
    split: str


class RoleGoldSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str | None = None
    metadata: BenchmarkMetadata | None = None
    records: tuple[RoleGoldRecord, ...]

    @model_validator(mode="after")
    def require_version(self) -> "RoleGoldSet":
        if self.version is None and self.metadata is None:
            raise ValueError("benchmark version metadata is required")
        if self.metadata is not None and self.metadata.label_count != len(self.records):
            raise ValueError("benchmark metadata label_count does not match records")
        return self

    @property
    def benchmark_version(self) -> str:
        return self.metadata.benchmark_version if self.metadata else str(self.version)


class RoleMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    precision: float | None
    recall: float | None
    f1: float | None
    support: int


class RoleSplitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_count: int
    accuracy: float | None
    macro_precision: float | None
    macro_recall: float | None
    macro_f1: float | None
    per_role: dict[str, RoleMetrics]
    confusion_matrix: dict[str, dict[str, int]]


class RoleBenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    taxonomy_version: str
    total_sample_count: int
    development: RoleSplitResult
    held_out_test: RoleSplitResult
    gate: QualityGateResult

    def write_json(self, path: Path) -> None:
        write_json_model(self, path)


def _evaluate_split(
    records: list[RoleGoldRecord], taxonomy: RoleTaxonomy
) -> RoleSplitResult:
    role_ids = [rule.id for rule in taxonomy.roles]
    confusion = {gold: {predicted: 0 for predicted in role_ids} for gold in role_ids}
    correct = 0
    for record in records:
        predicted = normalize_role(record.title, taxonomy).role_id
        confusion[record.gold_role][predicted] += 1
        correct += int(predicted == record.gold_role)

    per_role: dict[str, RoleMetrics] = {}
    supported_metrics: list[RoleMetrics] = []
    for role_id in role_ids:
        true_positive = confusion[role_id][role_id]
        false_positive = sum(confusion[gold][role_id] for gold in role_ids if gold != role_id)
        false_negative = sum(confusion[role_id][predicted] for predicted in role_ids if predicted != role_id)
        support = sum(confusion[role_id].values())
        precision = safe_ratio(true_positive, true_positive + false_positive)
        recall = safe_ratio(true_positive, true_positive + false_negative)
        if support and precision is None:
            precision = 0.0
        metrics = RoleMetrics(
            precision=precision,
            recall=recall,
            f1=f1_score(precision, recall),
            support=support,
        )
        per_role[role_id] = metrics
        if support:
            supported_metrics.append(metrics)

    def macro(field: str) -> float | None:
        values = [getattr(metric, field) for metric in supported_metrics]
        defined = [value for value in values if value is not None]
        return sum(defined) / len(defined) if defined else None

    return RoleSplitResult(
        sample_count=len(records),
        accuracy=safe_ratio(correct, len(records)),
        macro_precision=macro("precision"),
        macro_recall=macro("recall"),
        macro_f1=macro("f1"),
        per_role=per_role,
        confusion_matrix=confusion,
    )


def evaluate_role_benchmark(
    gold_path: Path,
    taxonomy: RoleTaxonomy,
    quality_config_path: Path,
) -> RoleBenchmarkResult:
    gold = RoleGoldSet.model_validate(load_yaml_mapping(gold_path))
    role_ids = {rule.id for rule in taxonomy.roles}
    invalid_roles = sorted({record.gold_role for record in gold.records} - role_ids)
    invalid_splits = sorted({record.split for record in gold.records} - VALID_SPLITS)
    if invalid_roles:
        raise ValueError(f"Unknown gold roles: {invalid_roles}")
    if invalid_splits:
        raise ValueError(f"Unknown benchmark splits: {invalid_splits}")
    if len({record.record_id for record in gold.records}) != len(gold.records):
        raise ValueError("Role benchmark record_id values must be unique")

    development = _evaluate_split(
        [record for record in gold.records if record.split == "development"], taxonomy
    )
    held_out = _evaluate_split(
        [record for record in gold.records if record.split == "held_out_test"], taxonomy
    )
    gate_config = load_yaml_mapping(quality_config_path)["quality_gates"]["roles"]
    target_roles = role_ids - {taxonomy.fallback_role}
    minimum_per_role_met = all(
        held_out.per_role[role].support >= gate_config["minimum_samples_per_target_role"]
        for role in target_roles
    )
    checks = {
        "minimum_gold_samples": len(gold.records) >= gate_config["minimum_gold_samples"],
        "minimum_held_out_samples": held_out.sample_count
        >= gate_config["minimum_held_out_samples"],
        "minimum_samples_per_target_role": minimum_per_role_met,
        "minimum_macro_f1": held_out.macro_f1 is not None
        and held_out.macro_f1 >= gate_config["minimum_macro_f1"],
    }
    enough_data = all(
        checks[name]
        for name in (
            "minimum_gold_samples",
            "minimum_held_out_samples",
            "minimum_samples_per_target_role",
        )
    )
    status = INSUFFICIENT_BENCHMARK_DATA if not enough_data else PASSED if all(checks.values()) else FAILED
    warnings = tuple(name for name, passed in checks.items() if not passed)
    return RoleBenchmarkResult(
        benchmark_version=gold.benchmark_version,
        taxonomy_version=taxonomy.version,
        total_sample_count=len(gold.records),
        development=development,
        held_out_test=held_out,
        gate=QualityGateResult(
            status=status,
            portfolio_ready=status == PASSED,
            checks=checks,
            warnings=warnings,
        ),
    )
