from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl

from skillworth_analytics.china_skillworth import (
    ChinaSkillWorthConfig,
    ChinaSkillWorthEngine,
    MarketSignalInput,
    RankingRobustnessInput,
    build_china_skillworth_summary,
    build_china_skillworth_visual_ready,
    calculate_ranking_robustness,
    is_high_skillworth_candidate,
)
from skillworth_analytics.confidence_config import load_data_confidence_config


ROOT = Path(__file__).resolve().parents[2]


def _config() -> ChinaSkillWorthConfig:
    return ChinaSkillWorthConfig.model_validate(
        {
            "version": "test-v1",
            "market_signal_weights": {
                "demand_strength": 0.30,
                "company_breadth": 0.20,
                "role_breadth": 0.20,
                "skill_synergy": 0.15,
                "confidence": 0.15,
            },
            "role_breadth": {
                "minimum_role_support": 1,
                "target_recognized_skill_jobs": 2,
                "excluded_roles": ["other"],
            },
            "synergy": {
                "centrality_weight": 0.40,
                "edge_support_weight": 0.20,
                "jaccard_weight": 0.20,
                "positive_pmi_weight": 0.20,
                "positive_pmi_reference": 2.0,
            },
            "learning_efficiency": {"half_value_hours": 100},
            "sensitivity": {
                "market_signal_weight_scenarios": {
                    "demand_heavy": {
                        "demand_strength": 0.55,
                        "company_breadth": 0.15,
                        "role_breadth": 0.10,
                        "skill_synergy": 0.10,
                        "confidence": 0.10,
                    }
                },
                "learning_half_value_scenarios": [80, 160],
                "sensitive_rank_range": 2,
            },
        }
    )


def test_market_signal_and_skillworth_are_transparent_and_salary_independent() -> None:
    result = ChinaSkillWorthEngine(_config()).score(
        MarketSignalInput(
            skill_id="programming_python",
            demand_strength=0.50,
            company_breadth=0.40,
            role_breadth=0.30,
            skill_synergy=0.20,
            confidence=50,
            learning_hours_expected=100,
        )
    )

    assert result.market_signal == 39.5
    assert result.learning_efficiency == 0.5
    assert result.skillworth_score == 19.75
    assert result.components["demand_strength"].raw_value == 0.5
    assert result.components["confidence"].normalized_score == 50
    assert result.salary_signal is None
    assert result.salary_signal_status == "unavailable"
    assert result.trend_signal is None
    assert result.trend_signal_status == "unavailable"


def test_ranking_robustness_is_distinct_from_confidence_and_penalizes_uncertainty() -> None:
    config = _config()
    stable = calculate_ranking_robustness(
        RankingRobustnessInput(
            rank_min=3,
            rank_max=5,
            job_count=60,
            company_count=30,
            role_count=6,
            confidence=45,
            learning_hours_min=80,
            learning_hours_expected=120,
            learning_hours_max=160,
        ),
        config.robustness,
    )
    unstable = calculate_ranking_robustness(
        RankingRobustnessInput(
            rank_min=2,
            rank_max=30,
            job_count=5,
            company_count=3,
            role_count=1,
            confidence=45,
            learning_hours_min=20,
            learning_hours_expected=100,
            learning_hours_max=400,
        ),
        config.robustness,
    )

    assert stable.score > unstable.score
    assert stable.level == "robust"
    assert unstable.level == "sensitive"
    assert stable.score != stable.components["confidence"]


def test_high_candidate_requires_main_semantics_support_and_acceptable_robustness() -> None:
    gate = _config().candidate_gate

    assert is_high_skillworth_candidate(
        eligibility="main",
        job_count=10,
        company_count=8,
        confidence=30,
        robustness_level="moderate",
        config=gate,
    )
    assert not is_high_skillworth_candidate(
        eligibility="excluded",
        job_count=100,
        company_count=80,
        confidence=50,
        robustness_level="robust",
        config=gate,
    )


def test_build_china_skillworth_summary_uses_job_company_role_and_network_evidence(
    tmp_path: Path,
) -> None:
    database = tmp_path / "skillworth.duckdb"
    connection = duckdb.connect(str(database))
    try:
        connection.execute(
            "CREATE TABLE jobs(canonical_job_id VARCHAR, company_id VARCHAR, role_id VARCHAR, "
            "published_at DATE)"
        )
        connection.execute(
            "INSERT INTO jobs VALUES "
            "('j1','c1','data_engineer','2026-08-01'),"
            "('j2','c2','backend_engineer','2026-08-02'),"
            "('j3','c1','other','2026-08-03')"
        )
        connection.execute(
            "CREATE TABLE skills(skill_id VARCHAR, canonical_name VARCHAR, category VARCHAR, "
            "learning_hours_min DOUBLE, learning_hours_expected DOUBLE, learning_hours_max DOUBLE, "
            "skill_type VARCHAR, skillworth_eligibility VARCHAR, skillworth_reason VARCHAR)"
        )
        connection.execute(
            "INSERT INTO skills VALUES "
            "('programming_python','Python','programming',80,100,140,'programming_language','main','specific'),"
            "('database_sql','SQL','database',30,50,80,'database','main','specific'),"
            "('devops_docker','Docker','devops',50,80,120,'devops_tool','main','specific')"
        )
        connection.execute(
            "CREATE TABLE job_skills(canonical_job_id VARCHAR, skill_id VARCHAR)"
        )
        connection.execute(
            "INSERT INTO job_skills VALUES "
            "('j1','programming_python'),('j2','programming_python'),"
            "('j1','database_sql'),('j3','database_sql'),('j2','devops_docker')"
        )
        connection.execute(
            "CREATE TABLE job_source_map(canonical_job_id VARCHAR, source_id VARCHAR, "
            "upstream_source VARCHAR, observed_at VARCHAR, api_accessed_at VARCHAR)"
        )
        connection.execute(
            "INSERT INTO job_source_map VALUES "
            "('j1','freehire_china_tech','greenhouse','2026-08-10T10:00:00Z','2026-08-10T09:00:00Z'),"
            "('j2','freehire_china_tech','workday','2026-08-10T10:00:00Z','2026-08-10T09:01:00Z'),"
            "('j3','freehire_china_tech','greenhouse','2026-08-10T10:00:00Z','2026-08-10T09:02:00Z')"
        )
    finally:
        connection.close()

    nodes = tmp_path / "nodes.parquet"
    edges = tmp_path / "edges.parquet"
    pl.DataFrame(
        {
            "skill_id": ["programming_python", "database_sql", "devops_docker"],
            "weighted_degree": [0.8, 0.5, 0.3],
        }
    ).write_parquet(nodes)
    pl.DataFrame(
        {
            "skill_a_id": ["database_sql", "devops_docker"],
            "skill_b_id": ["programming_python", "programming_python"],
            "cooccurrence_count": [1, 1],
            "jaccard": [1 / 3, 0.5],
            "pmi": [0.1, 0.4],
        }
    ).write_parquet(edges)

    report = build_china_skillworth_summary(
        database_path=database,
        graph_nodes_path=nodes,
        graph_edges_path=edges,
        snapshot_id="freehire_china_tech_2026_08",
        snapshot_completed_at=datetime(2026, 8, 10, 10, 0, tzinfo=UTC),
        config=_config(),
        confidence_config=load_data_confidence_config(
            ROOT / "data/reference/data_confidence.v1.yml"
        ),
    )

    assert report.snapshot_id == "freehire_china_tech_2026_08"
    assert report.job_count == 3
    assert report.company_count == 2
    assert report.source_count == 2
    assert report.skill_count == 3
    python = next(row for row in report.records if row.skill_id == "programming_python")
    assert python.job_count == 2
    assert python.job_coverage == 2 / 3
    assert python.company_count == 2
    assert python.company_coverage == 1
    assert python.role_count == 2
    assert python.role_breadth_score == 1
    assert (python.learning_hours_min, python.learning_hours_expected, python.learning_hours_max) == (80, 100, 140)
    assert 0 <= python.synergy_score <= 1
    assert python.salary_signal is None
    assert python.trend_signal is None

    connection = duckdb.connect(str(database), read_only=True)
    try:
        stored = connection.execute(
            "SELECT salary_signal, salary_signal_status, trend_signal, trend_signal_status, snapshot_id "
            "FROM china_skillworth_summary WHERE skill = 'Python'"
        ).fetchone()
    finally:
        connection.close()
    assert stored == (
        None,
        "unavailable",
        None,
        "unavailable",
        "freehire_china_tech_2026_08",
    )

    visual = build_china_skillworth_visual_ready(
        database_path=database,
        snapshot_id="freehire_china_tech_2026_08",
        snapshot_completed_at=datetime(2026, 8, 10, 10, 0, tzinfo=UTC),
        config=_config(),
        confidence_config=load_data_confidence_config(
            ROOT / "data/reference/data_confidence.v1.yml"
        ),
    )
    assert {window.recency_window for window in visual.windows} == {
        "90d",
        "180d",
        "365d",
        "all_active",
    }
    assert visual.windows[-1].job_count == 3
    connection = duckdb.connect(str(database), read_only=True)
    try:
        columns = {
            item[1]
            for item in connection.execute(
                "PRAGMA table_info('china_skillworth_visual_ready')"
            ).fetchall()
        }
    finally:
        connection.close()
    assert {
        "skill_type",
        "skillworth_eligibility",
        "ranking_robustness",
        "robustness_level",
        "high_skillworth_candidate",
        "recency_window",
        "market_theme",
    } <= columns
