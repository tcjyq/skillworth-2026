from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from rapidfuzz import fuzz


DEDUPLICATION_RULE_VERSION = "1.1.0"
FUZZY_TITLE_THRESHOLD = 96.0
SIMHASH_TITLE_THRESHOLD = 90.0
SIMHASH_MAX_DISTANCE = 3
SAME_SOURCE_EXACT_DESCRIPTION_THRESHOLD = 95.0
_METHOD_RANK = {
    "level_1_exact": 1,
    "level_2_fuzzy_title": 2,
    "level_3_simhash_description": 3,
}
_SENIORITY_PATTERNS = {
    "intern": re.compile(r"实习|\bintern(?:ship)?\b", re.IGNORECASE),
    "junior": re.compile(r"初级|junior|应届|graduate", re.IGNORECASE),
    "senior": re.compile(r"高级|资深|senior", re.IGNORECASE),
    "lead": re.compile(r"专家|负责人|lead|principal|staff", re.IGNORECASE),
}
_FULL_TIME_PATTERN = re.compile(r"全职|full[- ]?time", re.IGNORECASE)
_BUSINESS_UNIT_PATTERN = re.compile(r"[（(\[【]([^）)\]】]+)[）)\]】]")
AuditedPairKey = frozenset[tuple[str, str]]
AuditedPairDecisions = dict[AuditedPairKey, tuple[str, str]]


class DeduplicationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    deduplication_rule_version: str
    raw_job_count: int = Field(ge=0)
    eligible_job_count: int = Field(ge=0)
    canonical_job_count: int = Field(ge=0)
    duplicate_group_count: int = Field(ge=0)
    deduplicated_job_count: int = Field(ge=0)
    dedup_rate: float = Field(ge=0.0, le=1.0)
    cross_platform_overlap_group_count: int = Field(ge=0)
    cross_platform_overlap_rate: float = Field(ge=0.0, le=1.0)
    match_method_counts: dict[str, int]

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


@dataclass(frozen=True, slots=True)
class PairMatch:
    method: str
    score: float
    reason: str


@dataclass(slots=True)
class DedupGroup:
    members: list[dict[str, Any]]
    member_matches: dict[str, PairMatch] = field(default_factory=dict)

    @property
    def representative(self) -> dict[str, Any]:
        return self.members[0]

    @property
    def method(self) -> str:
        if not self.member_matches:
            return "unique"
        return max(self.member_matches.values(), key=lambda match: _METHOD_RANK[match.method]).method


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    groups: list[DedupGroup]
    source_maps: list[dict[str, Any]]
    report: DeduplicationReport


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _city_key(record: dict[str, Any]) -> str:
    return _text(record.get("city_code")) or _text(record.get("city_raw")).casefold()


def _title(record: dict[str, Any]) -> str:
    return _text(record.get("job_title_normalized")).casefold()


def _description(record: dict[str, Any]) -> str:
    value = unicodedata.normalize("NFKC", _text(record.get("job_description_raw"))).casefold()
    return re.sub(r"\s+", "", value)


def _seniority(record: dict[str, Any]) -> str | None:
    title = " ".join((_text(record.get("job_title_raw")), _title(record)))
    for label, pattern in _SENIORITY_PATTERNS.items():
        if pattern.search(title):
            return label
    experience = _text(record.get("experience_band")).casefold()
    if experience and experience not in {"unlimited", "unknown"}:
        return experience
    return None


def _is_intern(record: dict[str, Any]) -> bool:
    return bool(_SENIORITY_PATTERNS["intern"].search(" ".join((_text(record.get("job_title_raw")), _description(record)))))


def _is_explicit_full_time(record: dict[str, Any]) -> bool:
    return bool(_FULL_TIME_PATTERN.search(" ".join((_text(record.get("job_title_raw")), _description(record)))))


def _business_unit(record: dict[str, Any]) -> str | None:
    title = _text(record.get("job_title_raw")) or _title(record)
    match = _BUSINESS_UNIT_PATTERN.search(title)
    return match.group(1).strip().casefold() if match else None


def _has_protected_difference(left: dict[str, Any], right: dict[str, Any]) -> bool:
    left_role = _text(left.get("role_id"))
    right_role = _text(right.get("role_id"))
    if left_role and right_role and left_role != "other" and right_role != "other" and left_role != right_role:
        return True
    left_seniority = _seniority(left)
    right_seniority = _seniority(right)
    if left_seniority and right_seniority and left_seniority != right_seniority:
        return True
    if _is_intern(left) != _is_intern(right):
        return True
    if (_is_intern(left) and _is_explicit_full_time(right)) or (_is_intern(right) and _is_explicit_full_time(left)):
        return True
    left_unit = _business_unit(left)
    right_unit = _business_unit(right)
    return left_unit != right_unit and (left_unit is not None or right_unit is not None)


def _simhash(text: str) -> int | None:
    if len(text) < 3:
        return None
    weights = [0] * 64
    for index in range(len(text) - 2):
        feature = text[index : index + 3].encode("utf-8")
        fingerprint = int.from_bytes(hashlib.blake2b(feature, digest_size=8).digest(), "big")
        for bit in range(64):
            weights[bit] += 1 if fingerprint & (1 << bit) else -1
    return sum(1 << bit for bit, weight in enumerate(weights) if weight >= 0)


def _simhash_similarity(left: str, right: str) -> float | None:
    left_hash = _simhash(left)
    right_hash = _simhash(right)
    if left_hash is None or right_hash is None:
        return None
    distance = (left_hash ^ right_hash).bit_count()
    if distance > SIMHASH_MAX_DISTANCE:
        return None
    return round((1 - distance / 64) * 100, 6)


def _record_identity(record: dict[str, Any]) -> tuple[str, str]:
    return _text(record.get("source_id")), _text(record.get("source_job_id"))


def match_pair(left: dict[str, Any], right: dict[str, Any]) -> PairMatch | None:
    company = _text(left.get("company_name_normalized"))
    if not company or company != _text(right.get("company_name_normalized")):
        return None
    city = _city_key(left)
    if not city or city != _city_key(right) or _has_protected_difference(left, right):
        return None
    left_title = _title(left)
    right_title = _title(right)
    if not left_title or not right_title:
        return None
    if left_title == right_title:
        same_source = _text(left.get("source_id")) == _text(right.get("source_id"))
        distinct_native_ids = (
            _text(left.get("source_job_id"))
            and _text(right.get("source_job_id"))
            and _text(left.get("source_job_id")) != _text(right.get("source_job_id"))
        )
        if same_source and distinct_native_ids:
            left_description = _description(left)
            right_description = _description(right)
            if not left_description or not right_description:
                return None
            description_ratio = fuzz.ratio(left_description, right_description)
            if description_ratio < SAME_SOURCE_EXACT_DESCRIPTION_THRESHOLD:
                return None
        return PairMatch("level_1_exact", 100.0, "same normalized company, city, and title")
    left_role = _text(left.get("role_id"))
    right_role = _text(right.get("role_id"))
    if not left_role or left_role == "other" or left_role != right_role:
        return None
    title_score = fuzz.ratio(left_title, right_title, score_cutoff=SIMHASH_TITLE_THRESHOLD)
    if title_score >= FUZZY_TITLE_THRESHOLD:
        return PairMatch("level_2_fuzzy_title", round(title_score, 6), "same company/city; conservative title ratio")
    if title_score < SIMHASH_TITLE_THRESHOLD:
        return None
    description_score = _simhash_similarity(_description(left), _description(right))
    if description_score is None:
        return None
    return PairMatch("level_3_simhash_description", description_score, "same company/city; title and SimHash JD thresholds")


def _record_sort_key(record: dict[str, Any]) -> tuple[str, str, str]:
    observed_at = _text(record.get("observed_at")) or "9999-12-31T23:59:59+00:00"
    return observed_at, _text(record.get("source_id")), _text(record.get("silver_job_id"))


def _canonical_job_id(silver_job_id: str) -> str:
    digest = hashlib.sha256(silver_job_id.encode("utf-8")).hexdigest()[:24]
    return f"job_{digest}"


def _match_group(record: dict[str, Any], group: DedupGroup) -> PairMatch | None:
    matches = [match_pair(record, member) for member in group.members]
    if any(match is None for match in matches):
        return None
    concrete_matches = [match for match in matches if match is not None]
    return max(concrete_matches, key=lambda match: (_METHOD_RANK[match.method], -match.score))


def _audited_distinct_reason(
    record: dict[str, Any], decisions: AuditedPairDecisions
) -> str | None:
    identity = _record_identity(record)
    reasons = sorted(
        reason
        for pair, (decision, reason) in decisions.items()
        if decision == "different" and identity in pair
    )
    return f"audited distinct: {'; '.join(reasons)}" if reasons else None


def _apply_audited_decisions(
    groups: list[DedupGroup], decisions: AuditedPairDecisions
) -> list[DedupGroup]:
    identities = {
        _record_identity(member)
        for group in groups
        for member in group.members
    }
    result = list(groups)
    for pair, (decision, reason) in decisions.items():
        if not pair.issubset(identities):
            continue
        group_indexes = [
            index
            for index, group in enumerate(result)
            if pair.intersection(_record_identity(member) for member in group.members)
        ]
        if decision == "same":
            if len(group_indexes) != 1:
                raise ValueError("Audited same pair is not in one existing merge group")
            group = result[group_indexes[0]]
            if len([member for member in group.members if _record_identity(member) in pair]) != 2:
                raise ValueError("Audited same pair does not identify two members")
            for member in group.members:
                silver_job_id = _text(member.get("silver_job_id"))
                if _record_identity(member) in pair and silver_job_id in group.member_matches:
                    match = group.member_matches[silver_job_id]
                    group.member_matches[silver_job_id] = PairMatch(
                        match.method, match.score, f"audited same: {reason}"
                    )
            continue
        if len(group_indexes) != 1:
            raise ValueError("Audited different pair is not in one existing merge group")
        index = group_indexes[0]
        group = result[index]
        if len(group.members) != 2 or {
            _record_identity(member) for member in group.members
        } != pair:
            raise ValueError("Audited different decision is limited to one existing two-member group")
        result[index : index + 1] = [
            DedupGroup(members=[member]) for member in group.members
        ]
    return result


def deduplicate_records(
    records: list[dict[str, Any]],
    audited_decisions: AuditedPairDecisions | None = None,
) -> DeduplicationResult:
    audited_decisions = audited_decisions or {}
    raw_job_count = len(records)
    eligible = [record for record in records if _text(record.get("record_status")) == "valid"]
    ids = [_text(record.get("silver_job_id")) for record in eligible]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError("Eligible Silver records require unique, non-empty silver_job_id values")
    if any(not _text(record.get("source_record_id")) or not _text(record.get("source_id")) for record in eligible):
        raise ValueError("Eligible Silver records require source_record_id and source_id provenance")

    groups: list[DedupGroup] = []
    for record in sorted(eligible, key=_record_sort_key):
        candidates = [
            (group, match)
            for group in groups
            if (match := _match_group(record, group)) is not None
        ]
        if not candidates:
            groups.append(DedupGroup(members=[record]))
            continue
        group, match = min(
            candidates,
            key=lambda item: (_METHOD_RANK[item[1].method], -item[1].score, item[0].representative["silver_job_id"]),
        )
        group.members.append(record)
        group.member_matches[_text(record["silver_job_id"])] = match

    groups = _apply_audited_decisions(groups, audited_decisions)

    source_maps: list[dict[str, Any]] = []
    duplicate_group_count = 0
    overlap_group_count = 0
    method_counts = {"level_1_exact": 0, "level_2_fuzzy_title": 0, "level_3_simhash_description": 0}
    for group in groups:
        canonical_id = _canonical_job_id(_text(group.representative["silver_job_id"]))
        if len(group.members) > 1:
            duplicate_group_count += 1
        if len({_text(member.get("source_id")) for member in group.members}) > 1:
            overlap_group_count += 1
        for member in group.members:
            silver_job_id = _text(member["silver_job_id"])
            match = group.member_matches.get(silver_job_id)
            if match is not None:
                method_counts[match.method] += 1
            source_maps.append(
                {
                    "canonical_job_id": canonical_id,
                    "silver_job_id": silver_job_id,
                    "source_record_id": member.get("source_record_id"),
                    "source_id": member.get("source_id"),
                    "source_job_id": member.get("source_job_id"),
                    "source_url": member.get("source_url"),
                    "observed_at": member.get("observed_at"),
                    "upstream_source": member.get("upstream_source"),
                    "upstream_external_id": member.get("upstream_external_id"),
                    "source_company_slug": member.get("source_company_slug"),
                    "api_accessed_at": member.get("api_accessed_at"),
                    "source_payload_sha256": member.get("source_payload_sha256"),
                    "match_method": match.method if match else "unique",
                    "match_score": match.score if match else None,
                    "match_reason": match.reason if match else (
                        _audited_distinct_reason(member, audited_decisions)
                        or "no conservative duplicate match"
                    ),
                    "deduplication_rule_version": DEDUPLICATION_RULE_VERSION,
                }
            )
    canonical_count = len(groups)
    deduplicated_count = len(eligible) - canonical_count
    report = DeduplicationReport(
        deduplication_rule_version=DEDUPLICATION_RULE_VERSION,
        raw_job_count=raw_job_count,
        eligible_job_count=len(eligible),
        canonical_job_count=canonical_count,
        duplicate_group_count=duplicate_group_count,
        deduplicated_job_count=deduplicated_count,
        dedup_rate=deduplicated_count / len(eligible) if eligible else 0.0,
        cross_platform_overlap_group_count=overlap_group_count,
        cross_platform_overlap_rate=overlap_group_count / canonical_count if canonical_count else 0.0,
        match_method_counts=method_counts,
    )
    return DeduplicationResult(groups=groups, source_maps=source_maps, report=report)
