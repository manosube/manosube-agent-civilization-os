"""The one public Runtime Observation route (Phase 15, Issue #64).

``RUNTIME_OWNER_COUNT=1``, ``PUBLIC_RUNTIME_ENTRY_POINT_COUNT=1`` (this module) ``+1``
(:mod:`~manosube_agent_civilization.runtime.evidence_handoff`'s own single hand-off route).

``observe_runtime_target`` re-verifies Project/Human Authority identity through the existing
Boot owner (:func:`~manosube_agent_civilization.boot.boot_project`), independently fingerprints
an explicit runtime target identity and a closed Observation Boundary (never trusting either
from a caller beyond their declared shape), refuses an observation whose own request instant
falls outside the Boundary's own declared time window before ever reaching an adapter, calls
the one replaceable :class:`~manosube_agent_civilization.runtime.types.RuntimeAdapter` exactly
once, and independently reclassifies whatever transport-level facts it reports into the full,
closed outcome vocabulary -- ``NEGATIVE`` and ``IDENTITY_MISMATCH`` are computed here alone,
never accepted from the adapter's own report. It then derives and commits one canonical Runtime
Observation Envelope through the existing Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow, Binding, and Projection already share) and returns an ephemeral, in-memory
:class:`~manosube_agent_civilization.runtime.types.RuntimeObservationReceipt`.

Read-only, so no create-once-reuse-after side effect exists to protect: unlike Projection,
this route derives no intent/materialize-attempt claim pair (see
:mod:`~manosube_agent_civilization.runtime.engine`'s own module docstring) and commits exactly
one new Envelope per call -- observing the identical target under the identical Boundary twice
is two independent facts, not a duplicate external artifact.

Canonical route (``10_RUNTIME/RUNTIME_CONTRACT.md`` §5):

```text
real Project/Human Authority (Boot re-verification)
→ explicit runtime target identity, fingerprinted (never trusted from a caller)
→ closed Observation Boundary, fingerprinted (never trusted from a caller)
→ time-window check -- refuses before any adapter call once expired
→ deterministic observation_request_identity (target + Boundary + issued_at)
→ replaceable Runtime Adapter -- one bounded transport call
→ independent content/identity reclassification (NEGATIVE/IDENTITY_MISMATCH computed here,
  never accepted from the adapter's own report; redaction applied before any fingerprint or
  persistence)
→ canonical Runtime Observation Envelope
→ existing canonical persistence boundary (commit_state_transition)
→ bounded Runtime Observation Receipt
```
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import RUNTIME_SCHEMA_BASE, derive_runtime_observation_envelope
from .errors import RuntimeAdapterError, RuntimeEnvelopeIntegrityError, RuntimeRequirementError
from .identity import (
    runtime_observation_boundary_fingerprint,
    runtime_observation_envelope_semantic_fingerprint,
    runtime_observation_request_identity,
    runtime_observed_content_fingerprint,
    runtime_target_fingerprint,
)
from .types import (
    RUNTIME_ADAPTER_TRANSPORT_OUTCOMES,
    RUNTIME_OBSERVATION_METHODS,
    RUNTIME_OUTCOME_TO_RECEIPT_STATUS,
    RuntimeAdapter,
    RuntimeObservationReceipt,
)

_ENVELOPE_RECORD_KIND = "runtime_observation_envelope"
#: The identical Compare-And-Swap retry bound Projection's own ``_claim_slot`` uses -- not a
#: timeout, not a backoff, bounded protection against genuine, ordinary contention from an
#: unrelated commit landing on this project between this route's own ``load_current`` and its
#: own ``commit``.
_MAX_COMMIT_RETRIES = 8


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise RuntimeRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise RuntimeRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"{context} must be an explicit reference object: {value!r}")
    if value.get("kind") != kind:
        raise RuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise RuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    return dict(value)


def _require_target_identity(value: Any, *, project_binding_id: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"target_identity must be an explicit mapping: {value!r}")
    for key in ("provider", "deployment_id", "instance_identity", "deployment_fingerprint"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise RuntimeRequirementError(f"target_identity.{key} must be a non-empty string")
    project_binding_ref = _require_reference(
        value.get("project_binding_ref"),
        context="target_identity.project_binding_ref",
        kind="project_binding",
    )
    # Substituted-Binding refusal (Issue #64 V4): a target declaring a different Project
    # Binding than the one this call itself re-verified through Boot must never be observed
    # under this project's own identity -- exactly the cross-project/cross-binding exact
    # reference-equality discipline every other owner in this repository already applies.
    if project_binding_ref["id"] != project_binding_id:
        raise RuntimeRequirementError(
            "target_identity.project_binding_ref does not name the requested "
            f"project_binding_id: {project_binding_ref['id']!r} != {project_binding_id!r}"
        )
    return dict(value)


def _require_boundary(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeRequirementError(f"boundary must be an explicit mapping: {value!r}")
    if value.get("observation_method") not in RUNTIME_OBSERVATION_METHODS:
        raise RuntimeRequirementError(
            f"boundary.observation_method is not recognized: {value.get('observation_method')!r}"
        )
    time_window = value.get("time_window")
    if not isinstance(time_window, Mapping):
        raise RuntimeRequirementError(
            f"boundary.time_window must be an explicit mapping: {time_window!r}"
        )
    for key in ("issued_at", "expires_at"):
        if not isinstance(time_window.get(key), str) or not time_window[key]:
            raise RuntimeRequirementError(f"boundary.time_window.{key} must be a non-empty string")
    permitted_fields = value.get("permitted_fields")
    if not isinstance(permitted_fields, list) or not permitted_fields:
        raise RuntimeRequirementError(
            f"boundary.permitted_fields must be a non-empty list: {permitted_fields!r}"
        )
    return dict(value)


def _require_within_time_window(boundary: dict[str, Any], observed_at: str) -> None:
    """Refuse before any adapter call once *observed_at* falls outside the Boundary's own
    declared, closed time window -- string comparison is sound here because every timestamp
    in this schema is required to be the identical ISO-8601 UTC ``Z``-suffixed encoding
    (``common/timestamp.schema.json``), which sorts lexicographically in chronological order.
    """

    issued_at = boundary["time_window"]["issued_at"]
    expires_at = boundary["time_window"]["expires_at"]
    if not (issued_at <= observed_at <= expires_at):
        raise RuntimeRequirementError(
            f"observed_at {observed_at!r} falls outside the Boundary's own declared time "
            f"window [{issued_at!r}, {expires_at!r}] -- refusing before any adapter call"
        )


def _redact(observed_fields: Mapping[str, Any], redaction_fields: list[str]) -> dict[str, Any]:
    redacted = set(redaction_fields)
    return {
        field: ("<REDACTED>" if field in redacted else value)
        for field, value in observed_fields.items()
    }


def observe_runtime_target(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    target_identity: Mapping[str, Any],
    boundary: Mapping[str, Any],
    adapter: RuntimeAdapter,
    observed_at: str,
) -> dict[str, Any]:
    """Bounded-observe one explicit runtime target and return ``{"envelope": ...,
    "receipt": RuntimeObservationReceipt}``.

    *target_identity* and *boundary* must already be real, explicit, closed shapes -- this
    function fingerprints them itself (never trusting a caller-declared fingerprint), and
    requires *target_identity*'s own ``project_binding_ref`` to name *project_binding_id*
    exactly. *observed_at* is a required, caller-supplied instant (this route reads no clock,
    the identical discipline every other route in this repository already requires) that must
    fall within *boundary*'s own declared, closed time window -- an observation whose own
    instant already falls outside that window refuses before the adapter is ever called.

    See ``10_RUNTIME/RUNTIME_CONTRACT.md`` §5 for the full canonical route this function
    implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    _require_canonical_identity("observed_at", observed_at)

    checked_boundary = _require_boundary(boundary)
    checked_target_identity = _require_target_identity(
        target_identity, project_binding_id=project_binding_id
    )
    _require_within_time_window(checked_boundary, observed_at)

    # Project/Human Authority re-verification through the existing Boot owner -- this route
    # mints no Authority Decision of its own (Runtime Observation is bounded by the closed
    # Observation Boundary itself, never by a write-permission grant; see this delivery's own
    # disclosed judgment call in ``10_RUNTIME/RUNTIME_CONTRACT.md`` §4). Every
    # ``boot_project`` failure propagates unchanged; this route calls the adapter zero times
    # on any such rejection.
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)

    target_fingerprint = runtime_target_fingerprint(checked_target_identity)
    boundary_fingerprint = runtime_observation_boundary_fingerprint(checked_boundary)
    observation_request_identity = runtime_observation_request_identity(
        target_fingerprint, boundary_fingerprint, checked_boundary["time_window"]["issued_at"]
    )

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise RuntimeAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated "
            "or unverifiable identity may never observe on this route's behalf"
        )

    raw = adapter.observe(target_identity=checked_target_identity, boundary=checked_boundary)
    if not isinstance(raw, Mapping):
        raise RuntimeAdapterError(f"adapter.observe() returned {raw!r}, not a mapping")
    transport_outcome = raw.get("transport_outcome")
    if transport_outcome not in RUNTIME_ADAPTER_TRANSPORT_OUTCOMES:
        raise RuntimeAdapterError(
            f"adapter.observe()'s own transport_outcome is not recognized: {transport_outcome!r}"
        )

    if transport_outcome == "OBSERVED":
        raw_observed_fields = raw.get("observed_fields")
        if not isinstance(raw_observed_fields, Mapping):
            raise RuntimeAdapterError(
                "adapter.observe() reported OBSERVED with no readable observed_fields: "
                f"{raw_observed_fields!r}"
            )
        observed_deployment_identity = raw.get("observed_deployment_identity")

        # Redaction happens before any fingerprint or persistence -- Issue #64's own V4
        # credential-leakage proof requires a redacted field to never appear, in any form,
        # in what this route fingerprints or commits.
        observed_fields = _redact(
            raw_observed_fields, list(checked_boundary.get("redaction_fields", []))
        )
        observed_content_fingerprint: str | None = runtime_observed_content_fingerprint(
            observed_fields
        )

        # Structural discipline (Issue #64 V2/V4): the adapter's own transport-level
        # ``OBSERVED`` report is never itself trusted as "this is genuinely the declared
        # target, and its content is genuinely positive" -- both are independently
        # recomputed/compared here, never accepted from the adapter's own say-so.
        if observed_deployment_identity != checked_target_identity["deployment_fingerprint"]:
            observation_outcome = "IDENTITY_MISMATCH"
        elif "expected_field" in checked_boundary and (
            observed_fields.get(checked_boundary["expected_field"])
            != checked_boundary.get("expected_value")
        ):
            observation_outcome = "NEGATIVE"
        else:
            observation_outcome = "OBSERVED"
    else:
        # A transport failure (NOT_FOUND/PERMISSION_DENIED/TIMEOUT/UNAVAILABLE/MALFORMED)
        # is committed exactly as the adapter honestly reported it -- never folded into
        # NEGATIVE, never promoted to OBSERVED, and never silently discarded as an absence
        # unless the adapter itself reported the one outcome that means that (NOT_FOUND).
        observation_outcome = transport_outcome
        observed_fields = None
        observed_content_fingerprint = None

    envelope = derive_runtime_observation_envelope(
        project_id=project_id,
        target_identity=checked_target_identity,
        target_fingerprint=target_fingerprint,
        boundary=checked_boundary,
        boundary_fingerprint=boundary_fingerprint,
        observation_request_identity=observation_request_identity,
        observed_at=observed_at,
        observation_outcome=observation_outcome,
        observed_fields=observed_fields,
        observed_content_fingerprint=observed_content_fingerprint,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
    )

    _commit_envelope(store, project_id, envelope, observed_at)

    receipt = RuntimeObservationReceipt(
        status=RUNTIME_OUTCOME_TO_RECEIPT_STATUS[observation_outcome],
        runtime_observation_envelope_id=envelope["runtime_observation_envelope_id"],
        project_id=project_id,
        target_identity=checked_target_identity,
        boundary=checked_boundary,
        adapter_identity=dict(declared_identity),
        human_authority_ref=real_human_authority_ref,
        input_refs=(dict(checked_target_identity["project_binding_ref"]),),
        observations={
            "observation_outcome": observation_outcome,
            "observed_content_fingerprint": observed_content_fingerprint,
            "observed_at": observed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


def _commit_envelope(
    store: Any, project_id: str, envelope: dict[str, Any], committed_at: str
) -> None:
    """Durably persist *envelope* through the Store's own single sanctioned committer,
    bounded Compare-And-Swap retry against genuine, unrelated contention only (Issue #64 V4's
    own "unrelated Store mutation between calls still refuses/succeeds correctly" proof) --
    the identical discipline :func:`~manosube_agent_civilization.projection.route._claim_slot`
    already establishes.

    A record already resolved at this exact (kind, id) is, by construction, byte-identical
    content (the id is a pure content address over the complete envelope) -- committing it
    again is a genuine idempotent replay, never a conflict; the Store's own same-key/
    identical-content acceptance is the entire mechanism this relies on. A ``RecordConflictError``
    here would mean a real hash collision or a genuine tamper between derivation and commit --
    refused, never silently retried.
    """

    envelope_id = envelope["runtime_observation_envelope_id"]
    if (
        runtime_observation_envelope_semantic_fingerprint(envelope)
        != envelope["runtime_observation_semantic_fingerprint"]
    ):
        raise RuntimeEnvelopeIntegrityError(
            "newly derived envelope's own recomputed semantic fingerprint does not equal its "
            "own declared value -- refusing to commit"
        )

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"TX-RUNTIME-OBSERVATION-{envelope_id}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(_ENVELOPE_RECORD_KIND, envelope_id, envelope)],
            )
            return
        except RecordConflictError as error:
            raise RuntimeEnvelopeIntegrityError(
                f"a different record already occupies {_ENVELOPE_RECORD_KIND}/{envelope_id} "
                "with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise RuntimeRequirementError(
        f"could not durably commit {_ENVELOPE_RECORD_KIND}/{envelope_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = ["RUNTIME_SCHEMA_BASE", "observe_runtime_target"]
