from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict

from app.skill_extraction import RuleSkillExtractor
from app.skill_taxonomy import load_skill_taxonomy


class SkillExtractionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    taxonomy_version: str
    skill_count: int
    job_count: int
    valid_job_count: int
    job_skill_relation_count: int


def _read_silver(path: Path) -> pl.DataFrame:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Silver input does not exist: {path}")
    frame = pl.read_parquet(path)
    required = {"silver_job_id", "job_description_raw"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Silver input is missing columns: {sorted(missing)}")
    if frame["silver_job_id"].null_count() or frame["silver_job_id"].n_unique() != frame.height:
        raise ValueError("Silver input silver_job_id values must be non-null and unique")
    return frame


def extract_skills(
    *,
    input_path: Path,
    taxonomy_path: Path,
    skills_output_path: Path,
    job_skills_output_path: Path,
) -> SkillExtractionReport:
    for output in (skills_output_path, job_skills_output_path):
        if output.exists():
            raise FileExistsError(f"Skill extraction output already exists: {output}")
        if output.resolve() == input_path.resolve():
            raise ValueError("Skill extraction output must not overwrite Silver input")

    taxonomy = load_skill_taxonomy(taxonomy_path)
    extractor = RuleSkillExtractor(taxonomy)
    silver = _read_silver(input_path)
    valid = silver.filter(pl.col("record_status") == "valid") if "record_status" in silver.columns else silver
    relation_rows: list[dict[str, object]] = []
    title_column = "job_title_raw" if "job_title_raw" in valid.columns else None
    for row in valid.iter_rows(named=True):
        matches_by_skill: dict[str, dict[str, object]] = {}
        structured = row.get("structured_skills_raw")
        if structured:
            try:
                raw_skills = json.loads(str(structured))
            except json.JSONDecodeError:
                raw_skills = []
            if isinstance(raw_skills, list):
                for raw_skill_value in raw_skills:
                    raw_skill = str(raw_skill_value).strip()
                    definition = taxonomy.alias_index.get(raw_skill.casefold())
                    if not raw_skill or definition is None:
                        continue
                    matches_by_skill[definition.skill_id] = {
                        "silver_job_id": row["silver_job_id"],
                        "skill_id": definition.skill_id,
                        "canonical_skill": definition.canonical_name,
                        "matched_text": raw_skill,
                        "extraction_method": "structured_taxonomy_alias",
                        "confidence": 0.85,
                        "taxonomy_version": taxonomy.version,
                        "raw_skill": raw_skill,
                        "mapping_method": "taxonomy_alias_exact",
                        "mapping_confidence": 0.85,
                        "evidence_type": "source_structured_skill",
                    }
        text_parts = [row.get("job_description_raw") or ""]
        if title_column:
            text_parts.append(row.get(title_column) or "")
        for match in extractor.extract("\n".join(text_parts)):
            matches_by_skill.setdefault(
                match.skill_id,
                {
                    "silver_job_id": row["silver_job_id"],
                    "skill_id": match.skill_id,
                    "canonical_skill": match.canonical_skill,
                    "matched_text": match.matched_text,
                    "extraction_method": match.extraction_method,
                    "confidence": match.confidence,
                    "taxonomy_version": taxonomy.version,
                    "raw_skill": match.matched_text,
                    "mapping_method": match.extraction_method,
                    "mapping_confidence": match.confidence,
                    "evidence_type": "qualification_or_title_text",
                },
            )
        relation_rows.extend(matches_by_skill.values())

    skills = pl.from_dicts(
        [skill.model_dump() | {"taxonomy_version": taxonomy.version} for skill in taxonomy.skills]
    )
    relation_schema = {
        "silver_job_id": pl.String,
        "skill_id": pl.String,
        "canonical_skill": pl.String,
        "matched_text": pl.String,
        "extraction_method": pl.String,
        "confidence": pl.Float64,
        "taxonomy_version": pl.String,
        "raw_skill": pl.String,
        "mapping_method": pl.String,
        "mapping_confidence": pl.Float64,
        "evidence_type": pl.String,
    }
    relations = pl.from_dicts(relation_rows, schema=relation_schema, strict=False)
    skills_output_path.parent.mkdir(parents=True, exist_ok=True)
    job_skills_output_path.parent.mkdir(parents=True, exist_ok=True)
    skills.write_parquet(skills_output_path)
    relations.write_parquet(job_skills_output_path)
    return SkillExtractionReport(
        taxonomy_version=taxonomy.version,
        skill_count=skills.height,
        job_count=silver.height,
        valid_job_count=valid.height,
        job_skill_relation_count=relations.height,
    )
