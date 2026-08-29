"""MANOSUBE-STATE-SHA256-0.1 semantic fingerprint implementation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping

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
    project_state: Mapping[str, Any], *, schema_root: Path | None = None
) -> SemanticFingerprint:
    return _digest(canonical_semantic_state_bytes(project_state, schema_root=schema_root))


def fingerprint_semantic_state(
    semantic_state: Mapping[str, Any], *, schema_root: Path | None = None
) -> SemanticFingerprint:
    return _digest(canonical_semantic_value_bytes(semantic_state, schema_root=schema_root))


def verify_fingerprint(
    semantic_state: Mapping[str, Any],
    recorded: Mapping[str, Any],
    *,
    schema_root: Path | None = None,
) -> SemanticFingerprint:
    profile = recorded.get("profile")
    if profile != FINGERPRINT_PROFILE:
        raise FingerprintProfileError(f"unsupported fingerprint profile: {profile!r}")
    expected = fingerprint_semantic_state(semantic_state, schema_root=schema_root)
    if recorded.get("digest") != expected.digest:
        raise FingerprintMismatchError("recorded semantic fingerprint does not match")
    return expected
