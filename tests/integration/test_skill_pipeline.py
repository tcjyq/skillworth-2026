from pathlib import Path

import polars as pl
import pytest

from app.skill_pipeline import extract_skills


ROOT = Path(__file__).resolve().parents[2]


def test_skill_pipeline_writes_contract_parquets(tmp_path: Path) -> None:
    silver_input = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-1", "job-2"],
            "job_title_raw": ["数据工程师", "销售经理"],
            "job_description_raw": ["熟悉 Python、Spark、k8s 和 PostgreSQL", "负责客户开拓并跟进合同"],
            "record_status": ["valid", "valid"],
        }
    ).write_parquet(silver_input)
    skills_output = tmp_path / "skills.parquet"
    relations_output = tmp_path / "job_skills.parquet"

    report = extract_skills(
        input_path=silver_input,
        taxonomy_path=ROOT / "data/taxonomy/skills.yml",
        skills_output_path=skills_output,
        job_skills_output_path=relations_output,
    )

    assert report.job_count == 2
    assert report.skill_count >= 120
    assert report.job_skill_relation_count == 4
    assert skills_output.exists() and relations_output.exists()
    relations = pl.read_parquet(relations_output)
    assert relations.columns == [
        "silver_job_id", "skill_id", "canonical_skill", "matched_text",
        "extraction_method", "confidence", "taxonomy_version", "raw_skill",
        "mapping_method", "mapping_confidence", "evidence_type",
    ]


def test_skill_pipeline_maps_structured_skills_without_using_llm_summary(tmp_path: Path) -> None:
    silver_input = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-1"],
            "job_title_raw": ["ML Engineer"],
            "job_description_raw": ["Build reliable services."],
            "structured_skills_raw": ['["Postgres", "k8s", "Unknown Skill"]'],
            "description_type": ["llm_summary"],
            "record_status": ["valid"],
        }
    ).write_parquet(silver_input)

    extract_skills(
        input_path=silver_input,
        taxonomy_path=ROOT / "data/taxonomy/skills.yml",
        skills_output_path=tmp_path / "skills.parquet",
        job_skills_output_path=tmp_path / "job_skills.parquet",
    )

    relations = pl.read_parquet(tmp_path / "job_skills.parquet")
    structured = relations.filter(pl.col("evidence_type") == "source_structured_skill")
    assert set(structured["canonical_skill"].to_list()) == {"PostgreSQL", "Kubernetes"}
    assert set(structured["raw_skill"].to_list()) == {"Postgres", "k8s"}
    assert set(structured["mapping_method"].to_list()) == {"taxonomy_alias_exact"}
    assert "Unknown Skill" not in structured["raw_skill"].to_list()


@pytest.mark.parametrize("job_ids", [["job-1", "job-1"], ["job-1", None]])
def test_skill_pipeline_rejects_invalid_silver_job_ids(tmp_path: Path, job_ids: list[str | None]) -> None:
    silver_input = tmp_path / "invalid-silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": job_ids,
            "job_description_raw": ["Python", "SQL"],
            "record_status": ["valid", "valid"],
        }
    ).write_parquet(silver_input)

    with pytest.raises(ValueError, match="silver_job_id"):
        extract_skills(
            input_path=silver_input,
            taxonomy_path=ROOT / "data/taxonomy/skills.yml",
            skills_output_path=tmp_path / "skills.parquet",
            job_skills_output_path=tmp_path / "job_skills.parquet",
        )
