from __future__ import annotations

from copy import deepcopy

from manosube_agent_civilization.state.canonicalize import canonical_semantic_state_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from tests.state_helpers import SCHEMA_ROOT, initial_state


def test_key_set_unicode_and_metadata_variations_converge() -> None:
    baseline = initial_state()
    variant = deepcopy(baseline)
    variant["semantic_state"] = dict(reversed(list(variant["semantic_state"].items())))
    refs = [
        {"kind": "difference", "id": "DIFF-0001"},
        {"kind": "difference", "id": "DIFF-0002"},
    ]
    baseline["semantic_state"]["open_differences"] = refs
    variant["semantic_state"]["open_differences"] = list(reversed(refs))
    baseline["semantic_state"]["project"]["claims"]["label"] = "é"
    variant["semantic_state"]["project"]["claims"]["label"] = "e\u0301"
    variant["state_metadata"]["producer"] = "other-model"
    variant["state_metadata"]["execution_context"]["session_id"] = "other-session"

    assert canonical_semantic_state_bytes(baseline, schema_root=SCHEMA_ROOT) == (
        canonical_semantic_state_bytes(variant, schema_root=SCHEMA_ROOT)
    )
    assert fingerprint_project_state(baseline, schema_root=SCHEMA_ROOT) == fingerprint_project_state(
        variant, schema_root=SCHEMA_ROOT
    )


def test_each_semantic_axis_changes_fingerprint() -> None:
    baseline = initial_state()
    baseline_fingerprint = fingerprint_project_state(baseline, schema_root=SCHEMA_ROOT)

    variants = []
    claim = deepcopy(baseline)
    claim["semantic_state"]["project"]["claims"]["bound"] = False
    variants.append(claim)

    status = deepcopy(baseline)
    status["semantic_state"]["runtime"]["status"] = "UNKNOWN"
    variants.append(status)

    difference = deepcopy(baseline)
    difference["semantic_state"]["open_differences"] = [
        {"kind": "difference", "id": "DIFF-0001"}
    ]
    variants.append(difference)

    for variant in variants:
        assert fingerprint_project_state(variant, schema_root=SCHEMA_ROOT) != baseline_fingerprint
