from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl
import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.config import load_role_taxonomy
from app.annotation_translation import TranslationHelperStore
from app.skill_taxonomy import load_skill_taxonomy


AnnotationKind = Literal["skills", "roles", "dedup"]


class AnnotationValidationError(ValueError):
    pass


class AnnotationProgress(BaseModel):
    model_config = ConfigDict(frozen=True)

    completed: int = Field(ge=0)
    total: int = Field(ge=0)

    @property
    def remaining(self) -> int:
        return self.total - self.completed


_CONFIG: dict[AnnotationKind, dict[str, str]] = {
    "skills": {"rows_key": "records", "id_key": "record_id", "gold_key": "gold_skills"},
    "roles": {"rows_key": "records", "id_key": "record_id", "gold_key": "gold_role"},
    "dedup": {"rows_key": "pairs", "id_key": "pair_id", "gold_key": "gold_duplicate"},
}
_WRITE_LOCK = threading.RLock()

_ROLE_LABELS_ZH = {
    "bi_analyst": "BI 分析师",
    "business_analyst": "业务分析师",
    "data_scientist": "数据科学家",
    "data_engineer": "数据工程师",
    "analytics_engineer": "分析工程师",
    "llm_engineer": "大语言模型工程师",
    "mlops_engineer": "MLOps 工程师",
    "ml_engineer": "机器学习工程师",
    "ai_engineer": "AI 工程师",
    "data_analyst": "数据分析师",
    "backend_engineer": "后端工程师",
    "frontend_engineer": "前端工程师",
    "fullstack_engineer": "全栈工程师",
    "cloud_engineer": "云工程师",
    "devops_engineer": "DevOps / 运维开发工程师",
    "security_engineer": "安全工程师",
    "software_engineer": "软件工程师",
    "technical_product_manager": "技术产品经理",
    "product_manager": "产品经理",
    "other": "其他",
}
_SKILL_CATEGORY_LABELS_ZH = {
    "programming": "编程语言",
    "database": "数据库",
    "data_analysis": "数据分析",
    "data_engineering": "数据工程",
    "ai_ml": "AI / 机器学习",
    "frontend": "前端技术",
    "backend": "后端技术",
    "devops": "DevOps / 工程工具",
    "cloud": "云平台",
    "visualization": "数据可视化",
    "testing": "测试",
    "product": "产品方法",
    "office": "办公工具",
    "statistics": "统计方法",
    "other": "其他技术",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"标注文件不存在：{path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AnnotationValidationError(f"标注文件根节点必须是 mapping：{path}")
    return payload


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = yaml.safe_dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


class AnnotationWorkspace:
    def __init__(
        self,
        *,
        benchmark_root: Path,
        skill_taxonomy_path: Path,
        role_taxonomy_path: Path,
        silver_path: Path | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.benchmark_root = benchmark_root
        self.skill_taxonomy_path = skill_taxonomy_path
        self.role_taxonomy_path = role_taxonomy_path
        self.silver_path = silver_path
        self.clock = clock or (lambda: datetime.now(UTC))
        skill_taxonomy = load_skill_taxonomy(skill_taxonomy_path)
        role_taxonomy = load_role_taxonomy(role_taxonomy_path)
        self.skill_options = {
            skill.skill_id: (
                f"{skill.canonical_name}  ·  "
                f"{_SKILL_CATEGORY_LABELS_ZH.get(skill.category, skill.category)}  ·  {skill.skill_id}"
            )
            for skill in skill_taxonomy.skills
        }
        self.role_options = tuple(role.id for role in role_taxonomy.roles)
        unknown_roles = sorted(set(self.role_options) - set(_ROLE_LABELS_ZH))
        extra_roles = sorted(set(_ROLE_LABELS_ZH) - set(self.role_options))
        if unknown_roles or extra_roles:
            raise AnnotationValidationError(
                f"岗位中文标签与当前 taxonomy 不一致：missing={unknown_roles}, extra={extra_roles}"
            )
        self.role_labels = {role_id: _ROLE_LABELS_ZH[role_id] for role_id in self.role_options}
        self.translation_store = TranslationHelperStore(benchmark_root / "annotation_helpers")
        self.state_path = benchmark_root / ".annotation_state.yml"
        self._silver_index: dict[str, dict[str, Any]] | None = None

    def _paths(self, kind: AnnotationKind) -> tuple[Path, Path]:
        return (
            self.benchmark_root / kind / "pending" / "batch.yml",
            self.benchmark_root / kind / "gold.yml",
        )

    def _rows(self, kind: AnnotationKind, *, gold: bool) -> list[dict[str, Any]]:
        pending_path, gold_path = self._paths(kind)
        payload = _load_yaml(gold_path if gold else pending_path)
        rows = payload.get(_CONFIG[kind]["rows_key"], [])
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise AnnotationValidationError(f"{kind} 标注记录必须是 mapping 列表")
        return rows

    def progress(self) -> dict[AnnotationKind, AnnotationProgress]:
        result: dict[AnnotationKind, AnnotationProgress] = {}
        for kind in ("skills", "roles", "dedup"):
            self.validate_integrity(kind)
            result[kind] = AnnotationProgress(
                completed=len(self._rows(kind, gold=True)),
                total=len(self._rows(kind, gold=False)),
            )
        return result

    def pending_samples(self, kind: AnnotationKind) -> list[dict[str, Any]]:
        id_key = _CONFIG[kind]["id_key"]
        completed_ids = {
            str(row.get(id_key)) for row in self._rows(kind, gold=True)
        }
        return [
            {
                "sample_id": str(row[id_key]),
                "completed": str(row[id_key]) in completed_ids,
            }
            for row in self._rows(kind, gold=False)
        ]

    def annotation(self, kind: AnnotationKind, sample_id: str) -> dict[str, Any] | None:
        id_key = _CONFIG[kind]["id_key"]
        return next(
            (dict(row) for row in self._rows(kind, gold=True) if str(row.get(id_key)) == sample_id),
            None,
        )

    def next_unannotated(self, kind: AnnotationKind) -> dict[str, Any] | None:
        id_key = _CONFIG[kind]["id_key"]
        completed = {str(row.get(id_key)) for row in self._rows(kind, gold=True)}
        for row in self._rows(kind, gold=False):
            sample_id = str(row.get(id_key))
            if sample_id not in completed:
                return self.presented_sample(kind, sample_id)
        return None

    def resume_sample_id(self, kind: AnnotationKind) -> str | None:
        pending_ids = [item["sample_id"] for item in self.pending_samples(kind)]
        state = self._load_state()
        remembered = str(state.get("current", {}).get(kind) or "")
        if remembered in pending_ids:
            return remembered
        next_sample = self.next_unannotated(kind)
        return str(next_sample["sample_id"]) if next_sample else (pending_ids[0] if pending_ids else None)

    def remember_position(self, kind: AnnotationKind, sample_id: str) -> None:
        if sample_id not in {item["sample_id"] for item in self.pending_samples(kind)}:
            raise AnnotationValidationError(f"未知的 {kind} sample_id：{sample_id}")
        with _WRITE_LOCK:
            state = self._load_state()
            current = dict(state.get("current") or {})
            current[kind] = sample_id
            _atomic_write_yaml(self.state_path, {"current": current})

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {"current": {}}
        return _load_yaml(self.state_path)

    def presented_sample(self, kind: AnnotationKind, sample_id: str) -> dict[str, Any]:
        row = self._pending_row(kind, sample_id)
        if kind == "skills":
            title = str(row.get("title") or "")
            description = str(row.get("description") or "")
            translation = self.translation_store.get(
                "skills", sample_id, title=title, description=description
            )
            return {
                "sample_id": sample_id,
                "title": title,
                "description": description,
                "source": str(row.get("source") or ""),
                "prediction": list(row.get("predicted_skills") or []),
                "prediction_is_gold": False,
                "translation": translation.model_dump(mode="json") if translation else None,
            }
        if kind == "roles":
            title = str(row.get("title") or "")
            description = str(row.get("description_excerpt") or "")
            translation = self.translation_store.get(
                "roles", sample_id, title=title, description=description
            )
            return {
                "sample_id": sample_id,
                "title": title,
                "description": description,
                "source": str(row.get("source") or ""),
                "prediction": str(row.get("predicted_role") or ""),
                "prediction_is_gold": False,
                "translation": translation.model_dump(mode="json") if translation else None,
            }
        left = self._job_details(str(row.get("left_job_id") or ""))
        right = self._job_details(str(row.get("right_job_id") or ""))
        translation = self.translation_store.get_dedup(
            sample_id,
            left_title=str(left.get("title") or ""),
            left_description=str(left.get("description") or ""),
            right_title=str(right.get("title") or ""),
            right_description=str(right.get("description") or ""),
        )
        return {
            "sample_id": sample_id,
            "prediction": bool(row.get("predicted_duplicate")),
            "prediction_is_gold": False,
            "left": left,
            "right": right,
            "different_fields": [key for key in left if left.get(key) != right.get(key)],
            "translation": translation.model_dump(mode="json") if translation else None,
        }

    def _pending_row(self, kind: AnnotationKind, sample_id: str) -> dict[str, Any]:
        id_key = _CONFIG[kind]["id_key"]
        matches = [row for row in self._rows(kind, gold=False) if str(row.get(id_key)) == sample_id]
        if not matches:
            raise AnnotationValidationError(f"未知的 {kind} sample_id：{sample_id}")
        if len(matches) > 1:
            raise AnnotationValidationError(f"待标注批次存在重复 sample_id：{sample_id}")
        return matches[0]

    def _job_details(self, job_id: str) -> dict[str, Any]:
        if self.silver_path is None or not self.silver_path.is_file():
            return {"job_id": job_id, "details": "Silver dataset unavailable"}
        if self._silver_index is None:
            frame = pl.read_parquet(self.silver_path)
            id_column = "silver_job_id" if "silver_job_id" in frame.columns else "job_id"
            self._silver_index = {
                str(row.get(id_column)): row for row in frame.to_dicts()
            }
        row = self._silver_index.get(job_id, {})
        return {
            "job_id": job_id,
            "company": row.get("company_name_normalized") or row.get("company_name_raw"),
            "title": row.get("job_title_raw") or row.get("job_title_normalized"),
            "role": row.get("role_id"),
            "city": row.get("city_raw") or row.get("city_code"),
            "salary": row.get("salary_raw"),
            "posted_at": row.get("posted_at") or row.get("published_at"),
            "source": row.get("source_id"),
            "description": row.get("job_description_raw"),
        }

    def save_skill(
        self,
        sample_id: str,
        gold_skills: Sequence[str],
        *,
        annotator: str,
        ambiguous: bool,
        notes: str,
        human_confirmed: bool,
    ) -> None:
        unknown = sorted(set(gold_skills) - set(self.skill_options))
        if unknown:
            raise AnnotationValidationError(f"未知的技能 ID：{unknown}")
        self._save(
            "skills",
            sample_id,
            list(dict.fromkeys(gold_skills)),
            annotator=annotator,
            ambiguous=ambiguous,
            notes=notes,
            human_confirmed=human_confirmed,
        )

    def save_role(
        self,
        sample_id: str,
        gold_role: str,
        *,
        annotator: str,
        ambiguous: bool,
        notes: str,
        human_confirmed: bool,
    ) -> None:
        if gold_role not in self.role_options:
            raise AnnotationValidationError(f"未知的岗位类别：{gold_role}")
        self._save(
            "roles",
            sample_id,
            gold_role,
            annotator=annotator,
            ambiguous=ambiguous,
            notes=notes,
            human_confirmed=human_confirmed,
        )

    def save_dedup(
        self,
        sample_id: str,
        gold_duplicate: bool,
        *,
        annotator: str,
        ambiguous: bool,
        notes: str,
        human_confirmed: bool,
    ) -> None:
        if type(gold_duplicate) is not bool:
            raise AnnotationValidationError("重复岗位 Gold 标签必须是布尔值")
        self._save(
            "dedup",
            sample_id,
            gold_duplicate,
            annotator=annotator,
            ambiguous=ambiguous,
            notes=notes,
            human_confirmed=human_confirmed,
        )

    def _save(
        self,
        kind: AnnotationKind,
        sample_id: str,
        gold_value: object,
        *,
        annotator: str,
        ambiguous: bool,
        notes: str,
        human_confirmed: bool,
    ) -> None:
        if not human_confirmed:
            raise AnnotationValidationError("保存 Gold 前必须明确进行人工确认")
        if not annotator.strip():
            raise AnnotationValidationError("标注人不能为空")
        pending = self._pending_row(kind, sample_id)
        id_key = _CONFIG[kind]["id_key"]
        gold_key = _CONFIG[kind]["gold_key"]
        rows_key = _CONFIG[kind]["rows_key"]
        _, gold_path = self._paths(kind)

        with _WRITE_LOCK:
            self.validate_integrity(kind)
            payload = _load_yaml(gold_path)
            rows = list(payload.get(rows_key) or [])
            existing_index = next(
                (index for index, row in enumerate(rows) if str(row.get(id_key)) == sample_id),
                None,
            )
            existing = rows[existing_index] if existing_index is not None else None
            now = self.clock().astimezone(UTC).isoformat()
            row = self._gold_row(kind, pending)
            row[gold_key] = gold_value
            row.update(
                {
                    "annotator": annotator.strip(),
                    "annotation_notes": notes.strip(),
                    "annotated_at": existing.get("annotated_at", now) if existing else now,
                    "updated_at": now,
                    "annotation_version": int(existing.get("annotation_version", 0)) + 1 if existing else 1,
                    "ambiguous": bool(ambiguous),
                    "human_confirmed": True,
                }
            )
            if existing_index is None:
                rows.append(row)
            else:
                rows[existing_index] = row
            metadata = dict(payload.get("metadata") or {})
            metadata["label_count"] = len(rows)
            payload["metadata"] = metadata
            payload[rows_key] = rows
            _atomic_write_yaml(gold_path, payload)

    @staticmethod
    def _gold_row(kind: AnnotationKind, pending: dict[str, Any]) -> dict[str, Any]:
        if kind == "skills":
            keys = (
                "record_id", "title", "description", "source", "language",
                "negative_terms", "difficulty", "split",
            )
        elif kind == "roles":
            keys = (
                "record_id", "title", "description_excerpt", "source",
                "difficulty", "split",
            )
        else:
            keys = (
                "pair_id", "left_job_id", "right_job_id", "difficulty",
                "reason", "source_pair", "split",
            )
        return {key: pending.get(key) for key in keys}

    def validate_integrity(self, kind: AnnotationKind) -> None:
        id_key = _CONFIG[kind]["id_key"]
        pending_ids = [str(row.get(id_key) or "") for row in self._rows(kind, gold=False)]
        gold_rows = self._rows(kind, gold=True)
        gold_ids = [str(row.get(id_key) or "") for row in gold_rows]
        if len(pending_ids) != len(set(pending_ids)):
            raise AnnotationValidationError(f"{kind} 存在重复的待标注 ID")
        if len(gold_ids) != len(set(gold_ids)):
            raise AnnotationValidationError(f"{kind} 存在重复 Gold ID")
        orphan_ids = sorted(set(gold_ids) - set(pending_ids))
        if orphan_ids:
            raise AnnotationValidationError(f"{kind} 存在孤立 Gold ID：{orphan_ids}")
        pending_by_id = {str(row.get(id_key)): row for row in self._rows(kind, gold=False)}
        for gold in gold_rows:
            pending = pending_by_id[str(gold.get(id_key))]
            if kind == "dedup" and (
                gold.get("left_job_id") != pending.get("left_job_id")
                or gold.get("right_job_id") != pending.get("right_job_id")
            ):
                raise AnnotationValidationError(f"{kind} sample_id 不匹配：{gold.get(id_key)}")
            if gold.get("split") != pending.get("split"):
                raise AnnotationValidationError(f"{kind} split 不匹配：{gold.get(id_key)}")
