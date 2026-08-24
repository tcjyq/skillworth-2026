from pathlib import Path

import yaml

from app.skill_extraction import RuleSkillExtractor
from app.skill_gold_benchmark import evaluate_skill_gold_benchmark
from app.skill_taxonomy import load_skill_taxonomy


ROOT = Path(__file__).resolve().parents[2]


def test_skill_gold_metrics_and_short_alias_precision(tmp_path: Path) -> None:
    path = tmp_path / "skills.yml"
    path.write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "records": [
                    {
                        "record_id": "dev-1",
                        "title": "数据分析师",
                        "description": "使用 Python 与 SQL 分析数据",
                        "source": "fixture",
                        "language": "zh",
                        "gold_skills": ["programming_python", "database_sql"],
                        "negative_terms": [],
                        "notes": "explicit skills",
                        "split": "development",
                    },
                    {
                        "record_id": "test-1",
                        "title": "Frontend",
                        "description": "Build UI with JS",
                        "source": "fixture",
                        "language": "en",
                        "gold_skills": ["programming_javascript"],
                        "negative_terms": [],
                        "notes": "short alias true positive",
                        "split": "held_out_test",
                    },
                    {
                        "record_id": "test-2",
                        "title": "General role",
                        "description": "Go to market planning",
                        "source": "fixture",
                        "language": "en",
                        "gold_skills": [],
                        "negative_terms": ["Go"],
                        "notes": "short alias negative",
                        "split": "held_out_test",
                    },
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    extractor = RuleSkillExtractor(load_skill_taxonomy(ROOT / "data/taxonomy/skills.yml"))

    result = evaluate_skill_gold_benchmark(
        path,
        extractor,
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.development.sample_count == 1
    assert result.held_out_test.sample_count == 2
    assert result.held_out_test.micro_precision == 1.0
    assert result.held_out_test.micro_recall == 1.0
    assert result.held_out_test.exact_match == 1.0
    assert result.held_out_test.short_alias_precision == 1.0
    assert result.held_out_test.false_positives == ()
    assert result.gate.status == "INSUFFICIENT BENCHMARK DATA"


def test_empty_skill_held_out_split_returns_null_metrics(tmp_path: Path) -> None:
    path = tmp_path / "empty.yml"
    path.write_text("version: test\nrecords: []\n", encoding="utf-8")
    extractor = RuleSkillExtractor(load_skill_taxonomy(ROOT / "data/taxonomy/skills.yml"))
    result = evaluate_skill_gold_benchmark(
        path,
        extractor,
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.held_out_test.micro_precision is None
    assert result.held_out_test.micro_recall is None
    assert result.held_out_test.exact_match is None
    assert result.gate.portfolio_ready is False
