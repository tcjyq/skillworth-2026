from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import median
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.benchmark_common import load_yaml_mapping


class SalaryMergeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    conflict_relative_spread_threshold: float = Field(ge=0)
    minimum_valid_monthly_salary: float = Field(gt=0)


class CanonicalMergeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    salary: SalaryMergeConfig
    title: dict[str, float]
    description: dict[str, int]


def load_canonical_merge_config(path: Path) -> CanonicalMergeConfig:
    return CanonicalMergeConfig.model_validate(load_yaml_mapping(path))


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _stable_mode(members: list[dict[str, Any]], field: str) -> object | None:
    values = [member.get(field) for member in members if _text(member.get(field))]
    if not values:
        return None
    counts = Counter(str(value) for value in values)
    selected = max(counts, key=lambda value: (counts[value], len(value), value))
    return next(value for value in values if str(value) == selected)


def _title_member(members: list[dict[str, Any]]) -> dict[str, Any]:
    def rank(member: dict[str, Any]) -> tuple[float, int, int, str]:
        confidence = member.get("title_normalization_confidence")
        confidence_value = float(confidence) if isinstance(confidence, (int, float)) else 0.0
        parsed_role = int(member.get("role_parse_status") == "parsed")
        raw_title = _text(member.get("job_title_raw"))
        normalized_title = _text(member.get("job_title_normalized"))
        return confidence_value, parsed_role, len(raw_title or normalized_title), _text(member.get("silver_job_id"))

    return max(members, key=rank)


def _description_member(members: list[dict[str, Any]]) -> dict[str, Any]:
    def rank(member: dict[str, Any]) -> tuple[int, int, str]:
        description = re.sub(r"\s+", " ", _text(member.get("job_description_raw")))
        tokens = set(re.findall(r"[\w+#.-]+", description.casefold()))
        return len(tokens), len(description.replace(" ", "")), _text(member.get("silver_job_id"))

    return max(members, key=rank)


def _iso_value(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError:
            return None


def _date_boundary(
    members: list[dict[str, Any]], field: str, *, earliest: bool, require_reliable: bool = False
) -> str | None:
    candidates: list[str] = []
    for member in members:
        if require_reliable and member.get("date_parse_status") in {"unparseable", "missing_at_source"}:
            continue
        value = _iso_value(member.get(field))
        if value is not None:
            candidates.append(value)
    return (min if earliest else max)(candidates) if candidates else None


def _salary_merge(
    members: list[dict[str, Any]], config: SalaryMergeConfig
) -> dict[str, Any]:
    observations: list[dict[str, Any]] = []
    valid_by_source: dict[str, list[float]] = defaultdict(list)
    valid_months: list[int] = []
    for member in members:
        value = member.get("salary_mid_monthly")
        valid = (
            isinstance(value, (int, float))
            and math.isfinite(float(value))
            and float(value) >= config.minimum_valid_monthly_salary
            and str(member.get("salary_parse_status", "")).startswith("parsed")
        )
        normalized_salary = float(value) if valid else None
        source = _text(member.get("source_id"))
        observations.append(
            {
                "source": source or None,
                "raw_salary": member.get("salary_raw"),
                "normalized_salary": normalized_salary,
                "currency": member.get("salary_currency"),
                "native_min_monthly": member.get("salary_native_min_monthly"),
                "observed_at": _iso_value(member.get("observed_at")),
            }
        )
        if valid and source:
            valid_by_source[source].append(float(value))
            months = member.get("salary_months")
            if isinstance(months, int) and months > 0:
                valid_months.append(months)

    source_values = [median(values) for values in valid_by_source.values()]
    canonical_salary: float | None = None
    conflict = False
    if source_values:
        candidate = float(median(source_values))
        relative_spread = (max(source_values) - min(source_values)) / candidate if candidate else math.inf
        conflict = len(source_values) > 1 and relative_spread > config.conflict_relative_spread_threshold
        if not conflict:
            canonical_salary = round(candidate, 6)
    status = "conflict" if conflict else "merged_compatible" if len(source_values) > 1 else "parsed_from_group" if source_values else "unavailable"
    return {
        "salary_observations": observations,
        "canonical_salary": canonical_salary,
        "salary_mid_monthly": canonical_salary,
        "salary_source_count": len(source_values),
        "salary_conflict_flag": conflict,
        "salary_parse_status": status,
        "salary_months": int(round(median(valid_months))) if valid_months else None,
    }


def merge_canonical_group(
    members: list[dict[str, Any]], config: CanonicalMergeConfig
) -> dict[str, Any]:
    if not members:
        raise ValueError("Canonical group must contain at least one member")
    title_member = _title_member(members)
    description_member = _description_member(members)
    merged = {
        "canonical_silver_job_id": title_member.get("silver_job_id"),
        "title_source_silver_job_id": title_member.get("silver_job_id"),
        "description_source_silver_job_id": description_member.get("silver_job_id"),
        "company_name_normalized": _stable_mode(members, "company_name_normalized"),
        "job_title_raw": title_member.get("job_title_raw"),
        "job_title_normalized": title_member.get("job_title_normalized"),
        "role_id": title_member.get("role_id"),
        "city_code": _stable_mode(members, "city_code"),
        "experience_band": _stable_mode(members, "experience_band"),
        "education_band": _stable_mode(members, "education_band"),
        "market_scope": title_member.get("market_scope"),
        "market_scope_method": title_member.get("market_scope_method"),
        "market_scope_version": title_member.get("market_scope_version"),
        "job_description_raw": description_member.get("job_description_raw"),
        "first_posted_at": _date_boundary(members, "published_at", earliest=True, require_reliable=True),
        "first_seen_at": _date_boundary(members, "observed_at", earliest=True),
        "last_seen_at": _date_boundary(members, "observed_at", earliest=False),
        "canonical_merge_version": config.version,
    }
    merged["published_at"] = merged["first_posted_at"]
    merged.update(_salary_merge(members, config.salary))
    return merged
