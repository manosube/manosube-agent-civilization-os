"""Issue #22's own required adapter conformance proof.

Structural Review Round 1 (P84-R1-F1, ``REAL_ADAPTER_INTEGRATION_TESTS_REQUIRED=8_OF_8``): every
one of the eight closed :data:`~manosube_agent_civilization.work_time_transparency.types.
ADAPTER_KINDS` is now proved here through its own real, completely unmodified production
entrypoint, called at its real entry boundary, over a real ``FileStateStore``, with each
adapter's own real accepted precondition chain (a real bound Project, a real committed
Difference/Boundary/Grant, a real signed Human declaration, a real git worktree, a real Ed25519
kill-switch, a real ``FakeGitHubAdapter`` -- never a dummy stand-in callable) -- superseding this
module's own prior disclosed scope decision, which proved only Boot this way and stood in an
arbitrary zero-argument callable for the remaining seven.

Every test below reuses, by direct cross-import, the identical fixture-construction functions
each adapter's own existing integration-test module already establishes and proves end to end
(``tests/integration/cli/test_cli_boot_command.py``, ``tests/integration/agent_runtime/
test_temporary_agent_lifecycle.py``, ``tests/fixtures/model_runtime_world.py``, ``tests/fixtures/
multi_agent_world.py``, ``tests/fixtures/change_executor_world.py`` (+ its own kill-switch
issuer), and -- since Independent Verification and GitHub Projection carry no dedicated ``tests/
fixtures/*_world.py`` module of their own -- the small, plain (non-``pytest.fixture``-decorated)
helper functions their own integration-test modules already define, imported directly rather than
duplicated. This is the identical "no second owner of another vertical's own precondition chain"
discipline ``adapters.py``'s own module docstring already commits this package to -- reusing an
existing test-side builder is not the same as this package importing (or wrapping) that
vertical's own shipped ``route.py``, which it still never does.

Every real adapter call below is wrapped by the one shared composition primitive
(:func:`~manosube_agent_civilization.work_time_transparency.adapters.with_work_time_coordination`)
exactly as a real caller would use it (Structural Review Round 1, P84-R1-F4): a deterministic,
monotonically-advancing injected ``clock=`` (never the real wall clock), and *perform* receiving
one :class:`~manosube_agent_civilization.work_time_transparency.adapters.ProgressReporter` --
two of the tests below (Change Executor, Independent Verification) call
:meth:`~manosube_agent_civilization.work_time_transparency.adapters.ProgressReporter.report`
once, mid-``perform``, proving the real in-flight progress channel genuinely commits a durable
heartbeat while the wrapped adapter call is still running, not only around an opaque call.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import itertools
from pathlib import Path
from typing import Any

import pytest
import tests.evidence_helpers as evidence_helpers
from tests.fixtures.change_executor_kill_switch_issuer import issuer_public_key_hex
from tests.fixtures.change_executor_world import (
    CountingAdapter,
    bound as change_executor_bound,
    build_committed_change,
    commit_active_kill_switch,
    execution_boundary_for,
    git_worktree,
    operation_for,
)
from tests.fixtures.model_runtime_world import (
    authorized_world as model_runtime_authorized_world,
    open_kwargs as model_runtime_open_kwargs,
)
from tests.fixtures.multi_agent_world import (
    authorized_world as multi_agent_authorized_world,
    open_plan_kwargs,
)
from tests.fixtures.product_binding import human_authority_ref as canonical_human_authority_ref
from tests.fixtures.work_time_transparency_world import bound
from tests.integration.agent_runtime.test_temporary_agent_lifecycle import (
    _bound as _agent_bound,
)
from tests.integration.cli.test_cli_boot_command import (
    _argv as _cli_argv,
    _bound as _cli_bound,
)
from tests.integration.independent_verification.test_run_independent_verification import (
    _advance as _iv_advance,
    _bound as _iv_bound,
    _counting_verifier as _iv_counting_verifier,
    _grant as _iv_grant,
    _ref as _iv_ref,
    _requirement as _iv_requirement,
    _selection as _iv_selection,
    _sign_declaration as _iv_sign_declaration,
)
from tests.integration.projection.test_project_to_github import (
    _PAYLOAD as _PROJECTION_PAYLOAD,
    _TARGET_REPOSITORY,
    _bound as _proj_bound,
    _commit_declaration as _proj_commit_declaration,
    _commit_grant as _proj_commit_grant,
    _commit_records as _proj_commit_records,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.agent_runtime import TemporaryAgent, start_temporary_agent
from manosube_agent_civilization.binding import declare_human_grant
from manosube_agent_civilization.boot import BootContext, boot_project
from manosube_agent_civilization.change_executor.route import compose_change_executor
from manosube_agent_civilization.cli.main import run
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.evidence.identity import evidence_semantic_fingerprint
from manosube_agent_civilization.independent_verification import (
    VerificationResult,
    run_independent_verification,
)
from manosube_agent_civilization.model_runtime.route import open_model_work_unit
from manosube_agent_civilization.multi_agent.route import open_dynamic_execution_plan
from manosube_agent_civilization.projection import FakeGitHubAdapter, project_to_github
from manosube_agent_civilization.projection.identity import projection_payload_fingerprint
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.work_time_transparency.adapters import (
    ProgressReporter,
    with_work_time_coordination,
)
from manosube_agent_civilization.work_time_transparency.clock import parse_canonical_timestamp
from manosube_agent_civilization.work_time_transparency.identity import (
    work_time_coordination_open_id,
    work_time_coordination_terminal_id,
)
from manosube_agent_civilization.work_time_transparency.types import (
    ADAPTER_KIND_TO_WORK_UNIT_REF_KIND,
    ADAPTER_KINDS,
)


def _deterministic_clock(*, start: str, step_seconds: int = 1) -> Callable[[], str]:
    """A real, deterministic, monotonically-advancing clock -- never the real wall clock --
    used as every test below's own injected ``clock=`` argument (Structural Review Round 1,
    P84-R1-F4). Each call returns *start* plus one more whole *step_seconds* increment than the
    previous call, so a genuine sequence of ``open``/``report``/terminal observations is always
    strictly ordered and always passes :func:`~manosube_agent_civilization.work_time_
    transparency.clock.is_monotonic`."""

    base = parse_canonical_timestamp(start)
    calls = itertools.count()

    def _clock() -> str:
        moment = base + timedelta(seconds=step_seconds * next(calls))
        return moment.strftime("%Y-%m-%dT%H:%M:%S") + "Z"

    return _clock


# --- Boot (the one adapter this module always proved this way) ------------------------------ #


def test_boot_the_one_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform(reporter: ProgressReporter) -> BootContext:
        return boot_project(store, project_id=project_id, project_binding_id=project_binding_id)

    open_record, terminal_record, boot_context = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="BOOT",
        work_unit_ref={"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["boot"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T08:00:00Z"),
    )
    assert terminal_record["terminal_outcome"] == "COMPLETED"
    assert boot_context.project_id == project_id
    resolved_terminal = store.resolve_record(
        project_id,
        "work_time_coordination_terminal",
        terminal_record["work_time_coordination_terminal_id"],
    )
    assert resolved_terminal == terminal_record
    assert (
        store.resolve_record(
            project_id, "work_time_coordination_open", open_record["work_time_coordination_open_id"]
        )
        == open_record
    )


def test_a_failing_real_call_produces_a_failed_terminal_notice_and_the_original_exception_still_propagates(
    tmp_path: Path,
) -> None:
    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform_and_fail(reporter: ProgressReporter) -> object:
        # A real, unmodified production call with a deliberately wrong project_binding_id --
        # boot_project itself refuses this; no work_time_transparency code fabricates the failure.
        return boot_project(store, project_id=project_id, project_binding_id="WRONG-BINDING-ID")

    with pytest.raises(Exception) as excinfo:
        with_work_time_coordination(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            adapter_kind="BOOT",
            work_unit_ref={"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-FAIL-1"},
            estimated_duration_lower_minutes=0,
            estimated_duration_upper_minutes=1,
            estimate_confidence="HIGH",
            major_steps=["boot"],
            next_progress_update_due_minutes=10,
            variability_factors="none",
            perform=_perform_and_fail,
            clock=_deterministic_clock(start="2026-09-14T08:10:00Z"),
        )
    original_exception_type = excinfo.type

    open_id = work_time_coordination_open_id(
        project_id, {"kind": "boot_session", "id": "WORK-UNIT-ADAPTER-BOOT-FAIL-1"}
    )
    terminal = store.resolve_record(
        project_id, "work_time_coordination_terminal", work_time_coordination_terminal_id(open_id)
    )
    assert terminal is not None
    assert terminal["terminal_outcome"] == "FAILED_TERMINAL"
    assert original_exception_type.__name__ in terminal["explanation"]


@pytest.mark.parametrize("adapter_kind", ADAPTER_KINDS)
def test_every_declared_adapter_kind_composes_uniformly_through_the_shared_primitive(
    tmp_path: Path, adapter_kind: str
) -> None:
    """Uniform semantics across every closed adapter kind -- Issue #22's own Kernel Placement
    requirement ("Adapter-specific UI may format the notice differently but must preserve the
    same fields and timing rules"), proved here with an arbitrary representative callable at the
    :func:`with_work_time_coordination` interface itself; the real production entrypoint of every
    one of these eight adapter kinds is separately proved below and above."""

    store, world = bound(tmp_path)
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]
    calls: list[str] = []

    def _perform(reporter: ProgressReporter) -> str:
        calls.append(adapter_kind)
        return f"{adapter_kind}-result"

    open_record, terminal_record, result = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind=adapter_kind,
        work_unit_ref={
            "kind": ADAPTER_KIND_TO_WORK_UNIT_REF_KIND[adapter_kind],
            "id": f"WORK-UNIT-UNIFORM-{adapter_kind.replace('_', '-')}",
        },
        estimated_duration_lower_minutes=1,
        estimated_duration_upper_minutes=2,
        estimate_confidence="HIGH",
        major_steps=["run"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T09:00:00Z"),
    )
    assert result == f"{adapter_kind}-result"
    assert calls == [adapter_kind]
    assert open_record["adapter_kind"] == adapter_kind
    assert terminal_record["terminal_outcome"] == "COMPLETED"


# --- CLI -------------------------------------------------------------------------------------- #


def test_cli_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path, capsysbinary: pytest.CaptureFixture[bytes]
) -> None:
    store_root, kwargs, result = _cli_bound(tmp_path)
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    def _perform(reporter: ProgressReporter) -> int:
        exit_code = run(_cli_argv(store_root, SCHEMA_ROOT, project_id, project_binding_id))
        capsysbinary.readouterr()
        return exit_code

    open_record, terminal_record, exit_code = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="CLI",
        work_unit_ref={"kind": "cli_invocation", "id": "WORK-UNIT-ADAPTER-CLI-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["run the boot command"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:00:00Z"),
    )
    assert exit_code == 0
    assert open_record["adapter_kind"] == "CLI"
    assert terminal_record["terminal_outcome"] == "COMPLETED"


# --- Temporary Agent ---------------------------------------------------------------------------- #


def test_temporary_agent_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store_root, kwargs, result = _agent_bound(tmp_path)
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)

    def _perform(reporter: ProgressReporter) -> TemporaryAgent:
        return start_temporary_agent(
            store, project_id=project_id, project_binding_id=project_binding_id
        )

    open_record, terminal_record, agent = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="TEMPORARY_AGENT",
        work_unit_ref={"kind": "temporary_agent_session", "id": "WORK-UNIT-ADAPTER-AGENT-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["start temporary agent"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:10:00Z"),
    )
    assert agent.boot_context.project_id == project_id
    agent.release()
    assert open_record["adapter_kind"] == "TEMPORARY_AGENT"
    assert terminal_record["terminal_outcome"] == "COMPLETED"


# --- Model Runtime -------------------------------------------------------------------------- #


def test_model_runtime_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    world = model_runtime_authorized_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform(reporter: ProgressReporter) -> dict[str, Any]:
        # The Agent is started *inside* perform, after the coordination's own open record has
        # already committed -- open_model_work_unit's own live-contract check requires the
        # Agent's Boot-observed State to exactly match the Store's own current State.
        agent = start_temporary_agent(
            store, project_id=project_id, project_binding_id=project_binding_id
        )
        return open_model_work_unit(
            store,
            agent,
            **model_runtime_open_kwargs(world, opened_at="2026-09-14T10:20:00Z"),
        )

    open_record, terminal_record, opened = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="MODEL_RUNTIME",
        work_unit_ref={"kind": "model_runtime_work_unit", "id": "WORK-UNIT-ADAPTER-MODEL-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["open model work unit"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:20:00Z"),
    )
    assert "model_work_unit" in opened
    assert opened["model_execution_decision"]["decision"] == "MODEL_EXECUTION_AUTHORIZED"
    assert open_record["adapter_kind"] == "MODEL_RUNTIME"
    assert terminal_record["terminal_outcome"] == "COMPLETED"


# --- Multi-Agent ------------------------------------------------------------------------------ #


def test_multi_agent_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    world = multi_agent_authorized_world(tmp_path)
    store = world["store"]
    project_id = world["project_id"]
    project_binding_id = world["project_binding_id"]

    def _perform(reporter: ProgressReporter) -> dict[str, Any]:
        agent = start_temporary_agent(
            store, project_id=project_id, project_binding_id=project_binding_id
        )
        return open_dynamic_execution_plan(
            store,
            agent,
            **open_plan_kwargs(
                world, opened_at="2026-09-14T10:30:00Z", expires_at="2026-09-14T11:30:00Z"
            ),
        )

    open_record, terminal_record, opened = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="MULTI_AGENT",
        work_unit_ref={"kind": "multi_agent_execution_plan", "id": "WORK-UNIT-ADAPTER-MULTI-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["open dynamic execution plan"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:30:00Z"),
    )
    assert "plan" in opened
    assert open_record["adapter_kind"] == "MULTI_AGENT"
    assert terminal_record["terminal_outcome"] == "COMPLETED"


# --- Change Executor ----------------------------------------------------------------------- #


def test_change_executor_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store, info = change_executor_bound(tmp_path)
    project_id = info["project_id"]
    project_binding_id = info["project_binding_id"]
    commit_active_kill_switch(store, project_id)

    content = "# Adapter Conformance\n\nWritten by a real Change Executor adapter call.\n"
    worktree_root = git_worktree(tmp_path)
    adapter = CountingAdapter()

    def _perform(reporter: ProgressReporter) -> dict[str, Any]:
        # A real, immediately-committed in-flight heartbeat, posted while this real adapter call
        # is genuinely still running (P84-R1-F4's own required in-flight channel) -- posted
        # *before* the Change is built so the Change is authorized against the State exactly as
        # it stands right before execute() runs (Change Executor's own preflight staleness check
        # refuses a Change authorized against any State but the one immediately preceding it).
        reporter.report(
            position_kind="WORK_RUNNING",
            current_position="about to build and execute the real Change",
            remaining_duration_unknown=True,
            next_progress_update_due_minutes=5,
        )
        change_result = build_committed_change(
            store,
            project_id,
            action_kind="WRITE_DOCUMENTATION_FILE",
            operation=operation_for(
                "WRITE_DOCUMENTATION_FILE",
                writes=[{"path": "docs/adapter_conformance.md", "content_utf8": content}],
            ),
            paths=["docs/adapter_conformance.md"],
        )
        change = change_result["change"]
        execute = compose_change_executor(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            execution_boundary=execution_boundary_for(worktree_root=str(worktree_root)),
            adapter_identity={"kind": "controlled_filesystem_adapter", "version": "0.1"},
            adapter=adapter,
            kill_switch_trust_anchor_public_key_hex=issuer_public_key_hex(),
        )
        return execute(
            change["change_id"],
            claim_token="adapter-conformance-claim",  # noqa: S106
            execution_instant="2026-09-10T00:00:01Z",
        )

    open_record, terminal_record, outcome = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="CHANGE_EXECUTOR",
        work_unit_ref={"kind": "change_executor_execution", "id": "WORK-UNIT-ADAPTER-CHANGE-1"},
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["execute change"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:40:00Z"),
    )
    assert outcome["receipt"]["outcome"] == "SUCCEEDED"
    assert adapter.call_count == 1
    assert open_record["adapter_kind"] == "CHANGE_EXECUTOR"
    assert terminal_record["terminal_outcome"] == "COMPLETED"
    # the in-flight heartbeat genuinely committed, chained ahead of the terminal notice.
    heartbeat_id = terminal_record["predecessor_ref"]["id"]
    heartbeat = store.resolve_record(project_id, "work_time_coordination_update", heartbeat_id)
    assert heartbeat is not None
    assert heartbeat["sequence_number"] == 1


# --- Independent Verification ---------------------------------------------------------------- #


def test_independent_verification_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store_root, kwargs, result = _iv_bound(tmp_path)
    project_id = kwargs["project_id"]
    project_binding_id = result["project_binding_id"]
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    genesis_state = result["committed_state"]
    evidence_id = "EVID-ADAPTER-CONFORMANCE-0001"
    successor, event = _iv_advance(store, project_id, genesis_state)

    human_ref = canonical_human_authority_ref()
    grant = _iv_grant({"project_id": project_id, "human_authority_ref": human_ref})

    store.commit(
        project_id,
        genesis_state["state_revision"],
        genesis_state["semantic_fingerprint"],
        successor,
        event,
        records=[
            (
                "observation_evidence",
                evidence_id,
                {"kind": "observation_evidence", "note": "adapter conformance fixture record"},
            ),
            ("verifier_selection_grant", grant["verifier_selection_grant_id"], grant),
        ],
    )

    declared_at = "2026-09-14T10:50:00Z"
    grant_ref = _iv_ref(grant)
    declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at=declared_at,
        signature=_iv_sign_declaration(
            {
                "project_id": project_id,
                "project_binding_id": project_binding_id,
                "grant_ref": grant_ref,
                "declared_by": human_ref,
                "requirement_id": grant["requirement_id"],
                "selection_id": grant["selection_id"],
                "verifier_identity": grant["verifier_identity"],
                "permitted_boundary": grant["permitted_boundary"],
                "status": "ACTIVE",
                "declared_at": declared_at,
            }
        ),
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    declaration_ref = {
        "kind": "human_grant_declaration",
        "id": declaration["human_grant_declaration_id"],
    }

    requirement = _iv_requirement(evidence_id, "D-ADAPTER-CONFORMANCE-0001", human_ref)
    selection = _iv_selection(human_ref)
    _calls, verifier = _iv_counting_verifier(
        {
            "status": "VERIFIED",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-ADAPTER-CONFORMANCE-0001"}],
            "observations": {"summary": "adapter conformance"},
        }
    )

    def _perform(reporter: ProgressReporter) -> VerificationResult:
        reporter.report(
            position_kind="WORK_RUNNING",
            current_position="calling the verifier",
            remaining_duration_unknown=True,
            next_progress_update_due_minutes=5,
        )
        return run_independent_verification(
            store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            verification_requirement=requirement,
            verifier_selection=selection,
            verifier_selection_grant_refs=[grant_ref],
            human_grant_declaration_refs=[declaration_ref],
            verifier=verifier,
        )

    open_record, terminal_record, verification_result = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="INDEPENDENT_VERIFICATION",
        work_unit_ref={
            "kind": "independent_verification_run",
            "id": "WORK-UNIT-ADAPTER-VERIFY-1",
        },
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["run independent verification"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T10:50:00Z"),
    )
    assert verification_result.status == "VERIFIED"
    assert _calls == [1]
    assert open_record["adapter_kind"] == "INDEPENDENT_VERIFICATION"
    assert terminal_record["terminal_outcome"] == "COMPLETED"
    heartbeat_id = terminal_record["predecessor_ref"]["id"]
    heartbeat = store.resolve_record(project_id, "work_time_coordination_update", heartbeat_id)
    assert heartbeat is not None
    assert heartbeat["sequence_number"] == 1


# --- GitHub Projection ------------------------------------------------------------------------ #


def test_github_projection_the_real_unmodified_production_entrypoint_composes_end_to_end(
    tmp_path: Path,
) -> None:
    store, ctx = _proj_bound(tmp_path)
    project_id = ctx["project_id"]
    project_binding_id = ctx["project_binding_id"]

    evidence = derive_evidence(evidence_helpers.observation_evidence_request())
    evidence_id = evidence["evidence_id"]
    _proj_commit_records(
        store,
        project_id,
        ctx["genesis_state"],
        "TX-ADAPTER-CONFORMANCE-PROJECTION-0001",
        [("observation_evidence", evidence_id, evidence)],
    )
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    human_authority_ref = dict(boot_context.human_authority_ref)

    evidence_subject_ref = {"kind": "observation_evidence", "id": evidence_id}
    evidence_fingerprint = evidence_semantic_fingerprint(evidence)
    grant_ref, grant = _proj_commit_grant(
        store,
        project_id,
        human_authority_ref,
        "TX-ADAPTER-CONFORMANCE-PROJECTION-0002",
        subject_ref=evidence_subject_ref,
        subject_fingerprint=evidence_fingerprint,
        payload_fingerprint=projection_payload_fingerprint(dict(_PROJECTION_PAYLOAD)),
    )
    declaration_ref = _proj_commit_declaration(
        store,
        project_id,
        project_binding_id,
        human_authority_ref,
        grant,
        declared_at="2026-09-14T11:00:00Z",
    )
    adapter = FakeGitHubAdapter()

    def _perform(reporter: ProgressReporter) -> dict[str, Any]:
        return project_to_github(
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            subject_ref=evidence_subject_ref,
            projection_kind="EVIDENCE_ARTIFACT",
            target_repository=_TARGET_REPOSITORY,
            projection_payload=_PROJECTION_PAYLOAD,
            github_authority_ref=human_authority_ref,
            materialized_at="2026-09-14T11:00:02Z",
            adapter=adapter,
            github_projection_grant_refs=[grant_ref],
            github_projection_grant_declaration_refs=[declaration_ref],
            attempt_claim_token="ADAPTER-CONFORMANCE-PROJECTION-ATTEMPT-0001",  # noqa: S106
        )

    open_record, terminal_record, outcome = with_work_time_coordination(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        adapter_kind="GITHUB_PROJECTION",
        work_unit_ref={
            "kind": "github_projection_attempt",
            "id": "WORK-UNIT-ADAPTER-PROJECTION-1",
        },
        estimated_duration_lower_minutes=0,
        estimated_duration_upper_minutes=1,
        estimate_confidence="HIGH",
        major_steps=["project to github"],
        next_progress_update_due_minutes=10,
        variability_factors="none",
        perform=_perform,
        clock=_deterministic_clock(start="2026-09-14T11:00:00Z"),
    )
    assert outcome["reused"] is False
    assert outcome["receipt"].status == "VERIFIED"
    assert adapter.materialize_call_count == 1
    assert open_record["adapter_kind"] == "GITHUB_PROJECTION"
    assert terminal_record["terminal_outcome"] == "COMPLETED"
