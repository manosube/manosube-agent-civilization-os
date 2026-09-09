"""What GitHub can actually attest to for each projection kind (Phase 14, Structural Review
Round 1, Issue #62, P14-R1-F3).

The full committed ``projection_payload`` is never itself the thing an external GitHub
artifact's own read API echoes back -- a Pull Request's ``head_ref``/``base_ref`` are visible,
but nothing about *why* the branch was created is; a Check Run's ``output.text`` is often not
returned by a plain ``GET``. Comparing the whole payload against whatever an adapter reports
would either compare fields no read API could ever confirm (a permanent, spurious mismatch),
or -- if a caller silently narrowed the comparison to whatever fields happened to match --
quietly stop checking the rest.

This module is the one place that says, per projection kind, exactly which ``projection_payload``
fields are the closed *observable projection* -- and is shared, unchanged, by
:mod:`~manosube_agent_civilization.projection.route` (which recomputes the *expected* fingerprint
from the real, committed payload) and every :class:`~manosube_agent_civilization.projection.
types.GitHubAdapter` implementation (which must compute its own *observed* fingerprint the
identical way, from what it actually reads back) -- so a real content mismatch is the only thing
that can make the two disagree.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from .errors import ProjectionAdapterError, ProjectionRequirementError
from .identity import projection_payload_fingerprint
from .types import OBSERVATION_OUTCOME_KINDS

if TYPE_CHECKING:
    from .types import GitHubAdapter

#: The closed, per-projection-kind subset of ``projection_payload`` an external GitHub
#: artifact's own read API can actually attest to. Adding a projection kind without adding it
#: here means it has no observable comparison, and F3's own tamper-detection proof cannot run
#: for it -- the identical "no admission path, no reachable decision" discipline
#: ``authority/conformance.py``'s own ``RECORD_TYPES`` registry already documents.
OBSERVABLE_FIELDS: dict[str, tuple[str, ...]] = {
    "DIFFERENCE_ISSUE": ("title", "body"),
    "CHANGE_PULL_REQUEST": ("title", "body", "head_ref", "base_ref"),
    "EVIDENCE_ARTIFACT": ("name", "head_sha", "status", "conclusion", "output"),
}

#: The reverse of ``FakeGitHubAdapter``'s/``RealGitHubAdapter``'s own projection_kind ->
#: artifact_kind mapping (``route.py``'s own ``_REQUIRED_SUBJECT_KIND`` sibling table) --
#: needed because :meth:`~manosube_agent_civilization.projection.types.GitHubAdapter.observe`
#: receives only ``external_artifact_ref``, never ``projection_kind`` directly, and must
#: still select the correct observable-field subset for whatever it reads back. Three distinct
#: artifact kinds (``check_run``/``review``/``artifact``) all name the one Evidence
#: projection kind -- a real many-to-one relationship, not an ambiguity, since Issue #62's own
#: Evidence projection kind spans all three GitHub surfaces (§"Canonical route").
ARTIFACT_KIND_TO_PROJECTION_KIND: dict[str, str] = {
    "issue": "DIFFERENCE_ISSUE",
    "pull_request": "CHANGE_PULL_REQUEST",
    "check_run": "EVIDENCE_ARTIFACT",
    "review": "EVIDENCE_ARTIFACT",
    "artifact": "EVIDENCE_ARTIFACT",
}


def expected_observable_projection(projection_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Return the closed subset of *payload* GitHub's own read API can attest to."""

    fields = OBSERVABLE_FIELDS.get(projection_kind)
    if fields is None:
        raise ProjectionRequirementError(
            f"projection_kind has no observable projection defined: {projection_kind!r}"
        )
    return {field: payload.get(field) for field in fields}


def expected_observable_fingerprint(projection_kind: str, payload: dict[str, Any]) -> str:
    """Return the deterministic digest of *payload*'s own observable projection.

    Computed with the identical :func:`~manosube_agent_civilization.projection.identity.
    projection_payload_fingerprint` every other Projection fingerprint uses, so a real
    :class:`~manosube_agent_civilization.projection.types.GitHubAdapter` and this route's own
    independent recomputation can only ever agree when the artifact genuinely still carries
    what was committed.
    """

    return projection_payload_fingerprint(expected_observable_projection(projection_kind, payload))


def observe_and_classify(
    adapter: GitHubAdapter,
    *,
    external_artifact_ref: Mapping[str, Any],
    projection_kind: str,
    committed_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Call *adapter*'s own ``observe`` exactly once and classify the result into one of
    ``VERIFIED``/``FAILED``/``UNAVAILABLE`` -- the one shared observation-and-classification
    body :mod:`~manosube_agent_civilization.projection.route` (materialize-time observation)
    and :mod:`~manosube_agent_civilization.projection.receipt_handoff` (Structural Review
    Round 3, P14-R3-F2's own independent re-observation at handoff) both call, so a real
    content mismatch is the only thing that can ever produce a different classification
    between the two call sites.

    Structural Review Round 1 (P14-R1-F3): the adapter's own reported status is never
    trusted for a ``FOUND`` outcome -- this function independently recomputes the expected
    observable fingerprint from *committed_payload* and compares it against what the adapter
    reports, forcing a non-``VERIFIED`` result on any mismatch. Structural Review Round 1
    (P14-R1-F6): the adapter's own ``observation_outcome`` is required to be one of
    :data:`~manosube_agent_civilization.projection.types.OBSERVATION_OUTCOME_KINDS`; only
    ``NOT_FOUND`` establishes absence, and ``PERMISSION_DENIED``/``UNAVAILABLE`` both leave
    existence undetermined rather than being folded into a false absence or a false
    confirmation.

    Returns a mapping carrying ``observation_outcome``, ``exists``,
    ``observed_content_fingerprint``, ``observed_at``, and the derived ``status``.
    """

    result = adapter.observe(external_artifact_ref=external_artifact_ref)
    if not isinstance(result, Mapping):
        raise ProjectionAdapterError(f"adapter.observe() returned {result!r}, not a mapping")
    outcome = result.get("observation_outcome")
    if outcome not in OBSERVATION_OUTCOME_KINDS:
        raise ProjectionAdapterError(
            f"adapter.observe()'s own 'observation_outcome' is not recognized: {outcome!r}"
        )
    observed_content_fingerprint = result.get("observed_content_fingerprint")
    observed_at = result.get("observed_at")

    if outcome == "FOUND":
        if not isinstance(observed_content_fingerprint, str) or not observed_content_fingerprint:
            raise ProjectionAdapterError(
                "adapter.observe() reported FOUND with no observed_content_fingerprint: "
                f"{observed_content_fingerprint!r}"
            )
        expected_fingerprint = expected_observable_fingerprint(
            projection_kind, dict(committed_payload)
        )
        exists: bool | None = True
        status = "VERIFIED" if observed_content_fingerprint == expected_fingerprint else "FAILED"
    elif outcome == "NOT_FOUND":
        exists = False
        status = "FAILED"
    else:  # PERMISSION_DENIED / UNAVAILABLE -- existence itself is undetermined
        exists = None
        status = "UNAVAILABLE"

    return {
        "observation_outcome": outcome,
        "exists": exists,
        "observed_content_fingerprint": observed_content_fingerprint,
        "observed_at": observed_at,
        "status": status,
    }
