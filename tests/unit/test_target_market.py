from pathlib import Path

import polars as pl

from app.target_market import build_target_market_report, load_target_market_config


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "data/reference/target_market.v1.yml"


def test_target_market_report_uses_evidence_to_separate_source_and_taxonomy_causes(
    tmp_path: Path,
) -> None:
    silver_path = tmp_path / "silver.parquet"
    canonical_path = tmp_path / "canonical.parquet"
    source_map_path = tmp_path / "source_map.parquet"
    job_skills_path = tmp_path / "job_skills.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["s1", "s2", "s3", "s4"],
            "source_id": ["source_a"] * 4,
            "company_name_normalized": ["industrial.example"] * 4,
            "job_title_raw": [
                "Software Engineer",
                "Data Analyst",
                "Production Supervisor",
                "Application Engineer",
            ],
            "job_title_normalized": [
                "software engineer",
                "data analyst",
                "production supervisor",
                "application engineer",
            ],
            "role_id": ["other", "data_analyst", "other", "other"],
            "job_description_raw": [
                "Build Python software.",
                "Analyze data with SQL.",
                "Lead manufacturing production.",
                "Support vehicle applications.",
            ],
        }
    ).write_parquet(silver_path)
    pl.DataFrame(
        {
            "canonical_job_id": ["j1", "j2", "j3", "j4"],
            "canonical_silver_job_id": ["s1", "s2", "s3", "s4"],
        }
    ).write_parquet(canonical_path)
    pl.DataFrame(
        {
            "canonical_job_id": ["j1", "j2", "j3", "j4"],
            "silver_job_id": ["s1", "s2", "s3", "s4"],
            "source_id": ["source_a"] * 4,
        }
    ).write_parquet(source_map_path)
    pl.DataFrame(
        {
            "silver_job_id": ["s1", "s2"],
            "skill_id": ["programming_python", "database_sql"],
        }
    ).write_parquet(job_skills_path)

    report = build_target_market_report(
        silver_path=silver_path,
        canonical_path=canonical_path,
        source_map_path=source_map_path,
        job_skills_path=job_skills_path,
        config=load_target_market_config(CONFIG),
    )

    assert report.classification_counts == {
        "target": 2,
        "possible": 1,
        "non_target": 1,
    }
    assert report.explicit_target_current_other_count == 1
    assert report.extracted_skill_job_count == 2
    assert report.other_primary_cause == "C_both_source_composition_and_taxonomy_recall"
    assert report.other_primary_cause_evidence.source_mismatch_detected is True
    assert report.other_primary_cause_evidence.taxonomy_recall_gap_detected is True


def test_unmatched_titles_are_possible_instead_of_guessed_non_target(tmp_path: Path) -> None:
    config = load_target_market_config(CONFIG)

    assert config.classify_title("System Integration Specialist").classification == "possible"
    assert config.classify_title("Finance Accountant").classification == "non_target"
    assert config.classify_title("Backend Developer").classification == "target"
