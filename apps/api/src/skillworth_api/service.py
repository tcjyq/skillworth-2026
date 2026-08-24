from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar

import duckdb
import polars as pl

from skillworth_analytics import (
    AdvancedAnalyticsRepository,
    AnalyticsFilters,
    AnalyticsRepository,
    LearningOptimizer,
    LearningOptimizerRequest,
    OpportunityRequest,
    PersonalSkillOpportunityEngine,
    SkillRelationRepository,
    load_exploratory_relation_config,
    calculate_demand_ranks,
    load_data_confidence_config,
    load_decision_score_config,
)
from skillworth_analytics.advanced import AdjustedSalaryAssociationRecord, SkillTrendRecord
from skillworth_analytics.analytics import SalaryBySkillRecord, SkillDemandRecord
from app.source_registry import load_source_registry

from .cache import CacheLookup, TTLCache
from .schemas import (
    DataQualityResponse,
    ChinaSkillWorthQuery,
    ChinaSkillWorthSummaryResponse,
    ChinaSkillRelationsQuery,
    ChinaSkillRelationsResponse,
    MarketSummaryResponse,
    ProductScopeMetadata,
    RelatedSkillRecord,
    RelatedSkillsResponse,
    RoleRecord,
    RolesResponse,
    SourceRecord,
    SourcesResponse,
    SkillDetailResponse,
)
from .settings import ApiSettings, REPOSITORY_ROOT


T = TypeVar("T")


class ApiService:
    """Thin read service that delegates every analytical calculation to Phase 6-10 modules."""

    def __init__(self, settings: ApiSettings) -> None:
        self.settings = settings
        self._analytics = AnalyticsRepository(settings.warehouse_path)
        self._advanced = AdvancedAnalyticsRepository(settings.warehouse_path)
        confidence_config = load_data_confidence_config(
            REPOSITORY_ROOT / "data/reference/data_confidence.v1.yml"
        )
        decision_config = load_decision_score_config(
            REPOSITORY_ROOT / "data/reference/decision_scores.v1.yml"
        )
        self._opportunity = PersonalSkillOpportunityEngine(settings.warehouse_path, confidence_config)
        self._optimizer = LearningOptimizer(
            settings.warehouse_path,
            decision_config=decision_config,
            confidence_config=confidence_config,
        )
        self._cache = TTLCache(settings.cache_ttl_seconds)
        self._relations = SkillRelationRepository(
            settings.warehouse_path,
            load_exploratory_relation_config(
                REPOSITORY_ROOT / "data/reference/exploratory_relations.v1.yml"
            ),
        )
        self._source_registry = load_source_registry(
            REPOSITORY_ROOT / "data/reference/sources.v1.yml"
        )
        present_sources = {str(row["source_id"]) for row in self._query("SELECT DISTINCT source_id FROM job_source_map")}
        self._core_source_ids = tuple(sorted(
            source.source_id for source in self._source_registry.sources
            if source.analysis_role in {"core_market", "supplementary_market"}
            and source.source_id in present_sources
        ))

    def cached(self, key: str, loader: Callable[[], T]) -> CacheLookup[T]:
        return self._cache.get_or_load(key, loader)

    def market_summary(self, filters: AnalyticsFilters) -> MarketSummaryResponse:
        requested_filters = filters
        filters = self._core_filters(filters)
        demand = self._analytics.skill_demand(filters)
        balanced = self._analytics.platform_balanced_demand(
            requested_filters.model_copy(update={"source_scope": "all"})
        )
        salary = self._analytics.salary_by_skill(filters)
        return MarketSummaryResponse(
            metadata=demand.metadata,
            top_skills=tuple(sorted(demand.records, key=_demand_sort_key)[:20]),
            platform_balanced_top_skills=tuple(
                sorted(balanced.records, key=_balanced_sort_key)[:20]
            ),
            platform_balanced_eligible_source_count=balanced.eligible_source_count,
            platform_balanced_ineligible_sources=balanced.ineligible_sources,
            platform_balanced_methodology_version=balanced.methodology_version,
            salary_by_skill=tuple(
                sorted(salary.records, key=lambda item: (-item.sample_size, item.skill_id))[:20]
            ),
        )

    def skill_demand(self, filters: AnalyticsFilters):
        return self._analytics.skill_demand(filters)

    def market_trends(self, filters: AnalyticsFilters):
        return self._advanced.skill_trend(self._core_filters(filters))

    def china_skillworth_summary(
        self, query: ChinaSkillWorthQuery
    ) -> ChinaSkillWorthSummaryResponse:
        clauses = ["recency_window = ?", "role_id IS NULL"]
        parameters: list[object] = [query.recency_window]
        if query.role is not None:
            clauses[-1] = "role_id = ?"
            parameters.append(query.role)
        if query.eligibility != "all":
            clauses.append("skillworth_eligibility = ?")
            parameters.append(query.eligibility)
        if query.robustness != "all":
            clauses.append("robustness_level = ?")
            parameters.append(query.robustness)
        if query.skill_type is not None:
            clauses.append("skill_type = ?")
            parameters.append(query.skill_type)
        try:
            rows = self._query(
                "SELECT * FROM china_skillworth_visual_ready WHERE "
                + " AND ".join(clauses)
                + " ORDER BY skillworth_rank NULLS LAST, skillworth_score DESC, skill_id",
                parameters,
            )
        except duckdb.CatalogException as error:
            raise FileNotFoundError("China SkillWorth visual-ready data is unavailable") from error
        scope_clauses = ["recency_window = ?", "role_id IS NULL"]
        scope_parameters: list[object] = [query.recency_window]
        if query.role is not None:
            scope_clauses[-1] = "role_id = ?"
            scope_parameters.append(query.role)
        if rows and "demand_rank" not in rows[0]:
            rank_rows = self._query(
                "SELECT skill_id, job_count, skillworth_eligibility "
                "FROM china_skillworth_visual_ready WHERE "
                + " AND ".join(scope_clauses),
                scope_parameters,
            )
            demand_ranks = calculate_demand_ranks([
                (
                    str(item["skill_id"]),
                    int(item["job_count"]),
                    str(item["skillworth_eligibility"]),
                )
                for item in rank_rows
            ])
            for row in rows:
                row["demand_rank"] = demand_ranks.get(str(row["skill_id"]))
        scope = self._query(
            "SELECT coalesce(max(sample_size), 0) AS job_count, "
            "coalesce(max(company_sample_size), 0) AS company_count, "
            "count(DISTINCT skill_id) AS skill_count "
            "FROM china_skillworth_visual_ready WHERE " + " AND ".join(scope_clauses),
            scope_parameters,
        )[0]
        themes = self._query(
            "SELECT * FROM china_skillworth_market_themes WHERE recency_window = ? "
            "ORDER BY job_coverage DESC, market_theme",
            [query.recency_window],
        )
        return ChinaSkillWorthSummaryResponse(
            market_scope=self.settings.market_scope,
            source_role=self.settings.source_role,
            snapshot=self.settings.snapshot,
            access_date=self.settings.access_date,
            recency_window=query.recency_window,
            job_count=int(scope["job_count"]),
            company_count=int(scope["company_count"]),
            skill_count=int(scope["skill_count"]),
            source_count=self.settings.source_count,
            disclaimer=self.settings.disclaimer,
            market_themes=tuple(themes),
            records=tuple(rows),
        )

    def china_skill_relations(
        self, query: ChinaSkillRelationsQuery
    ) -> ChinaSkillRelationsResponse:
        if query.market_scope is not None and query.market_scope != self.settings.market_scope:
            raise ValueError("market_scope does not match the active dataset")
        if query.source_role is not None and query.source_role != self.settings.source_role:
            raise ValueError("source_role does not match the active dataset")
        as_of_date = self.settings.access_date
        if as_of_date is None:
            row = self._query("SELECT max(published_at) AS as_of_date FROM jobs")[0]
            as_of_date = row["as_of_date"] or date.today()
        result = self._relations.related_skills(
            core_skill_id=query.core_skill_id,
            role_id=query.role_id,
            recency_window=query.recency_window,
            as_of_date=as_of_date,
        )
        return ChinaSkillRelationsResponse(
            market_scope=self.settings.market_scope,
            source_role=self.settings.source_role,
            snapshot=self.settings.snapshot,
            **result.model_dump(),
        )

    def skill_detail(self, skill_id: str, filters: AnalyticsFilters) -> SkillDetailResponse | None:
        filters = self._core_filters(filters)
        demand = _find_skill(self._analytics.skill_demand(filters).records, skill_id)
        if demand is None:
            return None
        salary = _find_skill(self._analytics.salary_by_skill(filters).records, skill_id)
        association = self._advanced.adjusted_salary_association(
            filters, skill_ids=(skill_id,)
        ).records[0]
        trend = _find_skill(self._advanced.skill_trend(filters).records, skill_id)
        return SkillDetailResponse(
            demand=demand,
            salary_distribution=salary,
            adjusted_salary_association=association,
            trend=trend,
        )

    def skill_trend(self, skill_id: str, filters: AnalyticsFilters) -> SkillTrendRecord | None:
        return _find_skill(self._advanced.skill_trend(self._core_filters(filters)).records, skill_id)

    def skill_salary(
        self, skill_id: str, filters: AnalyticsFilters
    ) -> tuple[SalaryBySkillRecord | None, AdjustedSalaryAssociationRecord] | None:
        filters = self._core_filters(filters)
        if _find_skill(self._analytics.skill_demand(filters).records, skill_id) is None:
            return None
        salary = _find_skill(self._analytics.salary_by_skill(filters).records, skill_id)
        association = self._advanced.adjusted_salary_association(
            filters, skill_ids=(skill_id,)
        ).records[0]
        return salary, association

    def related_skills(self, skill_id: str) -> RelatedSkillsResponse | None:
        if not self.settings.graph_edges_path.is_file():
            raise FileNotFoundError(f"Skill graph does not exist: {self.settings.graph_edges_path}")
        catalog = {record.skill_id: record for record in self._analytics.skill_demand().records}
        if skill_id not in catalog:
            return None
        edges = pl.read_parquet(self.settings.graph_edges_path)
        related = (
            edges.filter((pl.col("skill_a_id") == skill_id) | (pl.col("skill_b_id") == skill_id))
            .with_columns(
                pl.when(pl.col("skill_a_id") == skill_id)
                .then(pl.col("skill_b_id"))
                .otherwise(pl.col("skill_a_id"))
                .alias("skill_id")
            )
            .sort(["weight", "skill_id"], descending=[True, False])
        )
        rows = related.to_dicts()
        return RelatedSkillsResponse(
            skill_id=skill_id,
            records=tuple(
                RelatedSkillRecord(
                    skill_id=row["skill_id"],
                    canonical_name=catalog[row["skill_id"]].canonical_name,
                    category=catalog[row["skill_id"]].category,
                    cooccurrence_count=row["cooccurrence_count"],
                    jaccard=row["jaccard"],
                    pmi=row["pmi"],
                    weight=row["weight"],
                )
                for row in rows
                if row["skill_id"] in catalog
            ),
            methodology_version=rows[0]["methodology_version"] if rows else "phase7_advanced_analytics_v1",
            config_version=rows[0]["config_version"] if rows else self._advanced.config.version,
        )

    def roles(self) -> RolesResponse:
        rows = self._query(
            "SELECT role_id, canonical_job_count, company_count, city_count, salary_mid_median "
            "FROM role_summary ORDER BY role_id"
        )
        return RolesResponse(records=tuple(RoleRecord(**row) for row in rows if row["role_id"] is not None))

    def role(self, role_id: str) -> RoleRecord | None:
        return next((record for record in self.roles().records if record.role_id == role_id), None)

    def role_skill_demand(self, role_id: str):
        return self._analytics.skill_demand(AnalyticsFilters(role_id=role_id))

    def sources(self) -> SourcesResponse:
        rows = self._query(
            "SELECT source_id, source_job_count, canonical_job_count, "
            "CAST(first_observed_at AS VARCHAR) AS first_observed_at, "
            "CAST(last_observed_at AS VARCHAR) AS last_observed_at "
            "FROM source_summary ORDER BY source_id"
        )
        eligibility = {
            item.source_id: item
            for item in self._analytics.platform_balanced_demand(
                AnalyticsFilters(source_scope="all")
            ).source_eligibility
        }
        records = []
        for row in rows:
            configured = next(
                (item for item in self._source_registry.sources if item.source_id == row["source_id"]),
                None,
            )
            evidence = eligibility.get(str(row["source_id"]))
            records.append(
                SourceRecord(
                    **row,
                    source_name=configured.source_name if configured else None,
                    dataset_version=configured.dataset_version if configured else None,
                    dataset_url=configured.dataset_url if configured else None,
                    license_name=configured.license_name if configured else None,
                    license_url=configured.license_url if configured else None,
                    data_usage_status=configured.data_usage_status if configured else None,
                    analysis_role=configured.analysis_role if configured else "core_market",
                    core_market_eligible=evidence.eligible if evidence else False,
                    ineligibility_reasons=evidence.reasons if evidence else ("SOURCE_ELIGIBILITY_NOT_EVALUATED",),
                    target_sample_size=evidence.target_sample_size if evidence else 0,
                )
            )
        return SourcesResponse(records=tuple(records))

    def data_quality(self) -> DataQualityResponse:
        if not self.settings.quality_report_path.is_file():
            raise FileNotFoundError(f"Data-quality report does not exist: {self.settings.quality_report_path}")
        payload = json.loads(self.settings.quality_report_path.read_text(encoding="utf-8"))
        latest_observed = self._query("SELECT CAST(max(last_observed_at) AS VARCHAR) AS value FROM source_summary")[0]["value"]
        freshness = self._query(
            "SELECT max(published_at) AS latest_posted_at, "
            "median(date_diff('day', published_at, current_date)) FILTER (WHERE published_at IS NOT NULL) AS median_age, "
            "quantile_cont(date_diff('day', published_at, current_date), 0.75) FILTER (WHERE published_at IS NOT NULL) AS p75_age, "
            "count(published_at)::DOUBLE / nullif(count(*), 0) AS coverage FROM jobs"
        )[0]
        observed_date = (
            latest_observed.date()
            if isinstance(latest_observed, datetime)
            else date.fromisoformat(str(latest_observed)[:10]) if latest_observed else None
        )
        payload["pipeline_freshness"] = {
            "latest_observed_at": observed_date,
            "pipeline_age_days": max(0, (date.today() - observed_date).days) if observed_date else None,
        }
        payload["market_freshness"] = {
            "latest_posted_at": freshness["latest_posted_at"],
            "median_posting_age_days": max(0, freshness["median_age"]) if freshness["median_age"] is not None else None,
            "p75_posting_age_days": max(0, freshness["p75_age"]) if freshness["p75_age"] is not None else None,
            "posting_date_coverage": freshness["coverage"] or 0,
        }
        payload["source_roles"] = {record.source_id: record.analysis_role for record in self.sources().records}
        return DataQualityResponse.model_validate(payload)

    def analyze_portfolio(self, request: OpportunityRequest):
        return self._opportunity.analyze(request, as_of_date=date.today())

    def optimize_portfolio(self, request: LearningOptimizerRequest):
        return self._optimizer.optimize(request, as_of_date=date.today())

    def _query(
        self, sql: str, parameters: list[object] | None = None
    ) -> list[dict[str, object]]:
        connection = duckdb.connect(str(self.settings.warehouse_path), read_only=True)
        try:
            cursor = connection.execute(sql, parameters or [])
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        finally:
            connection.close()

    def _core_filters(self, filters: AnalyticsFilters) -> AnalyticsFilters:
        if filters.source_scope == "all" or filters.source_ids or not self._core_source_ids:
            return filters
        return filters.model_copy(update={"source_ids": self._core_source_ids})


def _find_skill(records: tuple[T, ...], skill_id: str) -> T | None:
    return next((record for record in records if getattr(record, "skill_id") == skill_id), None)


def _demand_sort_key(record: SkillDemandRecord) -> tuple[float, str]:
    return (-(record.job_coverage or 0), record.skill_id)


def _balanced_sort_key(record) -> tuple[float, str]:
    return (-(record.platform_balanced_coverage or 0), record.skill_id)
