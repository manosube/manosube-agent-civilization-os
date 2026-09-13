"""Canonical schema validation for the Acceptance Policy Lineage domain (FD-0004, Issue #80,
P82-R1-F4).

The schema registry is the repository's single ``01_SCHEMA`` tree -- the same one every other
domain's own ``validation.py`` reads (see ``binding/validation.py``, ``difference/validation.py``).
This module keeps its own private registry copy, per this repository's established
per-package validation convention: never imports another package's registry, never restates
another package's schema loading.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import AcceptancePolicyValidationError

SCHEMA_BASE = "https://schemas.manosube.org/agent-civilization-os/v0.1/"
ACCEPTANCE_POLICY_SCHEMA_BASE = SCHEMA_BASE + "acceptance_policy/"


def _default_schema_root() -> Path:
    module_path = Path(__file__).resolve()
    for candidate in (
        module_path.parents[3] / "01_SCHEMA",  # source checkout
        module_path.parents[2] / "01_SCHEMA",  # installed wheel at site-packages root
        Path.cwd() / "01_SCHEMA",
    ):
        if candidate.is_dir():
            return candidate
    raise AcceptancePolicyValidationError("canonical schema root is unavailable")


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
    schema_root: Path | None = None,
) -> None:
    """Validate one Acceptance Policy record, raising fail-closed on any schema violation.

    Called at both boundaries P82-R1-F4 requires: right after a record is constructed
    (:mod:`.route`, before any commit), and again every time a record is Store-resolved -- a
    malformed on-disk body must never reach this package's own identity/fingerprint/lineage
    logic un-validated.
    """

    schema_id = ACCEPTANCE_POLICY_SCHEMA_BASE + schema_name
    validators = _validators(schema_root or _default_schema_root())
    validator = validators.get(schema_id)
    if validator is None:
        raise AcceptancePolicyValidationError(f"canonical schema is unavailable: {schema_id}")
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.absolute_path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path)}: {error.message}"
            for error in errors
        )
        raise AcceptancePolicyValidationError(f"{schema_id} is schema-invalid: {detail}")


__all__ = ["validate_record"]
