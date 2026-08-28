from __future__ import annotations

import json
from pathlib import Path
import shutil

import duckdb

from fastapi.testclient import TestClient

from skillworth_api.main import create_app
from skillworth_api.settings import ApiSettings


def _client() -> TestClient:
    return TestClient(create_app(ApiSettings(cache_ttl_seconds=120)), raise_server_exceptions=False)


def test_api_settings_keep_demo_default_and_load_real_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("SKILLWORTH_DATA_MODE", raising=False)
    demo_settings = ApiSettings.from_environment()
    assert demo_settings.data_mode == "demo"
    assert demo_settings.access_date.isoformat() == "2026-08-08"

    manifest = tmp_path / "current.json"
    manifest.write_text(
        json.dumps(
            {
                "warehouse_path": str(tmp_path / "real.duckdb"),
                "graph_edges_path": str(tmp_path / "edges.parquet"),
                "quality_report_path": str(tmp_path / "quality.json"),
                "acquired_at": "2026-08-10T12:30:00+08:00",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SKILLWORTH_DATA_MODE", "real")
    monkeypatch.setenv("SKILLWORTH_REAL_MODE_MANIFEST", str(manifest))

    settings = ApiSettings.from_environment()

    assert settings.data_mode == "real"
    assert settings.warehouse_path == tmp_path / "real.duckdb"
    assert settings.access_date.isoformat() == "2026-08-10"


def test_health_and_openapi_document_every_public_endpoint() -> None:
    client = _client()
    health = client.get("/health")
    assert health.json()["status"] == "ok"
    assert health.headers["X-Content-Type-Options"] == "nosniff"
    assert health.headers["X-Frame-Options"] == "DENY"
    assert health.headers["Referrer-Policy"] == "no-referrer"

    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/health",
        "/market/summary",
        "/market/trends",
        "/market/china-skillworth",
        "/market/china-skill-relations",
        "/skills",
        "/skills/{skill_id}",
        "/skills/{skill_id}/trend",
        "/skills/{skill_id}/salary",
        "/skills/{skill_id}/related",
        "/roles",
        "/roles/{role_id}",
        "/sources",
        "/data-quality",
        "/portfolio/analyze",
        "/portfolio/optimize",
    }
    assert expected <= set(paths)


def test_china_skillworth_endpoint_exposes_scope_and_unavailable_signals(tmp_path: Path) -> None:
    source = Path("data/modes/demo/current/warehouse/skillworth.duckdb")
    warehouse = tmp_path / "skillworth.duckdb"
    shutil.copyfile(source, warehouse)
    connection = duckdb.connect(str(warehouse))
    try:
        connection.execute(
            "CREATE OR REPLACE TABLE china_skillworth_visual_ready AS SELECT "
            "'python' skill_id, 'Python' skill, 'programming_language' skill_type, "
            "'programming' skill_category, 'main' skillworth_eligibility, "
            "'specific technology' eligibility_reason, "
            "1 job_count, 0.5 job_coverage, 2 sample_size, "
            "1 company_count, 0.5 company_coverage, 2 company_sample_size, "
            "1 role_count, 0.5 role_breadth, 0.4 synergy_score, 40.0 market_signal, "
            "50.0 learning_hours_min, 80.0 learning_hours_expected, 120.0 learning_hours_max, "
            "26.4 skillworth_score, 1 skillworth_rank, 1 sensitivity_rank_min, "
            "2 sensitivity_rank_max, 80.0 ranking_robustness, 'robust' robustness_level, "
            "35.0 confidence, 'Low' confidence_level, true high_skillworth_candidate, "
            "NULL::VARCHAR market_theme, 'freehire_china_tech_2026_08' snapshot_id, "
            "'180d' recency_window, NULL::VARCHAR role_id, 'available' window_status, "
            "'unavailable' salary_signal_status, 'unavailable' trend_signal_status"
        )
        connection.execute(
            "CREATE OR REPLACE TABLE china_skillworth_market_themes AS SELECT "
            "'AI' market_theme, 1 job_count, 0.5 job_coverage, 1 company_count, "
            "0.5 company_coverage, 1 role_count, 'freehire_china_tech_2026_08' snapshot_id, "
            "'180d' recency_window"
        )
    finally:
        connection.close()
    settings = ApiSettings(
        data_mode="real",
        warehouse_path=warehouse,
        market_scope="china_open_tech_sample",
        source_role="china_supplementary",
        snapshot="2026-08",
        access_date="2026-08-10",
        job_count=2,
        company_count=2,
        source_count=1,
        disclaimer="scope disclaimer",
    )
    client = TestClient(create_app(settings), raise_server_exceptions=False)

    response = client.get("/market/china-skillworth")

    assert response.status_code == 200
    assert response.json()["snapshot"] == "2026-08"
    assert response.json()["access_date"] == "2026-08-10"
    assert response.json()["recency_window"] == "180d"
    assert response.json()["skill_count"] == 1
    assert response.json()["source_role"] == "china_supplementary"
    assert response.json()["records"][0]["skillworth_eligibility"] == "main"
    assert response.json()["records"][0]["demand_rank"] == 1
    assert response.json()["records"][0]["synergy_score"] == 0.4
    assert response.json()["market_themes"][0]["market_theme"] == "AI"
    assert response.json()["records"][0]["trend_signal_status"] == "unavailable"
    assert response.headers["X-SkillWorth-Market-Scope"] == "china_open_tech_sample"

    assert client.get("/market/china-skillworth?eligibility=excluded").json()["records"] == []
    assert client.get("/market/china-skillworth?robustness=robust").status_code == 200
    assert len(client.get("/market/china-skillworth?skill_type=programming_language").json()["records"]) == 1
    assert client.get("/market/china-skillworth?role=data_engineer").json()["records"] == []
    assert client.get("/market/china-skillworth?recency_window=invalid").status_code == 422


def test_market_skill_role_source_and_quality_endpoints_use_real_warehouse_outputs() -> None:
    client = _client()

    first_summary = client.get("/market/summary")
    second_summary = client.get("/market/summary")
    assert first_summary.status_code == 200
    assert first_summary.headers["X-Cache"] == "MISS"
    assert second_summary.headers["X-Cache"] == "HIT"
    assert first_summary.json()["metadata"]["sample_size"] >= 0

    assert client.get("/market/trends").status_code == 200
    skills = client.get("/skills")
    assert skills.status_code == 200
    skill_id = skills.json()["records"][0]["skill_id"]
    for suffix in ("", "/trend", "/salary", "/related"):
        assert client.get(f"/skills/{skill_id}{suffix}").status_code == 200
    relations = client.get(
        "/market/china-skill-relations",
        params={"core_skill_id": skill_id, "recency_window": "all_active"},
    )
    assert relations.status_code == 200
    assert relations.json()["core_skill_id"] == skill_id
    assert relations.json()["metadata"]["canonical_job_denominator"] == "canonical_job_id"
    assert client.get(
        "/market/china-skill-relations",
        params={"core_skill_id": skill_id, "market_scope": "wrong-scope"},
    ).status_code == 422

    roles = client.get("/roles")
    assert roles.status_code == 200
    role_id = roles.json()["records"][0]["role_id"]
    assert client.get(f"/roles/{role_id}").status_code == 200
    assert client.get("/sources").status_code == 200
    assert client.get("/data-quality").status_code == 200


def test_portfolio_endpoints_delegate_validated_requests_to_existing_engines() -> None:
    client = _client()
    role_id = client.get("/roles").json()["records"][0]["role_id"]

    analysis = client.post(
        "/portfolio/analyze",
        json={"current_skills": [], "target_role": role_id, "match_threshold": 0.7},
    )
    optimization = client.post(
        "/portfolio/optimize",
        json={"current_skills": [], "target_role": role_id, "hour_budget": 100},
    )
    assert analysis.status_code == 200
    assert "current_average_fit" in analysis.json()
    assert optimization.status_code == 200
    assert optimization.json()["strategy"] == "iterative_greedy_marginal_gain"


def test_invalid_and_unknown_requests_have_clear_status_codes_and_error_contract() -> None:
    client = _client()
    invalid_dates = client.get("/market/summary?published_from=2026-02-01&published_to=2026-01-01")
    unknown_skill = client.get("/skills/not-a-real-skill")
    invalid_portfolio = client.post(
        "/portfolio/analyze",
        json={"current_skills": ["python", "python"], "target_role": "data_analyst", "match_threshold": 0.7},
    )

    assert invalid_dates.status_code == 422
    assert invalid_dates.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unknown_skill.status_code == 404
    assert unknown_skill.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert invalid_portfolio.status_code == 422
    assert invalid_portfolio.json()["error"]["code"] == "VALIDATION_ERROR"


def test_request_models_reject_unknown_and_oversized_input() -> None:
    client = _client()

    unknown = client.post(
        "/portfolio/analyze",
        json={
            "current_skills": [],
            "target_role": "data_analyst",
            "match_threshold": 0.7,
            "unexpected": "ignored-before-audit",
        },
    )
    oversized = client.post(
        "/portfolio/analyze",
        json={
            "current_skills": [f"skill-{index}" for index in range(257)],
            "target_role": "data_analyst",
            "match_threshold": 0.7,
        },
    )

    assert unknown.status_code == 422
    assert oversized.status_code == 422


def test_missing_data_error_does_not_expose_local_file_path(tmp_path: Path) -> None:
    missing = tmp_path / "private" / "quality.json"
    client = TestClient(
        create_app(ApiSettings(quality_report_path=missing)),
        raise_server_exceptions=False,
    )

    response = client.get("/data-quality")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATA_UNAVAILABLE"
    assert str(missing) not in response.text
