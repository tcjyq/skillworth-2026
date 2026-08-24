from __future__ import annotations

import json
from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict, Field


PARSED_SALARY_STATUSES = {
    "parsed_monthly",
    "parsed_monthly_with_months",
    "parsed_daily",
    "parsed_annual",
}


class DataQualityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_row_count: int = Field(ge=0)
    silver_row_count: int = Field(ge=0)
    missing_rate: float = Field(ge=0, le=1)
    missing_rate_by_field: dict[str, float]
    salary_parse_rate: float = Field(ge=0, le=1)
    role_parse_rate: float = Field(ge=0, le=1)
    city_parse_rate: float = Field(ge=0, le=1)
    invalid_record_rate: float = Field(ge=0, le=1)

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = self.model_dump(mode="json")
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def create_quality_report(raw_row_count: int, silver: pl.DataFrame) -> DataQualityReport:
    denominator = silver.height
    measured_fields = (
        "company_name_normalized",
        "job_title_normalized",
        "city_code",
        "education_band",
        "experience_band",
        "salary_mid_monthly",
        "published_at",
    )
    missing_by_field = {
        field: _rate(silver[field].null_count(), denominator)
        for field in measured_fields
    }
    missing_rate = (
        sum(missing_by_field.values()) / len(measured_fields)
        if measured_fields
        else 0.0
    )

    salary_parsed = silver.filter(
        pl.col("salary_parse_status").is_in(PARSED_SALARY_STATUSES)
    ).height
    role_parsed = silver.filter(pl.col("role_parse_status") == "parsed").height
    city_parsed = silver.filter(pl.col("city_parse_status") == "parsed").height
    invalid_records = silver.filter(pl.col("record_status") == "invalid").height

    return DataQualityReport(
        raw_row_count=raw_row_count,
        silver_row_count=denominator,
        missing_rate=missing_rate,
        missing_rate_by_field=missing_by_field,
        salary_parse_rate=_rate(salary_parsed, denominator),
        role_parse_rate=_rate(role_parsed, denominator),
        city_parse_rate=_rate(city_parsed, denominator),
        invalid_record_rate=_rate(invalid_records, denominator),
    )
