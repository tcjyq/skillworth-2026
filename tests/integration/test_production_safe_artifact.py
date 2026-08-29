from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from skillworth_api.main import create_app
from skillworth_api.production_safe import audit_production_safe_artifact
from skillworth_api.settings import ApiSettings


ARTIFACT_ROOT = Path("data/production-safe/current")


def test_checked_in_production_safe_artifact_has_frozen_parity_and_no_restricted_content() -> None:
    audit = audit_production_safe_artifact(ARTIFACT_ROOT)

    assert audit.classification == "PUBLIC_SAFE"
    assert audit.snapshot == "freehire_china_tech_2026_08"
    assert audit.job_count == 998
    assert audit.company_count == 313
    assert audit.skill_count == 134
    assert audit.parity["cpp_demand_rank"] == 3
    assert audit.parity["cpp_skillworth_rank"] == 35
    assert audit.parity["python_sql_cooccurrence"] == 128
    assert audit.parity["devops_sample_size"] == 21
    assert audit.parity["data_engineer_sample_size"] == 38
    assert audit.restricted_findings == ()


def test_production_safe_runtime_reads_only_checked_in_aggregate_artifact() -> None:
    settings = ApiSettings(data_mode="production_safe", production_safe_artifact_path=ARTIFACT_ROOT)
    client = TestClient(create_app(settings), raise_server_exceptions=False)

    health = client.get("/health")
    overview = client.get(
        "/market/china-skillworth",
        params={"eligibility": "all", "robustness": "all", "recency_window": "180d"},
    )
    relations = client.get(
        "/market/china-skill-relations",
        params={"core_skill_id": "programming_python", "recency_window": "180d"},
    )
    portfolio = client.post(
        "/portfolio/analyze",
        json={"current_skills": [], "target_role": "data_engineer", "match_threshold": 0.7},
    )

    assert health.status_code == 200
    assert health.json()["warehouse_available"] is True
    assert overview.status_code == 200
    assert overview.json()["job_count"] == 998
    assert relations.status_code == 200
    assert portfolio.status_code == 503
    assert portfolio.json()["error"]["code"] == "DATA_UNAVAILABLE"
