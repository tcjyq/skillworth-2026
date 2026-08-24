from __future__ import annotations

from pathlib import Path
from typing import Any

import polars as pl
import yaml

from app.deduplication import (
    DEDUPLICATION_RULE_VERSION,
    AuditedPairDecisions,
    DeduplicationReport,
    deduplicate_records,
)
from app.canonical_merge import load_canonical_merge_config, merge_canonical_group


_REQUIRED_SILVER_COLUMNS = {
    "silver_job_id",
    "source_record_id",
    "source_id",
    "company_name_normalized",
    "job_title_normalized",
    "city_code",
    "role_id",
    "experience_band",
    "job_description_raw",
    "record_status",
}
_OPTIONAL_PROVENANCE_COLUMNS = (
    "source_job_id", "source_url", "observed_at", "job_title_raw",
    "education_band", "published_at", "salary_raw", "salary_mid_monthly", "salary_parse_status",
    "salary_min_monthly", "salary_max_monthly", "salary_annualized", "salary_months",
    "role_parse_status", "date_parse_status",
    "salary_currency", "salary_native_min_monthly", "market_scope",
    "market_scope_method", "market_scope_version",
    "upstream_source", "upstream_external_id", "source_company_slug",
    "api_accessed_at", "source_payload_sha256",
)
_CANONICAL_SCHEMA = {
    "canonical_job_id": pl.String,
    "canonical_silver_job_id": pl.String,
    "title_source_silver_job_id": pl.String,
    "description_source_silver_job_id": pl.String,
    "company_name_normalized": pl.String,
    "job_title_raw": pl.String,
    "job_title_normalized": pl.String,
    "role_id": pl.String,
    "city_code": pl.String,
    "experience_band": pl.String,
    "education_band": pl.String,
    "market_scope": pl.String,
    "market_scope_method": pl.String,
    "market_scope_version": pl.String,
    "published_at": pl.String,
    "first_posted_at": pl.String,
    "first_seen_at": pl.String,
    "last_seen_at": pl.String,
    "job_description_raw": pl.String,
    "salary_observations": pl.List(pl.Struct({
        "source": pl.String,
        "raw_salary": pl.String,
        "normalized_salary": pl.Float64,
        "currency": pl.String,
        "native_min_monthly": pl.Float64,
        "observed_at": pl.String,
    })),
    "canonical_salary": pl.Float64,
    "salary_mid_monthly": pl.Float64,
    "salary_source_count": pl.Int64,
    "salary_conflict_flag": pl.Boolean,
    "salary_months": pl.Int64,
    "salary_parse_status": pl.String,
    "group_size": pl.Int64,
    "deduplication_status": pl.String,
    "canonicalization_method": pl.String,
    "deduplication_rule_version": pl.String,
    "canonical_merge_version": pl.String,
}
_SOURCE_MAP_SCHEMA = {
    "canonical_job_id": pl.String,
    "silver_job_id": pl.String,
    "source_record_id": pl.String,
    "source_id": pl.String,
    "source_job_id": pl.String,
    "source_url": pl.String,
    "observed_at": pl.String,
    "upstream_source": pl.String,
    "upstream_external_id": pl.String,
    "source_company_slug": pl.String,
    "api_accessed_at": pl.String,
    "source_payload_sha256": pl.String,
    "match_method": pl.String,
    "match_score": pl.Float64,
    "match_reason": pl.String,
    "deduplication_rule_version": pl.String,
}


def _read_silver(path: Path) -> pl.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Silver input does not exist: {path}")
    frame = pl.read_parquet(path)
    missing = _REQUIRED_SILVER_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Silver input is missing columns: {sorted(missing)}")
    if "city_code" not in frame.columns and "city_raw" not in frame.columns:
        raise ValueError("Silver input requires city_code or city_raw")
    additions = [
        pl.lit(None, dtype=pl.String).alias(column)
        for column in _OPTIONAL_PROVENANCE_COLUMNS
        if column not in frame.columns
    ]
    return frame.with_columns(additions) if additions else frame


def _load_audited_decisions(path: Path | None) -> AuditedPairDecisions:
    if path is None:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("decisions"), list):
        raise ValueError("Audited dedup decisions require a decisions list")
    decisions: AuditedPairDecisions = {}
    for item in payload["decisions"]:
        if not isinstance(item, dict) or item.get("decision") not in {"same", "different"}:
            raise ValueError("Audited dedup decision must be same or different")
        identities = []
        for side in ("left", "right"):
            value = item.get(side)
            if not isinstance(value, dict) or not value.get("source_id") or not value.get("source_job_id"):
                raise ValueError("Audited dedup decision sides require source_id and source_job_id")
            identities.append((str(value["source_id"]), str(value["source_job_id"])))
        pair = frozenset(identities)
        if len(pair) != 2:
            raise ValueError("Audited dedup decision must reference two distinct source jobs")
        reason = str(item.get("reason") or "").strip()
        if not reason:
            raise ValueError("Audited dedup decision requires a reason")
        if pair in decisions:
            raise ValueError("Duplicate audited dedup decision pair")
        decisions[pair] = (str(item["decision"]), reason)
    return decisions


def _canonical_rows(
    groups: list[Any], source_maps: list[dict[str, Any]], merge_config_path: Path
) -> list[dict[str, Any]]:
    canonical_by_silver = {row["silver_job_id"]: row["canonical_job_id"] for row in source_maps}
    merge_config = load_canonical_merge_config(merge_config_path)
    rows: list[dict[str, Any]] = []
    for group in groups:
        representative = group.representative
        merged = merge_canonical_group(group.members, merge_config)
        rows.append(
            {
                "canonical_job_id": canonical_by_silver[representative["silver_job_id"]],
                **merged,
                "group_size": len(group.members),
                "deduplication_status": "merged" if len(group.members) > 1 else "unique",
                "canonicalization_method": group.method,
                "deduplication_rule_version": DEDUPLICATION_RULE_VERSION,
            }
        )
    return rows


def deduplicate_silver(
    *,
    input_path: Path,
    canonical_output_path: Path,
    source_map_output_path: Path,
    report_path: Path,
    merge_config_path: Path | None = None,
    audited_decisions_path: Path | None = None,
) -> DeduplicationReport:
    input_path = input_path.resolve()
    outputs = (canonical_output_path.resolve(), source_map_output_path.resolve(), report_path.resolve())
    if any(output == input_path for output in outputs):
        raise ValueError("Deduplication outputs must not overwrite Silver input")
    for output in outputs:
        if output.exists():
            raise FileExistsError(f"Deduplication output already exists: {output}")

    silver = _read_silver(input_path)
    result = deduplicate_records(
        list(silver.iter_rows(named=True)),
        audited_decisions=_load_audited_decisions(audited_decisions_path),
    )
    merge_config_path = merge_config_path or Path(__file__).resolve().parents[4] / "data/reference/canonical_merge.v1.yml"
    canonical = pl.from_dicts(
        _canonical_rows(result.groups, result.source_maps, merge_config_path),
        schema=_CANONICAL_SCHEMA,
        strict=False,
    )
    source_map = pl.from_dicts(result.source_maps, schema=_SOURCE_MAP_SCHEMA, strict=False)
    canonical_output_path.parent.mkdir(parents=True, exist_ok=True)
    source_map_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_parquet(canonical_output_path)
    source_map.write_parquet(source_map_output_path)
    result.report.write_json(report_path)
    return result.report
