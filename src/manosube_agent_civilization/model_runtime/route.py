"""The four public Model Runtime routes (Phase 16, Issue #66).

``MODEL_RUNTIME_OWNER_COUNT=1``, ``PUBLIC_MODEL_RUNTIME_ENTRY_POINT_COUNT=4`` (this module)
``+1`` (:mod:`~manosube_agent_civilization.model_runtime.evidence_handoff`'s own single
hand-off route).

```text
open_model_work_unit             open one immutable, State-bound Work Unit (genesis, once)
execute_model_work_unit          one bounded, provider-neutral model execution against it
record_model_swap                prove Adapter/Agent A stopped and B resumed the same Work Unit
recover_model_execution_session  prove a totally lost session was recovered from Store alone
```

**The Phase 12 Temporary Agent Execution Contract is the execution contract, unchanged.** Every
route here takes a live :class:`~manosube_agent_civilization.agent_runtime.TemporaryAgent` as an
argument and reads its own ``boot_context`` -- which is what makes the handle's liveness a
*checked* fact rather than an assumption, since a released Agent raises
:class:`~manosube_agent_civilization.agent_runtime.errors.AgentReleasedError` from that very
property. This package defines no execution-contract record, no contract id field, no schema for
one, no durable agent identity, and no second Boot wrapper: it reaches Boot **only** through
:func:`~manosube_agent_civilization.agent_runtime.start_temporary_agent`, at exactly one literal
call site in this module (:func:`_fresh_execution_contract`), and never imports
``boot_project`` at all. ``agent_runtime`` itself is untouched by this Phase.

**Two independent freshness gates, and why they run where they do.**

```text
STALE STATE          the State the caller's own live TemporaryAgent holds must still be the
                     State this Store reports, checked once per call, before any adapter and
                     before any resolution is trusted. A Work Unit's own opened_state_revision
                     is deliberately NOT what "stale" means here (see below).
AUTHORITY FRESHNESS  the Project Binding / Human Authority / signing key this call runs under
                     must equal the ones the Work Unit's own Authority Decision was made under
                     -- checked before the adapter, and again on EVERY commit attempt.
```

"Stale State" cannot mean "the Work Unit's ``opened_state_revision`` is behind the current
revision": committing the Work Unit itself advances the revision, so that reading would make
every Work Unit unusable the instant it existed, and would make resumption after any unrelated
commit impossible -- the exact opposite of what P16-C4 asks to prove. What must be current is
the *execution contract the caller is acting under*. An Agent Booted at revision 7 and still
holding revision 7 while the Store has moved to revision 9 has a stale contract, and is refused
with zero adapter calls. What is additionally required of the Work Unit's own snapshot is only
that it not claim the impossible: a Work Unit declaring an ``opened_state_revision`` **greater
than** the current one was not opened against any State this Store ever had.

**Model output is never authoritative (P16-C3).** The adapter receives one deep-frozen,
provider-neutral canonical request and returns a result from which this route reads exactly
three keys (:data:`~manosube_agent_civilization.model_runtime.types.MODEL_ADAPTER_RESULT_KEYS`).
An adapter cannot mutate Canonical State, mint Authority, declare a Difference closed, commit a
Change, self-accept its own Evidence, or widen its own Boundary or capability -- not because
this route refuses those attempts at runtime, but because there is no call shape through which
one could be made: ``adapter.py`` imports no Store, Boot, Agent Runtime, Authority, Evidence,
Difference, or Change module at all, and the only three keys this route ever reads back are the
three above. The accepting classification ``CANDIDATE_ACCEPTED`` does not exist in the adapter
vocabulary; only this route computes it, and only after independently projecting the candidate
down to the Boundary's own ``permitted_candidate_fields`` and independently re-fingerprinting
that projection.

Canonical route (``11_MODEL_RUNTIME/MODEL_RUNTIME_CONTRACT.md`` §5):

```text
live Phase 12 Temporary Agent Execution Contract (its own boot_context, read not assumed)
→ fresh Boot through the same Phase 12 owner -- stale-State refusal, zero adapter calls
→ Store-resolved, schema-valid, identity-recomputed Difference
→ Store-resolved, schema-valid, identity-recomputed Model Execution Boundary
→ real Human-Authority-signed grant(s) -> ONE evaluate_model_execution_authorization call
→ canonical, State-bound Model Work Unit (immutable, opened once, content-addressed)
→ deterministic provider-neutral model_execution_request_identity (no adapter reached yet)
→ authority-freshness re-check -- refuses before the adapter
→ replaceable Model Adapter -- one bounded call, handed deep-frozen structures it cannot mutate
→ independent Boundary projection and typed reclassification (CANDIDATE_ACCEPTED computed
  here, never accepted from the adapter's own report)
→ canonical Model Execution Envelope
→ authority-freshness re-check on every commit attempt
→ existing canonical persistence boundary (commit_state_transition)
→ bounded Model Execution Receipt -> existing Evidence / Independent Verification owners
```
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
from manosube_agent_civilization.agent_runtime.errors import AgentReleasedError
from manosube_agent_civilization.authority import (
    MODEL_EXECUTION_AUTHORIZED,
    evaluate_model_execution_authorization,
)
from manosube_agent_civilization.authority.identity import model_execution_decision_id
from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.identity import difference_id as compute_difference_id
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record as validate_canonical_record,
)
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .engine import (
    MODEL_RUNTIME_SCHEMA_BASE,
    derive_model_execution_envelope,
    derive_model_swap_receipt,
    derive_model_work_unit,
    derive_session_recovery_receipt,
    require_valid_model_execution_boundary,
    require_valid_model_execution_decision,
    require_valid_model_execution_envelope,
    require_valid_model_work_unit,
    require_valid_semantic_fingerprint,
    require_valid_timestamp,
)
from .errors import (
    ModelAdapterError,
    ModelRecordIntegrityError,
    ModelReleasedAgentError,
    ModelRuntimeAuthorityFreshnessError,
    ModelRuntimeRequirementError,
    ModelRuntimeStaleStateError,
)
from .identity import (
    model_candidate_fingerprint,
    model_execution_boundary_id,
    model_execution_boundary_semantic_fingerprint,
    model_execution_envelope_id,
    model_execution_envelope_semantic_fingerprint,
    model_execution_request_identity,
    model_swap_receipt_semantic_fingerprint,
    model_work_unit_id,
    model_work_unit_semantic_fingerprint,
    session_recovery_receipt_semantic_fingerprint,
)
from .types import (
    MODEL_ADAPTER_OUTCOMES,
    MODEL_ADAPTER_RESULT_KEYS,
    MODEL_EXECUTION_CAPABILITIES,
    MODEL_OUTCOME_TO_RECEIPT_STATUS,
    ModelAdapter,
    ModelExecutionReceipt,
    deep_freeze,
)

WORK_UNIT_RECORD_KIND = "model_work_unit"
BOUNDARY_RECORD_KIND = "model_execution_boundary"
DECISION_RECORD_KIND = "model_execution_decision"
GRANT_RECORD_KIND = "model_execution_grant"
ENVELOPE_RECORD_KIND = "model_execution_envelope"
SWAP_RECEIPT_RECORD_KIND = "model_swap_receipt"
RECOVERY_RECEIPT_RECORD_KIND = "session_recovery_receipt"
DIFFERENCE_RECORD_KIND = "difference"

#: The identical Compare-And-Swap retry bound Projection's own ``_claim_slot`` and Runtime's own
#: ``_commit_envelope`` use -- not a timeout, not a backoff, bounded protection against genuine,
#: ordinary contention from an unrelated commit landing on this project between this route's own
#: ``load_current`` and its own ``commit``.
_MAX_COMMIT_RETRIES = 8

#: Exactly the fields a Model Execution Envelope, a Model Swap Receipt and a Session Recovery
#: Receipt each restate from the one Work Unit they are about. Restated on the record rather
#: than left implicit behind ``model_work_unit_ref`` so that "the resumed execution retained
#: identical Work Unit, Difference, Authority, Boundary and Evidence-requirement identities"
#: (P16-C4) is a fact readable off the two committed records themselves, and so that each of
#: those five fields participates in every one of those records' own content addresses.
CONTINUITY_FIELDS: tuple[str, ...] = (
    "difference_ref",
    "required_capability",
    "authority_ref",
    "boundary_ref",
    "evidence_requirements",
)

#: The authority-defining projection of an execution contract -- *whose authority* this
#: execution runs under. Deliberately separate from the State-defining projection below, for the
#: identical reason :func:`~manosube_agent_civilization.runtime.route._authority_context`
#: records: an ordinary unrelated commit moves State without changing whose authority is in
#: force, and only the latter is a reason to refuse a commit.
_AUTHORITY_FIELDS: tuple[str, ...] = (
    "project_id",
    "project_binding_ref",
    "human_authority_ref",
    "human_authority_signing_key",
)

#: The State-defining projection of an execution contract -- *which exact State* it was
#: established against.
_STATE_FIELDS: tuple[str, ...] = ("state_revision", "semantic_fingerprint")


def _plain(value: Any) -> Any:
    """Recursively rebuild *value* as plain ``dict``/``list``/scalar.

    A :class:`~manosube_agent_civilization.boot.BootContext` deep-freezes everything it holds
    into ``MappingProxyType``/``tuple``; a canonical record must be a plain, canonically
    serializable structure, and a ``!=`` between a frozen and a plain copy of the identical
    content would otherwise report inequality on container type alone.
    """

    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ModelRuntimeRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise ModelRuntimeRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(value: Any, *, context: str, kind: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelRuntimeRequirementError(
            f"{context} must be an explicit reference object: {value!r}"
        )
    if value.get("kind") != kind:
        raise ModelRuntimeRequirementError(f"{context} does not name kind={kind!r}: {value!r}")
    identity = value.get("id")
    if not isinstance(identity, str) or not identity:
        raise ModelRuntimeRequirementError(f"{context} carries no readable id: {value!r}")
    _require_canonical_identity(f"{context}.id", identity)
    return dict(value)


# --------------------------------------------------------------------------- #
# The Phase 12 Temporary Agent Execution Contract -- read, never redefined
# --------------------------------------------------------------------------- #


def _contract_snapshot(boot_context: Any) -> dict[str, Any]:
    """The closed projection of one Boot Context that *is* an execution contract identity here.

    There is no persisted execution-contract record in this repository and this Phase does not
    create one: Phase 12's own ``TemporaryAgent`` is a thin, ephemeral, non-persisted Boot
    wrapper with no schema, no content address and no durable identity, and its adopted frozen
    semantic decisions forbid giving it one. So "the Phase 12 execution contract identity",
    operationally, is exactly this: the Project, the Project Binding, the Human Authority and
    signing key that Binding currently names, and the exact State revision/semantic fingerprint
    the wrapped Boot restored. Every field here is re-derived from a real Boot every time it is
    needed and never cached across a session boundary.
    """

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
    """The execution contract the caller's own live Temporary Agent holds.

    A released Agent raises :class:`~manosube_agent_civilization.agent_runtime.errors.
    AgentReleasedError` from its own ``boot_context`` property; that error is never swallowed,
    it is chained into this package's own :class:`~manosube_agent_civilization.model_runtime.
    errors.ModelReleasedAgentError` so the refusal names this package's own boundary while the
    original cause stays readable.
    """

    if not isinstance(agent, TemporaryAgent):
        raise ModelRuntimeRequirementError(
            "agent must be a live Phase 12 TemporaryAgent obtained from start_temporary_agent, "
            f"not {type(agent)!r} -- this package defines no execution contract of its own"
        )
    try:
        boot_context = agent.boot_context
    except AgentReleasedError as error:
        raise ModelReleasedAgentError(
            "the supplied Temporary Agent has already been released -- a released Phase 12 "
            "execution contract cannot be restarted, resumed, or executed under"
        ) from error
    return _contract_snapshot(boot_context)


def _fresh_execution_contract(
    store: Any, *, project_id: str, project_binding_id: str
) -> dict[str, Any]:
    """The one literal ``start_temporary_agent`` call site in this package.

    Reached from several points in a single route call -- once to prove the caller's own
    contract is still current, once immediately before the adapter is reached, and once on every
    commit attempt -- so this package's own static conformance proof still sees exactly one
    Phase 12 entry point here, and no second, drifting way of restoring a project can ever appear
    beside it. This package never calls ``boot_project`` and never imports it: current State
    restoration remains Boot's own concern, reached only through Phase 12's own route, exactly as
    Phase 12 itself reaches it.

    The Agent started here is released immediately: it exists only to take one honest snapshot,
    and Phase 12's own release is local, idempotent and zero-write. Every Boot/Binding/Store
    failure propagates its owning domain's own typed error unchanged.
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
    """The State half of the two freshness gates -- see this module's own docstring for what
    "stale" means here and, just as importantly, what it deliberately does not.

    Two rules always apply, and a third applies only where *require_exact* is set:

    ```text
    NOT FROM THE FUTURE   a contract claiming a State revision this Store has never reached is
                          not a view of this Store at all
    NOT A DIFFERENT WORLD a contract claiming the Store's own current revision must carry the
                          Store's own current semantic fingerprint -- this is what refuses a
                          contract genuinely established against a *different*, internally
                          self-consistent Store at the same revision number
    FULLY CURRENT         genesis only: opening a Work Unit binds it to an exact State snapshot,
                          so it may be opened only under a contract that is still exactly the
                          State this Store reports
    ```

    Execution, swap and recovery deliberately do **not** require the third: committing the Work
    Unit itself advances the revision, and every later unrelated commit advances it again, so
    requiring exact currency there would make a Work Unit unusable the instant it existed and
    would make resumption after any unrelated commit impossible -- the exact opposite of what
    P16-C4 asks to prove. What they require instead is that the contract not predate the Work
    Unit itself (:func:`_resume_from_store`).
    """

    if held["state_revision"] > fresh["state_revision"]:
        raise ModelRuntimeStaleStateError(
            "this call's own Phase 12 execution contract claims State revision "
            f"{held['state_revision']}, which this Store has never reached (current revision "
            f"{fresh['state_revision']}) -- refusing before any adapter call"
        )
    if (
        held["state_revision"] == fresh["state_revision"]
        and held["semantic_fingerprint"] != fresh["semantic_fingerprint"]
    ):
        raise ModelRuntimeStaleStateError(
            "this call's own Phase 12 execution contract carries a different semantic "
            f"fingerprint at revision {held['state_revision']} than this Store reports -- a "
            "contract established against a different Store or a substituted State is refused "
            "before any adapter call"
        )
    if require_exact and {field: held[field] for field in _STATE_FIELDS} != {
        field: fresh[field] for field in _STATE_FIELDS
    }:
        raise ModelRuntimeStaleStateError(
            "the Canonical State this call's own Phase 12 execution contract was established "
            f"against (revision {held['state_revision']}) is no longer the State this Store "
            f"reports (revision {fresh['state_revision']}) -- a Work Unit binds the exact State "
            "snapshot it was opened against, so it is opened only under a fully current contract"
        )


def _require_authority_current(
    expected: Mapping[str, Any], fresh: Mapping[str, Any], *, stage: str
) -> None:
    if {field: expected[field] for field in _AUTHORITY_FIELDS} != {
        field: fresh[field] for field in _AUTHORITY_FIELDS
    }:
        raise ModelRuntimeAuthorityFreshnessError(
            "the Project Binding / Human Authority this execution contract was verified against "
            f"is no longer the one this Store reports -- refusing {stage} rather than act under, "
            "or commit, stale Authority"
        )


def _live_contract(
    store: Any,
    agent: Any,
    *,
    project_id: str,
    project_binding_id: str,
    require_exact_state: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Prove the caller's own Temporary Agent is live, names this exact project/Binding, runs
    under the Authority this Store currently reports, and holds an admissible State view -- and
    return ``(held, fresh)``: the contract the Agent itself holds, and the contract a fresh Boot
    through the same Phase 12 owner reports right now.

    Every refusal here lands before any Store record is resolved, before any Authority is
    evaluated and before any adapter exists.
    """

    held = _held_execution_contract(agent)
    if held["project_id"] != project_id:
        raise ModelRuntimeRequirementError(
            "the supplied Temporary Agent's own execution contract names a different project "
            f"than requested: {held['project_id']!r} != {project_id!r}"
        )
    if held["project_binding_ref"]["id"] != project_binding_id:
        raise ModelRuntimeRequirementError(
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


def _resolve(store: Any, project_id: str, kind: str, reference: Mapping[str, Any]) -> Any:
    resolved = store.resolve_record(project_id, kind, reference["id"])
    if resolved is None:
        raise ModelRuntimeRequirementError(
            f"{kind} reference does not resolve to a committed record under project "
            f"{project_id!r}: {reference['id']!r} -- a reference with no canonical record behind "
            "it is a caller string, not an independently verifiable fact"
        )
    return resolved


def _require_same_project(record: Mapping[str, Any], project_id: str, kind: str) -> None:
    if record.get("project_id") != project_id:
        raise ModelRuntimeRequirementError(
            f"resolved {kind} names a different project than the one being executed: "
            f"{record.get('project_id')!r} != {project_id!r} -- material genuinely belonging to "
            "another project or Store is never relabelled into this one"
        )


def _resolve_difference(
    store: Any, project_id: str, difference_ref: Mapping[str, Any]
) -> dict[str, Any]:
    """Resolve, schema-validate and independently identity-recompute the real Difference this
    Work Unit is about.

    An unresolved ``difference_ref`` is never accepted: the whole proposal is about work bound to
    a real Difference, and a reference naming nothing committed binds nothing. Identity is asked
    of the Difference package's own owner rather than recomputed here -- a second implementation
    of a content address is a second answer to what the address is.
    """

    resolved = _resolve(store, project_id, DIFFERENCE_RECORD_KIND, difference_ref)
    if not isinstance(resolved, Mapping):
        raise ModelRuntimeRequirementError(
            f"resolved difference is not a readable record: {resolved!r}"
        )
    difference = dict(resolved)
    try:
        validate_canonical_record(difference, "difference.schema.json", base=DIFFERENCE_SCHEMA_BASE)
    except DifferenceValidationError as error:
        raise ModelRuntimeRequirementError(
            f"resolved difference is not schema-valid: {error}"
        ) from error
    _require_same_project(difference, project_id, DIFFERENCE_RECORD_KIND)
    if compute_difference_id(difference) != difference.get("difference_id"):
        raise ModelRecordIntegrityError(
            f"resolved difference {difference_ref['id']!r} own recomputed identity does not equal "
            "its own declared value -- refusing to trust any of its fields"
        )
    return difference


def _resolve_boundary(
    store: Any,
    project_id: str,
    boundary_ref: Mapping[str, Any],
    *,
    project_binding_ref: Mapping[str, Any],
    required_capability: str,
    human_authority_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve, schema-validate, identity-recompute and Authority-bind the applicable Model
    Execution Boundary (P16-C1's "applicable Boundary reference").

    This Phase's Boundary is deliberately its own minimal, domain-scoped record rather than any
    of the three boundary concepts already in this repository: Product Binding's own Boundary
    bounds repository source paths, Difference's ``effective_boundary`` bounds an Observation
    Scope, and Runtime's Observation Boundary bounds live HTTP targets. None of the three is
    about "what a model's output may be used for", and force-fitting one would have meant
    declaring repo paths or network targets that this Phase neither reads nor honours. What is
    bounded here is exactly what this Phase actually bounds: which capability the output may
    serve, which candidate kinds it may propose, and which candidate fields may survive
    normalization at all.
    """

    resolved = _resolve(store, project_id, BOUNDARY_RECORD_KIND, boundary_ref)
    boundary = require_valid_model_execution_boundary(resolved)
    _require_same_project(boundary, project_id, BOUNDARY_RECORD_KIND)
    if model_execution_boundary_id(boundary) != boundary.get("model_execution_boundary_id"):
        raise ModelRecordIntegrityError(
            f"resolved model_execution_boundary {boundary_ref['id']!r} own recomputed identity "
            "does not equal its own declared value -- refusing to trust it"
        )
    if model_execution_boundary_semantic_fingerprint(boundary) != boundary.get(
        "model_execution_boundary_semantic_fingerprint"
    ):
        raise ModelRecordIntegrityError(
            f"resolved model_execution_boundary {boundary_ref['id']!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust it"
        )
    if boundary["project_binding_ref"] != dict(project_binding_ref):
        raise ModelRuntimeRequirementError(
            "resolved model_execution_boundary is bound to a different Project Binding than the "
            f"one this call's own execution contract names: {boundary['project_binding_ref']!r} "
            f"!= {dict(project_binding_ref)!r}"
        )
    if boundary["permitted_capability"] != required_capability:
        raise ModelRuntimeRequirementError(
            "resolved model_execution_boundary does not permit the required capability: "
            f"{boundary['permitted_capability']!r} != {required_capability!r}"
        )
    if boundary["declared_by"] != dict(human_authority_ref):
        raise ModelRuntimeAuthorityFreshnessError(
            "resolved model_execution_boundary was declared by a different Human Authority than "
            "the one this call's own fresh Boot restored -- a Boundary declared under a previous "
            "Human Authority is never carried forward silently across a legitimate re-binding"
        )
    return boundary


def _resolve_authority_decision(
    store: Any,
    project_id: str,
    authority_ref: Mapping[str, Any],
    *,
    difference_ref: Mapping[str, Any],
    required_capability: str,
    boundary_ref: Mapping[str, Any],
    human_authority_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve, schema-validate, identity-recompute and re-bind the real Authority Decision a
    Work Unit's own ``authority_ref`` names (P16-C1's "explicit Authority reference and
    decision").

    A Work Unit never carries a caller-asserted "authorized" flag: it carries a reference to a
    genuinely committed, content-addressed decision record minted by the existing Authority
    owner's own :func:`~manosube_agent_civilization.authority.
    evaluate_model_execution_authorization`. Resolving it here re-proves, on **every** later
    call, that the decision exists, is internally self-consistent, actually says
    ``MODEL_EXECUTION_AUTHORIZED``, and was made about exactly this Difference, this capability,
    this Boundary and this Human Authority -- so a decision legitimately made for one question
    can never be replayed as the authority for a different one.
    """

    resolved = _resolve(store, project_id, DECISION_RECORD_KIND, authority_ref)
    decision = require_valid_model_execution_decision(resolved)
    _require_same_project(decision, project_id, DECISION_RECORD_KIND)
    if model_execution_decision_id(decision) != decision.get("model_execution_decision_id"):
        raise ModelRecordIntegrityError(
            f"resolved model_execution_decision {authority_ref['id']!r} own recomputed identity "
            "does not equal its own declared value -- refusing to trust it"
        )
    if decision["decision"] != MODEL_EXECUTION_AUTHORIZED:
        raise ModelRuntimeRequirementError(
            f"resolved model_execution_decision {authority_ref['id']!r} does not authorize model "
            f"execution ({decision['decision']!r}) -- refused before any adapter call"
        )
    for field, expected in (
        ("difference_ref", dict(difference_ref)),
        ("required_capability", required_capability),
        ("boundary_ref", dict(boundary_ref)),
    ):
        if decision[field] != expected:
            raise ModelRuntimeRequirementError(
                f"resolved model_execution_decision own {field} does not equal this Work Unit's "
                f"own: {decision[field]!r} != {expected!r} -- a decision genuinely made for one "
                "question may never authorize a different one"
            )
    if decision["selection_authority_ref"] != dict(human_authority_ref):
        raise ModelRuntimeAuthorityFreshnessError(
            "resolved model_execution_decision was made under a different Human Authority than "
            "the one this call's own fresh Boot restored -- refusing before any adapter call"
        )
    return decision


def _resolve_work_unit(
    store: Any, project_id: str, work_unit_ref: Mapping[str, Any]
) -> dict[str, Any]:
    resolved = _resolve(store, project_id, WORK_UNIT_RECORD_KIND, work_unit_ref)
    work_unit = require_valid_model_work_unit(resolved)
    _require_same_project(work_unit, project_id, WORK_UNIT_RECORD_KIND)
    if model_work_unit_id(work_unit) != work_unit.get("model_work_unit_id"):
        raise ModelRecordIntegrityError(
            f"resolved model_work_unit {work_unit_ref['id']!r} own recomputed identity does not "
            "equal its own declared value -- refusing to trust any of its fields"
        )
    if model_work_unit_semantic_fingerprint(work_unit) != work_unit.get(
        "model_work_unit_semantic_fingerprint"
    ):
        raise ModelRecordIntegrityError(
            f"resolved model_work_unit {work_unit_ref['id']!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust it"
        )
    if work_unit["model_work_unit_id"] != work_unit_ref["id"]:
        raise ModelRecordIntegrityError(
            "resolved model_work_unit does not carry the identity it was resolved by: "
            f"{work_unit['model_work_unit_id']!r} != {work_unit_ref['id']!r}"
        )
    return work_unit


def _resume_from_store(
    store: Any,
    *,
    project_id: str,
    held: Mapping[str, Any],
    fresh: Mapping[str, Any],
    work_unit_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild, from Store-resolved canonical records alone, everything an Agent needs to
    continue this exact Work Unit (P16-C4/P16-C5).

    Nothing here is carried in memory across a session boundary: every record is resolved fresh
    by content address, schema-validated, identity-recomputed, project-bound, Binding-bound and
    Authority-bound, in that order. That is why a totally lost session is recoverable, and why
    stale, substituted, cross-project, wrong-Difference, wrong-Authority, wrong-Boundary and
    wrong-State-revision material is all refused **before any adapter call** rather than after
    one.
    """

    work_unit = _resolve_work_unit(store, project_id, work_unit_ref)
    if work_unit["project_binding_ref"] != fresh["project_binding_ref"]:
        raise ModelRuntimeRequirementError(
            "resolved model_work_unit is bound to a different Project Binding than this call's "
            f"own execution contract: {work_unit['project_binding_ref']!r} != "
            f"{fresh['project_binding_ref']!r}"
        )
    if work_unit["opened_state_revision"] > fresh["state_revision"]:
        raise ModelRuntimeStaleStateError(
            "resolved model_work_unit declares it was opened against State revision "
            f"{work_unit['opened_state_revision']}, which this Store has never reached "
            f"(current revision {fresh['state_revision']}) -- refusing before any adapter call"
        )
    if work_unit["opened_state_revision"] > held["state_revision"]:
        raise ModelRuntimeStaleStateError(
            "this call's own Phase 12 execution contract was established against State revision "
            f"{held['state_revision']}, which predates the revision this Work Unit was opened "
            f"against ({work_unit['opened_state_revision']}) -- an Agent whose own contract is "
            "older than the work it claims to continue is operating on a stale view of the "
            "world, and is refused before any adapter call"
        )
    difference = _resolve_difference(store, project_id, work_unit["difference_ref"])
    boundary = _resolve_boundary(
        store,
        project_id,
        work_unit["boundary_ref"],
        project_binding_ref=fresh["project_binding_ref"],
        required_capability=work_unit["required_capability"],
        human_authority_ref=fresh["human_authority_ref"],
    )
    decision = _resolve_authority_decision(
        store,
        project_id,
        work_unit["authority_ref"],
        difference_ref=work_unit["difference_ref"],
        required_capability=work_unit["required_capability"],
        boundary_ref=work_unit["boundary_ref"],
        human_authority_ref=fresh["human_authority_ref"],
    )
    return {
        "model_work_unit": work_unit,
        "difference": difference,
        "model_execution_boundary": boundary,
        "model_execution_decision": decision,
    }


# --------------------------------------------------------------------------- #
# Route 1 -- open one immutable, State-bound Work Unit
# --------------------------------------------------------------------------- #


def open_model_work_unit(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    difference_ref: Mapping[str, Any],
    required_capability: str,
    boundary_ref: Mapping[str, Any],
    model_execution_grant_refs: list[Mapping[str, Any]],
    opened_at: str,
) -> dict[str, Any]:
    """Open one canonical, immutable, State-bound Model Work Unit and return it.

    A Work Unit is genesis-only: it is opened exactly once by whichever Agent starts the work,
    is never mutated, has no current pointer and no transition chain, and is resolved by content
    address for the whole lifetime of the work. Two Agents "resuming the same Work Unit" resolve
    the identical address and independently re-verify the identical body -- which is what makes
    "the same Work Unit" a re-proved fact rather than a shared variable.

    Returns ``{"model_work_unit": ..., "model_work_unit_ref": ..., "model_execution_decision":
    ...}``. The Authority Decision is committed in the **same** State transition as the Work Unit
    that references it, so a Work Unit whose ``authority_ref`` resolves to nothing can never
    exist.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(opened_at, "opened_at")
    if required_capability not in MODEL_EXECUTION_CAPABILITIES:
        raise ModelRuntimeRequirementError(
            f"required_capability is not a recognized capability: {required_capability!r}"
        )
    checked_difference_ref = _require_reference(
        difference_ref, context="difference_ref", kind=DIFFERENCE_RECORD_KIND
    )
    checked_boundary_ref = _require_reference(
        boundary_ref, context="boundary_ref", kind=BOUNDARY_RECORD_KIND
    )
    if not isinstance(model_execution_grant_refs, list) or not model_execution_grant_refs:
        raise ModelRuntimeRequirementError(
            "model_execution_grant_refs must be a non-empty list of references -- a Work Unit "
            "opened against no Human Authority grant at all is never authorized"
        )
    checked_grant_refs = [
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
    _resolve_difference(store, project_id, checked_difference_ref)
    _resolve_boundary(
        store,
        project_id,
        checked_boundary_ref,
        project_binding_ref=fresh["project_binding_ref"],
        required_capability=required_capability,
        human_authority_ref=fresh["human_authority_ref"],
    )

    grants = [
        _resolve(store, project_id, GRANT_RECORD_KIND, reference)
        for reference in checked_grant_refs
    ]
    signing_key = fresh["human_authority_signing_key"]
    if not isinstance(signing_key, Mapping):
        raise ModelRuntimeRequirementError(
            "the Boot-restored project_binding carries no readable human_authority_signing_key "
            "-- a Model Execution Grant's own Human Authority signature cannot be verified "
            "against it, so nothing is authorized"
        )
    decision = evaluate_model_execution_authorization(
        {
            "schema_version": "0.1",
            "project_id": project_id,
            "difference_ref": checked_difference_ref,
            "required_capability": required_capability,
            "boundary_ref": checked_boundary_ref,
            "human_authority_ref": dict(fresh["human_authority_ref"]),
            "human_authority_signing_key": dict(signing_key),
            "grants": grants,
        }
    )
    if decision["decision"] != MODEL_EXECUTION_AUTHORIZED:
        raise ModelRuntimeRequirementError(
            "no real Human Authority grant authorizes this model execution capability for this "
            f"Difference and Boundary: {decision['decision']!r} "
            f"{decision['decision_reason_codes']!r} -- no Work Unit is opened, and no adapter is "
            "ever reached"
        )

    work_unit = derive_model_work_unit(
        project_id=project_id,
        project_binding_ref=dict(fresh["project_binding_ref"]),
        opened_state_revision=int(fresh["state_revision"]),
        opened_semantic_fingerprint=require_valid_semantic_fingerprint(
            fresh["semantic_fingerprint"], "the Boot-restored State semantic_fingerprint"
        ),
        difference_ref=checked_difference_ref,
        required_capability=required_capability,
        authority_ref={
            "kind": DECISION_RECORD_KIND,
            "id": str(decision["model_execution_decision_id"]),
        },
        boundary_ref=checked_boundary_ref,
        opened_at=opened_at,
    )
    _commit(
        store,
        project_id,
        [
            (
                DECISION_RECORD_KIND,
                str(decision["model_execution_decision_id"]),
                decision,
            ),
            (WORK_UNIT_RECORD_KIND, str(work_unit["model_work_unit_id"]), work_unit),
        ],
        committed_at=opened_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MODEL-WORK-UNIT",
        transaction_key=str(work_unit["model_work_unit_id"]),
    )
    return {
        "model_work_unit": work_unit,
        "model_work_unit_ref": {
            "kind": WORK_UNIT_RECORD_KIND,
            "id": str(work_unit["model_work_unit_id"]),
        },
        "model_execution_decision": decision,
    }


# --------------------------------------------------------------------------- #
# Route 2 -- one bounded, provider-neutral model execution
# --------------------------------------------------------------------------- #


def _canonical_request(
    *,
    request_identity: str,
    project_id: str,
    fresh: Mapping[str, Any],
    work_unit: Mapping[str, Any],
    boundary: Mapping[str, Any],
    work_unit_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """The one provider-neutral request/response boundary every model invocation is bound to
    (P16-C1).

    Carries exactly: the exact State revision and semantic fingerprint; the State-bound Work Unit
    identity; the same Difference reference; the required capability; the explicit Authority
    reference *and* the decision it records; the applicable Boundary reference and its resolved
    body; the Evidence requirements; and the Phase 12 Temporary Agent Execution Contract
    identity. It carries **no** provider payload, prompt text, chat transcript, model memory or
    provider session id -- there is no key here through which one could arrive, and the adapter
    receives nothing else at all.
    """

    return {
        "model_execution_request_identity": request_identity,
        "project_id": project_id,
        "project_binding_ref": dict(fresh["project_binding_ref"]),
        "state_revision": int(fresh["state_revision"]),
        "semantic_fingerprint": dict(fresh["semantic_fingerprint"]),
        "model_work_unit_ref": dict(work_unit_ref),
        "difference_ref": dict(work_unit["difference_ref"]),
        "required_capability": str(work_unit["required_capability"]),
        "authority_ref": dict(work_unit["authority_ref"]),
        "authority_decision": MODEL_EXECUTION_AUTHORIZED,
        "boundary_ref": dict(work_unit["boundary_ref"]),
        "boundary": dict(boundary),
        "evidence_requirements": dict(work_unit["evidence_requirements"]),
        "execution_contract": {
            "project_id": str(fresh["project_id"]),
            "project_binding_ref": dict(fresh["project_binding_ref"]),
            "state_revision": int(fresh["state_revision"]),
            "semantic_fingerprint": dict(fresh["semantic_fingerprint"]),
            "human_authority_ref": dict(fresh["human_authority_ref"]),
        },
    }


def _normalize(
    raw: Any, *, boundary: Mapping[str, Any]
) -> tuple[str, str | None, dict[str, Any] | None, str | None]:
    """Turn one adapter's own untrusted result into this route's own typed, bounded outcome.

    Normalization happens **here**, before any candidate reaches a canonical record or the
    existing Evidence owner (P16-C3). Exactly three keys are read
    (:data:`~manosube_agent_civilization.model_runtime.types.MODEL_ADAPTER_RESULT_KEYS`); every
    other key an adapter returns is invisible to this route, which is what makes an adapter's
    attempt to authorize itself, mint Evidence or close a Difference structurally impossible
    rather than merely refused.

    ``CANDIDATE_ACCEPTED`` is computed here and nowhere else. An adapter that reports a field
    the Boundary never permitted, a candidate kind it never permitted, or the route-only
    accepting classification itself, is an adapter defect
    (:class:`~manosube_agent_civilization.model_runtime.errors.ModelAdapterError`) -- never
    silently dropped, and never recorded as any outcome at all.

    One route-level downgrade exists and is deliberate: an adapter reporting ``CANDIDATE`` whose
    bounded projection retains **no** permitted field at all has not produced a candidate this
    Boundary can carry, and is recorded as ``INCOMPLETE_EVIDENCE`` rather than as an accepted
    candidate over an empty object. That direction is the only one taken anywhere here: no
    failure is ever converted into success, and no outcome is ever converted into an
    authoritative absence of a result.
    """

    if not isinstance(raw, Mapping):
        raise ModelAdapterError(f"adapter.execute() returned {raw!r}, not a mapping")
    adapter_outcome = raw.get(MODEL_ADAPTER_RESULT_KEYS[0])
    if adapter_outcome not in MODEL_ADAPTER_OUTCOMES:
        raise ModelAdapterError(
            "adapter.execute()'s own adapter_outcome is not an adapter-reportable outcome: "
            f"{adapter_outcome!r} -- the accepting classification is computed by this route "
            "alone and may never be claimed by an adapter"
        )
    if adapter_outcome != "CANDIDATE":
        return str(adapter_outcome), None, None, None

    candidate_kind = raw.get(MODEL_ADAPTER_RESULT_KEYS[1])
    if candidate_kind not in list(boundary["permitted_candidate_kinds"]):
        raise ModelAdapterError(
            "adapter.execute() proposed a candidate_kind the Model Execution Boundary never "
            f"permitted: {candidate_kind!r} not in "
            f"{list(boundary['permitted_candidate_kinds'])!r}"
        )
    candidate_fields = raw.get(MODEL_ADAPTER_RESULT_KEYS[2])
    if not isinstance(candidate_fields, Mapping):
        raise ModelAdapterError(
            "adapter.execute() reported CANDIDATE with no readable candidate_fields: "
            f"{candidate_fields!r}"
        )
    permitted = list(boundary["permitted_candidate_fields"])
    extra = sorted(set(candidate_fields) - set(permitted))
    if extra:
        raise ModelAdapterError(
            "adapter.execute() reported candidate field(s) outside the Model Execution "
            f"Boundary's own permitted_candidate_fields: {extra} -- refusing rather than persist "
            "anything the Boundary never admitted, and never widening the Boundary to fit"
        )
    normalized = {
        field: candidate_fields[field] for field in permitted if field in candidate_fields
    }
    if not normalized:
        return "INCOMPLETE_EVIDENCE", None, None, None
    return (
        "CANDIDATE_ACCEPTED",
        str(candidate_kind),
        normalized,
        model_candidate_fingerprint(normalized),
    )


def execute_model_work_unit(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    model_work_unit_ref: Mapping[str, Any],
    adapter: ModelAdapter,
    executed_at: str,
) -> dict[str, Any]:
    """Execute one bounded, provider-neutral model invocation against one already-open Work Unit
    and return ``{"envelope": ..., "receipt": ModelExecutionReceipt}``.

    *model_work_unit_ref* is resolved from the canonical Store by content address alone -- no
    conversation handoff, no model memory, no provider-local session, and nothing carried in
    memory from whatever Agent opened it, is required or accepted. *executed_at* is a required,
    caller-supplied instant (this route reads no clock, the identical discipline every other
    route in this repository already requires).

    Every refusal below lands with the adapter called **zero** times and nothing committed: a
    released or foreign Temporary Agent, a stale execution contract, a Work Unit that does not
    resolve or whose own identity does not recompute, a Difference/Boundary/Authority reference
    that does not resolve or does not restate this exact question, a Boundary or Authority
    Decision belonging to a different Human Authority, and a Work Unit claiming a State revision
    this Store never reached. Only after all of them does the adapter exist at all, and what it
    then returns can only ever become one of the seven typed outcomes.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(executed_at, "executed_at")
    checked_work_unit_ref = _require_reference(
        model_work_unit_ref, context="model_work_unit_ref", kind=WORK_UNIT_RECORD_KIND
    )

    held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=False,
    )
    resumed = _resume_from_store(
        store,
        project_id=project_id,
        held=held,
        fresh=fresh,
        work_unit_ref=checked_work_unit_ref,
    )
    work_unit = resumed["model_work_unit"]
    boundary = resumed["model_execution_boundary"]

    declared_identity = getattr(adapter, "adapter_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise ModelAdapterError(
            "adapter does not declare a readable adapter_identity attribute -- an unstated or "
            "unverifiable identity may never execute on this route's behalf"
        )
    adapter_identity = _plain(declared_identity)

    request_identity = model_execution_request_identity(
        model_work_unit_id_value=str(work_unit["model_work_unit_id"]),
        state_revision=int(fresh["state_revision"]),
        semantic_fingerprint=dict(fresh["semantic_fingerprint"]),
        adapter_identity=adapter_identity,
    )
    request = _canonical_request(
        request_identity=request_identity,
        project_id=project_id,
        fresh=fresh,
        work_unit=work_unit,
        boundary=boundary,
        work_unit_ref=checked_work_unit_ref,
    )

    # Authority freshness at the adapter boundary: everything above was verified against the
    # world as it stood at this call's own fresh Boot. Re-prove that world is still the one in
    # force before a model is reached at all -- a Binding/Authority change lands here as a
    # refusal with zero adapter calls, never as a model reached under stale Authority.
    _require_authority_current(
        fresh,
        _fresh_execution_contract(
            store, project_id=project_id, project_binding_id=project_binding_id
        ),
        stage="before the adapter is reached",
    )

    # The adapter receives deep-frozen, alias-free copies: a replaceable adapter could otherwise
    # mutate the exact structures this route validated and then goes on to fingerprint, persist
    # and attest to, so that what was committed would differ from what was actually checked.
    raw = adapter.execute(request=deep_freeze(request))
    outcome, candidate_kind, normalized_candidate, candidate_fingerprint = _normalize(
        raw, boundary=boundary
    )

    envelope = derive_model_execution_envelope(
        project_id=project_id,
        project_binding_ref=dict(fresh["project_binding_ref"]),
        model_work_unit_ref=checked_work_unit_ref,
        model_execution_request_identity=request_identity,
        executed_state_revision=int(fresh["state_revision"]),
        executed_semantic_fingerprint=dict(fresh["semantic_fingerprint"]),
        adapter_identity=adapter_identity,
        executed_at=executed_at,
        execution_outcome=outcome,
        normalized_candidate_kind=candidate_kind,
        normalized_candidate=normalized_candidate,
        normalized_candidate_fingerprint=candidate_fingerprint,
        difference_ref=dict(work_unit["difference_ref"]),
        required_capability=str(work_unit["required_capability"]),
        authority_ref=dict(work_unit["authority_ref"]),
        boundary_ref=dict(work_unit["boundary_ref"]),
        evidence_requirements=dict(work_unit["evidence_requirements"]),
        human_authority_ref=dict(fresh["human_authority_ref"]),
    )
    if (
        model_execution_envelope_semantic_fingerprint(envelope)
        != envelope["model_execution_semantic_fingerprint"]
    ):
        raise ModelRecordIntegrityError(
            "newly derived Envelope's own recomputed semantic fingerprint does not equal its own "
            "declared value -- refusing to commit"
        )
    _commit(
        store,
        project_id,
        [
            (
                ENVELOPE_RECORD_KIND,
                str(envelope["model_execution_envelope_id"]),
                envelope,
            )
        ],
        committed_at=executed_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MODEL-EXECUTION",
        transaction_key=str(envelope["model_execution_envelope_id"]),
    )

    receipt = ModelExecutionReceipt(
        status=MODEL_OUTCOME_TO_RECEIPT_STATUS[outcome],
        model_execution_envelope_id=str(envelope["model_execution_envelope_id"]),
        project_id=project_id,
        model_work_unit_ref=checked_work_unit_ref,
        adapter_identity=adapter_identity,
        difference_ref=dict(work_unit["difference_ref"]),
        authority_ref=dict(work_unit["authority_ref"]),
        boundary_ref=dict(work_unit["boundary_ref"]),
        required_capability=str(work_unit["required_capability"]),
        evidence_requirements=dict(work_unit["evidence_requirements"]),
        human_authority_ref=dict(fresh["human_authority_ref"]),
        input_refs=(dict(work_unit["difference_ref"]), dict(checked_work_unit_ref)),
        observations={
            "execution_outcome": outcome,
            "normalized_candidate_fingerprint": candidate_fingerprint,
            "executed_at": executed_at,
        },
    )
    return {"envelope": envelope, "receipt": receipt}


# --------------------------------------------------------------------------- #
# Route 3 -- prove one Adapter/Agent stopped and another resumed the same Work Unit
# --------------------------------------------------------------------------- #


def _resolve_envelope(
    store: Any,
    project_id: str,
    reference: Mapping[str, Any],
    *,
    work_unit: Mapping[str, Any],
    work_unit_ref: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    resolved = _resolve(store, project_id, ENVELOPE_RECORD_KIND, reference)
    envelope = require_valid_model_execution_envelope(resolved)
    _require_same_project(envelope, project_id, ENVELOPE_RECORD_KIND)
    if model_execution_envelope_id(envelope) != envelope.get("model_execution_envelope_id"):
        raise ModelRecordIntegrityError(
            f"resolved {role} model_execution_envelope {reference['id']!r} own recomputed "
            "identity does not equal its own declared value -- refusing to trust it"
        )
    if model_execution_envelope_semantic_fingerprint(envelope) != envelope.get(
        "model_execution_semantic_fingerprint"
    ):
        raise ModelRecordIntegrityError(
            f"resolved {role} model_execution_envelope {reference['id']!r} own recomputed "
            "semantic fingerprint does not equal its own declared value -- refusing to trust it"
        )
    if envelope["model_work_unit_ref"] != dict(work_unit_ref):
        raise ModelRuntimeRequirementError(
            f"resolved {role} model_execution_envelope names a different Work Unit than the one "
            f"this swap is about: {envelope['model_work_unit_ref']!r} != {dict(work_unit_ref)!r}"
        )
    for field in CONTINUITY_FIELDS:
        if envelope[field] != work_unit[field]:
            raise ModelRuntimeRequirementError(
                f"resolved {role} model_execution_envelope own {field} does not equal the real, "
                f"resolved Work Unit's own: {envelope[field]!r} != {work_unit[field]!r} -- a "
                "continuity claim this route cannot independently re-prove is never recorded"
            )
    return envelope


def record_model_swap(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    model_work_unit_ref: Mapping[str, Any],
    predecessor_execution_ref: Mapping[str, Any],
    successor_execution_ref: Mapping[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    """Record one canonical Model Swap Receipt and return ``{"model_swap_receipt": ...,
    "model_swap_receipt_ref": ..., "predecessor_envelope": ..., "successor_envelope": ...}`` --
    the two Envelopes being the real, Store-resolved, independently identity-recomputed bodies
    this route itself verified, never the caller's own copies of them.

    Proves, from Store-resolved canonical records alone, that two genuinely different Model
    Adapters executed the **identical** Work Unit while retaining identical Difference,
    Authority, Boundary and Evidence-requirement identities (P16-C4). Both Envelopes are
    re-resolved and independently identity-recomputed here; neither the caller's own claim about
    them, nor any receipt object it holds, is trusted.

    Refuses -- with nothing committed -- if either Envelope does not resolve, does not
    recompute, belongs to another project, names a different Work Unit, disagrees with the Work
    Unit on any continuity field, is the same Envelope twice, was produced by the *same* adapter
    identity (which is not a swap at all), or claims a predecessor that executed against a later
    State than its successor.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(recorded_at, "recorded_at")
    checked_work_unit_ref = _require_reference(
        model_work_unit_ref, context="model_work_unit_ref", kind=WORK_UNIT_RECORD_KIND
    )
    checked_predecessor_ref = _require_reference(
        predecessor_execution_ref,
        context="predecessor_execution_ref",
        kind=ENVELOPE_RECORD_KIND,
    )
    checked_successor_ref = _require_reference(
        successor_execution_ref, context="successor_execution_ref", kind=ENVELOPE_RECORD_KIND
    )
    if checked_predecessor_ref["id"] == checked_successor_ref["id"]:
        raise ModelRuntimeRequirementError(
            "predecessor_execution_ref and successor_execution_ref name the same Envelope -- one "
            "execution recorded twice is not a model swap"
        )

    held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=False,
    )
    resumed = _resume_from_store(
        store,
        project_id=project_id,
        held=held,
        fresh=fresh,
        work_unit_ref=checked_work_unit_ref,
    )
    work_unit = resumed["model_work_unit"]

    predecessor = _resolve_envelope(
        store,
        project_id,
        checked_predecessor_ref,
        work_unit=work_unit,
        work_unit_ref=checked_work_unit_ref,
        role="predecessor",
    )
    successor = _resolve_envelope(
        store,
        project_id,
        checked_successor_ref,
        work_unit=work_unit,
        work_unit_ref=checked_work_unit_ref,
        role="successor",
    )
    if predecessor["adapter_identity"] == successor["adapter_identity"]:
        raise ModelRuntimeRequirementError(
            "both Envelopes name the identical adapter_identity -- a model swap receipt states "
            "that a *different* Adapter resumed this Work Unit, and this route never records a "
            f"swap it cannot prove: {predecessor['adapter_identity']!r}"
        )
    if predecessor["executed_state_revision"] > successor["executed_state_revision"]:
        raise ModelRuntimeRequirementError(
            "the predecessor Envelope executed against a later State revision than the successor "
            f"({predecessor['executed_state_revision']} > "
            f"{successor['executed_state_revision']}) -- refusing to record a continuity claim "
            "whose own order is impossible"
        )

    receipt = derive_model_swap_receipt(
        project_id=project_id,
        project_binding_ref=dict(fresh["project_binding_ref"]),
        model_work_unit_ref=checked_work_unit_ref,
        predecessor_execution_ref=checked_predecessor_ref,
        predecessor_adapter_identity=dict(predecessor["adapter_identity"]),
        predecessor_state_revision=int(predecessor["executed_state_revision"]),
        predecessor_semantic_fingerprint=dict(predecessor["executed_semantic_fingerprint"]),
        successor_execution_ref=checked_successor_ref,
        successor_adapter_identity=dict(successor["adapter_identity"]),
        successor_state_revision=int(successor["executed_state_revision"]),
        successor_semantic_fingerprint=dict(successor["executed_semantic_fingerprint"]),
        difference_ref=dict(work_unit["difference_ref"]),
        required_capability=str(work_unit["required_capability"]),
        authority_ref=dict(work_unit["authority_ref"]),
        boundary_ref=dict(work_unit["boundary_ref"]),
        evidence_requirements=dict(work_unit["evidence_requirements"]),
        recorded_at=recorded_at,
    )
    if (
        model_swap_receipt_semantic_fingerprint(receipt)
        != receipt["model_swap_receipt_semantic_fingerprint"]
    ):
        raise ModelRecordIntegrityError(
            "newly derived Model Swap Receipt's own recomputed semantic fingerprint does not "
            "equal its own declared value -- refusing to commit"
        )
    _commit(
        store,
        project_id,
        [(SWAP_RECEIPT_RECORD_KIND, str(receipt["model_swap_receipt_id"]), receipt)],
        committed_at=recorded_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MODEL-SWAP",
        transaction_key=str(receipt["model_swap_receipt_id"]),
    )
    return {
        "model_swap_receipt": receipt,
        "model_swap_receipt_ref": {
            "kind": SWAP_RECEIPT_RECORD_KIND,
            "id": str(receipt["model_swap_receipt_id"]),
        },
        "predecessor_envelope": predecessor,
        "successor_envelope": successor,
    }


# --------------------------------------------------------------------------- #
# Route 4 -- recover a totally lost execution session from the canonical Store alone
# --------------------------------------------------------------------------- #


def recover_model_execution_session(
    store: Any,
    agent: TemporaryAgent,
    *,
    project_id: str,
    project_binding_id: str,
    model_work_unit_ref: Mapping[str, Any],
    recovered_at: str,
) -> dict[str, Any]:
    """Recover one Work Unit's complete execution context from the canonical Store alone and
    record one canonical Session Recovery Receipt (P16-C5).

    Returns ``{"session_recovery_receipt": ..., "session_recovery_receipt_ref": ...,
    "model_work_unit": ..., "difference": ..., "model_execution_boundary": ...,
    "model_execution_decision": ...}`` -- every one of which was resolved by content address,
    schema-validated, identity-recomputed, project-bound, Binding-bound and Authority-bound
    inside this call, with nothing carried over from the lost session.

    Recovery refuses, before any adapter could ever be reached, on stale State, substituted
    references, cross-project or cross-Store material, a wrong Difference, a wrong Authority, a
    wrong Boundary and a wrong State revision -- each with its own typed error, none of which is
    ever converted into a success, a closure, or an authoritative absence.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    require_valid_timestamp(recovered_at, "recovered_at")
    checked_work_unit_ref = _require_reference(
        model_work_unit_ref, context="model_work_unit_ref", kind=WORK_UNIT_RECORD_KIND
    )

    held, fresh = _live_contract(
        store,
        agent,
        project_id=project_id,
        project_binding_id=project_binding_id,
        require_exact_state=False,
    )
    resumed = _resume_from_store(
        store,
        project_id=project_id,
        held=held,
        fresh=fresh,
        work_unit_ref=checked_work_unit_ref,
    )
    work_unit = resumed["model_work_unit"]

    receipt = derive_session_recovery_receipt(
        project_id=project_id,
        project_binding_ref=dict(fresh["project_binding_ref"]),
        model_work_unit_ref=checked_work_unit_ref,
        recovered_state_revision=int(fresh["state_revision"]),
        recovered_semantic_fingerprint=dict(fresh["semantic_fingerprint"]),
        difference_ref=dict(work_unit["difference_ref"]),
        required_capability=str(work_unit["required_capability"]),
        authority_ref=dict(work_unit["authority_ref"]),
        boundary_ref=dict(work_unit["boundary_ref"]),
        evidence_requirements=dict(work_unit["evidence_requirements"]),
        recovered_at=recovered_at,
    )
    if (
        session_recovery_receipt_semantic_fingerprint(receipt)
        != receipt["session_recovery_receipt_semantic_fingerprint"]
    ):
        raise ModelRecordIntegrityError(
            "newly derived Session Recovery Receipt's own recomputed semantic fingerprint does "
            "not equal its own declared value -- refusing to commit"
        )
    _commit(
        store,
        project_id,
        [
            (
                RECOVERY_RECEIPT_RECORD_KIND,
                str(receipt["session_recovery_receipt_id"]),
                receipt,
            )
        ],
        committed_at=recovered_at,
        project_binding_id=project_binding_id,
        expected_authority=fresh,
        transaction_prefix="TX-MODEL-SESSION-RECOVERY",
        transaction_key=str(receipt["session_recovery_receipt_id"]),
    )
    return {
        "session_recovery_receipt": receipt,
        "session_recovery_receipt_ref": {
            "kind": RECOVERY_RECEIPT_RECORD_KIND,
            "id": str(receipt["session_recovery_receipt_id"]),
        },
        **resumed,
    }


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
    """Durably persist *records* through the Store's own single sanctioned committer
    (:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
    primitive Reflow, Binding, Projection and Runtime already share), with a bounded
    Compare-And-Swap retry against genuine, unrelated contention only.

    The authority-defining context is re-proved on **every** attempt, not once before the loop:
    a retry exists precisely because the Store moved underneath this call, and the whole point of
    the check is to distinguish a harmless unrelated commit (which bumps ``state_revision`` alone
    and must not block anything) from a genuine Binding/Human Authority change (which must refuse
    rather than commit a record carrying now-stale Authority into newer State). This is the
    identical P15-R1-F5 discipline, applied to this package's own records.

    A record already resolved at this exact ``(kind, id)`` is, by construction, byte-identical
    content -- every id here is a pure content address over its own complete record -- so
    committing it again is a genuine idempotent replay, never a conflict. A
    ``RecordConflictError`` here would mean a real hash collision or a genuine tamper between
    derivation and commit: refused, never silently retried.
    """

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
            raise ModelRecordIntegrityError(
                "a different record already occupies one of "
                f"{[f'{kind}/{identity}' for kind, identity, _body in records]} with different "
                "content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
    raise ModelRuntimeRequirementError(
        f"could not durably commit {[kind for kind, _identity, _body in records]} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


__all__ = [
    "MODEL_RUNTIME_SCHEMA_BASE",
    "execute_model_work_unit",
    "open_model_work_unit",
    "record_model_swap",
    "recover_model_execution_session",
]
