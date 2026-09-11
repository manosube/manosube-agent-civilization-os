"""MANOSUBE-STATE-SHA256-0.1 semantic fingerprint implementation.

Issue #75 (``D-KERNEL-VERIFIED-SCHEMA-BYTE-INJECTION``): each function here accepts the one
Kernel-owned :class:`~manosube_agent_civilization.schema_context.CanonicalSchemaContext` and
passes it straight through to :mod:`.canonicalize`, which owns the validation. The fingerprint
algorithm, its domain separator, and its profile are untouched
(``IDENTITY_ALGORITHM_CHANGE=false``, ``STATE_FINGERPRINT_CHANGE=false``) -- only the bytes
the schema validation preceding the digest is performed against can now be pinned.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping

from manosube_agent_civilization.schema_context import CanonicalSchemaContext

from .canonicalize import canonical_semantic_state_bytes, canonical_semantic_value_bytes
from .errors import FingerprintMismatchError, FingerprintProfileError

FINGERPRINT_PROFILE = "MANOSUBE-STATE-SHA256-0.1"
DOMAIN_SEPARATOR = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00STATE\x000.1\x00"


@dataclass(frozen=True, slots=True)
class SemanticFingerprint:
    """Profile-aware semantic content identity."""

    profile: str
    digest: str

    def as_dict(self) -> dict[str, str]:
        return {"profile": self.profile, "digest": self.digest}


def _digest(canonical_bytes: bytes) -> SemanticFingerprint:
    digest = hashlib.sha256(DOMAIN_SEPARATOR + canonical_bytes).hexdigest()
    return SemanticFingerprint(profile=FINGERPRINT_PROFILE, digest=digest)


def fingerprint_project_state(
    project_state: Mapping[str, Any],
    *,
    schema_root: Path | None = None,
    schema_context: CanonicalSchemaContext | None = None,
) -> SemanticFingerprint:
    return _digest(
        canonical_semantic_state_bytes(
            project_state, schema_root=schema_root, schema_context=schema_context
        )
    )


def fingerprint_semantic_state(
    semantic_state: Mapping[str, Any],
    *,
    schema_root: Path | None = None,
    schema_context: CanonicalSchemaContext | None = None,
) -> SemanticFingerprint:
    return _digest(
        canonical_semantic_value_bytes(
            semantic_state, schema_root=schema_root, schema_context=schema_context
        )
    )


def verify_fingerprint(
    semantic_state: Mapping[str, Any],
    recorded: Mapping[str, Any],
    *,
    schema_root: Path | None = None,
    schema_context: CanonicalSchemaContext | None = None,
) -> SemanticFingerprint:
    profile = recorded.get("profile")
    if profile != FINGERPRINT_PROFILE:
        raise FingerprintProfileError(f"unsupported fingerprint profile: {profile!r}")
    expected = fingerprint_semantic_state(
        semantic_state, schema_root=schema_root, schema_context=schema_context
    )
    if recorded.get("digest") != expected.digest:
        raise FingerprintMismatchError("recorded semantic fingerprint does not match")
    return expected
