from __future__ import annotations

from datetime import date

from skillworth_analytics.guardrails import SourceEligibilityConfig, evaluate_source_eligibility


def test_core_market_candidate_cannot_pass_source_gate() -> None:
    evidence = evaluate_source_eligibility(
        source_id="ncss_public_jobs",
        source_role="core_market_candidate",
        target_sample_size=500,
        all_sample_size=600,
        skilled_target_sample_size=450,
        latest_posted_at=date(2026, 8, 1),
        as_of_date=date(2026, 8, 10),
        config=SourceEligibilityConfig(
            minimum_target_sample_size=50,
            minimum_target_market_ratio=0.20,
            minimum_skill_extraction_coverage=0.50,
            maximum_market_age_days=180,
            minimum_agreement_sample_size=30,
            required_eligible_sources=2,
        ),
    )

    assert evidence.eligible is False
    assert evidence.reasons == ("SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE",)


def test_external_market_benchmark_cannot_pass_source_gate() -> None:
    evidence = evaluate_source_eligibility(
        source_id="qarera_skills_2026",
        source_role="external_market_benchmark",
        target_sample_size=360_336,
        all_sample_size=360_336,
        skilled_target_sample_size=360_336,
        latest_posted_at=date(2026, 6, 16),
        as_of_date=date(2026, 8, 10),
        config=SourceEligibilityConfig(
            minimum_target_sample_size=50,
            minimum_target_market_ratio=0.20,
            minimum_skill_extraction_coverage=0.50,
            maximum_market_age_days=180,
            minimum_agreement_sample_size=30,
            required_eligible_sources=2,
        ),
    )

    assert evidence.eligible is False
    assert "SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE" in evidence.reasons
