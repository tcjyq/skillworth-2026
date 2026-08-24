from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


TranslationKind = Literal["skills", "roles", "dedup"]


class TranslationHelperError(ValueError):
    pass


class TranslationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(min_length=1)
    original_title_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    original_description_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    title_zh: str = Field(min_length=1)
    description_zh: str = Field(min_length=1)
    method: str = Field(min_length=1)
    model: str = Field(min_length=1)


class DedupTranslationEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(min_length=1)
    left: TranslationEntry
    right: TranslationEntry
    method: str = Field(min_length=1)
    model: str = Field(min_length=1)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_translation_record(
    *,
    kind: Literal["skills", "roles"],
    sample_id: str,
    title: str,
    description: str,
    title_zh: str,
    description_zh: str,
    method: str,
    model: str,
) -> dict[str, Any]:
    del kind
    return TranslationEntry(
        sample_id=sample_id,
        original_title_sha256=_hash(title),
        original_description_sha256=_hash(description),
        title_zh=title_zh,
        description_zh=description_zh,
        method=method,
        model=model,
    ).model_dump(mode="json")


def build_dedup_translation_record(
    *,
    sample_id: str,
    left_job_id: str,
    left_title: str,
    left_description: str,
    left_title_zh: str,
    left_description_zh: str,
    right_job_id: str,
    right_title: str,
    right_description: str,
    right_title_zh: str,
    right_description_zh: str,
    method: str,
    model: str,
) -> dict[str, Any]:
    def side(job_id: str, title: str, description: str, title_zh: str, description_zh: str) -> TranslationEntry:
        return TranslationEntry(
            sample_id=job_id,
            original_title_sha256=_hash(title),
            original_description_sha256=_hash(description),
            title_zh=title_zh,
            description_zh=description_zh,
            method=method,
            model=model,
        )

    return DedupTranslationEntry(
        sample_id=sample_id,
        left=side(left_job_id, left_title, left_description, left_title_zh, left_description_zh),
        right=side(right_job_id, right_title, right_description, right_title_zh, right_description_zh),
        method=method,
        model=model,
    ).model_dump(mode="json")


class TranslationHelperStore:
    def __init__(self, helper_root: Path) -> None:
        self.helper_root = helper_root
        self._records: dict[tuple[str, str], TranslationEntry | DedupTranslationEntry] = {}
        for kind in ("skills", "roles", "dedup"):
            path = helper_root / f"{kind}.jsonl"
            if not path.is_file():
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    record = (
                        DedupTranslationEntry.model_validate(payload)
                        if kind == "dedup"
                        else TranslationEntry.model_validate(payload)
                    )
                except (json.JSONDecodeError, ValueError) as error:
                    raise TranslationHelperError(f"翻译 helper 无效：{path}:{line_number}: {error}") from error
                key = (kind, record.sample_id)
                if key in self._records:
                    raise TranslationHelperError(f"翻译 helper 存在重复 sample_id：{kind}/{record.sample_id}")
                self._records[key] = record

    def get(
        self,
        kind: Literal["skills", "roles"],
        sample_id: str,
        *,
        title: str,
        description: str,
    ) -> TranslationEntry | None:
        record = self._records.get((kind, sample_id))
        if record is None:
            return None
        if not isinstance(record, TranslationEntry):
            raise TranslationHelperError(f"翻译 helper 类型错误：{kind}/{sample_id}")
        self._validate_text(record, title=title, description=description, label=f"{kind}/{sample_id}")
        return record

    def get_dedup(
        self,
        sample_id: str,
        *,
        left_title: str,
        left_description: str,
        right_title: str,
        right_description: str,
    ) -> DedupTranslationEntry | None:
        record = self._records.get(("dedup", sample_id))
        if record is None:
            return None
        if not isinstance(record, DedupTranslationEntry):
            raise TranslationHelperError(f"翻译 helper 类型错误：dedup/{sample_id}")
        self._validate_text(record.left, title=left_title, description=left_description, label=f"dedup/{sample_id}/left")
        self._validate_text(record.right, title=right_title, description=right_description, label=f"dedup/{sample_id}/right")
        return record

    @staticmethod
    def _validate_text(record: TranslationEntry, *, title: str, description: str, label: str) -> None:
        if record.original_title_sha256 != _hash(title) or record.original_description_sha256 != _hash(description):
            raise TranslationHelperError(f"翻译 helper 原文 hash 不匹配：{label}")

