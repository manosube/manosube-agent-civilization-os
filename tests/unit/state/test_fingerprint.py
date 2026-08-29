from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from manosube_agent_civilization.state.canonicalize import canonical_semantic_state_bytes
from manosube_agent_civilization.state.errors import (
    FingerprintMismatchError,
    FingerprintProfileError,
)
from manosube_agent_civilization.state.fingerprint import (
    DOMAIN_SEPARATOR,
    FINGERPRINT_PROFILE,
    fingerprint_project_state,
    verify_fingerprint,
)
from tests.state_helpers import SCHEMA_ROOT, initial_state


def test_fingerprint_uses_exact_domain_separated_sha256() -> None:
    state = initial_state()
    canonical = canonical_semantic_state_bytes(state, schema_root=SCHEMA_ROOT)
    expected = hashlib.sha256(DOMAIN_SEPARATOR + canonical).hexdigest()
    actual = fingerprint_project_state(state, schema_root=SCHEMA_ROOT)
    assert actual.profile == FINGERPRINT_PROFILE
    assert actual.digest == expected
    assert len(actual.digest) == 64
    assert actual.digest == actual.digest.lower()


def test_metadata_agent_and_session_changes_do_not_change_fingerprint() -> None:
    left = initial_state()
    right = deepcopy(left)
    right["state_metadata"]["observed_at"] = "2026-08-30T00:00:00Z"
    right["state_metadata"]["producer"] = "model-b"
    right["state_metadata"]["execution_context"]["session_id"] = "session-b"
    assert fingerprint_project_state(left, schema_root=SCHEMA_ROOT) == fingerprint_project_state(
        right, schema_root=SCHEMA_ROOT
    )


def test_semantic_change_changes_fingerprint() -> None:
    left = initial_state()
    right = deepcopy(left)
    right["semantic_state"]["runtime"]["status"] = "KNOWN"
    assert fingerprint_project_state(left, schema_root=SCHEMA_ROOT) != fingerprint_project_state(
        right, schema_root=SCHEMA_ROOT
    )


def test_unknown_profile_is_rejected() -> None:
    state = initial_state()["semantic_state"]
    with pytest.raises(FingerprintProfileError):
        verify_fingerprint(state, {"profile": "UNKNOWN", "digest": "0" * 64}, schema_root=SCHEMA_ROOT)


def test_tampered_digest_is_rejected_without_repair() -> None:
    state = initial_state()["semantic_state"]
    recorded = {"profile": FINGERPRINT_PROFILE, "digest": "0" * 64}
    before = dict(recorded)
    with pytest.raises(FingerprintMismatchError):
        verify_fingerprint(state, recorded, schema_root=SCHEMA_ROOT)
    assert recorded == before


def test_matching_digest_is_verified() -> None:
    project = initial_state()
    expected = fingerprint_project_state(project, schema_root=SCHEMA_ROOT)
    assert verify_fingerprint(
        project["semantic_state"], expected.as_dict(), schema_root=SCHEMA_ROOT
    ) == expected
