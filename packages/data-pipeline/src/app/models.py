from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SalaryParseResult:
    salary_raw: str | None
    salary_min_monthly: float | None
    salary_max_monthly: float | None
    salary_mid_monthly: float | None
    salary_annualized: float | None
    salary_months: int | None
    salary_parse_status: str


@dataclass(frozen=True, slots=True)
class RoleNormalizationResult:
    role_id: str
    role_parse_status: str
    taxonomy_version: str


@dataclass(frozen=True, slots=True)
class CityNormalizationResult:
    city_code: str | None
    city_parse_status: str
    taxonomy_version: str


@dataclass(frozen=True, slots=True)
class EducationNormalizationResult:
    education_band: str | None
    education_parse_status: str


@dataclass(frozen=True, slots=True)
class ExperienceNormalizationResult:
    experience_min_years: float | None
    experience_max_years: float | None
    experience_band: str | None
    experience_parse_status: str


@dataclass(frozen=True, slots=True)
class DateNormalizationResult:
    published_at: date | None
    date_parse_status: str
