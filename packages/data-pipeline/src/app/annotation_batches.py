from __future__ import annotations

import hashlib
import itertools
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, TypeVar

import polars as pl
import yaml
from pydantic import BaseModel, ConfigDict, Field
from rapidfuzz import fuzz

from app.target_market import load_target_market_config
from app.config import load_role_taxonomy
from app.normalization import normalize_role
from app.skill_extraction import RuleSkillExtractor
from app.skill_taxonomy import load_skill_taxonomy


class AnnotationBatchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_row_count: int = Field(ge=0)
    role_sample_count: int = Field(ge=0)
    skill_sample_count: int = Field(ge=0)
    dedup_pair_count: int = Field(ge=0)
    role_output: str
    skill_output: str
    dedup_output: str


T = TypeVar("T")


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _split(record_id: str, seed: int) -> str:
    return "development" if int(_hash(f"{seed}:{record_id}")[:8], 16) % 10 < 3 else "held_out_test"


def _round_robin(buckets: list[list[T]], limit: int) -> list[T]:
    selected: list[T] = []
    for group in itertools.zip_longest(*buckets):
        selected.extend(item for item in group if item is not None)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _language(text: str) -> str:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if chinese and latin:
        return "mixed"
    if chinese:
        return "zh"
    if latin:
        return "en"
    return "other"


def _sanitize_text(value: str) -> str:
    value = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[EMAIL REDACTED]", value, flags=re.I)
    value = re.sub(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)", "[PHONE REDACTED]", value)
    return value


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
    )


def prepare_annotation_batches(
    silver_path: Path,
    benchmark_root: Path,
    quality_config_path: Path,
    *,
    role_count: int = 120,
    skill_count: int = 120,
    dedup_pair_count: int = 120,
    split_seed: int = 42,
    annotation_type: Literal["skills", "roles", "dedup"] | None = None,
    output: Path | None = None,
) -> AnnotationBatchReport:
    rows = pl.read_parquet(silver_path).to_dicts()
    rows = sorted(rows, key=lambda row: _hash(_text(row.get("silver_job_id"))))
    target_config = load_target_market_config(quality_config_path)
    repository_root = Path(__file__).resolve().parents[4]
    role_taxonomy = load_role_taxonomy(repository_root / "data/reference/role_taxonomy.v1.json")
    skill_extractor = RuleSkillExtractor(load_skill_taxonomy(repository_root / "data/taxonomy/skills.yml"))
    role_buckets: dict[str, list[dict[str, Any]]] = {key: [] for key in ("target", "possible", "non_target")}
    for row in rows:
        category = target_config.classify_title(
            _text(row.get("job_title_raw")) or _text(row.get("job_title_normalized"))
        ).classification
        role_buckets[category].append(row)
    role_rows = _round_robin(list(role_buckets.values()), min(role_count, len(rows)))
    role_records = [
        {
            "record_id": _text(row.get("silver_job_id")),
            "title": _text(row.get("job_title_raw")) or _text(row.get("job_title_normalized")),
            "description_excerpt": _sanitize_text(_text(row.get("job_description_raw")))[:800],
            "source": _text(row.get("source_id")),
            "predicted_role": normalize_role(
                _text(row.get("job_title_raw")) or _text(row.get("job_title_normalized")), role_taxonomy
            ).role_id,
            "gold_role": None,
            "difficulty": "hard" if _text(row.get("role_id")) == "other" else "medium",
            "annotator": None,
            "annotation_notes": "",
            "split": _split(_text(row.get("silver_job_id")), split_seed),
        }
        for row in role_rows
    ]

    ambiguity_pattern = re.compile(r"(?<![A-Za-z0-9_])(?:R|C|C\+\+|Go|AI|ML|BI|CV|MD|SQL|JS|TS)(?![A-Za-z0-9_])", re.I)
    skill_rows = sorted(
        rows,
        key=lambda row: (
            not bool(ambiguity_pattern.search(_text(row.get("job_description_raw")))),
            -len(_text(row.get("job_description_raw"))),
            _hash(_text(row.get("silver_job_id"))),
        ),
    )[: min(skill_count, len(rows))]
    skill_records = [
        {
            "record_id": _text(row.get("silver_job_id")),
            "title": _text(row.get("job_title_raw")) or _text(row.get("job_title_normalized")),
            "description": _sanitize_text(_text(row.get("job_description_raw"))),
            "source": _text(row.get("source_id")),
            "language": _language(
                _text(row.get("job_title_raw")) + " " + _text(row.get("job_description_raw"))
            ),
            "predicted_skills": [
                match.skill_id for match in skill_extractor.extract(
                    _text(row.get("job_title_raw")) + "\n" + _text(row.get("job_description_raw"))
                )
            ],
            "gold_skills": None,
            "negative_terms": [],
            "difficulty": "hard" if ambiguity_pattern.search(_text(row.get("job_description_raw"))) else "medium",
            "annotator": None,
            "annotation_notes": "",
            "split": _split(_text(row.get("silver_job_id")), split_seed),
        }
        for row in skill_rows
    ]

    candidates: list[tuple[int, str, dict[str, Any], dict[str, Any], str]] = []
    for left, right in itertools.combinations(rows, 2):
        same_company = _text(left.get("company_name_normalized")) == _text(right.get("company_name_normalized"))
        different_source = _text(left.get("source_id")) != _text(right.get("source_id"))
        same_city = _text(left.get("city_code")) == _text(right.get("city_code"))
        left_title = _text(left.get("job_title_normalized"))
        right_title = _text(right.get("job_title_normalized"))
        same_title = bool(left_title and left_title == right_title)
        similarity = fuzz.ratio(left_title, right_title) if left_title and right_title else 0.0
        if same_company and same_title and same_city:
            priority, difficulty, reason = 0, "easy", "same normalized company, city and title"
        elif same_company and same_title and not same_city:
            priority, difficulty, reason = 1, "hard", "same company/title but different city"
        elif same_company and same_city and similarity >= 85:
            priority, difficulty, reason = 2, "hard", f"same company/city; title similarity={similarity:.1f}"
        elif same_company and similarity >= 75:
            priority, difficulty, reason = 3, "medium", f"same company; title similarity={similarity:.1f}"
        elif different_source and similarity >= 65:
            priority, difficulty, reason = -1, "hard", f"cross-source hard negative candidate; title similarity={similarity:.1f}"
        else:
            continue
        key = "|".join(sorted((_text(left.get("silver_job_id")), _text(right.get("silver_job_id")))))
        candidates.append((priority, _hash(key), left, right, f"{difficulty}|{reason}"))
    candidates.sort(key=lambda item: (item[0], item[1]))
    pair_buckets: dict[str, list[tuple[int, str, dict[str, Any], dict[str, Any], str]]] = {
        "easy": [], "medium": [], "hard": []
    }
    for candidate in candidates:
        pair_buckets[candidate[4].split("|", 1)[0]].append(candidate)
    selected_candidates = _round_robin(
        [pair_buckets["easy"], pair_buckets["medium"], pair_buckets["hard"]],
        dedup_pair_count,
    )
    pair_records = []
    for _, _, left, right, detail in selected_candidates:
        difficulty, reason = detail.split("|", 1)
        left_id = _text(left.get("silver_job_id"))
        right_id = _text(right.get("silver_job_id"))
        pair_records.append(
            {
                "pair_id": _hash("|".join(sorted((left_id, right_id))))[:24],
                "left_job_id": left_id,
                "right_job_id": right_id,
                "predicted_duplicate": difficulty == "easy",
                "gold_duplicate": None,
                "difficulty": difficulty,
                "reason": reason,
                "source_pair": f"{_text(left.get('source_id'))}|{_text(right.get('source_id'))}",
                "annotator": None,
                "annotation_notes": "",
                "split": _split("|".join(sorted((left_id, right_id))), split_seed),
            }
        )

    role_output = benchmark_root / "roles/pending/batch.yml"
    skill_output = benchmark_root / "skills/pending/batch.yml"
    dedup_output = benchmark_root / "dedup/pending/batch.yml"
    metadata = {
        "benchmark_version": "pending-2.0.0",
        "created_at": datetime.now(UTC).isoformat(),
        "label_count": 0,
        "split_seed": split_seed,
        "taxonomy_version": skill_extractor.taxonomy.version,
        "dedup_version": "1.1.0",
        "role_taxonomy_version": role_taxonomy.version,
    }
    if annotation_type in {None, "roles"}:
        _write_yaml(role_output, {"metadata": metadata, "records": role_records})
    if annotation_type in {None, "skills"}:
        _write_yaml(skill_output, {"metadata": metadata, "records": skill_records})
    if annotation_type in {None, "dedup"}:
        _write_yaml(dedup_output, {"metadata": metadata, "pairs": pair_records})
    if output is not None and annotation_type is not None:
        selected = {"roles": role_records, "skills": skill_records, "dedup": pair_records}[annotation_type]
        if output.suffix.lower() != ".jsonl":
            raise ValueError("annotation output must use .jsonl")
        _write_jsonl(output, selected)
    return AnnotationBatchReport(
        source_row_count=len(rows),
        role_sample_count=len(role_records),
        skill_sample_count=len(skill_records),
        dedup_pair_count=len(pair_records),
        role_output=str(role_output),
        skill_output=str(skill_output),
        dedup_output=str(dedup_output),
    )
