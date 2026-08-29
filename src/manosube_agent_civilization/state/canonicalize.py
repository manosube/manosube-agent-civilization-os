"""MANOSUBE-CANONICAL-JSON-0.1 implementation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .errors import (
    AmbiguousCollectionError,
    InvalidUnicodeError,
    NonStringKeyError,
    SchemaValidationError,
    SecretFieldError,
    UnsupportedValueError,
)

SERIALIZATION_PROFILE = "MANOSUBE-CANONICAL-JSON-0.1"
SEMANTIC_STATE_SCHEMA_ID = (
    "https://schemas.manosube.org/agent-civilization-os/v0.1/state/semantic_state.schema.json"
)
PROJECT_STATE_SCHEMA_ID = (
    "https://schemas.manosube.org/agent-civilization-os/v0.1/state/project_state.schema.json"
)

_SET_LIKE_FIELDS = frozenset(
    {
        "active_changes",
        "blind_spots",
        "constitutional_constraints",
        "evidence",
        "evidence_refs",
        "identity_refs",
        "open_differences",
        "source_snapshot_refs",
        "observation_scope_refs",
        "warnings",
    }
)
_SECRET_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "authorization_header",
        "credential",
        "credentials",
        "password",
        "private_key",
        "secret",
        "session_cookie",
        "token",
    }
)


def _normalize_string(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    try:
        normalized.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise InvalidUnicodeError("string contains an invalid Unicode surrogate") from exc
    return normalized


def _normalized_key_for_secret_check(key: str) -> str:
    return key.strip().lower().replace("-", "_").replace(" ", "_")


def _canonical_tree(value: Any, path: tuple[str, ...] = ()) -> Any:
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return value
    if isinstance(value, float):
        raise UnsupportedValueError("floating-point values are prohibited in v0.1")
    if isinstance(value, str):
        return _normalize_string(value)
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise NonStringKeyError("canonical object keys must be strings")
            key = _normalize_string(raw_key)
            if _normalized_key_for_secret_check(key) in _SECRET_KEYS:
                raise SecretFieldError(f"forbidden secret-bearing field: {key}")
            if key in normalized:
                raise NonStringKeyError("keys collide after Unicode normalization")
            normalized[key] = _canonical_tree(child, (*path, key))
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not isinstance(value, list):
            raise UnsupportedValueError("only JSON arrays represented as list are supported")
        items = [_canonical_tree(item, (*path, "[]")) for item in value]
        if path and path[-1] in _SET_LIKE_FIELDS:
            encoded = [canonical_json_bytes(item) for item in items]
            if len(set(encoded)) != len(encoded):
                raise AmbiguousCollectionError("duplicate element in set-like collection")
            items = [item for _, item in sorted(zip(encoded, items, strict=True))]
        return items
    raise UnsupportedValueError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes without mutating *value*."""

    tree = _canonical_tree(value)
    text = json.dumps(
        tree,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return text.encode("utf-8", errors="strict")


def _default_schema_root() -> Path:
    module_path = Path(__file__).resolve()
    candidates = (
        module_path.parents[3] / "01_SCHEMA",  # source checkout
        module_path.parents[2] / "01_SCHEMA",  # installed wheel at site-packages root
        Path.cwd() / "01_SCHEMA",
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SchemaValidationError("canonical schema root is unavailable")


def _schema_registry(schema_root: Path) -> tuple[dict[str, Any], Registry[Any]]:
    schemas: list[dict[str, Any]] = []
    for path in sorted(schema_root.rglob("*.schema.json")):
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SchemaValidationError(f"cannot load schema: {path}") from exc
        if not isinstance(schema, dict) or not isinstance(schema.get("$id"), str):
            raise SchemaValidationError(f"schema has no stable $id: {path}")
        schemas.append(schema)
    registry: Registry[Any] = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in schemas
    )
    return {schema["$id"]: schema for schema in schemas}, registry


def _validate(value: Any, schema_id: str, schema_root: Path | None) -> None:
    schemas, registry = _schema_registry(schema_root or _default_schema_root())
    try:
        schema = schemas[schema_id]
    except KeyError as exc:
        raise SchemaValidationError(f"required schema is unavailable: {schema_id}") from exc
    validator = Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    )
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        location = "/".join(str(part) for part in errors[0].absolute_path) or "<root>"
        raise SchemaValidationError(f"schema validation failed at {location}: {errors[0].message}")


def canonical_semantic_state_bytes(
    project_state: Mapping[str, Any], *, schema_root: Path | None = None
) -> bytes:
    """Validate a Project State, exclude metadata, and serialize its Semantic State."""

    _validate(project_state, PROJECT_STATE_SCHEMA_ID, schema_root)
    if "semantic_state" not in project_state:
        raise SchemaValidationError("project state has no semantic_state")
    semantic_state = project_state["semantic_state"]
    _validate(semantic_state, SEMANTIC_STATE_SCHEMA_ID, schema_root)
    return canonical_json_bytes(semantic_state)


def canonical_semantic_value_bytes(
    semantic_state: Mapping[str, Any], *, schema_root: Path | None = None
) -> bytes:
    """Validate and serialize an already projected Semantic State."""

    _validate(semantic_state, SEMANTIC_STATE_SCHEMA_ID, schema_root)
    return canonical_json_bytes(semantic_state)
