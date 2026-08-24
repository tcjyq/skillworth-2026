from __future__ import annotations

import re
from dataclasses import dataclass

from app.skill_taxonomy import SkillDefinition, SkillTaxonomy


@dataclass(frozen=True, slots=True)
class SkillMatch:
    skill_id: str
    canonical_skill: str
    matched_text: str
    extraction_method: str
    confidence: float


@dataclass(frozen=True, slots=True)
class _Rule:
    skill: SkillDefinition
    pattern: re.Pattern[str]
    method: str
    confidence: float


SHORT_CONTEXT_PATTERNS: dict[str, str] = {
    "programming_r": r"(?<![A-Za-z0-9_])(?P<term>R)(?=\s*(?:语言|programming\b|统计|数据分析))",
    "programming_c": r"(?<![A-Za-z0-9_])(?P<term>C)(?=\s*(?:语言|programming\b|/\s*C\+\+))",
    "programming_go": r"(?<![A-Za-z0-9_])(?P<term>Go)(?=\s*(?:语言|开发|工程师|developer\b|programming\b|后端))",
    "ai_ml_ai": r"(?<![A-Za-z0-9_])(?P<term>AI)(?=\s*(?:模型|工程|平台|应用|算法|开发|系统|agent\b|engineering\b))",
}


def _term_pattern(term: str) -> re.Pattern[str]:
    left_boundary = r"(?<![A-Za-z0-9_.])" if term.casefold() == "js" else r"(?<![A-Za-z0-9_])"
    return re.compile(
        rf"{left_boundary}(?P<term>{re.escape(term)})(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )


class RuleSkillExtractor:
    def __init__(self, taxonomy: SkillTaxonomy) -> None:
        self.taxonomy = taxonomy
        self._rules = self._compile_rules()

    def _compile_rules(self) -> list[_Rule]:
        rules: list[_Rule] = []
        for skill in self.taxonomy.skills:
            if skill.skill_id in SHORT_CONTEXT_PATTERNS:
                rules.append(
                    _Rule(
                        skill,
                        re.compile(SHORT_CONTEXT_PATTERNS[skill.skill_id], re.IGNORECASE),
                        "rule_short_context",
                        0.90,
                    )
                )
            else:
                rules.append(_Rule(skill, _term_pattern(skill.canonical_name), "rule_canonical", 0.98))
            for alias in skill.aliases:
                rules.append(_Rule(skill, _term_pattern(alias), "rule_alias", 0.95))
        return sorted(rules, key=lambda rule: len(rule.pattern.pattern), reverse=True)

    def extract(self, text: str | None) -> list[SkillMatch]:
        if not text:
            return []
        candidates: dict[str, tuple[int, SkillMatch]] = {}
        method_rank = {"rule_canonical": 3, "rule_alias": 2, "rule_short_context": 1}
        for rule in self._rules:
            match = rule.pattern.search(text)
            if match is None:
                continue
            value = SkillMatch(
                skill_id=rule.skill.skill_id,
                canonical_skill=rule.skill.canonical_name,
                matched_text=match.group("term"),
                extraction_method=rule.method,
                confidence=rule.confidence,
            )
            current = candidates.get(rule.skill.skill_id)
            if current is None or (value.confidence, method_rank[value.extraction_method], -match.start()) > (
                current[1].confidence,
                method_rank[current[1].extraction_method],
                -current[0],
            ):
                candidates[rule.skill.skill_id] = (match.start(), value)
        return [item[1] for item in sorted(candidates.values(), key=lambda item: (item[0], item[1].skill_id))]
