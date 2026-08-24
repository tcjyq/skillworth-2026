from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.connectors import ConnectorReadResult


FREEHIRE_API_BASE = "https://freehire.me/api/v1"
FREEHIRE_CHINA_TECH_CATEGORIES = (
    "backend",
    "frontend",
    "fullstack",
    "data_engineering",
    "data_science",
    "data_analytics",
    "ml_ai",
    "ai_engineering",
    "devops",
    "sre",
    "security",
    "embedded",
    "hardware",
    "product",
    "business_analysis",
)
HttpGet = Callable[[str, dict[str, str]], tuple[int, dict[str, str], bytes]]


class FreehireApiJob(BaseModel):
    model_config = ConfigDict(extra="allow")

    public_slug: str = Field(min_length=1)
    source: str = Field(min_length=1)
    external_id: str | None = None
    url: str | None = None
    title: str = Field(min_length=1)
    company: str = Field(min_length=1)
    company_slug: str | None = None
    location: str | None = None
    description: str | None = None
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    posted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    enrichment: dict[str, Any] | None = None

    @field_validator("public_slug", "source", "title", "company")
    @classmethod
    def required_text_is_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("required Freehire text cannot be blank")
        return value


class FreehireSearchMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class FreehireSearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: list[dict[str, Any]]
    meta: FreehireSearchMeta


class FreehireSnapshotConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str = Field(pattern=r"^freehire_china_tech_\d{4}_\d{2}$")
    api_base: str = FREEHIRE_API_BASE
    country: str = "cn"
    categories: tuple[str, ...] = FREEHIRE_CHINA_TECH_CATEGORIES
    page_size: int = Field(default=100, ge=1, le=100)
    delay_seconds: float = Field(default=0.5, ge=0.1, le=60)
    maximum_retries: int = Field(default=4, ge=0, le=8)
    initial_backoff_seconds: float = Field(default=1, ge=0.1, le=60)
    request_timeout_seconds: float = Field(default=30, ge=1, le=120)

    @field_validator("api_base")
    @classmethod
    def public_api_must_use_https(cls, value: str) -> str:
        if not value.startswith("https://"):
            raise ValueError("Freehire public API must use HTTPS")
        return value.rstrip("/")

    @field_validator("categories")
    @classmethod
    def categories_must_be_audited(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or set(value) - set(FREEHIRE_CHINA_TECH_CATEGORIES):
            raise ValueError("Freehire categories must use the audited China technical set")
        return value


class FreehireSnapshotResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    source: str = "freehire_public_api"
    api_version: str = "v1"
    snapshot_started_at: datetime
    snapshot_completed_at: datetime
    api_query: str
    query_scope: dict[str, Any]
    raw_count: int = Field(ge=0)
    valid_count: int = Field(ge=0)
    rejected_count: int = Field(default=0, ge=0)
    canonical_count: int | None = Field(default=None, ge=0)
    company_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_schema: tuple[str, ...]
    artifact_path: Path
    metadata_path: Path
    cache_directory: Path
    usage_status: str = "no_explicit_block_found"
    warnings: tuple[str, ...] = (
        "live_api_snapshot_is_not_transactionally_atomic",
        "third_party_job_text_not_licensed_for_bulk_redistribution",
        "source_role_is_china_supplementary",
    )


class FreehirePublicApiConnector:
    """Consume only Freehire's documented, unauthenticated public read API."""

    def __init__(
        self,
        *,
        http_get: HttpGet | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http_get = http_get or self._default_http_get
        self._sleeper = sleeper
        self._request_timeout_seconds = 30.0

    def read(self, path: Path) -> pl.DataFrame:
        return self.read_result(path).frame

    def read_result(self, path: Path) -> ConnectorReadResult:
        path = path.resolve()
        if not path.is_file() or path.suffix.lower() != ".jsonl":
            raise ValueError("Freehire connector accepts only a local JSONL snapshot")
        mapped: list[dict[str, Any]] = []
        raw_count = 0
        rejected = 0
        # JSONL records may legally contain U+2028/U+2029 inside JSON strings;
        # str.splitlines() treats those characters as record separators.
        for line_number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
            if not line.strip():
                continue
            raw_count += 1
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("record is not an object")
                job = FreehireApiJob.model_validate(raw)
            except (json.JSONDecodeError, ValueError):
                rejected += 1
                continue
            enrichment = job.enrichment or {}
            salary_raw = self._salary_raw(enrichment)
            mapped.append(
                {
                    **raw,
                    "source_job_id": job.public_slug,
                    "source_url": self._text(job.url),
                    "company_name": job.company,
                    "job_title": job.title,
                    "city": self._city(job),
                    "education": self._text(enrichment.get("education_level")),
                    "experience": self._experience(enrichment),
                    "salary": None,
                    "salary_raw_structured": salary_raw,
                    "salary_currency_original": self._text(enrichment.get("salary_currency")),
                    "salary_rate_unit_original": self._text(enrichment.get("salary_period")),
                    "published_at": self._text(job.posted_at),
                    "job_description": self._text(job.description),
                    "description_type": "source_catalogue_full_description",
                    "skill_evidence_source": "source_structured_skills_and_job_text",
                    "structured_skills_raw": json.dumps(job.skills, ensure_ascii=False),
                    "country_raw": json.dumps(job.countries, ensure_ascii=False),
                    "geography_source": "freehire_structured_and_raw_location",
                    "upstream_source": job.source,
                    "upstream_external_id": self._text(job.external_id),
                    "source_company_slug": self._text(job.company_slug),
                    "api_accessed_at": self._text(raw.get("_skillworth_api_accessed_at")),
                    "source_payload_sha256": self._text(raw.get("_skillworth_payload_sha256")),
                    "source_category_raw": json.dumps(
                        enrichment.get("category"), ensure_ascii=False, default=str
                    ),
                }
            )
        frame = pl.from_dicts(mapped, infer_schema_length=None) if mapped else pl.DataFrame()
        return ConnectorReadResult(
            frame=frame,
            raw_record_count=raw_count,
            accepted_record_count=len(mapped),
            rejected_record_count=rejected,
            warnings=(
                "source_role_is_china_supplementary_not_core_market",
                "source_structured_skills_require_skillworth_taxonomy_mapping",
                "salary_is_preserved_as_source_structured_evidence_and_not_imputed",
                "third_party_job_text_must_not_be_bulk_redistributed",
            ),
        )

    def acquire_snapshot(
        self,
        output_root: Path,
        *,
        config: FreehireSnapshotConfig,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> FreehireSnapshotResult:
        snapshot_root = output_root.resolve() / config.snapshot_id
        cache_directory = snapshot_root / "cache/pages"
        artifact_path = snapshot_root / "raw/freehire_jobs.jsonl"
        metadata_path = snapshot_root / "snapshot_metadata.json"
        if metadata_path.is_file() and artifact_path.is_file():
            result = FreehireSnapshotResult.model_validate_json(
                metadata_path.read_text(encoding="utf-8")
            )
            if self._sha256(artifact_path) != result.content_sha256:
                raise ValueError("Completed Freehire snapshot content hash does not match metadata")
            return result

        cache_directory.mkdir(parents=True, exist_ok=True)
        started_at = now()
        self._request_timeout_seconds = config.request_timeout_seconds
        scope = {"countries": config.country, "category": list(config.categories)}
        base_params = {
            "countries": config.country,
            "category": ",".join(config.categories),
            "description_format": "html",
            "sort": "posted_at",
            "order": "desc",
            "limit": str(config.page_size),
        }
        query_without_page = f"{config.api_base}/agent/jobs/search?{urlencode(base_params)}"
        rows: list[dict[str, Any]] = []
        raw_count = 0
        rejected_count = 0
        observed_schema: set[str] = set()
        initial_total: int | None = None
        offset = 0
        while initial_total is None or offset < initial_total:
            page_path = cache_directory / f"page_{offset:06d}.json"
            if page_path.is_file():
                cached = json.loads(page_path.read_text(encoding="utf-8"))
                body = json.dumps(cached["response"], ensure_ascii=False).encode("utf-8")
                if hashlib.sha256(body).hexdigest() != cached["response_sha256"]:
                    raise ValueError(f"Freehire cache hash mismatch: {page_path}")
                response = FreehireSearchResponse.model_validate(cached["response"])
                accessed_at = str(cached["api_accessed_at"])
            else:
                params = {**base_params, "offset": str(offset)}
                url = f"{config.api_base}/agent/jobs/search?{urlencode(params)}"
                status, headers, payload = self._request_with_retry(url, config)
                if status != 200:
                    raise RuntimeError(f"Freehire API request failed with HTTP {status}")
                response_payload = json.loads(payload.decode("utf-8"))
                response = FreehireSearchResponse.model_validate(response_payload)
                accessed_at = now().isoformat()
                canonical_body = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
                self._write_json_atomic(
                    page_path,
                    {
                        "api_accessed_at": accessed_at,
                        "response_sha256": hashlib.sha256(canonical_body).hexdigest(),
                        "response_headers": {
                            key: value
                            for key, value in headers.items()
                            if key.casefold() in {"date", "etag", "last-modified", "retry-after"}
                        },
                        "response": response_payload,
                    },
                )
            if response.meta.offset != offset:
                raise ValueError("Freehire API returned an unexpected page offset")
            if initial_total is None:
                initial_total = response.meta.total
            raw_count += len(response.data)
            for raw in response.data:
                observed_schema.update(raw)
                try:
                    job = FreehireApiJob.model_validate(raw)
                except ValueError:
                    rejected_count += 1
                    continue
                canonical_payload = json.dumps(raw, sort_keys=True, ensure_ascii=False, default=str)
                rows.append(
                    {
                        **raw,
                        "_skillworth_api_accessed_at": accessed_at,
                        "_skillworth_payload_sha256": hashlib.sha256(
                            canonical_payload.encode("utf-8")
                        ).hexdigest(),
                        "_skillworth_validated_public_slug": job.public_slug,
                    }
                )
            if not response.data:
                break
            offset += config.page_size
            if initial_total is not None and offset < initial_total:
                self._sleeper(config.delay_seconds)

        unique_rows: dict[str, dict[str, Any]] = {}
        for row in rows:
            unique_rows.setdefault(str(row["public_slug"]), row)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_jsonl_atomic(artifact_path, unique_rows.values())
        content_hash = self._sha256(artifact_path)
        completed_at = now()
        result = FreehireSnapshotResult(
            snapshot_id=config.snapshot_id,
            snapshot_started_at=started_at,
            snapshot_completed_at=completed_at,
            api_query=query_without_page,
            query_scope=scope,
            raw_count=raw_count,
            valid_count=len(unique_rows),
            rejected_count=rejected_count,
            company_count=len(
                {
                    str(row.get("company_slug") or row.get("company"))
                    for row in unique_rows.values()
                    if row.get("company_slug") or row.get("company")
                }
            ),
            source_count=len(
                {str(row["source"]) for row in unique_rows.values() if row.get("source")}
            ),
            content_sha256=content_hash,
            observed_schema=tuple(sorted(observed_schema)),
            artifact_path=artifact_path,
            metadata_path=metadata_path,
            cache_directory=cache_directory,
        )
        self._write_text_atomic(metadata_path, result.model_dump_json(indent=2))
        return result

    def _request_with_retry(
        self, url: str, config: FreehireSnapshotConfig
    ) -> tuple[int, dict[str, str], bytes]:
        for attempt in range(config.maximum_retries + 1):
            try:
                status, headers, body = self._http_get(
                    url,
                    {
                        "Accept": "application/json",
                        "User-Agent": "SkillWorth-Live/0.1 (+source-audit; aggregate-analysis-only)",
                    },
                )
            except (OSError, URLError) as error:
                if attempt >= config.maximum_retries:
                    raise RuntimeError("Freehire API network request failed") from error
                self._sleeper(config.initial_backoff_seconds * (2**attempt))
                continue
            normalized_headers = {key.casefold(): value for key, value in headers.items()}
            if status == 429 or 500 <= status < 600:
                if attempt >= config.maximum_retries:
                    return status, normalized_headers, body
                retry_after = normalized_headers.get("retry-after")
                delay = self._retry_after_seconds(retry_after)
                self._sleeper(
                    delay
                    if delay is not None
                    else config.initial_backoff_seconds * (2**attempt)
                )
                continue
            return status, normalized_headers, body
        raise RuntimeError("Freehire retry loop ended unexpectedly")

    def _default_http_get(self, url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], bytes]:
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self._request_timeout_seconds) as response:
                return response.status, dict(response.headers.items()), response.read()
        except HTTPError as error:
            return error.code, dict(error.headers.items()), error.read()

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            return None

    @staticmethod
    def _city(job: FreehireApiJob) -> str | None:
        return FreehirePublicApiConnector._text(job.cities[0] if job.cities else job.location)

    @staticmethod
    def _experience(enrichment: dict[str, Any]) -> str | None:
        value = enrichment.get("experience_years_min")
        try:
            years = float(value)
        except (TypeError, ValueError):
            return FreehirePublicApiConnector._text(enrichment.get("seniority"))
        return "不限" if years <= 0 else f"{years:g}年以上"

    @staticmethod
    def _salary_raw(enrichment: dict[str, Any]) -> str | None:
        payload = {
            "min": enrichment.get("salary_min"),
            "max": enrichment.get("salary_max"),
            "currency": enrichment.get("salary_currency"),
            "period": enrichment.get("salary_period"),
        }
        if all(value is None for value in payload.values()):
            return None
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _text(value: object) -> str | None:
        text = "" if value is None else str(value).strip()
        return text or None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _write_text_atomic(path: Path, text: str) -> None:
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)

    @classmethod
    def _write_json_atomic(cls, path: Path, payload: dict[str, Any]) -> None:
        cls._write_text_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2))

    @classmethod
    def _write_jsonl_atomic(cls, path: Path, rows: Any) -> None:
        cls._write_text_atomic(
            path,
            "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in rows),
        )
