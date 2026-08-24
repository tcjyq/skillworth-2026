from pathlib import Path

import polars as pl
import yaml

from app.annotation_batches import prepare_annotation_batches


ROOT = Path(__file__).resolve().parents[2]


def test_prepare_annotation_batches_writes_unlabeled_real_samples(tmp_path: Path) -> None:
    silver = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["a", "b", "c", "d"],
            "job_title_raw": ["Data Analyst", "Data Analyst", "Production Supervisor", "Backend Engineer"],
            "job_title_normalized": ["data analyst", "data analyst", "production supervisor", "backend engineer"],
            "job_description_raw": ["SQL and Python", "SQL and Python", "factory operations", "Build Java APIs"],
            "source_id": ["source_a", "source_b", "source_a", "source_a"],
            "company_name_normalized": ["company", "company", "factory", "company"],
            "city_code": ["CN-11", "CN-11", "CN-31", "CN-11"],
            "role_id": ["data_analyst", "data_analyst", "other", "backend_engineer"],
            "experience_band": ["mid", "mid", "mid", "mid"],
        }
    ).write_parquet(silver)

    report = prepare_annotation_batches(
        silver,
        tmp_path / "benchmarks",
        ROOT / "data/reference/benchmark_quality.v1.yml",
        role_count=4,
        skill_count=4,
        dedup_pair_count=4,
    )

    assert report.role_sample_count == 4
    assert report.skill_sample_count == 4
    assert report.dedup_pair_count > 0
    roles = yaml.safe_load((tmp_path / "benchmarks/roles/pending/batch.yml").read_text(encoding="utf-8"))
    pairs = yaml.safe_load((tmp_path / "benchmarks/dedup/pending/batch.yml").read_text(encoding="utf-8"))
    assert all(record["gold_role"] is None for record in roles["records"])
    assert all(pair["gold_duplicate"] is None for pair in pairs["pairs"])
    assert all("predicted_role" in record and "difficulty" in record for record in roles["records"])
    assert all("pair_id" in pair and "predicted_duplicate" in pair for pair in pairs["pairs"])
    assert roles["metadata"]["split_seed"] == 42
