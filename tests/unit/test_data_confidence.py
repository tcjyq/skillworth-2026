from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from skillworth_analytics import (
    ConfidenceEvidence,
    DataConfidenceEngine,
    load_data_confidence_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data/reference/data_confidence.v1.yml"


@pytest.fixture
def engine() -> DataConfidenceEngine:
    return DataConfidenceEngine(load_data_confidence_config(CONFIG_PATH))


def _evidence(**updates: object) -> ConfidenceEvidence:
    values: dict[str, object] = {
        "sample_size": 1000,
        "source_sample_sizes": {
            "source_a": 250,
            "source_b": 250,
            "source_c": 250,
            "source_d": 250,
        },
        "latest_observation_date": date(2026, 8, 1),
        "latest_posted_date": date(2026, 8, 1),
        "median_posting_age_days": 7,
        "p75_posting_age_days": 10,
        "posting_date_coverage": 1.0,
        "as_of_date": date(2026, 8, 8),
        "source_eligibility": {"source_a": True, "source_b": True, "source_c": True, "source_d": True},
        "gold_benchmark_available": True,
        "is_salary_metric": True,
        "salary_eligible_count": 900,
        "platform_metric_values": {
            "source_a": 0.40,
            "source_b": 0.41,
            "source_c": 0.42,
            "source_d": 0.39,
        },
    }
    values.update(updates)
    return ConfidenceEvidence.model_validate(values)


def _warning_codes(result: object) -> set[str]:
    return {warning.code for warning in result.warnings}


def test_high_confidence_result_exposes_every_component(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(_evidence())

    assert result.confidence_level == "High"
    assert 0 <= result.confidence_score <= 100
    assert set(result.confidence_components) == {
        "sample_strength",
        "effective_source_diversity",
        "market_freshness",
        "metric_specific_coverage",
        "cross_source_agreement",
    }
    assert result.warnings == ()
    assert result.methodology_version == "data-confidence-2.0.0"
    assert result.config_version == "2.0.0"
    assert result.raw_source_count == 4
    assert result.effective_source_count == pytest.approx(4.0)
    assert result.confidence_cap == 100
    assert sum(
        component.effective_weight
        for component in result.confidence_components.values()
    ) == pytest.approx(1.0)


def test_low_quality_evidence_emits_required_warnings(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(
        _evidence(
            sample_size=10,
            source_sample_sizes={"source_a": 10},
            source_eligibility={"source_a": True},
            latest_observation_date=date(2025, 1, 1),
            latest_posted_date=date(2025, 1, 1),
            p75_posting_age_days=584,
            salary_eligible_count=2,
            platform_metric_values={"source_a": 0.05, "source_b": 0.95},
        )
    )

    assert result.confidence_level == "Low"
    assert {
        "sample_size_below_threshold",
        "effective_source_count_below_threshold",
        "market_data_older_than_threshold",
        "salary_coverage_below_threshold",
            "cross_source_agreement_unavailable",
    } <= _warning_codes(result)


def test_warning_thresholds_are_strict_boundaries(engine: DataConfidenceEngine) -> None:
    config = engine.config
    at_boundary = engine.evaluate(
        _evidence(
            sample_size=config.sample_strength.warning_below,
            source_sample_sizes={"source_a": 25, "source_b": 25},
            source_eligibility={"source_a": True, "source_b": True},
            latest_posted_date=date(2026, 8, 8)
            - timedelta(days=config.market_freshness.warning_after_days),
            p75_posting_age_days=config.market_freshness.warning_after_days,
            salary_eligible_count=30,
            platform_metric_values={"source_a": 0.35, "source_b": 0.65},
        )
    )

    assert "sample_size_below_threshold" not in _warning_codes(at_boundary)
    assert "effective_source_count_below_threshold" not in _warning_codes(at_boundary)
    assert "market_data_older_than_threshold" not in _warning_codes(at_boundary)
    assert "salary_coverage_below_threshold" not in _warning_codes(at_boundary)
    assert "platform_disagreement_above_threshold" not in _warning_codes(at_boundary)


def test_non_salary_metric_marks_salary_coverage_not_applicable(
    engine: DataConfidenceEngine,
) -> None:
    result = engine.evaluate(
        _evidence(is_salary_metric=False, salary_eligible_count=None)
    )
    salary = result.confidence_components["metric_specific_coverage"]

    assert salary.applicable is False
    assert salary.component_score is None
    assert salary.effective_weight == 0
    assert "salary_coverage_below_threshold" not in _warning_codes(result)


def test_balanced_sources_score_above_concentrated_sources(
    engine: DataConfidenceEngine,
) -> None:
    balanced = engine.evaluate(_evidence())
    concentrated = engine.evaluate(
        _evidence(
            source_sample_sizes={
                "source_a": 970,
                "source_b": 10,
                "source_c": 10,
                "source_d": 10,
            }
        )
    )

    assert (
        balanced.confidence_components["effective_source_diversity"].component_score
        > concentrated.confidence_components["effective_source_diversity"].component_score
    )


def test_missing_agreement_is_unknown_not_perfect(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(_evidence(platform_metric_values={"source_a": 0.4}))
    component = result.confidence_components["cross_source_agreement"]

    assert component.applicable is True
    assert component.available is False
    assert component.component_score == 0
    assert component.effective_weight > 0
    assert "cross_source_agreement_unavailable" in _warning_codes(result)


def test_level_boundaries_are_inclusive(engine: DataConfidenceEngine) -> None:
    assert engine.level_for_score(100) == "High"
    assert engine.level_for_score(75) == "High"
    assert engine.level_for_score(74.999) == "Medium"
    assert engine.level_for_score(50) == "Medium"
    assert engine.level_for_score(49.999) == "Low"
    assert engine.level_for_score(0) == "Low"


def test_future_observation_is_clamped_and_warned(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(
        _evidence(latest_posted_date=date(2026, 8, 9), p75_posting_age_days=None)
    )

    freshness = result.confidence_components["market_freshness"]
    assert freshness.component_score == 100
    assert freshness.raw_value == 0
    assert "market_data_older_than_threshold" not in _warning_codes(result)


def test_missing_posting_date_scores_zero_and_warns(
    engine: DataConfidenceEngine,
) -> None:
    result = engine.evaluate(
        _evidence(latest_posted_date=None, p75_posting_age_days=None, posting_date_coverage=0)
    )

    freshness = result.confidence_components["market_freshness"]
    assert freshness.component_score == 0
    assert freshness.raw_value is None
    assert "market_freshness_missing" in _warning_codes(result)


def test_ineligible_tiny_source_has_small_effective_contribution(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(
        _evidence(
            source_sample_sizes={"core": 100, "tiny": 2},
            source_eligibility={"core": True, "tiny": False},
            platform_metric_values={"core": 0.4, "tiny": 0.0},
        )
    )
    assert result.raw_source_count == 2
    assert result.eligible_source_count == 1
    assert result.effective_source_count == pytest.approx(1.0)
    assert result.confidence_components["cross_source_agreement"].available is False


def test_missing_gold_benchmark_caps_confidence(engine: DataConfidenceEngine) -> None:
    result = engine.evaluate(_evidence(gold_benchmark_available=False))
    assert result.confidence_cap == 60
    assert result.confidence_score <= 60
    assert "confidence_capped_no_gold_benchmark" in _warning_codes(result)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"salary_eligible_count": 1001}, "salary_eligible_count"),
        (
            {"is_salary_metric": False, "salary_eligible_count": 1},
            "salary_eligible_count",
        ),
        ({"platform_metric_values": {"source_a": 1.01}}, "platform_metric_values"),
        ({"platform_metric_values": {"source_a": float("nan")}}, "platform_metric_values"),
    ],
)
def test_invalid_evidence_is_rejected(updates: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _evidence(**updates)
