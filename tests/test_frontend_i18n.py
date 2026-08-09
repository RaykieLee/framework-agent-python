"""Regression tests for the generated frontend translation catalogs."""

import json
from pathlib import Path
from typing import Any

from fastapi_gen.generator import _find_template_dir


def _message_catalogs() -> dict[str, dict[str, Any]]:
    message_dir = _find_template_dir() / "{{cookiecutter.project_slug}}" / "frontend" / "messages"
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(message_dir.glob("*.json"))
    }


def _leaf_keys(value: Any, prefix: str = "") -> set[str]:
    if not isinstance(value, dict):
        return {prefix}

    result: set[str] = set()
    for key, child in value.items():
        child_prefix = f"{prefix}.{key}" if prefix else key
        result.update(_leaf_keys(child, child_prefix))
    return result


def test_frontend_locales_have_identical_translation_keys() -> None:
    catalogs = _message_catalogs()

    assert set(catalogs) == {"en", "pl", "zh"}
    key_sets = {locale: _leaf_keys(catalog) for locale, catalog in catalogs.items()}
    assert key_sets["zh"] == key_sets["en"] == key_sets["pl"]


def test_dashboard_translation_namespaces_are_complete() -> None:
    catalogs = _message_catalogs()
    required_namespaces = {
        "admin",
        "billing",
        "chat",
        "dashboard",
        "knowledgeBases",
        "organizations",
        "rag",
        "settings",
    }

    for locale, catalog in catalogs.items():
        assert required_namespaces <= catalog.keys(), locale


def test_catalogs_do_not_contain_cookiecutter_comment_openers() -> None:
    """ICU's ``{#}`` shorthand is parsed as a Jinja comment in templates."""
    message_dir = _find_template_dir() / "{{cookiecutter.project_slug}}" / "frontend" / "messages"

    for path in message_dir.glob("*.json"):
        assert "{#" not in path.read_text(encoding="utf-8"), path.name
