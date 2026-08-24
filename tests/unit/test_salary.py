from __future__ import annotations

import pytest

from app.salary import parse_salary


@pytest.mark.parametrize(
    ("raw", "minimum", "maximum", "midpoint", "annualized", "months", "status"),
    [
        ("15-25K", 15_000, 25_000, 20_000, 240_000, None, "parsed_monthly"),
        ("15-25k", 15_000, 25_000, 20_000, 240_000, None, "parsed_monthly"),
        ("20-30K·13薪", 20_000, 30_000, 25_000, 325_000, 13, "parsed_monthly_with_months"),
        ("30-50K·14薪", 30_000, 50_000, 40_000, 560_000, 14, "parsed_monthly_with_months"),
        ("200-300元/天", 4_350, 6_525, 5_437.5, 65_250, 12, "parsed_daily"),
        ("20-30万/年", 200_000 / 12, 300_000 / 12, 250_000 / 12, 250_000, 12, "parsed_annual"),
    ],
)
def test_parse_supported_salary_formats(
    raw: str,
    minimum: float,
    maximum: float,
    midpoint: float,
    annualized: float,
    months: int | None,
    status: str,
) -> None:
    result = parse_salary(raw)

    assert result.salary_min_monthly == pytest.approx(minimum)
    assert result.salary_max_monthly == pytest.approx(maximum)
    assert result.salary_mid_monthly == pytest.approx(midpoint)
    assert result.salary_annualized == pytest.approx(annualized)
    assert result.salary_months == months
    assert result.salary_parse_status == status


def test_negotiable_salary_is_not_imputed() -> None:
    result = parse_salary("面议")

    assert result.salary_parse_status == "negotiable"
    assert result.salary_min_monthly is None
    assert result.salary_max_monthly is None
    assert result.salary_mid_monthly is None
    assert result.salary_annualized is None
    assert result.salary_months is None


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (None, "missing_at_source"),
        ("", "missing_at_source"),
        ("30-20K", "invalid_range"),
        ("0-0K", "invalid_range"),
        ("15-25美元/月", "unparseable"),
        ("随便写的薪资", "unparseable"),
        (f"{'9' * 400}-{'9' * 401}K", "invalid_range"),
    ],
)
def test_invalid_salary_never_guesses(raw: str | None, status: str) -> None:
    result = parse_salary(raw)

    assert result.salary_parse_status == status
    assert result.salary_min_monthly is None
    assert result.salary_max_monthly is None
    assert result.salary_mid_monthly is None
    assert result.salary_annualized is None
    assert result.salary_months is None


def test_salary_parser_normalizes_unicode_and_whitespace() -> None:
    result = parse_salary(" ￥ ２０ - ３０ ｋ · １３薪 ")

    assert result.salary_min_monthly == pytest.approx(20_000)
    assert result.salary_max_monthly == pytest.approx(30_000)
    assert result.salary_months == 13
