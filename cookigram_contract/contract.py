from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REQUIRED_OUTPUTS = ("index.html", "manifest.webmanifest", "sw.js", "recipes.json", "sitemap.xml", "robots.txt", "feed.xml", ".nojekyll", "provenance.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
        text = recipe.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"{recipe.relative_to(root)}: YAML frontmatter is required")
        elif not re.search(r"(?m)^title:\s*\S", text):
            errors.append(f"{recipe.relative_to(root)}: title is required")
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
