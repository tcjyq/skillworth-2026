from __future__ import annotations

import re
import unicodedata
from math import isfinite

from app.models import SalaryParseResult


STANDARD_MONTHS_PER_YEAR = 12
WORKING_DAYS_PER_MONTH = 21.75

_MONTHLY_PATTERN = re.compile(
    r"^(?P<minimum>\d+(?:\.\d+)?)-(?P<maximum>\d+(?:\.\d+)?)k"
    r"(?:[·x*]?(?P<months>\d{1,2})薪)?$",
    re.IGNORECASE,
)
_DAILY_PATTERN = re.compile(
    r"^(?P<minimum>\d+(?:\.\d+)?)-(?P<maximum>\d+(?:\.\d+)?)元/(?:天|日)$"
)
_ANNUAL_PATTERN = re.compile(
    r"^(?P<minimum>\d+(?:\.\d+)?)-(?P<maximum>\d+(?:\.\d+)?)万/年$"
)


def _empty(raw: str | None, status: str) -> SalaryParseResult:
    return SalaryParseResult(
        salary_raw=raw,
        salary_min_monthly=None,
        salary_max_monthly=None,
        salary_mid_monthly=None,
        salary_annualized=None,
        salary_months=None,
        salary_parse_status=status,
    )


def _valid_range(minimum: float, maximum: float) -> bool:
    return isfinite(minimum) and isfinite(maximum) and minimum > 0 and maximum > 0 and minimum <= maximum


def parse_salary(raw: str | None) -> SalaryParseResult:
    if raw is None or not raw.strip():
        return _empty(raw, "missing_at_source")

    normalized = unicodedata.normalize("NFKC", raw).strip().lower()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace("￥", "").replace("¥", "")

    if normalized in {"面议", "薪资面议"}:
        return _empty(raw, "negotiable")

    monthly = _MONTHLY_PATTERN.fullmatch(normalized)
    if monthly:
        minimum = float(monthly.group("minimum")) * 1_000
        maximum = float(monthly.group("maximum")) * 1_000
        if not _valid_range(minimum, maximum):
            return _empty(raw, "invalid_range")
        midpoint = (minimum + maximum) / 2
        months_text = monthly.group("months")
        months = int(months_text) if months_text is not None else None
        if months is not None and not 12 <= months <= 24:
            return _empty(raw, "invalid_range")
        annualized = midpoint * (months or STANDARD_MONTHS_PER_YEAR)
        status = "parsed_monthly_with_months" if months is not None else "parsed_monthly"
        return SalaryParseResult(raw, minimum, maximum, midpoint, annualized, months, status)

    daily = _DAILY_PATTERN.fullmatch(normalized)
    if daily:
        minimum_daily = float(daily.group("minimum"))
        maximum_daily = float(daily.group("maximum"))
        if not _valid_range(minimum_daily, maximum_daily):
            return _empty(raw, "invalid_range")
        minimum = minimum_daily * WORKING_DAYS_PER_MONTH
        maximum = maximum_daily * WORKING_DAYS_PER_MONTH
        midpoint = (minimum + maximum) / 2
        return SalaryParseResult(
            raw,
            minimum,
            maximum,
            midpoint,
            midpoint * STANDARD_MONTHS_PER_YEAR,
            STANDARD_MONTHS_PER_YEAR,
            "parsed_daily",
        )

    annual = _ANNUAL_PATTERN.fullmatch(normalized)
    if annual:
        minimum_annual = float(annual.group("minimum")) * 10_000
        maximum_annual = float(annual.group("maximum")) * 10_000
        if not _valid_range(minimum_annual, maximum_annual):
            return _empty(raw, "invalid_range")
        minimum = minimum_annual / STANDARD_MONTHS_PER_YEAR
        maximum = maximum_annual / STANDARD_MONTHS_PER_YEAR
        midpoint_annual = (minimum_annual + maximum_annual) / 2
        return SalaryParseResult(
            raw,
            minimum,
            maximum,
            midpoint_annual / STANDARD_MONTHS_PER_YEAR,
            midpoint_annual,
            STANDARD_MONTHS_PER_YEAR,
            "parsed_annual",
        )

    range_match = re.match(r"^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)", normalized)
    if range_match and float(range_match.group(1)) > float(range_match.group(2)):
        return _empty(raw, "invalid_range")
    return _empty(raw, "unparseable")
