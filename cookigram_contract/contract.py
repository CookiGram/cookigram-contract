from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REQUIRED_OUTPUTS = ("index.html", "manifest.webmanifest", "sw.js", "recipes.json", "sitemap.xml", "robots.txt", "feed.xml", ".nojekyll", "provenance.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_FRONTMATTER = ("title", "portions", "prep_time", "total_time", "tags", "source", "author", "image", "image_credit", "scaling")
MENTION = re.compile(r"@(?P<name>[^@{}\n]+?)\{(?P<quantity>[^{}\n]+)\}")
HEADING = re.compile(r"^\[(?P<header>[^\]]+)\]\s*$")
STEP_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CONTRACT_1_1 = re.compile(r"^1\.1\.\d+$")
MEAL_COMPLETENESS = {"complete", "partial", "component"}
MEAL_ROLES = {"main", "starch", "vegetable", "sauce"}
MEAL_NEEDS = {"starch", "vegetable", "sauce"}


@dataclass(frozen=True)
class IngredientMention:
    name: str
    quantity: str
    line: int


@dataclass(frozen=True)
class RecipeStep:
    id: str
    action: str
    line: int
    ingredients: tuple[IngredientMention, ...]


@dataclass(frozen=True)
class Recipe:
    frontmatter: dict[str, Any]
    steps: tuple[RecipeStep, ...]
    source: str = "<string>"


@dataclass(frozen=True)
class ValidationError:
    """Stable, serializable contract error."""

    code: str
    path: str
    message: str
    line: int | None = None

    def __str__(self) -> str:
        location = f" line {self.line}" if self.line is not None else ""
        return f"{self.code} {self.path}{location}: {self.message}"


class RecipeParseError(ValueError):
    def __init__(self, error: ValidationError):
        self.error = error
        super().__init__(str(error))


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-") or "step"


def _mentions(text: str, line: int) -> list[IngredientMention]:
    return [IngredientMention(match.group("name").strip(), match.group("quantity").strip(), line) for match in MENTION.finditer(text)]


def parse_recipe(source: str | Path, *, source_name: str | None = None) -> Recipe:
    """Parse Gram blocks ``[id | action]`` and ``@ingredient{quantity}``."""
    if isinstance(source, Path):
        source_name = source_name or source.as_posix()
        text = source.read_text(encoding="utf-8")
    else:
        text = source
        source_name = source_name or "<string>"
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise RecipeParseError(ValidationError("frontmatter.missing", source_name, "expected opening ---", 1))
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise RecipeParseError(ValidationError("frontmatter.unclosed", source_name, "expected closing ---", 1)) from exc
    try:
        frontmatter = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        raise RecipeParseError(ValidationError("frontmatter.invalid", source_name, "invalid YAML", 1)) from exc
    if not isinstance(frontmatter, dict):
        raise RecipeParseError(ValidationError("frontmatter.type", source_name, "frontmatter must be a mapping", 1))
    steps: list[RecipeStep] = []
    current_id: str | None = None
    current_action: str | None = None
    current_line = 0
    for number, raw in enumerate(lines[end + 1 :], end + 2):
        line = raw.strip()
        heading = HEADING.fullmatch(line)
        if heading:
            if current_id is not None:
                steps.append(RecipeStep(current_id, current_action or "", current_line, tuple(_mentions(current_action or "", current_line))))
            header = heading.group("header").strip()
            if "|" in header:
                current_id, current_action = (part.strip() for part in header.split("|", 1))
            else:
                current_id, current_action = _slug(header), header
            current_line = number
        elif current_id is not None and line.startswith("-"):
            action = line[1:].strip()
            current_action = f"{current_action}\n{action}" if current_action else action
    if current_id is not None:
        steps.append(RecipeStep(current_id, current_action or "", current_line, tuple(_mentions(current_action or "", current_line))))
    return Recipe(frontmatter, tuple(steps), source_name)


def validate_recipe(recipe: Recipe | str | Path, *, contract_version: str = "1.0.0") -> list[ValidationError]:
    """Return stable structural errors; an empty list means valid."""
    if not isinstance(recipe, Recipe):
        try:
            recipe = parse_recipe(recipe)
        except RecipeParseError as exc:
            return [exc.error]
    errors: list[ValidationError] = []
    metadata = recipe.frontmatter
    for field in REQUIRED_FRONTMATTER:
        if field not in metadata:
            errors.append(ValidationError("field.required", field, "required field is missing"))
    for field in ("title", "prep_time", "total_time", "source", "author", "image"):
        if field in metadata and (not isinstance(metadata[field], str) or not metadata[field].strip()):
            errors.append(ValidationError("field.type", field, "must be a non-empty string"))
    if "portions" in metadata and (isinstance(metadata["portions"], bool) or not isinstance(metadata["portions"], int) or metadata["portions"] <= 0):
        errors.append(ValidationError("field.value", "portions", "must be a positive integer"))
    if "tags" in metadata and (not isinstance(metadata["tags"], list) or not metadata["tags"] or not all(isinstance(tag, str) and tag.strip() for tag in metadata["tags"])):
        errors.append(ValidationError("field.value", "tags", "must be a non-empty list of strings"))
    credit = metadata.get("image_credit")
    if not isinstance(credit, dict):
        errors.append(ValidationError("field.type", "image_credit", "must be a mapping"))
    else:
        for field in ("author", "source", "license"):
            if not isinstance(credit.get(field), str) or not credit[field].strip():
                errors.append(ValidationError("field.required", f"image_credit.{field}", "required non-empty string is missing"))
    scaling = metadata.get("scaling")
    if not isinstance(scaling, dict) or not isinstance(scaling.get("enabled"), bool):
        errors.append(ValidationError("field.type", "scaling.enabled", "must be a boolean"))
    if not recipe.steps:
        errors.append(ValidationError("steps.empty", "steps", "at least one step is required"))
    seen: set[str] = set()
    for step in recipe.steps:
        if not STEP_ID.fullmatch(step.id):
            errors.append(ValidationError("step.id", f"steps.{step.id}", "must match [a-z0-9][a-z0-9-]*", step.line))
        if step.id in seen:
            errors.append(ValidationError("step.duplicate", f"steps.{step.id}", "step id must be unique", step.line))
        seen.add(step.id)
        if not step.action.strip():
            errors.append(ValidationError("step.action", f"steps.{step.id}", "action must be non-empty", step.line))
        for mention in step.ingredients:
            if not mention.name or not mention.quantity:
                errors.append(ValidationError("ingredient.mention", f"steps.{step.id}", "ingredient mentions require name and quantity", mention.line))
    if isinstance(contract_version, str) and CONTRACT_1_1.fullmatch(contract_version):
        errors.extend(_validate_meal(metadata))
    return errors


def _validate_meal(metadata: dict[str, Any]) -> list[ValidationError]:
    if "meal" not in metadata:
        return []
    meal = metadata["meal"]
    if not isinstance(meal, dict):
        return [ValidationError("invalid_type", "meal", "must be a mapping")]
    errors: list[ValidationError] = []
    for field in meal:
        if field not in {"completeness", "role", "needs", "benefits_from"}:
            errors.append(ValidationError("forbidden", f"meal.{field}", "unknown meal field"))
    completeness = meal.get("completeness")
    if completeness is None:
        errors.append(ValidationError("required", "meal.completeness", "required field is missing"))
    elif not isinstance(completeness, str):
        errors.append(ValidationError("invalid_type", "meal.completeness", "must be a string"))
    elif completeness not in MEAL_COMPLETENESS:
        errors.append(ValidationError("invalid_value", "meal.completeness", "unsupported completeness"))

    role = meal.get("role")
    if role is not None:
        if not isinstance(role, str):
            errors.append(ValidationError("invalid_type", "meal.role", "must be exactly one role"))
        elif role not in MEAL_ROLES:
            errors.append(ValidationError("invalid_value", "meal.role", "unsupported role"))

    needs = meal.get("needs")
    if needs is not None:
        if not isinstance(needs, list):
            errors.append(ValidationError("invalid_type", "meal.needs", "must be a list"))
        else:
            seen: list[Any] = []
            for value in needs:
                if value in seen:
                    errors.append(ValidationError("duplicate", "meal.needs", "list entries must be unique"))
                seen.append(value)
                if not isinstance(value, str):
                    errors.append(ValidationError("invalid_type", "meal.needs", "entries must be strings"))
                elif value not in MEAL_NEEDS:
                    errors.append(ValidationError("forbidden" if value == "main" else "invalid_value", "meal.needs", "unsupported relation target"))

    if isinstance(completeness, str) and completeness in MEAL_COMPLETENESS:
        has_role = isinstance(role, str) and role in MEAL_ROLES
        needs_count = len(needs) if isinstance(needs, list) else None
        if completeness in {"component", "partial"} and "role" not in meal:
            errors.append(ValidationError("required", "meal.role", "exactly one role is required"))
        if completeness == "component" and needs_count not in (None, 0):
            errors.append(ValidationError("forbidden", "meal.needs", "component cannot declare needs"))
        if completeness == "partial" and isinstance(needs, list) and needs_count == 0:
            errors.append(ValidationError("required", "meal.needs", "partial requires at least one need"))
        if completeness == "partial" and "needs" not in meal:
            errors.append(ValidationError("required", "meal.needs", "partial requires at least one need"))
        if completeness == "complete" and needs_count not in (None, 0):
            errors.append(ValidationError("forbidden", "meal.needs", "complete cannot declare needs"))
    return errors


def content_files(root: Path) -> list[Path]:
    """Return hashable content files in deterministic relative-path order."""
    excluded = {".git", "_site", "__pycache__"}
    return sorted((p for p in root.rglob("*") if p.is_file() and not any(part in excluded for part in p.parts)), key=lambda p: p.relative_to(root).as_posix())


def content_sha(root: Path) -> str:
    """Hash relative paths and bytes; changing either changes the digest."""
    digest = hashlib.sha256()
    for path in content_files(root):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def validate_content(root: Path, allow_empty: bool = False) -> list[str]:
    errors: list[str] = []
    recipes = sorted((root / "recipes").glob("*.gram")) if (root / "recipes").is_dir() else []
    if not recipes and not allow_empty:
        errors.append("recipes/: at least one .gram file is required")
    ingredients = root / ".gram" / "ingredients.yaml"
    provenance = root / ".gram" / "ingredient-provenance.yaml"
    if recipes and not ingredients.is_file():
        errors.append(".gram/ingredients.yaml: required when recipes exist")
    if recipes and not provenance.is_file():
        errors.append(".gram/ingredient-provenance.yaml: required when recipes exist")
    for recipe in recipes:
        try:
            errors.extend(validate_recipe(recipe))
        except (OSError, UnicodeError) as exc:
            errors.append(ValidationError("recipe.read", recipe.as_posix(), str(exc)))
    return errors


def verify_output(output: Path) -> list[str]:
    errors = [f"{name}: missing" for name in REQUIRED_OUTPUTS if not (output / name).exists()]
    if not (output / "assets").is_dir():
        errors.append("assets/: missing")
    provenance = output / "provenance.json"
    if provenance.is_file():
        try:
            data = json.loads(provenance.read_text(encoding="utf-8"))
            if set(data) != {"content_sha", "core_sha", "built_at"}:
                errors.append("provenance.json: fields must be content_sha, core_sha, built_at")
            elif not isinstance(data["content_sha"], str) or not SHA256.fullmatch(data["content_sha"]):
                errors.append("provenance.json: content_sha must be a lowercase SHA-256")
            elif not isinstance(data["core_sha"], str) or not data["core_sha"]:
                errors.append("provenance.json: core_sha must be non-empty")
            elif not isinstance(data["built_at"], str) or not data["built_at"].endswith("Z"):
                errors.append("provenance.json: built_at must be UTC and end with Z")
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"provenance.json: invalid JSON ({exc})")
    return errors
