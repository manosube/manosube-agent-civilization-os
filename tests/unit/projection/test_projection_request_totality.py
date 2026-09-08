"""Phase 14 (Issue #62): the ``PROJECTION_INPUT`` opaque-location generated coverage
``difference.admissibility.UNCONSTRAINED_CONTRACT_LOCATIONS`` names when it tags a Projection
Envelope's own ``projection_payload`` (``projection/projection_envelope.schema.json``).

The identical declaration-and-sweep pattern ``tests/unit/evidence/test_request_totality.py``
already uses for its own ``VERIFICATION_INPUT`` locations, applied here: a real, JSON-shaped
payload is built once, every reachable location inside it (the generic recursive sweep
reaches every nested path) is deleted and retyped, and both
:func:`~manosube_agent_civilization.projection.identity.projection_payload_fingerprint` (the
one place a payload's own content is canonicalized) and
:func:`~manosube_agent_civilization.projection.engine.derive_projection_envelope` must always
answer: a typed :class:`~manosube_agent_civilization.state.errors.CanonicalizationError` or
:class:`~manosube_agent_civilization.projection.errors.ProjectionError` refusal, or a
schema-valid Envelope. Never a raw ``TypeError`` or ``KeyError``.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from manosube_agent_civilization.projection.engine import derive_projection_envelope
from manosube_agent_civilization.projection.errors import ProjectionError
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.state.errors import CanonicalizationError

#: Values chosen because each one reaches a *different* operation in the canonicalizer: a
#: hash, a sort key, a mapping subscript, a membership test, a truth test, a length --
#: identical rationale to ``tests/unit/evidence/test_request_totality.py``'s own set.
SUBSTITUTIONS: tuple[Any, ...] = (
    None,
    True,
    0,
    -1,
    "",
    "unexpected",
    [],
    [None],
    {},
    {"kind": "unexpected"},
    float("nan"),
    {"secret": "leaked"},
)

_PAYLOAD: dict[str, Any] = {
    "title": "Evidence artifact",
    "body": "A real GitHub artifact payload, schema-opaque to this Kernel.",
    "labels": ["projection", "phase-14"],
    "metadata": {"source": "manosube_agent_civilization.projection", "revision": 1},
}

_SUBJECT_REF = {"kind": "observation_evidence", "id": "EVIDENCE-AAAA"}
_SUBJECT_FINGERPRINT = "sha256:" + "a" * 64
_TARGET_REPOSITORY = {"host": "github", "owner": "acme", "repo": "widget"}
_EXTERNAL_ARTIFACT_REF = {
    "host": "github",
    "owner": "acme",
    "repo": "widget",
    "artifact_kind": "artifact",
    "external_id": "1",
    "url": "https://github.com/acme/widget/artifact/1",
}
_AUTHORITY_REF = {"kind": "human_authority", "id": "AUTH-0001"}


def _locations(value: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    found = [path] if path else []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(_locations(child, (*path, key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_locations(child, (*path, index)))
    return found


_PAYLOAD_LOCATIONS: list[tuple[Any, ...]] = _locations(_PAYLOAD)


def _at(payload: dict[str, Any], path: tuple[Any, ...]) -> Any:
    target: Any = payload
    for step in path[:-1]:
        target = target[step]
    return target


def _fingerprint_answer(payload: dict[str, Any]) -> str:
    """Return how the canonicalizer answered. A raw, untyped exception is not an answer and
    propagates -- the test itself fails, rather than silently passing on a masked crash."""

    try:
        projection_payload_fingerprint(payload)
    except CanonicalizationError:
        return "REJECTED"
    return "FINGERPRINTED"


def _envelope_answer(payload: dict[str, Any]) -> str:
    try:
        derive_projection_envelope(
            subject_ref=_SUBJECT_REF,
            subject_fingerprint=_SUBJECT_FINGERPRINT,
            projection_kind="EVIDENCE_ARTIFACT",
            target_repository=_TARGET_REPOSITORY,
            projection_payload=payload,
            projection_payload_fingerprint="sha256:" + "0" * 64,
            external_artifact_ref=_EXTERNAL_ARTIFACT_REF,
            github_authority_ref=_AUTHORITY_REF,
            materialized_at="2026-01-01T00:00:00Z",
            claim_token="PROJECTION-ATTEMPT-TOTALITY-0001",  # noqa: S106
        )
    except (ProjectionError, CanonicalizationError):
        return "REJECTED"
    return "DERIVED"


def test_the_payload_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(_PAYLOAD_LOCATIONS) >= 6, len(_PAYLOAD_LOCATIONS)


def test_the_base_payload_fingerprints_and_derives() -> None:
    assert _fingerprint_answer(deepcopy(_PAYLOAD)) == "FINGERPRINTED"
    assert _envelope_answer(deepcopy(_PAYLOAD)) == "DERIVED"


@pytest.mark.parametrize(
    "path", _PAYLOAD_LOCATIONS, ids=lambda path: ".".join(str(step) for step in path)
)
def test_every_payload_location_answers_when_deleted(path: tuple[Any, ...]) -> None:
    payload = deepcopy(_PAYLOAD)
    target = _at(payload, path)
    before = deepcopy(target)
    del target[path[-1]]
    assert target != before, path
    assert _fingerprint_answer(deepcopy(payload)) in ("REJECTED", "FINGERPRINTED")
    assert _envelope_answer(deepcopy(payload)) in ("REJECTED", "DERIVED")


@pytest.mark.parametrize("value", SUBSTITUTIONS)
@pytest.mark.parametrize(
    "path", _PAYLOAD_LOCATIONS, ids=lambda path: ".".join(str(step) for step in path)
)
def test_every_payload_location_answers_when_retyped(path: tuple[Any, ...], value: Any) -> None:
    payload = deepcopy(_PAYLOAD)
    _at(payload, path)[path[-1]] = deepcopy(value)
    assert _fingerprint_answer(deepcopy(payload)) in ("REJECTED", "FINGERPRINTED")
    assert _envelope_answer(deepcopy(payload)) in ("REJECTED", "DERIVED")
