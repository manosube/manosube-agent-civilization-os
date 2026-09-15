"""Phase 20 Long-Running Project Proof -- the bounded, deterministic, cycle-indexed fixture
world (``00_KERNEL/LONG_RUNNING_PROOF_CONTRACT.md``, Issue #86).

This module is the Fixture Boundary for a *sequence* of natural-cycle Differences, generalizing
Phase 8's one-shot ``tests/fixtures/vertical_proof.py`` to a deterministic corpus of up to
``MAX_CYCLES`` distinct, ordered cycles against one long-running Project. Exactly as Phase 8's
own fixture module explains for itself, this module supplies only bounded *source-world
inputs* -- an Objective (with one Target Predicate per cycle, declared up front), a before/after
observation source fact per cycle, a fixed Authority rule, a fixed Change action/scope, and a
Closure Policy -- never a completed Observation, Difference, Authority Decision, Change,
Evidence, Evidence Sufficiency Result, Closure Evaluation, lifecycle event, or State transition.
Those are produced every time by :mod:`tests.long_running_proof.cycle`, itself calling only the
real, public canonical owners (``NO_MANUAL_INTERMEDIATE_CANONICAL_RECORD_CONSTRUCTION=true``).

This module is deliberately self-contained and does not import from ``tests/fixtures/
vertical_proof.py`` -- ``PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true`` -- even
though several shapes below deliberately match its field-for-field pattern (the real, frozen
request schemas), for the same reason Phase 8 gives: matching the schema is fidelity, not
duplication of test-support code; keeping the fixture worlds independent means a defect in one
phase's fixture can never mask or amplify a defect in another's.

**One Project, one Objective Revision, ``MAX_CYCLES`` Target Predicates, declared once.**
``difference.engine.derive_differences`` requires every bound Target Predicate to already be
declared by the Objective Revision (``"Target Predicate is not declared by the Objective"``),
so this Objective Revision is built with all ``MAX_CYCLES`` predicates present from the start --
a genuinely long-running Project that already knows the shape of the work ahead, not one that
silently redefines its own Objective mid-run to admit each new cycle.

**Two physical Source Snapshot files, reused across every cycle.** Exactly as Phase 8's own
``before_source_world.txt``/``after_source_world.txt`` are real, checked-in bytes this
repository ships (P8-R1 Source Snapshot fixture truthfulness), this proof reuses one dedicated
before/after file pair across all cycles: a Source Snapshot names *where* real content was
observed, not *what specific claim* was read from it -- the same two files can truthfully back
``MAX_CYCLES`` distinct Observations of ``MAX_CYCLES`` distinct subjects/predicates without a
single per-cycle physical file, exactly as one real source file in a real long-running Project
can back many distinct facts read from it over time.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path
from typing import Any

from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot

ROOT = Path(__file__).resolve().parents[2]

PROJECT_ID = "PRJ-P20-0001"
PROJECT_BINDING_ID = "PB-P20-0001"
OBJECTIVE_ID = "OBJ-P20-0001"
OBJECTIVE_REVISION_ID = "OBJ-REV-P20-0001"
SCOPE_ID = "OBS-SCOPE-P20-0001"
REPOSITORY = "manosube/example-long-running-proof-fixture"
BRANCH = "main"

#: The maximum corpus length this fixture world declares Target Predicates for. T10/T30/T50 are
#: literal prefixes of this same ordered corpus -- ``predicate_id(k)``/``subject(k)`` for
#: ``k in range(tier)`` names exactly the first ``tier`` entries of the identical sequence
#: ``k in range(MAX_CYCLES)`` names, so no tier is ever a differently-shuffled or independently
#: fabricated corpus.
MAX_CYCLES = 100

HUMAN_AUTHORITY: dict[str, Any] = {"kind": "human_authority", "id": "AUTH-P20-0001"}

OBJECTIVE_RECORDED_AT = "2026-09-15T12:00:00Z"
AUTHORITY_EVALUATION_TIME = "2026-09-15T12:10:00Z"
EVIDENCE_RECORDED_AT = "2026-09-15T12:30:00Z"
SUFFICIENCY_EVALUATED_AT = "2026-09-15T12:35:00Z"
REFLOW_INSTANT = "2026-09-15T12:40:00Z"

METHOD_REF: dict[str, Any] = {"kind": "observation_method", "id": "OBS-METHOD-P20-0001"}
OBSERVATION_METHOD: dict[str, Any] = {
    "method_profile": "MANOSUBE-OBSERVATION-METHOD-SHA256-0.1",
    "procedure_kind": "CANONICAL_OBSERVER",
    "procedure_ref": {
        "kind": "observer_procedure",
        "id": "OBS-PROCEDURE-P20-0001",
        "version": "0.1",
        "semantic_fingerprint": "sha256:" + "f" * 64,
    },
    "normalization_profile": "FIXTURE-0.1",
    "input_contract_ref": {"kind": "schema", "id": "OBS-INPUT-01"},
    "output_contract_refs": {
        "collection_kind": "UNORDERED_SET",
        "members": [{"kind": "schema", "id": "NORMALIZED-FACT-01"}],
    },
    "execution_boundary_ref": {"kind": "execution_boundary", "id": "KERNEL-LOCAL"},
}

BEFORE_SOURCE_WORLD_LOCATOR = "tests/fixtures/long_running_proof/before_source_world.txt"
AFTER_SOURCE_WORLD_LOCATOR = "tests/fixtures/long_running_proof/after_source_world.txt"
_BEFORE_SOURCE_WORLD_BYTES = (ROOT / BEFORE_SOURCE_WORLD_LOCATOR).read_bytes()
_AFTER_SOURCE_WORLD_BYTES = (ROOT / AFTER_SOURCE_WORLD_LOCATOR).read_bytes()

BEFORE_SOURCE_SNAPSHOT: dict[str, Any] = build_source_snapshot(
    source_locator=BEFORE_SOURCE_WORLD_LOCATOR,
    content_digest="sha256:" + hashlib.sha256(_BEFORE_SOURCE_WORLD_BYTES).hexdigest(),
    captured_at="2026-09-15T11:59:00Z",
)
BEFORE_SNAPSHOT_REF: dict[str, str] = {
    "kind": "source_snapshot",
    "id": BEFORE_SOURCE_SNAPSHOT["source_snapshot_id"],
}

AFTER_SOURCE_SNAPSHOT: dict[str, Any] = build_source_snapshot(
    source_locator=AFTER_SOURCE_WORLD_LOCATOR,
    content_digest="sha256:" + hashlib.sha256(_AFTER_SOURCE_WORLD_BYTES).hexdigest(),
    captured_at="2026-09-15T12:19:00Z",
)
AFTER_SNAPSHOT_REF: dict[str, str] = {
    "kind": "source_snapshot",
    "id": AFTER_SOURCE_SNAPSHOT["source_snapshot_id"],
}

ARTIFACT: dict[str, Any] = {
    "kind": "artifact",
    "id": "ARTIFACT-P20-0001",
    "content_sha256": "1" * 64,
    "byte_length": 64,
    "media_type": "application/json",
}

NEGATIVE_EVIDENCE_REF: dict[str, str] = {"kind": "negative_evidence", "id": "NEG-EVID-P20-0001"}

VERIFICATION_RESULT_PROVENANCE: dict[str, Any] = {
    "status": "VERIFIED",
    "requirement_id": "VREQ-P20-0001",
    "selection_id": "VSEL-P20-0001",
    "project_id": PROJECT_ID,
    "target_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    "verifier_identity": {"kind": "deterministic_test_runner", "id": "VERIFIER-P20-0001"},
    "selection_authority_ref": {"kind": "human_authority", "id": "AUTH-P20-0001"},
    "verification_boundary": {"scope": "repository", "boundary_id": "VB-P20-0001"},
    "input_refs": {"collection_kind": "UNORDERED_SET", "members": []},
    "observations": {"summary": "long-running-proof fixture provenance"},
}


def predicate_id(k: int) -> str:
    return f"TP-P20-{k:04d}"


def subject(k: int) -> str:
    return f"long_running_proof.marker_{k:04d}"


def claim_key(k: int) -> str:
    return f"marker_{k:04d}"


def evidence_ref(k: int, *, role: str) -> dict[str, str]:
    """A per-cycle, per-role schema-valid placeholder evidence ref -- distinct across cycles
    and roles so two different cycles' provisional Evidence-derivation seeds can never collide
    with each other (the identical structural reason Phase 8's own single ``EVIDENCE_REF``
    placeholder is safe for a *one*-cycle proof but would not be for a many-cycle corpus).

    Observation/Evidence identifiers must match ``^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$`` -- uppercase
    hyphen-segments only -- so *role* is upper-cased here."""

    return {"kind": "observation_evidence", "id": f"EVID-P20-{k:04d}-{role.upper()}"}


def target_predicate(k: int) -> dict[str, Any]:
    return {
        "predicate_id": predicate_id(k),
        "subject": subject(k),
        "operator": "equals",
        "expected_value": "READY",
        "observation_scope": "long_running_proof",
        "evidence_requirement": "E1",
        "unknown_policy": "INCOMPLETE",
        "criticality": "mandatory",
    }


def objective_revision() -> dict[str, Any]:
    """The one Objective Revision this entire corpus is derived against -- every cycle's own
    Target Predicate declared up front (see module docstring)."""

    return {
        "schema_version": "0.1",
        "objective_id": OBJECTIVE_ID,
        "objective_revision_id": OBJECTIVE_REVISION_ID,
        "project_id": PROJECT_ID,
        "statement": (
            "The long-running proof's markers, cycle 0000 through "
            f"{MAX_CYCLES - 1:04d}, each reach READY in sequence."
        ),
        "owner_authority_ref": dict(HUMAN_AUTHORITY),
        "target_predicates": [target_predicate(k) for k in range(MAX_CYCLES)],
        "completion_policy": {"mode": "ALL", "contradiction_policy": "BLOCK"},
        "boundary_ref": {"kind": "objective_boundary", "id": "BOUND-P20-0001"},
        "constitutional_constraints": [],
        "status": "ACTIVE",
        "revision": 0,
        "previous_objective_ref": None,
        "change_reason": "initial long-running-proof objective",
        "base_semantic_fingerprint": None,
        "semantic_change_summary": "initial long-running-proof objective revision",
        "human_authority_ref": dict(HUMAN_AUTHORITY),
        "recorded_at": OBJECTIVE_RECORDED_AT,
    }


def observation_scope(k: int, *, snapshot_ref: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "scope_id": f"{SCOPE_ID}-{k:04d}",
        "project_id": PROJECT_ID,
        "target_identity": predicate_id(k),
        "included_subjects": [subject(k)],
        "excluded_subjects": ["long_running_proof.secret"],
        "boundary_root": "/long_running_proof",
        "path_policy": {
            "relative_locators_only": True,
            "symlink_escape": "BLOCK",
            "submodule_traversal": "DECLARED_ONLY",
            "mount_escape": "BLOCK",
            "credential_paths": "EXCLUDE",
        },
        "observation_window": {"start": "2026-09-15T12:00:00Z", "end": "2026-12-31T00:00:00Z"},
        "target_effective_window": {
            "start": "2026-09-15T11:00:00Z",
            "end": "2026-12-31T00:00:00Z",
        },
        "freshness_limit_seconds": 31536000,
        "cutoff": "2026-12-31T00:00:00Z",
        "source_snapshot_refs": [dict(snapshot_ref)],
        "enumeration_rule": {"kind": "enumeration_rule", "id": f"ENUM-P20-{k:04d}"},
        "completion_predicate": {"kind": "completion_predicate", "id": f"COMPLETE-P20-{k:04d}"},
        "method_ref": dict(METHOD_REF),
        "attempt_policy": {"max_attempts": 1, "timeout_seconds": 60, "retry_on": []},
        "blind_spots": [],
        "scope_status": "COMPLETE",
    }


def raw_fact(k: int, *, value: str, snapshot_id: str) -> dict[str, Any]:
    return {
        "subject": subject(k),
        "predicate": "equals@v1",
        "value": value,
        "value_type": "STRING",
        "unit": None,
        "effective_boundary": {
            "kind": "SOURCE_SNAPSHOT",
            "identity": snapshot_id,
            "start": None,
            "end": None,
        },
    }


def observation_request(
    k: int,
    *,
    value: str,
    snapshot_ref: dict[str, str],
    snapshot_locator: str,
    snapshot_time: str,
    fingerprint: dict[str, Any],
    state_revision: int,
    started_at: str,
    ended_at: str,
    attempt_id: str,
    ref: dict[str, str],
) -> dict[str, Any]:
    scope = observation_scope(k, snapshot_ref=snapshot_ref)
    return {
        "project_id": PROJECT_ID,
        "state_revision_observed": state_revision,
        "state_fingerprint_observed": deepcopy(fingerprint),
        "target_identity": predicate_id(k),
        "target_kind": "FIXTURE",
        "scope": scope,
        "method_ref": dict(METHOD_REF),
        "time_boundary": {
            "observation_started_at": started_at,
            "observation_ended_at": ended_at,
            "target_effective_start": "2026-09-15T11:00:00Z",
            "target_effective_end": "2026-12-31T00:00:00Z",
            "source_snapshot_time": snapshot_time,
        },
        "source_snapshot_refs": [dict(snapshot_ref)],
        "normalization_profile": "FIXTURE-0.1",
        "source_occurrences": [
            {
                "source_ref": dict(snapshot_ref),
                "source_locator": snapshot_locator,
                "facts": [raw_fact(k, value=value, snapshot_id=snapshot_ref["id"])],
            }
        ],
        "attempts": [
            {
                "attempt_id": attempt_id,
                "method_ref": dict(METHOD_REF),
                "started_at": started_at,
                "ended_at": ended_at,
                "result": "COMPLETE",
                "failure_class": None,
            }
        ],
        "blind_spots": [],
        "observation_evidence_refs": [dict(ref)],
        "negative_evidence_refs": [dict(NEGATIVE_EVIDENCE_REF)],
        "negative_claims": [],
        "collection_complete": True,
    }


def before_observation_request(
    k: int,
    *,
    fingerprint: dict[str, Any],
    state_revision: int,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="NOT-READY",
        snapshot_ref=BEFORE_SNAPSHOT_REF,
        snapshot_locator=BEFORE_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time="2026-09-15T11:59:00Z",
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at="2026-09-15T12:05:00Z",
        ended_at="2026-09-15T12:05:30Z",
        attempt_id=f"ATTEMPT-P20-{k:04d}-BEFORE",
        ref=ref if ref is not None else evidence_ref(k, role="before-seed"),
    )


def change_result_observation_request(
    k: int,
    *,
    fingerprint: dict[str, Any],
    state_revision: int,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="READY",
        snapshot_ref=AFTER_SNAPSHOT_REF,
        snapshot_locator=AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time="2026-09-15T12:19:00Z",
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at="2026-09-15T12:20:00Z",
        ended_at="2026-09-15T12:20:30Z",
        attempt_id=f"ATTEMPT-P20-{k:04d}-CHANGE-RESULT",
        ref=ref if ref is not None else evidence_ref(k, role="change-result-seed"),
    )


def verification_observation_request(
    k: int,
    *,
    fingerprint: dict[str, Any],
    state_revision: int,
    ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    return observation_request(
        k,
        value="READY",
        snapshot_ref=AFTER_SNAPSHOT_REF,
        snapshot_locator=AFTER_SOURCE_SNAPSHOT["source_locator"],
        snapshot_time="2026-09-15T12:19:00Z",
        fingerprint=fingerprint,
        state_revision=state_revision,
        started_at="2026-09-15T12:25:00Z",
        ended_at="2026-09-15T12:25:30Z",
        attempt_id=f"ATTEMPT-P20-{k:04d}-VERIFICATION",
        ref=ref if ref is not None else evidence_ref(k, role="verification-seed"),
    )


def derivation_request(
    k: int,
    *,
    observation_bundle: dict[str, Any] | None,
    fingerprint: dict[str, Any],
    state_revision: int,
    snapshot_ref: dict[str, str] = BEFORE_SNAPSHOT_REF,
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "identity_profile": "MANOSUBE-DIFFERENCE-SHA256-0.1",
        "comparison_profile": "MANOSUBE-DIFFERENCE-COMPARISON-0.1",
        "normalization_profile": "MANOSUBE-DIFFERENCE-NORMALIZATION-0.1",
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "state_revision": state_revision,
        "state_fingerprint": deepcopy(fingerprint),
        "closure_policy_requirements": {"minimum_evidence_level": "E1"},
        "observation_method": deepcopy(OBSERVATION_METHOD),
        "bindings": [
            {
                "target_predicate_id": predicate_id(k),
                "observation_scope": observation_scope(k, snapshot_ref=snapshot_ref),
                "observation_bundle": observation_bundle,
            }
        ],
    }


def action_scope() -> dict[str, Any]:
    return {
        "repository": REPOSITORY,
        "branch": BRANCH,
        "paths": ["src/long_running_proof_target.py"],
        "subjects": [],
    }


def authority_rule(*, project_id: str) -> dict[str, Any]:
    """A single, real Authority Rule, declared once, authorizing every cycle's identical
    action_kind/scope -- exactly one long-running Project's one standing grant to keep making
    the same bounded, reversible class of write across its whole run, not a fresh rule minted
    per cycle."""

    from manosube_agent_civilization.authority.identity import rule_id

    record = {
        "schema_version": "0.1",
        "authority_rule_id": "",
        "project_id": project_id,
        "action_kinds": ["WRITE_FILE"],
        "maximum_reversibility": "REVERSIBLE",
        "scope": action_scope(),
        "decision": "AUTONOMOUS",
        "declared_by": dict(HUMAN_AUTHORITY),
    }
    record["authority_rule_id"] = rule_id(record)
    return record


def bind_project_kwargs(genesis_state: dict[str, Any]) -> dict[str, Any]:
    """Every keyword :func:`~manosube_agent_civilization.binding.route.bind_project` needs
    for one real, atomic genesis+Binding admission of :data:`PROJECT_ID` (P87-R1-F4/F7's own
    required correction: the long-running cycle sequence, Agent swap, and runtime observation
    slices must all share one real Project Binding, not three unrelated fixture worlds).
    Reuses ``tests/fixtures/product_binding.py``'s own generic, non-project-scoped fixtures
    (``boundary``/``source_registrations``/``command_policy``/``secret_exclusion_policy``/
    ``human_authority_signing_key``) verbatim -- only ``project_id``, ``objective_revision``,
    ``authority_rule``, ``authority_policy_ref``, ``human_authority_ref``, and *genesis_state*
    itself are this fixture world's own. ``human_authority_ref`` is :data:`HUMAN_AUTHORITY`
    (not ``product_binding``'s own ``AUTH-BIND-0001``), matching the ``owner_authority_ref``/
    ``human_authority_ref``/``declared_by`` every one of :func:`objective_revision` and
    :func:`authority_rule` already carry -- ``bind_project``'s own four-way Human Authority
    canonical-reference exact match requires all four to agree."""

    from tests.fixtures import product_binding as pb

    rule = authority_rule(project_id=PROJECT_ID)
    return {
        "project_id": PROJECT_ID,
        "objective_revision": objective_revision(),
        "boundary": pb.boundary(),
        "authority_policy_ref": {"kind": "authority_rule", "id": rule["authority_rule_id"]},
        "authority_rule": rule,
        "source_registrations": pb.source_registrations(),
        "command_policy": pb.command_policy(),
        "secret_exclusion_policy": pb.secret_exclusion_policy(),
        "human_authority_ref": dict(HUMAN_AUTHORITY),
        "human_authority_signing_key": pb.human_authority_signing_key(),
        "bound_at": OBJECTIVE_RECORDED_AT,
        "genesis_state": genesis_state,
    }


def requested_action(k: int) -> dict[str, Any]:
    from manosube_agent_civilization.authority.identity import action_fingerprint

    record = {
        "action_kind": "WRITE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": {"body": f"mark long-running-proof marker {k:04d} READY"},
        "action_semantic_fingerprint": "",
    }
    record["action_semantic_fingerprint"] = action_fingerprint(record)
    return record


def closure_policy(difference_id: str, *, predicate: str) -> dict[str, Any]:
    from manosube_agent_civilization.difference.identity import (
        closure_policy_id,
        policy_semantic_fingerprint,
    )

    policy: dict[str, Any] = {
        "schema_version": "0.1",
        "closure_policy_id": "",
        "policy_version": "0.1",
        "policy_semantic_fingerprint": "",
        "subject_difference_ref": {"kind": "difference", "id": difference_id},
        "target_predicate_ref": {"kind": "target_predicate", "id": predicate},
        "required_observation_scope": None,
        "minimum_evidence_level": "E1",
        "required_claims": [],
        "required_invariants": [],
        "allowed_terminal_states": ["CLOSED", "BLOCKED", "RETAINED"],
        "independent_verification_required": False,
        "maximum_evidence_age": None,
        "contradiction_policy": "FAIL_CLOSED",
        "reopen_conditions": [],
    }
    policy["policy_semantic_fingerprint"] = policy_semantic_fingerprint(policy)
    policy["closure_policy_id"] = closure_policy_id(
        policy["policy_semantic_fingerprint"], difference_id
    )
    return policy
