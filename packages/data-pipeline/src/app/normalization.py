from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from app.config import CityTaxonomy, RoleTaxonomy
from app.models import (
    CityNormalizationResult,
    DateNormalizationResult,
    EducationNormalizationResult,
    ExperienceNormalizationResult,
    RoleNormalizationResult,
)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized or None


def normalize_company(value: str | None) -> str | None:
    return _normalize_text(value)


def normalize_job_title(value: str | None) -> str | None:
    return _normalize_text(value)


def normalize_role(value: str | None, taxonomy: RoleTaxonomy) -> RoleNormalizationResult:
    normalized = normalize_job_title(value)
    if normalized is None:
        return RoleNormalizationResult(taxonomy.fallback_role, "missing_at_source", taxonomy.version)

    for role in taxonomy.roles:
        if role.id == taxonomy.fallback_role:
            continue
        if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in role.patterns):
            return RoleNormalizationResult(role.id, "parsed", taxonomy.version)
    return RoleNormalizationResult(taxonomy.fallback_role, "fallback_other", taxonomy.version)


def normalize_city(value: str | None, taxonomy: CityTaxonomy) -> CityNormalizationResult:
    normalized = _normalize_text(value)
    if normalized is None:
        return CityNormalizationResult(None, "missing_at_source", taxonomy.version)

    candidates: list[tuple[int, str]] = []
    for city in taxonomy.cities:
        for alias in city.aliases:
            normalized_alias = _normalize_text(alias)
            if normalized_alias and normalized.startswith(normalized_alias):
                candidates.append((len(normalized_alias), city.code))
    if not candidates:
        return CityNormalizationResult(None, "unparseable", taxonomy.version)
    _, code = max(candidates, key=lambda item: item[0])
    return CityNormalizationResult(code, "parsed", taxonomy.version)


def normalize_education(value: str | None) -> EducationNormalizationResult:
    normalized = _normalize_text(value)
    if normalized is None:
        return EducationNormalizationResult(None, "missing_at_source")

    rules = (
        ("no_requirement", ("不限", "无学历要求")),
        ("doctorate", ("博士",)),
        ("master", ("硕士", "研究生")),
        ("bachelor", ("本科",)),
        ("associate", ("大专", "专科",)),
        ("high_school", ("高中", "中专", "中技")),
    )
    for band, patterns in rules:
        if any(pattern in normalized for pattern in patterns):
            return EducationNormalizationResult(band, "parsed")
    return EducationNormalizationResult(None, "unparseable")


def _experience_band(minimum: float, maximum: float | None) -> str:
    if maximum is not None and maximum <= 1:
        return "entry"
    if minimum < 3:
        return "junior"
    if minimum < 5:
        return "mid"
    if minimum < 10:
        return "senior"
    return "expert"


def normalize_experience(value: str | None) -> ExperienceNormalizationResult:
    normalized = _normalize_text(value)
    if normalized is None:
        return ExperienceNormalizationResult(None, None, None, "missing_at_source")
    normalized = normalized.replace("－", "-").replace("—", "-")

    if "不限" in normalized or "无经验要求" in normalized:
        return ExperienceNormalizationResult(0.0, None, "no_requirement", "parsed")
    if any(token in normalized for token in ("应届", "在校", "实习")):
        return ExperienceNormalizationResult(0.0, 0.0, "entry", "parsed")

    range_match = re.search(r"(?P<minimum>\d+(?:\.\d+)?)\s*-\s*(?P<maximum>\d+(?:\.\d+)?)年", normalized)
    if range_match:
        minimum = float(range_match.group("minimum"))
        maximum = float(range_match.group("maximum"))
        if minimum > maximum:
            return ExperienceNormalizationResult(None, None, None, "unparseable")
        return ExperienceNormalizationResult(minimum, maximum, _experience_band(minimum, maximum), "parsed")

    within_match = re.search(r"(?P<maximum>\d+(?:\.\d+)?)年(?:以内|以下)", normalized)
    if within_match:
        maximum = float(within_match.group("maximum"))
        return ExperienceNormalizationResult(0.0, maximum, _experience_band(0.0, maximum), "parsed")

    above_match = re.search(r"(?P<minimum>\d+(?:\.\d+)?)年(?:以上|及以上)", normalized)
    if above_match:
        minimum = float(above_match.group("minimum"))
        return ExperienceNormalizationResult(minimum, None, _experience_band(minimum, None), "parsed")

    exact_match = re.search(r"(?P<years>\d+(?:\.\d+)?)年", normalized)
    if exact_match:
        years = float(exact_match.group("years"))
        return ExperienceNormalizationResult(years, years, _experience_band(years, years), "parsed")
    return ExperienceNormalizationResult(None, None, None, "unparseable")


def normalize_date(value: str | None) -> DateNormalizationResult:
    normalized = _normalize_text(value)
    if normalized is None:
        return DateNormalizationResult(None, "missing_at_source")

    iso_candidate = normalized.replace("z", "+00:00")
    try:
        return DateNormalizationResult(datetime.fromisoformat(iso_candidate).date(), "parsed")
    except ValueError:
        pass

    for pattern in ("%Y/%m/%d", "%Y.%m.%d"):
        try:
            return DateNormalizationResult(datetime.strptime(normalized, pattern).date(), "parsed")
        except ValueError:
            continue
    return DateNormalizationResult(None, "unparseable")
