"""Canonical schema validation for every record the Difference Engine returns.

The schema registry is the repository's single ``01_SCHEMA`` tree. No record leaves the
Engine without passing the schema that owns it.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import DifferenceValidationError

SCHEMA_BASE = "https://schemas.manosube.org/agent-civilization-os/v0.1/"
DIFFERENCE_SCHEMA_BASE = SCHEMA_BASE + "difference/"
SUPPORTED_SCHEMA_VERSION = "0.1"


def _schema_root() -> Path:
    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",
        module_path.parents[2] / "01_SCHEMA",
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise DifferenceValidationError("canonical schema root is unavailable")


@lru_cache(maxsize=1)
def validators() -> dict[str, Draft202012Validator]:
    """Return one validator per canonical schema, keyed by canonical ``$id``."""

    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_schema_root().rglob("*.schema.json"))
    ]
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {
        schema["$id"]: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for schema in schemas
    }


def validate_record(record: dict[str, Any], schema_name: str, base: str = DIFFERENCE_SCHEMA_BASE) -> None:
    """Validate one generated record, raising a fail-closed error on any violation."""

    validator = validators().get(base + schema_name)
    if validator is None:
        raise DifferenceValidationError(f"canonical schema is unavailable: {schema_name}")
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors)
        raise DifferenceValidationError(f"generated {schema_name} is schema-invalid: {detail}")


def require_schema_version(record: dict[str, Any], context: str) -> None:
    """Reject an input record that declares an unknown schema version."""

    version = record.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise DifferenceValidationError(
            f"unsupported schema_version {version!r} at {context}"
        )
