from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TypeVar
from zoneinfo import ZoneInfo

from skillworth_analytics import AnalyticsFilters
from skillworth_analytics.advanced import SkillTrendRecord, SkillTrendResult
from skillworth_analytics.analytics import SalaryBySkillRecord, SkillDemandResult
from skillworth_analytics.skill_relations import RecencyWindow

from .cache import CacheLookup, TTLCache
from .schemas import (
    ChinaSkillRelationsQuery,
    ChinaSkillRelationsResponse,
    ChinaSkillWorthQuery,
    ChinaSkillWorthSummaryResponse,
    DataQualityResponse,
    MarketSummaryResponse,
    RelatedSkillsResponse,
    RoleRecord,
    RolesResponse,
    SkillDetailResponse,
)
from .service import ApiService
from .settings import ApiSettings, REPOSITORY_ROOT


ARTIFACT_FORMAT = "skillworth_production_safe_aggregate_v1"
CLASSIFICATION = "PUBLIC_SAFE"
EXPECTED_FILES = {
    "artifact_metadata.json",
    "artifact_inventory.json",
    "skill_aggregates.json",
    "role_aggregates.json",
    "relation_aggregates.json",
    "quality_snapshot.json",
}
RELATION_WINDOW: RecencyWindow = "180d"
RECENCY_WINDOWS = ("90d", "180d", "365d", "all_active")
_WINDOW_TO_API = {"all_active": "all_active", "90d": "90d", "180d": "180d", "365d": "365d"}
_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
_PATH_PATTERN = re.compile(r"(?:[A-Za-z]:[\\/]|(?:^|[\\/])(?:Users|home|tmp)[\\/])")
_FORBIDDEN_KEYS = {
    "job_id",
    "canonical_job_id",
    "job_description",
    "full_job_description",
    "description_html",
    "source_url",
    "dataset_url",
    "license_url",
    "warehouse_path",
    "graph_edges_path",
    "quality_report_path",
}

T = TypeVar("T")


@dataclass(frozen=True)
class ProductionSafeArtifactAudit:
    classification: str
    snapshot: str
    job_count: int
    company_count: int
    skill_count: int
    parity: dict[str, int]
    restricted_findings: tuple[str, ...]
    files: tuple[dict[str, Any], ...]


def default_artifact_root() -> Path:
    return REPOSITORY_ROOT / "data/production-safe/current"


def build_production_safe_artifact(
    source_settings: ApiSettings,
    output_root: Path,
    *,
    generated_at: datetime | None = None,
) -> ProductionSafeArtifactAudit:
    """Serialise only existing public aggregate API outputs from a frozen Real snapshot."""
    if source_settings.data_mode != "real":
        raise ValueError("Production-safe artifact generation requires Real dataset mode")
    if output_root.exists():
        existing = {path.name for path in output_root.iterdir() if path.is_file()}
        if existing and existing != EXPECTED_FILES:
            raise FileExistsError("Refusing to overwrite an unexpected production-safe artifact file set")

    service = ApiService(source_settings)
    roles = service.roles()
    role_ids = tuple(record.role_id for record in roles.records)
    skill_catalog = service.skill_demand(AnalyticsFilters())
    aggregate_skills = _build_skill_aggregates(service, role_ids, skill_catalog)
    aggregate_roles = _build_role_aggregates(service, roles)
    relation_aggregates = _build_relation_aggregates(service, role_ids)
    quality_snapshot = service.data_quality().model_dump(mode="json")
    china_scopes = _build_china_skillworth_scopes(service, role_ids)
    default_scope = china_scopes[_china_key("180d", None)]
    source_snapshot = _source_snapshot(default_scope)

    timestamp = generated_at or datetime.now(ZoneInfo("Asia/Shanghai"))
    metadata = {
        "artifact_format": ARTIFACT_FORMAT,
        "classification": CLASSIFICATION,
        "source_snapshot": source_snapshot,
        "generated_at": timestamp.isoformat(timespec="seconds"),
        "market_scope": source_settings.market_scope,
        "source_role": source_settings.source_role,
        "access_date": source_settings.access_date.isoformat() if source_settings.access_date else None,
        "job_count": int(default_scope["job_count"]),
        "company_count": int(default_scope["company_count"]),
        "skill_count": int(default_scope["skill_count"]),
        "source_count": source_settings.source_count,
        "disclaimer": source_settings.disclaimer,
        "schema": {
            "skill_aggregates": ["market_summary", "market_trends", "skill_demand", "skill_details", "related_skills"],
            "role_aggregates": ["roles", "role_details"],
            "relation_aggregates": ["recency_window", "global_and_role_scopes", "skill_relation_records"],
            "quality_snapshot": ["data_quality"],
            "china_skillworth_scopes": ["recency_window", "role", "skill_aggregates", "robustness", "sensitivity"],
        },
    }
    skill_payload = {"china_skillworth_scopes": china_scopes, **aggregate_skills}
    files = {
        "artifact_metadata.json": metadata,
        "skill_aggregates.json": skill_payload,
        "role_aggregates.json": aggregate_roles,
        "relation_aggregates.json": relation_aggregates,
        "quality_snapshot.json": {"data_quality": quality_snapshot},
    }

    output_root.mkdir(parents=True, exist_ok=True)
    for name, payload in files.items():
        _write_json(output_root / name, payload)

    parity = _build_parity(skill_payload, relation_aggregates)
    inventory = {
        "artifact_format": ARTIFACT_FORMAT,
        "classification": CLASSIFICATION,
        "source_snapshot": source_snapshot,
        "generated_at": metadata["generated_at"],
        "files": tuple(_file_inventory(output_root / name, payload) for name, payload in files.items()),
        "parity": parity,
    }
    _write_json(output_root / "artifact_inventory.json", inventory)
    return audit_production_safe_artifact(output_root)


def audit_production_safe_artifact(root: Path) -> ProductionSafeArtifactAudit:
    if not root.is_dir():
        raise FileNotFoundError("Production-safe aggregate artifact is unavailable")
    present = {path.name for path in root.iterdir() if path.is_file()}
    if present != EXPECTED_FILES:
        raise FileNotFoundError("Production-safe aggregate artifact file set is invalid")

    metadata = _read_json(root / "artifact_metadata.json")
    inventory = _read_json(root / "artifact_inventory.json")
    if metadata.get("artifact_format") != ARTIFACT_FORMAT or inventory.get("artifact_format") != ARTIFACT_FORMAT:
        raise ValueError("Production-safe aggregate artifact format is unsupported")
    if metadata.get("classification") != CLASSIFICATION or inventory.get("classification") != CLASSIFICATION:
        raise ValueError("Production-safe aggregate artifact classification is invalid")

    findings = list(_restricted_content_findings(root))
    inventory_files = inventory.get("files")
    if not isinstance(inventory_files, list):
        findings.append("artifact_inventory.files is invalid")
        inventory_files = []
    for item in inventory_files:
        if not isinstance(item, dict):
            findings.append("artifact_inventory contains an invalid file entry")
            continue
        name = item.get("name")
        if name not in EXPECTED_FILES - {"artifact_inventory.json"}:
            findings.append("artifact_inventory names an unexpected file")
            continue
        file_path = root / str(name)
        if item.get("sha256") != _sha256(file_path):
            findings.append(f"sha256 mismatch: {name}")
        if item.get("size_bytes") != file_path.stat().st_size:
            findings.append(f"size mismatch: {name}")
        if item.get("row_count") != _row_count(_read_json(file_path)):
            findings.append(f"row count mismatch: {name}")

    return ProductionSafeArtifactAudit(
        classification=str(metadata["classification"]),
        snapshot=str(metadata["source_snapshot"]),
        job_count=int(metadata["job_count"]),
        company_count=int(metadata["company_count"]),
        skill_count=int(metadata["skill_count"]),
        parity={key: int(value) for key, value in dict(inventory["parity"]).items()},
        restricted_findings=tuple(findings),
        files=tuple(inventory_files),
    )


class ProductionSafeApiService:
    """Read-only API adapter over the checked-in aggregate artifact; it never opens Real files."""

    def __init__(self, settings: ApiSettings) -> None:
        self.settings = settings
        self._audit = audit_production_safe_artifact(settings.production_safe_artifact_path)
        self._root = settings.production_safe_artifact_path
        self._metadata = _read_json(self._root / "artifact_metadata.json")
        self._skills = _read_json(self._root / "skill_aggregates.json")
        self._roles = _read_json(self._root / "role_aggregates.json")
        self._relations = _read_json(self._root / "relation_aggregates.json")
        self._quality = _read_json(self._root / "quality_snapshot.json")
        self._cache = TTLCache(settings.cache_ttl_seconds)

    @property
    def data_available(self) -> bool:
        return self._audit.restricted_findings == ()

    def cached(self, key: str, loader: Callable[[], T]) -> CacheLookup[T]:
        return self._cache.get_or_load(key, loader)

    def market_summary(self, filters: AnalyticsFilters) -> MarketSummaryResponse:
        return MarketSummaryResponse.model_validate(self._scope_payload("market_summary", filters))

    def skill_demand(self, filters: AnalyticsFilters) -> SkillDemandResult:
        return SkillDemandResult.model_validate(self._scope_payload("skill_demand", filters))

    def market_trends(self, filters: AnalyticsFilters) -> SkillTrendResult:
        return SkillTrendResult.model_validate(self._scope_payload("market_trends", filters))

    def china_skillworth_summary(self, query: ChinaSkillWorthQuery) -> ChinaSkillWorthSummaryResponse:
        scope = self._china_scope(query.recency_window, query.role)
        records = [record for record in scope["records"] if _matches_china_query(record, query)]
        return ChinaSkillWorthSummaryResponse.model_validate({**scope, "records": records})

    def china_skill_relations(self, query: ChinaSkillRelationsQuery) -> ChinaSkillRelationsResponse:
        if query.market_scope is not None and query.market_scope != self._metadata["market_scope"]:
            raise ValueError("market_scope does not match the active dataset")
        if query.source_role is not None and query.source_role != self._metadata["source_role"]:
            raise ValueError("source_role does not match the active dataset")
        if query.recency_window != RELATION_WINDOW:
            raise FileNotFoundError("Requested relation aggregate is unavailable")
        key = _relation_key(query.core_skill_id, query.role_id)
        payload = self._relations["scopes"].get(key)
        if payload is None:
            raise FileNotFoundError("Requested relation aggregate is unavailable")
        return ChinaSkillRelationsResponse.model_validate(payload)

    def skill_detail(self, skill_id: str, filters: AnalyticsFilters) -> SkillDetailResponse | None:
        self._require_global_filters(filters)
        payload = self._skills["skill_details"].get(skill_id)
        return SkillDetailResponse.model_validate(payload) if payload is not None else None

    def skill_trend(self, skill_id: str, filters: AnalyticsFilters) -> SkillTrendRecord | None:
        detail = self.skill_detail(skill_id, filters)
        return detail.trend if detail else None

    def skill_salary(self, skill_id: str, filters: AnalyticsFilters) -> tuple[SalaryBySkillRecord | None, Any] | None:
        detail = self.skill_detail(skill_id, filters)
        if detail is None:
            return None
        return detail.salary_distribution, detail.adjusted_salary_association

    def related_skills(self, skill_id: str) -> RelatedSkillsResponse | None:
        payload = self._skills["related_skills"].get(skill_id)
        return RelatedSkillsResponse.model_validate(payload) if payload is not None else None

    def roles(self) -> RolesResponse:
        return RolesResponse.model_validate(self._roles["roles"])

    def role(self, role_id: str) -> RoleRecord | None:
        payload = self._roles["role_details"].get(role_id)
        return RoleRecord.model_validate(payload["role"]) if payload is not None else None

    def role_skill_demand(self, role_id: str) -> SkillDemandResult:
        payload = self._roles["role_details"].get(role_id)
        if payload is None:
            raise FileNotFoundError("Requested role aggregate is unavailable")
        return SkillDemandResult.model_validate(payload["skill_demand"])

    def sources(self):
        raise FileNotFoundError("Source-level data is intentionally excluded from the production-safe artifact")

    def data_quality(self) -> DataQualityResponse:
        return DataQualityResponse.model_validate(self._quality["data_quality"])

    def analyze_portfolio(self, request: Any):
        raise FileNotFoundError("Job-level portfolio analysis is intentionally unavailable in production-safe mode")

    def optimize_portfolio(self, request: Any):
        raise FileNotFoundError("Job-level portfolio analysis is intentionally unavailable in production-safe mode")

    def _scope_payload(self, section: str, filters: AnalyticsFilters) -> dict[str, Any]:
        _validate_supported_filters(filters)
        key = filters.role_id or "global"
        payload = self._skills[section].get(key)
        if payload is None:
            raise FileNotFoundError("Requested aggregate scope is unavailable")
        return payload

    def _require_global_filters(self, filters: AnalyticsFilters) -> None:
        _validate_supported_filters(filters)
        if filters.role_id is not None:
            raise FileNotFoundError("Requested aggregate scope is unavailable")

    def _china_scope(self, recency_window: str, role_id: str | None) -> dict[str, Any]:
        payload = self._skills["china_skillworth_scopes"].get(_china_key(recency_window, role_id))
        if payload is None:
            raise FileNotFoundError("Requested China SkillWorth aggregate scope is unavailable")
        return payload


def _build_skill_aggregates(service: ApiService, role_ids: tuple[str, ...], skills: SkillDemandResult) -> dict[str, Any]:
    scopes = ("global", *role_ids)
    filters = {scope: AnalyticsFilters() if scope == "global" else AnalyticsFilters(role_id=scope) for scope in scopes}
    return {
        "market_summary": {scope: service.market_summary(value).model_dump(mode="json") for scope, value in filters.items()},
        "market_trends": {scope: service.market_trends(value).model_dump(mode="json") for scope, value in filters.items()},
        "skill_demand": {scope: service.skill_demand(value).model_dump(mode="json") for scope, value in filters.items()},
        "skill_details": {
            record.skill_id: detail.model_dump(mode="json")
            for record in skills.records
            if (detail := service.skill_detail(record.skill_id, AnalyticsFilters())) is not None
        },
        "related_skills": {
            record.skill_id: related.model_dump(mode="json")
            for record in skills.records
            if (related := service.related_skills(record.skill_id)) is not None
        },
    }


def _build_role_aggregates(service: ApiService, roles: RolesResponse) -> dict[str, Any]:
    return {
        "roles": roles.model_dump(mode="json"),
        "role_details": {
            record.role_id: {
                "role": record.model_dump(mode="json"),
                "skill_demand": service.role_skill_demand(record.role_id).model_dump(mode="json"),
            }
            for record in roles.records
        },
    }


def _build_china_skillworth_scopes(service: ApiService, role_ids: tuple[str, ...]) -> dict[str, Any]:
    scopes: dict[str, Any] = {}
    for recency_window in RECENCY_WINDOWS:
        for role_id in (None, *role_ids):
            response = service.china_skillworth_summary(
                ChinaSkillWorthQuery(
                    eligibility="all",
                    robustness="all",
                    role=role_id,
                    recency_window=_WINDOW_TO_API[recency_window],
                )
            )
            payload = response.model_dump(mode="json")
            payload["snapshot"] = _source_snapshot(payload)
            scopes[_china_key(recency_window, role_id)] = payload
    return scopes


def _build_relation_aggregates(service: ApiService, role_ids: tuple[str, ...]) -> dict[str, Any]:
    global_scope = _read_china_scope_for_builder(service)
    source_snapshot = _source_snapshot(global_scope.model_dump(mode="json"))
    scopes: dict[str, Any] = {}
    for record in global_scope.records:
        for role_id in (None, *role_ids):
            response = service.china_skill_relations(
                ChinaSkillRelationsQuery(
                    core_skill_id=record.skill_id,
                    role_id=role_id,
                    recency_window=RELATION_WINDOW,
                )
            )
            payload = response.model_dump(mode="json")
            payload["snapshot"] = source_snapshot
            scopes[_relation_key(record.skill_id, role_id)] = payload
    return {"recency_window": RELATION_WINDOW, "scopes": scopes}


def _read_china_scope_for_builder(service: ApiService) -> ChinaSkillWorthSummaryResponse:
    return service.china_skillworth_summary(
        ChinaSkillWorthQuery(eligibility="all", robustness="all", recency_window="180d")
    )


def _build_parity(skill_payload: dict[str, Any], relations: dict[str, Any]) -> dict[str, int]:
    global_scope = skill_payload["china_skillworth_scopes"][_china_key("180d", None)]
    cpp = next(record for record in global_scope["records"] if record["skill_id"] == "programming_cpp")
    python_relations = relations["scopes"][_relation_key("programming_python", None)]["records"]
    python_sql = next(record for record in python_relations if record["related_skill_id"] == "database_sql")
    devops = skill_payload["china_skillworth_scopes"][_china_key("180d", "devops_engineer")]
    data_engineer = skill_payload["china_skillworth_scopes"][_china_key("180d", "data_engineer")]
    return {
        "cpp_demand_rank": int(cpp["demand_rank"]),
        "cpp_skillworth_rank": int(cpp["skillworth_rank"]),
        "python_sql_cooccurrence": int(python_sql["cooccurrence_count"]),
        "devops_sample_size": int(devops["job_count"]),
        "data_engineer_sample_size": int(data_engineer["job_count"]),
    }


def _scope_skill_count(scopes: dict[str, Any], recency_window: str, role_id: str | None) -> int:
    return int(scopes[_china_key(recency_window, role_id)]["skill_count"])


def _source_snapshot(scope: dict[str, Any]) -> str:
    snapshot_ids = {str(record["snapshot_id"]) for record in scope["records"]}
    if len(snapshot_ids) != 1:
        raise ValueError("China SkillWorth scope does not have one frozen source snapshot")
    return snapshot_ids.pop()


def _validate_supported_filters(filters: AnalyticsFilters) -> None:
    unsupported = filters.model_dump(exclude={"role_id"})
    if any(value not in (None, (), "target", "core") for value in unsupported.values()):
        raise ValueError("Production-safe mode supports only global or role aggregate scopes")


def _matches_china_query(record: dict[str, Any], query: ChinaSkillWorthQuery) -> bool:
    return (
        (query.eligibility == "all" or record["skillworth_eligibility"] == query.eligibility)
        and (query.robustness == "all" or record["robustness_level"] == query.robustness)
        and (query.skill_type is None or record["skill_type"] == query.skill_type)
    )


def _china_key(recency_window: str, role_id: str | None) -> str:
    return f"{recency_window}:{role_id or '__global__'}"


def _relation_key(core_skill_id: str, role_id: str | None) -> str:
    return f"{core_skill_id}:{role_id or '__global__'}"


def _file_inventory(path: Path, payload: Any) -> dict[str, Any]:
    return {"name": path.name, "row_count": _row_count(payload), "size_bytes": path.stat().st_size, "sha256": _sha256(path)}


def _row_count(payload: Any) -> int:
    if isinstance(payload, dict):
        if "records" in payload and isinstance(payload["records"], list):
            return len(payload["records"])
        return sum(_row_count(value) for value in payload.values())
    if isinstance(payload, list):
        return len(payload)
    return 1


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _restricted_content_findings(root: Path) -> tuple[str, ...]:
    findings: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            findings.append("artifact contains a non-file entry")
            continue
        if path.suffix != ".json":
            findings.append(f"artifact contains a non-JSON file: {path.name}")
            continue
        content = path.read_text(encoding="utf-8")
        if _URL_PATTERN.search(content):
            findings.append(f"URL content found: {path.name}")
        if _PATH_PATTERN.search(content):
            findings.append(f"local path content found: {path.name}")
        for key in _walk_keys(_read_json(path)):
            if key in _FORBIDDEN_KEYS:
                findings.append(f"restricted field found: {key}")
    return tuple(findings)


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Build the checked-in production-safe aggregate artifact from a local Real snapshot.")
    parser.add_argument("--output-root", type=Path, default=default_artifact_root())
    args = parser.parse_args()
    settings = ApiSettings.from_environment()
    audit = build_production_safe_artifact(settings, args.output_root)
    if audit.restricted_findings:
        raise RuntimeError("Production-safe artifact audit failed")


if __name__ == "__main__":
    _main()
