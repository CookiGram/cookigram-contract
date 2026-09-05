import json
from pathlib import Path

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
