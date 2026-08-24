from pathlib import Path

import pytest

from app.llm_fallback import DisabledLLMSkillExtractor
from app.skill_extraction import RuleSkillExtractor
from app.skill_taxonomy import load_skill_taxonomy


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def extractor() -> RuleSkillExtractor:
    return RuleSkillExtractor(load_skill_taxonomy(ROOT / "data/taxonomy/skills.yml"))


def canonical_names(extractor: RuleSkillExtractor, text: str) -> set[str]:
    return {match.canonical_skill for match in extractor.extract(text)}


def test_case_insensitive_alias_and_boundaries(extractor: RuleSkillExtractor) -> None:
    matches = extractor.extract("Use K8S, POSTGRES, js, TS, PBI and sklearn; not jsonish.")

    assert {match.canonical_skill for match in matches} >= {
        "Kubernetes", "PostgreSQL", "JavaScript", "TypeScript", "Power BI", "scikit-learn"
    }
    assert all(0.0 <= match.confidence <= 1.0 for match in matches)
    assert all(match.skill_id and match.matched_text and match.extraction_method for match in matches)


def test_short_terms_require_technical_context(extractor: RuleSkillExtractor) -> None:
    negative = "We go to market, manage R&D, maintain client accounts and improve AIr quality."
    assert canonical_names(extractor, negative).isdisjoint({"Go", "R", "C", "AI"})

    positive = "熟悉 Go 语言、R语言、C/C++，参与 AI 模型开发。"
    assert canonical_names(extractor, positive) >= {"Go", "R", "C", "C++", "AI"}


def test_one_relation_per_skill_and_best_evidence(extractor: RuleSkillExtractor) -> None:
    matches = extractor.extract("Python、python 与 PYTHON；使用 k8s 和 Kubernetes。")

    assert [match.canonical_skill for match in matches].count("Python") == 1
    assert [match.canonical_skill for match in matches].count("Kubernetes") == 1


def test_js_alias_does_not_match_framework_suffix(extractor: RuleSkillExtractor) -> None:
    names = canonical_names(extractor, "Node.js, Next.js, Vue.js and React.js")

    assert "JavaScript" not in names
    assert names >= {"Node.js", "Next.js", "Vue.js", "React"}


def test_llm_fallback_is_disabled_and_has_no_side_effects() -> None:
    fallback = DisabledLLMSkillExtractor()

    assert fallback.enabled is False
    assert fallback.extract("unknown technology") == []
