"""Phase 21 Comparative Benchmark -- the orchestrator (``00_KERNEL/
COMPARATIVE_BENCHMARK_CONTRACT.md``, Issue #89, ``ADOPT_PHASE_21_COMPARATIVE_BENCHMARK``;
Structural Review Round 1, P90-R1-F1/F2/F3).

Composes the real natural-route mechanism (:mod:`tests.long_running_proof.cycle`, reused
directly -- see ``tests/fixtures/comparative_benchmark.py``'s own module docstring for why) into
one comparative-benchmark run over :data:`tests.fixtures.comparative_benchmark.TASK_IDS`' single
frozen corpus, then commits the three real :mod:`manosube_agent_civilization.comparative_
benchmark` record kinds through their own real, public ``route.py`` entrypoints.

**P90-R1-F1: the ``MANOSUBE_ABSENT`` groups are a real, structurally-ungated execution, never a
fixture table.** :func:`run_ungated_reference_harness_group` drives each of the 3
``MANOSUBE_ABSENT`` comparison groups (``codex_alone``, ``claude_code_alone``,
``existing_agent_framework``) through the identical real natural-route mechanism the
``MANOSUBE_PRESENT`` group's own real ``CLOSED`` tasks use -- a fresh Store, a fresh genesis/
Project Binding, the real :func:`tests.long_running_proof.cycle.observe_before`/
``assemble_one_cycle``, and the real, unmodified ``reflow()`` -- over the byte-identical frozen
8-task corpus, never the deliberately-crafted ``REFUSED``/``FAILED``/``RETAINED`` branches the
``MANOSUBE_PRESENT`` group's own task-routing policy uses (that routing choice is itself
MANOSUBE's own deliberate policy, which by definition does not exist in the ``MANOSUBE_ABSENT``
condition). "Ungated" is structural, not an absence of Authority: no pre-flight Authority
decision ever gates whether an absent-group task is *attempted* -- every task is driven
uniformly -- but after each task's own real Reflow closure, this module retroactively
re-evaluates the identical real Authority Rule fixture against the exact action actually taken,
purely for audit/classification, and records that classification in the raw event's own
free-text ``reason`` field (never a live gate, never a new schema field). ``codex_alone`` and
``existing_agent_framework`` are driven by the identical real mechanism, differing from
``claude_code_alone`` only in their protocol freeze's own predeclared, honest ``agent_label`` --
never a real invocation of Codex, Claude Code, or any other third-party product
(``PRODUCTION_CREDENTIAL_USE_ALLOWED=false``, ``REMOTE_COMMAND_AUTHORITY_ALLOWED=false``, Issue
#89's own unchanged constraint).

**P90-R1-F3: the independent reproduction pass runs in a genuinely separate OS process.**
:func:`run_comparative_benchmark` spawns a real child Python process
(``tests.comparative_benchmark.reproduction_subprocess_entrypoint``) to produce
``reproduced_raw_events`` and that child's own real ``os.getpid()``/environment manifest, read
from *inside* the child, never guessed by the parent -- so
``engine.build_reproduction_receipt``'s own same-process-refusal check
(``reproduction_process_id == original_result_bundle["generation_process_id"]``) is checking
something real.

This module owns no Canonical State, Authority, Evidence, Reflow, or Completion decision of its
own (Issue #89 section 7) -- every canonical record either group produces is minted by calling
the real, existing owner (:mod:`~manosube_agent_civilization.observation`, ``.difference``,
``.authority``, ``.reflow``, all reused unmodified through :mod:`tests.long_running_proof.
cycle`); this module only decides *which* real route each task runs (the frozen
:data:`~tests.fixtures.comparative_benchmark.PRESENT_TASK_PLAN` for ``MANOSUBE_PRESENT``, the
uniform plain natural route for every ``MANOSUBE_ABSENT`` group) and records what happened as
raw events for :mod:`manosube_agent_civilization.comparative_benchmark.engine` to aggregate.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from tests.fixtures import comparative_benchmark as cb, long_running_proof as lrp
from tests.long_running_proof import cycle

from manosube_agent_civilization.authority import evaluate_authority
from manosube_agent_civilization.authority.identity import action_fingerprint
from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.difference import derive_differences
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.reflow.route import reflow
from manosube_agent_civilization.work_time_transparency.adapters import (
    ProgressReporter,
    with_work_time_coordination,
)
from manosube_agent_civilization.work_time_transparency.clock import default_clock

#: This file's own repository root -- the child reproduction-subprocess's own required ``cwd``
#: (P90-R1-F3), the identical convention ``tests/integration/boot/test_boot_project_route.py::
#: test_a_fresh_python_process_boots_successfully`` already establishes for a fresh-process proof.
REPO_ROOT = Path(__file__).resolve().parents[2]

#: The one Work-Time Transparency adapter_kind the adoption comment for Issue #89 itself
#: requires (``WORK_TIME_COORDINATION_REQUIRED=true`` for the comparison-group runner),
#: mirroring Phase 20's identical P87-R1-F7 precedent (``types.py``/schema both amended).
ADAPTER_KIND = "COMPARATIVE_BENCHMARK"
WORK_UNIT_REF_KIND = "comparative_benchmark_run"


class CorpusFidelityError(Exception):
    """Raised by :func:`verify_corpus_fidelity` -- the one real, decisive corpus-order-and-
    completeness guard this orchestrator itself enforces before any raw-event set may be
    committed as a result bundle or a reproduction receipt's own reproduced raw events
    (mirroring ``tests.long_running_proof.cycle.CorpusPositionError``'s own identical role,
    also a test-suite-level guard rather than a ``src/`` one): every declared comparison group
    must attempt *exactly* :data:`tests.fixtures.comparative_benchmark.TASK_IDS`, in that exact
    order, exactly once each -- never a reordered, omitted, duplicated, or substituted task set
    (NC-2), and never a success-only subset that drops a real refusal/retained/failed outcome
    (NC-5), and never a shorter/partial run impersonating this corpus's own full declared scale
    (NC-10)."""


def verify_corpus_fidelity(
    protocol_freeze: Mapping[str, Any], raw_events: Sequence[Mapping[str, Any]]
) -> None:
    """Refuse *raw_events* unless, for every ``comparison_group_id`` *protocol_freeze* itself
    declares, that group's own raw events name exactly *protocol_freeze*'s own
    ``corpus_manifest.task_ids`` list, in that exact order, with no gap and no repeat."""

    expected_task_ids = tuple(protocol_freeze["corpus_manifest"]["task_ids"])
    declared_group_ids = [
        group["comparison_group_id"] for group in protocol_freeze["comparison_groups"]
    ]
    by_group: dict[str, list[str]] = {group_id: [] for group_id in declared_group_ids}
    for event in raw_events:
        group_id = event["comparison_group_id"]
        if group_id not in by_group:
            raise CorpusFidelityError(
                f"raw event references undeclared comparison_group_id {group_id!r}"
            )
        by_group[group_id].append(event["task_id"])
    for group_id, task_ids in by_group.items():
        actual = tuple(task_ids)
        if actual != expected_task_ids:
            raise CorpusFidelityError(
                f"comparison_group_id={group_id!r} attempted task_ids {actual!r}, expected "
                f"exactly the frozen corpus {expected_task_ids!r} in that exact order -- "
                "refusing a reordered, omitted, duplicated, substituted, or partial-scale "
                "corpus attempt before any result bundle is committed"
            )


def _observed_now() -> str:
    """The one real wall-clock read this run's own raw events use for ``started_at``/
    ``closed_at`` -- genuinely non-deterministic observation time, never this corpus's own
    deterministic task/outcome identity. Reuses :func:`~manosube_agent_civilization.
    work_time_transparency.clock.default_clock`'s own canonical formatting (trailing-zero
    fractional digits stripped, per ``01_SCHEMA/common/timestamp.schema.json``'s own pattern)
    rather than a second, independently hand-rolled ``strftime`` call."""

    return default_clock()


def _task_event(
    *,
    group_id: str,
    task_id: str,
    outcome: str,
    started_at: str,
    closed_at: str,
    reason: str = "",
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "kind": "task_attempt",
        "comparison_group_id": group_id,
        "task_id": task_id,
        "outcome": outcome,
        "started_at": started_at,
        "closed_at": closed_at,
    }
    if reason:
        event["reason"] = reason
    return event


def _run_refused_task(
    store: Any, *, k: int, task_id: str, committed_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Drive task *k* through the real before-Observation and the real Difference derivation,
    then request a real Authority decision for an action this fixture world's own declared
    Authority Rule does not cover -- a genuine natural-route Authority refusal
    (``evaluate_authority``'s own "silence is not permission" floor resolves to
    ``HUMAN_APPROVAL_REQUIRED``, never ``AUTONOMOUS``), never a synthetic ``REFUSED`` event.
    No Change/Evidence/Reflow call is ever made for a refused task -- *committed_state* is
    returned unchanged."""

    started_at = _observed_now()
    before = cycle.observe_before(k, committed_state)
    diff = cycle.derive_difference(k, committed_state, before)
    difference = diff["difference"]

    out_of_scope_action: dict[str, Any] = {
        "action_kind": "DELETE_FILE",
        "reversibility": "REVERSIBLE",
        "operation": {"body": f"comparative-benchmark task {k:04d}: out-of-authority action"},
        "action_semantic_fingerprint": "",
    }
    out_of_scope_action["action_semantic_fingerprint"] = action_fingerprint(out_of_scope_action)

    request: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": difference["project_id"],
        "difference": difference,
        "requested_action": out_of_scope_action,
        "requested_scope": lrp.action_scope(),
        "current_state_revision": difference["observed_state_revision"],
        "current_state_fingerprint": difference["observed_state_fingerprint"],
        "authority_rules": [lrp.authority_rule(project_id=difference["project_id"])],
        "prohibitions": [],
        "approvals": [],
        "evaluation_time": lrp.AUTHORITY_EVALUATION_TIME,
    }
    decision = evaluate_authority(request)
    closed_at = _observed_now()
    if decision["decision"] == "AUTONOMOUS":
        raise AssertionError(
            f"task {task_id}: expected a real Authority refusal (non-AUTONOMOUS decision) for "
            f"an out-of-scope DELETE_FILE action, got {decision['decision']!r}"
        )
    event = _task_event(
        group_id=cb.PRESENT_GROUP_ID,
        task_id=task_id,
        outcome="REFUSED",
        started_at=started_at,
        closed_at=closed_at,
        reason=f"real Authority decision {decision['decision']!r} for an out-of-scope action",
    )
    return event, committed_state


def _run_failed_task(k: int, task_id: str, committed_state: dict[str, Any]) -> dict[str, Any]:
    """Drive task *k*'s real before-Observation, then hand a deliberately malformed Difference
    derivation request (its schema-required ``bindings`` field removed) to the real
    ``derive_differences`` owner -- a genuine, unhandled production validation failure, never a
    synthetic ``FAILED`` event."""

    started_at = _observed_now()
    before = cycle.observe_before(k, committed_state)
    request = lrp.derivation_request(
        k,
        observation_bundle=before["bundle"],
        fingerprint=committed_state["semantic_fingerprint"],
        state_revision=committed_state["state_revision"],
    )
    del request["bindings"]
    try:
        derive_differences(request)
    except DifferenceError as error:
        closed_at = _observed_now()
        return _task_event(
            group_id=cb.PRESENT_GROUP_ID,
            task_id=task_id,
            outcome="FAILED",
            started_at=started_at,
            closed_at=closed_at,
            reason=f"real {type(error).__name__}: {error}",
        )
    raise AssertionError(
        f"task {task_id}: expected the real derive_differences owner to raise on a malformed "
        "request missing its schema-required 'bindings' field"
    )


def _run_closed_task(
    store: Any, *, k: int, task_id: str, committed_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The unmodified real natural route: :func:`tests.long_running_proof.cycle.
    assemble_one_cycle`'s own assembly, committed through the real, unmodified ``reflow()``."""

    started_at = _observed_now()
    assembly = cycle.assemble_one_cycle(store, k=k, committed_state=committed_state)
    result = reflow(store, **assembly["reflow_kwargs"])
    closed_at = _observed_now()
    if result["decision"]["to_status"] != "CLOSED":
        raise AssertionError(
            f"task {task_id}: expected a real CLOSED Reflow outcome, got "
            f"{result['decision']['to_status']!r}"
        )
    event = _task_event(
        group_id=cb.PRESENT_GROUP_ID,
        task_id=task_id,
        outcome="COMPLETED_VERIFIED",
        started_at=started_at,
        closed_at=closed_at,
    )
    return event, result["committed_state"]


def _run_retained_task(
    store: Any, *, k: int, task_id: str, committed_state: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """The proven Phase 8 negative/interruption-route recipe (``tests/natural_cycle/
    test_vertical_proof_negative_routes.py::test_p8r1f2_a_genuinely_not_satisfied_evaluation_
    commits_a_real_retained_transition``), generalized to Phase 20's cycle composer: empty the
    Evidence Sufficiency pool, propose ``RETAINED`` (one of this fixture's own
    ``allowed_terminal_states``) instead of ``CLOSED``, and let the real, unmodified
    ``reflow()`` owner commit a real, non-``CLOSED`` terminal transition -- never a synthetic
    ``RETAINED_INCOMPLETE`` event."""

    started_at = _observed_now()
    assembly = cycle.assemble_one_cycle(store, k=k, committed_state=committed_state)
    before = assembly["before"]
    kwargs = dict(assembly["reflow_kwargs"])
    closure_request = dict(kwargs["closure_request"])

    sufficiency_request = dict(closure_request["evidence_sufficiency_request"])
    sufficiency_request["evidence_requests"] = []
    closure_request["evidence_sufficiency_request"] = sufficiency_request
    closure_request["proposed_terminal_status"] = "RETAINED"
    # A non-CLOSED terminal status requires its own real, resolvable terminal-reason Evidence
    # -- the real Observation Evidence `assemble_one_cycle` already derived serves that role
    # here, reused rather than a second Evidence derivation.
    closure_request["terminal_reason_evidence_refs"] = [
        {"kind": "observation_evidence", "id": before["observation_evidence"]["evidence_id"]}
    ]
    closure_request["terminal_reason_evidence_requests"] = [before["observation_evidence_request"]]
    # The base CLOSED-route assembly's own candidate invariant/claim bindings were verified
    # against the *original*, non-empty Sufficiency context -- emptying it above makes their
    # own re-verification genuinely stale, so neither is carried into this genuinely different
    # RETAINED route.
    closure_request["candidate_invariant_evaluation_bindings"] = []
    closure_request["invariant_evaluations"] = []
    closure_request["candidate_claim_evaluation_bindings"] = []
    closure_request["candidate_claim_evaluation_events"] = []
    kwargs["closure_request"] = closure_request
    # A non-CLOSED terminal status requires its own `next_observation_ref` (`reflow.lifecycle.
    # mint_transition_event`'s own real, structural requirement) -- the real, independent
    # verification Observation this cycle's own assembly already derived serves that role.
    kwargs["next_observation_ref"] = {
        "kind": "observation",
        "id": assembly["verification_observation_id"],
    }

    result = reflow(store, **kwargs)
    closed_at = _observed_now()
    if result["decision"]["to_status"] != "RETAINED":
        raise AssertionError(
            f"task {task_id}: expected a real RETAINED Reflow outcome, got "
            f"{result['decision']['to_status']!r}"
        )
    event = _task_event(
        group_id=cb.PRESENT_GROUP_ID,
        task_id=task_id,
        outcome="RETAINED_INCOMPLETE",
        started_at=started_at,
        closed_at=closed_at,
    )
    return event, result["committed_state"]


_PRESENT_STATE_ADVANCING_RUNNERS = {
    "CLOSED": _run_closed_task,
    "RETAINED": _run_retained_task,
}


def run_present_group(store: Any, *, committed_state: dict[str, Any]) -> list[dict[str, Any]]:
    """Drive the whole frozen 8-task corpus through the real natural route for the
    ``MANOSUBE_PRESENT`` group, exactly as :data:`tests.fixtures.comparative_benchmark.
    PRESENT_TASK_PLAN` predeclares -- never a stub, never a route this repository does not
    already, separately own. Every task produces a real raw event; none is ever dropped."""

    raw_events: list[dict[str, Any]] = []
    for task_id in cb.TASK_IDS:
        k = cb.CB_TASK_TO_NATURAL_ROUTE_CYCLE_INDEX[task_id]
        plan = cb.PRESENT_TASK_PLAN[task_id]
        if plan == "REFUSED":
            event, committed_state = _run_refused_task(
                store, k=k, task_id=task_id, committed_state=committed_state
            )
        elif plan == "FAILED":
            event = _run_failed_task(k, task_id, committed_state)
        else:
            runner = _PRESENT_STATE_ADVANCING_RUNNERS[plan]
            event, committed_state = runner(
                store, k=k, task_id=task_id, committed_state=committed_state
            )
        raw_events.append(event)
    return raw_events


#: A real ``MANOSUBE_ABSENT`` task's own real Reflow terminal status, mapped to the closed
#: :data:`~manosube_agent_civilization.comparative_benchmark.types.TASK_OUTCOMES` vocabulary --
#: the identical mapping :func:`_run_closed_task`/``_run_retained_task`` already use for the
#: ``MANOSUBE_PRESENT`` group, so a real ``RETAINED`` closure is never silently miscounted here
#: either. Deliberately has no entry for any other real terminal status (e.g. ``BLOCKED``):
#: :func:`run_ungated_reference_harness_group` raises rather than guess at an unmapped one.
_ABSENT_TERMINAL_STATUS_TO_OUTCOME: dict[str, str] = {
    "CLOSED": "COMPLETED_VERIFIED",
    "RETAINED": "RETAINED_INCOMPLETE",
}


def run_ungated_reference_harness_group(tmp_path: Path, *, group_id: str) -> list[dict[str, Any]]:
    """P90-R1-F1: the real, structurally-ungated ``MANOSUBE_ABSENT`` baseline -- a fresh Store
    and a fresh genesis/Project Binding (:func:`tests.long_running_proof.cycle.build_store`/
    ``bind_genesis``, the identical pattern this module's own independent-reproducer pass uses),
    driven through the real natural route (:func:`tests.long_running_proof.cycle.
    assemble_one_cycle` + the real, unmodified ``reflow()``) for every task in
    :data:`tests.fixtures.comparative_benchmark.TASK_IDS`, in order -- always the plain
    natural-route path, never the deliberately-crafted REFUSED/FAILED/RETAINED branches
    :func:`_run_refused_task`/``_run_failed_task``/``_run_retained_task`` use for
    ``MANOSUBE_PRESENT`` (that routing choice is itself MANOSUBE's own deliberate policy, which
    by definition does not exist in the ``MANOSUBE_ABSENT`` condition).

    After each task's own real Reflow closure, retroactively (audit/classification only, never
    a live pre-flight gate -- ``MANOSUBE_ABSENT`` structurally means no such gate exists) calls
    the real :func:`~manosube_agent_civilization.authority.evaluate_authority` again, against
    the exact real Authority request the real closure itself already used, and records that
    classification in the raw event's own free-text ``reason`` field -- the identical real
    Authority Rule/mechanism/runtime/resource boundary the ``MANOSUBE_PRESENT`` group uses
    (``SAME_AUTHORITY_RUNTIME_RESOURCE_BOUNDARY=true``), never a second schema field. Every
    outcome here is the real terminal status a real ``reflow()`` call actually returned --
    never a fixture-table lookup (``FABRICATED_CONTROL_OUTCOMES_COUNTED_AS_RESULTS=false``)."""

    store = cycle.build_store(tmp_path / group_id)
    bind_result = cycle.bind_genesis(store)
    committed_state = bind_result["committed_state"]

    events: list[dict[str, Any]] = []
    for task_id in cb.TASK_IDS:
        k = cb.CB_TASK_TO_NATURAL_ROUTE_CYCLE_INDEX[task_id]
        started_at = _observed_now()
        assembly = cycle.assemble_one_cycle(store, k=k, committed_state=committed_state)
        result = reflow(store, **assembly["reflow_kwargs"])
        closed_at = _observed_now()

        to_status = result["decision"]["to_status"]
        outcome = _ABSENT_TERMINAL_STATUS_TO_OUTCOME.get(to_status)
        if outcome is None:
            raise AssertionError(
                f"{group_id}: task {task_id} produced a real Reflow terminal status "
                f"{to_status!r} this ungated reference harness does not yet map to a declared "
                "TASK_OUTCOMES member -- refusing to silently miscount it"
            )

        retroactive_decision = evaluate_authority(assembly["authority"]["request"])
        reason = (
            "real natural-route execution over a fresh Store -- no pre-flight Authority gate; "
            "retroactive Authority classification of the exact action actually taken: "
            f"{retroactive_decision['decision']!r}"
        )
        events.append(
            _task_event(
                group_id=group_id,
                task_id=task_id,
                outcome=outcome,
                started_at=started_at,
                closed_at=closed_at,
                reason=reason,
            )
        )
        committed_state = result["committed_state"]
    return events


def run_all_comparison_groups(
    store: Any, *, committed_state: dict[str, Any], tmp_path: Path
) -> list[dict[str, Any]]:
    """Run every comparison group this protocol freeze declares -- the real natural route for
    ``MANOSUBE_PRESENT`` against *store*, the real, structurally-ungated reference harness (its
    own fresh Store rooted under *tmp_path*, per group) for every ``MANOSUBE_ABSENT`` group --
    over the identical frozen task corpus, in the identical declared order
    (``COMPARABLE_PROJECT_AND_TASK_CORPUS_REQUIRED=true``)."""

    raw_events = run_present_group(store, committed_state=committed_state)
    for group_id in cb.ABSENT_GROUP_IDS:
        raw_events += run_ungated_reference_harness_group(tmp_path, group_id=group_id)
    return raw_events


def run_one_full_pass(
    store: Any, *, project_binding_id: str, run_label: str, tmp_path: Path
) -> list[dict[str, Any]]:
    """Open one real Work Coordination (``WORK_TIME_COORDINATION_REQUIRED=true`` for this
    comparison-group runner, per the Issue #89 adoption comment) around the full run -- both
    the real natural-route driving of the ``MANOSUBE_PRESENT`` group and the real, structurally-
    ungated driving of every ``MANOSUBE_ABSENT`` group -- and return every raw event collected.
    *tmp_path* roots every ``MANOSUBE_ABSENT`` group's own fresh Store (one subdirectory per
    group), kept separate from *store*'s own root so neither family's own advancing State
    history ever collides with the other's."""

    work_unit_ref = {
        "kind": WORK_UNIT_REF_KIND,
        "id": f"WORK-UNIT-CB21-{run_label.upper().replace('_', '-')}",
    }

    def _perform(reporter: ProgressReporter) -> list[dict[str, Any]]:
        committed_state = store.load_current(lrp.PROJECT_ID)
        raw_events = run_all_comparison_groups(
            store, committed_state=committed_state, tmp_path=tmp_path
        )
        reporter.report(
            position_kind="WORK_RUNNING",
            current_position=(
                f"comparative benchmark run {run_label}: all comparison groups complete"
            ),
            next_progress_update_due_minutes=10,
            remaining_duration_unknown=True,
        )
        return raw_events

    _open_record, _terminal_record, raw_events = with_work_time_coordination(
        store,
        project_id=lrp.PROJECT_ID,
        project_binding_id=project_binding_id,
        adapter_kind=ADAPTER_KIND,
        work_unit_ref=work_unit_ref,
        estimated_duration_lower_minutes=1,
        estimated_duration_upper_minutes=10,
        estimate_confidence="LOW",
        major_steps=[
            "MANOSUBE_PRESENT group: real natural route over the frozen corpus",
            "MANOSUBE_ABSENT groups: ungated reference harness over the identical frozen corpus",
        ],
        next_progress_update_due_minutes=10,
        variability_factors="none -- fully deterministic fixture-world run",
        perform=_perform,
    )
    return raw_events


def _environment_manifest() -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }


#: The child reproduction-subprocess's own module path -- run with ``-m`` so its own
#: ``if __name__ == "__main__"`` guard fires, exactly the ``sys.executable``/``cwd``-rooted
#: fresh-process idiom ``tests/integration/boot/test_boot_project_route.py::
#: test_a_fresh_python_process_boots_successfully`` already establishes for a real, separate-
#: process proof.
_REPRODUCTION_SUBPROCESS_MODULE = "tests.comparative_benchmark.reproduction_subprocess_entrypoint"


def _run_reproduction_subprocess() -> dict[str, Any]:
    """P90-R1-F3: spawn a genuinely separate OS process to perform the independent reproduction
    run, and return that child's own reported ``reproduced_raw_events``/
    ``reproduction_process_id``/``reproduction_environment_manifest`` -- all three read from
    *inside* the child (never guessed or forwarded by this, the parent, process), so
    ``engine.build_reproduction_receipt``'s own same-process-refusal check has something real to
    check against this run's own ``result_bundle["generation_process_id"]``."""

    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-m", _REPRODUCTION_SUBPROCESS_MODULE],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=600,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"reproduction subprocess ({_REPRODUCTION_SUBPROCESS_MODULE}) exited "
            f"{proc.returncode}: stderr={proc.stderr}"
        )
    payload: dict[str, Any] = json.loads(proc.stdout.strip().splitlines()[-1])
    return payload


def run_comparative_benchmark(tmp_path: Path) -> dict[str, Any]:
    """The one Gate 21 proof entry point: freeze the protocol before any result exists
    (``PROTOCOL_FROZEN_BEFORE_RESULTS=true``), run every comparison group's tasks over the
    identical frozen corpus once (the original run, in this process) and once more, entirely
    independently, in a genuinely separate OS process (P90-R1-F3: its own fresh Store, its own
    fresh project genesis+binding, its own reproducer identity -- see
    :func:`_run_reproduction_subprocess`), and commit all three real record kinds through the
    real ``comparative_benchmark.route`` entrypoints."""

    store = cycle.build_store(tmp_path / "original")
    bind_result = cycle.bind_genesis(store)
    project_binding_id = bind_result["project_binding_id"]

    generated_at = default_clock()
    protocol_freeze = cb_route.commit_protocol_freeze(
        store,
        project_id=cb.PROJECT_ID,
        **cb.protocol_freeze_kwargs(generated_at=generated_at),
    )

    raw_events = run_one_full_pass(
        store,
        project_binding_id=project_binding_id,
        run_label="original",
        tmp_path=tmp_path / "original-absent-groups",
    )
    verify_corpus_fidelity(protocol_freeze, raw_events)

    result_bundle = cb_route.commit_result_bundle(
        store,
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": project_binding_id},
        protocol_freeze=protocol_freeze,
        raw_events=raw_events,
        environment_manifest=_environment_manifest(),
        generated_at=default_clock(),
    )

    reproduction_payload = _run_reproduction_subprocess()
    reproduced_raw_events: list[dict[str, Any]] = reproduction_payload["reproduced_raw_events"]
    verify_corpus_fidelity(protocol_freeze, reproduced_raw_events)

    reproduction_receipt = cb_route.commit_reproduction_receipt(
        store,
        project_id=cb.PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": project_binding_id},
        protocol_freeze=protocol_freeze,
        original_result_bundle=result_bundle,
        reproducer_identity={
            "reproducer": "independent-reproducer-001",
            "is_original_author": False,
            "reproduction_process_id": reproduction_payload["reproduction_process_id"],
            "reproduction_environment_manifest": reproduction_payload[
                "reproduction_environment_manifest"
            ],
        },
        reproduced_raw_events=reproduced_raw_events,
        generated_at=default_clock(),
    )

    return {
        "store": store,
        "project_binding_id": project_binding_id,
        "protocol_freeze": protocol_freeze,
        "raw_events": raw_events,
        "result_bundle": result_bundle,
        "reproduced_raw_events": reproduced_raw_events,
        "reproduction_receipt": reproduction_receipt,
    }
