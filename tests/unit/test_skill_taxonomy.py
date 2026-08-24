from pathlib import Path

import pytest

from app.skill_taxonomy import (
    REQUIRED_SKILL_CATEGORIES,
    SKILL_TYPES,
    SKILLWORTH_ELIGIBILITY,
    load_skill_taxonomy,
)


ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "data/taxonomy/skills.yml"


def test_taxonomy_has_required_scale_categories_and_learning_costs() -> None:
    taxonomy = load_skill_taxonomy(TAXONOMY_PATH)

    assert taxonomy.version == "1.1.0"
    assert len(taxonomy.skills) >= 120
    assert REQUIRED_SKILL_CATEGORIES <= {skill.category for skill in taxonomy.skills}
    assert len({skill.skill_id for skill in taxonomy.skills}) == len(taxonomy.skills)
    for skill in taxonomy.skills:
        assert skill.learning_hours_min <= skill.learning_hours_expected <= skill.learning_hours_max
        assert skill.learning_cost_source
        assert skill.notes
        assert skill.skill_type in SKILL_TYPES
        assert skill.skillworth_eligibility in SKILLWORTH_ELIGIBILITY
        assert skill.skillworth_reason


def test_semantic_overrides_keep_broad_and_productivity_terms_off_main_ranking() -> None:
    taxonomy = load_skill_taxonomy(TAXONOMY_PATH)
    by_name = {skill.canonical_name: skill for skill in taxonomy.skills}

    for name in ("AI", "Optimization", "Agile", "PowerPoint", "Word"):
        assert by_name[name].skillworth_eligibility == "excluded"
    for name in ("Excel", "Machine Learning", "A/B Testing"):
        assert by_name[name].skillworth_eligibility == "secondary"
    for name in ("Python", "SQL", "Docker", "Kubernetes", "React", "FastAPI"):
        assert by_name[name].skillworth_eligibility == "main"


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("k8s", "Kubernetes"),
        ("postgres", "PostgreSQL"),
        ("js", "JavaScript"),
        ("ts", "TypeScript"),
        ("pbi", "Power BI"),
        ("sklearn", "scikit-learn"),
    ],
)
def test_required_aliases_resolve(alias: str, canonical: str) -> None:
    taxonomy = load_skill_taxonomy(TAXONOMY_PATH)

    assert taxonomy.alias_index[alias.casefold()].canonical_name == canonical


def test_taxonomy_terms_are_globally_unambiguous() -> None:
    taxonomy = load_skill_taxonomy(TAXONOMY_PATH)

    terms = [
        term.casefold()
        for skill in taxonomy.skills
        for term in [skill.canonical_name, *skill.aliases]
    ]
    assert len(terms) == len(set(terms))
