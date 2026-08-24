from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
import json
from math import log1p
from pathlib import Path
from statistics import median
from typing import Any, Literal

import duckdb
import polars as pl
from pydantic import BaseModel, ConfigDict, Field, model_validator
import yaml

from .confidence import ConfidenceEvidence, DataConfidenceEngine
from .confidence_config import DataConfidenceConfig
from .decision import ScoreComponent


METHODOLOGY_VERSION = "china-open-sample-skillworth-v1"
DISCLAIMER = "该样本来源于 Freehire 当前可观察的中国技术岗位，不代表完整中国招聘市场。"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class MarketSignalWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    demand_strength: float = Field(ge=0, le=1)
    company_breadth: float = Field(ge=0, le=1)
    role_breadth: float = Field(ge=0, le=1)
    skill_synergy: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "MarketSignalWeights":
        if abs(sum(self.model_dump().values()) - 1) > 1e-9:
            raise ValueError("China Market Signal weights must sum to 1")
        return self


class RoleBreadthConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_role_support: int = Field(ge=1)
    target_recognized_skill_jobs: int = Field(ge=1)
    excluded_roles: tuple[str, ...] = ("other",)


class SynergyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    centrality_weight: float = Field(ge=0, le=1)
    edge_support_weight: float = Field(ge=0, le=1)
    jaccard_weight: float = Field(ge=0, le=1)
    positive_pmi_weight: float = Field(ge=0, le=1)
    positive_pmi_reference: float = Field(gt=0)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "SynergyConfig":
        values = (
            self.centrality_weight,
            self.edge_support_weight,
            self.jaccard_weight,
            self.positive_pmi_weight,
        )
        if abs(sum(values) - 1) > 1e-9:
            raise ValueError("Skill synergy weights must sum to 1")
        return self


class LearningEfficiencyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    half_value_hours: float = Field(gt=0)


class ChinaSensitivityConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    market_signal_weight_scenarios: dict[str, MarketSignalWeights]
    learning_half_value_scenarios: tuple[float, ...]
    sensitive_rank_range: int = Field(ge=1)


class RobustnessWeights(BaseModel):
    model_config = ConfigDict(frozen=True)

    sensitivity_rank_width: float = Field(ge=0, le=1, default=0.30)
    sample_size: float = Field(ge=0, le=1, default=0.20)
    company_breadth: float = Field(ge=0, le=1, default=0.15)
    role_breadth: float = Field(ge=0, le=1, default=0.10)
    confidence: float = Field(ge=0, le=1, default=0.15)
    learning_hours_uncertainty: float = Field(ge=0, le=1, default=0.10)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> "RobustnessWeights":
        if abs(sum(self.model_dump().values()) - 1) > 1e-9:
            raise ValueError("ranking robustness weights must sum to 1")
        return self


class RankingRobustnessConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    weights: RobustnessWeights = Field(default_factory=RobustnessWeights)
    rank_width_reference: int = Field(default=30, ge=1)
    job_support_reference: int = Field(default=30, ge=1)
    company_support_reference: int = Field(default=20, ge=1)
    role_breadth_reference: int = Field(default=4, ge=1)
    learning_uncertainty_reference_ratio: float = Field(default=2.0, gt=0)
    robust_threshold: float = Field(default=70, ge=0, le=100)
    moderate_threshold: float = Field(default=50, ge=0, le=100)

    @model_validator(mode="after")
    def thresholds_are_ordered(self) -> "RankingRobustnessConfig":
        if self.moderate_threshold > self.robust_threshold:
            raise ValueError("moderate robustness threshold cannot exceed robust threshold")
        return self


class HighCandidateGateConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_job_support: int = Field(default=10, ge=1)
    minimum_company_support: int = Field(default=8, ge=1)
    minimum_confidence: float = Field(default=30, ge=0, le=100)
    accepted_robustness_levels: tuple[Literal["robust", "moderate", "sensitive"], ...] = (
        "robust",
        "moderate",
    )


class RecencyWindowConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    days: int | None = Field(default=None, ge=1)
    minimum_jobs: int = Field(default=100, ge=1)


class ChinaSkillWorthConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    market_signal_weights: MarketSignalWeights
    role_breadth: RoleBreadthConfig
    synergy: SynergyConfig
    learning_efficiency: LearningEfficiencyConfig
    sensitivity: ChinaSensitivityConfig
    robustness: RankingRobustnessConfig = Field(default_factory=RankingRobustnessConfig)
    candidate_gate: HighCandidateGateConfig = Field(default_factory=HighCandidateGateConfig)
    recency_windows: dict[str, RecencyWindowConfig] = Field(
        default_factory=lambda: {
            "90d": RecencyWindowConfig(days=90),
            "180d": RecencyWindowConfig(days=180),
            "365d": RecencyWindowConfig(days=365),
            "all_active": RecencyWindowConfig(days=None),
        }
    )
    market_themes: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    homepage_minimum_all_active_share: float = Field(default=0.8, gt=0, le=1)


def load_china_skillworth_config(path: Path) -> ChinaSkillWorthConfig:
    if not path.is_file():
        raise FileNotFoundError(f"China SkillWorth config does not exist: {path}")
    return ChinaSkillWorthConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


class MarketSignalInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    demand_strength: float = Field(ge=0, le=1)
    company_breadth: float = Field(ge=0, le=1)
    role_breadth: float = Field(ge=0, le=1)
    skill_synergy: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=100)
    learning_hours_expected: float = Field(gt=0)


class RankingRobustnessInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    rank_min: int = Field(ge=1)
    rank_max: int = Field(ge=1)
    job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    role_count: int = Field(ge=0)
    confidence: float = Field(ge=0, le=100)
    learning_hours_min: float = Field(gt=0)
    learning_hours_expected: float = Field(gt=0)
    learning_hours_max: float = Field(gt=0)


class RankingRobustnessResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0, le=100)
    level: Literal["robust", "moderate", "sensitive"]
    components: dict[str, float]


def calculate_ranking_robustness(
    evidence: RankingRobustnessInput,
    config: RankingRobustnessConfig,
) -> RankingRobustnessResult:
    rank_width = evidence.rank_max - evidence.rank_min
    uncertainty_ratio = (
        (evidence.learning_hours_max - evidence.learning_hours_min)
        / evidence.learning_hours_expected
    )
    components = {
        "sensitivity_rank_width": max(0.0, 1 - rank_width / config.rank_width_reference),
        "sample_size": min(1.0, evidence.job_count / config.job_support_reference),
        "company_breadth": min(1.0, evidence.company_count / config.company_support_reference),
        "role_breadth": min(1.0, evidence.role_count / config.role_breadth_reference),
        "confidence": evidence.confidence / 100,
        "learning_hours_uncertainty": max(
            0.0,
            1 - uncertainty_ratio / config.learning_uncertainty_reference_ratio,
        ),
    }
    weights = config.weights.model_dump()
    score = round(sum(components[name] * weights[name] for name in components) * 100, 2)
    level: Literal["robust", "moderate", "sensitive"]
    if score >= config.robust_threshold:
        level = "robust"
    elif score >= config.moderate_threshold:
        level = "moderate"
    else:
        level = "sensitive"
    return RankingRobustnessResult(
        score=score,
        level=level,
        components={name: round(value * 100, 2) for name, value in components.items()},
    )


def is_high_skillworth_candidate(
    *,
    eligibility: str,
    job_count: int,
    company_count: int,
    confidence: float,
    robustness_level: str,
    config: HighCandidateGateConfig,
) -> bool:
    return (
        eligibility == "main"
        and job_count >= config.minimum_job_support
        and company_count >= config.minimum_company_support
        and confidence >= config.minimum_confidence
        and robustness_level in config.accepted_robustness_levels
    )


class ChinaSkillWorthScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    market_signal: float = Field(ge=0, le=100)
    skillworth_score: float = Field(ge=0, le=100)
    learning_efficiency: float = Field(gt=0, le=1)
    components: dict[str, ScoreComponent]
    salary_signal: float | None = None
    salary_signal_status: str = "unavailable"
    trend_signal: float | None = None
    trend_signal_status: str = "unavailable"
    methodology_version: str = METHODOLOGY_VERSION
    config_version: str


class ChinaSkillWorthEngine:
    def __init__(self, config: ChinaSkillWorthConfig) -> None:
        self.config = config

    def score(
        self,
        evidence: MarketSignalInput,
        *,
        weights: MarketSignalWeights | None = None,
        half_value_hours: float | None = None,
    ) -> ChinaSkillWorthScore:
        weights = weights or self.config.market_signal_weights
        half_value = half_value_hours or self.config.learning_efficiency.half_value_hours
        raw = {
            "demand_strength": evidence.demand_strength,
            "company_breadth": evidence.company_breadth,
            "role_breadth": evidence.role_breadth,
            "skill_synergy": evidence.skill_synergy,
            "confidence": evidence.confidence,
        }
        normalized = {
            name: value if name == "confidence" else value * 100
            for name, value in raw.items()
        }
        weight_values = weights.model_dump()
        explanations = {
            "demand_strength": "技能岗位数 / Snapshot canonical jobs。",
            "company_breadth": "要求该技能的公司数 / Snapshot 公司总数。",
            "role_breadth": "有效角色数、角色分布集中度和角色样本支持共同得到。",
            "skill_synergy": "现有共现网络的 centrality、support、Jaccard 与正 PMI。",
            "confidence": "现有 Data Confidence Engine 结果。",
        }
        components: dict[str, ScoreComponent] = {}
        market_signal = 0.0
        for name, normalized_score in normalized.items():
            contribution = normalized_score * weight_values[name]
            market_signal += contribution
            components[name] = ScoreComponent(
                raw_value=raw[name],
                normalized_score=round(normalized_score, 6),
                configured_weight=weight_values[name],
                effective_weight=weight_values[name],
                contribution=round(contribution, 6),
                available=True,
                explanation=explanations[name],
            )
        learning_efficiency = half_value / (half_value + evidence.learning_hours_expected)
        return ChinaSkillWorthScore(
            skill_id=evidence.skill_id,
            market_signal=round(market_signal, 2),
            skillworth_score=round(market_signal * learning_efficiency, 2),
            learning_efficiency=round(learning_efficiency, 6),
            components=components,
            config_version=self.config.version,
        )


class ChinaSkillWorthRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    skill: str
    skill_category: str
    job_count: int = Field(ge=0)
    job_coverage: float = Field(ge=0, le=1)
    company_count: int = Field(ge=0)
    company_coverage: float = Field(ge=0, le=1)
    role_count: int = Field(ge=0)
    role_breadth_score: float = Field(ge=0, le=1)
    network_centrality: float = Field(ge=0, le=1)
    synergy_score: float = Field(ge=0, le=1)
    market_signal: float = Field(ge=0, le=100)
    market_signal_components: dict[str, ScoreComponent]
    learning_hours_min: float = Field(gt=0)
    learning_hours_expected: float = Field(gt=0)
    learning_hours_max: float = Field(gt=0)
    learning_efficiency: float = Field(gt=0, le=1)
    skillworth_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=100)
    confidence_level: str
    confidence_components: dict[str, Any]
    source_count: int = Field(ge=0)
    sample_size: int = Field(ge=0)
    salary_signal: float | None = None
    salary_signal_status: str = "unavailable"
    trend_signal: float | None = None
    trend_signal_status: str = "unavailable"
    snapshot_id: str
    rank_stability: float = Field(ge=0, le=1)
    rank_min: int = Field(ge=1)
    rank_max: int = Field(ge=1)
    sensitive_ranking_warning: str | None = None
    warnings: tuple[str, ...]


class ChinaSkillWorthBuildReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    market_scope: str = "china_open_tech_sample"
    source_role: str = "china_supplementary"
    job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)
    salary_signal_status: str = "unavailable"
    trend_signal_status: str = "unavailable"
    disclaimer: str = DISCLAIMER
    methodology_version: str = METHODOLOGY_VERSION
    config_version: str
    records: tuple[ChinaSkillWorthRecord, ...]


class RecencyWindowSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    recency_window: str
    job_count: int = Field(ge=0)
    company_count: int = Field(ge=0)
    skill_count: int = Field(ge=0)
    status: Literal["available", "insufficient"]


class ChinaSkillWorthVisualRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str
    skill: str
    skill_type: str
    skill_category: str
    skillworth_eligibility: Literal["main", "secondary", "excluded"]
    eligibility_reason: str
    job_count: int = Field(ge=0)
    job_coverage: float = Field(ge=0, le=1)
    sample_size: int = Field(ge=0)
    company_count: int = Field(ge=0)
    company_coverage: float = Field(ge=0, le=1)
    company_sample_size: int = Field(ge=0)
    role_count: int = Field(ge=0)
    role_breadth: float = Field(ge=0, le=1)
    synergy_score: float = Field(ge=0, le=1)
    market_signal: float = Field(ge=0, le=100)
    learning_hours_min: float = Field(gt=0)
    learning_hours_expected: float = Field(gt=0)
    learning_hours_max: float = Field(gt=0)
    skillworth_score: float = Field(ge=0, le=100)
    skillworth_rank: int | None = Field(default=None, ge=1)
    demand_rank: int | None = Field(default=None, ge=1)
    sensitivity_rank_min: int = Field(ge=1)
    sensitivity_rank_max: int = Field(ge=1)
    ranking_robustness: float = Field(ge=0, le=100)
    robustness_level: Literal["robust", "moderate", "sensitive"]
    confidence: float = Field(ge=0, le=100)
    confidence_level: str
    high_skillworth_candidate: bool
    market_theme: str | None = None
    snapshot_id: str
    recency_window: str
    role_id: str | None = None
    window_status: Literal["available", "insufficient"]
    salary_signal_status: Literal["unavailable"] = "unavailable"
    trend_signal_status: Literal["unavailable"] = "unavailable"


class ChinaSkillWorthVisualBuildReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    record_count: int = Field(ge=0)
    windows: tuple[RecencyWindowSummary, ...]
    records: tuple[ChinaSkillWorthVisualRecord, ...]


def calculate_demand_ranks(
    records: list[tuple[str, int, str]],
) -> dict[str, int]:
    """Rank main skills by existing canonical job demand with a stable tie-break."""
    ordered = sorted(
        (
            (skill_id, job_count)
            for skill_id, job_count, eligibility in records
            if eligibility == "main"
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return {skill_id: rank for rank, (skill_id, _) in enumerate(ordered, start=1)}


def build_china_skillworth_visual_ready(
    *,
    database_path: Path,
    snapshot_id: str,
    snapshot_completed_at: datetime,
    config: ChinaSkillWorthConfig,
    confidence_config: DataConfidenceConfig,
) -> ChinaSkillWorthVisualBuildReport:
    """Build semantic, recency-aware ranking slices without inventing salary or trend signals."""
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        jobs = _rows(
            connection,
            "SELECT canonical_job_id, company_id, role_id, published_at FROM jobs",
        )
        skills = _rows(
            connection,
            "SELECT skill_id, canonical_name, category, skill_type, "
            "skillworth_eligibility, skillworth_reason, learning_hours_min, "
            "learning_hours_expected, learning_hours_max FROM skills",
        )
        relations = _rows(
            connection,
            "SELECT DISTINCT canonical_job_id, skill_id FROM job_skills",
        )
        sources = _rows(
            connection,
            "SELECT canonical_job_id, source_id, upstream_source, observed_at, api_accessed_at "
            "FROM job_source_map",
        )
        base_rows = _rows(
            connection,
            "SELECT skill_id, network_centrality, synergy_score FROM china_skillworth_summary",
        )
    finally:
        connection.close()
    if not jobs:
        raise ValueError("visual-ready SkillWorth dataset requires canonical jobs")

    skill_metadata = {str(row["skill_id"]): row for row in skills}
    _validate_market_themes(config.market_themes, skill_metadata)
    base_by_skill = {str(row["skill_id"]): row for row in base_rows}
    all_job_by_id = {str(row["canonical_job_id"]): row for row in jobs}
    skill_jobs: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        job_id = str(relation["canonical_job_id"])
        if job_id in all_job_by_id:
            skill_jobs[str(relation["skill_id"])].add(job_id)
    source_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sources:
        source_by_job[str(row["canonical_job_id"])].append(row)

    as_of_date = snapshot_completed_at.date()
    role_ids = sorted(
        {str(row["role_id"]) for row in jobs if row.get("role_id")}
    )
    engine = ChinaSkillWorthEngine(config)
    confidence_engine = DataConfidenceEngine(confidence_config)
    records: list[ChinaSkillWorthVisualRecord] = []
    theme_rows: list[dict[str, Any]] = []
    windows: list[RecencyWindowSummary] = []
    for window_name, window_config in config.recency_windows.items():
        cutoff = (
            as_of_date.fromordinal(as_of_date.toordinal() - window_config.days)
            if window_config.days is not None
            else None
        )
        window_jobs = {
            job_id: row
            for job_id, row in all_job_by_id.items()
            if cutoff is None
            or (
                (posted := _date_value(row.get("published_at"))) is not None
                and posted >= cutoff
            )
        }
        window_status: Literal["available", "insufficient"] = (
            "available"
            if len(window_jobs) >= window_config.minimum_jobs
            else "insufficient"
        )
        window_skill_count = sum(
            bool(job_ids & window_jobs.keys()) for job_ids in skill_jobs.values()
        )
        windows.append(
            RecencyWindowSummary(
                recency_window=window_name,
                job_count=len(window_jobs),
                company_count=len(
                    {str(row["company_id"]) for row in window_jobs.values() if row.get("company_id")}
                ),
                skill_count=window_skill_count,
                status=window_status,
            )
        )
        theme_rows.extend(
            _market_theme_rows(
                jobs=window_jobs,
                skill_jobs=skill_jobs,
                themes=config.market_themes,
                snapshot_id=snapshot_id,
                recency_window=window_name,
            )
        )
        for role_id in (None, *role_ids):
            scoped_jobs = {
                job_id: row
                for job_id, row in window_jobs.items()
                if role_id is None or str(row.get("role_id")) == role_id
            }
            if not scoped_jobs:
                continue
            records.extend(
                _visual_records_for_scope(
                    jobs=scoped_jobs,
                    skill_jobs=skill_jobs,
                    skill_metadata=skill_metadata,
                    base_by_skill=base_by_skill,
                    source_by_job=source_by_job,
                    snapshot_id=snapshot_id,
                    recency_window=window_name,
                    role_id=role_id,
                    window_status=window_status,
                    as_of_date=as_of_date,
                    engine=engine,
                    confidence_engine=confidence_engine,
                    config=config,
                )
            )
    _write_visual_ready_table(database_path, records)
    _write_market_theme_table(database_path, theme_rows)
    return ChinaSkillWorthVisualBuildReport(
        snapshot_id=snapshot_id,
        record_count=len(records),
        windows=tuple(windows),
        records=tuple(records),
    )


def write_skillworth_visual_reports(
    *,
    database_path: Path,
    report: ChinaSkillWorthVisualBuildReport,
    config: ChinaSkillWorthConfig,
    audit_output_path: Path,
    findings_output_path: Path,
) -> None:
    global_records = [
        row
        for row in report.records
        if row.recency_window == "all_active" and row.role_id is None
    ]
    connection = duckdb.connect(str(database_path), read_only=True)
    try:
        current_rows = _rows(
            connection,
            "SELECT skill_id, row_number() OVER (ORDER BY skillworth_score DESC, skill_id) "
            "AS current_rank FROM china_skillworth_summary",
        )
        themes = _rows(
            connection,
            "SELECT * FROM china_skillworth_market_themes "
            "WHERE recency_window = 'all_active' ORDER BY job_coverage DESC, market_theme",
        )
    finally:
        connection.close()
    current_rank = {str(row["skill_id"]): int(row["current_rank"]) for row in current_rows}
    audit_rows = [
        {
            "skill": row.skill,
            "current_category": row.skill_category,
            "skill_type": row.skill_type,
            "skillworth_eligibility": row.skillworth_eligibility,
            "reason": row.eligibility_reason,
            "job_count": row.job_count,
            "company_count": row.company_count,
            "role_count": row.role_count,
            "market_signal": row.market_signal,
            "learning_hours_expected": row.learning_hours_expected,
            "current_skillworth_rank": current_rank[row.skill_id],
            "confidence": row.confidence,
            "sensitivity_rank_min": row.sensitivity_rank_min,
            "sensitivity_rank_max": row.sensitivity_rank_max,
        }
        for row in sorted(global_records, key=lambda item: current_rank[item.skill_id])
    ]
    audit_output_path.parent.mkdir(parents=True, exist_ok=True)
    pl.from_dicts(audit_rows, infer_schema_length=None).write_csv(audit_output_path)

    eligibility_counts = Counter(row.skillworth_eligibility for row in global_records)
    robustness_counts = Counter(row.robustness_level for row in global_records)
    candidates = sorted(
        (row for row in global_records if row.high_skillworth_candidate),
        key=lambda row: (row.skillworth_rank or 10**9, row.skill_id),
    )
    robust_candidates = [row for row in candidates if row.robustness_level == "robust"]
    excluded = sorted(
        (row for row in global_records if row.skillworth_eligibility == "excluded"),
        key=lambda row: (-row.job_count, row.skill_id),
    )
    main = [row for row in global_records if row.skillworth_eligibility == "main"]
    market_values = sorted(row.market_signal for row in main)
    hour_values = sorted(row.learning_hours_expected for row in main)
    market_p75 = _quantile([int(value * 100) for value in market_values], 0.75) / 100 if market_values else 0
    market_median = median(market_values) if market_values else 0
    hours_p25 = _quantile([int(value) for value in hour_values], 0.25) or 0
    hours_p75 = _quantile([int(value) for value in hour_values], 0.75) or 0
    high_cost_value = sorted(
        (row for row in main if row.market_signal >= market_p75 and row.learning_hours_expected >= hours_p75),
        key=lambda row: (-row.market_signal, row.skill_id),
    )
    low_cost_average = sorted(
        (row for row in main if row.learning_hours_expected <= hours_p25 and row.market_signal <= market_median),
        key=lambda row: (row.learning_hours_expected, -row.market_signal, row.skill_id),
    )
    windows = {window.recency_window: window for window in report.windows}
    all_jobs = windows["all_active"].job_count
    recommended = next(
        (
            name
            for name in ("90d", "180d", "365d")
            if windows.get(name)
            and windows[name].status == "available"
            and windows[name].job_count / all_jobs >= config.homepage_minimum_all_active_share
        ),
        "all_active",
    )
    candidate_lines = ", ".join(
        f"{row.skill}（{row.skillworth_score:.2f}）" for row in robust_candidates
    ) or "无"
    window_candidate_lines = []
    for name in ("90d", "180d", "365d", "all_active"):
        top = sorted(
            (
                row
                for row in report.records
                if row.recency_window == name
                and row.role_id is None
                and row.high_skillworth_candidate
            ),
            key=lambda row: (row.skillworth_rank or 10**9, row.skill_id),
        )[:10]
        window_candidate_lines.append(
            f"- {name}: " + (", ".join(row.skill for row in top) or "无")
        )
    findings = [
        "# SkillWorth Visual-ready Findings",
        "",
        f"Snapshot：`{report.snapshot_id}`。口径：2026-08 当前可观察的开放岗位快照，不代表所有岗位均发布于 2026 年。",
        "",
        "## 1. 从主榜排除的技能",
        "",
        *[f"- {row.skill}：{row.eligibility_reason}（{row.job_count} jobs）" for row in excluded],
        "",
        "## 2. 主榜资格规模",
        "",
        f"main={eligibility_counts['main']}，secondary={eligibility_counts['secondary']}，excluded={eligibility_counts['excluded']}。",
        "",
        "## 3. 排名稳健性",
        "",
        f"robust={robustness_counts['robust']}，moderate={robustness_counts['moderate']}，sensitive={robustness_counts['sensitive']}。Ranking Robustness 不等同于统计置信度。",
        "",
        "## 4. 最稳健的高技值候选",
        "",
        candidate_lines,
        "",
        "## 5. 市场价值高但学习投入高",
        "",
        ", ".join(f"{row.skill}（{row.learning_hours_expected:.0f}h）" for row in high_cost_value[:10]) or "无。",
        "",
        "## 6. 学习成本低但市场价值一般",
        "",
        ", ".join(f"{row.skill}（{row.learning_hours_expected:.0f}h）" for row in low_cost_average[:10]) or "无。",
        "",
        "## 7. Demand 高但不适合主榜",
        "",
        ", ".join(f"{row.skill}（{row.job_count} jobs）" for row in excluded[:10]) or "无。",
        "",
        "## 8. 90 / 180 / 365 day 差异",
        "",
        *[
            f"- {name}: jobs={windows[name].job_count}, companies={windows[name].company_count}, skills={windows[name].skill_count}, status={windows[name].status}"
            for name in ("90d", "180d", "365d", "all_active")
        ],
        "",
        "各窗口 Top 10 high SkillWorth candidates：",
        "",
        *window_candidate_lines,
        "",
        "## 9. 首页默认窗口",
        "",
        f"建议 `{recommended}`。选择规则为最短且 available、同时覆盖至少 {config.homepage_minimum_all_active_share:.0%} all-active 岗位的窗口。",
        "",
        "## 10. 是否适合公开 SkillWorth Matrix",
        "",
        "适合进入受限的真实数据可视化重构，但必须持续显示单来源、Low/Medium Confidence、Salary unavailable 与 Trend unavailable；当前不构成生产级劳动力市场结论。",
        "",
        "## Market Themes",
        "",
        *[
            f"- {row['market_theme']}: jobs={row['job_count']}, coverage={float(row['job_coverage']):.2%}, companies={row['company_count']}, roles={row['role_count']}"
            for row in themes
        ],
    ]
    findings_output_path.parent.mkdir(parents=True, exist_ok=True)
    findings_output_path.write_text("\n".join(findings) + "\n", encoding="utf-8")


def build_china_skillworth_summary(
    *,
    database_path: Path,
    graph_nodes_path: Path,
    graph_edges_path: Path,
    snapshot_id: str,
    snapshot_completed_at: datetime,
    config: ChinaSkillWorthConfig,
    confidence_config: DataConfidenceConfig,
) -> ChinaSkillWorthBuildReport:
    connection = duckdb.connect(str(database_path))
    try:
        jobs = _rows(connection, "SELECT canonical_job_id, company_id, role_id, published_at FROM jobs")
        skills = _rows(
            connection,
            "SELECT skill_id, canonical_name, category, learning_hours_min, "
            "learning_hours_expected, learning_hours_max FROM skills",
        )
        relations = _rows(
            connection,
            "SELECT DISTINCT canonical_job_id, skill_id FROM job_skills",
        )
        source_rows = _rows(
            connection,
            "SELECT canonical_job_id, source_id, upstream_source, observed_at, api_accessed_at "
            "FROM job_source_map",
        )
    finally:
        connection.close()
    if not jobs:
        raise ValueError("China SkillWorth summary requires at least one canonical job")

    job_by_id = {str(row["canonical_job_id"]): row for row in jobs}
    skill_jobs: dict[str, set[str]] = defaultdict(set)
    for relation in relations:
        job_id = str(relation["canonical_job_id"])
        if job_id in job_by_id:
            skill_jobs[str(relation["skill_id"])].add(job_id)
    source_by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        source_by_job[str(row["canonical_job_id"])].append(row)

    nodes = pl.read_parquet(graph_nodes_path).to_dicts()
    edges = pl.read_parquet(graph_edges_path).to_dicts()
    node_by_skill = {str(row["skill_id"]): row for row in nodes}
    max_weighted_degree = max((float(row.get("weighted_degree") or 0) for row in nodes), default=0)
    edge_by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    support_by_skill: Counter[str] = Counter()
    for edge in edges:
        for skill_id in (str(edge["skill_a_id"]), str(edge["skill_b_id"])):
            edge_by_skill[skill_id].append(edge)
            support_by_skill[skill_id] += int(edge.get("cooccurrence_count") or 0)
    max_log_support = max((log1p(value) for value in support_by_skill.values()), default=0)

    total_jobs = len(job_by_id)
    total_companies = len({str(row["company_id"]) for row in jobs if row.get("company_id")})
    excluded_roles = set(config.role_breadth.excluded_roles)
    total_roles = len(
        {
            str(row["role_id"])
            for row in jobs
            if row.get("role_id") and str(row["role_id"]) not in excluded_roles
        }
    )
    engine = ChinaSkillWorthEngine(config)
    confidence_engine = DataConfidenceEngine(confidence_config)
    skill_metadata = {str(row["skill_id"]): row for row in skills}
    evidence_by_skill: dict[str, MarketSignalInput] = {}
    partial: dict[str, dict[str, Any]] = {}
    as_of_date = snapshot_completed_at.date()
    for skill_id, job_ids in sorted(skill_jobs.items()):
        metadata = skill_metadata.get(skill_id)
        if metadata is None or not job_ids:
            continue
        companies = {
            str(job_by_id[job_id]["company_id"])
            for job_id in job_ids
            if job_by_id[job_id].get("company_id")
        }
        role_counts = Counter(
            str(job_by_id[job_id]["role_id"])
            for job_id in job_ids
            if job_by_id[job_id].get("role_id")
            and str(job_by_id[job_id]["role_id"]) not in excluded_roles
        )
        supported_role_counts = {
            role: count
            for role, count in role_counts.items()
            if count >= config.role_breadth.minimum_role_support
        }
        role_breadth = _role_breadth(supported_role_counts, total_roles, config)
        centrality = (
            float(node_by_skill.get(skill_id, {}).get("weighted_degree") or 0)
            / max_weighted_degree
            if max_weighted_degree
            else 0.0
        )
        synergy = _synergy_score(
            skill_id, centrality, edge_by_skill, support_by_skill, max_log_support, config
        )
        source_counts: Counter[str] = Counter()
        observed_dates: list[date] = []
        for job_id in job_ids:
            for source in source_by_job.get(job_id, []):
                source_name = str(source.get("upstream_source") or source.get("source_id") or "")
                if source_name:
                    source_counts[source_name] += 1
                observed = _date_value(source.get("api_accessed_at") or source.get("observed_at"))
                if observed:
                    observed_dates.append(observed)
        posted_dates = [
            value
            for job_id in job_ids
            if (value := _date_value(job_by_id[job_id].get("published_at"))) is not None
        ]
        posting_ages = sorted(max(0, (as_of_date - value).days) for value in posted_dates)
        confidence_result = confidence_engine.evaluate(
            ConfidenceEvidence(
                sample_size=len(job_ids),
                source_sample_sizes=dict(source_counts) or {"freehire": len(job_ids)},
                source_eligibility={source: False for source in source_counts} or {"freehire": False},
                latest_observation_date=max(observed_dates) if observed_dates else as_of_date,
                latest_posted_date=max(posted_dates) if posted_dates else None,
                median_posting_age_days=median(posting_ages) if posting_ages else None,
                p75_posting_age_days=_quantile(posting_ages, 0.75),
                posting_date_coverage=len(posted_dates) / len(job_ids),
                as_of_date=as_of_date,
                metric_eligible_count=len(job_ids),
                platform_metric_values={},
                gold_benchmark_available=False,
            )
        )
        evidence = MarketSignalInput(
            skill_id=skill_id,
            demand_strength=len(job_ids) / total_jobs,
            company_breadth=len(companies) / total_companies if total_companies else 0,
            role_breadth=role_breadth,
            skill_synergy=synergy,
            confidence=confidence_result.confidence_score,
            learning_hours_expected=float(metadata["learning_hours_expected"]),
        )
        evidence_by_skill[skill_id] = evidence
        partial[skill_id] = {
            "metadata": metadata,
            "job_ids": job_ids,
            "companies": companies,
            "role_counts": supported_role_counts,
            "centrality": centrality,
            "synergy": synergy,
            "source_counts": source_counts,
            "confidence": confidence_result,
            "score": engine.score(evidence),
        }

    rank_maps = _sensitivity_ranks(evidence_by_skill, engine, config)
    records: list[ChinaSkillWorthRecord] = []
    skill_count = len(evidence_by_skill)
    for skill_id in sorted(evidence_by_skill):
        item = partial[skill_id]
        confidence_result = item["confidence"]
        ranks = [rank_map[skill_id] for rank_map in rank_maps]
        rank_min, rank_max = min(ranks), max(ranks)
        rank_range = rank_max - rank_min
        rank_stability = 1 if skill_count <= 1 else 1 - rank_range / (skill_count - 1)
        score = item["score"]
        warnings = tuple(
            dict.fromkeys(
                [warning.code for warning in confidence_result.warnings]
                + ["salary_signal_unavailable_insufficient_coverage", "trend_signal_unavailable_single_snapshot"]
            )
        )
        metadata = item["metadata"]
        records.append(
            ChinaSkillWorthRecord(
                skill_id=skill_id,
                skill=str(metadata["canonical_name"]),
                skill_category=str(metadata["category"]),
                job_count=len(item["job_ids"]),
                job_coverage=len(item["job_ids"]) / total_jobs,
                company_count=len(item["companies"]),
                company_coverage=len(item["companies"]) / total_companies if total_companies else 0,
                role_count=len(item["role_counts"]),
                role_breadth_score=round(evidence_by_skill[skill_id].role_breadth, 6),
                network_centrality=round(item["centrality"], 6),
                synergy_score=round(item["synergy"], 6),
                market_signal=score.market_signal,
                market_signal_components=score.components,
                learning_hours_min=float(metadata["learning_hours_min"]),
                learning_hours_expected=evidence_by_skill[skill_id].learning_hours_expected,
                learning_hours_max=float(metadata["learning_hours_max"]),
                learning_efficiency=score.learning_efficiency,
                skillworth_score=score.skillworth_score,
                confidence=confidence_result.confidence_score,
                confidence_level=confidence_result.confidence_level,
                confidence_components={
                    name: component.model_dump(mode="json")
                    for name, component in confidence_result.confidence_components.items()
                },
                source_count=len(item["source_counts"]),
                sample_size=total_jobs,
                snapshot_id=snapshot_id,
                rank_stability=round(rank_stability, 6),
                rank_min=rank_min,
                rank_max=rank_max,
                sensitive_ranking_warning=(
                    "Sensitive Ranking Warning"
                    if rank_range >= config.sensitivity.sensitive_rank_range
                    else None
                ),
                warnings=warnings,
            )
        )
    records.sort(key=lambda record: (-record.skillworth_score, record.skill_id))
    _write_summary_table(database_path, records)
    return ChinaSkillWorthBuildReport(
        snapshot_id=snapshot_id,
        job_count=total_jobs,
        company_count=total_companies,
        source_count=len(
            {
                str(row.get("upstream_source") or row.get("source_id"))
                for row in source_rows
                if row.get("upstream_source") or row.get("source_id")
            }
        ),
        skill_count=len(records),
        config_version=config.version,
        records=tuple(records),
    )


def _role_breadth(
    role_counts: dict[str, int], total_roles: int, config: ChinaSkillWorthConfig
) -> float:
    total_support = sum(role_counts.values())
    if not role_counts or not total_support or not total_roles:
        return 0.0
    effective_roles = 1 / sum((count / total_support) ** 2 for count in role_counts.values())
    diversity = min(1.0, effective_roles / total_roles)
    support = min(1.0, total_support / config.role_breadth.target_recognized_skill_jobs)
    return round(diversity * support, 6)


def _synergy_score(
    skill_id: str,
    centrality: float,
    edge_by_skill: dict[str, list[dict[str, Any]]],
    support_by_skill: Counter[str],
    max_log_support: float,
    config: ChinaSkillWorthConfig,
) -> float:
    edges = edge_by_skill.get(skill_id, [])
    edge_support = (
        log1p(support_by_skill[skill_id]) / max_log_support if max_log_support else 0.0
    )
    total_weight = sum(int(edge.get("cooccurrence_count") or 0) for edge in edges)
    mean_jaccard = (
        sum(float(edge.get("jaccard") or 0) * int(edge.get("cooccurrence_count") or 0) for edge in edges)
        / total_weight
        if total_weight
        else 0.0
    )
    positive_pmi = (
        sum(
            min(1.0, max(0.0, float(edge.get("pmi") or 0) / config.synergy.positive_pmi_reference))
            * int(edge.get("cooccurrence_count") or 0)
            for edge in edges
        )
        / total_weight
        if total_weight
        else 0.0
    )
    result = (
        centrality * config.synergy.centrality_weight
        + edge_support * config.synergy.edge_support_weight
        + mean_jaccard * config.synergy.jaccard_weight
        + positive_pmi * config.synergy.positive_pmi_weight
    )
    return min(1.0, max(0.0, result))


def _sensitivity_ranks(
    evidence: dict[str, MarketSignalInput],
    engine: ChinaSkillWorthEngine,
    config: ChinaSkillWorthConfig,
) -> list[dict[str, int]]:
    scenarios: list[tuple[MarketSignalWeights | None, float | None]] = [(None, None)]
    scenarios.extend((weights, None) for weights in config.sensitivity.market_signal_weight_scenarios.values())
    scenarios.extend((None, half_value) for half_value in config.sensitivity.learning_half_value_scenarios)
    rank_maps = []
    for weights, half_value in scenarios:
        scores = {
            skill_id: engine.score(item, weights=weights, half_value_hours=half_value).skillworth_score
            for skill_id, item in evidence.items()
        }
        ordered = sorted(scores, key=lambda skill_id: (-scores[skill_id], skill_id))
        rank_maps.append({skill_id: rank for rank, skill_id in enumerate(ordered, start=1)})
    return rank_maps


def _write_summary_table(database_path: Path, records: list[ChinaSkillWorthRecord]) -> None:
    if not records:
        raise ValueError("China SkillWorth summary requires at least one extracted skill")
    rows = []
    for record in records:
        payload = record.model_dump(mode="json")
        payload["market_signal_components"] = json.dumps(
            payload["market_signal_components"], ensure_ascii=False
        )
        payload["confidence_components"] = json.dumps(
            payload["confidence_components"], ensure_ascii=False
        )
        payload["warnings"] = json.dumps(payload["warnings"], ensure_ascii=False)
        payload["market_scope"] = "china_open_tech_sample"
        payload["source_role"] = "china_supplementary"
        payload["disclaimer"] = DISCLAIMER
        rows.append(payload)
    frame = pl.from_dicts(rows, infer_schema_length=None)
    connection = duckdb.connect(str(database_path))
    try:
        connection.register("input_china_skillworth_summary", frame)
        sql_path = REPOSITORY_ROOT / "backend/app/sql/04_china_skillworth_summary.sql"
        connection.execute(sql_path.read_text(encoding="utf-8"))
        violations = connection.execute(
            "SELECT count(*) FROM china_skillworth_summary WHERE "
            "salary_signal IS NOT NULL OR trend_signal IS NOT NULL OR "
            "salary_signal_status <> 'unavailable' OR trend_signal_status <> 'unavailable' OR "
            "market_signal NOT BETWEEN 0 AND 100 OR skillworth_score NOT BETWEEN 0 AND 100"
        ).fetchone()[0]
        if violations:
            raise ValueError(f"China SkillWorth table quality checks failed: {violations}")
    finally:
        connection.close()


def _visual_records_for_scope(
    *,
    jobs: dict[str, dict[str, Any]],
    skill_jobs: dict[str, set[str]],
    skill_metadata: dict[str, dict[str, Any]],
    base_by_skill: dict[str, dict[str, Any]],
    source_by_job: dict[str, list[dict[str, Any]]],
    snapshot_id: str,
    recency_window: str,
    role_id: str | None,
    window_status: Literal["available", "insufficient"],
    as_of_date: date,
    engine: ChinaSkillWorthEngine,
    confidence_engine: DataConfidenceEngine,
    config: ChinaSkillWorthConfig,
) -> list[ChinaSkillWorthVisualRecord]:
    total_jobs = len(jobs)
    total_companies = len(
        {str(row["company_id"]) for row in jobs.values() if row.get("company_id")}
    )
    excluded_roles = set(config.role_breadth.excluded_roles)
    total_roles = len(
        {
            str(row["role_id"])
            for row in jobs.values()
            if row.get("role_id") and str(row["role_id"]) not in excluded_roles
        }
    )
    evidence_by_skill: dict[str, MarketSignalInput] = {}
    partial: dict[str, dict[str, Any]] = {}
    job_ids_in_scope = set(jobs)
    for skill_id, all_job_ids in skill_jobs.items():
        matched_jobs = all_job_ids & job_ids_in_scope
        metadata = skill_metadata.get(skill_id)
        if not matched_jobs or metadata is None:
            continue
        companies = {
            str(jobs[job_id]["company_id"])
            for job_id in matched_jobs
            if jobs[job_id].get("company_id")
        }
        role_counts = Counter(
            str(jobs[job_id]["role_id"])
            for job_id in matched_jobs
            if jobs[job_id].get("role_id")
            and str(jobs[job_id]["role_id"]) not in excluded_roles
        )
        supported_roles = {
            key: value
            for key, value in role_counts.items()
            if value >= config.role_breadth.minimum_role_support
        }
        confidence = _scope_confidence(
            matched_jobs,
            jobs,
            source_by_job,
            as_of_date,
            confidence_engine,
        )
        base = base_by_skill.get(skill_id, {})
        evidence = MarketSignalInput(
            skill_id=skill_id,
            demand_strength=len(matched_jobs) / total_jobs,
            company_breadth=len(companies) / total_companies if total_companies else 0,
            role_breadth=_role_breadth(supported_roles, total_roles, config),
            skill_synergy=float(base.get("synergy_score") or 0),
            confidence=confidence.confidence_score,
            learning_hours_expected=float(metadata["learning_hours_expected"]),
        )
        evidence_by_skill[skill_id] = evidence
        partial[skill_id] = {
            "job_ids": matched_jobs,
            "companies": companies,
            "roles": supported_roles,
            "confidence": confidence,
            "metadata": metadata,
            "score": engine.score(evidence),
        }
    if not evidence_by_skill:
        return []
    rank_maps_by_eligibility = {
        eligibility: _sensitivity_ranks(
            {
                skill_id: evidence
                for skill_id, evidence in evidence_by_skill.items()
                if partial[skill_id]["metadata"]["skillworth_eligibility"] == eligibility
            },
            engine,
            config,
        )
        for eligibility in ("main", "secondary", "excluded")
        if any(
            item["metadata"]["skillworth_eligibility"] == eligibility
            for item in partial.values()
        )
    }
    main_order = sorted(
        (
            skill_id
            for skill_id, item in partial.items()
            if item["metadata"]["skillworth_eligibility"] == "main"
        ),
        key=lambda skill_id: (-partial[skill_id]["score"].skillworth_score, skill_id),
    )
    main_ranks = {skill_id: rank for rank, skill_id in enumerate(main_order, start=1)}
    demand_ranks = calculate_demand_ranks([
        (
            skill_id,
            len(item["job_ids"]),
            str(item["metadata"]["skillworth_eligibility"]),
        )
        for skill_id, item in partial.items()
    ])
    output: list[ChinaSkillWorthVisualRecord] = []
    for skill_id, item in partial.items():
        metadata = item["metadata"]
        eligibility = str(metadata["skillworth_eligibility"])
        ranks = [
            rank_map[skill_id]
            for rank_map in rank_maps_by_eligibility[eligibility]
        ]
        rank_min, rank_max = min(ranks), max(ranks)
        robustness = calculate_ranking_robustness(
            RankingRobustnessInput(
                rank_min=rank_min,
                rank_max=rank_max,
                job_count=len(item["job_ids"]),
                company_count=len(item["companies"]),
                role_count=len(item["roles"]),
                confidence=item["confidence"].confidence_score,
                learning_hours_min=float(metadata["learning_hours_min"]),
                learning_hours_expected=float(metadata["learning_hours_expected"]),
                learning_hours_max=float(metadata["learning_hours_max"]),
            ),
            config.robustness,
        )
        score = item["score"]
        output.append(
            ChinaSkillWorthVisualRecord(
                skill_id=skill_id,
                skill=str(metadata["canonical_name"]),
                skill_type=str(metadata["skill_type"]),
                skill_category=str(metadata["category"]),
                skillworth_eligibility=eligibility,
                eligibility_reason=str(metadata["skillworth_reason"]),
                job_count=len(item["job_ids"]),
                job_coverage=len(item["job_ids"]) / total_jobs,
                sample_size=total_jobs,
                company_count=len(item["companies"]),
                company_coverage=(
                    len(item["companies"]) / total_companies if total_companies else 0
                ),
                company_sample_size=total_companies,
                role_count=len(item["roles"]),
                role_breadth=evidence_by_skill[skill_id].role_breadth,
                synergy_score=evidence_by_skill[skill_id].skill_synergy,
                market_signal=score.market_signal,
                learning_hours_min=float(metadata["learning_hours_min"]),
                learning_hours_expected=float(metadata["learning_hours_expected"]),
                learning_hours_max=float(metadata["learning_hours_max"]),
                skillworth_score=score.skillworth_score,
                skillworth_rank=main_ranks.get(skill_id),
                demand_rank=demand_ranks.get(skill_id),
                sensitivity_rank_min=rank_min,
                sensitivity_rank_max=rank_max,
                ranking_robustness=robustness.score,
                robustness_level=robustness.level,
                confidence=item["confidence"].confidence_score,
                confidence_level=item["confidence"].confidence_level,
                high_skillworth_candidate=is_high_skillworth_candidate(
                    eligibility=eligibility,
                    job_count=len(item["job_ids"]),
                    company_count=len(item["companies"]),
                    confidence=item["confidence"].confidence_score,
                    robustness_level=robustness.level,
                    config=config.candidate_gate,
                ),
                market_theme=_market_theme_for_skill(skill_id, config.market_themes),
                snapshot_id=snapshot_id,
                recency_window=recency_window,
                role_id=role_id,
                window_status=window_status,
            )
        )
    return sorted(output, key=lambda row: (-row.skillworth_score, row.skill_id))


def _scope_confidence(
    job_ids: set[str],
    jobs: dict[str, dict[str, Any]],
    source_by_job: dict[str, list[dict[str, Any]]],
    as_of_date: date,
    engine: DataConfidenceEngine,
):
    source_counts: Counter[str] = Counter()
    observed_dates: list[date] = []
    for job_id in job_ids:
        for source in source_by_job.get(job_id, []):
            source_name = str(source.get("upstream_source") or source.get("source_id") or "")
            if source_name:
                source_counts[source_name] += 1
            observed = _date_value(source.get("api_accessed_at") or source.get("observed_at"))
            if observed:
                observed_dates.append(observed)
    posted_dates = [
        value
        for job_id in job_ids
        if (value := _date_value(jobs[job_id].get("published_at"))) is not None
    ]
    ages = sorted(max(0, (as_of_date - value).days) for value in posted_dates)
    return engine.evaluate(
        ConfidenceEvidence(
            sample_size=len(job_ids),
            source_sample_sizes=dict(source_counts) or {"freehire": len(job_ids)},
            source_eligibility={source: False for source in source_counts} or {"freehire": False},
            latest_observation_date=max(observed_dates) if observed_dates else as_of_date,
            latest_posted_date=max(posted_dates) if posted_dates else None,
            median_posting_age_days=median(ages) if ages else None,
            p75_posting_age_days=_quantile(ages, 0.75),
            posting_date_coverage=len(posted_dates) / len(job_ids),
            as_of_date=as_of_date,
            metric_eligible_count=len(job_ids),
            platform_metric_values={},
            gold_benchmark_available=False,
        )
    )


def _validate_market_themes(
    themes: dict[str, tuple[str, ...]],
    skill_metadata: dict[str, dict[str, Any]],
) -> None:
    canonical_names = {str(row["canonical_name"]) for row in skill_metadata.values()}
    unknown_themes = set(themes) - canonical_names
    unknown_skills = {
        skill_id
        for members in themes.values()
        for skill_id in members
        if skill_id not in skill_metadata
    }
    if unknown_themes or unknown_skills:
        raise ValueError(
            f"invalid market theme mapping: unknown_themes={sorted(unknown_themes)}, "
            f"unknown_skills={sorted(unknown_skills)}"
        )


def _market_theme_for_skill(
    skill_id: str,
    themes: dict[str, tuple[str, ...]],
) -> str | None:
    matches = [theme for theme, members in themes.items() if skill_id in members]
    return "; ".join(matches) if matches else None


def _market_theme_rows(
    *,
    jobs: dict[str, dict[str, Any]],
    skill_jobs: dict[str, set[str]],
    themes: dict[str, tuple[str, ...]],
    snapshot_id: str,
    recency_window: str,
) -> list[dict[str, Any]]:
    total_jobs = len(jobs)
    total_companies = len(
        {str(row["company_id"]) for row in jobs.values() if row.get("company_id")}
    )
    scope_ids = set(jobs)
    rows = []
    for theme, members in themes.items():
        theme_jobs = set().union(*(skill_jobs.get(skill_id, set()) for skill_id in members))
        theme_jobs &= scope_ids
        companies = {
            str(jobs[job_id]["company_id"])
            for job_id in theme_jobs
            if jobs[job_id].get("company_id")
        }
        roles = {
            str(jobs[job_id]["role_id"])
            for job_id in theme_jobs
            if jobs[job_id].get("role_id")
        }
        rows.append(
            {
                "market_theme": theme,
                "job_count": len(theme_jobs),
                "job_coverage": len(theme_jobs) / total_jobs if total_jobs else 0,
                "company_count": len(companies),
                "company_coverage": len(companies) / total_companies if total_companies else 0,
                "role_count": len(roles),
                "snapshot_id": snapshot_id,
                "recency_window": recency_window,
            }
        )
    return rows


def _write_visual_ready_table(
    database_path: Path,
    records: list[ChinaSkillWorthVisualRecord],
) -> None:
    if not records:
        raise ValueError("visual-ready SkillWorth dataset requires extracted skills")
    frame = pl.from_dicts(
        [record.model_dump(mode="json") for record in records],
        infer_schema_length=None,
    )
    connection = duckdb.connect(str(database_path))
    try:
        connection.register("input_china_skillworth_visual_ready", frame)
        sql_path = REPOSITORY_ROOT / "backend/app/sql/05_china_skillworth_visual_ready.sql"
        connection.execute(sql_path.read_text(encoding="utf-8"))
        violations = connection.execute(
            "SELECT count(*) FROM china_skillworth_visual_ready WHERE "
            "salary_signal_status <> 'unavailable' OR trend_signal_status <> 'unavailable' "
            "OR skillworth_eligibility NOT IN ('main','secondary','excluded') "
            "OR robustness_level NOT IN ('robust','moderate','sensitive')"
        ).fetchone()[0]
        if violations:
            raise ValueError(f"visual-ready table quality checks failed: {violations}")
    finally:
        connection.close()


def _write_market_theme_table(database_path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    frame = pl.from_dicts(rows, infer_schema_length=None)
    connection = duckdb.connect(str(database_path))
    try:
        connection.register("input_china_skillworth_market_themes", frame)
        connection.execute(
            "CREATE OR REPLACE TABLE china_skillworth_market_themes AS "
            "SELECT * FROM input_china_skillworth_market_themes"
        )
    finally:
        connection.close()


def _rows(connection: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    cursor = connection.execute(sql)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _date_value(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _quantile(values: list[int], probability: float) -> float | None:
    if not values:
        return None
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction
