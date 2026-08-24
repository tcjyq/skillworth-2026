from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb

from skillworth_analytics.skill_relations import (
    ExploratoryRelationConfig,
    SkillRelationRepository,
)


def _warehouse(tmp_path: Path) -> Path:
    database = tmp_path / "relations.duckdb"
    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            "CREATE TABLE jobs(canonical_job_id VARCHAR, role_id VARCHAR, published_at DATE)"
        )
        connection.execute(
            "INSERT INTO jobs VALUES "
            "('j1','data_engineer','2026-08-01'),"
            "('j2','data_engineer','2026-08-02'),"
            "('j3','backend_engineer','2026-08-03'),"
            "('j4','data_engineer','2025-01-01')"
        )
        connection.execute(
            "CREATE TABLE skills(skill_id VARCHAR, canonical_name VARCHAR, category VARCHAR)"
        )
        connection.execute(
            "INSERT INTO skills VALUES "
            "('python','Python','programming'),"
            "('sql','SQL','database'),"
            "('spark','Apache Spark','data_engineering'),"
            "('docker','Docker','devops')"
        )
        connection.execute(
            "CREATE TABLE job_skills(canonical_job_id VARCHAR, skill_id VARCHAR)"
        )
        connection.execute(
            "INSERT INTO job_skills VALUES "
            "('j1','python'),('j1','sql'),('j1','spark'),"
            "('j2','python'),('j2','sql'),('j2','docker'),"
            "('j3','python'),('j3','docker'),"
            "('j4','python'),('j4','spark')"
        )
    finally:
        connection.close()
    return database


def _config() -> ExploratoryRelationConfig:
    return ExploratoryRelationConfig(
        version="exploratory-relations-test-v1",
        minimum_cooccurrence_count=2,
        minimum_jaccard=0.01,
        role_normal_sample_size=10,
        role_small_sample_minimum=4,
    )


def test_relation_query_uses_canonical_job_denominator_and_support_gate(
    tmp_path: Path,
) -> None:
    result = SkillRelationRepository(_warehouse(tmp_path), _config()).related_skills(
        core_skill_id="python",
        recency_window="180d",
        as_of_date=date(2026, 8, 10),
    )

    assert result.sample_size == 3
    assert result.core_job_count == 3
    assert [record.related_skill_id for record in result.records] == ["docker", "sql"]
    sql = next(record for record in result.records if record.related_skill_id == "sql")
    assert sql.cooccurrence_count == 2
    assert sql.core_conditional_coverage == 2 / 3
    assert sql.jaccard == 2 / 3
    assert sql.evidence_status == "supported"
    assert result.metadata.config_version == "exploratory-relations-test-v1"


def test_role_relation_query_preserves_role_context_and_blocks_tiny_samples(
    tmp_path: Path,
) -> None:
    repository = SkillRelationRepository(_warehouse(tmp_path), _config())

    result = repository.related_skills(
        core_skill_id="python",
        role_id="data_engineer",
        recency_window="180d",
        as_of_date=date(2026, 8, 10),
    )

    assert result.role_id == "data_engineer"
    assert result.sample_size == 2
    assert result.evidence_status == "insufficient_role_sample"
    assert result.records == ()
    assert result.limitations == (
        "当前岗位样本不足，暂不足以形成稳定排序。",
    )


def test_role_relation_query_marks_four_to_nine_jobs_as_small_sample(
    tmp_path: Path,
) -> None:
    database = _warehouse(tmp_path)
    connection = duckdb.connect(str(database))
    try:
        for index in range(5, 9):
            connection.execute(
                "INSERT INTO jobs VALUES (?, 'data_engineer', '2026-08-04')",
                [f"j{index}"],
            )
            connection.execute(
                "INSERT INTO job_skills VALUES (?, 'python'), (?, 'sql')",
                [f"j{index}", f"j{index}"],
            )
    finally:
        connection.close()

    result = SkillRelationRepository(database, _config()).related_skills(
        core_skill_id="python",
        role_id="data_engineer",
        recency_window="180d",
        as_of_date=date(2026, 8, 10),
    )

    assert result.sample_size == 6
    assert result.evidence_status == "small_role_sample"
    assert result.limitations == ("小样本，仅供方向参考",)
    assert result.records[0].evidence_status == "small_sample_supported"
