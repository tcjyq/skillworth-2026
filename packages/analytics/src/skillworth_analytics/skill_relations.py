from __future__ import annotations

from datetime import date, timedelta
from math import log2
from pathlib import Path
from typing import Literal

import duckdb
import yaml
from pydantic import BaseModel, ConfigDict, Field


RecencyWindow = Literal["90d", "180d", "365d", "all_active"]
RelationEvidenceStatus = Literal[
    "supported",
    "small_role_sample",
    "insufficient_role_sample",
    "core_skill_not_observed",
]


class ExploratoryRelationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    minimum_cooccurrence_count: int = Field(ge=1)
    minimum_jaccard: float = Field(ge=0, le=1)
    role_normal_sample_size: int = Field(ge=4)
    role_small_sample_minimum: int = Field(ge=1)


class SkillRelationMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    methodology_version: str = "exploratory_skill_relations_v1"
    config_version: str
    canonical_job_denominator: str = "canonical_job_id"
    minimum_cooccurrence_count: int = Field(ge=1)
    minimum_jaccard: float = Field(ge=0, le=1)


class SkillRelationRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    core_skill_id: str
    related_skill_id: str
    related_skill: str
    related_skill_category: str
    role_id: str | None
    recency_window: RecencyWindow
    sample_size: int = Field(ge=0)
    core_job_count: int = Field(ge=0)
    related_job_count: int = Field(ge=0)
    cooccurrence_count: int = Field(ge=0)
    core_conditional_coverage: float = Field(ge=0, le=1)
    jaccard: float = Field(ge=0, le=1)
    pmi: float
    evidence_status: Literal["supported", "small_sample_supported"]


class SkillRelationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    core_skill_id: str
    role_id: str | None
    recency_window: RecencyWindow
    sample_size: int = Field(ge=0)
    core_job_count: int = Field(ge=0)
    evidence_status: RelationEvidenceStatus
    records: tuple[SkillRelationRecord, ...]
    metadata: SkillRelationMetadata
    limitations: tuple[str, ...] = ()


def load_exploratory_relation_config(path: Path) -> ExploratoryRelationConfig:
    return ExploratoryRelationConfig.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


class SkillRelationRepository:
    def __init__(self, database_path: Path, config: ExploratoryRelationConfig) -> None:
        self.database_path = database_path
        self.config = config

    def related_skills(
        self,
        *,
        core_skill_id: str,
        recency_window: RecencyWindow,
        as_of_date: date,
        role_id: str | None = None,
    ) -> SkillRelationResult:
        connection = duckdb.connect(str(self.database_path), read_only=True)
        try:
            job_ids = self._cohort_job_ids(
                connection,
                role_id=role_id,
                recency_window=recency_window,
                as_of_date=as_of_date,
            )
            sample_size = len(job_ids)
            metadata = SkillRelationMetadata(
                config_version=self.config.version,
                minimum_cooccurrence_count=self.config.minimum_cooccurrence_count,
                minimum_jaccard=self.config.minimum_jaccard,
            )
            if role_id is not None and sample_size < self.config.role_small_sample_minimum:
                return SkillRelationResult(
                    core_skill_id=core_skill_id,
                    role_id=role_id,
                    recency_window=recency_window,
                    sample_size=sample_size,
                    core_job_count=0,
                    evidence_status="insufficient_role_sample",
                    records=(),
                    metadata=metadata,
                    limitations=("当前岗位样本不足，暂不足以形成稳定排序。",),
                )
            skill_jobs = self._skill_jobs(connection, job_ids)
            core_jobs = skill_jobs.get(core_skill_id, set())
            if not core_jobs:
                return SkillRelationResult(
                    core_skill_id=core_skill_id,
                    role_id=role_id,
                    recency_window=recency_window,
                    sample_size=sample_size,
                    core_job_count=0,
                    evidence_status="core_skill_not_observed",
                    records=(),
                    metadata=metadata,
                    limitations=("当前范围内未观察到该技能。",),
                )
            if role_id is not None and sample_size < self.config.role_normal_sample_size:
                result_status: RelationEvidenceStatus = "small_role_sample"
                record_status: Literal["supported", "small_sample_supported"] = (
                    "small_sample_supported"
                )
                limitations = ("小样本，仅供方向参考",)
            else:
                result_status = "supported"
                record_status = "supported"
                limitations = ()
            catalog = {
                str(row[0]): (str(row[1]), str(row[2]))
                for row in connection.execute(
                    "SELECT skill_id, canonical_name, category FROM skills"
                ).fetchall()
            }
            records = []
            for related_skill_id, related_jobs in skill_jobs.items():
                if related_skill_id == core_skill_id or related_skill_id not in catalog:
                    continue
                cooccurrence_count = len(core_jobs & related_jobs)
                union_count = len(core_jobs | related_jobs)
                jaccard = cooccurrence_count / union_count if union_count else 0
                if (
                    cooccurrence_count < self.config.minimum_cooccurrence_count
                    or jaccard < self.config.minimum_jaccard
                ):
                    continue
                related_name, related_category = catalog[related_skill_id]
                records.append(
                    SkillRelationRecord(
                        core_skill_id=core_skill_id,
                        related_skill_id=related_skill_id,
                        related_skill=related_name,
                        related_skill_category=related_category,
                        role_id=role_id,
                        recency_window=recency_window,
                        sample_size=sample_size,
                        core_job_count=len(core_jobs),
                        related_job_count=len(related_jobs),
                        cooccurrence_count=cooccurrence_count,
                        core_conditional_coverage=cooccurrence_count / len(core_jobs),
                        jaccard=jaccard,
                        pmi=log2(
                            cooccurrence_count
                            * sample_size
                            / (len(core_jobs) * len(related_jobs))
                        ),
                        evidence_status=record_status,
                    )
                )
            records.sort(
                key=lambda item: (
                    -item.jaccard,
                    -item.cooccurrence_count,
                    item.related_skill_id,
                )
            )
            return SkillRelationResult(
                core_skill_id=core_skill_id,
                role_id=role_id,
                recency_window=recency_window,
                sample_size=sample_size,
                core_job_count=len(core_jobs),
                evidence_status=result_status,
                records=tuple(records),
                metadata=metadata,
                limitations=limitations,
            )
        finally:
            connection.close()

    @staticmethod
    def _cohort_job_ids(
        connection: duckdb.DuckDBPyConnection,
        *,
        role_id: str | None,
        recency_window: RecencyWindow,
        as_of_date: date,
    ) -> set[str]:
        clauses = []
        parameters: list[object] = []
        if role_id is not None:
            clauses.append("role_id = ?")
            parameters.append(role_id)
        if recency_window != "all_active":
            days = int(recency_window.removesuffix("d"))
            clauses.append("published_at BETWEEN ? AND ?")
            parameters.extend([as_of_date - timedelta(days=days), as_of_date])
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            f"SELECT DISTINCT canonical_job_id FROM jobs{where}", parameters
        ).fetchall()
        return {str(row[0]) for row in rows}

    @staticmethod
    def _skill_jobs(
        connection: duckdb.DuckDBPyConnection, job_ids: set[str]
    ) -> dict[str, set[str]]:
        if not job_ids:
            return {}
        sorted_job_ids = sorted(job_ids)
        placeholders = ",".join("?" for _ in sorted_job_ids)
        rows = connection.execute(
            "SELECT DISTINCT skill_id, canonical_job_id FROM job_skills "
            f"WHERE canonical_job_id IN ({placeholders})",
            sorted_job_ids,
        ).fetchall()
        output: dict[str, set[str]] = {}
        for skill_id, job_id in rows:
            output.setdefault(str(skill_id), set()).add(str(job_id))
        return output
