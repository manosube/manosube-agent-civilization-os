"""Phase 21 Comparative Benchmark -- the 13 required decisive negative controls (Issue #89
section 8, ``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``), numbered NC-1..NC-13 exactly as the
adoption issue itself lists them. Each test is a real attacker-world substitution/tamper attempt
against real, already-built ``manosube_agent_civilization.comparative_benchmark`` machinery --
never a vacuous assertion."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
from typing import Any

import pytest
from tests.comparative_benchmark.orchestrator import CorpusFidelityError, verify_corpus_fidelity
from tests.fixtures import comparative_benchmark as cb

from manosube_agent_civilization.comparative_benchmark import route as cb_route
import manosube_agent_civilization.comparative_benchmark.engine as cb_engine_module
from manosube_agent_civilization.comparative_benchmark.engine import (
    aggregate_metrics,
    build_protocol_freeze,
    build_reproduction_receipt,
    build_result_bundle,
    derive_bounded_claims,
)
from manosube_agent_civilization.comparative_benchmark.errors import (
    ProtocolFreezeValidationError,
    ReproductionReceiptValidationError,
    ResultBundleValidationError,
)
import manosube_agent_civilization.comparative_benchmark.route as cb_route_module
from manosube_agent_civilization.store.errors import RecordConflictError

_GENERATED_AT = "2026-01-01T00:00:00.000001Z"
_ENVIRONMENT_MANIFEST = {
    "python_implementation": "CPython",
    "python_version": "3.12.0",
    "platform": "test-platform",
}


def _reproducer_identity(
    *, reproduction_process_id: int, is_original_author: bool = False, reproducer: str = "nc-test"
) -> dict[str, Any]:
    """A real, schema-shaped ``reproducer_identity`` for a fast, in-process negative-control
    test (P90-R1-F3): *reproduction_process_id* is supplied explicitly by the caller rather than
    read from ``os.getpid()`` here, since a same-process negative control must be able to pass
    the identical pid this test process is itself running under, and a positive control must be
    able to pass a genuinely different one."""

    return {
        "reproducer": reproducer,
        "is_original_author": is_original_author,
        "reproduction_process_id": reproduction_process_id,
        "reproduction_environment_manifest": dict(_ENVIRONMENT_MANIFEST),
    }


def _built_protocol_freeze() -> dict[str, Any]:
    """A real, schema-valid protocol freeze -- a pure computation, no Store I/O -- built fresh
    for each fast negative-control test below."""

    return build_protocol_freeze(
        project_id=cb.PROJECT_ID, **cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)
    )


def _raw_event(*, group_id: str, task_id: str, outcome: str) -> dict[str, Any]:
    return {
        "kind": "task_attempt",
        "comparison_group_id": group_id,
        "task_id": task_id,
        "outcome": outcome,
    }


def _full_raw_events(protocol_freeze: dict[str, Any]) -> list[dict[str, Any]]:
    """A minimal, schema-valid, fully-corpus-complete raw-event set for every declared group --
    every group attempts every task, in the declared order, so :func:`verify_corpus_fidelity`
    accepts it as a baseline a test can then tamper with."""

    events: list[dict[str, Any]] = []
    for group in protocol_freeze["comparison_groups"]:
        for task_id in protocol_freeze["corpus_manifest"]["task_ids"]:
            events.append(
                _raw_event(group_id=group["comparison_group_id"], task_id=task_id, outcome="FAILED")
            )
    return events


# --- NC-1: different Agent/runtime/configuration cannot be mislabeled as same-agent comparison  #


def test_nc1_present_and_absent_groups_sharing_a_mechanism_identity_is_refused() -> None:
    kwargs = cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)
    groups = [dict(g) for g in kwargs["comparison_groups"]]
    for group in groups:
        if group["comparison_group_role"] == "MANOSUBE_ABSENT":
            group["mechanism_identity"] = dict(cb.PRESENT_MECHANISM_IDENTITY)
    kwargs["comparison_groups"] = groups

    with pytest.raises(ProtocolFreezeValidationError, match="never share a mechanism_identity"):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)


# --- NC-2: task/corpus substitution, omission, reordering, duplicate sampling fail closed ----- #


def test_nc2_corpus_reordering_omission_and_duplication_all_fail_closed() -> None:
    protocol_freeze = _built_protocol_freeze()
    good = _full_raw_events(protocol_freeze)
    present_id = cb.PRESENT_GROUP_ID
    task_ids = list(protocol_freeze["corpus_manifest"]["task_ids"])

    def present_events(ids: list[str]) -> list[dict[str, Any]]:
        others = [e for e in good if e["comparison_group_id"] != present_id]
        mine = [_raw_event(group_id=present_id, task_id=t, outcome="FAILED") for t in ids]
        return others + mine

    verify_corpus_fidelity(protocol_freeze, good)  # baseline is accepted

    reordered = present_events(list(reversed(task_ids)))
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, reordered)

    omitted = present_events(task_ids[:-1])
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, omitted)

    duplicated = present_events([*task_ids[:-1], task_ids[0]])
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, duplicated)

    substituted = present_events([*task_ids[:-1], "TSK-NOT-IN-CORPUS-0000"])
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, substituted)


# --- NC-3: Authority/tool-surface asymmetry is detected, not treated as a MANOSUBE effect ----- #


def test_nc3_authority_and_tool_surface_asymmetry_is_disclosed_never_asserted_equivalent() -> None:
    protocol_freeze = _built_protocol_freeze()
    receipts = protocol_freeze["comparability_loss_receipts"]
    assert receipts, "expected at least one comparability-loss receipt"
    joined = " ".join(r["description"] for r in receipts)
    assert "Authority" in joined
    assert "tool-surface" in joined or "tool surface" in joined

    equivalence_statement = protocol_freeze["authority_boundary_equivalence_manifest"][
        "equivalence_statement"
    ]
    assert "not asserted equivalent" in equivalence_statement


# --- NC-4: resource/time/budget asymmetry is detected ------------------------------------------ #


def test_nc4_a_per_group_resource_budget_override_cannot_even_be_declared() -> None:
    kwargs = cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)
    groups = [dict(g) for g in kwargs["comparison_groups"]]
    groups[0] = dict(groups[0])
    groups[0]["resource_budget_manifest"] = {
        "per_task_timeout_seconds": "999",
        "total_time_budget_seconds": "999",
    }
    kwargs["comparison_groups"] = groups

    with pytest.raises(ProtocolFreezeValidationError):
        build_protocol_freeze(project_id=cb.PROJECT_ID, **kwargs)


# --- NC-5: successful runs cannot exclude failures, refusals, retained, incomplete outcomes --- #


def test_nc5_a_success_only_subset_of_raw_events_is_refused() -> None:
    protocol_freeze = _built_protocol_freeze()
    good = _full_raw_events(protocol_freeze)
    present_id = cb.PRESENT_GROUP_ID
    task_ids = list(protocol_freeze["corpus_manifest"]["task_ids"])

    # A "success-only" attempt: drop the failing task's own event for the PRESENT group,
    # keeping the rest -- exactly the omission NC-2's own guard refuses, exercised here from
    # its own dedicated success-only-exclusion angle.
    others = [e for e in good if e["comparison_group_id"] != present_id]
    success_only = others + [
        _raw_event(group_id=present_id, task_id=t, outcome="COMPLETED_VERIFIED")
        for t in task_ids[:-1]
    ]
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, success_only)


# --- NC-6: raw-result deletion/edit invalidates derived metrics and claims -------------------- #


def test_nc6_a_tampered_or_deleted_raw_event_invalidates_recomputed_metrics(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    result_bundle = comparative_benchmark_run["result_bundle"]
    raw_events = [dict(e) for e in result_bundle["raw_events"]]

    # Edit: flip one FAILED event to COMPLETED_VERIFIED.
    edited = list(raw_events)
    for i, event in enumerate(edited):
        if event["outcome"] == "FAILED":
            edited[i] = {**event, "outcome": "COMPLETED_VERIFIED"}
            break
    else:
        raise AssertionError("expected at least one FAILED raw event to tamper with")
    recomputed_edited = aggregate_metrics(edited, protocol_freeze)
    assert recomputed_edited != result_bundle["metrics"]

    # Delete: drop one raw event outright.
    deleted = raw_events[:-1]
    recomputed_deleted = aggregate_metrics(deleted, protocol_freeze)
    assert recomputed_deleted != result_bundle["metrics"]

    # A reproducer who reproduces the *edited* raw events, compared against the real original
    # bundle, is caught structurally as DIVERGENT -- never silently accepted as MATCH.
    receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref=dict(result_bundle["project_binding_ref"]),
        protocol_freeze=protocol_freeze,
        original_result_bundle=result_bundle,
        reproducer_identity=_reproducer_identity(
            reproduction_process_id=result_bundle["generation_process_id"] + 1,
            reproducer="nc6-tamper-attempt",
        ),
        reproduced_raw_events=edited,
        generated_at=_GENERATED_AT,
    )
    assert receipt["agreement"] == "DIVERGENT"


# --- NC-7: post-hoc metric, denominator or threshold change is rejected ----------------------- #


def test_nc7_a_post_hoc_metric_or_threshold_change_mints_a_new_identity_never_retroactive(
    tmp_path: Path,
) -> None:
    """P90-R1-F4 widened ``identity.PROTOCOL_FREEZE_ID_FIELDS`` to include
    ``metric_definitions``/``numeric_thresholds`` themselves (previously excluded) -- so a
    post-hoc change to either now mints a genuinely *new* ``protocol_freeze_id``, never a
    same-id collision. This is the decisive proof for the required
    ``POST_HOC_THRESHOLD_MUTATION_REFUSED`` flag: the mutated policy content can never overwrite
    or retroactively apply to the original, already-committed protocol identity -- it can only
    ever exist as its own, separately identified, separately committed protocol freeze, and the
    original identity's own already-committed body is provably unchanged by the attempt."""

    from tests.long_running_proof import cycle as lrp_cycle

    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(tmp_path / "backend", schema_root=lrp_cycle.SCHEMA_ROOT)
    lrp_cycle.bind_genesis(store)

    kwargs = cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)
    first = cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **kwargs)

    mutated_metrics_kwargs = dict(kwargs)
    mutated_metrics_kwargs["metric_definitions"] = [
        {
            "metric_name": "a_new_metric_added_after_the_fact",
            "formula": "post-hoc",
            "denominator": "post-hoc",
        }
    ]
    mutated_metrics = build_protocol_freeze(project_id=cb.PROJECT_ID, **mutated_metrics_kwargs)
    assert mutated_metrics["protocol_freeze_id"] != first["protocol_freeze_id"]
    committed_mutated_metrics = cb_route.commit_protocol_freeze(
        store, project_id=cb.PROJECT_ID, **mutated_metrics_kwargs
    )
    assert committed_mutated_metrics["protocol_freeze_id"] == mutated_metrics["protocol_freeze_id"]

    mutated_thresholds_kwargs = dict(kwargs)
    mutated_thresholds_kwargs["numeric_thresholds"] = [
        {
            "metric_name": "raw_event_count",
            "comparison_group_id": cb.PRESENT_GROUP_ID,
            "operator": ">=",
            "threshold_value": 0,
            "comparison_decision_rule": "post-hoc rule",
        }
    ]
    mutated_thresholds = build_protocol_freeze(
        project_id=cb.PROJECT_ID, **mutated_thresholds_kwargs
    )
    assert mutated_thresholds["protocol_freeze_id"] != first["protocol_freeze_id"]
    assert mutated_thresholds["protocol_freeze_id"] != mutated_metrics["protocol_freeze_id"]

    # Decisive: the original, already-committed identity's own body is provably unchanged by
    # either post-hoc mutation attempt -- neither ever retroactively applies to it.
    resolved_original = cb_route.resolve_protocol_freeze(
        store, project_id=cb.PROJECT_ID, protocol_freeze_id=first["protocol_freeze_id"]
    )
    assert resolved_original == first

    # The original, unmutated re-commit is still a harmless idempotent replay at its own id.
    replay = cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **kwargs)
    assert replay == first

    # A genuinely conflicting re-commit at an *already-used* id (same id, different body) is
    # still refused -- P90-R1-F4 widened which fields mint a new identity, it did not remove
    # the underlying conflict guard for the one field ``protocol_freeze_id`` still excludes:
    # ``generated_at`` alone (the one genuinely nondeterministic field, per identity.py).
    conflicting_generated_at = dict(kwargs)
    conflicting_generated_at["generated_at"] = "2027-01-01T00:00:00.000001Z"
    with pytest.raises(RecordConflictError):
        cb_route.commit_protocol_freeze(store, project_id=cb.PROJECT_ID, **conflicting_generated_at)


# --- NC-8: cross-group/cross-project/cross-binding/cross-environment substitutions fail closed  #


def test_nc8_an_undeclared_comparison_group_id_in_a_raw_event_is_refused() -> None:
    protocol_freeze = _built_protocol_freeze()
    events = [
        _raw_event(
            group_id="a-group-this-protocol-freeze-never-declared",
            task_id=protocol_freeze["corpus_manifest"]["task_ids"][0],
            outcome="FAILED",
        )
    ]
    with pytest.raises(ResultBundleValidationError):
        build_result_bundle(
            project_id=cb.PROJECT_ID,
            project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
            protocol_freeze=protocol_freeze,
            raw_events=events,
            environment_manifest={
                "python_implementation": "CPython",
                "python_version": "3.12.0",
                "platform": "test",
            },
            generated_at=_GENERATED_AT,
        )


def test_nc8_a_foreign_result_bundle_reproduction_is_incomparable_never_silently_matched() -> None:
    protocol_freeze = _built_protocol_freeze()
    foreign_original_bundle = {
        "result_bundle_id": "CBRB-" + ("0" * 64),
        "result_bundle_semantic_fingerprint": "sha256:" + ("0" * 64),
        "metrics": {"a-completely-different-group-id": {"raw_event_count": 0}},
        "generation_process_id": os.getpid() + 1,
    }
    reproduced = _full_raw_events(protocol_freeze)
    receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
        protocol_freeze=protocol_freeze,
        original_result_bundle=foreign_original_bundle,
        reproducer_identity=_reproducer_identity(
            reproduction_process_id=os.getpid(), reproducer="nc8-cross-binding-attempt"
        ),
        reproduced_raw_events=reproduced,
        generated_at=_GENERATED_AT,
    )
    assert receipt["agreement"] == "INCOMPARABLE"


# --- NC-9: MANOSUBE timing/WTT/artifact records cannot become Completion Evidence ------------- #


def test_nc9_the_package_ships_no_evidence_handoff_module_and_never_imports_the_evidence_owner() -> (
    None
):
    package_root = Path(cb_route_module.__file__).resolve().parent
    assert not (package_root / "evidence_handoff.py").exists()

    for module in (cb_route_module, cb_engine_module):
        source = inspect.getsource(module)
        assert "manosube_agent_civilization.evidence" not in source, (
            f"{module.__name__} must never import the Evidence owner -- MANOSUBE's own timing/"
            "WTT/artifact records must never become Completion Evidence"
        )


def test_nc9_no_work_time_coordination_id_ever_appears_inside_a_committed_result_bundle(
    comparative_benchmark_run: dict[str, Any],
) -> None:
    import json

    result_bundle = comparative_benchmark_run["result_bundle"]
    serialized = json.dumps(result_bundle)
    assert "WORK-UNIT-CB21-" not in serialized
    assert "work_time_coordination" not in serialized


# --- NC-10: shorter or partial runs cannot impersonate the adopted benchmark scale ------------- #


def test_nc10_a_partial_scale_run_cannot_impersonate_the_full_frozen_corpus() -> None:
    protocol_freeze = _built_protocol_freeze()
    good = _full_raw_events(protocol_freeze)
    present_id = cb.PRESENT_GROUP_ID
    task_ids = list(protocol_freeze["corpus_manifest"]["task_ids"])
    assert len(task_ids) == 8

    others = [e for e in good if e["comparison_group_id"] != present_id]
    # A run over only the first 2 of 8 declared tasks -- a real "shorter tier" attempt.
    partial = others + [
        _raw_event(group_id=present_id, task_id=t, outcome="FAILED") for t in task_ids[:2]
    ]
    with pytest.raises(CorpusFidelityError):
        verify_corpus_fidelity(protocol_freeze, partial)


# --- NC-11: the benchmark harness cannot mutate existing Canonical owners through an extension #
#            surface --------------------------------------------------------------------------- #


def test_nc11_route_and_engine_never_call_commit_state_transition() -> None:
    for module in (cb_route_module, cb_engine_module):
        source = inspect.getsource(module)
        assert "commit_state_transition(" not in source, (
            f"{module.__name__} must never call commit_state_transition -- the benchmark must "
            "never become a new owner of Canonical State/Authority/Change/Evidence-"
            "sufficiency/Completion"
        )


def test_nc11_only_route_py_calls_commit_coordination_record_at_tip() -> None:
    route_source = inspect.getsource(cb_route_module)
    assert "commit_coordination_record_at_tip(" in route_source
    engine_source = inspect.getsource(cb_engine_module)
    assert "commit_coordination_record_at_tip(" not in engine_source
    assert ".commit(" not in engine_source


# --- NC-12: unsupported causal/superiority claims cannot exceed recorded Evidence -------------- #


def test_nc12_claim_text_is_only_ever_the_frozen_templates_own_placeholders_filled_in() -> None:
    """P90-R1-F5 made `derive_bounded_claims` genuinely read `metrics` into a claim's own
    rendered `statement` (`.format(**computed_values)` against the frozen template) -- so a
    claim's *text* now legitimately varies with the metrics handed in. NC-12's own decisive
    proof updates accordingly: nothing beyond the frozen `claim_statement_template`'s own
    declared placeholders, filled in with the real `computed_values` this function itself
    derived, is ever present in a claim's `statement` -- no causal or superiority language is
    ever synthesized beyond that frozen template, however favorable the metrics handed in."""

    protocol_freeze = _built_protocol_freeze()
    declared = {c["claim_id"]: c for c in protocol_freeze["claim_vocabulary"]}

    tiny_metrics = {
        cb.PRESENT_GROUP_ID: {"raw_event_count": 0, "COMPLETED_VERIFIED": 0},
        "claude_code_alone": {"raw_event_count": 0, "COMPLETED_VERIFIED": 0},
    }
    fabricated_favorable_metrics = {
        cb.PRESENT_GROUP_ID: {"raw_event_count": 1000, "COMPLETED_VERIFIED": 1000},
        "claude_code_alone": {"raw_event_count": 1000, "COMPLETED_VERIFIED": 1000},
    }

    claims_a = derive_bounded_claims(tiny_metrics, protocol_freeze)
    claims_b = derive_bounded_claims(fabricated_favorable_metrics, protocol_freeze)

    # Each claim's own rendered statement is exactly its frozen template, formatted against
    # exactly its own recomputed computed_values -- nothing more, nothing less.
    for claim in (*claims_a, *claims_b):
        entry = declared[claim["claim_id"]]
        expected_statement = entry["claim_statement_template"].format(**claim["computed_values"])
        assert claim["statement"] == expected_statement
        assert claim["bound"] == entry["bound"]

    # Every field except the rendered statement/computed_values is identical regardless of the
    # metrics content handed in -- a favorable-looking metrics dict changes only the
    # substituted numeric counts, never the claim's own identity, bound, or subject fields.
    def _stable(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {k: v for k, v in c.items() if k not in ("statement", "computed_values")}
            for c in claims
        ]

    assert _stable(claims_a) == _stable(claims_b)
    # And the two DO genuinely differ, precisely in the substituted numbers -- proving the
    # statement really is metrics-bound (P90-R1-F5), not independent boilerplate.
    assert claims_a != claims_b


# --- NC-13: a self-run reproduction cannot impersonate an independent third-party receipt ----- #


def test_nc13_a_self_claimed_original_author_cannot_force_a_match_verdict() -> None:
    protocol_freeze = _built_protocol_freeze()
    original_events = _full_raw_events(protocol_freeze)
    original_bundle = build_result_bundle(
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
        protocol_freeze=protocol_freeze,
        raw_events=original_events,
        environment_manifest={
            "python_implementation": "CPython",
            "python_version": "3.12.0",
            "platform": "test",
        },
        generated_at=_GENERATED_AT,
    )
    # A distinct-from-this-process pid stands in for "a genuinely separate reproduction
    # process" in this fast, in-process test -- see P90-R1-F3's own dedicated proof
    # (test_p90_r1_f3_self_asserted_independence_via_identical_process_id_is_refused below)
    # for the decisive same-process-refusal test itself.
    distinct_pid = original_bundle["generation_process_id"] + 1

    # A genuinely divergent re-run (one outcome flipped), claimed as the *original author*
    # ("is_original_author": True) -- the self-claim must never override the real, independent
    # recomputation this function itself performs.
    tampered = list(original_events)
    tampered[0] = {**tampered[0], "outcome": "COMPLETED_VERIFIED"}
    receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        reproducer_identity=_reproducer_identity(
            reproduction_process_id=distinct_pid, is_original_author=True, reproducer="self"
        ),
        reproduced_raw_events=tampered,
        generated_at=_GENERATED_AT,
    )
    assert receipt["agreement"] == "DIVERGENT"

    # Structural: build_reproduction_receipt accepts no caller-supplied "agreement" parameter
    # at all -- a caller cannot inject a claimed verdict even in principle.
    assert "agreement" not in inspect.signature(build_reproduction_receipt).parameters

    # An honestly-identical re-run, correctly disclosed as an independent reproducer, is a real
    # MATCH -- the flag never manufactures a false MATCH, and never manufactures a false
    # non-MATCH either.
    honest_receipt = build_reproduction_receipt(
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        reproducer_identity=_reproducer_identity(
            reproduction_process_id=distinct_pid, reproducer="independent-reproducer-002"
        ),
        reproduced_raw_events=original_events,
        generated_at=_GENERATED_AT,
    )
    assert honest_receipt["agreement"] == "MATCH"


def test_p90_r1_f3_self_asserted_independence_via_identical_process_id_is_refused() -> None:
    """P90-R1-F3's own decisive mechanical proof (``SELF_ASSERTED_INDEPENDENCE_REFUSED=true``):
    a caller that attempts to pass ``reproduction_process_id=os.getpid()`` -- the identical OS
    process that produced the original bundle -- is refused outright with
    ``ReproductionReceiptValidationError``, whatever ``is_original_author`` claims and whatever
    the reproduced raw events actually contain. Independence can never be a caller-supplied
    boolean nobody verifies; it is refused fail-closed the moment the two processes are
    provably the same one."""

    protocol_freeze = _built_protocol_freeze()
    original_events = _full_raw_events(protocol_freeze)
    original_bundle = build_result_bundle(
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
        protocol_freeze=protocol_freeze,
        raw_events=original_events,
        environment_manifest={
            "python_implementation": "CPython",
            "python_version": "3.12.0",
            "platform": "test",
        },
        generated_at=_GENERATED_AT,
    )
    # This test process is the same OS process that just built original_bundle above, so its
    # own os.getpid() is genuinely identical to original_bundle["generation_process_id"].
    assert os.getpid() == original_bundle["generation_process_id"]

    for is_original_author in (False, True):
        with pytest.raises(ReproductionReceiptValidationError, match="genuinely separate"):
            build_reproduction_receipt(
                project_id=cb.PROJECT_ID,
                project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
                protocol_freeze=protocol_freeze,
                original_result_bundle=original_bundle,
                reproducer_identity=_reproducer_identity(
                    reproduction_process_id=os.getpid(), is_original_author=is_original_author
                ),
                reproduced_raw_events=original_events,
                generated_at=_GENERATED_AT,
            )
