"""Deterministic identities for canonical Observation records."""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

_DOMAIN = b"MANOSUBE_AGENT_CIVILIZATION_OS\x00OBSERVATION\x000.1\x00"


def deterministic_id(prefix: str, value: Any) -> str:
    """Return a stable, domain-separated identity for canonical *value*."""

    digest = hashlib.sha256(_DOMAIN + canonical_json_bytes(value)).hexdigest().upper()
    return f"{prefix}-{digest}"
