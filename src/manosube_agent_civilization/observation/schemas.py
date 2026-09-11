"""Canonical Observation schema registry.

The registry is loading infrastructure, not a rule: it exists once so that every
Observation consumer validates against the same canonical schema documents.

Issue #75 (``D-KERNEL-VERIFIED-SCHEMA-BYTE-INJECTION``) adds one thing and removes none:
:func:`observation_schema_errors` lets a caller that has already captured and digest-verified
the canonical schema bytes have *those exact bytes* perform the validation, by supplying the
one Kernel-owned :class:`~manosube_agent_civilization.schema_context.CanonicalSchemaContext`
instead of letting this module resolve the filesystem again. Observation remains the owner of
which schema each Observation-owned record is validated against
(``OBSERVATION_SCHEMA_OWNER_COUNT=1``); the context only decides which bytes that schema is
read from, and only when a caller explicitly supplies one.

:func:`validators` itself -- the zero-argument, reloadable, filesystem-backed registry -- is
unchanged, and remains the default for every caller that does not request verified-byte
injection. It is not, and cannot be made, byte-identity: its ``cache_clear()`` is public and
its documents come from a directory that may have changed since any earlier digest. That is
precisely why the injected context exists, and why a caller that supplies one never reaches
this function at all.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

from manosube_agent_civilization.schema_context import CanonicalSchemaContext

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


def observation_schema_errors(
    record: Any,
    schema_id: str,
    *,
    schema_context: CanonicalSchemaContext | None = None,
) -> list[ValidationError]:
    """Return every validation error *record* produces against *schema_id* (Issue #75).

    The one place Observation resolves a validator, so that "which bytes validated this
    record" has exactly one answer for every Observation-owned record kind.

    With *schema_context* supplied, the validation is performed by the validator that context
    already built from its own captured, digest-verified bytes -- no ``schema_root()``
    resolution, no ``*.schema.json`` read, no call to the legacy zero-argument
    :func:`validators` registry, and no second registry silently constructed
    (``KSI-C2``). Without one, the existing default registry answers exactly as before.

    Fails closed on an unknown *schema_id* either way: an injected context raises
    :class:`~manosube_agent_civilization.schema_context.SchemaContextError`, and the default
    registry raises :class:`ObservationValidationError` rather than the bare ``KeyError`` a
    direct subscript of :func:`validators` would have produced.
    """

    if schema_context is not None:
        return schema_context.validation_errors(record, schema_id)
    validator = validators().get(schema_id)
    if validator is None:
        raise ObservationValidationError(f"canonical schema is unavailable: {schema_id}")
    return list(validator.iter_errors(record))
