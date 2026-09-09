"""Canonical schema validation for every record the Difference Engine returns.

The schema registry is the repository's single ``01_SCHEMA`` tree. No record leaves the
Engine without passing the schema that owns it.
"""

from __future__ import annotations

from functools import cache, lru_cache
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
def _schemas_and_registry() -> tuple[tuple[dict[str, Any], ...], Registry[Any]]:
    """Load the single ``01_SCHEMA`` tree once and return every schema alongside the one
    resolution registry built over it -- the single owner of "which canonical schemas exist
    and how do their ``$ref``s resolve", shared by :func:`validators` and
    :func:`subschema_validator` so neither can ever disagree with the other about either."""

    schemas = tuple(
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_schema_root().rglob("*.schema.json"))
    )
    registry: Registry[Any] = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return schemas, registry


@lru_cache(maxsize=1)
def validators() -> dict[str, Draft202012Validator]:
    """Return one validator per canonical schema, keyed by canonical ``$id``."""

    schemas, registry = _schemas_and_registry()
    return {
        schema["$id"]: Draft202012Validator(
            schema, registry=registry, format_checker=FormatChecker()
        )
        for schema in schemas
    }


@cache
def subschema_validator(schema_id: str, pointer: str) -> Draft202012Validator:
    """Return a validator for one internal ``$defs`` subschema of an already-registered
    canonical schema, resolved through the identical registry :func:`validators` uses.

    A canonical schema often owns a shape that is only ever *embedded* in a record -- a
    Runtime Observation Envelope's own ``$defs/target_identity`` and ``$defs/boundary``, for
    instance. A caller that must validate such a shape *before* the enclosing record can
    exist (Phase 15 Structural Review Round 1, P15-R1-F2: the complete Boundary must be
    schema-valid before an adapter is ever reached, long before an Envelope is derivable) has
    exactly two options -- reuse the canonical registry through this function, or hand-roll a
    second schema loader. This function exists so that second loader never gets written.

    *pointer* is a JSON pointer fragment including its leading ``#`` (e.g.
    ``"#/$defs/boundary"``); relative ``$ref``s inside the subschema resolve against
    *schema_id*'s own base exactly as they do when the whole schema is validated.
    """

    _, registry = _schemas_and_registry()
    return Draft202012Validator(
        {"$ref": schema_id + pointer}, registry=registry, format_checker=FormatChecker()
    )


def validate_record(record: dict[str, Any], schema_name: str, base: str = DIFFERENCE_SCHEMA_BASE) -> None:
    """Validate one generated record, raising a fail-closed error on any violation."""

    validator = validators().get(base + schema_name)
    if validator is None:
        raise DifferenceValidationError(f"canonical schema is unavailable: {schema_name}")
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors)
        raise DifferenceValidationError(f"generated {schema_name} is schema-invalid: {detail}")


def validate_subrecord(
    value: Any, schema_name: str, pointer: str, base: str = DIFFERENCE_SCHEMA_BASE
) -> None:
    """Validate *value* against one internal ``$defs`` subschema of a canonical schema,
    raising the identical fail-closed error :func:`validate_record` raises for a whole
    record."""

    schema_id = base + schema_name
    if schema_id not in validators():
        raise DifferenceValidationError(f"canonical schema is unavailable: {schema_name}")
    validator = subschema_validator(schema_id, pointer)
    errors = sorted(validator.iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors
        )
        raise DifferenceValidationError(
            f"value at {schema_name}{pointer} is schema-invalid: {detail}"
        )


def require_schema_version(record: dict[str, Any], context: str) -> None:
    """Reject an input record that declares an unknown schema version."""

    version = record.get("schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise DifferenceValidationError(
            f"unsupported schema_version {version!r} at {context}"
        )
