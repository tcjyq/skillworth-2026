from pathlib import Path

import yaml

from app.config import load_role_taxonomy
from app.role_benchmark import evaluate_role_benchmark


ROOT = Path(__file__).resolve().parents[2]


def test_role_benchmark_separates_splits_and_reports_confusion(tmp_path: Path) -> None:
    gold_path = tmp_path / "roles.yml"
    gold_path.write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "records": [
                    {
                        "record_id": "dev-1",
                        "title": "Data Analyst",
                        "description_excerpt": "SQL reporting",
                        "source": "fixture",
                        "gold_role": "data_analyst",
                        "annotator_notes": "explicit title",
                        "split": "development",
                    },
                    {
                        "record_id": "test-1",
                        "title": "Frontend Engineer",
                        "description_excerpt": "React UI",
                        "source": "fixture",
                        "gold_role": "frontend_engineer",
                        "annotator_notes": "explicit title",
                        "split": "held_out_test",
                    },
                    {
                        "record_id": "test-2",
                        "title": "Accountant",
                        "description_excerpt": "general ledger",
                        "source": "fixture",
                        "gold_role": "other",
                        "annotator_notes": "not a target role",
                        "split": "held_out_test",
                    },
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_role_benchmark(
        gold_path,
        load_role_taxonomy(ROOT / "data/reference/role_taxonomy.v1.json"),
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.development.sample_count == 1
    assert result.held_out_test.sample_count == 2
    assert result.held_out_test.accuracy == 1.0
    assert result.held_out_test.per_role["frontend_engineer"].support == 1
    assert result.held_out_test.confusion_matrix["other"]["other"] == 1
    assert result.gate.status == "INSUFFICIENT BENCHMARK DATA"
    assert result.gate.portfolio_ready is False


def test_empty_role_held_out_split_has_no_misleading_metrics(tmp_path: Path) -> None:
    path = tmp_path / "empty.yml"
    path.write_text("version: test\nrecords: []\n", encoding="utf-8")
    result = evaluate_role_benchmark(
        path,
        load_role_taxonomy(ROOT / "data/reference/role_taxonomy.v1.json"),
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.held_out_test.sample_count == 0
    assert result.held_out_test.accuracy is None
    assert result.held_out_test.macro_f1 is None
    assert result.gate.status == "INSUFFICIENT BENCHMARK DATA"


def test_missed_role_is_zero_not_excluded_from_macro_f1(tmp_path: Path) -> None:
    path = tmp_path / "miss.yml"
    path.write_text(
        """version: test
records:
  - record_id: test-1
    title: Unknown Specialist
    description_excerpt: SQL analysis
    source: fixture
    gold_role: data_analyst
    annotator_notes: title requires human context
    split: held_out_test
""",
        encoding="utf-8",
    )
    result = evaluate_role_benchmark(
        path,
        load_role_taxonomy(ROOT / "data/reference/role_taxonomy.v1.json"),
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.held_out_test.per_role["data_analyst"].precision == 0.0
    assert result.held_out_test.per_role["data_analyst"].recall == 0.0
    assert result.held_out_test.macro_f1 == 0.0
