from pathlib import Path

import polars as pl

from skillworth_analytics.external_benchmark import compare_qarera_benchmark


ROOT = Path(__file__).resolve().parents[2]


def test_qarera_comparison_maps_aliases_but_stays_an_external_rank_comparison(tmp_path: Path) -> None:
    benchmark = tmp_path / "overall.csv"
    pl.DataFrame(
        {
            "skill": ["python", "postgres", "communication"],
            "postings_with_skill": [100, 80, 200],
            "pct_of_all_postings": [10.0, 8.0, 20.0],
        }
    ).write_csv(benchmark)

    report = compare_qarera_benchmark(
        internal_skill_demand=[
            {"skill_id": "database_postgresql", "job_coverage": 0.30},
            {"skill_id": "programming_python", "job_coverage": 0.20},
        ],
        qarera_overall_path=benchmark,
        taxonomy_path=ROOT / "data/taxonomy/skills.yml",
        divergence_rank_threshold=1,
    )

    assert report.source_role == "external_market_benchmark"
    assert report.external_row_count == 3
    assert report.mapped_external_skill_count == 2
    assert report.overlap_skill_count == 2
    assert {item.canonical_skill for item in report.comparisons} == {"Python", "PostgreSQL"}
    assert all(item.divergence_warning for item in report.comparisons)
