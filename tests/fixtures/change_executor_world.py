"""Phase 18 (Issue #73) shared Change Executor test world.

Deliberately self-contained, the identical "each phase's own fixture module builds its own
``bound()`` from ``tests.fixtures.product_binding`` directly" discipline
``tests/fixtures/url_boot_world.py``/``tests/fixtures/model_runtime_world.py`` already keep --
never importing another phase's own ``tests/fixtures/*_world.py`` module. It does reuse the
shared, cross-suite, real-route-only builders every other suite in this repository already
shares (``tests.change_helpers``, ``tests.authority_helpers``) -- those are not a phase's own
fixture *world*, they are the "never hand-forge a Change or an Authority Decision" discipline
the task itself asks for, exactly as :mod:`tests.evidence_helpers` already reuses them for its
own Evidence route.

**The one genuinely hard part, solved the way ``tests/fixtures/vertical_proof.py`` solves it.**
``authority/engine.py`` requires ``difference["observed_state_revision"] == current_state_
revision`` (and the matching fingerprint) *exactly* -- and, one layer up, Change Executor's own
``route.py`` requires the resulting Change's ``before_state_fingerprint``/``expected_state_
revision`` to equal the *freshly Booted* current State of the real, bound project a test is
executing against. A canned, ad hoc Difference fixture (the kind ``tests.difference_helpers``
hands out by default, pinned to its own arbitrary ``state_fingerprint()``) will not align with a
real ``FileStateStore``'s own genesis (or since-advanced) State. This module therefore never
uses that default: :func:`build_committed_change` derives its own Difference, from scratch, from
the caller-supplied *current_state* (or a fresh ``store.load_current`` read) every single call,
the identical "build a Difference bound to the real State I actually have" technique
``vertical_proof.py``'s own docstring names as the hard part -- so a Change built here is always
genuinely, freshly staleness-clean against whatever the Store's current State actually is at
call time, never merely self-consistent in isolation.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from tests.authority_helpers import action as authority_action, rule as authority_rule
from tests.change_helpers import route as change_route
from tests.fixtures.change_executor_kill_switch_issuer import (
    issuer_public_key_hex,
    mint_kill_switch_signature,
)
from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.scope import canonical_scope
from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.change.engine import derive_change
from manosube_agent_civilization.change_executor.adapter import ControlledFilesystemAdapter
from manosube_agent_civilization.change_executor.kill_switch import (
    KILL_SWITCH_RECORD_KIND,
    commit_change_executor_kill_switch,
    kill_switch_id,
    kill_switch_semantic_fingerprint,
    kill_switch_signing_payload,
)
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import StaleStateError

#: This world's own repository/branch -- shared by every Change's ``scope`` and every Execution
#: Boundary a test builds from :func:`execution_boundary_for`, so the two agree by construction.
REPOSITORY = "manosube/example-change-executor-fixture"
BRANCH = "main"

DEFAULT_TIME_WINDOW: dict[str, str] = {
    "issued_at": "2026-09-10T00:00:00Z",
    "expires_at": "2026-09-10T01:00:00Z",
}

_PREDICATE_ID = "TP-CE-0001"
_SCOPE_ID = "OBS-SCOPE-CE-0001"
_SUBJECT = "change_executor.readiness_marker"
_SNAPSHOT_REF: dict[str, str] = {"kind": "source_snapshot", "id": "SNAP-CE-0001"}
_METHOD_REF: dict[str, str] = {"kind": "observation_method", "id": "OBS-METHOD-CE-0001"}
_OBSERVATION_METHOD: dict[str, Any] = {
    "method_profile": "MANOSUBE-OBSERVATION-METHOD-SHA256-0.1",
    "procedure_kind": "CANONICAL_OBSERVER",
    "procedure_ref": {
        "kind": "observer_procedure",
        "id": "OBS-PROCEDURE-CE-0001",
        "version": "0.1",
        "semantic_fingerprint": "sha256:" + "c" * 64,
    },
    "normalization_profile": "FIXTURE-0.1",
    "input_contract_ref": {"kind": "schema", "id": "OBS-INPUT-01"},
    "output_contract_refs": {
        "collection_kind": "UNORDERED_SET",
        "members": [{"kind": "schema", "id": "NORMALIZED-FACT-01"}],
    },
    "execution_boundary_ref": {"kind": "execution_boundary", "id": "KERNEL-LOCAL"},
}

_CHANGE_RECORD_KIND = "change"
_AUTHORITY_DECISION_RECORD_KIND = "authority_decision"


def bound(tmp_path: Path, *, subdir: str = "backend") -> tuple[FileStateStore, dict[str, Any]]:
    """One real ``FileStateStore`` with one real, genuinely bound project.

    *subdir* exists so a test can build a **second, entirely separate Store** under the same
    ``tmp_path`` (cross-Store substitution controls, V6)."""

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


def bound_with_project_id(
    tmp_path: Path, project_id: str, *, subdir: str = "backend"
) -> tuple[FileStateStore, dict[str, Any]]:
    """The identical real binding :func:`bound` performs, except under a genuinely distinct,
    caller-chosen *project_id* -- ``tests.fixtures.product_binding`` itself hardcodes a single
    module-level ``PROJECT_ID`` throughout every nested record it builds, so this rewrites that
    one identity everywhere it appears (including recomputing the one content-addressed identity
    that is itself a function of it, the Authority Rule's own ``authority_rule_id``) before
    binding for real. Needed only where a test genuinely requires two distinct, independently
    booted projects (never merely two Stores) -- e.g. a Change resolving under one project's own
    directory while its own declared content still names a different, equally real, equally
    booted one."""

    from manosube_agent_civilization.authority.identity import rule_id

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    kwargs = deepcopy(bind_project_kwargs())
    kwargs["project_id"] = project_id
    kwargs["objective_revision"]["project_id"] = project_id
    kwargs["authority_rule"]["project_id"] = project_id
    kwargs["authority_rule"]["authority_rule_id"] = rule_id(kwargs["authority_rule"])
    kwargs["authority_policy_ref"] = {
        "kind": "authority_rule",
        "id": kwargs["authority_rule"]["authority_rule_id"],
    }
    kwargs["genesis_state"]["project_id"] = project_id
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": project_id,
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }


# --------------------------------------------------------------------------------------- #
# Difference / Authority / Change -- built fresh against the real current State every time.
# --------------------------------------------------------------------------------------- #


def _objective_revision(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "objective_id": "OBJ-CE-0001",
        "objective_revision_id": "OBJ-REV-CE-0001",
        "project_id": project_id,
        "statement": "The change_executor fixture readiness marker reaches READY.",
        "owner_authority_ref": {"kind": "human_authority", "id": "AUTH-CE-0001"},
        "target_predicates": [
            {
                "predicate_id": _PREDICATE_ID,
                "subject": _SUBJECT,
                "operator": "equals",
                "expected_value": "READY",
                "observation_scope": "change_executor",
                "evidence_requirement": "E1",
                "unknown_policy": "INCOMPLETE",
                "criticality": "mandatory",
            }
        ],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-CE-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": "initial change_executor fixture objective",
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial change_executor fixture objective revision",
        "human_authority_ref": {"kind": "human_authority", "id": "AUTH-CE-0001"},
        "recorded_at": "2026-09-05T08:00:00Z",
    }


def _observation_scope(project_id: str) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "scope_id": _SCOPE_ID,
        "project_id": project_id,
        "target_identity": _PREDICATE_ID,
        "included_subjects": [_SUBJECT],
        "excluded_subjects": ["change_executor.secret"],
        "boundary_root": "/change_executor",
        "path_policy": {
            "relative_locators_only": True,
            "symlink_escape": "BLOCK",
            "submodule_traversal": "DECLARED_ONLY",
            "mount_escape": "BLOCK",
            "credential_paths": "EXCLUDE",
        },
        "observation_window": {"start": "2026-09-05T08:00:00Z", "end": "2026-09-05T09:00:00Z"},
        "target_effective_window": {
            "start": "2026-09-05T07:00:00Z",
            "end": "2026-09-05T09:00:00Z",
        },
        "freshness_limit_seconds": 3600,
        "cutoff": "2026-09-05T09:00:00Z",
        "source_snapshot_refs": [dict(_SNAPSHOT_REF)],
        "enumeration_rule": {"kind": "enumeration_rule", "id": "ENUM-CE-0001"},
        "completion_predicate": {"kind": "completion_predicate", "id": "COMPLETE-CE-0001"},
        "method_ref": dict(_METHOD_REF),
        "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
        "blind_spots": [],
        "scope_status": "COMPLETE",
    }


def _observation_request(
    project_id: str, *, fingerprint: dict[str, Any], state_revision: int
) -> dict[str, Any]:
    scope = _observation_scope(project_id)
    fact = {
        "subject": _SUBJECT,
        "predicate": "equals@v1",
        "value": "NOT-READY",
        "value_type": "STRING",
        "unit": None,
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": _SNAPSHOT_REF["id"],
            "start": None,
            "end": None,
        },
    }
    return {
        "project_id": project_id,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(fingerprint),
        "target_identity": _PREDICATE_ID,
        "target_kind": "FIXTURE",
        "scope": scope,
        "method_ref": dict(_METHOD_REF),
        "time_boundary": {
            "observation_started_at": "2026-09-05T08:05:00Z",
            "observation_ended_at": "2026-09-05T08:05:30Z",
            "target_effective_start": "2026-09-05T07:00:00Z",
            "target_effective_end": "2026-09-05T09:00:00Z",
            "source_snapshot_time": "2026-09-05T08:04:00Z",
        },
        "source_snapshot_refs": [dict(_SNAPSHOT_REF)],
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": dict(_SNAPSHOT_REF),
                "source_locator": "fixtures/change_executor_world.txt",
                "facts": [fact],
            }
        ],
        "attempts": [
            {
                "attempt_id": "ATTEMPT-CE-0001",
                "method_ref": dict(_METHOD_REF),
                "started_at": "2026-09-05T08:05:00Z",
                "ended_at": "2026-09-05T08:05:30Z",
                "result": "COMPLETE",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [{"kind": "observation_evidence", "id": "EVID-CE-0001"}],
        "negative_evidence_refs": [{"kind": "negative_evidence", "id": "NEG-EVID-CE-0001"}],
        "negative_claims": [],
        "collection_complete": True,
    }


def _derived_difference(
    project_id: str, *, state_revision: int, state_fingerprint: dict[str, Any]
) -> dict[str, Any]:
    """One real Difference, freshly derived against *state_revision*/*state_fingerprint* --
    always the caller's own real, currently-committed values, never a canned constant (see this
    module's own docstring)."""

    bundle = observe(
        _observation_request(
            project_id, fingerprint=state_fingerprint, state_revision=state_revision
        )
    )
    request = {
        "schema_version": "0.1",
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
        "comparison_profile": "MANOSUBE-DIFFERENCE-COMPARISON-0.1",
        "normalization_profile": "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1",
        "project_id": project_id,
        "objective_revision": _objective_revision(project_id),
        "state_revision": state_revision,
        "state_fingerprint": deepcopy(state_fingerprint),
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
        "observation_method": deepcopy(_OBSERVATION_METHOD),
        "bindings": [
            {
                "target_predicate_id": _PREDICATE_ID,
                "observation_scope": _observation_scope(project_id),
                "observation_bundle": bundle,
            }
        ],
    }
    result = derive_differences(request)
    difference: dict[str, Any] = result["differences"][0]
    return difference


def _commit_records(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    committed_at: str,
    *,
    transaction_prefix: str,
) -> dict[str, Any]:
    """The identical bounded Compare-And-Swap commit template every real committer in this
    repository shares -- this fixture module is the one place that commits a Change/Authority
    Decision pair to the Store, since nothing in the shipped ``change_executor`` package itself
    ever does (route.py only ever *resolves* a pre-existing Change/Authority Decision)."""

    for _ in range(8):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
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
            return commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=records,
            )
        except StaleStateError:
            continue
    raise RuntimeError(f"could not durably commit under prefix {transaction_prefix!r}")


def build_committed_change(
    store: Any,
    project_id: str,
    *,
    action_kind: str,
    operation: dict[str, Any],
    paths: list[str],
    repository: str = REPOSITORY,
    branch: str = BRANCH,
    reversibility: str = "REVERSIBLE",
    current_state: dict[str, Any] | None = None,
    committed_at: str = "2026-09-10T00:00:00Z",
    extra_state_revision_headroom: int = 0,
) -> dict[str, Any]:
    """Build, through the real ``evaluate_authority``/``derive_change`` route (never a
    hand-forged decision or Change), one genuinely AUTONOMOUS Change for *action_kind* over
    *paths*, freshly aligned to the Store's own real current State -- then commit both the
    Change and its own Authority Decision into *store*.

    *extra_state_revision_headroom* -- a disclosed, test-only isolation technique, never
    anything a genuine production caller could supply. It exists because ``route.py``'s own
    staleness check (step 9) runs *before* its own idempotency-slot resolution (step 10), and
    this package's own commits (``execution_intent``/``execution_attempt``/
    ``change_execution_receipt``) each unconditionally advance the Store's ``state_revision``
    counter by one, regardless of terminal outcome -- so a Change is stale-by-construction for
    any *second* ``execute()`` call made against it once the *first* call has committed anything
    at all (see ``tests/integration/change_executor/
    test_change_executor_idempotency_crash_matrix.py``'s own module docstring for the full
    finding). Passing the exact number of Store-revision-advancing commits a test's own setup
    will perform *after* this function returns and *before* the ``execute()`` call under test
    predicts the Change's own ``expected_state_revision`` far enough ahead to still land exactly
    on the real value current at call time -- letting a test reach and isolate a specific
    idempotency-slot mechanism (concurrent claim, reconciliation-required, terminal-claim
    mismatch, semantic reuse) that the staleness-ordering defect would otherwise mask entirely.
    Defaults to ``0`` (the ordinary, single-call case every other test in this suite uses).

    **Why this derives the Difference against ``current_state_revision + 1``, not the current
    revision itself.** Every commit through this repository's own single sanctioned committer
    (``commit_state_transition``) unconditionally advances ``state_revision`` by exactly one --
    including this very function's own commit of the Change/Authority Decision pair below, which
    touches no ``semantic_state`` content at all. ``state.fingerprint.fingerprint_project_state``
    hashes only ``semantic_state`` (never ``state_revision``/``lineage_head_ref``), so that
    commit leaves the *fingerprint* genuinely unchanged while still advancing the *revision*
    counter by one. ``route.py``'s own staleness check (V6 covers the positive/negative form of
    this exact check) requires a Change's own ``expected_state_revision`` to equal the *freshly
    Booted* current revision **exactly** -- so a Change derived against the pre-commit revision
    would be stale by construction the instant this function's own commit lands. Deriving
    against the revision this commit is *about to produce* (with the *current*, unchanged
    fingerprint, since this commit's own ``next_state`` never differs from *current* in its own
    ``semantic_state``) is what keeps a Change genuinely fresh immediately after
    :func:`build_committed_change` returns it -- exactly the discipline a real Change-persisting
    caller would need, which nothing in the shipped ``change_executor`` package supplies (see
    this module's own docstring).

    Returns ``{"change", "decision", "difference"}`` -- every intermediate real record a caller
    might independently want to inspect or tamper with post-commit.
    """

    current = current_state if current_state is not None else store.load_current(project_id)
    state_revision = current["state_revision"] + 1 + extra_state_revision_headroom
    state_fingerprint = current["semantic_fingerprint"]

    difference = _derived_difference(
        project_id, state_revision=state_revision, state_fingerprint=state_fingerprint
    )

    requested_scope = canonical_scope(
        {"repository": repository, "branch": branch, "paths": list(paths), "subjects": []}
    )
    requested_action = authority_action(
        action_kind=action_kind, reversibility=reversibility, operation=operation
    )
    rule = authority_rule(
        project_id,
        action_kinds=[action_kind],
        maximum_reversibility=reversibility,
        rule_scope=requested_scope,
    )

    _authority_input, decision, change_request = change_route(
        difference, requested_action, requested_scope, rules=[rule]
    )
    change = derive_change(change_request)

    _commit_records(
        store,
        project_id,
        [
            (_CHANGE_RECORD_KIND, change["change_id"], change),
            (_AUTHORITY_DECISION_RECORD_KIND, decision["authority_decision_id"], decision),
        ],
        committed_at,
        transaction_prefix=f"TX-CE-CHANGE-{change['change_id']}",
    )
    return {"change": change, "decision": decision, "difference": difference}


def commit_foreign_record(
    store: Any,
    project_id: str,
    kind: str,
    record_id: str,
    body: dict[str, Any],
    *,
    committed_at: str = "2026-09-10T00:00:00Z",
) -> None:
    """Commit *body* verbatim under ``(project_id, kind, record_id)`` -- through the real,
    ordinary Store commit API, never a filesystem write -- even when *body*'s own declared
    content (e.g. its own ``project_id`` field) disagrees with *project_id* itself. Used to
    plant a genuinely-real record (never hand-forged) that resolves under one project's own
    directory while its own content still names a different one -- the exact cross-project
    substitution V2/V6 need, achieved through the same public commit surface every legitimate
    caller uses, not a filesystem shortcut."""

    _commit_records(
        store,
        project_id,
        [(kind, record_id, body)],
        committed_at,
        transaction_prefix=f"TX-CE-FOREIGN-{record_id}",
    )


def slot_key_for(
    change_id: str, boundary: dict[str, Any], adapter_identity: dict[str, Any]
) -> tuple[str, str, str]:
    """The identical mapping-slot key, Boundary fingerprint, and adapter-identity fingerprint
    ``route.py`` itself would compute for *change_id* under a composed executor bound to
    *boundary*/*adapter_identity* -- exposed here so a test can plant a real, standalone
    ``execution_intent``/``execution_attempt`` record at the exact slot a subsequent real
    ``execute()`` call will also resolve (V4's concurrent-claim and reconciliation-required
    controls)."""

    from manosube_agent_civilization.change_executor.boundary import (
        execution_boundary_fingerprint,
        validate_execution_boundary,
    )
    from manosube_agent_civilization.change_executor.identity import execution_mapping_slot_key

    canonical_boundary = validate_execution_boundary(boundary)
    boundary_fp = execution_boundary_fingerprint(canonical_boundary)
    adapter_fp = adapter_identity_fingerprint(adapter_identity)
    slot_key = execution_mapping_slot_key(change_id, boundary_fp, adapter_fp)
    return slot_key, boundary_fp, adapter_fp


def commit_bare_execution_intent(
    store: Any,
    project_id: str,
    *,
    change_id: str,
    boundary: dict[str, Any],
    adapter_identity: dict[str, Any],
    claim_token: str,
    requested_at: str,
    committed_at: str = "2026-09-10T00:00:00Z",
) -> dict[str, Any]:
    """Commit one real, schema-valid, standalone ``execution_intent`` -- built by the real
    ``engine.build_execution_intent`` -- directly to *store*, at the exact mapping slot a
    composed executor for *change_id*/*boundary*/*adapter_identity* would itself resolve.
    Nothing in the shipped package commits an ``execution_intent`` this way on its own; this is
    the test-only "a genuinely concurrent claim already holds this slot" setup V4(d) needs."""

    from manosube_agent_civilization.change_executor.engine import build_execution_intent

    slot_key, boundary_fp, adapter_fp = slot_key_for(change_id, boundary, adapter_identity)
    intent = build_execution_intent(
        project_id=project_id,
        change_ref={"kind": "change", "id": change_id},
        execution_boundary_fingerprint=boundary_fp,
        adapter_identity_fingerprint=adapter_fp,
        claim_token=claim_token,
        requested_at=requested_at,
    )
    commit_foreign_record(
        store, project_id, "execution_intent", slot_key, intent, committed_at=committed_at
    )
    return intent


def commit_bare_execution_attempt(
    store: Any,
    project_id: str,
    *,
    change_id: str,
    boundary: dict[str, Any],
    adapter_identity: dict[str, Any],
    claim_token: str,
    requested_at: str,
    committed_at: str = "2026-09-10T00:00:00Z",
) -> dict[str, Any]:
    """Commit one real, schema-valid, standalone ``execution_attempt`` (no receipt) directly to
    *store*, at the exact mapping slot a composed executor for the same triple would itself
    resolve -- the crash-recovery setup V4(e) needs."""

    from manosube_agent_civilization.change_executor.engine import build_execution_attempt

    slot_key, boundary_fp, adapter_fp = slot_key_for(change_id, boundary, adapter_identity)
    # A deterministic (never `secrets`-random) test-only nonce: this helper plants a *standalone*
    # attempt directly, never through a live `execute()` call, so there is no genuine concurrent
    # caller here to distinguish from -- determinism keeps this fixture's own output reproducible.
    attempt_nonce = hashlib.sha256(
        f"bare-attempt-nonce:{slot_key}:{claim_token}".encode()
    ).hexdigest()[:32]
    attempt = build_execution_attempt(
        project_id=project_id,
        change_ref={"kind": "change", "id": change_id},
        execution_boundary_fingerprint=boundary_fp,
        adapter_identity_fingerprint=adapter_fp,
        claim_token=claim_token,
        requested_at=requested_at,
        execution_intent_ref={"kind": "execution_intent", "id": slot_key},
        attempt_nonce=attempt_nonce,
    )
    commit_foreign_record(
        store, project_id, "execution_attempt", slot_key, attempt, committed_at=committed_at
    )
    return attempt


def plant_terminal_receipt(
    store: Any,
    project_id: str,
    change: dict[str, Any],
    decision: dict[str, Any],
    boundary: dict[str, Any],
    adapter_identity: dict[str, Any],
    *,
    project_binding_id: str,
    worktree_root: str,
    claim_token: str,
    outcome: str,
    performed_result_summary: dict[str, Any] | None = None,
    rollback_outcome: str | None = None,
    execution_instant: str = "2026-09-10T00:00:01Z",
    committed_at: str = "2026-09-10T00:00:01Z",
) -> dict[str, Any]:
    """Commit one real, schema-valid, fully self-consistent terminal ``change_execution_receipt``
    directly to *store*, at the exact mapping slot a composed executor for *change* under
    *boundary*/*adapter_identity* would itself resolve -- built by the real ``engine.
    build_change_execution_receipt`` (so its own recomputed identity/semantic fingerprint
    genuinely agree, the exact check ``route.py``'s own ``_verify_slot_record`` performs).

    **Why this exists, disclosed in full in ``tests/integration/change_executor/
    test_change_executor_idempotency_crash_matrix.py``'s own module docstring.** ``route.py``'s
    own staleness check (step 9) runs before its own idempotency-slot resolution (step 10), so a
    Change can only ever pass staleness at the *one* revision its own ``expected_state_revision``
    names -- once any commit happens (including this package's own execution_intent/attempt/
    receipt commits from a genuine first call), that Change is stale for every future call,
    forever. There is therefore no way to exercise the replay/semantic-reuse/terminal-mismatch
    branches of step 10 through two genuine, live ``execute()`` calls at all. This function
    reaches step 10 a different, still entirely real way: it plants a genuine terminal receipt
    directly (matching the real Change's own semantic content throughout), so a *single*
    ``execute()`` call -- which never advances the Store's own revision on the replay/mismatch/
    reuse branches (all three return or raise before any commit) -- can reach and prove step 10's
    own resolution logic in isolation, with a caller-chosen ``extra_state_revision_headroom=1``
    accounting for this very function's own one commit.
    """

    from manosube_agent_civilization.change_executor.boundary import (
        execution_boundary_fingerprint,
        validate_execution_boundary,
    )
    from manosube_agent_civilization.change_executor.engine import build_change_execution_receipt
    from manosube_agent_civilization.change_executor.identity import execution_mapping_slot_key

    canonical_boundary = validate_execution_boundary(boundary)
    boundary_fp = execution_boundary_fingerprint(canonical_boundary)
    adapter_fp = adapter_identity_fingerprint(adapter_identity)
    slot_key = execution_mapping_slot_key(change["change_id"], boundary_fp, adapter_fp)

    summary = (
        dict(performed_result_summary)
        if performed_result_summary is not None
        else {"files_written": [], "bytes_written": 0, "files_deleted": []}
    )
    summary_fingerprint = "sha256:" + hashlib.sha256(canonical_json_bytes(summary)).hexdigest()
    reobservation_request = {
        "kind": "change_execution_reobservation_request",
        "target": {
            "repository": canonical_boundary["repository"],
            "branch": canonical_boundary["branch"],
            "paths": sorted(change["scope"]["paths"]),
        },
        "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
        "requested_at": execution_instant,
    }
    receipt = build_change_execution_receipt(
        execution_request_id=slot_key,
        change_ref={"kind": "change", "id": change["change_id"]},
        idempotency_key=change["idempotency_key"],
        authority_ref={"kind": "authority_decision", "id": decision["authority_decision_id"]},
        project_id=project_id,
        project_binding_ref={"kind": "project_binding", "id": project_binding_id},
        boot_state_fingerprint=dict(change["before_state_fingerprint"]),
        execution_boundary_fingerprint=boundary_fp,
        executor_identity=canonical_boundary["executor_identity"],
        executor_version=canonical_boundary["executor_version"],
        target={
            "repository": canonical_boundary["repository"],
            "branch": canonical_boundary["branch"],
            "worktree_root": worktree_root,
        },
        operation=change["action"]["operation"],
        execution_started_at=execution_instant,
        execution_ended_at=execution_instant,
        outcome=outcome,
        performed_result_fingerprint=summary_fingerprint,
        performed_result_summary=summary,
        rollback_outcome=rollback_outcome,
        claim_token=claim_token,
        reobservation_request=reobservation_request,
    )
    commit_foreign_record(
        store, project_id, "execution_receipt", slot_key, receipt, committed_at=committed_at
    )
    return receipt


def tamper_committed_record(
    store: Any,
    project_id: str,
    kind: str,
    record_id: str,
    mutate: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Tamper a genuinely already-committed record on disk, bypassing the normal commit path
    entirely (never a second, different-content commit through the Store's own API, which its
    own content-addressed ``RecordConflictError`` refuses outright -- see ``FileStateStore.
    _stage_records``).

    ``FileStateStore.resolve_record`` cross-checks the permanent record file against *every*
    manifest claimant's own staged journal copy still on disk, and raises
    :class:`~manosube_agent_civilization.store.errors.CorruptStoreError` the moment any two of
    them disagree (``SAME_ID_DIFFERENT_BODY_MUST_FAIL_CLOSED``) -- a lower, storage-layer
    integrity gate this package's own ``ExecutionReceiptIntegrityError`` never gets a chance to
    run against if only the permanent file is edited. This helper edits *every* on-disk copy of
    the record identically (the permanent file, and every still-present staged copy under
    ``state/recovery/*/records/``), so the Store's own storage-layer view stays internally
    self-consistent and ``resolve_record`` returns the tampered content cleanly -- exactly the
    scenario ``change_executor.route``'s own recomputed-identity/fingerprint check exists to
    catch, once the record actually reaches it.
    """

    permanent_path = store._record_path(project_id, kind, record_id)
    original = json.loads(permanent_path.read_text(encoding="utf-8"))
    tampered = mutate(deepcopy(original))
    tampered_bytes = canonical_json_bytes(tampered)

    permanent_path.write_bytes(tampered_bytes)

    recovery_root = store._project(project_id) / "state" / "recovery"
    if recovery_root.exists():
        for journal in recovery_root.iterdir():
            staged = journal / "records" / f"{kind}__{record_id}.json"
            if staged.exists():
                staged.write_bytes(tampered_bytes)
    return tampered


# --------------------------------------------------------------------------------------- #
# Kill switch.
# --------------------------------------------------------------------------------------- #


def _build_kill_switch(
    project_id: str, *, status: str, generation: int, predecessor_ref: dict[str, str] | None
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "change_executor_kill_switch_id": "",
        "project_id": project_id,
        "status": status,
        "generation": generation,
        "predecessor_ref": predecessor_ref,
        "signature": {"algorithm": "ed25519", "key_id": "PLACEHOLDER", "value": "0" * 128},
        "change_executor_kill_switch_semantic_fingerprint": "",
    }
    record["change_executor_kill_switch_id"] = kill_switch_id(record)
    record["change_executor_kill_switch_semantic_fingerprint"] = kill_switch_semantic_fingerprint(
        record
    )
    payload = kill_switch_signing_payload(record)
    record["signature"] = mint_kill_switch_signature(payload)
    return record


def commit_active_kill_switch(
    store: Any, project_id: str, *, committed_at: str = "2026-09-10T00:00:00Z"
) -> dict[str, Any]:
    """Mint (via the genuinely separate test issuer) and commit (via the real, verify-only
    ``commit_change_executor_kill_switch``) one genesis ``ACTIVE`` kill switch."""

    record = _build_kill_switch(project_id, status="ACTIVE", generation=0, predecessor_ref=None)
    commit_change_executor_kill_switch(
        store,
        project_id,
        record,
        trust_anchor_public_key_hex=issuer_public_key_hex(),
        committed_at=committed_at,
    )
    return record


def commit_revoked_successor(
    store: Any,
    project_id: str,
    current: dict[str, Any],
    *,
    committed_at: str = "2026-09-10T00:00:30Z",
) -> dict[str, Any]:
    """Mint and commit a real ``REVOKED`` successor to *current* -- terminal, by the real
    monotonic chain rules ``commit_change_executor_kill_switch`` itself enforces."""

    record = _build_kill_switch(
        project_id,
        status="REVOKED",
        generation=current["generation"] + 1,
        predecessor_ref={
            "kind": KILL_SWITCH_RECORD_KIND,
            "id": current["change_executor_kill_switch_id"],
        },
    )
    commit_change_executor_kill_switch(
        store,
        project_id,
        record,
        trust_anchor_public_key_hex=issuer_public_key_hex(),
        committed_at=committed_at,
    )
    return record


# --------------------------------------------------------------------------------------- #
# Execution Boundary / operation / adapter identity.
# --------------------------------------------------------------------------------------- #


def execution_boundary_for(**overrides: Any) -> dict[str, Any]:
    """One real, schema-valid, closed Execution Boundary -- mirrors
    ``tests/fixtures/url_boot_world.py``'s own ``boundary_for`` shape. *overrides* replaces any
    single top-level key (including ``validity_window`` wholesale)."""

    boundary: dict[str, Any] = {
        "permitted_action_kinds": ["WRITE_DOCUMENTATION_FILE", "DELETE_DOCUMENTATION_FILE"],
        "repository": REPOSITORY,
        "branch": BRANCH,
        "admitted_paths": ["docs"],
        "max_files_changed": 5,
        "max_bytes_changed": 100_000,
        "max_file_bytes": 50_000,
        "permit_symlinks": False,
        "permit_path_traversal": False,
        "permit_network": False,
        "permit_subprocess": False,
        "permit_environment_mutation": False,
        "permit_credential_access": False,
        "timeout_seconds": 30,
        "rollback_policy": "NONE",
        "executor_identity": "controlled_filesystem_adapter",
        "executor_version": "0.1",
        "validity_window": dict(DEFAULT_TIME_WINDOW),
    }
    boundary.update(overrides)
    return boundary


def operation_for(
    action_kind: str,
    *,
    writes: list[dict[str, str]] | None = None,
    deletes: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """A deterministic, UTF-8, closed :class:`~manosube_agent_civilization.change_executor.
    types.ExecutionOperation`-shaped operation -- this is the opaque payload embedded verbatim
    as ``action.operation`` on a Change built by :func:`build_committed_change`."""

    return {
        "operation_kind": action_kind,
        "file_writes": [dict(entry) for entry in (writes or [])],
        "file_deletes": [dict(entry) for entry in (deletes or [])],
    }


def adapter_identity_for(**overrides: Any) -> dict[str, Any]:
    identity: dict[str, Any] = {"kind": "controlled_filesystem_adapter", "version": "0.1"}
    identity.update(overrides)
    return identity


class CountingAdapter:
    """A real, functioning adapter (wraps a genuine ``ControlledFilesystemAdapter`` by default)
    that additionally counts every ``execute`` call -- the one decisive-control instrument every
    zero-call refusal proof in this suite shares: ``assert spy.call_count == 0`` after a refusal,
    ``== 1`` after exactly one genuine primary call, etc. Never a mock: every call it does let
    through is a real, mechanical filesystem operation."""

    def __init__(self, *, inner: Any | None = None) -> None:
        self.inner = (
            inner
            if inner is not None
            else ControlledFilesystemAdapter(
                executor_identity="controlled_filesystem_adapter", executor_version="0.1"
            )
        )
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        self.call_count += 1
        self.calls.append({"operation": operation, "worktree_root": worktree_root})
        result: dict[str, Any] = self.inner.execute(operation, worktree_root=worktree_root)
        return result


def adapter_identity_fingerprint(adapter_identity: dict[str, Any]) -> str:
    """The identical content fingerprint ``route.py`` itself computes over a canonicalized
    adapter identity -- exposed here so a test can independently predict a slot key without
    reaching into ``route.py``'s own private module internals."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(dict(adapter_identity))).hexdigest()


__all__ = [
    "BRANCH",
    "DEFAULT_TIME_WINDOW",
    "REPOSITORY",
    "CountingAdapter",
    "adapter_identity_fingerprint",
    "adapter_identity_for",
    "bound",
    "bound_with_project_id",
    "build_committed_change",
    "commit_active_kill_switch",
    "commit_bare_execution_attempt",
    "commit_bare_execution_intent",
    "commit_foreign_record",
    "commit_revoked_successor",
    "execution_boundary_for",
    "operation_for",
    "plant_terminal_receipt",
    "slot_key_for",
    "tamper_committed_record",
]
