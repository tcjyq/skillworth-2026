from __future__ import annotations

from collections import defaultdict
from datetime import date
from itertools import combinations
from math import log
from pathlib import Path
from statistics import stdev
from typing import Any, Literal

import duckdb
import networkx as nx
import numpy as np
import polars as pl
import statsmodels.api as sm
from pydantic import BaseModel, ConfigDict, Field

from .advanced_config import AdvancedAnalyticsConfig, TrendConfig, load_advanced_analytics_config
from .analytics import (
    AnalyticsFilters,
    AnalyticsMetadata,
    _fetch_rows,
    _filtered_jobs,
    _metadata,
    _jobs_has_market_scope,
    _source_filter,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CONFIG_PATH = REPOSITORY_ROOT / "data/reference/advanced_analytics.v1.yml"
ADVANCED_SQL_DIRECTORY = Path(__file__).parent / "sql"
ADVANCED_METHODOLOGY_VERSION = "phase7_advanced_analytics_v1"
TrendClassification = Literal["Emerging", "Growing", "Mature", "Stable", "Declining", "Niche"]


class MonthlySkillTrendPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    month: date
    job_count: int = Field(ge=0)
    sample_size: int = Field(ge=1)
    skill_job_coverage: float = Field(ge=0, le=1)
    rolling_mean: float | None = Field(default=None, ge=0, le=1)


class SkillTrendRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    monthly: tuple[MonthlySkillTrendPoint, ...]
    change_3m: float | None
    change_6m: float | None
    trend_slope: float | None
    volatility: float | None = Field(default=None, ge=0)
    observed_month_count: int = Field(ge=0)
    qualified_month_count: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    posting_date_coverage: float = Field(ge=0, le=1)
    classification: TrendClassification | None
    conclusion_strength: Literal["qualified", "insufficient", "inconclusive"]
    limitations: tuple[str, ...]


class SkillTrendResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    config_version: str
    records: tuple[SkillTrendRecord, ...]


class SalaryModelDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True)

    covariance_type: str
    r_squared: float | None = None
    adjusted_r_squared: float | None = None
    aic: float | None = None
    bic: float | None = None
    residual_std_error: float | None = None
    residual_degrees_of_freedom: float | None = None
    condition_number: float | None = None
    matrix_rank: int | None = None
    parameter_count: int = Field(ge=0)
    control_variable_count: int = Field(ge=0)
    warnings: tuple[str, ...] = ()


class AdjustedSalaryAssociationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    canonical_name: str
    category: str
    coefficient: float | None
    percentage_approximation: float | None
    confidence_interval_low: float | None
    confidence_interval_high: float | None
    percentage_confidence_interval_low: float | None
    percentage_confidence_interval_high: float | None
    p_value: float | None = Field(default=None, ge=0, le=1)
    sample_size: int = Field(ge=0)
    skill_job_count: int = Field(ge=0)
    non_skill_job_count: int = Field(ge=0)
    status: Literal[
        "estimated",
        "estimated_with_warning",
        "unavailable",
        "insufficient_sample",
        "rank_deficient",
        "model_error",
    ]
    diagnostics: SalaryModelDiagnostics


class AdjustedSalaryAssociationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    metadata: AnalyticsMetadata
    config_version: str
    records: tuple[AdjustedSalaryAssociationRecord, ...]


class SkillNetworkBuildReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    methodology_version: str = ADVANCED_METHODOLOGY_VERSION
    config_version: str
    sample_size: int = Field(ge=0)
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    filtered_edge_count: int = Field(ge=0)
    community_count: int = Field(ge=0)
    nodes_output_path: Path
    edges_output_path: Path


class AdvancedAnalyticsRepository:
    def __init__(
        self,
        database_path: Path,
        *,
        config: AdvancedAnalyticsConfig | None = None,
        config_path: Path = DEFAULT_CONFIG_PATH,
    ) -> None:
        self._database_path = database_path.resolve()
        if not self._database_path.is_file():
            raise FileNotFoundError(f"Analytics warehouse does not exist: {self._database_path}")
        self.config = config or load_advanced_analytics_config(config_path)
        self._market_scope_available = _jobs_has_market_scope(self._database_path)

    def skill_trend(self, filters: AnalyticsFilters | None = None) -> SkillTrendResult:
        filters = filters or AnalyticsFilters()
        rows, metadata = self._query("skill_trend.sql", "skill_trend", filters, source_filter_references=1)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[row["skill_id"]].append(row)
        records = tuple(
            _skill_trend_record(skill_rows, self.config.trend, metadata.sample_size)
            for _, skill_rows in sorted(grouped.items())
        )
        return SkillTrendResult(metadata=metadata, config_version=self.config.version, records=records)

    def adjusted_salary_association(
        self,
        filters: AnalyticsFilters | None = None,
        *,
        skill_ids: tuple[str, ...] | None = None,
    ) -> AdjustedSalaryAssociationResult:
        filters = filters or AnalyticsFilters()
        if skill_ids is not None and any(not skill_id.strip() for skill_id in skill_ids):
            raise ValueError("skill_ids cannot contain blank values")
        rows, catalog, metadata = self._salary_model_inputs(filters)
        requested = set(skill_ids) if skill_ids is not None else None
        known = {row["skill_id"] for row in catalog}
        missing = requested - known if requested is not None else set()
        if missing:
            raise ValueError(f"Unknown skill_ids: {sorted(missing)}")
        observed = {skill_id for row in rows for skill_id in (row["skill_ids"] or [])}
        selected_catalog = [
            row for row in catalog
            if row["skill_id"] in (requested if requested is not None else observed)
        ]
        records = _fit_salary_models(rows, selected_catalog, self.config)
        return AdjustedSalaryAssociationResult(
            metadata=metadata,
            config_version=self.config.version,
            records=tuple(records),
        )

    def build_skill_network(
        self,
        *,
        nodes_output_path: Path = REPOSITORY_ROOT / "data/gold/skill_graph_nodes.parquet",
        edges_output_path: Path = REPOSITORY_ROOT / "data/gold/skill_graph_edges.parquet",
        filters: AnalyticsFilters | None = None,
    ) -> SkillNetworkBuildReport:
        filters = filters or AnalyticsFilters()
        nodes_output_path = nodes_output_path.resolve()
        edges_output_path = edges_output_path.resolve()
        if nodes_output_path == edges_output_path:
            raise ValueError("Skill network node and edge outputs must be different files")
        rows, metadata = self._query(
            "skill_network_data.sql",
            "skill_network",
            filters,
            source_filter_references=1,
        )
        nodes, edges, candidate_edge_count, community_count = _build_skill_graph(
            rows,
            metadata.sample_size,
            self.config,
        )
        node_frame = _network_frame(nodes, _NODE_SCHEMA)
        edge_frame = _network_frame(edges, _EDGE_SCHEMA)
        _write_parquet_atomic(node_frame, nodes_output_path)
        _write_parquet_atomic(edge_frame, edges_output_path)
        return SkillNetworkBuildReport(
            config_version=self.config.version,
            sample_size=metadata.sample_size,
            node_count=len(nodes),
            edge_count=len(edges),
            filtered_edge_count=candidate_edge_count - len(edges),
            community_count=community_count,
            nodes_output_path=nodes_output_path,
            edges_output_path=edges_output_path,
        )

    def _salary_model_inputs(
        self,
        filters: AnalyticsFilters,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], AnalyticsMetadata]:
        filtered_jobs, parameters = _filtered_jobs(filters, self._market_scope_available)
        source_filter, source_parameters = _source_filter(filters, "mapping")
        sql = (ADVANCED_SQL_DIRECTORY / "salary_model_data.sql").read_text(encoding="utf-8").format(
            filtered_jobs=filtered_jobs,
            source_filter=source_filter,
        )
        salary = self.config.salary
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            rows = _fetch_rows(
                connection,
                sql,
                parameters
                + source_parameters
                + [salary.minimum_salary_monthly, salary.maximum_salary_monthly],
            )
            catalog = _fetch_rows(
                connection,
                "SELECT skill_id, canonical_name, category FROM skills ORDER BY skill_id",
                [],
            )
            metadata = _metadata(
                connection,
                filters,
                "adjusted_salary_association",
                market_scope_available=self._market_scope_available,
            ).model_copy(
                update={"methodology_version": ADVANCED_METHODOLOGY_VERSION}
            )
        finally:
            connection.close()
        return rows, catalog, metadata

    def _query(
        self,
        filename: str,
        metric_name: str,
        filters: AnalyticsFilters,
        *,
        source_filter_references: int = 0,
    ) -> tuple[list[dict[str, Any]], AnalyticsMetadata]:
        filtered_jobs, parameters = _filtered_jobs(filters, self._market_scope_available)
        source_filter, source_parameters = _source_filter(filters, "mapping")
        sql = (ADVANCED_SQL_DIRECTORY / filename).read_text(encoding="utf-8").format(
            filtered_jobs=filtered_jobs,
            source_filter=source_filter,
        )
        connection = duckdb.connect(str(self._database_path), read_only=True)
        try:
            rows = _fetch_rows(
                connection,
                sql,
                parameters + source_parameters * source_filter_references,
            )
            metadata = _metadata(
                connection,
                filters,
                metric_name,
                market_scope_available=self._market_scope_available,
            ).model_copy(
                update={"methodology_version": ADVANCED_METHODOLOGY_VERSION}
            )
        finally:
            connection.close()
        return rows, metadata


def _skill_trend_record(
    rows: list[dict[str, Any]], config: TrendConfig, total_market_sample_size: int
) -> SkillTrendRecord:
    rows.sort(key=lambda row: row["month"])
    ordinals = [_month_ordinal(row["month"]) for row in rows]
    coverages = [float(row["skill_job_coverage"]) for row in rows]
    monthly: list[MonthlySkillTrendPoint] = []
    for index, row in enumerate(rows):
        start = index - config.rolling_window_months + 1
        rolling_mean = None
        if start >= 0 and ordinals[index] - ordinals[start] == config.rolling_window_months - 1:
            rolling_mean = sum(coverages[start:index + 1]) / config.rolling_window_months
        monthly.append(
            MonthlySkillTrendPoint(
                month=row["month"],
                job_count=row["job_count"],
                sample_size=row["sample_size"],
                skill_job_coverage=row["skill_job_coverage"],
                rolling_mean=rolling_mean,
            )
        )

    qualified = [
        point for point in monthly
        if point.sample_size >= config.minimum_monthly_sample_size
    ]
    qualified_by_month = {_month_ordinal(point.month): point for point in qualified}
    latest = qualified[-1] if qualified else None
    latest_ordinal = _month_ordinal(latest.month) if latest else None
    change_3m = _coverage_change(qualified_by_month, latest_ordinal, 3)
    change_6m = _coverage_change(qualified_by_month, latest_ordinal, 6)
    slope = _trend_slope(qualified)
    volatility = _trend_volatility(qualified)
    sample_size = sum(point.sample_size for point in monthly)
    posting_date_coverage = (
        min(1.0, sample_size / total_market_sample_size) if total_market_sample_size else 0.0
    )
    classification, strength, limitations = _classify_trend(
        latest=latest,
        change_3m=change_3m,
        slope=slope,
        volatility=volatility,
        qualified_by_month=qualified_by_month,
        sample_size=sample_size,
        posting_date_coverage=posting_date_coverage,
        config=config,
    )
    first = rows[0]
    return SkillTrendRecord(
        skill_id=first["skill_id"],
        canonical_name=first["canonical_name"],
        category=first["category"],
        monthly=tuple(monthly),
        change_3m=change_3m,
        change_6m=change_6m,
        trend_slope=slope,
        volatility=volatility,
        observed_month_count=len(monthly),
        qualified_month_count=len(qualified),
        sample_size=sample_size,
        posting_date_coverage=posting_date_coverage,
        classification=classification,
        conclusion_strength=strength,
        limitations=limitations,
    )


def _month_ordinal(month: date) -> int:
    return month.year * 12 + month.month


def _coverage_change(
    points: dict[int, MonthlySkillTrendPoint],
    latest_ordinal: int | None,
    lag: int,
) -> float | None:
    if latest_ordinal is None or latest_ordinal - lag not in points:
        return None
    return points[latest_ordinal].skill_job_coverage - points[latest_ordinal - lag].skill_job_coverage


def _trend_slope(points: list[MonthlySkillTrendPoint]) -> float | None:
    if len(points) < 2:
        return None
    x = [_month_ordinal(point.month) for point in points]
    y = [point.skill_job_coverage for point in points]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return None
    return sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(x, y, strict=True)) / denominator


def _trend_volatility(points: list[MonthlySkillTrendPoint]) -> float | None:
    differences = [
        current.skill_job_coverage - previous.skill_job_coverage
        for previous, current in zip(points, points[1:])
        if _month_ordinal(current.month) - _month_ordinal(previous.month) == 1
    ]
    return stdev(differences) if len(differences) >= 2 else None


def _classify_trend(
    *,
    latest: MonthlySkillTrendPoint | None,
    change_3m: float | None,
    slope: float | None,
    volatility: float | None,
    qualified_by_month: dict[int, MonthlySkillTrendPoint],
    sample_size: int,
    posting_date_coverage: float,
    config: TrendConfig,
) -> tuple[TrendClassification | None, Literal["qualified", "insufficient", "inconclusive"], tuple[str, ...]]:
    limitations: list[str] = []
    if len(qualified_by_month) < config.minimum_observed_months:
        limitations.append("qualified_month_count_below_threshold")
    if sample_size < config.minimum_total_sample_size:
        limitations.append("total_sample_size_below_threshold")
    if posting_date_coverage < config.minimum_posting_date_coverage:
        limitations.append("posting_date_coverage_below_threshold")
    if latest is None or latest.sample_size < config.minimum_monthly_sample_size:
        limitations.append("latest_month_sample_below_threshold")
    if limitations:
        return None, "insufficient", tuple(limitations)
    if slope is None or volatility is None or change_3m is None:
        return None, "inconclusive", ("required_trend_statistic_unavailable",)

    latest_ordinal = _month_ordinal(latest.month)
    previous_3m = qualified_by_month.get(latest_ordinal - 3)
    if slope <= config.declining_max_slope and change_3m <= config.declining_max_change_3m:
        return "Declining", "qualified", ()
    if (
        previous_3m is not None
        and previous_3m.skill_job_coverage <= config.emerging_max_coverage_3m_ago
        and change_3m >= config.emerging_min_change_3m
    ):
        return "Emerging", "qualified", ()
    if slope >= config.growing_min_slope and change_3m >= config.growing_min_change_3m:
        return "Growing", "qualified", ()
    if (
        latest.skill_job_coverage >= config.mature_min_latest_coverage
        and abs(slope) <= config.mature_max_abs_slope
        and volatility <= config.mature_max_volatility
    ):
        return "Mature", "qualified", ()
    if latest.skill_job_coverage <= config.niche_max_latest_coverage and abs(slope) <= config.niche_max_abs_slope:
        return "Niche", "qualified", ()
    if abs(slope) <= config.stable_max_abs_slope and volatility <= config.stable_max_volatility:
        return "Stable", "qualified", ()
    return None, "inconclusive", ("classification_rules_not_matched",)


def _fit_salary_models(
    rows: list[dict[str, Any]],
    catalog: list[dict[str, Any]],
    config: AdvancedAnalyticsConfig,
) -> list[AdjustedSalaryAssociationRecord]:
    if not rows:
        return [
            _unavailable_salary_record(skill, 0, 0, 0, config, "unavailable", ("no_salary_sample",))
            for skill in catalog
        ]
    controls, control_names, dropped_control_names = _control_matrix(rows)
    control_warnings = (
        (f"redundant_control_columns_dropped:{','.join(dropped_control_names)}",)
        if dropped_control_names
        else ()
    )
    salaries = np.asarray([float(row["salary_mid_monthly"]) for row in rows], dtype=float)
    outcome = np.log(salaries)
    skill_sets = [set(row["skill_ids"] or []) for row in rows]
    records: list[AdjustedSalaryAssociationRecord] = []
    for skill in catalog:
        has_skill = np.asarray(
            [1.0 if skill["skill_id"] in row_skills else 0.0 for row_skills in skill_sets],
            dtype=float,
        )
        skill_count = int(has_skill.sum())
        non_skill_count = len(rows) - skill_count
        if (
            len(rows) < config.salary.minimum_sample_size
            or skill_count < config.salary.minimum_skill_jobs
            or non_skill_count < config.salary.minimum_non_skill_jobs
        ):
            records.append(
                _unavailable_salary_record(
                    skill,
                    len(rows),
                    skill_count,
                    non_skill_count,
                    config,
                    "insufficient_sample",
                    ("salary_or_skill_sample_below_threshold",) + control_warnings,
                    control_variable_count=len(control_names),
                )
            )
            continue

        design = np.column_stack((controls[:, 0], has_skill, controls[:, 1:]))
        rank = int(np.linalg.matrix_rank(design))
        if len(rows) <= design.shape[1]:
            records.append(
                _unavailable_salary_record(
                    skill,
                    len(rows),
                    skill_count,
                    non_skill_count,
                    config,
                    "insufficient_sample",
                    ("residual_degrees_of_freedom_not_positive",) + control_warnings,
                    matrix_rank=rank,
                    parameter_count=design.shape[1],
                    control_variable_count=len(control_names),
                )
            )
            continue
        if rank < design.shape[1]:
            records.append(
                _unavailable_salary_record(
                    skill,
                    len(rows),
                    skill_count,
                    non_skill_count,
                    config,
                    "rank_deficient",
                    ("design_matrix_rank_deficient",) + control_warnings,
                    matrix_rank=rank,
                    parameter_count=design.shape[1],
                    control_variable_count=len(control_names),
                )
            )
            continue
        try:
            fitted = sm.OLS(outcome, design).fit(cov_type=config.salary.covariance_type)
            coefficient = float(fitted.params[1])
            interval = fitted.conf_int(alpha=1 - config.salary.confidence_level)[1]
            interval_low, interval_high = float(interval[0]), float(interval[1])
            condition_number = float(fitted.condition_number)
            p_value = float(fitted.pvalues[1])
            if not np.isfinite([coefficient, interval_low, interval_high, condition_number, p_value]).all():
                raise FloatingPointError("non-finite salary model output")
            warnings = control_warnings
            status: Literal["estimated", "estimated_with_warning"] = "estimated"
            if condition_number > config.salary.maximum_condition_number:
                status = "estimated_with_warning"
                warnings = warnings + ("condition_number_above_threshold",)
            residual_std_error = (
                float(np.sqrt(fitted.ssr / fitted.df_resid))
                if fitted.df_resid > 0
                else None
            )
            diagnostics = SalaryModelDiagnostics(
                covariance_type=config.salary.covariance_type,
                r_squared=float(fitted.rsquared),
                adjusted_r_squared=float(fitted.rsquared_adj),
                aic=float(fitted.aic),
                bic=float(fitted.bic),
                residual_std_error=residual_std_error,
                residual_degrees_of_freedom=float(fitted.df_resid),
                condition_number=condition_number,
                matrix_rank=rank,
                parameter_count=design.shape[1],
                control_variable_count=len(control_names),
                warnings=warnings,
            )
            records.append(
                AdjustedSalaryAssociationRecord(
                    skill_id=skill["skill_id"],
                    canonical_name=skill["canonical_name"],
                    category=skill["category"],
                    coefficient=coefficient,
                    percentage_approximation=_coefficient_percent(coefficient),
                    confidence_interval_low=interval_low,
                    confidence_interval_high=interval_high,
                    percentage_confidence_interval_low=_coefficient_percent(interval_low),
                    percentage_confidence_interval_high=_coefficient_percent(interval_high),
                    p_value=p_value,
                    sample_size=len(rows),
                    skill_job_count=skill_count,
                    non_skill_job_count=non_skill_count,
                    status=status,
                    diagnostics=diagnostics,
                )
            )
        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as error:
            records.append(
                _unavailable_salary_record(
                    skill,
                    len(rows),
                    skill_count,
                    non_skill_count,
                    config,
                    "model_error",
                    (f"model_error:{type(error).__name__}",),
                    matrix_rank=rank,
                    parameter_count=design.shape[1],
                    control_variable_count=len(control_names),
                )
            )
    return records


def _control_matrix(rows: list[dict[str, Any]]) -> tuple[np.ndarray, list[str], list[str]]:
    candidate_columns = [np.ones(len(rows), dtype=float)]
    candidate_names: list[str] = []
    fields = ("role_id", "city_code", "experience_band", "education_band", "published_month")
    for field in fields:
        values = [str(row[field]) if row[field] is not None else "__missing__" for row in rows]
        categories = sorted(set(values))
        for category in categories[1:]:
            candidate_columns.append(np.asarray([1.0 if value == category else 0.0 for value in values]))
            candidate_names.append(f"{field}={category}")

    retained = [candidate_columns[0]]
    retained_names: list[str] = []
    dropped_names: list[str] = []
    current_rank = 1
    for column, name in zip(candidate_columns[1:], candidate_names, strict=True):
        candidate = np.column_stack((*retained, column))
        candidate_rank = int(np.linalg.matrix_rank(candidate))
        if candidate_rank > current_rank:
            retained.append(column)
            retained_names.append(name)
            current_rank = candidate_rank
        else:
            dropped_names.append(name)
    return np.column_stack(retained), retained_names, dropped_names


def _coefficient_percent(coefficient: float) -> float:
    return float(100 * np.expm1(coefficient))


def _unavailable_salary_record(
    skill: dict[str, Any],
    sample_size: int,
    skill_count: int,
    non_skill_count: int,
    config: AdvancedAnalyticsConfig,
    status: Literal["unavailable", "insufficient_sample", "rank_deficient", "model_error"],
    warnings: tuple[str, ...],
    *,
    matrix_rank: int | None = None,
    parameter_count: int = 0,
    control_variable_count: int = 0,
) -> AdjustedSalaryAssociationRecord:
    diagnostics = SalaryModelDiagnostics(
        covariance_type=config.salary.covariance_type,
        matrix_rank=matrix_rank,
        parameter_count=parameter_count,
        control_variable_count=control_variable_count,
        warnings=warnings,
    )
    return AdjustedSalaryAssociationRecord(
        skill_id=skill["skill_id"],
        canonical_name=skill["canonical_name"],
        category=skill["category"],
        coefficient=None,
        percentage_approximation=None,
        confidence_interval_low=None,
        confidence_interval_high=None,
        percentage_confidence_interval_low=None,
        percentage_confidence_interval_high=None,
        p_value=None,
        sample_size=sample_size,
        skill_job_count=skill_count,
        non_skill_job_count=non_skill_count,
        status=status,
        diagnostics=diagnostics,
    )


_NODE_SCHEMA = {
    "skill_id": pl.String,
    "canonical_name": pl.String,
    "category": pl.String,
    "job_count": pl.Int64,
    "job_coverage": pl.Float64,
    "degree": pl.Int64,
    "weighted_degree": pl.Float64,
    "community_id": pl.Int64,
    "methodology_version": pl.String,
    "config_version": pl.String,
}
_EDGE_SCHEMA = {
    "skill_a_id": pl.String,
    "skill_b_id": pl.String,
    "cooccurrence_count": pl.Int64,
    "jaccard": pl.Float64,
    "pmi": pl.Float64,
    "weight": pl.Float64,
    "methodology_version": pl.String,
    "config_version": pl.String,
}


def _build_skill_graph(
    rows: list[dict[str, Any]],
    sample_size: int,
    config: AdvancedAnalyticsConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    job_skills: dict[str, set[str]] = defaultdict(set)
    skill_metadata: dict[str, tuple[str, str]] = {}
    for row in rows:
        job_skills[row["canonical_job_id"]].add(row["skill_id"])
        skill_metadata[row["skill_id"]] = (row["canonical_name"], row["category"])

    supports: dict[str, int] = defaultdict(int)
    pair_supports: dict[tuple[str, str], int] = defaultdict(int)
    for skills in job_skills.values():
        ordered = sorted(skills)
        for skill_id in ordered:
            supports[skill_id] += 1
        for pair in combinations(ordered, 2):
            pair_supports[pair] += 1

    graph = nx.Graph()
    for skill_id in sorted(supports):
        graph.add_node(skill_id)

    edges: list[dict[str, Any]] = []
    for (skill_a, skill_b), cooccurrence_count in sorted(pair_supports.items()):
        union_count = supports[skill_a] + supports[skill_b] - cooccurrence_count
        jaccard = cooccurrence_count / union_count
        pmi = log(cooccurrence_count * sample_size / (supports[skill_a] * supports[skill_b]))
        if (
            cooccurrence_count < config.network.minimum_cooccurrence_count
            or jaccard < config.network.minimum_jaccard
        ):
            continue
        weight = jaccard if config.network.edge_weight == "jaccard" else float(cooccurrence_count)
        graph.add_edge(
            skill_a,
            skill_b,
            weight=weight,
            jaccard=jaccard,
            pmi=pmi,
            cooccurrence_count=cooccurrence_count,
        )
        edges.append(
            {
                "skill_a_id": skill_a,
                "skill_b_id": skill_b,
                "cooccurrence_count": cooccurrence_count,
                "jaccard": jaccard,
                "pmi": pmi,
                "weight": weight,
                "methodology_version": ADVANCED_METHODOLOGY_VERSION,
                "config_version": config.version,
            }
        )

    communities = _communities(graph)
    community_by_skill = {
        skill_id: community_id
        for community_id, community in enumerate(communities)
        for skill_id in community
    }
    nodes = []
    for skill_id in sorted(supports):
        canonical_name, category = skill_metadata[skill_id]
        nodes.append(
            {
                "skill_id": skill_id,
                "canonical_name": canonical_name,
                "category": category,
                "job_count": supports[skill_id],
                "job_coverage": supports[skill_id] / sample_size if sample_size else 0.0,
                "degree": int(graph.degree(skill_id)),
                "weighted_degree": float(graph.degree(skill_id, weight="weight")),
                "community_id": community_by_skill[skill_id],
                "methodology_version": ADVANCED_METHODOLOGY_VERSION,
                "config_version": config.version,
            }
        )
    return nodes, edges, len(pair_supports), len(communities)


def _communities(graph: nx.Graph) -> list[set[str]]:
    if graph.number_of_nodes() == 0:
        return []
    if graph.number_of_edges() == 0:
        return [{node} for node in sorted(graph.nodes)]
    detected = [set(community) for community in nx.community.greedy_modularity_communities(graph, weight="weight")]
    return sorted(detected, key=lambda community: (-len(community), min(community)))


def _network_frame(rows: list[dict[str, Any]], schema: dict[str, pl.DataType]) -> pl.DataFrame:
    if not rows:
        return pl.Schema(schema).to_frame()
    return pl.from_dicts(rows, schema=schema, strict=True)


def _write_parquet_atomic(frame: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    frame.write_parquet(temporary)
    temporary.replace(path)
