"""Canonical projection helpers shared by every Difference derivation step.

The canonical serializer itself is owned by :mod:`manosube_agent_civilization.state`.
This module only adds the collection-wrapper semantics that the Difference Identity
Contract defines on top of it, so that no parallel serializer exists.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .admissibility import is_scalar_tag, require_collection, require_scalar_tag
from .errors import DifferenceError, SecurityRejectionError

ORDERED_LIST = "ORDERED_LIST"
UNORDERED_SET = "UNORDERED_SET"
COLLECTION_KINDS = frozenset({ORDERED_LIST, UNORDERED_SET})

_SECRET_KEY = re.compile(
    r"(?:password|passwd|secret|credential|token|api[_-]?key|private[_-]?key|"
    r"authorization|bearer|session[_-]?id|access[_-]?key)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?:-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})"
)
# Canonical v0.1 schema fields whose names match the secret pattern but which are
# closed policy declarations, never secret carriers.
_SECRET_KEY_ALLOWLIST = frozenset({"credential_paths"})
MOVING_REFERENCE = re.compile(
    r"^(?:HEAD|LATEST|CURRENT|MAIN|MASTER|TRUNK|DEFAULT)$|"
    r"^REFS-(?:HEADS|TAGS|REMOTES)-|@(?:LATEST|HEAD|CURRENT)$",
    re.IGNORECASE,
)


def canonical_semantic(value: Any) -> Any:
    """Return *value* with every ``UNORDERED_SET`` wrapper sorted by canonical bytes."""

    if isinstance(value, dict):
        normalized = {key: canonical_semantic(item) for key, item in value.items()}
        if normalized.get("collection_kind") == UNORDERED_SET and "members" in normalized:
            members = normalized["members"]
            require_collection(members, "UNORDERED_SET members")
            normalized["members"] = sorted(members, key=canonical_json_bytes)
        return normalized
    if isinstance(value, list):
        return [canonical_semantic(item) for item in value]
    return value


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 JSON bytes of the canonical semantic projection."""

    return canonical_json_bytes(canonical_semantic(value))


def has_duplicate_members(members: Any) -> bool:
    """Return whether *members* holds two canonically equal members.

    The one place set multiplicity is decided. A canonical unordered set is a set: two
    members that serialise to the same canonical bytes are one member, and carrying both
    makes an identity depend on multiplicity a set does not have.

    Two shapes of declared set exist and both read this. An ``UNORDERED_SET`` wrapper is
    declared *in the record*, and is found by the recursive walk below. A Closure Policy
    semantic set is declared by its *fingerprint profile* rather than by a wrapper, and its
    duplicate only exists after the contract's projection has dropped the excluded fields --
    so the projection is applied first and the projected members are passed here. Comparing
    them by anything other than this function is how the two would come to disagree.
    """

    if not isinstance(members, list):
        return False
    canonical = [canonical_bytes(item) for item in members]
    return len(canonical) != len(set(canonical))


def has_recursive_set_duplicate(value: Any) -> bool:
    """Return whether any nested ``UNORDERED_SET`` holds duplicate canonical members."""

    if isinstance(value, dict):
        if any(has_recursive_set_duplicate(item) for item in value.values()):
            return True
        if value.get("collection_kind") == UNORDERED_SET:
            return has_duplicate_members(value.get("members", []))
        return False
    if isinstance(value, list):
        return any(has_recursive_set_duplicate(item) for item in value)
    return False


def unordered_set(members: list[Any]) -> dict[str, Any]:
    """Return a duplicate-free ``UNORDERED_SET`` wrapper in canonical member order."""

    projected = [canonical_semantic(item) for item in members]
    encoded = [canonical_json_bytes(item) for item in projected]
    if len(encoded) != len(set(encoded)):
        raise DifferenceError("unordered collection contains duplicate canonical members")
    return {
        "collection_kind": UNORDERED_SET,
        "members": [item for _, item in sorted(zip(encoded, projected, strict=True))],
    }


def content_address(prefix: str, record: dict[str, Any], identity_field: str) -> str:
    """Return the canonical content address of *record* excluding its identity field."""

    payload = {key: value for key, value in record.items() if key != identity_field}
    return prefix + hashlib.sha256(canonical_bytes(payload)).hexdigest().upper()


def reject_bare_arrays(value: Any, context: str) -> None:
    """Reject any bare JSON array reachable from an identity-bearing projection."""

    if isinstance(value, list):
        raise DifferenceError(f"bare JSON array is not an identity input at {context}")
    if isinstance(value, dict):
        kind = value.get("collection_kind")
        if kind is not None:
            # `in` hashes its operand, so a wrapper declaring an array or object as its
            # collection kind raised `unhashable type` one line before the rejection
            # written for it. A value that cannot be a tag names no declared kind, so the
            # tag is established first, by the one owner that answers that question.
            if not is_scalar_tag(kind) or kind not in COLLECTION_KINDS:
                raise DifferenceError(f"unknown collection_kind {kind!r} at {context}")
            if set(value) != {"collection_kind", "members"}:
                raise DifferenceError(f"collection wrapper carries unknown fields at {context}")
            for index, member in enumerate(value["members"]):
                reject_bare_arrays(member, f"{context}.members[{index}]")
            return
        for key, item in value.items():
            reject_bare_arrays(item, f"{context}.{key}")


def reject_secret_material(value: Any, context: str) -> None:
    """Reject secret-bearing keys or values anywhere inside *value*."""

    if isinstance(value, dict):
        for key, item in value.items():
            if (
                isinstance(key, str)
                and key not in _SECRET_KEY_ALLOWLIST
                and _SECRET_KEY.search(key)
            ):
                raise SecurityRejectionError(f"secret-bearing field {key!r} at {context}")
            reject_secret_material(item, f"{context}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            reject_secret_material(item, f"{context}[{index}]")
        return
    if isinstance(value, str) and _SECRET_VALUE.search(value):
        raise SecurityRejectionError(f"secret-bearing value at {context}")


def reject_moving_reference(reference: dict[str, Any], context: str) -> None:
    """Reject a typed reference whose identity is not immutable."""

    identity = reference.get("id")
    identity = require_scalar_tag(identity, f"reference identity at {context}")
    if MOVING_REFERENCE.search(identity):
        raise SecurityRejectionError(f"moving reference {identity!r} at {context}")


def walk_references(value: Any, context: str) -> None:
    """Reject every moving reference reachable from *value*."""

    if isinstance(value, dict):
        if isinstance(value.get("kind"), str) and isinstance(value.get("id"), str):
            reject_moving_reference(value, context)
        for key, item in value.items():
            walk_references(item, f"{context}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            walk_references(item, f"{context}[{index}]")
