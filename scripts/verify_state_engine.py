"""Executable conformance evidence for the v0.1 state serializer and fingerprint."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys

from manosube_agent_civilization.state.canonicalize import (
    canonical_json_bytes,
    canonical_semantic_state_bytes,
)
from manosube_agent_civilization.state.errors import CanonicalizationError
from manosube_agent_civilization.state.fingerprint import (
    FINGERPRINT_PROFILE,
    fingerprint_project_state,
    verify_fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def initial_state() -> dict[str, object]:
    cases = json.loads(
        (ROOT / "tests/contract/fixtures/schema/valid/cases.json").read_text(
            encoding="utf-8"
        )
    )
    return next(case["instance"] for case in cases if case["name"] == "initial_state_revision_zero")


def must_reject(name: str, value: object) -> None:
    try:
        canonical_json_bytes(value)
    except CanonicalizationError:
        return
    raise AssertionError(f"invalid vector escaped: {name}")


def main() -> int:
    vector_count = 0
    invalid_escape_count = 0

    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})
    vector_count += 1
    assert canonical_json_bytes({"label": "e\u0301"}) == canonical_json_bytes({"label": "é"})
    vector_count += 1
    assert canonical_json_bytes({"ordered": [1, 2]}) != canonical_json_bytes({"ordered": [2, 1]})
    vector_count += 1

    left = initial_state()
    right = deepcopy(left)
    refs = [{"kind": "difference", "id": "DIFF-0002"}, {"kind": "difference", "id": "DIFF-0001"}]
    left["semantic_state"]["open_differences"] = refs
    right["semantic_state"]["open_differences"] = list(reversed(refs))
    right["state_metadata"]["observed_at"] = "2026-08-30T00:00:00Z"
    right["state_metadata"]["producer"] = "other-agent"
    right["state_metadata"]["execution_context"]["session_id"] = "other-session"
    assert canonical_semantic_state_bytes(left, schema_root=SCHEMA_ROOT) == canonical_semantic_state_bytes(right, schema_root=SCHEMA_ROOT)
    assert fingerprint_project_state(left, schema_root=SCHEMA_ROOT) == fingerprint_project_state(right, schema_root=SCHEMA_ROOT)
    vector_count += 2

    changed = deepcopy(left)
    changed["semantic_state"]["runtime"]["status"] = "KNOWN"
    assert fingerprint_project_state(left, schema_root=SCHEMA_ROOT) != fingerprint_project_state(changed, schema_root=SCHEMA_ROOT)
    vector_count += 1

    expected = fingerprint_project_state(left, schema_root=SCHEMA_ROOT)
    assert expected.profile == FINGERPRINT_PROFILE and len(expected.digest) == 64
    assert verify_fingerprint(left["semantic_state"], expected.as_dict(), schema_root=SCHEMA_ROOT) == expected
    vector_count += 2

    invalid_values = {
        "float": 1.5,
        "nan": float("nan"),
        "infinity": float("inf"),
        "negative_zero": -0.0,
        "bytes": b"x",
        "tuple": (1, 2),
        "set": {1, 2},
        "custom": object(),
        "non_string_key": {1: "x"},
        "invalid_unicode": {"value": "\ud800"},
        "secret": {"api-key": "redacted"},
        "duplicate_set": {"evidence_refs": [{"kind": "evidence", "id": "EVID-1"}] * 2},
    }
    for name, value in invalid_values.items():
        try:
            must_reject(name, value)
        except AssertionError:
            invalid_escape_count += 1
        vector_count += 1

    if invalid_escape_count:
        raise AssertionError(f"INVALID_INPUT_ESCAPE_COUNT={invalid_escape_count}")
    print(f"CONFORMANCE_VECTOR_COUNT={vector_count}")
    print(f"INVALID_INPUT_ESCAPE_COUNT={invalid_escape_count}")
    print("METADATA_VARIATION_FINGERPRINT_EQUAL=true")
    print("AGENT_VARIATION_FINGERPRINT_EQUAL=true")
    print("SESSION_VARIATION_FINGERPRINT_EQUAL=true")
    print("SEMANTIC_VARIATION_FINGERPRINT_DIFFERENT=true")
    print("STATE_SERIALIZABLE=true")
    print("STATE_DETERMINISTIC=true")
    print("SEMANTIC_FINGERPRINT_STABLE=true")
    print("STATE_ENGINE_CONFORMANCE=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
