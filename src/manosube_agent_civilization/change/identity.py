"""Deterministic Change identities.

Canonical serialization has one owner in this repository -- ``state.canonicalize`` -- and this
module reads it rather than restating it, exactly as ``authority/identity.py`` does. What is
defined here is only *which payload* each Change identity is computed over.
"""

from __future__ import annotations

import hashlib
from typing import Any

from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

#: What a Change *is*: which project, from which Difference, on which Authority decision,
#: against which State, doing what, where.
#:
#: ``status`` and ``execution_result`` are deliberately **excluded**. They are lifecycle, not
#: identity: a Change that is later executed is the same Change, and if its address moved
#: when its status did, nothing downstream could refer to it across that boundary.
#: ``KERNEL_CONSTITUTION.md`` 第26条 requires a duplicate Change to be idempotent, which is
#: only expressible if the address is a function of the Change's meaning alone.
CHANGE_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "difference_ref",
    "authority_ref",
    "before_state_fingerprint",
    "expected_state_revision",
    "action",
    "scope",
)


def _semantic_projection(change: dict[str, Any]) -> dict[str, Any]:
    return {field: change[field] for field in CHANGE_SEMANTIC_FIELDS}


def change_semantic_fingerprint(change: dict[str, Any]) -> str:
    """The digest of a Change's meaning."""

    return "sha256:" + hashlib.sha256(
        canonical_json_bytes(_semantic_projection(change))
    ).hexdigest()


def change_id(change: dict[str, Any]) -> str:
    """The content address of a Change."""

    return "CHANGE-" + hashlib.sha256(
        canonical_json_bytes(_semantic_projection(change))
    ).hexdigest().upper()


def idempotency_key(change: dict[str, Any]) -> str:
    """The key an executor deduplicates on. 第24条 requires it; 第26条 says what it must do.

    It is the same projection as the address, in the encoding executors expect, and the two
    are therefore **one-to-one by construction**. That is the point rather than a redundancy:
    ``DUPLICATE_CHANGE_IDEMPOTENT`` is true because deriving the same Change twice cannot
    produce two keys, and it could not be guaranteed by a key generated from anything else --
    a counter, a clock or a random value would make the second derivation a different Change.
    """

    return change_semantic_fingerprint(change)
