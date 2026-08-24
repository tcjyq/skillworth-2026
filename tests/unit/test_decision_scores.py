from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from skillworth_analytics import (
    DecisionScoreEngine,
    LearningHoursEstimate,
    MarketValueInput,
    PersonalROIInput,
    SensitivityAnalyzer,
    load_decision_score_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data/reference/decision_scores.v1.yml"


@pytest.fixture
def engine() -> DecisionScoreEngine:
    return DecisionScoreEngine(load_decision_score_config(CONFIG_PATH))


def _market(**updates: object) -> MarketValueInput:
    values: dict[str, object] = {
        "skill_id": "programming_python",
        "demand": 0.8,
        "adjusted_salary_association_pct": 10.0,
        "trend_slope": 0.01,
        "skill_synergy": 0.7,
        "confidence": 80.0,
    }
    values.update(updates)
    return MarketValueInput.model_validate(values)


def _hours() -> LearningHoursEstimate:
    return LearningHoursEstimate(
        skill_id="programming_python",
        learning_hours_min=80,
        learning_hours_expected=160,
        learning_hours_max=320,
        learning_cost_source="skillworth_curated_estimate_v1",
    )


def test_market_value_exposes_each_configured_component(
    engine: DecisionScoreEngine,
) -> None:
    result = engine.market_value(_market())

    assert 0 <= result.market_value_score <= 100
    assert set(result.components) == {
        "demand",
        "adjusted_salary_association",
        "trend",
        "skill_synergy",
        "confidence",
    }
    assert sum(component.effective_weight for component in result.components.values()) == pytest.approx(1)
    assert result.components["demand"].raw_value == 0.8
    assert result.config_version == "1.0.0"


def test_market_value_uses_transparent_configured_normalization(
    engine: DecisionScoreEngine,
) -> None:
    result = engine.market_value(
        _market(
            demand=1,
            adjusted_salary_association_pct=20,
            trend_slope=0.02,
            skill_synergy=1,
            confidence=100,
        )
    )

    assert result.market_value_score == 100
    assert all(component.normalized_score == 100 for component in result.components.values())


def test_missing_statistical_component_is_visible_and_reweighted(
    engine: DecisionScoreEngine,
) -> None:
    result = engine.market_value(
        _market(adjusted_salary_association_pct=None, trend_slope=None)
    )

    assert result.components["adjusted_salary_association"].available is False
    assert result.components["adjusted_salary_association"].normalized_score is None
    assert result.components["adjusted_salary_association"].effective_weight == 0
    assert "adjusted_salary_association_unavailable" in result.warnings
    assert "trend_unavailable" in result.warnings


def test_personal_roi_exposes_learning_estimate_and_all_components(
    engine: DecisionScoreEngine,
) -> None:
    result = engine.personal_roi(
        PersonalROIInput(
            skill_id="programming_python",
            marginal_skill_coverage_gain=0.12,
            market_value=72,
            learning_hours=_hours(),
            confidence=80,
        )
    )

    assert 0 <= result.personal_roi_score <= 100
    assert result.learning_hours.is_estimate is True
    assert result.learning_hours.effective_expected_hours == 160
    assert result.learning_hours.is_user_override is False
    assert set(result.components) == {
        "marginal_skill_coverage_gain",
        "market_value",
        "learning_cost_efficiency",
        "confidence",
    }


def test_user_learning_hours_override_changes_roi_without_changing_default_estimate(
    engine: DecisionScoreEngine,
) -> None:
    default = engine.personal_roi(
        PersonalROIInput(
            skill_id="programming_python",
            marginal_skill_coverage_gain=0.12,
            market_value=72,
            learning_hours=_hours(),
            confidence=80,
        )
    )
    overridden = engine.personal_roi(
        PersonalROIInput(
            skill_id="programming_python",
            marginal_skill_coverage_gain=0.12,
            market_value=72,
            learning_hours=_hours(),
            learning_hours_override=40,
            confidence=80,
        )
    )

    assert overridden.personal_roi_score > default.personal_roi_score
    assert overridden.learning_hours.effective_expected_hours == 40
    assert overridden.learning_hours.learning_hours_expected == 160
    assert overridden.learning_hours.is_user_override is True


def test_learning_hours_are_validated_as_ordered_estimates() -> None:
    with pytest.raises(ValidationError, match="learning hours"):
        LearningHoursEstimate(
            skill_id="bad",
            learning_hours_min=100,
            learning_hours_expected=50,
            learning_hours_max=200,
            learning_cost_source="fixture",
        )


def test_non_finite_learning_hours_are_rejected() -> None:
    with pytest.raises(ValidationError, match="learning hours"):
        LearningHoursEstimate(
            skill_id="bad",
            learning_hours_min=10,
            learning_hours_expected=float("inf"),
            learning_hours_max=float("inf"),
            learning_cost_source="fixture",
        )


def test_invalid_market_input_is_rejected() -> None:
    with pytest.raises(ValidationError, match="demand"):
        _market(demand=1.01)


def test_market_value_sensitivity_reports_rank_range_and_warning(
    engine: DecisionScoreEngine,
) -> None:
    result = SensitivityAnalyzer(engine).market_value(
        (
            _market(
                skill_id="skill_a",
                demand=1,
                adjusted_salary_association_pct=-20,
                trend_slope=-0.02,
                skill_synergy=0.5,
            ),
            _market(
                skill_id="skill_b",
                demand=0,
                adjusted_salary_association_pct=20,
                trend_slope=-0.02,
                skill_synergy=0.5,
            ),
            _market(
                skill_id="skill_c",
                demand=0.5,
                adjusted_salary_association_pct=0,
                trend_slope=-0.02,
                skill_synergy=0.5,
            ),
        )
    )
    skill_a = next(record for record in result.records if record.skill_id == "skill_a")

    assert skill_a.baseline_rank == 1
    assert skill_a.rank_min == 1
    assert skill_a.rank_max == 3
    assert skill_a.rank_range == 2
    assert skill_a.rank_stability == 0
    assert skill_a.warning == "Sensitive Ranking Warning"
    assert 0 <= result.overall_rank_stability <= 1
    assert set(skill_a.scenario_ranks) == {
        "baseline",
        "demand_heavy",
        "salary_heavy",
        "trend_heavy",
    }


def test_personal_roi_sensitivity_uses_configured_scenarios(
    engine: DecisionScoreEngine,
) -> None:
    inputs = (
        PersonalROIInput(
            skill_id="fast_low_market",
            marginal_skill_coverage_gain=0.08,
            market_value=30,
            learning_hours=LearningHoursEstimate(
                skill_id="fast_low_market",
                learning_hours_min=10,
                learning_hours_expected=20,
                learning_hours_max=40,
                learning_cost_source="fixture",
            ),
            confidence=80,
        ),
        PersonalROIInput(
            skill_id="slow_high_market",
            marginal_skill_coverage_gain=0.08,
            market_value=95,
            learning_hours=LearningHoursEstimate(
                skill_id="slow_high_market",
                learning_hours_min=100,
                learning_hours_expected=300,
                learning_hours_max=500,
                learning_cost_source="fixture",
            ),
            confidence=80,
        ),
    )
    result = SensitivityAnalyzer(engine).personal_roi(inputs)

    assert result.score_type == "personal_roi"
    assert result.scenario_names == (
        "baseline",
        "opportunity_heavy",
        "market_heavy",
        "learning_cost_heavy",
    )


def test_sensitivity_rejects_duplicate_skill_ids(engine: DecisionScoreEngine) -> None:
    with pytest.raises(ValueError, match="unique"):
        SensitivityAnalyzer(engine).market_value((_market(), _market()))
