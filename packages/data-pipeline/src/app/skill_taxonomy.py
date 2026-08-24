from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


REQUIRED_SKILL_CATEGORIES = {
    "programming", "database", "data_analysis", "data_engineering", "ai_ml",
    "frontend", "backend", "devops", "cloud", "visualization", "testing",
    "product", "office", "statistics", "other",
}
SKILL_TYPES = {
    "programming_language", "database", "framework_library", "cloud_platform",
    "devops_tool", "data_tool", "ai_ml_technology", "technical_method",
    "security_technology", "frontend_technology", "backend_technology",
    "operating_system", "engineering_tool", "general_productivity_tool",
    "general_methodology", "broad_concept", "domain_knowledge", "other",
}
SKILLWORTH_ELIGIBILITY = {"main", "secondary", "excluded"}


class SkillSemanticRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_type: str
    skillworth_eligibility: str
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_enums(self) -> "SkillSemanticRule":
        if self.skill_type not in SKILL_TYPES:
            raise ValueError(f"unsupported skill_type: {self.skill_type}")
        if self.skillworth_eligibility not in SKILLWORTH_ELIGIBILITY:
            raise ValueError(
                f"unsupported skillworth_eligibility: {self.skillworth_eligibility}"
            )
        return self


class SkillDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_id: str = Field(min_length=1)
    canonical_name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    aliases: list[str]
    learning_hours_min: int = Field(ge=0)
    learning_hours_expected: int = Field(ge=0)
    learning_hours_max: int = Field(ge=0)
    learning_cost_source: str = Field(min_length=1)
    notes: str = Field(min_length=1)
    skill_type: str
    skillworth_eligibility: str
    skillworth_reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_learning_hours(self) -> "SkillDefinition":
        if not self.learning_hours_min <= self.learning_hours_expected <= self.learning_hours_max:
            raise ValueError("learning hours must satisfy min <= expected <= max")
        if self.skill_type not in SKILL_TYPES:
            raise ValueError(f"unsupported skill_type: {self.skill_type}")
        if self.skillworth_eligibility not in SKILLWORTH_ELIGIBILITY:
            raise ValueError(
                f"unsupported skillworth_eligibility: {self.skillworth_eligibility}"
            )
        return self


class SkillTaxonomy(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    learning_cost_methodology: str = Field(min_length=1)
    semantic_defaults: dict[str, SkillSemanticRule]
    semantic_overrides: dict[str, SkillSemanticRule] = Field(default_factory=dict)
    skills: list[SkillDefinition]

    @model_validator(mode="before")
    @classmethod
    def apply_semantic_rules(cls, payload: object) -> object:
        if not isinstance(payload, dict):
            return payload
        defaults = payload.get("semantic_defaults") or {}
        overrides = payload.get("semantic_overrides") or {}
        resolved = []
        for raw_skill in payload.get("skills") or []:
            skill = dict(raw_skill)
            rule = overrides.get(skill.get("skill_id")) or defaults.get(skill.get("category"))
            if not rule:
                raise ValueError(
                    f"missing semantic rule for skill_id={skill.get('skill_id')!r}"
                )
            skill["skill_type"] = rule["skill_type"]
            skill["skillworth_eligibility"] = rule["skillworth_eligibility"]
            skill["skillworth_reason"] = rule["reason"]
            resolved.append(skill)
        return dict(payload) | {"skills": resolved}

    @model_validator(mode="after")
    def validate_uniqueness(self) -> "SkillTaxonomy":
        ids = [skill.skill_id for skill in self.skills]
        if len(ids) != len(set(ids)):
            raise ValueError("skill_id values must be unique")
        names = [skill.canonical_name.casefold() for skill in self.skills]
        if len(names) != len(set(names)):
            raise ValueError("canonical_name values must be unique case-insensitively")
        terms: set[str] = set()
        for skill in self.skills:
            for term in [skill.canonical_name, *skill.aliases]:
                key = term.casefold()
                if key in terms:
                    raise ValueError(f"taxonomy term {term!r} is duplicated")
                terms.add(key)
        return self

    @property
    def alias_index(self) -> dict[str, SkillDefinition]:
        index: dict[str, SkillDefinition] = {}
        for skill in self.skills:
            for term in [skill.canonical_name, *skill.aliases]:
                key = term.casefold()
                index[key] = skill
        return index


def load_skill_taxonomy(path: Path) -> SkillTaxonomy:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Skill taxonomy root must be a mapping: {path}")
    taxonomy = SkillTaxonomy.model_validate(payload)
    missing_categories = REQUIRED_SKILL_CATEGORIES - {skill.category for skill in taxonomy.skills}
    if missing_categories:
        raise ValueError(f"Skill taxonomy is missing required categories: {sorted(missing_categories)}")
    return taxonomy
