from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class RoleRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    patterns: tuple[str, ...]


class RoleTaxonomy(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    fallback_role: str
    roles: tuple[RoleRule, ...]

    @model_validator(mode="after")
    def validate_role_ids(self) -> "RoleTaxonomy":
        role_ids = [role.id for role in self.roles]
        if len(role_ids) != len(set(role_ids)):
            raise ValueError("role taxonomy contains duplicate ids")
        if self.fallback_role not in role_ids:
            raise ValueError("fallback_role must reference a configured role")
        return self


class CityRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    name: str
    aliases: tuple[str, ...]

    @field_validator("aliases")
    @classmethod
    def aliases_must_not_be_empty(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("city aliases must not be empty")
        return value


class CityTaxonomy(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str
    cities: tuple[CityRule, ...]

    @model_validator(mode="after")
    def validate_city_codes(self) -> "CityTaxonomy":
        codes = [city.code for city in self.cities]
        if len(codes) != len(set(codes)):
            raise ValueError("city taxonomy contains duplicate codes")
        return self


def _load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_role_taxonomy(path: Path) -> RoleTaxonomy:
    return RoleTaxonomy.model_validate(_load_json(path))


def load_city_taxonomy(path: Path) -> CityTaxonomy:
    return CityTaxonomy.model_validate(_load_json(path))
