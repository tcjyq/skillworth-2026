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
from app.skill_extraction import RuleSkillExtractor


VALID_SPLITS = {"development", "held_out_test"}
AMBIGUITY_TERMS = ("R", "C", "C++", "Go", "AI", "ML", "BI", "CV", "MD", "SQL", "JS", "TS")


class SkillGoldRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_id: str
    title: str
    description: str
    source: str
    language: str
    gold_skills: tuple[str, ...]
    negative_terms: tuple[str, ...] = ()
    difficulty: str = "medium"
    annotator: str = ""
    annotation_notes: str = Field(default="", validation_alias=AliasChoices("annotation_notes", "notes"))
    split: str


class SkillGoldSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str | None = None
    metadata: BenchmarkMetadata | None = None
    records: tuple[SkillGoldRecord, ...]

    @model_validator(mode="after")
    def require_version(self) -> "SkillGoldSet":
        if self.version is None and self.metadata is None:
            raise ValueError("benchmark version metadata is required")
        if self.metadata is not None and self.metadata.label_count != len(self.records):
            raise ValueError("benchmark metadata label_count does not match records")
        return self

    @property
    def benchmark_version(self) -> str:
        return self.metadata.benchmark_version if self.metadata else str(self.version)


class SkillSplitResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_count: int
    micro_precision: float | None
    micro_recall: float | None
    micro_f1: float | None
    macro_precision: float | None
    macro_recall: float | None
    macro_f1: float | None
    exact_match: float | None
    short_alias_precision: float | None
    short_alias_prediction_count: int
    ambiguity_term_prediction_counts: dict[str, int]
    false_positives: tuple[str, ...]
    false_negatives: tuple[str, ...]


class SkillBenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    taxonomy_version: str
    total_sample_count: int
    development: SkillSplitResult
    held_out_test: SkillSplitResult
    gate: QualityGateResult

    def write_json(self, path: Path) -> None:
        write_json_model(self, path)


def _record_ratio(numerator: int, denominator: int, both_empty: bool) -> float:
    if denominator:
        return numerator / denominator
    return 1.0 if both_empty else 0.0


def _evaluate_split(
    records: list[SkillGoldRecord], extractor: RuleSkillExtractor
) -> SkillSplitResult:
    true_positive_count = 0
    predicted_count = 0
    gold_count = 0
    exact_count = 0
    macro_precision_values: list[float] = []
    macro_recall_values: list[float] = []
    false_positives: list[str] = []
    false_negatives: list[str] = []
    short_predictions = 0
    short_true_positives = 0
    ambiguity_counts = {term: 0 for term in AMBIGUITY_TERMS}
    ambiguity_index = {term.casefold(): term for term in AMBIGUITY_TERMS}

    for record in records:
        expected = set(record.gold_skills)
        matches = extractor.extract(f"{record.title}\n{record.description}")
        actual = {match.skill_id for match in matches}
        true_positive = len(expected & actual)
        true_positive_count += true_positive
        predicted_count += len(actual)
        gold_count += len(expected)
        exact_count += int(actual == expected)
        both_empty = not expected and not actual
        macro_precision_values.append(_record_ratio(true_positive, len(actual), both_empty))
        macro_recall_values.append(_record_ratio(true_positive, len(expected), both_empty))
        false_positives.extend(
            f"{record.record_id}:{skill_id}" for skill_id in sorted(actual - expected)
        )
        false_negatives.extend(
            f"{record.record_id}:{skill_id}" for skill_id in sorted(expected - actual)
        )
        for match in matches:
            suite_term = ambiguity_index.get(match.matched_text.casefold())
            if suite_term is None:
                continue
            ambiguity_counts[suite_term] += 1
            short_predictions += 1
            short_true_positives += int(match.skill_id in expected)

    micro_precision = safe_ratio(true_positive_count, predicted_count)
    micro_recall = safe_ratio(true_positive_count, gold_count)
    macro_precision = (
        sum(macro_precision_values) / len(macro_precision_values) if records else None
    )
    macro_recall = sum(macro_recall_values) / len(macro_recall_values) if records else None
    return SkillSplitResult(
        sample_count=len(records),
        micro_precision=micro_precision,
        micro_recall=micro_recall,
        micro_f1=f1_score(micro_precision, micro_recall),
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=f1_score(macro_precision, macro_recall),
        exact_match=safe_ratio(exact_count, len(records)),
        short_alias_precision=safe_ratio(short_true_positives, short_predictions),
        short_alias_prediction_count=short_predictions,
        ambiguity_term_prediction_counts=ambiguity_counts,
        false_positives=tuple(false_positives),
        false_negatives=tuple(false_negatives),
    )


def evaluate_skill_gold_benchmark(
    gold_path: Path,
    extractor: RuleSkillExtractor,
    quality_config_path: Path,
) -> SkillBenchmarkResult:
    gold = SkillGoldSet.model_validate(load_yaml_mapping(gold_path))
    known_skill_ids = {skill.skill_id for skill in extractor.taxonomy.skills}
    unknown_skills = sorted(
        {skill for record in gold.records for skill in record.gold_skills} - known_skill_ids
    )
    invalid_splits = sorted({record.split for record in gold.records} - VALID_SPLITS)
    if unknown_skills:
        raise ValueError(f"Unknown gold skills: {unknown_skills}")
    if invalid_splits:
        raise ValueError(f"Unknown benchmark splits: {invalid_splits}")
    if len({record.record_id for record in gold.records}) != len(gold.records):
        raise ValueError("Skill benchmark record_id values must be unique")

    development = _evaluate_split(
        [record for record in gold.records if record.split == "development"], extractor
    )
    held_out = _evaluate_split(
        [record for record in gold.records if record.split == "held_out_test"], extractor
    )
    gate_config = load_yaml_mapping(quality_config_path)["quality_gates"]["skills"]
    checks = {
        "minimum_gold_samples": len(gold.records) >= gate_config["minimum_gold_samples"],
        "minimum_hard_samples": sum(record.difficulty == "hard" for record in gold.records) >= gate_config["minimum_hard_samples"],
        "minimum_negative_samples": sum(not record.gold_skills for record in gold.records) >= gate_config["minimum_negative_samples"],
        "minimum_held_out_samples": held_out.sample_count
        >= gate_config["minimum_held_out_samples"],
        "minimum_micro_precision": held_out.micro_precision is not None
        and held_out.micro_precision >= gate_config["minimum_micro_precision"],
        "minimum_micro_recall": held_out.micro_recall is not None
        and held_out.micro_recall >= gate_config["minimum_micro_recall"],
        "minimum_short_alias_precision": held_out.short_alias_precision is not None
        and held_out.short_alias_precision >= gate_config["minimum_short_alias_precision"],
    }
    enough_data = all(checks[name] for name in ("minimum_gold_samples", "minimum_held_out_samples", "minimum_hard_samples", "minimum_negative_samples"))
    status = INSUFFICIENT_BENCHMARK_DATA if not enough_data else PASSED if all(checks.values()) else FAILED
    return SkillBenchmarkResult(
        benchmark_version=gold.benchmark_version,
        taxonomy_version=extractor.taxonomy.version,
        total_sample_count=len(gold.records),
        development=development,
        held_out_test=held_out,
        gate=QualityGateResult(
            status=status,
            portfolio_ready=status == PASSED,
            checks=checks,
            warnings=tuple(name for name, passed in checks.items() if not passed),
        ),
    )
