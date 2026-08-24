from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "reference" / "china_tech_company_sources.yml"
REQUIRED_FIELDS = {
    "company",
    "career_site",
    "job_scope",
    "public_browsing",
    "public_job_detail",
    "login_required",
    "cookie_required",
    "csrf_required",
    "captcha_required",
    "public_api_observed",
    "terms_found",
    "data_reuse_permission",
    "automation_permission",
    "redistribution_permission",
    "contact",
    "status",
    "evidence",
    "reviewed_at",
}


def _load_registry() -> dict:
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_china_tech_source_registry_schema_and_statuses() -> None:
    registry = _load_registry()
    allowed_statuses = set(registry["allowed_statuses"])
    assert allowed_statuses == {
        "approved",
        "permission_required",
        "manual_reference_only",
        "rejected",
        "unknown",
    }

    companies = registry["companies"]
    assert {item["company"] for item in companies} == {
        "Tencent",
        "Baidu",
        "Alibaba",
        "Meituan",
        "ByteDance",
    }
    for item in companies:
        assert REQUIRED_FIELDS <= item.keys()
        assert item["status"] in allowed_statuses
        assert item["evidence"]


def test_tencent_automation_route_is_closed() -> None:
    registry = _load_registry()
    tencent = next(item for item in registry["companies"] if item["company"] == "Tencent")

    assert tencent["status"] == "manual_reference_only"
    assert tencent["automation_permission"] == "prohibited_by_current_terms"
    assert tencent["data_reuse_permission"] == "not_granted"


def test_unreviewed_company_sources_are_not_approved() -> None:
    registry = _load_registry()
    statuses = {item["company"]: item["status"] for item in registry["companies"]}

    assert statuses["Baidu"] == "permission_required"
    assert statuses["Alibaba"] == "permission_required"
    assert statuses["Meituan"] == "permission_required"
    assert statuses["ByteDance"] == "permission_required"
