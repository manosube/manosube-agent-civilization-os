"""Canonical Observation schema registry.

The registry is loading infrastructure, not a rule: it exists once so that every
Observation consumer validates against the same canonical schema documents.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import ObservationValidationError

OBSERVATION_SCHEMA_BASE = "https://schemas.manosube.org/agent-civilization-os/v0.1/observation/"


def schema_root() -> Path:
    """Return the canonical ``01_SCHEMA`` directory."""

    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",
        module_path.parents[2] / "01_SCHEMA",
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise ObservationValidationError("canonical schema root is unavailable")


@lru_cache(maxsize=1)
def validators() -> dict[str, Draft202012Validator]:
    """Return one validator per canonical schema, resolved through a shared registry."""

    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(schema_root().rglob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {
        schema["$id"]: Draft202012Validator(
            schema,
            registry=registry,
            format_checker=FormatChecker(),
        )
        for schema in schemas
    }
