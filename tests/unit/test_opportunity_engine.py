from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from skillworth_analytics import (
    OpportunityRequest,
    PersonalSkillOpportunityEngine,
    load_data_confidence_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIDENCE_CONFIG = ROOT / "data/reference/data_confidence.v1.yml"


def _warehouse(path: Path) -> Path:
    connection = duckdb.connect(str(path))
    try:
        connection.execute("""
            CREATE TABLE jobs (
                canonical_job_id VARCHAR,
                role_id VARCHAR,
                city_code VARCHAR,
                experience_band VARCHAR,
                published_at DATE
            );
            CREATE TABLE job_skills (
                canonical_job_id VARCHAR,
                skill_id VARCHAR
            );
            CREATE TABLE skills (
                skill_id VARCHAR,
                canonical_name VARCHAR,
                category VARCHAR
            );
            CREATE TABLE job_source_map (
                canonical_job_id VARCHAR,
                source_id VARCHAR
            );
        """)
        connection.executemany(
            "INSERT INTO skills VALUES (?, ?, ?)",
            [
                ("sql", "SQL", "database"),
                ("power_bi", "Power BI", "visualization"),
                ("python", "Python", "programming"),
                ("excel", "Excel", "office"),
                ("tableau", "Tableau", "visualization"),
                ("java", "Java", "programming"),
            ],
        )
        connection.executemany(
            "INSERT INTO jobs VALUES (?, ?, ?, ?, ?)",
            [
                ("j1", "data_analyst", "CN-110000", "junior", date(2026, 8, 1)),
                ("j2", "data_analyst", "CN-110000", "junior", date(2026, 8, 2)),
                ("j3", "data_analyst", "CN-110000", "senior", date(2026, 8, 3)),
                ("j4", "backend_engineer", "CN-110000", "junior", date(2026, 8, 4)),
                ("j5", "data_analyst", "CN-310000", "junior", date(2026, 8, 5)),
                ("j6", "data_analyst", "CN-110000", "junior", date(2026, 8, 6)),
            ],
        )
        connection.executemany(
            "INSERT INTO job_skills VALUES (?, ?)",
            [
                ("j1", "sql"),
                ("j1", "power_bi"),
                ("j2", "sql"),
                ("j2", "power_bi"),
                ("j2", "python"),
                ("j2", "excel"),
                ("j3", "sql"),
                ("j3", "tableau"),
                ("j4", "java"),
                ("j6", "sql"),
            ],
        )
        connection.executemany(
            "INSERT INTO job_source_map VALUES (?, ?)",
            [
                ("j1", "source_a"),
                ("j2", "source_b"),
                ("j3", "source_a"),
                ("j4", "source_b"),
                ("j5", "source_a"),
                ("j6", "source_b"),
            ],
        )
    finally:
        connection.close()
    return path


@pytest.fixture
def engine(tmp_path: Path) -> PersonalSkillOpportunityEngine:
    return PersonalSkillOpportunityEngine(
        _warehouse(tmp_path / "opportunity.duckdb"),
        load_data_confidence_config(CONFIDENCE_CONFIG),
    )


def _request(**updates: object) -> OpportunityRequest:
    values: dict[str, object] = {
        "current_skills": ("sql",),
        "target_role": "data_analyst",
        "city": "CN-110000",
        "experience": "junior",
        "match_threshold": 0.70,
    }
    values.update(updates)
    return OpportunityRequest.model_validate(values)


def _candidate(result: object, skill_id: str):
    return next(record for record in result.candidates if record.skill_id == skill_id)


def test_recomputes_fit_and_threshold_gain_with_set_based_sql(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(_request(), as_of_date=date(2026, 8, 8))
    power_bi = _candidate(result, "power_bi")

    assert result.target_job_count == 3
    assert result.sample_size == 3
    assert result.current_average_fit == pytest.approx((0.5 + 0.25 + 1.0) / 3)
    assert result.current_threshold_coverage == pytest.approx(1 / 3)
    assert power_bi.new_average_fit == pytest.approx((1.0 + 0.5 + 1.0) / 3)
    assert power_bi.average_fit_gain == pytest.approx(0.25)
    assert power_bi.new_threshold_coverage == pytest.approx(2 / 3)
    assert power_bi.threshold_coverage_gain == pytest.approx(1 / 3)
    assert power_bi.jobs_crossing_threshold == 1
    assert power_bi.sample_size == 3
    assert power_bi.confidence.confidence_score <= 100
    assert "cross_source_agreement_unavailable" in {
        warning.code for warning in power_bi.confidence.warnings
    }


def test_empty_current_skills_start_at_zero_fit(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(current_skills=()), as_of_date=date(2026, 8, 8)
    )

    assert result.current_average_fit == 0
    assert result.current_threshold_coverage == 0
    assert _candidate(result, "sql").average_fit_gain == pytest.approx(7 / 12)


def test_owned_skills_are_excluded_from_candidates(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(_request(), as_of_date=date(2026, 8, 8))

    assert "sql" not in {record.skill_id for record in result.candidates}


def test_filters_role_city_and_experience(engine: PersonalSkillOpportunityEngine) -> None:
    result = engine.analyze(_request(), as_of_date=date(2026, 8, 8))

    assert result.target_job_count == 3
    assert {record.skill_id for record in result.candidates} == {
        "power_bi",
        "python",
        "excel",
    }


def test_no_target_jobs_returns_explicit_empty_result(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(target_role="devops_engineer"), as_of_date=date(2026, 8, 8)
    )

    assert result.status == "no_target_jobs"
    assert result.target_job_count == 0
    assert result.sample_size == 0
    assert result.current_average_fit is None
    assert result.current_threshold_coverage is None
    assert result.candidates == ()
    assert result.confidence.confidence_level == "Low"


def test_target_jobs_without_skill_evidence_return_null_fit(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(city="CN-310000"), as_of_date=date(2026, 8, 8)
    )

    assert result.status == "no_skill_evidence"
    assert result.target_job_count == 1
    assert result.sample_size == 0
    assert result.jobs_without_extracted_skills == 1
    assert result.current_average_fit is None
    assert result.current_threshold_coverage is None
    assert result.candidates == ()


def test_jobs_without_skills_are_reported_and_excluded(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(city=None, experience=None), as_of_date=date(2026, 8, 8)
    )

    assert result.target_job_count == 5
    assert result.sample_size == 4
    assert result.jobs_without_extracted_skills == 1


def test_one_required_skill_can_cross_full_threshold(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(city=None, experience=None, current_skills=(), match_threshold=1),
        as_of_date=date(2026, 8, 8),
    )
    sql = _candidate(result, "sql")

    assert sql.jobs_crossing_threshold == 1
    assert sql.threshold_coverage_gain == pytest.approx(1 / 4)


def test_many_required_skills_use_fractional_gain(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(_request(), as_of_date=date(2026, 8, 8))

    assert _candidate(result, "python").average_fit_gain == pytest.approx(1 / 12)
    assert _candidate(result, "excel").average_fit_gain == pytest.approx(1 / 12)


def test_job_already_at_threshold_is_not_counted_again_as_crossing(
    engine: PersonalSkillOpportunityEngine,
) -> None:
    result = engine.analyze(
        _request(match_threshold=0.5), as_of_date=date(2026, 8, 8)
    )

    power_bi = _candidate(result, "power_bi")
    assert result.current_threshold_coverage == pytest.approx(2 / 3)
    assert power_bi.jobs_crossing_threshold == 1
    assert power_bi.threshold_coverage_gain == pytest.approx(1 / 3)
    assert power_bi.new_threshold_coverage == 1


@pytest.mark.parametrize("threshold", [-0.01, 1.01])
def test_match_threshold_must_be_a_probability(threshold: float) -> None:
    with pytest.raises(ValidationError, match="match_threshold"):
        _request(match_threshold=threshold)


def test_duplicate_or_blank_skill_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="current_skills"):
        _request(current_skills=("sql", "sql"))
    with pytest.raises(ValidationError, match="current_skills"):
        _request(current_skills=("",))
