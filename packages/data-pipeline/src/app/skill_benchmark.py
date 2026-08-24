from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.skill_extraction import RuleSkillExtractor


class BenchmarkFixture(BaseModel):
    model_config = ConfigDict(frozen=True)

    fixture_id: str
    fixture_type: str
    text: str
    expected_skill_ids: list[str]


class BenchmarkSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    annotation_method: str
    fixtures: list[BenchmarkFixture]


class BenchmarkResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark_version: str
    fixture_count: int
    fixture_types: set[str]
    true_positive_count: int
    false_positive_count: int
    false_negative_count: int
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1: float = Field(ge=0.0, le=1.0)
    false_positives: list[str]
    false_negatives: list[str]

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_benchmark(path: Path) -> BenchmarkSet:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Benchmark root must be a mapping: {path}")
    return BenchmarkSet.model_validate(payload)


def evaluate_benchmark(path: Path, extractor: RuleSkillExtractor) -> BenchmarkResult:
    benchmark = load_benchmark(path)
    known_skill_ids = {skill.skill_id for skill in extractor.taxonomy.skills}
    unknown_skill_ids = {
        skill_id
        for fixture in benchmark.fixtures
        for skill_id in fixture.expected_skill_ids
        if skill_id not in known_skill_ids
    }
    if unknown_skill_ids:
        raise ValueError(f"Benchmark references unknown skill IDs: {sorted(unknown_skill_ids)}")
    true_positives = 0
    false_positives: list[str] = []
    false_negatives: list[str] = []
    for fixture in benchmark.fixtures:
        expected = set(fixture.expected_skill_ids)
        actual = {match.skill_id for match in extractor.extract(fixture.text)}
        true_positives += len(expected & actual)
        false_positives.extend(f"{fixture.fixture_id}:{skill_id}" for skill_id in sorted(actual - expected))
        false_negatives.extend(f"{fixture.fixture_id}:{skill_id}" for skill_id in sorted(expected - actual))

    fp_count = len(false_positives)
    fn_count = len(false_negatives)
    precision = true_positives / (true_positives + fp_count) if true_positives + fp_count else 1.0
    recall = true_positives / (true_positives + fn_count) if true_positives + fn_count else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return BenchmarkResult(
        benchmark_version=benchmark.version,
        fixture_count=len(benchmark.fixtures),
        fixture_types={fixture.fixture_type for fixture in benchmark.fixtures},
        true_positive_count=true_positives,
        false_positive_count=fp_count,
        false_negative_count=fn_count,
        precision=precision,
        recall=recall,
        f1=f1,
        false_positives=false_positives,
        false_negatives=false_negatives,
    )
