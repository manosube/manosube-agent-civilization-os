"""Deterministic Evidence identities.

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and
this module reads it rather than restating it, exactly as ``change/identity.py`` does. What
is defined here is only *which payload* an Evidence identity is computed over.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: What an Evidence record *is*: which position it holds, when it was recorded, about what,
#: against which States, by which method, on which Change and Authority, what was expected,
#: what was observed, how it ended, what backs it, where it came from, and what it leaves
#: open.
#:
#: Every field of 第28条 is here, and so are the three this repository adds. That is not
#: incidental. ``E-003 EVIDENCE_IMMUTABLE`` requires accepted Evidence to be immutable, and
#: immutability is only enforceable if the address covers the whole meaning: a projection
#: that omitted ``status`` or ``observed_result`` would let a record be rewritten into a
#: different claim while keeping its address, which is overwriting Evidence with extra steps.
#:
#: Contrast ``CHANGE_SEMANTIC_FIELDS``, which deliberately excludes ``status``. A Change that
#: is later executed is the same Change. An Evidence record that later says something else is
#: a different Evidence record.
EVIDENCE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "evidence_position",
    "timestamp",
    "target",
    "before_state",
    "observation_method",
    "change_identity",
    "authority_used",
    "after_state",
    "expected_result",
    "observed_result",
    "status",
    "artifact_references",
    "lineage",
    "remaining_differences",
    "evidence_level",
)


def _semantic_projection(evidence: dict[str, Any]) -> dict[str, Any]:
    return {field: evidence[field] for field in EVIDENCE_SEMANTIC_FIELDS}


def evidence_semantic_fingerprint(evidence: dict[str, Any]) -> str:
    """The digest of an Evidence record's meaning."""

    return (
        "sha256:" + hashlib.sha256(canonical_json_bytes(_semantic_projection(evidence))).hexdigest()
    )


def evidence_id(evidence: dict[str, Any]) -> str:
    """The content address of an Evidence record."""

    return (
        "EVIDENCE-"
        + hashlib.sha256(canonical_json_bytes(_semantic_projection(evidence))).hexdigest().upper()
    )
