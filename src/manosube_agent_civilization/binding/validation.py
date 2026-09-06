"""Canonical schema validation for the Product Binding domain.

The schema registry is the repository's single ``01_SCHEMA`` tree -- the same one every
other domain's own ``validation.py`` reads (see ``difference/validation.py``). No record
this domain persists leaves :mod:`manosube_agent_civilization.binding.engine` without
passing the schema that owns it.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import BindingValidationError

SCHEMA_BASE = "https://schemas.manosube.org/agent-civilization-os/v0.1/"
BINDING_SCHEMA_BASE = SCHEMA_BASE + "binding/"
SUPPORTED_SCHEMA_VERSION = "0.1"


def _default_schema_root() -> Path:
    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",  # source checkout
        module_path.parents[2] / "01_SCHEMA",  # installed wheel at site-packages root
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise BindingValidationError("canonical schema root is unavailable")


@lru_cache(maxsize=4)
def _validators(schema_root: Path) -> dict[str, Draft202012Validator]:
    """Return one validator per canonical schema under *schema_root*, keyed by ``$id``."""

    schemas = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(schema_root.rglob("*.schema.json"))
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


def validate_record(
    record: Any,
    schema_name: str,
    *,
    base: str = BINDING_SCHEMA_BASE,
    schema_root: Path | None = None,
) -> None:
    """Validate one Product Binding record, raising a fail-closed error on any violation."""

    validate_against_schema_id(record, base + schema_name, schema_root=schema_root)


def validate_against_schema_id(
    record: Any, schema_id: str, *, schema_root: Path | None = None
) -> None:
    """Validate *record* against any schema already registered under ``01_SCHEMA``.

    Used for records this domain accepts but does not own the schema of -- an Objective
    Revision body, in particular, whose schema (``01_SCHEMA/objective/objective_revision.
    schema.json``) is Objective's own, never restated here.
    """

    validators = _validators(schema_root or _default_schema_root())
    validator = validators.get(schema_id)
    if validator is None:
        raise BindingValidationError(f"canonical schema is unavailable: {schema_id}")
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise BindingValidationError(f"{schema_id} is schema-invalid: {detail}")
