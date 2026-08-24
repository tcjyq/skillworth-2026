from __future__ import annotations

import pytest

from app.multi_source_validation import (
    guarded_jensen_shannon_divergence,
    agreement_status,
    jensen_shannon_divergence,
    rank_changes,
)


def test_jsd_carries_sample_sizes_and_eligibility_warning() -> None:
    result = guarded_jensen_shannon_divergence(
        {"a": 8, "b": 2}, {"a": 1, "b": 1},
        left_source_id="core", right_source_id="tiny",
        left_eligible=True, right_eligible=False,
    )
    assert result.sample_sizes == {"core": 10, "tiny": 2}
    assert result.eligibility == {"core": True, "tiny": False}
    assert result.warning == "INSUFFICIENT_COMPARABLE_SOURCES"


def test_jensen_shannon_divergence_is_symmetric_and_bounded() -> None:
    left = {"data": 0.75, "backend": 0.25}
    right = {"data": 0.25, "backend": 0.75}

    assert jensen_shannon_divergence(left, right) == pytest.approx(
        jensen_shannon_divergence(right, left)
    )
    assert 0 < jensen_shannon_divergence(left, right) < 1
    assert jensen_shannon_divergence(left, left) == pytest.approx(0)


def test_agreement_status_uses_transparent_thresholds() -> None:
    assert agreement_status(0.0025) == "High Agreement"
    assert agreement_status(0.01) == "Medium Agreement"
    assert agreement_status(0.08) == "Low Agreement"


def test_rank_changes_reports_largest_absolute_movements_first() -> None:
    changes = rank_changes(
        pooled={"python": 0.5, "sql": 0.4, "excel": 0.3},
        balanced={"excel": 0.6, "python": 0.5, "sql": 0.1},
    )

    assert changes[0]["skill_id"] == "excel"
    assert changes[0]["absolute_rank_change"] == 2
