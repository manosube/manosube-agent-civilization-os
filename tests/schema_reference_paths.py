"""Derive, from the canonical schemas, every location that can name another record.

The reference-edge registry in :mod:`difference.graph` is hand-declared and reviewed. This
module is the independent check on it: it reads ``01_SCHEMA`` and reports every schema
location whose subschema is an *identity-bearing reference* -- one requiring both ``kind``
and ``id``. Those are exactly the locations that can name a record in the emitted graph.

Locations that are typed pointers **without** an identity (``state_ref`` names a State
revision and fingerprint, ``kernel_source_ref_evaluated`` names a git tree) cannot resolve
to a bundle record at all, so they are deliberately outside this inventory; the registry
may still declare them to pin their ``kind``, and a contract test proves every such kind is
an enumerated non-claim and therefore adds no resolution obligation.

Paths use the registry's own locator syntax: ``a.b`` for nested objects and ``[]`` for
array expansion, so ``x.members[]`` reads an explicit collection wrapper.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def _load(base: str, name: str) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(
        (SCHEMA_ROOT / base / name).read_text(encoding="utf-8")
    )
    return document


def _resolve(node: Any, base: str, document: dict[str, Any]) -> tuple[Any, str, dict[str, Any]]:
    """Follow ``$ref`` until *node* is an inline subschema, tracking its document."""

    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 32:
        seen += 1
        target = node["$ref"]
        if target.startswith("#/"):
            resolved: Any = document
            for segment in target[2:].split("/"):
                resolved = resolved[segment]
            node = resolved
            continue
        path, _, pointer = target.partition("#")
        candidate = (SCHEMA_ROOT / base / path).resolve()
        try:
            relative = candidate.relative_to(SCHEMA_ROOT)
        except ValueError:  # pragma: no cover - a schema outside the canonical tree
            return node, base, document
        base = str(relative.parent)
        document = json.loads(candidate.read_text(encoding="utf-8"))
        node = document
        if pointer:
            for segment in pointer.lstrip("/").split("/"):
                node = node[segment]
    return node, base, document


def _is_identity_reference(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    required = node.get("required")
    return isinstance(required, list) and "kind" in required and "id" in required


def reference_paths(base: str, name: str) -> set[str]:
    """Return every identity-bearing reference location declared by one record schema."""

    document = _load(base, name)
    found: set[str] = set()

    def walk(node: Any, path: str, base: str, document: dict[str, Any], depth: int) -> None:
        if depth > 24 or not isinstance(node, dict):
            return
        node, base, document = _resolve(node, base, document)
        if not isinstance(node, dict):
            return
        if _is_identity_reference(node):
            if path:
                found.add(path)
            return
        properties = node.get("properties")
        if isinstance(properties, dict):
            for key, value in properties.items():
                walk(value, f"{path}.{key}" if path else key, base, document, depth + 1)
        items = node.get("items")
        if items is not None:
            walk(items, f"{path}[]", base, document, depth + 1)
        for keyword in ("allOf", "anyOf", "oneOf"):
            for branch in node.get(keyword, []) or []:
                walk(branch, path, base, document, depth + 1)
        for keyword in ("then", "else"):
            branch = node.get(keyword)
            if branch is not None:
                walk(branch, path, base, document, depth + 1)

    walk(document, "", base, document, 0)
    return found
