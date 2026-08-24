from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import median

import polars as pl
import yaml
from pydantic import BaseModel, ConfigDict, Field


class TitleClassification(BaseModel):
    model_config = ConfigDict(frozen=True)

    classification: str
    matched_pattern: str | None = None


class TargetMarketConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    cause_evidence_min_coverage: float = Field(ge=0.0, le=1.0)
    target_title_patterns: tuple[str, ...]
    possible_title_patterns: tuple[str, ...]
    non_target_title_patterns: tuple[str, ...]
    industry_clue_patterns: dict[str, str]
    technical_description_patterns: tuple[str, ...]
    boilerplate_phrases: tuple[str, ...]

    def classify_title(self, title: str | None) -> TitleClassification:
        value = title or ""
        for pattern in self.target_title_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return TitleClassification(classification="target", matched_pattern=pattern)
        for pattern in self.non_target_title_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return TitleClassification(classification="non_target", matched_pattern=pattern)
        for pattern in self.possible_title_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return TitleClassification(classification="possible", matched_pattern=pattern)
        return TitleClassification(classification="possible")


class CauseEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    explicit_non_target_coverage: float = Field(ge=0.0, le=1.0)
    explicit_target_current_other_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    source_mismatch_detected: bool
    taxonomy_recall_gap_detected: bool


class DistributionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str
    count: int = Field(ge=0)


class SourceCompositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_job_count: int = Field(ge=0)
    canonical_job_count: int = Field(ge=0)


class TargetMarketCoverageReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    methodology_version: str
    canonical_job_count: int = Field(ge=0)
    classification_counts: dict[str, int]
    classification_coverage: dict[str, float]
    current_other_count: int = Field(ge=0)
    explicit_target_current_other_count: int = Field(ge=0)
    extracted_skill_job_count: int = Field(ge=0)
    extracted_skill_coverage: float = Field(ge=0.0, le=1.0)
    technical_description_keyword_count: int = Field(ge=0)
    technical_description_keyword_coverage: float = Field(ge=0.0, le=1.0)
    industry_clue_counts: dict[str, int]
    title_distribution: tuple[DistributionRecord, ...]
    company_distribution: tuple[DistributionRecord, ...]
    source_composition: tuple[SourceCompositionRecord, ...]
    description_nonempty_count: int = Field(ge=0)
    description_median_characters: float = Field(ge=0.0)
    description_english_dominant_count: int = Field(ge=0)
    boilerplate_phrase_counts: dict[str, int]
    other_primary_cause: str
    other_primary_cause_evidence: CauseEvidence
    limitations: tuple[str, ...]

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_target_market_config(path: Path) -> TargetMarketConfig:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("target_market"), dict):
        raise ValueError(f"Target market configuration is missing: {path}")
    return TargetMarketConfig.model_validate(payload["target_market"])


def _distribution(frame: pl.DataFrame, column: str, limit: int = 30) -> tuple[DistributionRecord, ...]:
    rows = (
        frame.filter(pl.col(column).is_not_null())
        .group_by(column)
        .len()
        .sort(["len", column], descending=[True, False])
        .head(limit)
        .to_dicts()
    )
    return tuple(DistributionRecord(value=str(row[column]), count=int(row["len"])) for row in rows)


def build_target_market_report(
    *,
    silver_path: Path,
    canonical_path: Path,
    source_map_path: Path,
    job_skills_path: Path,
    config: TargetMarketConfig,
) -> TargetMarketCoverageReport:
    silver = pl.read_parquet(silver_path)
    canonical = pl.read_parquet(canonical_path)
    source_map = pl.read_parquet(source_map_path)
    job_skills = pl.read_parquet(job_skills_path)
    representatives = canonical.select("canonical_job_id", "canonical_silver_job_id").join(
        silver,
        left_on="canonical_silver_job_id",
        right_on="silver_job_id",
        how="left",
    )
    rows = representatives.to_dicts()
    classifications = [config.classify_title(row.get("job_title_raw")) for row in rows]
    counts = {
        label: sum(item.classification == label for item in classifications)
        for label in ("target", "possible", "non_target")
    }
    total = len(rows)
    target_indices = [index for index, item in enumerate(classifications) if item.classification == "target"]
    target_other = sum(str(rows[index].get("role_id") or "") == "other" for index in target_indices)
    current_other = sum(str(row.get("role_id") or "") == "other" for row in rows)
    non_target_coverage = counts["non_target"] / total if total else 0.0
    target_other_rate = target_other / len(target_indices) if target_indices else None
    source_mismatch = non_target_coverage >= config.cause_evidence_min_coverage
    taxonomy_gap = target_other_rate is not None and target_other_rate >= config.cause_evidence_min_coverage
    if source_mismatch and taxonomy_gap:
        cause = "C_both_source_composition_and_taxonomy_recall"
    elif source_mismatch:
        cause = "A_source_outside_target_market"
    elif taxonomy_gap:
        cause = "B_role_taxonomy_recall_too_low"
    else:
        cause = "INSUFFICIENT_EVIDENCE"

    technical_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in config.technical_description_patterns]
    technical_description_count = sum(
        any(pattern.search(str(row.get("job_description_raw") or "")) for pattern in technical_patterns)
        for row in rows
    )
    industry_counts = {
        name: sum(
            bool(re.search(pattern, f"{row.get('job_title_raw') or ''} {row.get('job_description_raw') or ''}", re.IGNORECASE))
            for row in rows
        )
        for name, pattern in config.industry_clue_patterns.items()
    }
    descriptions = [str(row.get("job_description_raw") or "").strip() for row in rows]
    description_lengths = [len(re.sub(r"\s+", " ", value)) for value in descriptions]
    english_dominant = sum(
        bool(value) and len(re.findall(r"[A-Za-z]", value)) / len(value) >= 0.5
        for value in descriptions
    )
    boilerplate_counts = {
        phrase: sum(phrase in value for value in descriptions)
        for phrase in config.boilerplate_phrases
    }
    skill_canonical_ids = (
        source_map.select("canonical_job_id", "silver_job_id")
        .join(job_skills.select("silver_job_id").unique(), on="silver_job_id", how="inner")
        .select("canonical_job_id")
        .unique()
    )
    source_rows = (
        source_map.group_by("source_id")
        .agg(
            pl.col("silver_job_id").n_unique().alias("source_job_count"),
            pl.col("canonical_job_id").n_unique().alias("canonical_job_count"),
        )
        .sort("source_job_count", descending=True)
        .to_dicts()
    )
    source_count = len(source_rows)
    limitations = [
        "Rule-based market-scope classification is an audit aid, not a Gold role label.",
        "Description keyword coverage can be inflated by employer boilerplate.",
    ]
    if source_count < 2:
        limitations.append("Fewer than two sources cannot support cross-source validation.")
    else:
        limitations.append("Multiple sources do not by themselves establish national market representativeness.")
    return TargetMarketCoverageReport(
        methodology_version=f"target_market_coverage_{config.version}",
        canonical_job_count=total,
        classification_counts=counts,
        classification_coverage={key: value / total if total else 0.0 for key, value in counts.items()},
        current_other_count=current_other,
        explicit_target_current_other_count=target_other,
        extracted_skill_job_count=skill_canonical_ids.height,
        extracted_skill_coverage=skill_canonical_ids.height / total if total else 0.0,
        technical_description_keyword_count=technical_description_count,
        technical_description_keyword_coverage=technical_description_count / total if total else 0.0,
        industry_clue_counts=industry_counts,
        title_distribution=_distribution(representatives, "job_title_normalized"),
        company_distribution=_distribution(representatives, "company_name_normalized"),
        source_composition=tuple(SourceCompositionRecord.model_validate(row) for row in source_rows),
        description_nonempty_count=sum(bool(value) for value in descriptions),
        description_median_characters=float(median(description_lengths)) if description_lengths else 0.0,
        description_english_dominant_count=english_dominant,
        boilerplate_phrase_counts=boilerplate_counts,
        other_primary_cause=cause,
        other_primary_cause_evidence=CauseEvidence(
            explicit_non_target_coverage=non_target_coverage,
            explicit_target_current_other_rate=target_other_rate,
            source_mismatch_detected=source_mismatch,
            taxonomy_recall_gap_detected=taxonomy_gap,
        ),
        limitations=tuple(limitations),
    )
