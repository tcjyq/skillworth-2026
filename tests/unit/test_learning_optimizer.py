from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest
from pydantic import ValidationError

from skillworth_analytics import (
    LearningOptimizer,
    LearningOptimizerRequest,
    load_data_confidence_config,
    load_decision_score_config,
)


ROOT = Path(__file__).resolve().parents[2]


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
            CREATE TABLE job_source_map (
                canonical_job_id VARCHAR,
                source_id VARCHAR
            );
            CREATE TABLE skills (
                skill_id VARCHAR,
                canonical_name VARCHAR,
                category VARCHAR,
                learning_hours_min DOUBLE,
                learning_hours_expected DOUBLE,
                learning_hours_max DOUBLE,
                learning_cost_source VARCHAR
            );
        """)
        connection.executemany(
            "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("skill_a", "Skill A", "other", 5, 10, 20, "fixture"),
                ("skill_b", "Skill B", "other", 5, 10, 20, "fixture"),
                ("skill_c", "Skill C", "other", 5, 10, 20, "fixture"),
            ],
        )
        jobs = [
            ("j1", "target_role", "CN-110000", "junior", date(2026, 8, 1)),
            ("j2", "target_role", "CN-110000", "junior", date(2026, 8, 2)),
            ("j3", "target_role", "CN-110000", "junior", date(2026, 8, 3)),
            ("j4", "target_role", "CN-110000", "junior", date(2026, 8, 4)),
        ]
        connection.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?)", jobs)
        connection.executemany(
            "INSERT INTO job_skills VALUES (?, ?)",
            [
                ("j1", "skill_a"),
                ("j1", "skill_b"),
                ("j2", "skill_a"),
                ("j2", "skill_b"),
                ("j3", "skill_a"),
                ("j3", "skill_b"),
                ("j4", "skill_c"),
            ],
        )
        connection.executemany(
            "INSERT INTO job_source_map VALUES (?, ?)",
            [(job[0], "source_a" if index < 2 else "source_b") for index, job in enumerate(jobs)],
        )
    finally:
        connection.close()
    return path


@pytest.fixture
def optimizer(tmp_path: Path) -> LearningOptimizer:
    return LearningOptimizer(
        _warehouse(tmp_path / "optimizer.duckdb"),
        decision_config=load_decision_score_config(
            ROOT / "data/reference/decision_scores.v1.yml"
        ),
        confidence_config=load_data_confidence_config(
            ROOT / "data/reference/data_confidence.v1.yml"
        ),
    )


def _request(**updates: object) -> LearningOptimizerRequest:
    values: dict[str, object] = {
        "current_skills": (),
        "target_role": "target_role",
        "hour_budget": 20,
        "match_threshold": 0.5,
    }
    values.update(updates)
    return LearningOptimizerRequest.model_validate(values)


def test_iterative_greedy_recomputes_overlap_instead_of_using_static_rank(
    optimizer: LearningOptimizer,
) -> None:
    result = optimizer.optimize(_request(), as_of_date=date(2026, 8, 8))

    assert [step.skill_id for step in result.steps] == ["skill_a", "skill_c"]
    assert result.steps[0].marginal_fit_gain == pytest.approx(0.375)
    assert result.steps[0].threshold_coverage == pytest.approx(0.75)
    assert result.steps[1].marginal_fit_gain == pytest.approx(0.25)
    assert result.steps[1].cumulative_fit == pytest.approx(0.625)
    assert result.steps[1].threshold_coverage == 1
    assert result.steps[1].cumulative_hours == 20
    assert result.strategy == "iterative_greedy_marginal_gain"
    assert result.beam_search_used is False


def test_optimizer_respects_budget_and_reports_learning_estimate(
    optimizer: LearningOptimizer,
) -> None:
    result = optimizer.optimize(_request(hour_budget=10), as_of_date=date(2026, 8, 8))

    assert len(result.steps) == 1
    assert result.steps[0].estimated_hours == 10
    assert result.steps[0].learning_hours.learning_hours_min == 5
    assert result.steps[0].learning_hours.learning_hours_max == 20
    assert result.steps[0].learning_hours.is_estimate is True
    assert result.cumulative_hours <= result.hour_budget


def test_optimizer_applies_user_learning_hours_override(
    optimizer: LearningOptimizer,
) -> None:
    result = optimizer.optimize(
        _request(hour_budget=15, learning_hours_overrides={"skill_c": 5}),
        as_of_date=date(2026, 8, 8),
    )

    assert [step.skill_id for step in result.steps] == ["skill_a", "skill_c"]
    assert result.steps[1].estimated_hours == 5
    assert result.steps[1].learning_hours.is_user_override is True


def test_owned_skill_is_never_selected(optimizer: LearningOptimizer) -> None:
    result = optimizer.optimize(
        _request(current_skills=("skill_a",), hour_budget=20),
        as_of_date=date(2026, 8, 8),
    )

    assert "skill_a" not in {step.skill_id for step in result.steps}


def test_budget_smaller_than_every_candidate_returns_no_steps(
    optimizer: LearningOptimizer,
) -> None:
    result = optimizer.optimize(_request(hour_budget=4), as_of_date=date(2026, 8, 8))

    assert result.steps == ()
    assert result.cumulative_hours == 0
    assert result.remaining_hours == 4


def test_optimizer_output_contains_reason(optimizer: LearningOptimizer) -> None:
    result = optimizer.optimize(_request(), as_of_date=date(2026, 8, 8))

    assert "重新计算" in result.steps[0].reason
    assert "单位学习小时" in result.steps[0].reason


@pytest.mark.parametrize("budget", [0, -1])
def test_hour_budget_must_be_positive(budget: float) -> None:
    with pytest.raises(ValidationError, match="hour_budget"):
        _request(hour_budget=budget)


def test_learning_hour_overrides_must_be_positive() -> None:
    with pytest.raises(ValidationError, match="learning_hours_overrides"):
        _request(learning_hours_overrides={"skill_a": 0})
