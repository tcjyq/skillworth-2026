from pathlib import Path

from app.skill_benchmark import evaluate_benchmark
from app.skill_extraction import RuleSkillExtractor
from app.skill_taxonomy import load_skill_taxonomy


ROOT = Path(__file__).resolve().parents[2]


def test_human_annotated_benchmark_covers_required_jd_types() -> None:
    extractor = RuleSkillExtractor(load_skill_taxonomy(ROOT / "data/taxonomy/skills.yml"))
    result = evaluate_benchmark(ROOT / "data/benchmark/jd_skill_extraction.yml", extractor)

    assert {"chinese", "english", "mixed", "tech_dense", "non_technical"} <= result.fixture_types
    assert result.precision >= 0.95
    assert result.recall >= 0.95
    assert result.f1 >= 0.95

