from __future__ import annotations

from app.deduplication import deduplicate_records


def job(
    job_id: str,
    *,
    company: str = "示例科技有限公司",
    title: str = "数据分析师",
    city: str = "CN-110000",
    role: str = "data_analyst",
    experience: str = "mid",
    description: str = "负责经营数据分析、报表建设和指标体系维护。",
    source: str = "platform_a",
    source_job_id: str | None = None,
) -> dict[str, object]:
    return {
        "silver_job_id": job_id,
        "source_record_id": f"record-{job_id}",
        "source_id": source,
        "source_job_id": source_job_id or f"native-{job_id}",
        "source_url": f"https://example.test/{job_id}",
        "observed_at": "2026-08-08T08:00:00+08:00",
        "company_name_normalized": company,
        "job_title_normalized": title,
        "job_title_raw": title,
        "city_code": city,
        "city_raw": city,
        "role_id": role,
        "experience_band": experience,
        "job_description_raw": description,
        "record_status": "valid",
    }


def grouped(records: list[dict[str, object]]):
    return deduplicate_records(records)


def test_level_1_exact_merges_cross_platform_and_preserves_provenance() -> None:
    result = grouped([job("a", source="platform_a"), job("b", source="platform_b")])

    assert len(result.groups) == 1
    assert result.groups[0].method == "level_1_exact"
    assert result.report.duplicate_group_count == 1
    assert result.report.cross_platform_overlap_group_count == 1
    assert {row["source_job_id"] for row in result.source_maps} == {"native-a", "native-b"}
    assert {row["source_url"] for row in result.source_maps} == {
        "https://example.test/a", "https://example.test/b"
    }


def test_exact_title_does_not_merge_distinct_same_source_postings_with_different_jds() -> None:
    result = grouped(
        [
            job("a", title="Part-time Instructor", description="Teach swimming classes."),
            job(
                "b",
                title="Part-time Instructor",
                description="Lead camps and supervise outdoor activities.",
            ),
        ]
    )

    assert len(result.groups) == 2


def test_level_2_merges_only_very_high_fuzzy_title_similarity() -> None:
    result = grouped(
        [
            job("a", title="data platform analytics engineer"),
            job("b", title="data platform analytics engineer!", source="platform_b"),
        ]
    )

    assert len(result.groups) == 1
    assert result.groups[0].method == "level_2_fuzzy_title"
    assert result.source_maps[1]["match_score"] >= 96.0


def test_level_3_merges_similar_titles_with_near_identical_descriptions() -> None:
    description = "负责数据平台指标建设、数据质量治理、日报自动化和跨团队分析支持。"
    result = grouped(
        [
            job("a", title="data platform analyst", description=description),
            job("b", title="data platform analytics", description=description, source="platform_b"),
        ]
    )

    assert len(result.groups) == 1
    assert result.groups[0].method == "level_3_simhash_description"
    assert result.source_maps[1]["match_score"] == 100.0


def test_deduplication_protects_different_city_seniority_company_role_and_employment() -> None:
    base = job("base")
    cases = [
        job("city", city="CN-310000", source="platform_b"),
        job("company", company="另一家公司", source="platform_b"),
        job("role", role="bi_analyst", source="platform_b"),
        job("intern", title="数据分析实习生", experience="entry", source="platform_b"),
    ]

    result = grouped([base, *cases])

    assert len(result.groups) == 5
    assert result.report.dedup_rate == 0.0


def test_deduplication_does_not_use_simhash_to_merge_different_seniority() -> None:
    shared_description = "负责跨部门数据分析、报表自动化、数据质量治理和指标体系建设。"
    result = grouped(
        [
            job("mid", title="data analytics platform engineer for international operations", description=shared_description),
            job("senior", title="senior data analytics platform engineer for international operations", description=shared_description, source="platform_b"),
        ]
    )

    assert len(result.groups) == 2


def test_fuzzy_and_simhash_levels_require_a_shared_classified_role() -> None:
    description = "负责数据平台指标建设、数据质量治理、日报自动化和跨团队分析支持。"
    result = grouped(
        [
            job("a", title="data platform analyst", role="other", description=description),
            job("b", title="data platform analytics", role="other", description=description, source="platform_b"),
        ]
    )

    assert len(result.groups) == 2


def test_deduplication_protects_distinct_business_units_and_chain_merges() -> None:
    business_units = grouped(
        [
            job("growth", title="数据分析师（增长）"),
            job("supply", title="数据分析师（供应链）", source="platform_b"),
        ]
    )
    assert len(business_units.groups) == 2

    chain = grouped(
        [
            job("a", title="data analytics engineer alpha"),
            job("b", title="data analytics engineer alpha!", source="platform_b"),
            job("c", title="data analytics engineer alpha!!", source="platform_c"),
        ]
    )
    assert len(chain.groups) == 1


def test_invalid_records_are_not_deduplicated_but_are_reported() -> None:
    invalid = job("invalid")
    invalid["record_status"] = "invalid"

    result = grouped([job("valid"), invalid])

    assert result.report.raw_job_count == 2
    assert result.report.eligible_job_count == 1
    assert len(result.groups) == 1


def test_valid_records_require_source_provenance() -> None:
    record = job("missing-source")
    record["source_id"] = None

    try:
        grouped([record])
    except ValueError as error:
        assert "source_record_id and source_id" in str(error)
    else:
        raise AssertionError("expected missing source provenance to be rejected")
