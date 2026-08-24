from pathlib import Path

import polars as pl
import yaml

from app.dedup_benchmark import evaluate_dedup_benchmark


ROOT = Path(__file__).resolve().parents[2]


def _job(job_id: str, *, city: str = "CN-110000") -> dict[str, object]:
    return {
        "silver_job_id": job_id,
        "company_name_normalized": "example company",
        "job_title_normalized": "data analyst",
        "job_title_raw": "Data Analyst",
        "city_code": city,
        "city_raw": city,
        "role_id": "data_analyst",
        "experience_band": "mid",
        "job_description_raw": "SQL dashboards and reporting",
    }


def test_dedup_benchmark_reports_false_merges_and_misses(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.parquet"
    pl.DataFrame(
        [_job("a"), _job("b"), _job("c"), _job("d", city="CN-310000")]
    ).write_parquet(silver_path)
    gold_path = tmp_path / "pairs.yml"
    gold_path.write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "pairs": [
                    {
                        "left_job_id": "a",
                        "right_job_id": "b",
                        "gold_duplicate": True,
                        "difficulty": "easy",
                        "reason": "same posting",
                        "source_pair": "a|b",
                        "notes": "",
                        "split": "held_out_test",
                    },
                    {
                        "left_job_id": "a",
                        "right_job_id": "c",
                        "gold_duplicate": False,
                        "difficulty": "hard",
                        "reason": "same title but different business opening",
                        "source_pair": "a|b",
                        "notes": "false merge guard",
                        "split": "held_out_test",
                    },
                    {
                        "left_job_id": "a",
                        "right_job_id": "d",
                        "gold_duplicate": True,
                        "difficulty": "hard",
                        "reason": "location formatting error in source",
                        "source_pair": "a|b",
                        "notes": "miss example",
                        "split": "held_out_test",
                    },
                ],
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = evaluate_dedup_benchmark(
        gold_path,
        silver_path,
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )

    assert result.held_out_test.precision == 0.5
    assert result.held_out_test.recall == 0.5
    assert result.held_out_test.f1 == 0.5
    assert result.held_out_test.false_merge_rate == 0.5
    assert result.held_out_test.miss_rate == 0.5
    assert len(result.held_out_test.false_merges) == 1
    assert result.gate.status == "INSUFFICIENT BENCHMARK DATA"


def test_empty_dedup_benchmark_returns_null_metrics(tmp_path: Path) -> None:
    silver_path = tmp_path / "silver.parquet"
    pl.DataFrame([_job("a")]).write_parquet(silver_path)
    gold_path = tmp_path / "empty.yml"
    gold_path.write_text("version: test\npairs: []\n", encoding="utf-8")

    result = evaluate_dedup_benchmark(
        gold_path,
        silver_path,
        ROOT / "data/reference/benchmark_quality.v1.yml",
    )
    assert result.held_out_test.precision is None
    assert result.held_out_test.false_merge_rate is None
    assert result.gate.portfolio_ready is False
