from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from app.annotation_translation import (
    TranslationHelperError,
    TranslationHelperStore,
    build_translation_record,
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def test_translation_helper_matches_kind_sample_and_original_hash(tmp_path: Path) -> None:
    helper_root = tmp_path / "annotation_helpers"
    helper_root.mkdir()
    record = build_translation_record(
        kind="roles",
        sample_id="role-1",
        title="Backend Engineer",
        description="Build Python services.",
        title_zh="后端工程师",
        description_zh="构建 Python 服务。",
        method="offline_machine_translation",
        model="fixture-model",
    )
    (helper_root / "roles.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    helper = TranslationHelperStore(helper_root).get(
        "roles", "role-1", title="Backend Engineer", description="Build Python services."
    )

    assert helper is not None
    assert helper.title_zh == "后端工程师"
    assert helper.description_zh == "构建 Python 服务。"
    assert helper.original_title_sha256 == _hash("Backend Engineer")
    assert helper.original_description_sha256 == _hash("Build Python services.")
    assert "gold" not in record
    assert "prediction" not in record


def test_translation_helper_rejects_stale_or_duplicate_records(tmp_path: Path) -> None:
    helper_root = tmp_path / "annotation_helpers"
    helper_root.mkdir()
    record = build_translation_record(
        kind="skills",
        sample_id="skill-1",
        title="Data Analyst",
        description="Use SQL.",
        title_zh="数据分析师",
        description_zh="使用 SQL。",
        method="human_assisted_translation",
        model="fixture",
    )
    (helper_root / "skills.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for _ in range(2)) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(TranslationHelperError, match="重复"):
        TranslationHelperStore(helper_root)

    (helper_root / "skills.jsonl").write_text(
        json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    store = TranslationHelperStore(helper_root)
    with pytest.raises(TranslationHelperError, match="原文 hash"):
        store.get("skills", "skill-1", title="Data Analyst", description="Changed")


def test_missing_translation_never_replaces_original(tmp_path: Path) -> None:
    store = TranslationHelperStore(tmp_path / "missing")

    assert store.get("roles", "missing", title="Original", description="Original JD") is None


def test_first_real_role_translation_matches_immutable_sample() -> None:
    project_root = Path(__file__).resolve().parents[2]
    pending_path = project_root / "data" / "benchmarks" / "roles" / "pending" / "batch.yml"
    helper_root = project_root / "data" / "benchmarks" / "annotation_helpers"
    if not pending_path.is_file() or not helper_root.is_dir():
        pytest.skip("requires local human-reviewed annotation artifacts")
    pending = yaml.safe_load(pending_path.read_text(encoding="utf-8"))
    first = pending["records"][0]

    helper = TranslationHelperStore(helper_root).get(
        "roles",
        first["record_id"],
        title=first["title"],
        description=first["description_excerpt"],
    )

    assert first["title"] == "Prin. Electrical Software Engineer"
    assert helper is not None
    assert helper.title_zh == "首席电气软件工程师（Principal）"
    assert "LabVIEW" in helper.description_zh
