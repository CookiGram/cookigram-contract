import json
from pathlib import Path

from cookigram_contract import parse_recipe, validate_recipe
from cookigram_contract.contract import content_sha, validate_content, verify_output

ROOT = Path(__file__).parents[1]


def test_example_content_is_valid_and_hash_is_stable():
    content = ROOT / "examples" / "minimal-content"
    assert validate_content(content) == []
    assert content_sha(content) == content_sha(content)


def test_hash_changes_when_content_changes(tmp_path):
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "one.gram").write_text("---\ntitle: One\n---\n", encoding="utf-8")
    first = content_sha(tmp_path)
    (tmp_path / "recipes" / "one.gram").write_text("---\ntitle: Two\n---\n", encoding="utf-8")
    assert content_sha(tmp_path) != first


def test_verify_output_accepts_documented_minimum(tmp_path):
    for name in ("index.html", "manifest.webmanifest", "sw.js", "recipes.json", "sitemap.xml", "robots.txt", "feed.xml", ".nojekyll"):
        (tmp_path / name).write_text("", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    provenance = {"content_sha": "a" * 64, "core_sha": "abc", "built_at": "2026-09-05T12:00:00Z"}
    (tmp_path / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    assert verify_output(tmp_path) == []


def test_empty_content_requires_explicit_opt_in(tmp_path):
    assert validate_content(tmp_path)
    assert validate_content(tmp_path, allow_empty=True) == []


def test_parse_recipe_supports_explicit_step_ids_and_mentions():
    recipe = parse_recipe("""---
title: Test
portions: 2
prep_time: 1 min
total_time: 2 min
tags: [test]
source: test
author: Test
image: images/test.svg
image_credit: {author: Test, source: test, license: MIT}
scaling: {enabled: false}
---
[mix | Mélanger]
- Ajouter @tomate{200 g} et @sel{1 pincée}.
""")
    assert recipe.steps[0].id == "mix"
    assert recipe.steps[0].action == "Mélanger\nAjouter @tomate{200 g} et @sel{1 pincée}."
    assert [(item.name, item.quantity) for item in recipe.steps[0].ingredients] == [("tomate", "200 g"), ("sel", "1 pincée")]
    assert validate_recipe(recipe) == []


def test_validation_errors_are_stable_and_structural():
    errors = validate_recipe("---\ntitle:   \n---\n")
    assert [(error.code, error.path) for error in errors] == [
        ("field.required", "portions"),
        ("field.required", "prep_time"),
        ("field.required", "total_time"),
        ("field.required", "tags"),
        ("field.required", "source"),
        ("field.required", "author"),
        ("field.required", "image"),
        ("field.required", "image_credit"),
        ("field.required", "scaling"),
        ("field.type", "title"),
        ("field.type", "image_credit"),
        ("field.type", "scaling.enabled"),
        ("steps.empty", "steps"),
    ]


def _meal_recipe(meal: str) -> str:
    return """---
title: Meal
portions: 2
prep_time: 1 min
total_time: 2 min
tags: [test]
source: test
author: Test
image: images/test.svg
image_credit: {author: Test, source: test, license: MIT}
scaling: {enabled: false}
meal:
%s---
[step | Cook]
- Cook it.
""" % meal


def test_meal_composition_forms_and_absence_are_valid():
    assert validate_recipe(_meal_recipe("  completeness: invalid\n")) == []
    assert [(error.code, error.path) for error in validate_recipe(_meal_recipe("  completeness: invalid\n"), contract_version="1.1.0") if error.path.startswith("meal")] == [("invalid_value", "meal.completeness")]
    assert validate_recipe(_meal_recipe("  completeness: complete\n  role: main\n  needs: []\n")) == []
    assert validate_recipe(_meal_recipe("  completeness: partial\n  role: sauce\n  needs: [vegetable]\n")) == []
    assert validate_recipe(_meal_recipe("  completeness: component\n  role: starch\n")) == []
    assert validate_recipe(_meal_recipe("  completeness: complete\n"), contract_version="1.1.0") == []
    assert validate_recipe(_meal_recipe("").replace("meal:\n---", "---"), contract_version="1.1.0") == []


def test_partial_requires_needs_when_pinned():
    errors = validate_recipe(_meal_recipe("  completeness: partial\n  role: sauce\n"), contract_version="1.1.0")
    assert [(error.code, error.path) for error in errors if error.path.startswith("meal")] == [("required", "meal.needs")]


def test_meal_composition_rejects_structural_violations_with_stable_codes():
    errors = validate_recipe(_meal_recipe("  completeness: partial\n  needs: [main, sauce, sauce]\n  extra: true\n"), contract_version="1.1.0")
    assert sorted((error.code, error.path) for error in errors if error.path.startswith("meal")) == sorted([
        ("forbidden", "meal.extra"),
        ("required", "meal.role"),
        ("duplicate", "meal.needs"),
        ("forbidden", "meal.needs"),
    ])
    assert [(error.code, error.path) for error in validate_recipe(_meal_recipe("  completeness: component\n  role: main\n  needs: [sauce]\n"), contract_version="1.1.0") if error.path.startswith("meal")] == [("forbidden", "meal.needs")]
    assert [(error.code, error.path) for error in validate_recipe(_meal_recipe("  completeness: complete\n  needs: [sauce]\n"), contract_version="1.1.0") if error.path.startswith("meal")] == [("forbidden", "meal.needs")]


def test_legacy_benefits_from_is_tolerated_and_other_unknown_fields_are_not():
    assert validate_recipe(_meal_recipe("  completeness: complete\n  benefits_from: [vegetable]\n"), contract_version="1.1.0") == []
    errors = validate_recipe(_meal_recipe("  completeness: complete\n  future: true\n"), contract_version="1.1.0")
    assert [(error.code, error.path) for error in errors if error.path.startswith("meal")] == [("forbidden", "meal.future")]
