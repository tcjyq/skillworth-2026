from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

import polars as pl

from app.config import load_city_taxonomy, load_role_taxonomy
from app.normalization import (
    normalize_city,
    normalize_company,
    normalize_date,
    normalize_education,
    normalize_experience,
    normalize_job_title,
    normalize_role,
)
from app.quality import DataQualityReport, create_quality_report
from app.salary import parse_salary
from app.target_market import load_target_market_config


PIPELINE_VERSION = "0.4.0"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]

BRONZE_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "source_record_id": ("source_record_id", "native_record_id", "record_id"),
    "source_id": ("source_id",),
    "source_job_id": ("source_job_id", "native_job_id", "job_id"),
    "source_url": ("source_url", "job_url", "url"),
    "observed_at": ("observed_at", "observed_at_raw"),
    "ingestion_run_id": ("ingestion_run_id", "run_id"),
    "company_name": ("company_name", "company", "company_name_raw"),
    "job_title": ("job_title", "title", "job_title_raw"),
    "city": ("city", "location", "city_raw"),
    "education": ("education", "education_requirement", "education_raw"),
    "experience": ("experience", "experience_requirement", "experience_raw"),
    "salary": ("salary", "salary_raw"),
    "salary_currency": ("salary_currency", "currency"),
    "salary_native_min_monthly": ("salary_native_min_monthly",),
    "salary_native_min_hourly": ("salary_native_min_hourly",),
    "salary_native_min_daily": ("salary_native_min_daily",),
    "salary_raw_structured": ("salary_raw_structured",),
    "salary_currency_original": ("salary_currency_original",),
    "salary_rate_unit_original": ("salary_rate_unit_original",),
    "salary_min_normalized": ("salary_min_normalized",),
    "salary_max_normalized": ("salary_max_normalized",),
    "salary_mid_normalized": ("salary_mid_normalized",),
    "salary_normalization_method": ("salary_normalization_method",),
    "fx_rate": ("fx_rate",),
    "fx_rate_date": ("fx_rate_date",),
    "fx_source": ("fx_source",),
    "published_at": ("published_at", "publish_date", "date", "published_at_raw"),
    "job_description": ("job_description", "description", "job_description_raw"),
    "source_job_description": ("source_job_description",),
    "description_type": ("description_type",),
    "skill_evidence_source": ("skill_evidence_source",),
    "structured_skills_raw": ("structured_skills_raw", "skills_required"),
    "country_raw": ("country_raw", "country"),
    "geography_source": ("geography_source",),
    "upstream_source": ("upstream_source", "ats_source"),
    "upstream_external_id": ("upstream_external_id",),
    "source_company_slug": ("source_company_slug",),
    "api_accessed_at": ("api_accessed_at",),
    "source_payload_sha256": ("source_payload_sha256",),
    "source_category_raw": ("source_category_raw",),
}

SILVER_SCHEMA: dict[str, pl.DataType] = {
    "silver_job_id": pl.String,
    "source_record_id": pl.String,
    "source_id": pl.String,
    "source_job_id": pl.String,
    "source_url": pl.String,
    "observed_at": pl.String,
    "ingestion_run_id": pl.String,
    "company_name_raw": pl.String,
    "company_name_normalized": pl.String,
    "job_title_raw": pl.String,
    "job_title_normalized": pl.String,
    "role_id": pl.String,
    "role_parse_status": pl.String,
    "role_taxonomy_version": pl.String,
    "city_raw": pl.String,
    "city_code": pl.String,
    "city_parse_status": pl.String,
    "city_taxonomy_version": pl.String,
    "education_raw": pl.String,
    "education_band": pl.String,
    "education_parse_status": pl.String,
    "experience_raw": pl.String,
    "experience_min_years": pl.Float64,
    "experience_max_years": pl.Float64,
    "experience_band": pl.String,
    "experience_parse_status": pl.String,
    "salary_raw": pl.String,
    "salary_min_monthly": pl.Float64,
    "salary_max_monthly": pl.Float64,
    "salary_mid_monthly": pl.Float64,
    "salary_annualized": pl.Float64,
    "salary_months": pl.Int64,
    "salary_parse_status": pl.String,
    "salary_currency": pl.String,
    "salary_native_min_monthly": pl.Float64,
    "salary_native_min_hourly": pl.Float64,
    "salary_native_min_daily": pl.Float64,
    "salary_raw_structured": pl.String,
    "salary_currency_original": pl.String,
    "salary_rate_unit_original": pl.String,
    "salary_min_normalized": pl.Float64,
    "salary_max_normalized": pl.Float64,
    "salary_mid_normalized": pl.Float64,
    "salary_normalization_method": pl.String,
    "fx_rate": pl.Float64,
    "fx_rate_date": pl.String,
    "fx_source": pl.String,
    "published_at_raw": pl.String,
    "published_at": pl.Date,
    "date_parse_status": pl.String,
    "job_description_raw": pl.String,
    "source_job_description": pl.String,
    "description_type": pl.String,
    "skill_evidence_source": pl.String,
    "structured_skills_raw": pl.String,
    "country_raw": pl.String,
    "geography_source": pl.String,
    "upstream_source": pl.String,
    "upstream_external_id": pl.String,
    "source_company_slug": pl.String,
    "api_accessed_at": pl.String,
    "source_payload_sha256": pl.String,
    "source_category_raw": pl.String,
    "market_scope": pl.String,
    "market_scope_method": pl.String,
    "market_scope_version": pl.String,
    "record_status": pl.String,
    "quality_flags": pl.List(pl.String),
    "pipeline_version": pl.String,
}


class PipelineError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discover_inputs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise PipelineError(f"Bronze input does not exist: {input_path}")
    paths = sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".parquet"}
    )
    if not paths:
        raise PipelineError(f"No CSV or Parquet Bronze files found in: {input_path}")
    return paths


def _read_file(path: Path) -> pl.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pl.read_parquet(path)
    if suffix == ".csv":
        return pl.read_csv(path, infer_schema=False)
    raise PipelineError(f"Unsupported Bronze file type: {path.suffix}")


def _read_bronze(paths: Iterable[Path]) -> pl.DataFrame:
    frames = [_read_file(path) for path in paths]
    if not frames:
        raise PipelineError("Bronze input is empty")
    frame = pl.concat(frames, how="diagonal_relaxed") if len(frames) > 1 else frames[0]
    if frame.height == 0:
        raise PipelineError("Bronze input contains no records")
    return frame


def _canonicalize_bronze(frame: pl.DataFrame) -> pl.DataFrame:
    expressions: list[pl.Expr] = []
    for canonical_name, aliases in BRONZE_COLUMN_ALIASES.items():
        source_name = next((name for name in aliases if name in frame.columns), None)
        expression = (
            pl.col(source_name).cast(pl.String, strict=False)
            if source_name is not None
            else pl.lit(None, dtype=pl.String)
        )
        expressions.append(expression.alias(canonical_name))
    return frame.select(expressions)


def _silver_id(row: dict[str, str | None], row_number: int) -> str:
    identity_parts = [
        str(row.get(field) or "")
        for field in ("source_id", "ingestion_run_id", "source_record_id")
    ]
    identity = "|".join(identity_parts)
    if not all(identity_parts):
        identity = f"{identity}|row:{row_number}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return f"silver_{digest}"


def _normalize_rows(
    bronze: pl.DataFrame,
    role_taxonomy_path: Path,
    city_taxonomy_path: Path,
) -> pl.DataFrame:
    role_taxonomy = load_role_taxonomy(role_taxonomy_path)
    city_taxonomy = load_city_taxonomy(city_taxonomy_path)
    market_config = load_target_market_config(REPOSITORY_ROOT / "data/reference/target_market.v1.yml")
    rows: list[dict[str, object]] = []

    for row_number, row in enumerate(bronze.iter_rows(named=True)):
        company = normalize_company(row["company_name"])
        title = normalize_job_title(row["job_title"])
        role = normalize_role(row["job_title"], role_taxonomy)
        city = normalize_city(row["city"], city_taxonomy)
        education = normalize_education(row["education"])
        experience = normalize_experience(row["experience"])
        salary = parse_salary(row["salary"])
        published = normalize_date(row["published_at"])
        market_scope = market_config.classify_title(row["job_title"])

        quality_flags: list[str] = []
        required_provenance = ("source_record_id", "source_id", "ingestion_run_id")
        if any(not row[field] for field in required_provenance):
            quality_flags.append("missing_provenance")
        if company is None:
            quality_flags.append("missing_company")
        if title is None:
            quality_flags.append("missing_job_title")
        if role.role_parse_status != "parsed":
            quality_flags.append("role_unparsed")
        if city.city_parse_status != "parsed":
            quality_flags.append("city_unparsed")
        if education.education_parse_status != "parsed":
            quality_flags.append("education_unparsed")
        if experience.experience_parse_status != "parsed":
            quality_flags.append("experience_unparsed")
        if not salary.salary_parse_status.startswith("parsed_"):
            quality_flags.append("salary_unparsed")
        if published.date_parse_status != "parsed":
            quality_flags.append("date_unparsed")

        structurally_invalid = "missing_provenance" in quality_flags or title is None
        rows.append(
            {
                "silver_job_id": _silver_id(row, row_number),
                "source_record_id": row["source_record_id"],
                "source_id": row["source_id"],
                "source_job_id": row["source_job_id"],
                "source_url": row["source_url"],
                "observed_at": row["observed_at"],
                "ingestion_run_id": row["ingestion_run_id"],
                "company_name_raw": row["company_name"],
                "company_name_normalized": company,
                "job_title_raw": row["job_title"],
                "job_title_normalized": title,
                "role_id": role.role_id,
                "role_parse_status": role.role_parse_status,
                "role_taxonomy_version": role.taxonomy_version,
                "city_raw": row["city"],
                "city_code": city.city_code,
                "city_parse_status": city.city_parse_status,
                "city_taxonomy_version": city.taxonomy_version,
                "education_raw": row["education"],
                "education_band": education.education_band,
                "education_parse_status": education.education_parse_status,
                "experience_raw": row["experience"],
                "experience_min_years": experience.experience_min_years,
                "experience_max_years": experience.experience_max_years,
                "experience_band": experience.experience_band,
                "experience_parse_status": experience.experience_parse_status,
                "salary_raw": salary.salary_raw,
                "salary_min_monthly": salary.salary_min_monthly,
                "salary_max_monthly": salary.salary_max_monthly,
                "salary_mid_monthly": salary.salary_mid_monthly,
                "salary_annualized": salary.salary_annualized,
                "salary_months": salary.salary_months,
                "salary_parse_status": salary.salary_parse_status,
                "salary_currency": row["salary_currency"],
                "salary_native_min_monthly": row["salary_native_min_monthly"],
                "salary_native_min_hourly": row["salary_native_min_hourly"],
                "salary_native_min_daily": row["salary_native_min_daily"],
                "salary_raw_structured": row["salary_raw_structured"],
                "salary_currency_original": row["salary_currency_original"],
                "salary_rate_unit_original": row["salary_rate_unit_original"],
                "salary_min_normalized": row["salary_min_normalized"],
                "salary_max_normalized": row["salary_max_normalized"],
                "salary_mid_normalized": row["salary_mid_normalized"],
                "salary_normalization_method": row["salary_normalization_method"],
                "fx_rate": row["fx_rate"],
                "fx_rate_date": row["fx_rate_date"],
                "fx_source": row["fx_source"],
                "published_at_raw": row["published_at"],
                "published_at": published.published_at,
                "date_parse_status": published.date_parse_status,
                "job_description_raw": row["job_description"],
                "source_job_description": row["source_job_description"],
                "description_type": row["description_type"],
                "skill_evidence_source": row["skill_evidence_source"],
                "structured_skills_raw": row["structured_skills_raw"],
                "country_raw": row["country_raw"],
                "geography_source": row["geography_source"],
                "upstream_source": row["upstream_source"],
                "upstream_external_id": row["upstream_external_id"],
                "source_company_slug": row["source_company_slug"],
                "api_accessed_at": row["api_accessed_at"],
                "source_payload_sha256": row["source_payload_sha256"],
                "source_category_raw": row["source_category_raw"],
                "market_scope": market_scope.classification,
                "market_scope_method": "configured_title_rules",
                "market_scope_version": market_config.version,
                "record_status": "invalid" if structurally_invalid else "valid",
                "quality_flags": quality_flags,
                "pipeline_version": PIPELINE_VERSION,
            }
        )
    return pl.from_dicts(rows, schema=SILVER_SCHEMA, strict=False)


def build_silver(
    *,
    input_path: Path,
    output_path: Path,
    quality_report_path: Path,
    role_taxonomy_path: Path,
    city_taxonomy_path: Path,
) -> DataQualityReport:
    input_path = input_path.resolve()
    output_path = output_path.resolve()
    quality_report_path = quality_report_path.resolve()
    input_files = _discover_inputs(input_path)

    if any(output_path == path.resolve() for path in input_files):
        raise PipelineError("Silver output must not overwrite a Bronze input")
    if output_path.exists():
        raise FileExistsError(f"Silver output already exists: {output_path}")
    if quality_report_path.exists():
        raise FileExistsError(f"Quality report already exists: {quality_report_path}")

    hashes_before = {path: _sha256(path) for path in input_files}
    raw = _read_bronze(input_files)
    bronze = _canonicalize_bronze(raw)
    silver = _normalize_rows(bronze, role_taxonomy_path, city_taxonomy_path)
    report = create_quality_report(raw.height, silver)

    hashes_after = {path: _sha256(path) for path in input_files}
    if hashes_after != hashes_before:
        raise PipelineError("Bronze input changed during build; append-only contract violated")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    silver.write_parquet(output_path)
    report.write_json(quality_report_path)
    return report
