from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.config import load_city_taxonomy, load_role_taxonomy
from app.normalization import (
    normalize_city,
    normalize_company,
    normalize_date,
    normalize_education,
    normalize_experience,
    normalize_job_title,
    normalize_role,
)


ROOT = Path(__file__).resolve().parents[2]
ROLE_CONFIG = ROOT / "data/reference/role_taxonomy.v1.json"
CITY_CONFIG = ROOT / "data/reference/city_taxonomy.v1.json"


@pytest.mark.parametrize(
    ("title", "expected_role"),
    [
        ("高级数据分析师", "data_analyst"),
        ("BI 数据分析师", "bi_analyst"),
        ("数据科学家", "data_scientist"),
        ("大数据开发工程师", "data_engineer"),
        ("算法工程师", "ai_engineer"),
        ("Java后端开发", "backend_engineer"),
        ("Web前端工程师", "frontend_engineer"),
        ("SRE 运维开发", "devops_engineer"),
        ("产品经理", "product_manager"),
        ("销售顾问", "other"),
    ],
)
def test_role_taxonomy_is_config_driven(title: str, expected_role: str) -> None:
    taxonomy = load_role_taxonomy(ROLE_CONFIG)

    result = normalize_role(title, taxonomy)

    assert result.role_id == expected_role
    expected_status = "fallback_other" if expected_role == "other" else "parsed"
    assert result.role_parse_status == expected_status


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        ("北京·海淀区", "CN-BJ"),
        ("上海市浦东新区", "CN-SH"),
        ("深圳", "CN-SZ"),
        ("Shanghai", "CN-SH"),
        ("Guangzhou", "CN-GZ"),
        ("remote", "REMOTE"),
    ],
)
def test_city_normalization(raw: str, expected_code: str) -> None:
    taxonomy = load_city_taxonomy(CITY_CONFIG)

    result = normalize_city(raw, taxonomy)

    assert result.city_code == expected_code
    assert result.city_parse_status == "parsed"


def test_unknown_city_is_not_guessed() -> None:
    taxonomy = load_city_taxonomy(CITY_CONFIG)

    result = normalize_city("未知城市", taxonomy)

    assert result.city_code is None
    assert result.city_parse_status == "unparseable"


def test_text_normalization_is_conservative() -> None:
    assert normalize_company("  ＡＢＣ　科技（北京）有限公司  ") == "abc 科技(北京)有限公司"
    assert normalize_job_title("  高级　Data Analyst  ") == "高级 data analyst"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("本科及以上", "bachelor"), ("硕士", "master"), ("学历不限", "no_requirement")],
)
def test_education_normalization(raw: str, expected: str) -> None:
    result = normalize_education(raw)

    assert result.education_band == expected
    assert result.education_parse_status == "parsed"


def test_experience_normalization_handles_ranges_and_no_requirement() -> None:
    ranged = normalize_experience("3-5年")
    unrestricted = normalize_experience("经验不限")

    assert (ranged.experience_min_years, ranged.experience_max_years) == (3.0, 5.0)
    assert ranged.experience_band == "mid"
    assert unrestricted.experience_band == "no_requirement"
    assert unrestricted.experience_min_years == 0
    assert unrestricted.experience_max_years is None


@pytest.mark.parametrize("raw", ["2026-08-01", "2026/08/01", "2026.08.01"])
def test_date_normalization(raw: str) -> None:
    result = normalize_date(raw)

    assert result.published_at == date(2026, 8, 1)
    assert result.date_parse_status == "parsed"


def test_invalid_date_is_not_guessed() -> None:
    result = normalize_date("昨天")

    assert result.published_at is None
    assert result.date_parse_status == "unparseable"
