"""The two public Multi-Agent Dynamic Execution routes (Phase 19, Issue #77).

``MULTI_AGENT_OWNER_COUNT=1``, ``PUBLIC_MULTI_AGENT_ENTRY_POINT_COUNT=3`` (this module's two
routes plus :mod:`~manosube_agent_civilization.multi_agent.evidence_handoff`'s own single
hand-off route).

```text
open_dynamic_execution_plan     select 1/2/N slots from one canonical Difference, open the one
                                shared Model Work Unit they act under (reusing Phase 16's own
                                Authority/Boundary machinery unchanged), and commit one
                                immutable, content-addressed plan (genesis, once per plan_ref)
execute_dynamic_execution_plan  fan out to 1/2/N fresh temporary Agents (Phase 12's own
                                lifecycle, reused, never reimplemented), record each slot's own
                                independent, provenance-bound attempt, release every Agent,
                                and produce the conflict set and Evidence-aggregation input
```

**Canonical route** (``14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md`` §5):

```text
live Phase 12 Temporary Agent Execution Contract (the caller's own -- a liveness/freshness
  proof, never itself one of the per-slot execution Agents)
→ Store-resolved, schema-valid, identity-recomputed Difference
→ selection.select_agent_slots (P19-C1) -- bounded, total, caller-immune
→ ONE shared Model Work Unit, opened through the existing Phase 16 owner unchanged
  (Authority evaluated exactly once, by the existing evaluator, never reimplemented here)
→ canonical, content-addressed Multi-Agent Dynamic Execution Plan (genesis, immutable)
→ for each slot: a FRESH Phase 12 Temporary Agent (one call site, executed 1/2/N times) ->
  Model Runtime's own execute_model_work_unit (reused end to end) -> release -> release receipt
→ deterministic conflict set (P19-C6) -> Evidence-aggregation input (P19-C7, refused unless
  every Agent's own release is accounted for -- P19-C8)
→ existing Evidence / Independent Verification owners
  (mod:`~manosube_agent_civilization.multi_agent.evidence_handoff`)
```

**Two Temporary Agent roles, deliberately never conflated.** The *caller's own* Agent (this
module's own second positional parameter, exactly the convention every Model Runtime route
already establishes) is a liveness/freshness proof for the *coordinating* call -- it is never
executed against, and its own ``boot_context`` is read, not consumed. Each *slot's own* Agent
is constructed fresh, once per slot, by this module alone, executed against exactly once, and
released before this module returns -- Phase 12's own lifecycle, reused unchanged, never a
second implementation of it (P19-C3). This is why ``start_temporary_agent`` has **two** literal
call sites in this package rather than Model Runtime's one: :func:`_fresh_execution_contract`
(the freshness-check helper, reused at every commit boundary) and the per-slot construction
inside :func:`execute_dynamic_execution_plan`'s own loop -- both disclosed, both named, in
``14_MULTI_AGENT/MULTI_AGENT_CONTRACT.md``'s own judgment-calls section, and both proved by this
package's own static conformance suite to be the *only* two.

**Authority is reproduced, never minted (P19-C4).** ``open_dynamic_execution_plan`` calls the
existing :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit` unchanged,
which itself calls the existing :func:`~manosube_agent_civilization.authority.
evaluate_model_execution_authorization` exactly once. This module never calls either evaluator
name itself. Because the one capability that exists today
(:data:`~manosube_agent_civilization.multi_agent.types.MULTI_AGENT_CAPABILITIES`'s own single
member) is read-only, no slot ever reaches ``change_executor``, and a maliciously-crafted
Adapter result claiming otherwise has no call shape through which to matter: this module reads
back only what :func:`~manosube_agent_civilization.model_runtime.execute_model_work_unit`
itself already returns (a real, committed, independently-bounded Envelope), never an Adapter's
own raw result directly.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
from manosube_agent_civilization.agent_runtime.errors import AgentReleasedError, AgentRuntimeError
from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record as validate_canonical_record,
)
from manosube_agent_civilization.model_runtime.errors import ModelRuntimeError
from manosube_agent_civilization.model_runtime.route import (
    execute_model_work_unit,
    open_model_work_unit,
)
from manosube_agent_civilization.model_runtime.types import ModelAdapter
from manosube_agent_civilization.observation.boundary import instant
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    MULTI_AGENT_SCHEMA_BASE,
    compute_attempt_id,
    compute_slot_output_id,
    derive_multi_agent_agent_release_receipt,
    derive_multi_agent_conflict_set,
    derive_multi_agent_dynamic_execution_plan,
    derive_multi_agent_evidence_aggregation_input,
    derive_multi_agent_slot_output,
    require_valid_adapter_identity,
    require_valid_multi_agent_agent_release_receipt,
    require_valid_multi_agent_conflict_set,
    require_valid_multi_agent_dynamic_execution_plan,
    require_valid_multi_agent_evidence_aggregation_input,
    require_valid_multi_agent_slot_output,
    require_valid_timestamp,
)
from .errors import (
    MultiAgentAuthorityFreshnessError,
    MultiAgentPlanExpiredError,
    MultiAgentRecordIntegrityError,
    MultiAgentReleasedAgentError,
    MultiAgentReplayConflictError,
    MultiAgentRequirementError,
    MultiAgentStaleStateError,
)
from .identity import (
    capability_selection_fingerprint,
    multi_agent_agent_release_receipt_id,
    multi_agent_agent_release_receipt_semantic_fingerprint,
    multi_agent_conflict_set_id,
    multi_agent_conflict_set_semantic_fingerprint,
    multi_agent_dynamic_execution_plan_id,
    multi_agent_dynamic_execution_plan_semantic_fingerprint,
    multi_agent_evidence_aggregation_input_id,
    multi_agent_evidence_aggregation_input_semantic_fingerprint,
    multi_agent_slot_output_id,
    multi_agent_slot_output_semantic_fingerprint,
)
from .selection import select_agent_slots
from .types import (
    ACCEPTED_SLOT_OUTCOME,
    CANCELLATION_POLICY,
    CONFLICT_POLICY,
    EXECUTION_ORDER,
    RELEASE_POLICY,
)

PLAN_RECORD_KIND = "multi_agent_dynamic_execution_plan"
SLOT_OUTPUT_RECORD_KIND = "multi_agent_slot_output"
RELEASE_RECEIPT_RECORD_KIND = "multi_agent_agent_release_receipt"
CONFLICT_SET_RECORD_KIND = "multi_agent_conflict_set"
AGGREGATION_INPUT_RECORD_KIND = "multi_agent_evidence_aggregation_input"
DIFFERENCE_RECORD_KIND = "difference"
BOUNDARY_RECORD_KIND = "model_execution_boundary"
GRANT_RECORD_KIND = "model_execution_grant"
DECISION_RECORD_KIND = "model_execution_decision"
WORK_UNIT_RECORD_KIND = "model_work_unit"
ENVELOPE_RECORD_KIND = "model_execution_envelope"

#: The identical bounded Compare-And-Swap retry Model Runtime's own ``_commit`` uses.
_MAX_COMMIT_RETRIES = 8

_AUTHORITY_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "human_authority_ref",
    "human_authority_signing_key",
)
_STATE_FIELDS: tuple[str, ...] = ("state_revision", "semantic_fingerprint")


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise MultiAgentRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise MultiAgentRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise MultiAgentRequirementError(
            f"{context} must be an explicit reference object: {value!r}"
        )
    if value.get("kind") != kind:
        raise MultiAgentRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    identity = value.get("id")
    if not isinstance(identity, str) or not identity:
        raise MultiAgentRequirementError(f"{context} carries no readable id: {value!r}")
    _require_canonical_identity(f"{context}.id", identity)
    return dict(value)


# --------------------------------------------------------------------------- #
# The caller's own Phase 12 Temporary Agent Execution Contract -- read, never redefined
# --------------------------------------------------------------------------- #


def _contract_snapshot(boot_context: Any) -> dict[str, Any]:
    current_state = boot_context.current_state
    binding = boot_context.project_binding
    return {
        "project_id": str(boot_context.project_id),
        "project_binding_ref": {
            "kind": "project_binding",
            "id": str(boot_context.project_binding_id),
        },
        "state_revision": int(current_state["state_revision"]),
        "semantic_fingerprint": _plain(current_state["semantic_fingerprint"]),
        "human_authority_ref": _plain(boot_context.human_authority_ref),
        "human_authority_signing_key": _plain(binding.get("human_authority_signing_key")),
    }


def _held_execution_contract(agent: Any) -> dict[str, Any]:
    if not isinstance(agent, TemporaryAgent):
        raise MultiAgentRequirementError(
            "agent must be a live Phase 12 TemporaryAgent obtained from start_temporary_agent, "
            f"not {type(agent)!r} -- this package defines no execution contract of its own"
        )
    try:
        boot_context = agent.boot_context
    except AgentReleasedError as error:
        raise MultiAgentReleasedAgentError(
            "the supplied Temporary Agent has already been released -- a released Phase 12 "
            "execution contract cannot be used to coordinate a dynamic execution plan"
        ) from error
    return _contract_snapshot(boot_context)


def _fresh_execution_contract(
    store: Any, *, project_id: str, project_binding_id: str
) -> dict[str, Any]:
    """The one literal ``start_temporary_agent`` call site used for freshness checks.

    See this module's own docstring: this is one of exactly two literal call sites in this
    package. This Agent is started only to take one honest snapshot and is released
    immediately -- Phase 12's own release is local, idempotent and zero-write.
    """

    agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    try:
        return _contract_snapshot(agent.boot_context)
    finally:
        agent.release()


def _require_contract_state_admissible(
    held: Mapping[str, Any], fresh: Mapping[str, Any], *, require_exact: bool
) -> None:
    if held["state_revision"] > fresh["state_revision"]:
        raise MultiAgentStaleStateError(
            "this call's own Phase 12 execution contract claims State revision "
            f"{held['state_revision']}, which this Store has never reached (current revision "
            f"{fresh['state_revision']}) -- refusing before any Agent is constructed"
        )
    if (
        held["state_revision"] == fresh["state_revision"]
        and held["semantic_fingerprint"] != fresh["semantic_fingerprint"]
    ):
        raise MultiAgentStaleStateError(
            "this call's own Phase 12 execution contract carries a different semantic "
            f"fingerprint at revision {held['state_revision']} than this Store reports -- a "
            "contract established against a different Store or a substituted State is refused "
            "before any Agent is constructed"
        )
    if require_exact and {field: held[field] for field in _STATE_FIELDS} != {
        field: fresh[field] for field in _STATE_FIELDS
    }:
        raise MultiAgentStaleStateError(
            "the Canonical State this call's own Phase 12 execution contract was established "
            f"against (revision {held['state_revision']}) is no longer the State this Store "
            f"reports (revision {fresh['state_revision']}) -- a plan binds the exact State "
            "snapshot it was opened against, so it is opened only under a fully current contract"
        )


def _require_authority_current(
    expected: Mapping[str, Any], fresh: Mapping[str, Any], *, stage: str
) -> None:
    if {field: expected[field] for field in _AUTHORITY_FIELDS} != {
        field: fresh[field] for field in _AUTHORITY_FIELDS
    }:
        raise MultiAgentAuthorityFreshnessError(
            "the Project Binding / Human Authority this execution contract was verified "
            f"against is no longer the one this Store reports -- refusing {stage} rather than "
            "act under, or commit, stale Authority"
        )


def _live_contract(
    store: Any,
    agent: Any,
    *,
    project_id: str,
    project_binding_id: str,
    require_exact_state: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    held = _held_execution_contract(agent)
    if held["project_id"] != project_id:
        raise MultiAgentRequirementError(
            "the supplied Temporary Agent's own execution contract names a different project "
            f"than requested: {held['project_id']!r} != {project_id!r}"
        )
    if held["project_binding_ref"]["id"] != project_binding_id:
        raise MultiAgentRequirementError(
            "the supplied Temporary Agent's own execution contract names a different Project "
            f"Binding than requested: {held['project_binding_ref']['id']!r} != "
            f"{project_binding_id!r}"
        )
    fresh = _fresh_execution_contract(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    _require_authority_current(held, fresh, stage="this call")
    _require_contract_state_admissible(held, fresh, require_exact=require_exact_state)
    return held, fresh


# --------------------------------------------------------------------------- #
# Store resolution -- every reference is resolved, schema-checked and identity-recomputed
# --------------------------------------------------------------------------- #


def _resolve(store: Any, project_id: str, kind: str, record_id: str) -> Any:
    return store.resolve_record(project_id, kind, record_id)


def _require_resolved(store: Any, project_id: str, kind: str, reference: Mapping[str, Any]) -> Any:
    resolved = _resolve(store, project_id, kind, reference["id"])
    if resolved is None:
        raise MultiAgentRequirementError(
            f"{kind} reference does not resolve to a committed record under project "
            f"{project_id!r}: {reference['id']!r} -- a reference with no canonical record "
            "behind it is a caller string, not an independently verifiable fact"
        )
    return resolved


def _require_same_project(record: Mapping[str, Any], project_id: str, kind: str) -> None:
    if record.get("project_id") != project_id:
        raise MultiAgentRequirementError(
            f"resolved {kind} names a different project than the one being executed: "
            f"{record.get('project_id')!r} != {project_id!r} -- material genuinely belonging "
            "to another project or Store is never relabelled into this one"
        )


def _resolve_difference(
    store: Any, project_id: str, difference_ref: Mapping[str, Any]
) -> dict[str, Any]:
    resolved = _require_resolved(store, project_id, DIFFERENCE_RECORD_KIND, difference_ref)
    if not isinstance(resolved, Mapping):
        raise MultiAgentRequirementError(
            f"resolved difference is not a readable record: {resolved!r}"
        )
    difference = dict(resolved)
    try:
        validate_canonical_record(difference, "difference.schema.json", base=DIFFERENCE_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise MultiAgentRequirementError(
            f"resolved difference is not schema-valid: {error}"
        ) from error
    _require_same_project(difference, project_id, DIFFERENCE_RECORD_KIND)
    if compute_difference_id(difference) != difference.get("difference_id"):
        raise MultiAgentRecordIntegrityError(
            f"resolved difference {difference_ref['id']!r} own recomputed identity does not "
            "equal its own declared value -- refusing to trust any of its fields"
        )
    return difference


def resolve_and_verify_committed_plan(store: Any, project_id: str, plan_id: str) -> dict[str, Any]:
    """Resolve the real, committed ``multi_agent_dynamic_execution_plan`` named by *plan_id*
    and require the identical three-way canonical admission every record this package resolves
    is held to: schema-valid, same project, and its own identity and semantic fingerprint,
    independently recomputed from its own content, equal to its own declared values *and* to
    the Store lookup key itself."""

    resolved = _require_resolved(
        store, project_id, PLAN_RECORD_KIND, {"kind": PLAN_RECORD_KIND, "id": plan_id}
    )
    plan = require_valid_multi_agent_dynamic_execution_plan(resolved)
    _require_same_project(plan, project_id, PLAN_RECORD_KIND)
    declared_id = plan.get("multi_agent_dynamic_execution_plan_id")
    recomputed_id = multi_agent_dynamic_execution_plan_id(plan)
    if plan_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRecordIntegrityError(
            "resolved multi_agent_dynamic_execution_plan's own identity does not agree across "
            f"the Store lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={plan_id!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if multi_agent_dynamic_execution_plan_semantic_fingerprint(plan) != plan.get(
        "multi_agent_dynamic_execution_plan_semantic_fingerprint"
    ):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_dynamic_execution_plan {plan_id!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return plan


def resolve_and_verify_committed_slot_output(
    store: Any, project_id: str, slot_output_id: str
) -> dict[str, Any] | None:
    resolved = _resolve(store, project_id, SLOT_OUTPUT_RECORD_KIND, slot_output_id)
    if resolved is None:
        return None
    slot_output = require_valid_multi_agent_slot_output(resolved)
    _require_same_project(slot_output, project_id, SLOT_OUTPUT_RECORD_KIND)
    declared_id = slot_output.get("multi_agent_slot_output_id")
    recomputed_id = multi_agent_slot_output_id(slot_output)
    if slot_output_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRecordIntegrityError(
            "resolved multi_agent_slot_output's own identity does not agree across the Store "
            f"lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={slot_output_id!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if multi_agent_slot_output_semantic_fingerprint(slot_output) != slot_output.get(
        "multi_agent_slot_output_semantic_fingerprint"
    ):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_slot_output {slot_output_id!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return slot_output


def resolve_and_verify_committed_release_receipt(
    store: Any, project_id: str, release_receipt_id: str
) -> dict[str, Any] | None:
    resolved = _resolve(store, project_id, RELEASE_RECEIPT_RECORD_KIND, release_receipt_id)
    if resolved is None:
        return None
    receipt = require_valid_multi_agent_agent_release_receipt(resolved)
    _require_same_project(receipt, project_id, RELEASE_RECEIPT_RECORD_KIND)
    declared_id = receipt.get("multi_agent_agent_release_receipt_id")
    recomputed_id = multi_agent_agent_release_receipt_id(receipt)
    if release_receipt_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRecordIntegrityError(
            "resolved multi_agent_agent_release_receipt's own identity does not agree across "
            f"the Store lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={release_receipt_id!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if multi_agent_agent_release_receipt_semantic_fingerprint(receipt) != receipt.get(
        "multi_agent_agent_release_receipt_semantic_fingerprint"
    ):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_agent_release_receipt {release_receipt_id!r} own recomputed "
            "semantic fingerprint does not equal its own declared value -- refusing to trust "
            "any of its fields"
        )
    return receipt


def resolve_and_verify_committed_conflict_set(
    store: Any, project_id: str, conflict_set_id: str
) -> dict[str, Any]:
    resolved = _require_resolved(
        store,
        project_id,
        CONFLICT_SET_RECORD_KIND,
        {"kind": CONFLICT_SET_RECORD_KIND, "id": conflict_set_id},
    )
    conflict_set = require_valid_multi_agent_conflict_set(resolved)
    _require_same_project(conflict_set, project_id, CONFLICT_SET_RECORD_KIND)
    declared_id = conflict_set.get("multi_agent_conflict_set_id")
    recomputed_id = multi_agent_conflict_set_id(conflict_set)
    if conflict_set_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRecordIntegrityError(
            "resolved multi_agent_conflict_set's own identity does not agree across the Store "
            f"lookup key, its own declared value, and its own recomputed value -- "
            f"lookup={conflict_set_id!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if multi_agent_conflict_set_semantic_fingerprint(conflict_set) != conflict_set.get(
        "multi_agent_conflict_set_semantic_fingerprint"
    ):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_conflict_set {conflict_set_id!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return conflict_set


def resolve_and_verify_committed_aggregation_input(
    store: Any, project_id: str, aggregation_input_id: str
) -> dict[str, Any]:
    resolved = _require_resolved(
        store,
        project_id,
        AGGREGATION_INPUT_RECORD_KIND,
        {"kind": AGGREGATION_INPUT_RECORD_KIND, "id": aggregation_input_id},
    )
    aggregation_input = require_valid_multi_agent_evidence_aggregation_input(resolved)
    _require_same_project(aggregation_input, project_id, AGGREGATION_INPUT_RECORD_KIND)
    declared_id = aggregation_input.get("multi_agent_evidence_aggregation_input_id")
    recomputed_id = multi_agent_evidence_aggregation_input_id(aggregation_input)
    if aggregation_input_id != declared_id or recomputed_id != declared_id:
        raise MultiAgentRecordIntegrityError(
            "resolved multi_agent_evidence_aggregation_input's own identity does not agree "
            f"across the Store lookup key, its own declared value, and its own recomputed "
            f"value -- lookup={aggregation_input_id!r}, declared={declared_id!r}, "
            f"recomputed={recomputed_id!r}"
        )
    if multi_agent_evidence_aggregation_input_semantic_fingerprint(
        aggregation_input
    ) != aggregation_input.get("multi_agent_evidence_aggregation_input_semantic_fingerprint"):
        raise MultiAgentRecordIntegrityError(
            f"resolved multi_agent_evidence_aggregation_input {aggregation_input_id!r} own "
            "recomputed semantic fingerprint does not equal its own declared value -- refusing "
            "to trust any of its fields"
        )
    return aggregation_input


# --------------------------------------------------------------------------- #
# The one persistence boundary
# --------------------------------------------------------------------------- #


def _commit(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    *,
    committed_at: str,
    project_binding_id: str,
    expected_authority: Mapping[str, Any],
    transaction_prefix: str,
    transaction_key: str,
) -> None:
    for _ in range(_MAX_COMMIT_RETRIES):
        _require_authority_current(
            expected_authority,
            _fresh_execution_contract(
                store, project_id=project_id, project_binding_id=project_binding_id
            ),
            stage="to commit this record",
        )
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{transaction_key}-{current_state['state_revision']}"
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
                records=list(records),
            )
            return
        except RecordConflictError as error:
            raise MultiAgentReplayConflictError(
                "a different record already occupies one of "
                f"{[f'{kind}/{identity}' for kind, identity, _body in records]} with different "
                "content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise MultiAgentRequirementError(
        f"could not durably commit {[kind for kind, _identity, _body in records]} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


# --------------------------------------------------------------------------- #
# Route 1 -- select slots, open the shared Model Work Unit, commit the plan
# --------------------------------------------------------------------------- #


def open_dynamic_execution_plan(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    difference_ref: Mapping[str, Any],
    boundary_ref: Mapping[str, Any],
    model_execution_grant_refs: list[Mapping[str, Any]],
    adapter_identity: Mapping[str, Any],
    opened_at: str,
    expires_at: str,
    deadline_at: str | None = None,
) -> dict[str, Any]:
    """Open one canonical, immutable, content-addressed Multi-Agent Dynamic Execution Plan and
    return ``{"plan": ..., "plan_ref": ..., "model_execution_decision": ...}``.

    Resolves and re-verifies the named Difference, derives its bounded slot selection (P19-C1),
    opens the one Model Work Unit every slot of this plan will share (reusing
    :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit` unchanged -- the
    existing Authority evaluator runs exactly once here, never reimplemented), and commits the
    plan. Genesis-once for the resulting ``plan_ref``: once committed, resolving that reference
    again always resolves the identical, immutable record -- this function itself is not
    required to land on the same plan across two *separate* calls, since the Canonical State
    two separate calls observe can genuinely differ (the identical precedent
    :func:`~manosube_agent_civilization.model_runtime.open_model_work_unit` itself already
    establishes; see this package's own contract doc for the disclosed reasoning).
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(opened_at, "opened_at")
    require_valid_timestamp(expires_at, "expires_at")
    resolved_deadline_at = expires_at if deadline_at is None else deadline_at
    require_valid_timestamp(resolved_deadline_at, "deadline_at")
    checked_difference_ref = _require_reference(
        difference_ref, context="difference_ref", kind=DIFFERENCE_RECORD_KIND
    )
    checked_boundary_ref = _require_reference(
        boundary_ref, context="boundary_ref", kind=BOUNDARY_RECORD_KIND
    )
    checked_adapter_identity = require_valid_adapter_identity(adapter_identity, "adapter_identity")
    if not isinstance(model_execution_grant_refs, list) or not model_execution_grant_refs:
        raise MultiAgentRequirementError(
            "model_execution_grant_refs must be a non-empty list of references -- a plan whose "
            "shared Model Work Unit is opened against no Human Authority grant at all is never "
            "authorized"
        )
    checked_grant_refs: list[Mapping[str, Any]] = [
        _require_reference(
            reference, context=f"model_execution_grant_refs[{position}]", kind=GRANT_RECORD_KIND
        )
        for position, reference in enumerate(model_execution_grant_refs)
    ]

    _held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=True,
    )

    difference = _resolve_difference(store, project_id, checked_difference_ref)
    slots = select_agent_slots(difference)
    capabilities = {slot["capability"] for slot in slots}
    if len(capabilities) != 1:
        raise MultiAgentRequirementError(
            "the selected slots do not share exactly one required capability -- this delivery "
            f"opens one shared Model Work Unit per plan: {sorted(capabilities)!r}"
        )
    required_capability = next(iter(capabilities))
    fingerprint = capability_selection_fingerprint(slots)

    opened = open_model_work_unit(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        difference_ref=checked_difference_ref,
        required_capability=required_capability,
        boundary_ref=checked_boundary_ref,
        model_execution_grant_refs=checked_grant_refs,
        opened_at=opened_at,
    )
    work_unit_ref = opened["model_work_unit_ref"]
    decision = opened["model_execution_decision"]
    authority_ref = {
        "kind": DECISION_RECORD_KIND,
        "id": str(decision["model_execution_decision_id"]),
    }

    plan = derive_multi_agent_dynamic_execution_plan(
        project_id=project_id,
        project_binding_ref=dict(fresh["project_binding_ref"]),
        boot_state_revision=int(fresh["state_revision"]),
        boot_semantic_fingerprint=dict(fresh["semantic_fingerprint"]),
        difference_ref=checked_difference_ref,
        capability_selection_fingerprint=fingerprint,
        slots=slots,
        model_work_unit_ref=work_unit_ref,
        authority_ref=authority_ref,
        adapter_identity=checked_adapter_identity,
        execution_order=EXECUTION_ORDER,
        execution_bounds={
            "deadline_at": resolved_deadline_at,
            "cancellation_policy": CANCELLATION_POLICY,
            "max_concurrent_slots": len(slots),
        },
        conflict_policy=CONFLICT_POLICY,
        release_policy=RELEASE_POLICY,
        opened_at=opened_at,
        expires_at=expires_at,
    )
    _commit(
        store,
        project_id,
        [(PLAN_RECORD_KIND, str(plan["multi_agent_dynamic_execution_plan_id"]), plan)],
        committed_at=opened_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MULTI-AGENT-PLAN",
        transaction_key=str(plan["multi_agent_dynamic_execution_plan_id"]),
    )
    return {
        "plan": plan,
        "plan_ref": {
            "kind": PLAN_RECORD_KIND,
            "id": str(plan["multi_agent_dynamic_execution_plan_id"]),
        },
        "model_execution_decision": decision,
    }


# --------------------------------------------------------------------------- #
# Route 2 -- fan out to 1/2/N fresh temporary Agents, release every one
# --------------------------------------------------------------------------- #


def _execute_one_slot(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    plan: Mapping[str, Any],
    plan_ref: Mapping[str, Any],
    slot: Mapping[str, Any],
    model_adapter_factory: Callable[[], ModelAdapter],
    executed_at: str,
    fresh_authority: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Execute (or replay) exactly one slot's own single attempt and return
    ``(slot_output, release_receipt)``.

    Replay-first (P19-C9): the attempt identity is computed *before* any Agent is constructed
    or any adapter is reached, and resolved against the Store; if it already exists, this
    function reuses it verbatim -- zero new Agent construction, zero new adapter calls.
    """

    slot_index = int(slot["slot_index"])
    capability = str(slot["capability"])
    attempt_id = compute_attempt_id(
        project_id=project_id, plan_ref=dict(plan_ref), slot_index=slot_index
    )
    slot_output_key = compute_slot_output_id(
        project_id=project_id, plan_ref=dict(plan_ref), slot_index=slot_index
    )

    existing_slot_output = resolve_and_verify_committed_slot_output(
        store, project_id, slot_output_key
    )
    if existing_slot_output is not None:
        existing_receipt = resolve_and_verify_committed_release_receipt(
            store,
            project_id,
            multi_agent_agent_release_receipt_id(
                {
                    "schema_version": plan["schema_version"],
                    "project_id": project_id,
                    "plan_ref": dict(plan_ref),
                    "slot_index": slot_index,
                }
            ),
        )
        if existing_receipt is None:
            # Structural Review Round 1, P19-R1-F2: this branch is defense in depth, not the
            # crash-gap fix itself. Since a slot's own attempt output and its release receipt are
            # now committed together in one atomic transaction below, a genuinely committed slot
            # output with no release receipt should be unreachable through this package's own
            # normal execution path -- but this function never trusts a resolved record's own
            # history without re-checking, the identical discipline this repository already
            # keeps everywhere else, so the refusal stays exactly where it always was.
            raise MultiAgentRequirementError(
                f"slot {slot_index} already has a committed attempt but no release receipt -- "
                "an incomplete prior orchestration attempt cannot be silently treated as replay"
            )
        return existing_slot_output, existing_receipt

    # The one, second literal `start_temporary_agent` call site in this package -- executed
    # once per slot that has not already been recorded. See this module's own docstring.
    slot_agent = start_temporary_agent(
        store, project_id=project_id, project_binding_id=project_binding_id
    )
    outcome: str
    envelope_ref: dict[str, Any] | None = None
    result_fingerprint: str | None = None
    outcome_detail: str | None = None
    try:
        adapter = model_adapter_factory()
        declared_identity = getattr(adapter, "adapter_identity", None)
        if dict(declared_identity or {}) != dict(plan["adapter_identity"]):
            raise MultiAgentRequirementError(
                "the adapter this slot's own model_adapter_factory produced declares an "
                f"adapter_identity that does not equal this plan's own admitted one: "
                f"{declared_identity!r} != {plan['adapter_identity']!r}"
            )
        result = execute_model_work_unit(
            store,
            slot_agent,
            project_id=project_id,
            project_binding_id=project_binding_id,
            model_work_unit_ref=plan["model_work_unit_ref"],
            adapter=adapter,
            executed_at=executed_at,
        )
        envelope = result["envelope"]
        outcome = str(envelope["execution_outcome"])
        result_fingerprint = envelope["normalized_candidate_fingerprint"]
        envelope_ref = {
            "kind": ENVELOPE_RECORD_KIND,
            "id": str(envelope["model_execution_envelope_id"]),
        }
    except (ModelRuntimeError, AgentRuntimeError) as error:
        # Disclosed judgment call (P19-C5/V6): a caught Model Runtime or Agent Runtime
        # operational failure never loses this slot's own provenance for the sake of the
        # others -- it becomes a first-class, honestly-classified UNAVAILABLE attempt rather
        # than an exception that aborts the whole orchestration. A genuinely unexpected error
        # (any other exception type) is deliberately NOT caught here -- it propagates, the
        # `finally` below still releases this slot's own Agent, and the orchestration attempt
        # as a whole aborts, leaving every slot completed so far durably committed and
        # released for a later, recovering call to resume.
        outcome = "UNAVAILABLE"
        outcome_detail = f"{type(error).__name__}: {error}"[:2000]
    finally:
        slot_agent.release()

    slot_output = derive_multi_agent_slot_output(
        project_id=project_id,
        plan_ref=dict(plan_ref),
        slot_index=slot_index,
        capability=capability,
        attempt_ordinal=1,
        model_execution_envelope_ref=envelope_ref,
        outcome=outcome,
        result_fingerprint=result_fingerprint,
        outcome_detail=outcome_detail,
        started_at=executed_at,
        ended_at=executed_at,
        execution_snapshot={
            "state_revision": plan["boot_state_revision"],
            "semantic_fingerprint": plan["boot_semantic_fingerprint"],
        },
    )
    release_receipt = derive_multi_agent_agent_release_receipt(
        project_id=project_id,
        plan_ref=dict(plan_ref),
        slot_index=slot_index,
        attempt_id=attempt_id,
        release_status="RELEASED",
        released_at=executed_at,
    )
    # Structural Review Round 1, P19-R1-F2: the slot's own attempt record and its release
    # receipt are committed here in one atomic transaction, never two separate ones -- closing
    # the crash gap the previous two-commit sequence left open (a crash between them left a
    # committed slot output with no release receipt, and every later replay call raised
    # MultiAgentRequirementError forever, since a slot's own release is derived only once, right
    # here, immediately after its own attempt). Either both records land, or neither does; there
    # is no longer an intermediate state to recover from. This is the identical multi-record
    # atomic-commit discipline this repository's own Model Runtime already uses for its paired
    # Decision+Work-Unit genesis commit (`open_model_work_unit`).
    _commit(
        store,
        project_id,
        [
            (
                SLOT_OUTPUT_RECORD_KIND,
                str(slot_output["multi_agent_slot_output_id"]),
                slot_output,
            ),
            (
                RELEASE_RECEIPT_RECORD_KIND,
                str(release_receipt["multi_agent_agent_release_receipt_id"]),
                release_receipt,
            ),
        ],
        committed_at=executed_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh_authority,
        transaction_prefix="TX-MULTI-AGENT-SLOT-COMPLETE",
        transaction_key=str(slot_output["multi_agent_slot_output_id"]),
    )
    return slot_output, release_receipt


def _classify_conflicts(
    slot_outputs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    """P19-C6's own deterministic classification: exact-fingerprint-equality-or-explicit-
    disagreement, grouped by capability. Returns ``(members, admitted_refs,
    unresolved_capabilities, absent_refs)``."""

    by_capability: dict[str, list[dict[str, Any]]] = {}
    for slot_output in slot_outputs:
        by_capability.setdefault(str(slot_output["capability"]), []).append(slot_output)

    members: list[dict[str, Any]] = []
    admitted_refs: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    absent_refs: list[dict[str, Any]] = []

    for capability in sorted(by_capability):
        group = by_capability[capability]
        accepted = [so for so in group if so["outcome"] == ACCEPTED_SLOT_OUTCOME]
        non_accepted = [so for so in group if so["outcome"] != ACCEPTED_SLOT_OUTCOME]

        if accepted:
            fingerprints = sorted({str(so["result_fingerprint"]) for so in accepted})
            if len(fingerprints) == 1:
                refs = sorted(
                    (
                        {
                            "kind": SLOT_OUTPUT_RECORD_KIND,
                            "id": str(so["multi_agent_slot_output_id"]),
                        }
                        for so in accepted
                    ),
                    key=lambda ref: ref["id"],
                )
                members.append(
                    {
                        "member_kind": "AGREEING",
                        "capability": capability,
                        "result_fingerprint": fingerprints[0],
                        "slot_output_refs": {"collection_kind": "UNORDERED_SET", "members": refs},
                    }
                )
                admitted_refs.extend(refs)
            else:
                fingerprint_groups = []
                for fingerprint_value in fingerprints:
                    refs = sorted(
                        (
                            {
                                "kind": SLOT_OUTPUT_RECORD_KIND,
                                "id": str(so["multi_agent_slot_output_id"]),
                            }
                            for so in accepted
                            if str(so["result_fingerprint"]) == fingerprint_value
                        ),
                        key=lambda ref: ref["id"],
                    )
                    fingerprint_groups.append(
                        {
                            "result_fingerprint": fingerprint_value,
                            "slot_output_refs": {
                                "collection_kind": "UNORDERED_SET",
                                "members": refs,
                            },
                        }
                    )
                members.append(
                    {
                        "member_kind": "CONTRADICTING",
                        "capability": capability,
                        "fingerprint_groups": fingerprint_groups,
                    }
                )
                unresolved.add(capability)
        else:
            unresolved.add(capability)

        for slot_output in sorted(non_accepted, key=lambda so: int(so["slot_index"])):
            ref = {
                "kind": SLOT_OUTPUT_RECORD_KIND,
                "id": str(slot_output["multi_agent_slot_output_id"]),
            }
            members.append(
                {
                    "member_kind": "ABSENT",
                    "capability": capability,
                    "slot_index": int(slot_output["slot_index"]),
                    "outcome": str(slot_output["outcome"]),
                    "slot_output_ref": ref,
                }
            )
            absent_refs.append(ref)

    return members, admitted_refs, sorted(unresolved), absent_refs


def execute_dynamic_execution_plan(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    plan_ref: Mapping[str, Any],
    model_adapter_factory: Callable[[], ModelAdapter],
    executed_at: str,
) -> dict[str, Any]:
    """Execute (or replay) every slot of one already-open plan and return
    ``{"plan": ..., "slot_outputs": [...], "conflict_set": ..., "aggregation_input": ...,
    "release_receipts": [...]}``.

    For each slot, in ``slot_index`` order (see this module's own docstring on what
    "CONCURRENT" honestly means here): resolve or execute exactly one attempt
    (:func:`_execute_one_slot`), release the slot's own Agent, and commit its release receipt.
    After every slot has settled, build and commit the deterministic conflict set (P19-C6) and,
    only if every constructed Agent's own release is accounted for as ``RELEASED``, the
    Evidence-aggregation input (P19-C7/P19-C8).
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(executed_at, "executed_at")
    checked_plan_ref = _require_reference(plan_ref, context="plan_ref", kind=PLAN_RECORD_KIND)

    _held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=False,
    )
    plan = resolve_and_verify_committed_plan(store, project_id, checked_plan_ref["id"])
    # Structural Review Round 1, P19-R1-F5: the plan's own recorded validity window is enforced
    # here, fail-closed, before any slot's own Agent is constructed, any adapter is reached, or
    # any new Store mutation is made for this call -- `expires_at` and `execution_bounds.
    # deadline_at` were previously recorded but never read by any runtime path. Checked against
    # `executed_at` (the caller-supplied instant, never a wall clock, the identical discipline
    # every other timestamp-bearing route in this repository already keeps), the identical
    # fail-closed discipline reflow's own G18 `evaluation_expires_at` check already applies to
    # an unrelated validity window (`~manosube_agent_civilization.reflow.commit`).
    if instant(executed_at) >= instant(plan["expires_at"]) or instant(executed_at) >= instant(
        plan["execution_bounds"]["deadline_at"]
    ):
        raise MultiAgentPlanExpiredError(
            f"executed_at {executed_at!r} is at or past this plan's own recorded "
            f"expires_at ({plan['expires_at']!r}) or execution_bounds.deadline_at "
            f"({plan['execution_bounds']['deadline_at']!r}) -- refusing before any slot's own "
            "Agent is constructed, any adapter is reached, or any new Store mutation is made"
        )
    if plan["project_binding_ref"] != dict(fresh["project_binding_ref"]):
        raise MultiAgentRequirementError(
            "resolved plan is bound to a different Project Binding than this call's own "
            f"execution contract: {plan['project_binding_ref']!r} != "
            f"{dict(fresh['project_binding_ref'])!r}"
        )

    slot_outputs: list[dict[str, Any]] = []
    release_receipts: list[dict[str, Any]] = []
    for slot in sorted(plan["slots"], key=lambda item: int(item["slot_index"])):
        slot_output, release_receipt = _execute_one_slot(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            plan=plan,
            plan_ref=checked_plan_ref,
            slot=slot,
            model_adapter_factory=model_adapter_factory,
            executed_at=executed_at,
            fresh_authority=fresh,
        )
        slot_outputs.append(slot_output)
        release_receipts.append(release_receipt)

    members, admitted_refs, unresolved_capabilities, absent_refs = _classify_conflicts(slot_outputs)
    considered_refs = sorted(
        (
            {"kind": SLOT_OUTPUT_RECORD_KIND, "id": str(so["multi_agent_slot_output_id"])}
            for so in slot_outputs
        ),
        key=lambda ref: ref["id"],
    )
    conflict_set = derive_multi_agent_conflict_set(
        project_id=project_id,
        plan_ref=dict(checked_plan_ref),
        considered_slot_output_refs=considered_refs,
        members=members,
    )
    _commit(
        store,
        project_id,
        [
            (
                CONFLICT_SET_RECORD_KIND,
                str(conflict_set["multi_agent_conflict_set_id"]),
                conflict_set,
            )
        ],
        committed_at=executed_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MULTI-AGENT-CONFLICT-SET",
        transaction_key=str(conflict_set["multi_agent_conflict_set_id"]),
    )
    conflict_set_ref = {
        "kind": CONFLICT_SET_RECORD_KIND,
        "id": str(conflict_set["multi_agent_conflict_set_id"]),
    }

    aggregation_input = derive_multi_agent_evidence_aggregation_input(
        project_id=project_id,
        plan_ref=dict(checked_plan_ref),
        conflict_set_ref=conflict_set_ref,
        admitted_slot_output_refs=admitted_refs,
        unresolved_capabilities=unresolved_capabilities,
        absent_slot_output_refs=absent_refs,
        release_receipts=release_receipts,
    )
    _commit(
        store,
        project_id,
        [
            (
                AGGREGATION_INPUT_RECORD_KIND,
                str(aggregation_input["multi_agent_evidence_aggregation_input_id"]),
                aggregation_input,
            )
        ],
        committed_at=executed_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MULTI-AGENT-AGGREGATION-INPUT",
        transaction_key=str(aggregation_input["multi_agent_evidence_aggregation_input_id"]),
    )

    return {
        "plan": plan,
        "slot_outputs": slot_outputs,
        "release_receipts": release_receipts,
        "conflict_set": conflict_set,
        "aggregation_input": aggregation_input,
    }


__all__ = [
    "MULTI_AGENT_SCHEMA_BASE",
    "execute_dynamic_execution_plan",
    "open_dynamic_execution_plan",
    "resolve_and_verify_committed_aggregation_input",
    "resolve_and_verify_committed_conflict_set",
    "resolve_and_verify_committed_plan",
    "resolve_and_verify_committed_release_receipt",
    "resolve_and_verify_committed_slot_output",
]
