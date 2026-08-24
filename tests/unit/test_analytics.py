from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pytest

from skillworth_analytics import AnalyticsFilters, AnalyticsRepository


def _warehouse(path: Path) -> Path:
    connection = duckdb.connect(str(path))
    try:
        connection.execute("""
            CREATE TABLE jobs (
                canonical_job_id VARCHAR,
                role_id VARCHAR,
                city_code VARCHAR,
                experience_band VARCHAR,
                education_band VARCHAR,
                published_at DATE,
                salary_mid_monthly DOUBLE
                ,market_scope VARCHAR
            );
            INSERT INTO jobs VALUES
                ('job-1', 'data_analyst', 'CN-110000', 'mid', 'bachelor', DATE '2026-08-01', 10000, 'target'),
                ('job-2', 'backend_engineer', 'CN-110000', 'senior', 'master', DATE '2026-08-15', 30000, 'target'),
                ('job-3', 'data_analyst', 'CN-310000', 'entry', 'bachelor', DATE '2026-09-01', NULL, 'target');

            CREATE TABLE job_source_map (
                canonical_job_id VARCHAR,
                silver_job_id VARCHAR,
                source_id VARCHAR
            );
            INSERT INTO job_source_map VALUES
                ('job-1', 'silver-1', 'source_a'),
                ('job-1', 'silver-2', 'source_b'),
                ('job-2', 'silver-3', 'source_a'),
                ('job-3', 'silver-4', 'source_b');

            CREATE TABLE skills (
                skill_id VARCHAR,
                canonical_name VARCHAR,
                category VARCHAR
            );
            INSERT INTO skills VALUES
                ('programming_python', 'Python', 'programming'),
                ('database_sql', 'SQL', 'database'),
                ('programming_java', 'Java', 'programming');

            CREATE TABLE job_skills (
                canonical_job_id VARCHAR,
                silver_job_id VARCHAR,
                skill_id VARCHAR
            );
            INSERT INTO job_skills VALUES
                ('job-1', 'silver-1', 'programming_python'),
                ('job-1', 'silver-2', 'database_sql'),
                ('job-2', 'silver-3', 'programming_python'),
                ('job-2', 'silver-3', 'database_sql'),
                ('job-3', 'silver-4', 'database_sql');
        """)
    finally:
        connection.close()
    return path


@pytest.fixture
def analytics(tmp_path: Path) -> AnalyticsRepository:
    return AnalyticsRepository(_warehouse(tmp_path / "analytics.duckdb"))


def test_skill_demand_uses_canonical_jobs_and_all_supported_filters(analytics: AnalyticsRepository) -> None:
    result = analytics.skill_demand(
        AnalyticsFilters(
            role_id="data_analyst",
            city_code="CN-110000",
            experience_band="mid",
            education_band="bachelor",
            source_ids=("source_b",),
            published_from=date(2026, 8, 1),
            published_to=date(2026, 8, 31),
        )
    )

    python = next(record for record in result.records if record.skill_id == "programming_python")
    assert result.metadata.sample_size == 1
    assert python.job_count == 0
    assert python.job_coverage == 0.0
    assert python.source_count == 0


def test_platform_balanced_demand_does_not_pool_source_postings(analytics: AnalyticsRepository) -> None:
    result = analytics.platform_balanced_demand()

    python = next(record for record in result.records if record.skill_id == "programming_python")
    assert python.pooled_coverage == pytest.approx(2 / 3)
    assert python.platform_balanced_coverage is None
    assert result.eligible_source_count == 0
    assert {item.source_id for item in result.ineligible_sources} == {"source_a", "source_b"}
    assert {(item.source_id, item.job_coverage, item.sample_size) for item in python.platform_breakdown} == {
        ("source_a", 1.0, 2),
        ("source_b", 0.0, 2),
    }


def test_platform_balanced_demand_only_averages_eligible_sources(tmp_path: Path) -> None:
    config = tmp_path / "guardrails.yml"
    config.write_text(
        """version: 'test'\nsource_roles:\n  source_a: core_market\n  source_b: supplementary_market\neligibility:\n  minimum_target_sample_size: 2\n  minimum_target_market_ratio: 0.5\n  minimum_skill_extraction_coverage: 0.25\n  maximum_market_age_days: 365\n  minimum_agreement_sample_size: 2\n  required_eligible_sources: 2\n""",
        encoding="utf-8",
    )
    repository = AnalyticsRepository(_warehouse(tmp_path / "eligible.duckdb"), guardrail_config_path=config)

    result = repository.platform_balanced_demand()
    python = next(record for record in result.records if record.skill_id == "programming_python")

    assert result.eligible_source_count == 2
    assert result.ineligible_sources == ()
    assert python.platform_balanced_coverage == pytest.approx(0.5)
    assert result.methodology_version == "platform-balanced-demand-2.0.0"


def test_every_metric_accepts_the_same_source_aware_slice(analytics: AnalyticsRepository) -> None:
    filters = AnalyticsFilters(
        role_id="data_analyst",
        city_code="CN-110000",
        experience_band="mid",
        education_band="bachelor",
        source_ids=("source_b",),
        published_from=date(2026, 8, 1),
        published_to=date(2026, 8, 31),
    )

    assert analytics.platform_balanced_demand(filters).metadata.sample_size == 1
    assert analytics.salary_by_skill(filters).metadata.sample_size == 1
    assert analytics.skill_by_role(filters).metadata.sample_size == 1
    assert analytics.skill_by_city(filters).metadata.sample_size == 1
    assert analytics.skill_by_experience(filters).metadata.sample_size == 1
    assert analytics.source_bias_analysis(filters).metadata.source_count == 1


def test_salary_skill_dimension_and_source_bias_statistics(analytics: AnalyticsRepository) -> None:
    salary = analytics.salary_by_skill()
    python_salary = next(record for record in salary.records if record.skill_id == "programming_python")
    assert (python_salary.median, python_salary.p25, python_salary.p75) == (20000.0, 15000.0, 25000.0)
    assert python_salary.sample_size == 2
    assert python_salary.salary_coverage == 1.0
    assert python_salary.status == "available"

    by_role = analytics.skill_by_role()
    python_analyst = next(
        record for record in by_role.records
        if record.skill_id == "programming_python" and record.dimension_value == "data_analyst"
    )
    assert (python_analyst.job_count, python_analyst.job_coverage, python_analyst.sample_size) == (1, 0.5, 2)

    by_city = analytics.skill_by_city()
    assert any(record.dimension_value == "CN-310000" for record in by_city.records)
    by_experience = analytics.skill_by_experience()
    assert any(record.dimension_value == "senior" for record in by_experience.records)

    bias = analytics.source_bias_analysis()
    source_a_roles = [record for record in bias.records if record.dimension == "role" and record.source_id == "source_a"]
    assert {(record.value, record.job_count, record.job_coverage) for record in source_a_roles} == {
        ("backend_engineer", 1, 0.5),
        ("data_analyst", 1, 0.5),
    }


def test_salary_by_skill_marks_zero_salary_sample_unavailable(analytics: AnalyticsRepository) -> None:
    result = analytics.salary_by_skill(AnalyticsFilters(published_from=date(2026, 9, 1)))
    sql = next(record for record in result.records if record.skill_id == "database_sql")

    assert sql.sample_size == 0
    assert sql.salary_coverage is None
    assert sql.status == "unavailable"


def test_invalid_date_filter_is_rejected() -> None:
    with pytest.raises(ValueError, match="published_from"):
        AnalyticsFilters(published_from=date(2026, 9, 1), published_to=date(2026, 8, 1))


def test_target_market_is_default_and_all_scope_is_explicit(tmp_path: Path) -> None:
    path = _warehouse(tmp_path / "scope.duckdb")
    connection = duckdb.connect(str(path))
    try:
        connection.execute("UPDATE jobs SET market_scope = 'non_target' WHERE canonical_job_id = 'job-3'")
    finally:
        connection.close()
    analytics = AnalyticsRepository(path)

    assert analytics.skill_demand().metadata.sample_size == 2
    assert analytics.skill_demand(AnalyticsFilters(market_scope="all")).metadata.sample_size == 3
