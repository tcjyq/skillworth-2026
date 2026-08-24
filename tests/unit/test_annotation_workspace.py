from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path

import polars as pl
import pytest
import yaml
from streamlit.testing.v1 import AppTest

from app.annotation_workspace import AnnotationValidationError, AnnotationWorkspace
from app.annotation_translation import build_translation_record


ROOT = Path(__file__).resolve().parents[2]


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _workspace(tmp_path: Path) -> AnnotationWorkspace:
    benchmark_root = tmp_path / "benchmarks"
    metadata = {
        "benchmark_version": "2.0.0",
        "created_at": "2026-08-10T00:00:00+08:00",
        "label_count": 0,
        "split_seed": 42,
        "taxonomy_version": "1.1.0",
        "dedup_version": "1.1.0",
        "role_taxonomy_version": "1.2.0",
    }
    _write_yaml(
        benchmark_root / "skills/pending/batch.yml",
        {
            "metadata": {"split_seed": 42},
            "records": [
                {
                    "record_id": "skill-1",
                    "title": "Data Analyst",
                    "description": "Use SQL and Python",
                    "source": "fixture",
                    "language": "en",
                    "predicted_skills": ["programming_python"],
                    "gold_skills": None,
                    "negative_terms": [],
                    "difficulty": "medium",
                    "annotator": None,
                    "annotation_notes": "",
                    "split": "held_out_test",
                },
                {
                    "record_id": "skill-2",
                    "title": "Operations",
                    "description": "Coordinate schedules",
                    "source": "fixture",
                    "language": "en",
                    "predicted_skills": [],
                    "gold_skills": None,
                    "negative_terms": [],
                    "difficulty": "hard",
                    "annotator": None,
                    "annotation_notes": "",
                    "split": "development",
                },
            ],
        },
    )
    _write_yaml(
        benchmark_root / "roles/pending/batch.yml",
        {
            "metadata": {"split_seed": 42},
            "records": [
                {
                    "record_id": "role-1",
                    "title": "Data Analyst",
                    "description_excerpt": "Build dashboards",
                    "source": "fixture",
                    "predicted_role": "data_analyst",
                    "gold_role": None,
                    "difficulty": "easy",
                    "annotator": None,
                    "annotation_notes": "",
                    "split": "held_out_test",
                }
            ],
        },
    )
    _write_yaml(
        benchmark_root / "dedup/pending/batch.yml",
        {
            "metadata": {"split_seed": 42},
            "pairs": [
                {
                    "pair_id": "pair-1",
                    "left_job_id": "job-a",
                    "right_job_id": "job-b",
                    "predicted_duplicate": True,
                    "gold_duplicate": None,
                    "difficulty": "hard",
                    "reason": "similar_title",
                    "source_pair": "a|b",
                    "annotator": None,
                    "annotation_notes": "",
                    "split": "development",
                }
            ],
        },
    )
    for kind, rows_key in (("skills", "records"), ("roles", "records"), ("dedup", "pairs")):
        _write_yaml(benchmark_root / kind / "gold.yml", {"metadata": metadata, rows_key: []})
    helper_root = benchmark_root / "annotation_helpers"
    helper_root.mkdir()
    role_helper = build_translation_record(
        kind="roles",
        sample_id="role-1",
        title="Data Analyst",
        description="Build dashboards",
        title_zh="数据分析师",
        description_zh="构建数据看板。",
        method="human_assisted_translation",
        model="fixture",
    )
    (helper_root / "roles.jsonl").write_text(
        json.dumps(role_helper, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    silver = tmp_path / "silver.parquet"
    pl.DataFrame(
        {
            "silver_job_id": ["job-a", "job-b"],
            "company_name_normalized": ["Acme", "Acme"],
            "job_title_raw": ["Backend Engineer", "Senior Backend Engineer"],
            "role_id": ["backend_engineer", "backend_engineer"],
            "city_raw": ["Beijing", "Shanghai"],
            "salary_raw": ["20-30K", "30-40K"],
            "published_at": ["2026-08-01", "2026-08-02"],
            "source_id": ["a", "b"],
            "job_description_raw": ["Build APIs", "Build platform APIs"],
        }
    ).write_parquet(silver)
    return AnnotationWorkspace(
        benchmark_root=benchmark_root,
        skill_taxonomy_path=ROOT / "data/taxonomy/skills.yml",
        role_taxonomy_path=ROOT / "data/reference/role_taxonomy.v1.json",
        silver_path=silver,
        clock=lambda: datetime(2026, 8, 11, 4, 0, tzinfo=UTC),
    )


def test_save_resume_and_edit_skill_annotation(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    workspace.save_skill(
        "skill-1",
        ["programming_python"],
        annotator="human-a",
        ambiguous=False,
        notes="confirmed from requirement",
        human_confirmed=True,
    )

    reopened = _workspace_from_existing(workspace)
    assert reopened.progress()["skills"].completed == 1
    assert reopened.next_unannotated("skills")["sample_id"] == "skill-2"
    saved = reopened.annotation("skills", "skill-1")
    assert saved["gold_skills"] == ["programming_python"]
    assert saved["human_confirmed"] is True
    assert saved["annotation_version"] == 1
    assert "predicted_skills" not in saved

    reopened.save_skill(
        "skill-1",
        [],
        annotator="human-a",
        ambiguous=True,
        notes="corrected after review",
        human_confirmed=True,
    )
    edited = reopened.annotation("skills", "skill-1")
    assert edited["gold_skills"] == []
    assert edited["annotation_version"] == 2
    assert reopened.progress()["skills"].completed == 1


def test_role_and_dedup_validation_and_prediction_isolation(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    with pytest.raises(AnnotationValidationError, match="人工确认"):
        workspace.save_role(
            "role-1", "data_analyst", annotator="human-a", ambiguous=False, notes="", human_confirmed=False
        )
    with pytest.raises(AnnotationValidationError, match="未知的岗位"):
        workspace.save_role(
            "role-1", "invented_role", annotator="human-a", ambiguous=False, notes="", human_confirmed=True
        )
    with pytest.raises(AnnotationValidationError, match="未知的技能"):
        workspace.save_skill(
            "skill-1", ["invented_skill"], annotator="human-a", ambiguous=False, notes="", human_confirmed=True
        )
    with pytest.raises(AnnotationValidationError, match="布尔"):
        workspace.save_dedup(  # type: ignore[arg-type]
            "pair-1", "likely_same", annotator="human-a", ambiguous=False, notes="", human_confirmed=True
        )

    workspace.save_role(
        "role-1", "data_analyst", annotator="human-a", ambiguous=False, notes="", human_confirmed=True
    )
    workspace.save_dedup(
        "pair-1", False, annotator="human-a", ambiguous=True, notes="close titles, different city", human_confirmed=True
    )
    assert workspace.annotation("roles", "role-1")["gold_role"] == "data_analyst"
    assert workspace.annotation("dedup", "pair-1")["gold_duplicate"] is False
    assert "predicted_duplicate" not in workspace.annotation("dedup", "pair-1")


def test_chinese_role_label_saves_canonical_enum_and_skill_keeps_canonical_name(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    assert workspace.role_labels["backend_engineer"] == "后端工程师"
    assert set(workspace.role_labels) == set(workspace.role_options)
    assert workspace.skill_options["programming_python"].startswith("Python")
    assert "编程" in workspace.skill_options["programming_python"]
    workspace.save_role(
        "role-1",
        "data_analyst",
        annotator="human-a",
        ambiguous=False,
        notes="中文界面选择",
        human_confirmed=True,
    )

    assert workspace.annotation("roles", "role-1")["gold_role"] == "data_analyst"


def test_presented_sample_hides_split_and_dedup_details_show_differences(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)

    skill = workspace.presented_sample("skills", "skill-1")
    assert "split" not in skill
    assert skill["prediction"] == ["programming_python"]
    assert skill["prediction_is_gold"] is False

    pair = workspace.presented_sample("dedup", "pair-1")
    assert "split" not in pair
    assert pair["left"]["city"] == "Beijing"
    assert pair["right"]["city"] == "Shanghai"
    assert "city" in pair["different_fields"]


def test_integrity_rejects_orphan_and_duplicate_gold(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    gold_path = workspace.benchmark_root / "roles/gold.yml"
    payload = yaml.safe_load(gold_path.read_text(encoding="utf-8"))
    payload["records"] = [
        {"record_id": "orphan"},
        {"record_id": "orphan"},
    ]
    payload["metadata"]["label_count"] = 2
    _write_yaml(gold_path, payload)

    with pytest.raises(AnnotationValidationError, match="重复 Gold ID"):
        workspace.validate_integrity("roles")


def test_navigation_state_is_persisted_and_recovers(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    workspace.remember_position("skills", "skill-2")

    reopened = _workspace_from_existing(workspace)

    assert reopened.resume_sample_id("skills") == "skill-2"
    state = yaml.safe_load(reopened.state_path.read_text(encoding="utf-8"))
    assert "split" not in state


def test_streamlit_skill_flow_saves_resumes_and_hides_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setenv("SKILLWORTH_ANNOTATION_ROOT", str(workspace.benchmark_root))
    monkeypatch.setenv("SKILLWORTH_SKILL_TAXONOMY", str(workspace.skill_taxonomy_path))
    monkeypatch.setenv("SKILLWORTH_ROLE_TAXONOMY", str(workspace.role_taxonomy_path))
    monkeypatch.setenv("SKILLWORTH_ANNOTATION_SILVER", str(workspace.silver_path))
    app_path = ROOT / "packages/data-pipeline/src/app/annotation_ui.py"

    app = AppTest.from_file(app_path, default_timeout=10).run()
    assert not app.exception
    assert app.metric[0].value == "0 / 2"
    assert "held_out_test" not in " ".join(item.value for item in app.markdown)
    assert app.title[0].value == "Gold Benchmark 人工标注"

    app.button(key="continue_skills").click().run()
    app.text_input(key="annotator").input("human-a").run()
    app.multiselect(key="gold_skills_skill-1").select("programming_python").run()
    app.button(key="save_skills_skill-1").click().run()
    assert not app.exception
    assert workspace.annotation("skills", "skill-1")["gold_skills"] == ["programming_python"]

    reopened = AppTest.from_file(app_path, default_timeout=10).run()
    reopened.button(key="continue_skills").click().run()
    assert any("skill-2" in item.value for item in reopened.markdown)
    reopened.button(key="previous_skills_skill-2").click().run()
    reopened.text_input(key="annotator").input("human-a").run()
    reopened.multiselect(key="gold_skills_skill-1").unselect("programming_python").run()
    reopened.button(key="save_skills_skill-1").click().run()
    assert workspace.annotation("skills", "skill-1")["annotation_version"] == 2


def test_streamlit_role_and_dedup_workflows_require_human_actions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = _workspace(tmp_path)
    monkeypatch.setenv("SKILLWORTH_ANNOTATION_ROOT", str(workspace.benchmark_root))
    monkeypatch.setenv("SKILLWORTH_SKILL_TAXONOMY", str(workspace.skill_taxonomy_path))
    monkeypatch.setenv("SKILLWORTH_ROLE_TAXONOMY", str(workspace.role_taxonomy_path))
    monkeypatch.setenv("SKILLWORTH_ANNOTATION_SILVER", str(workspace.silver_path))
    app_path = ROOT / "packages/data-pipeline/src/app/annotation_ui.py"

    role_app = AppTest.from_file(app_path, default_timeout=10).run()
    role_app.button(key="continue_roles").click().run()
    assert any(item.value == "数据分析师" for item in role_app.subheader)
    assert any("查看英文原文" in item.label for item in role_app.expander)
    assert any(item.value == "Build dashboards" for item in role_app.text)
    role_app.text_input(key="annotator").input("human-a").run()
    role_app.selectbox(key="gold_role_role-1").select("data_analyst").run()
    role_app.button(key="save_roles_role-1").click().run()
    assert not role_app.exception
    assert workspace.annotation("roles", "role-1")["human_confirmed"] is True
    assert workspace.annotation("roles", "role-1")["gold_role"] == "data_analyst"

    dedup_app = AppTest.from_file(app_path, default_timeout=10).run()
    dedup_app.button(key="continue_dedup").click().run()
    dedup_app.text_input(key="annotator").input("human-a").run()
    dedup_app.button(key="dedup_different_pair-1").click().run()
    dedup_app.button(key="toggle_ambiguous_dedup_pair-1").click().run()
    dedup_app.button(key="save_dedup_pair-1").click().run()
    assert not dedup_app.exception
    saved = workspace.annotation("dedup", "pair-1")
    assert saved["gold_duplicate"] is False
    assert saved["ambiguous"] is True


def _workspace_from_existing(workspace: AnnotationWorkspace) -> AnnotationWorkspace:
    return AnnotationWorkspace(
        benchmark_root=workspace.benchmark_root,
        skill_taxonomy_path=workspace.skill_taxonomy_path,
        role_taxonomy_path=workspace.role_taxonomy_path,
        silver_path=workspace.silver_path,
        clock=workspace.clock,
    )
