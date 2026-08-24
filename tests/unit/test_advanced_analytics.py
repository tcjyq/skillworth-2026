from __future__ import annotations

from datetime import date
from math import log
from pathlib import Path

import duckdb
import polars as pl
import pytest

from skillworth_analytics import (
    AdvancedAnalyticsRepository,
    AnalyticsFilters,
    load_advanced_analytics_config,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "data/reference/advanced_analytics.v1.yml"


def _create_tables(connection: duckdb.DuckDBPyConnection) -> None:
    connection.execute("""
        CREATE TABLE jobs (
            canonical_job_id VARCHAR,
            role_id VARCHAR,
            city_code VARCHAR,
            experience_band VARCHAR,
            education_band VARCHAR,
            published_at DATE,
            salary_mid_monthly DOUBLE
        );
        CREATE TABLE job_source_map (
            canonical_job_id VARCHAR,
            silver_job_id VARCHAR,
            source_id VARCHAR
        );
        CREATE TABLE skills (
            skill_id VARCHAR,
            canonical_name VARCHAR,
            category VARCHAR
        );
        CREATE TABLE job_skills (
            canonical_job_id VARCHAR,
            silver_job_id VARCHAR,
            skill_id VARCHAR
        );
    """)


def _config(**sections: dict[str, object]):
    config = load_advanced_analytics_config(CONFIG_PATH)
    updates = {
        name: getattr(config, name).model_copy(update=values)
        for name, values in sections.items()
    }
    return config.model_copy(update=updates)


def _trend_warehouse(
    path: Path,
    coverages: list[int] | None = None,
    monthly_job_count: int = 10,
) -> Path:
    connection = duckdb.connect(str(path))
    try:
        _create_tables(connection)
        connection.execute("INSERT INTO skills VALUES ('python', 'Python', 'programming')")
        coverages = coverages or [1, 1, 2, 3, 4, 5, 6]
        jobs = []
        mappings = []
        relations = []
        for month, python_jobs in enumerate(coverages, start=1):
            for index in range(monthly_job_count):
                job_id = f"job-{month}-{index}"
                silver_id = f"silver-{month}-{index}"
                jobs.append((job_id, "data_analyst", "CN-110000", "mid", "bachelor", date(2026, month, 1), 20000.0))
                mappings.append((job_id, silver_id, "source_a"))
                if index < python_jobs:
                    relations.append((job_id, silver_id, "python"))
        connection.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)", jobs)
        connection.executemany("INSERT INTO job_source_map VALUES (?, ?, ?)", mappings)
        connection.executemany("INSERT INTO job_skills VALUES (?, ?, ?)", relations)
    finally:
        connection.close()
    return path


def _salary_warehouse(path: Path) -> Path:
    connection = duckdb.connect(str(path))
    try:
        _create_tables(connection)
        connection.execute("""
            INSERT INTO skills VALUES
                ('python', 'Python', 'programming'),
                ('sql', 'SQL', 'database')
        """)
        jobs = []
        mappings = []
        relations = []
        for index in range(120):
            has_python = index % 2 == 0
            role = ("data_analyst", "backend_engineer", "data_engineer")[index % 3]
            city = ("CN-110000", "CN-310000")[index % 5 == 0]
            experience = ("entry", "mid", "senior")[index % 7 % 3]
            education = ("bachelor", "master")[index % 11 == 0]
            month = index % 5 + 1
            role_factor = {"data_analyst": 1.0, "backend_engineer": 1.15, "data_engineer": 1.1}[role]
            city_factor = 1.08 if city == "CN-310000" else 1.0
            experience_factor = {"entry": 0.85, "mid": 1.0, "senior": 1.25}[experience]
            skill_factor = 1.2 if has_python else 1.0
            noise = 1.02 if index % 4 < 2 else 0.98
            salary = 18000 * role_factor * city_factor * experience_factor * skill_factor * noise
            job_id = f"job-{index}"
            silver_id = f"silver-{index}"
            jobs.append((job_id, role, city, experience, education, date(2026, month, 1), salary))
            mappings.append((job_id, silver_id, "source_a"))
            relations.append((job_id, silver_id, "sql"))
            if has_python:
                relations.append((job_id, silver_id, "python"))
        connection.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)", jobs)
        connection.executemany("INSERT INTO job_source_map VALUES (?, ?, ?)", mappings)
        connection.executemany("INSERT INTO job_skills VALUES (?, ?, ?)", relations)
    finally:
        connection.close()
    return path


def _network_warehouse(path: Path) -> Path:
    connection = duckdb.connect(str(path))
    try:
        _create_tables(connection)
        connection.execute("""
            INSERT INTO skills VALUES
                ('a', 'Skill A', 'programming'),
                ('b', 'Skill B', 'database'),
                ('c', 'Skill C', 'cloud')
        """)
        skill_sets = [("a", "b"), ("a", "b"), ("a", "c"), ("b", "c")]
        for index, skill_set in enumerate(skill_sets):
            job_id = f"job-{index}"
            silver_id = f"silver-{index}"
            connection.execute(
                "INSERT INTO jobs VALUES (?, 'data_analyst', 'CN-110000', 'mid', 'bachelor', DATE '2026-01-01', 20000)",
                [job_id],
            )
            connection.execute("INSERT INTO job_source_map VALUES (?, ?, 'source_a')", [job_id, silver_id])
            for skill_id in skill_set:
                connection.execute("INSERT INTO job_skills VALUES (?, ?, ?)", [job_id, silver_id, skill_id])
    finally:
        connection.close()
    return path


def test_skill_trend_uses_monthly_coverage_and_transparent_changes(tmp_path: Path) -> None:
    config = _config(
        trend={
            "minimum_observed_months": 7,
            "minimum_monthly_sample_size": 1,
            "minimum_total_sample_size": 1,
        }
    )
    analytics = AdvancedAnalyticsRepository(_trend_warehouse(tmp_path / "trend.duckdb"), config=config)

    result = analytics.skill_trend()

    python = result.records[0]
    assert python.monthly[-1].job_count == 6
    assert python.monthly[-1].sample_size == 10
    assert python.monthly[-1].skill_job_coverage == pytest.approx(0.6)
    assert python.monthly[-1].rolling_mean == pytest.approx(0.5)
    assert python.change_3m == pytest.approx(0.3)
    assert python.change_6m == pytest.approx(0.5)
    assert python.trend_slope > 0
    assert python.classification == "Growing"


def test_skill_trend_with_low_sample_has_no_strong_classification(tmp_path: Path) -> None:
    analytics = AdvancedAnalyticsRepository(_trend_warehouse(tmp_path / "trend.duckdb"))

    python = analytics.skill_trend().records[0]

    assert python.classification is None
    assert python.conclusion_strength == "insufficient"


@pytest.mark.parametrize(
    ("coverage_counts", "monthly_job_count", "expected"),
    [
        ([0, 0, 0, 0, 1, 2, 3], 20, "Emerging"),
        ([2, 2, 4, 6, 8, 10, 12], 20, "Growing"),
        ([6, 6, 6, 6, 6, 6, 6], 20, "Mature"),
        ([2, 2, 2, 2, 2, 2, 2], 20, "Stable"),
        ([12, 10, 8, 6, 4, 2, 1], 20, "Declining"),
        ([1, 1, 1, 1, 1, 1, 1], 40, "Niche"),
    ],
)
def test_skill_trend_classification_rules_cover_all_labels(
    tmp_path: Path,
    coverage_counts: list[int],
    monthly_job_count: int,
    expected: str,
) -> None:
    config = _config(
        trend={
            "minimum_observed_months": 7,
            "minimum_monthly_sample_size": 1,
            "minimum_total_sample_size": 1,
        }
    )
    warehouse = _trend_warehouse(
        tmp_path / f"{expected}.duckdb",
        coverage_counts,
        monthly_job_count,
    )

    record = AdvancedAnalyticsRepository(warehouse, config=config).skill_trend().records[0]

    assert record.classification == expected
    assert record.conclusion_strength == "qualified"


def test_adjusted_salary_association_controls_covariates_and_reports_diagnostics(tmp_path: Path) -> None:
    config = _config(
        salary={
            "minimum_sample_size": 50,
            "minimum_skill_jobs": 20,
            "minimum_non_skill_jobs": 20,
        }
    )
    analytics = AdvancedAnalyticsRepository(_salary_warehouse(tmp_path / "salary.duckdb"), config=config)

    result = analytics.adjusted_salary_association(skill_ids=("python", "sql"))

    python = next(record for record in result.records if record.skill_id == "python")
    assert python.status in {"estimated", "estimated_with_warning"}
    assert python.coefficient == pytest.approx(log(1.2), abs=0.02)
    assert python.percentage_approximation == pytest.approx(20.0, abs=2.0)
    assert python.confidence_interval_low < python.coefficient < python.confidence_interval_high
    assert python.p_value < 0.05
    assert python.sample_size == 120
    assert python.diagnostics.covariance_type == "HC3"
    assert python.diagnostics.control_variable_count > 0

    sql = next(record for record in result.records if record.skill_id == "sql")
    assert sql.status == "insufficient_sample"
    assert sql.coefficient is None


def test_adjusted_salary_association_requires_positive_residual_degrees_of_freedom(tmp_path: Path) -> None:
    database_path = tmp_path / "zero-df.duckdb"
    connection = duckdb.connect(str(database_path))
    try:
        _create_tables(connection)
        connection.execute("INSERT INTO skills VALUES ('python', 'Python', 'programming')")
        roles = ["base", "base", "role-1", "role-2", "role-3"]
        for index, role in enumerate(roles):
            job_id = f"job-{index}"
            silver_id = f"silver-{index}"
            connection.execute(
                "INSERT INTO jobs VALUES (?, ?, 'CN-110000', 'mid', 'bachelor', DATE '2026-01-01', ?)",
                [job_id, role, 10000 + index * 1000],
            )
            connection.execute("INSERT INTO job_source_map VALUES (?, ?, 'source_a')", [job_id, silver_id])
            if index == 0:
                connection.execute("INSERT INTO job_skills VALUES (?, ?, 'python')", [job_id, silver_id])
    finally:
        connection.close()
    config = _config(
        salary={
            "minimum_sample_size": 3,
            "minimum_skill_jobs": 1,
            "minimum_non_skill_jobs": 1,
        }
    )

    record = AdvancedAnalyticsRepository(database_path, config=config).adjusted_salary_association().records[0]

    assert record.status == "insufficient_sample"
    assert "residual_degrees_of_freedom_not_positive" in record.diagnostics.warnings


def test_adjusted_salary_association_marks_missing_salary_data_unavailable(tmp_path: Path) -> None:
    config = _config()
    analytics = AdvancedAnalyticsRepository(_salary_warehouse(tmp_path / "salary.duckdb"), config=config)

    record = analytics.adjusted_salary_association(
        AnalyticsFilters(published_from=date(2030, 1, 1)), skill_ids=("python",)
    ).records[0]

    assert record.status == "unavailable"
    assert "no_salary_sample" in record.diagnostics.warnings


def test_skill_network_filters_low_support_edges_and_writes_communities(tmp_path: Path) -> None:
    config = _config(network={"minimum_cooccurrence_count": 2, "minimum_jaccard": 0.0})
    analytics = AdvancedAnalyticsRepository(_network_warehouse(tmp_path / "network.duckdb"), config=config)
    nodes_path = tmp_path / "skill_graph_nodes.parquet"
    edges_path = tmp_path / "skill_graph_edges.parquet"

    report = analytics.build_skill_network(nodes_output_path=nodes_path, edges_output_path=edges_path)

    nodes = pl.read_parquet(nodes_path)
    edges = pl.read_parquet(edges_path)
    assert report.node_count == 3
    assert report.edge_count == 1
    assert report.filtered_edge_count == 2
    edge = edges.row(0, named=True)
    assert (edge["skill_a_id"], edge["skill_b_id"]) == ("a", "b")
    assert edge["cooccurrence_count"] == 2
    assert edge["jaccard"] == pytest.approx(0.5)
    assert edge["pmi"] == pytest.approx(log(8 / 9))
    communities = dict(zip(nodes["skill_id"], nodes["community_id"], strict=True))
    assert communities["a"] == communities["b"]
    assert communities["c"] != communities["a"]


def test_advanced_analytics_supports_existing_market_filters(tmp_path: Path) -> None:
    config = _config(trend={"minimum_monthly_sample_size": 1, "minimum_total_sample_size": 1})
    analytics = AdvancedAnalyticsRepository(_trend_warehouse(tmp_path / "filters.duckdb"), config=config)
    filters = AnalyticsFilters(role_id="backend_engineer")

    assert analytics.skill_trend(filters).records == ()
