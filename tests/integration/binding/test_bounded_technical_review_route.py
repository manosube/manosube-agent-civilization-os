"""Decision 0004 (Issue #109), end to end: a Codex technical-review result, produced only by
a controlled local fake executable (never a real Codex CLI invocation --
``REAL_CODEX_MODEL_REQUEST_ALLOWED=false`` for this whole delivery), carried through the real
:mod:`manosube_agent_civilization.development_binding.review_adapter` process-launch boundary,
the real durable :mod:`.review_control` ledger, and the existing, unmodified
``run_independent_verification``/``route_verification_result_to_evidence`` routes -- proving
the full chain this decision's own handoff requires, without ever making a real model service
call, external automated reviewer request, live grant minting, or VPS/downstream operation.

Credential isolation, bounded timeout/output, and process-group-aware cancellation
(including "background survives foreground kill") are proven against real
:mod:`subprocess` processes -- genuine external effects, just never a real Codex CLI one.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import textwrap
import time
from typing import Any

import pytest
import scripts.bounded_technical_review as bounded_review_script
from tests.difference_helpers import PROJECT_ID as DIFFERENCE_FIXTURE_PROJECT_ID
from tests.evidence_helpers import change_free_verification_evidence_request
from tests.fixtures.product_binding import (
    bind_project_kwargs,
    genesis_records,
    human_authority_ref,
    sign_human_grant_declaration,
)
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.authority.identity import verifier_selection_grant_id
from manosube_agent_civilization.binding import bind_project, declare_human_grant
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.development_binding.errors import ReviewAdapterError
from manosube_agent_civilization.development_binding.policy import BOUNDED_REVIEW_NUMERIC_LIMITS
from manosube_agent_civilization.development_binding.review_adapter import (
    build_codex_review_argv,
    build_isolated_argv,
    build_subprocess_environment,
    cancel_review_task,
    check_isolation_capability,
    cleanup_inspection_workspace,
    launch_review_process,
    parse_structured_review_output,
    prepare_inspection_workspace,
    process_identity_token,
)
from manosube_agent_civilization.development_binding.review_control import (
    REVIEW_CLAIM_ADMITTED,
    REVIEW_CLAIM_REFUSED,
    STATUS_ABANDONED_UNSENT,
    STATUS_COMPLETED,
    claim_review_launch,
    compute_identity_key,
    evaluate_activation_gate,
    read_claim,
)
from manosube_agent_civilization.development_binding.review_selection import (
    REVIEW_SELECTION_ADMITTED,
    REVIEW_SELECTION_REFUSED,
    SUPPORTED_ENVIRONMENT_FINGERPRINT,
    authenticate_bounded_review_grant,
)
from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.independent_verification import (
    EvidenceHandoffError,
    VerificationRequirement,
    VerificationResult,
    VerifierSelection,
    route_verification_result_to_evidence,
    run_independent_verification,
)
from manosube_agent_civilization.store import FileStateStore

pytestmark = pytest.mark.integration

_REPO = "manosube/manosube-agent-civilization-os"
_NOW = "2026-10-06T12:00:00Z"


def _write_fake_codex(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_codex.py"
    script.write_text(body, encoding="utf-8")
    return script


_FAKE_CODEX_NORMAL = """
import json, sys
print(json.dumps({
    "review_status": "COMPLETED",
    "findings": [],
    "inspected_paths": sys.argv[1:],
}))
"""

_FAKE_CODEX_ENV_LEAK_PROBE = """
import json, os, sys
leaked = os.environ.get("GITHUB_TOKEN")
print(json.dumps({"review_status": "COMPLETED", "findings": [], "leaked_token": leaked}))
"""

_FAKE_CODEX_WRITE_PROBE = """
import json, sys
target = sys.argv[1]
try:
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("tampered")
    wrote = True
except OSError:
    wrote = False
print(json.dumps({"review_status": "COMPLETED", "findings": [], "wrote_to_inspected_file": wrote}))
"""

_FAKE_CODEX_HANG = """
import time
time.sleep(30)
"""

_FAKE_CODEX_BIG_OUTPUT = """
import sys
sys.stdout.write("x" * (2 * 1024 * 1024))
"""

_FAKE_CODEX_BACKGROUND = """
import subprocess, sys
# A real local background server is a pre-existing, independent process -- it does not
# inherit the launching invocation's own stdout/stderr pipes. DEVNULL + start_new_session
# models that: the detached child never holds this script's own pipe write end open, so the
# foreground launch's own stdout/stderr genuinely reach EOF as soon as *this* process exits,
# exactly as a real background-server-backed CLI invocation's own foreground exit would.
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(10)"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
print("parent exiting; background child", child.pid)
"""

_FAKE_CODEX_BACKGROUND_THEN_WAIT = """
import subprocess, sys, time
child = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(10)"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
print("parent waiting; background child", child.pid)
sys.stdout.flush()
time.sleep(10)
"""


def _clock() -> str:
    return _NOW


#: SR2-F6 correction (PR #112 comment 6021757577): a genuine, non-empty mask is now required
#: whenever ``require_isolation`` is true -- every direct ``launch_review_process`` call in
#: this file masks the real orchestrating user's own home directory, exactly the realistic
#: credential-protection scenario (SSH keys, a real Codex CLI's own config) this delivery's
#: own handoff names, rather than an empty tuple that was never evidence of isolation at all.
_DEFAULT_TEST_MASK_PATHS: tuple[Path, ...] = (Path.home(),)


# --------------------------------------------------------------------------- #
# review_adapter: real subprocess, bounded time/output
# --------------------------------------------------------------------------- #


def test_the_launch_completes_and_the_result_parses_as_structured_json(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    result = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    assert result.exit_code == 0
    assert not result.timed_out
    parsed = parse_structured_review_output(result.stdout)
    assert parsed["review_status"] == "COMPLETED"


def test_output_beyond_the_cap_is_truncated_not_buffered_unbounded(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_BIG_OUTPUT)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    result = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=1024,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    assert result.stdout_truncated
    assert len(result.stdout) == 1024


def test_a_hung_process_group_is_killed_at_the_deadline_not_left_running(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_HANG)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    started = time.monotonic()
    result = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=1,
        max_output_bytes=1024,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    elapsed = time.monotonic() - started
    assert result.timed_out
    assert elapsed < 10, "the process group must actually be killed, not merely abandoned"
    with pytest.raises(ProcessLookupError):
        os.kill(result.pid, 0)


# --------------------------------------------------------------------------- #
# credential isolation -- positive and negative controls
# --------------------------------------------------------------------------- #


def test_a_credential_shaped_allowed_key_is_refused_before_any_process_launches() -> None:
    with pytest.raises(ReviewAdapterError):
        build_subprocess_environment(
            {"PATH": "/usr/bin", "GITHUB_TOKEN": "x"},
            allowed_keys=frozenset({"PATH", "GITHUB_TOKEN"}),
        )


def test_a_secret_present_in_the_orchestrating_environment_never_reaches_the_child(
    tmp_path: Path,
) -> None:
    """Negative control: the orchestrating process genuinely holds a secret-shaped variable;
    the launched subprocess, built through the one sanctioned environment constructor, must
    never observe it -- proven by a fake executable that actively tries to read it back."""

    script = _write_fake_codex(tmp_path, _FAKE_CODEX_ENV_LEAK_PROBE)
    orchestrator_env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "GITHUB_TOKEN": "super-secret-value",
    }
    child_env = build_subprocess_environment(orchestrator_env)
    assert "GITHUB_TOKEN" not in child_env
    result = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=child_env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    parsed = parse_structured_review_output(result.stdout)
    assert parsed["leaked_token"] is None


def test_the_inspection_workspace_is_genuinely_read_only(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    inspected = source_root / "inspected.py"
    inspected.write_text("ORIGINAL CONTENT", encoding="utf-8")
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_WRITE_PROBE)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["inspected.py"])
    try:
        staged = workspace / "inspected.py"
        assert staged.read_text(encoding="utf-8") == "ORIGINAL CONTENT"
        mode = staged.stat().st_mode
        assert not (mode & stat.S_IWUSR), "a staged inspection file must not be writable"

        env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
        result = launch_review_process(
            [sys.executable, str(script), str(staged)],
            cwd=workspace,
            env=env,
            max_seconds=5,
            max_output_bytes=4096,
            clock=_clock,
            mask_paths=_DEFAULT_TEST_MASK_PATHS,
        )
        parsed = parse_structured_review_output(result.stdout)
        if os.geteuid() == 0:
            # A root-owned reviewing process bypasses the read-only file mode entirely --
            # this is a genuine, disclosed limit of chmod-based protection, not something
            # this module can close: the intended deployment (a regular, non-root user)
            # never has this bypass available, and the file-mode assertion above still
            # proves the control is actually set regardless of who is running this suite.
            pytest.skip("effective uid is 0 -- chmod 0o444 cannot block a root-owned writer")
        assert parsed["wrote_to_inspected_file"] is False
        assert staged.read_text(encoding="utf-8") == "ORIGINAL CONTENT"
    finally:
        cleanup_inspection_workspace(workspace)
    assert not workspace.exists()


def test_an_unsafe_permitted_path_is_refused_before_any_copy() -> None:
    with pytest.raises(ReviewAdapterError):
        prepare_inspection_workspace(Path("."), permitted_paths=["../outside.py"])


# --------------------------------------------------------------------------- #
# cancellation: owned process group only, never a shared background server
# --------------------------------------------------------------------------- #


def test_cancellation_terminates_the_owned_process_group(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_HANG)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    import subprocess

    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(script)], cwd=str(tmp_path), env=env, start_new_session=True
    )
    identity = process_identity_token(process.pid)
    assert identity is not None
    outcome = cancel_review_task(pid=process.pid, owned_process_identity=identity)
    assert outcome.ownership_confirmed is True
    assert outcome.local_process_group_terminated is True
    assert outcome.provider_server_state == "UNAVAILABLE"
    process.wait(timeout=5)


def test_a_detached_background_child_outlives_cancellation_of_its_parent(tmp_path: Path) -> None:
    """The exact honesty property this decision's own §5 requires: killing the foreground
    process this module started proves nothing about a detached grandchild that escaped its
    process group -- `cancel_review_task` must never claim that grandchild was stopped.

    Cancellation only ever has something to confirm while the foreground process this module
    itself owns is still alive -- so this spawns the detached grandchild and then keeps its
    own foreground running (unlike `_FAKE_CODEX_BACKGROUND`, which exits immediately) so the
    owned process group genuinely still exists at the moment `cancel_review_task` is called,
    exactly as a real cancellation request racing a still-running review would."""

    script = _write_fake_codex(tmp_path, _FAKE_CODEX_BACKGROUND_THEN_WAIT)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    import subprocess

    process = subprocess.Popen(  # noqa: S603
        [sys.executable, str(script)], cwd=str(tmp_path), env=env, start_new_session=True
    )
    identity = process_identity_token(process.pid)
    assert identity is not None
    time.sleep(0.3)  # let the script spawn its detached grandchild before cancelling
    assert process.poll() is None, "the foreground process must still be running when cancelled"

    outcome = cancel_review_task(pid=process.pid, owned_process_identity=identity)
    assert outcome.ownership_confirmed is True
    assert outcome.local_process_group_terminated is True
    # The one claim this module may never make: that the detached child (whose own pid this
    # test never learns, and which `cancel_review_task` was never asked about) was stopped.
    assert outcome.provider_server_state == "UNAVAILABLE"
    process.wait(timeout=5)


# --------------------------------------------------------------------------- #
# the durable ledger + activation gate, composed the way the script composes them
# --------------------------------------------------------------------------- #


def test_claim_then_activation_gate_never_activates_in_this_delivery(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    identity_key = compute_identity_key(
        repository=_REPO,
        pull_request="#777",
        base_sha="a" * 40,
        head_sha="b" * 40,
        requirement_id="REQ-ROUTE-1",
        input_digest="c" * 64,
    )
    claim = claim_review_launch(
        ledger,
        identity_key=identity_key,
        work_unit_id="WU-ROUTE-1",
        repository=_REPO,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    assert claim["decision"] == REVIEW_CLAIM_ADMITTED

    # Every precondition genuinely satisfied except the one this delivery never sets True.
    evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": False,
    }
    gate = evaluate_activation_gate(evidence)
    assert gate["decision"] == "ACTIVATION_GATE_NOT_ACTIVATED"
    assert "ACTIVATION_NOT_ENABLED" in gate["reason_codes"]

    duplicate = claim_review_launch(
        ledger,
        identity_key=identity_key,
        work_unit_id="WU-ROUTE-1",
        repository=_REPO,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    assert duplicate["decision"] == REVIEW_CLAIM_REFUSED


def test_build_codex_review_argv_never_shell_interpolates() -> None:
    argv = build_codex_review_argv(
        codex_executable="/usr/local/bin/codex",
        workspace=Path("/tmp/workspace"),  # noqa: S108 -- a literal, never executed, string
        prompt_path=Path("/tmp/workspace/prompt.md"),  # noqa: S108
    )
    assert argv[0] == "/usr/local/bin/codex"
    assert "&&" not in " ".join(argv)
    assert ";" not in " ".join(argv)


# --------------------------------------------------------------------------- #
# the genuine Evidence handoff -- a real Codex review result, carried through the existing,
# unmodified route_verification_result_to_evidence (never a Store or bound Project needed,
# exactly as this route's own module docstring states)
# --------------------------------------------------------------------------- #

_DEFAULT_VERIFIER_IDENTITY = {"kind": "bounded_codex_technical_reviewer", "id": "CODEX-ROUTE-0001"}


def test_a_codex_review_result_hands_off_to_a_genuine_evidence_record(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    launch = launch_review_process(
        [sys.executable, str(script), "src/some_reviewed_file.py"],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    codex_result = parse_structured_review_output(launch.stdout)
    assert codex_result["review_status"] == "COMPLETED"

    difference_id = str(
        derive_evidence(change_free_verification_evidence_request())["difference_ref"]["id"]
    )
    verification_result = VerificationResult(
        status="VERIFIED",
        requirement_id="VREQ-I109-ROUTE-0001",
        selection_id="VSEL-I109-ROUTE-0001",
        project_id=DIFFERENCE_FIXTURE_PROJECT_ID,
        target_refs=({"kind": "difference", "id": difference_id},),
        verifier_identity=dict(_DEFAULT_VERIFIER_IDENTITY),
        selection_authority_ref={"kind": "human_authority", "id": "AUTH-I109-ROUTE-0001"},
        verification_boundary={"scope": "repository", "boundary_id": "VB-I109-ROUTE-0001"},
        input_refs=({"kind": "source_snapshot", "id": "SS-I109-ROUTE-0001"},),
        observations={
            "codex_review": codex_result,
            "inspected_paths": codex_result["inspected_paths"],
        },
    )

    evidence_request = change_free_verification_evidence_request(provenance=None)
    evidence = route_verification_result_to_evidence(verification_result, evidence_request)

    assert evidence["target"]["project_id"] == verification_result.project_id
    assert evidence["difference_ref"]["id"] == difference_id
    assert (
        evidence["verification_result_provenance"]["observations"]["codex_review"]["review_status"]
        == "COMPLETED"
    )


def test_route_verification_result_to_evidence_rejects_a_bare_dict_result() -> None:
    with pytest.raises(EvidenceHandoffError):
        route_verification_result_to_evidence(
            {"not": "a VerificationResult"},  # type: ignore[arg-type]
            change_free_verification_evidence_request(),
        )


# --------------------------------------------------------------------------- #
# the full, heavy canonical route -- a real bound Project, a real committed grant and a real
# `declare_human_grant` declaration, Boot/Authority re-verified, wrapping a genuine Codex
# review result as the one real verifier call `run_independent_verification` makes
# --------------------------------------------------------------------------- #


def _grant(project_id: str, authority_ref: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "schema_version": "0.1",
        "verifier_selection_grant_id": "",
        "project_id": project_id,
        "requirement_id": "VREQ-I109-ROUTE-HEAVY-0001",
        "selection_id": "VSEL-I109-ROUTE-HEAVY-0001",
        "verifier_identity": dict(_DEFAULT_VERIFIER_IDENTITY),
        "permitted_boundary": {"scope": "repository", "boundary_id": "VB-I109-ROUTE-HEAVY-0001"},
        "status": "ACTIVE",
        "granted_by": dict(authority_ref),
    }
    fields.update(overrides)
    fields["verifier_selection_grant_id"] = verifier_selection_grant_id(fields)
    return fields


def _grant_ref(grant: dict[str, Any]) -> dict[str, Any]:
    return {"kind": "verifier_selection_grant", "id": grant["verifier_selection_grant_id"]}


@pytest.fixture
def _bound_route(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    tmp_path = tmp_path_factory.mktemp("i109-bounded-review-heavy-route")
    store_root = tmp_path / "backend"
    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    bind_result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    project_id = kwargs["project_id"]
    project_binding_id = bind_result["project_binding_id"]
    genesis_state = bind_result["committed_state"]

    authority_ref = human_authority_ref()
    evidence_id = "EVID-I109-ROUTE-HEAVY-0001"
    grant = _grant(project_id, authority_ref)

    successor = deepcopy(genesis_state)
    successor["state_revision"] = genesis_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = genesis_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": "TX-I109-ROUTE-HEAVY-0001"}
    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": "TX-I109-ROUTE-HEAVY-0001",
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": genesis_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": genesis_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-10-06T10:00:00Z",
    }
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
                {"kind": "observation_evidence", "note": "Issue #109 bounded-review fixture"},
            ),
            ("verifier_selection_grant", grant["verifier_selection_grant_id"], grant),
        ],
    )

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    assert dict(boot_context.human_authority_ref) == authority_ref

    declared_at = "2026-10-06T11:00:00Z"
    declaration_signature = sign_human_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=_grant_ref(grant),
        declared_by=authority_ref,
        requirement_id=grant["requirement_id"],
        selection_id=grant["selection_id"],
        verifier_identity=grant["verifier_identity"],
        permitted_boundary=grant["permitted_boundary"],
        status="ACTIVE",
        declared_at=declared_at,
    )
    declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=_grant_ref(grant),
        status="ACTIVE",
        declared_at=declared_at,
        signature=declaration_signature,
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]

    return {
        "store": store,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "evidence_id": evidence_id,
        "human_authority_ref": dict(boot_context.human_authority_ref),
        "grant": grant,
        "grant_ref": _grant_ref(grant),
        "declaration_ref": {
            "kind": "human_grant_declaration",
            "id": declaration["human_grant_declaration_id"],
        },
    }


def test_the_full_canonical_route_from_a_fake_codex_launch_to_a_real_verification_result(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    launch = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    codex_result = parse_structured_review_output(launch.stdout)

    requirement = VerificationRequirement(
        requirement_id=_bound_route["grant"]["requirement_id"],
        project_id=_bound_route["project_id"],
        target_refs=[{"kind": "observation_evidence", "id": _bound_route["evidence_id"]}],
        verification_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
        required_conditions={"minimum_distinctness": "DISTINCT_LINEAGE"},
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
    )
    selection = VerifierSelection(
        selection_id=_bound_route["grant"]["selection_id"],
        project_id=_bound_route["project_id"],
        requirement_id=_bound_route["grant"]["requirement_id"],
        status="ACTIVE",
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
        verifier_identity=dict(_DEFAULT_VERIFIER_IDENTITY),
        permitted_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
    )

    def verifier(
        *, requirement: VerificationRequirement, selection: VerifierSelection
    ) -> dict[str, Any]:
        return {
            "status": "VERIFIED" if codex_result["review_status"] == "COMPLETED" else "UNAVAILABLE",
            "input_refs": [{"kind": "source_snapshot", "id": "SS-I109-ROUTE-HEAVY-0001"}],
            "observations": {"codex_review": codex_result},
        }

    verifier.verifier_identity = dict(_DEFAULT_VERIFIER_IDENTITY)  # type: ignore[attr-defined]

    result = run_independent_verification(
        _bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verification_requirement=requirement,
        verifier_selection=selection,
        verifier_selection_grant_refs=[_bound_route["grant_ref"]],
        human_grant_declaration_refs=[_bound_route["declaration_ref"]],
        verifier=verifier,
    )

    assert isinstance(result, VerificationResult)
    assert result.status == "VERIFIED"
    assert result.observations["codex_review"]["review_status"] == "COMPLETED"


# --------------------------------------------------------------------------- #
# PR #112 Structural Review Round 1 (comment 6019024445): F1 (authenticated admission) and F2
# (the composed dispatch route), proven end to end against the identical real Boot/Authority/
# Store chain `_bound_route` already builds -- a second, Bounded-Review-Grant-shaped grant
# committed into the same already-booted project, since `_bound_route`'s own grant uses
# `independent_verification`'s own ``{"scope", "boundary_id"}`` permitted_boundary convention
# rather than the ``{"permitted_paths", "permitted_checks"}`` one F1's own ``authenticate_
# bounded_review_grant`` constructs for a Bounded Review Grant.
# --------------------------------------------------------------------------- #

_F1_F2_VERIFIER_IDENTITY = {
    "kind": "bounded_codex_technical_reviewer",
    "id": "codex-session-f1-f2-route-1",
}
_F1_F2_REQUIREMENT_ID = "REQ-I109-F1F2-ROUTE-1"
_F1_F2_WORK_UNIT_ID = "WORK-UNIT-I109-F1F2-ROUTE-1"


def _commit_additional_grant(
    bound_route: dict[str, Any],
    *,
    transaction_id: str,
    requirement_id: str,
    selection_id: str,
    verifier_identity: dict[str, Any],
    permitted_boundary: dict[str, Any],
) -> dict[str, Any]:
    """Commit a second ``verifier_selection_grant`` (plus its own signed declaration) into the
    identical already-booted project ``_bound_route`` built -- reusing its Store/Boot/Binding
    scaffolding rather than re-deriving it, for a grant shaped the way F1's own ``authenticate_
    bounded_review_grant`` actually constructs a Bounded Review Grant's authenticated-admission
    request (``permitted_boundary={"permitted_paths": ..., "permitted_checks": ...}``)."""

    from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

    store = bound_route["store"]
    project_id = bound_route["project_id"]
    project_binding_id = bound_route["project_binding_id"]
    authority_ref = bound_route["human_authority_ref"]

    current_state = store.load_current(project_id)
    grant = _grant(
        project_id,
        authority_ref,
        requirement_id=requirement_id,
        selection_id=selection_id,
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
    )
    successor = deepcopy(current_state)
    successor["state_revision"] = current_state["state_revision"] + 1
    successor["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
    successor["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
    successor["semantic_fingerprint"] = fingerprint_project_state(
        successor, schema_root=SCHEMA_ROOT
    ).as_dict()
    event = {
        "schema_version": "0.1",
        "transaction_id": transaction_id,
        "event_type": "TRANSITION",
        "project_id": project_id,
        "from_revision": current_state["state_revision"],
        "to_revision": successor["state_revision"],
        "before_fingerprint": current_state["semantic_fingerprint"],
        "after_fingerprint": successor["semantic_fingerprint"],
        "after_state": successor,
        "evidence_refs": [],
        "committed_at": "2026-10-06T11:30:00Z",
    }
    store.commit(
        project_id,
        current_state["state_revision"],
        current_state["semantic_fingerprint"],
        successor,
        event,
        records=[("verifier_selection_grant", grant["verifier_selection_grant_id"], grant)],
    )
    grant_ref = _grant_ref(grant)
    declared_at = "2026-10-06T11:45:00Z"
    signature = sign_human_grant_declaration(
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        declared_by=authority_ref,
        requirement_id=grant["requirement_id"],
        selection_id=grant["selection_id"],
        verifier_identity=grant["verifier_identity"],
        permitted_boundary=grant["permitted_boundary"],
        status="ACTIVE",
        declared_at=declared_at,
    )
    declaration = declare_human_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        grant_ref=grant_ref,
        status="ACTIVE",
        declared_at=declared_at,
        signature=signature,
        schema_root=SCHEMA_ROOT,
    )["human_grant_declaration"]
    declaration_ref = {
        "kind": "human_grant_declaration",
        "id": declaration["human_grant_declaration_id"],
    }
    return {"grant": grant, "grant_ref": grant_ref, "declaration_ref": declaration_ref}


def _bounded_review_grant_record(**overrides: Any) -> dict[str, Any]:
    base_receipt = {
        "work_unit_id": _F1_F2_WORK_UNIT_ID,
        "difference_id": "D-I109-F1F2-ROUTE",
        "governing_issue": "#109",
        "adoption_id": "ADOPT_I109_F1F2_ROUTE_1",
        "comment_url": (
            "https://github.com/manosube/manosube-agent-civilization-os"
            "/issues/109#issuecomment-1000000401"
        ),
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "authorized_repository": _REPO,
        "authorized_pull_request": "#109",
        "authorized_base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "authorized_head_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "requirement_id": _F1_F2_REQUIREMENT_ID,
        "implementation_provider": "CLAUDE_CODE",
        "implementation_session_ref": "session-f1-f2-route-1",
        "inspector_provider": "CODEX",
        "inspector_session_ref": _F1_F2_VERIFIER_IDENTITY["id"],
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
        "environment_fingerprint": dict(SUPPORTED_ENVIRONMENT_FINGERPRINT),
        "input_digest": "a" * 64,
        "not_before": "2026-10-06T00:00:00Z",
        "not_after": "2026-10-07T00:00:00Z",
    }
    record: dict[str, Any] = {
        "schema_version": "0.1",
        "work_unit_id": _F1_F2_WORK_UNIT_ID,
        "invoked_work_unit_id": _F1_F2_WORK_UNIT_ID,
        "difference_id": "D-I109-F1F2-ROUTE",
        "governing_issue": "#109",
        "adoption_id": "ADOPT_I109_F1F2_ROUTE_1",
        "comment_url": base_receipt["comment_url"],
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": base_receipt,
        "authorized_repository": _REPO,
        "authorized_pull_request": "#109",
        "authorized_base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "authorized_head_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "requirement_id": _F1_F2_REQUIREMENT_ID,
        "implementation_provider": "CLAUDE_CODE",
        "implementation_session_ref": "session-f1-f2-route-1",
        "inspector_provider": "CODEX",
        "inspector_session_ref": _F1_F2_VERIFIER_IDENTITY["id"],
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
        "environment_fingerprint": dict(SUPPORTED_ENVIRONMENT_FINGERPRINT),
        "input_digest": "a" * 64,
        "not_before": "2026-10-06T00:00:00Z",
        "not_after": "2026-10-07T00:00:00Z",
        "current_repository": _REPO,
        "current_pull_request": "#109",
        "current_base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "current_head_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "revoked": False,
    }
    record.update(overrides)
    return record


def test_f1_authenticate_bounded_review_grant_admits_a_real_signed_kernel_grant(
    _bound_route: dict[str, Any],
) -> None:
    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-F1-POSITIVE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    decision = authenticate_bounded_review_grant(
        _bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
    )
    assert decision["decision"] == REVIEW_SELECTION_ADMITTED
    assert decision["grant_ref"] == committed["grant_ref"]


def test_f1_authenticate_bounded_review_grant_refuses_a_caller_fabricated_grant(
    _bound_route: dict[str, Any],
) -> None:
    """The exact gap F1 closes: a caller supplying no genuine Store-resolved grant at all --
    however well-formed its own request otherwise is -- is never authenticated."""

    decision = authenticate_bounded_review_grant(
        _bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary={
            "permitted_paths": ["reviewed_f1_f2.py"],
            "permitted_checks": ["CORRECTNESS"],
        },
        verifier_selection_grant_refs=[],
        human_grant_declaration_refs=[],
    )
    assert decision["decision"] == REVIEW_SELECTION_REFUSED
    assert "GRANT_MISSING" in decision["decision_reason_codes"]


def test_f2_compose_bounded_technical_review_dispatch_completes_against_a_real_authenticated_grant(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-F2-POSITIVE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,  # test-only, never reachable via the CLI -- see the
        # module docstring of scripts/bounded_technical_review.py.
    }

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    assert result["stage"] == "complete", result
    assert result["classification"] == "VERIFIED", result

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_COMPLETED


def test_f2_compose_bounded_technical_review_dispatch_releases_the_slot_on_a_digest_mismatch(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """F5's own ordering/evidence discipline, exercised through the full F2 composed route: a
    staged input that does not match the grant's own declared ``input_digest`` is refused
    *after* claiming -- so the slot is released (``ABANDONED_UNSENT``), never recorded as a
    false outcome, and the one external-effect launch is never attempted."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-F2-NEGATIVE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest="f" * 64)
    grant["api_read_back_receipt"]["input_digest"] = "f" * 64

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    assert result["stage"] == "input-digest-verify", result

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_ABANDONED_UNSENT
    assert claim["dispatch_attempts"] == 0


# --------------------------------------------------------------------------- #
# PR #112 Structural Review Round 2 (comment 6021757577): permanent regression tests proving
# each SR2 finding's own exact reproduction is now refused/fixed, through the composed route.
# --------------------------------------------------------------------------- #


def test_sr2_f1_a_pre_send_live_recheck_refusal_releases_the_slot_unsent(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """The exact SR2-F1 gap: before this correction, nothing re-checked activation/admission
    between the top-of-call admission check and the one external-effect send -- a caller's own
    static ``activation_evidence`` string, read once, stood in for a live check forever. Here,
    *activation_evidence_provider* reports the activation gate as no longer active at the
    pre-send checkpoint even though the top-of-call *activation_evidence* itself still reports
    active -- simulating activation being revoked in the window between admission and send.
    The claim is still ``CLAIMED`` at that checkpoint, so it is released honestly as unsent,
    never recorded as a false outcome, and the one external-effect launch is never attempted."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F1-PRE-SEND",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest

    ledger_path = tmp_path / "ledger.json"
    live_activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }
    revoked_activation_evidence = {**live_activation_evidence, "activation_enabled": False}

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=live_activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        activation_evidence_provider=lambda: revoked_activation_evidence,
    )
    assert result["stage"] == "live-recheck-pre-send", result
    assert result["refusal"]["reason"] == "ACTIVATION_NO_LONGER_ACTIVE", result

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_ABANDONED_UNSENT
    assert claim["dispatch_attempts"] == 0


def test_sr2_f1_a_changed_grant_envelope_is_refused_by_the_live_recheck(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """*grant_provider* lets a caller re-fetch the grant fresh at each live-recheck checkpoint;
    a grant whose own authorized envelope (here, ``authorized_head_sha``) no longer matches the
    snapshot this call started from is refused as ``GRANT_ENVELOPE_CHANGED`` -- never silently
    trusted merely because it was read once, at the top of the call."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F1-ENVELOPE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest
    changed_grant = {**grant, "authorized_head_sha": "f" * 40}

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        grant_provider=lambda: changed_grant,
    )
    assert result["stage"] == "live-recheck-pre-send", result
    assert result["refusal"]["reason"] == "GRANT_ENVELOPE_CHANGED", result
    assert result["refusal"]["field"] == "authorized_head_sha", result


def test_sr2_f2_an_oversize_staged_input_is_refused_before_any_launch(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR2-F2: the staged inspection input itself is now bounded (distinct from the launched
    process's own captured-output ceiling) -- a staged file larger than *max_input_bytes* is
    refused, and the slot released unsent, before any process is ever started."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F2-SIZE-CAP",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        max_input_bytes=1,
    )
    assert result["stage"] == "input-size-cap", result
    assert result["staged_bytes"] > 1

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_ABANDONED_UNSENT


@pytest.mark.parametrize(
    "overrides,expected_classification",
    [
        ({"stdout_truncated": True}, "INSUFFICIENT"),
        ({"stderr_truncated": True}, "INSUFFICIENT"),
    ],
    ids=["stdout-truncated", "stderr-truncated"],
)
def test_sr2_f2_truncated_captured_output_is_never_trusted_as_a_complete_signal(
    overrides: dict[str, Any], expected_classification: str
) -> None:
    """SR2-F2: a truncated capture could be silently missing exactly the ``findings``/
    ``inspected_paths`` entry that would have changed this classification -- reported
    INSUFFICIENT, never VERIFIED/FAILED on a partial read, however clean ``review_status``
    itself otherwise looks."""

    stdout = json.dumps(
        {"review_status": "COMPLETED", "findings": [], "inspected_paths": ["x.py"]}
    ).encode("utf-8")
    base = {
        "exit_code": 0,
        "stdout": stdout,
        "stderr": b"",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "timed_out": False,
        "pid": 1,
        "process_identity": "1:0",
        "started_at": _NOW,
        "ended_at": _NOW,
    }
    launch_result = argparse.Namespace(**{**base, **overrides})
    classification, _codex_result = bounded_review_script.classify_review_result(
        launch_result, permitted_paths=["x.py"]
    )
    assert classification == expected_classification


def test_sr2_f2_a_completed_result_with_a_blocking_finding_is_failed_not_verified() -> None:
    """The exact SR2-F2 reproduction: a result carrying a P1/blocking finding, with
    ``review_status`` still reporting ``COMPLETED``, was previously reported VERIFIED because
    the classifier never read ``findings``' own severities at all."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [{"check": "ROOT_CAUSE", "severity": "P1"}],
            "inspected_paths": ["x.py"],
        }
    ).encode("utf-8")
    launch_result = argparse.Namespace(
        exit_code=0,
        stdout=stdout,
        stderr=b"",
        stdout_truncated=False,
        stderr_truncated=False,
        timed_out=False,
        pid=1,
        process_identity="1:0",
        started_at=_NOW,
        ended_at=_NOW,
    )
    classification, _codex_result = bounded_review_script.classify_review_result(
        launch_result, permitted_paths=["x.py"]
    )
    assert classification == "FAILED"


def test_sr2_f2_an_inspected_path_outside_the_permitted_scope_is_insufficient_not_verified() -> (
    None
):
    """SR2-F2: coverage was previously checked in one direction only (``permitted_paths`` ⊆
    ``inspected_paths``) -- a result naming an inspected path *outside* the grant's own
    permitted scope is over-scope, never silently accepted merely because the permitted set
    was also covered."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [],
            "inspected_paths": ["x.py", "outside_scope.py"],
        }
    ).encode("utf-8")
    launch_result = argparse.Namespace(
        exit_code=0,
        stdout=stdout,
        stderr=b"",
        stdout_truncated=False,
        stderr_truncated=False,
        timed_out=False,
        pid=1,
        process_identity="1:0",
        started_at=_NOW,
        ended_at=_NOW,
    )
    classification, _codex_result = bounded_review_script.classify_review_result(
        launch_result, permitted_paths=["x.py"]
    )
    assert classification == "INSUFFICIENT"


def _evidence_request_for_project(project_id: str) -> dict[str, Any]:
    """``change_free_verification_evidence_request``'s own fixture helpers hardcode
    ``tests.difference_helpers.PROJECT_ID`` ("PRJ-0001") at every nested ``project_id`` --
    there is no override hook. :func:`route_verification_result_to_evidence` itself requires
    the derived Evidence record's ``target.project_id`` to equal the real
    ``VerificationResult.project_id`` it was handed (never a mismatched Evidence record), so a
    caller whose Bounded Review Grant is bound to a different real project must rewrite every
    one of those nested occurrences to match -- exactly what this helper does."""

    request = change_free_verification_evidence_request(provenance=None)

    def _rewrite(obj: Any) -> None:
        if isinstance(obj, dict):
            if "project_id" in obj:
                obj["project_id"] = project_id
            for value in obj.values():
                _rewrite(value)
        elif isinstance(obj, list):
            for item in obj:
                _rewrite(item)

    _rewrite(request)
    return request


def test_sr2_f2_the_composed_route_performs_a_real_evidence_handoff_when_asked(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR2-F2: *evidence_handoff*, when given, performs the real ``run_independent_
    verification``/``route_verification_result_to_evidence`` chain itself, inside the shared
    composed route -- rather than leaving every caller to hand-assemble the identical sequence
    this delivery's own earlier tests previously had to do by hand."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F2-EVIDENCE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    # SR2-F2: the Evidence-handoff's own VerifierSelection is authorized through
    # ``_bound_route``'s own already-committed grant/declaration -- a *different* grant from
    # the Bounded Review admission's own ``committed`` above. A real Bounded Review Grant's own
    # ``{"permitted_paths": [...], "permitted_checks": [...]}`` boundary is never JSON-
    # canonicalizable once it round-trips through a VerifierSelection's own tuple-freezing (see
    # ``_hand_off_to_evidence``'s own docstring), so the handoff's own admission must go through
    # a list-free-boundary grant instead, exactly as this delivery's earlier, by-hand evidence-
    # handoff test already does.
    requirement = VerificationRequirement(
        requirement_id=_bound_route["grant"]["requirement_id"],
        project_id=_bound_route["project_id"],
        target_refs=[{"kind": "observation_evidence", "id": _bound_route["evidence_id"]}],
        verification_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
        required_conditions={"minimum_distinctness": "DISTINCT_LINEAGE"},
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
    )
    selection = VerifierSelection(
        selection_id=_bound_route["grant"]["selection_id"],
        project_id=_bound_route["project_id"],
        requirement_id=_bound_route["grant"]["requirement_id"],
        status="ACTIVE",
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
        verifier_identity=dict(_DEFAULT_VERIFIER_IDENTITY),
        permitted_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
    )

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        evidence_handoff={
            "verification_requirement": requirement,
            "verifier_selection": selection,
            "evidence_request": _evidence_request_for_project(_bound_route["project_id"]),
            "verifier_selection_grant_refs": [_bound_route["grant_ref"]],
            "human_grant_declaration_refs": [_bound_route["declaration_ref"]],
        },
    )
    assert result["stage"] == "complete", result
    assert result["classification"] == "VERIFIED", result
    assert "evidence" in result, result
    assert result["evidence"]["target"]["project_id"] == _bound_route["project_id"]


def test_sr2_f4_a_successful_dispatch_attaches_the_real_pid_before_collection(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR2-F4: the real pid/process identity is attached (``confirm_dispatch_sent``) the
    instant the process starts, before the collection wait ever begins -- proven here by
    reading the ledger claim after a successful run and confirming it carries the real pid the
    launch result itself reports, never ``None``."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")
    codex_script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    permitted_boundary = {
        "permitted_paths": ["reviewed_f1_f2.py"],
        "permitted_checks": ["CORRECTNESS"],
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F4-PID",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest

    ledger_path = tmp_path / "ledger.json"
    activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        build_argv=lambda workspace: [sys.executable, str(codex_script), "reviewed_f1_f2.py"],
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
    )
    assert result["stage"] == "complete", result

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["pid"] == result["launch_result"]["pid"]
    assert claim["pid"] is not None
    assert claim["process_identity"] is not None


def test_sr2_f5_cancellation_refuses_an_unrelated_processs_own_real_pid_and_identity(
    tmp_path: Path,
) -> None:
    """The exact SR2-F5 reproduction (PR #112 comment 6021757577): a harmless subprocess
    started entirely outside this delivery's own ledger/adapter, whose own real
    ``process_identity_token`` the caller reads directly, is refused -- never treated as
    ownership merely because its pid/identity happen to be genuine and self-consistent."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR2-F5",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR2-F5",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True
    )
    unrelated_process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True
    )
    try:
        owned_identity = process_identity_token(owned_process.pid)
        assert owned_identity is not None
        bounded_review_script.record_dispatch_attempt(
            ledger_path, identity_key, repository=repository, acknowledged=False
        )
        bounded_review_script.confirm_dispatch_sent(
            ledger_path,
            identity_key,
            repository=repository,
            pid=owned_process.pid,
            process_identity=owned_identity,
        )

        unrelated_identity = process_identity_token(unrelated_process.pid)
        assert unrelated_identity is not None

        refusal = bounded_review_script.compose_bounded_technical_review_cancellation(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            pid=unrelated_process.pid,
            owned_process_identity=unrelated_identity,
        )
        assert refusal["decision"] == "CANCELLATION_REFUSED", refusal
        assert refusal["reason"] == "PID_OR_IDENTITY_NOT_BOUND_TO_THIS_CLAIM", refusal
        # The unrelated process was never touched.
        assert unrelated_process.poll() is None

        confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
        )
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED", confirmed
        assert confirmed["local_process_group_terminated"] is True

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_FAILED
        assert (
            claim["resolution_kind"] == bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION
        )
        assert claim["result_digest"] is None
    finally:
        for process in (owned_process, unrelated_process):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


def test_sr2_f6_a_real_launched_namespace_blocks_remount_unmount_and_network(
    tmp_path: Path,
) -> None:
    """The exact SR2-F6 reproduction scenarios (PR #112 comment 6021757577), proven against a
    genuinely launched namespace -- not merely review_adapter's own internal capability probe:
    a namespace-"root" child cannot remount its own masked workspace read-write, cannot unmount
    it, and has no network reachability at all."""

    capability = check_isolation_capability()
    if not capability.available:
        pytest.skip(f"isolation unavailable in this environment: {capability.reason}")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "staged.txt").write_text("staged\n", encoding="utf-8")

    probe_script = tmp_path / "probe.py"
    probe_script.write_text(
        textwrap.dedent(
            """
            import json, socket, subprocess, sys
            workspace = sys.argv[1]
            results = {}
            try:
                subprocess.run(
                    ["mount", "-o", "remount,rw,bind", workspace],
                    capture_output=True,
                )
                with open(workspace + "/write_probe.txt", "w", encoding="utf-8") as handle:
                    handle.write("tampered")
                results["workspace_write_succeeded"] = True
            except OSError:
                results["workspace_write_succeeded"] = False
            unmount = subprocess.run(["umount", workspace], capture_output=True)
            results["unmount_succeeded"] = unmount.returncode == 0
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect(("8.8.8.8", 53))
                results["network_reachable"] = True
            except OSError:
                results["network_reachable"] = False
            print(json.dumps(results))
            """
        ),
        encoding="utf-8",
    )

    argv = build_isolated_argv(
        [sys.executable, str(probe_script), str(workspace)],
        mask_paths=(),
        workspace_path=workspace,
    )
    completed = subprocess.run(  # noqa: S603 -- argv is a literal list this test built itself
        argv, capture_output=True, text=True, timeout=30
    )
    results = json.loads(completed.stdout.strip().splitlines()[-1])
    assert results["workspace_write_succeeded"] is False, results
    assert results["unmount_succeeded"] is False, results
    assert results["network_reachable"] is False, results
    # The real launch's own masked workspace is untouched by the child's own attempt.
    assert not (workspace / "write_probe.txt").exists()


def test_f5_cmd_dispatch_cli_never_claims_even_when_the_grant_is_admitted(
    tmp_path: Path,
) -> None:
    """F5 correction regression: the CLI's own ``dispatch`` subcommand checks the activation
    gate *before* any claim is ever attempted, so a disabled delivery (every CLI invocation, in
    this delivery) makes zero ledger writes -- never reserving the repository's one
    concurrency slot or a day's own launch budget merely to then discover it was always going
    to be refused."""

    grant = _bounded_review_grant_record()
    grant_path = tmp_path / "grant.json"
    grant_path.write_text(json.dumps(grant), encoding="utf-8")
    ledger_path = tmp_path / "ledger.json"

    args = argparse.Namespace(
        grant_file=grant_path,
        ledger_file=ledger_path,
        now=_NOW,
        auth_confirmed=True,
        cli_version=SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        model=SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        allowance_confirmed_adequate=True,
        auto_recharge_verified_disabled=True,
        native_github_dedup_disposition="DISABLED",
    )
    exit_code = bounded_review_script.cmd_dispatch(args, io.StringIO())
    assert exit_code == 1
    assert not ledger_path.exists()


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622):
# zero Store/Boot/Authority needed -- this composed route never calls them.
# --------------------------------------------------------------------------- #


def _native_evidence(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "provider": "CODEX",
        "repository": _REPO,
        "pull_request": "#109",
        "review_id": "NATIVE-REVIEW-ROUTE-1",
        "reviewed_commit_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "inspected_base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "review_state": "APPROVED",
        "submitted_at": "2026-10-06T10:30:00Z",
        "inspected_paths": ["reviewed_native.py"],
        "findings": [],
    }
    base.update(overrides)
    return base


def _native_reuse_grant() -> dict[str, Any]:
    grant = _bounded_review_grant_record(permitted_paths=["reviewed_native.py"])
    grant["api_read_back_receipt"]["permitted_paths"] = ["reviewed_native.py"]
    return grant


def test_native_reuse_a_relevant_approved_review_is_verified_and_not_deduplicated(
    tmp_path: Path,
) -> None:
    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        native_evidence=_native_evidence(),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "VERIFIED"
    assert result["deduplicated"] is False


def test_native_reuse_the_identical_review_is_deduplicated_on_a_second_import(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    grant = _native_reuse_grant()
    first = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant, now=_NOW, ledger_path=ledger_path, native_evidence=_native_evidence()
    )
    second = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant, now=_NOW, ledger_path=ledger_path, native_evidence=_native_evidence()
    )
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert second["classification"] == first["classification"]
    assert second["content_address"] == first["content_address"]


def test_native_reuse_sr2_f3_a_changed_review_state_on_the_same_review_id_is_not_stale_cached(
    tmp_path: Path,
) -> None:
    """The exact SR2-F3 reproduction (PR #112 comment 6021757577): a native review that
    transitions ``APPROVED`` -> ``CHANGES_REQUESTED`` with new findings, on the *identical*
    ``review_id``, must never be returned as the earlier, now-superseded ``VERIFIED``
    classification merely because its ``review_id`` was already imported once."""

    ledger_path = tmp_path / "ledger.json"
    grant = _native_reuse_grant()
    first = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant, now=_NOW, ledger_path=ledger_path, native_evidence=_native_evidence()
    )
    second = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        native_evidence=_native_evidence(
            review_state="CHANGES_REQUESTED",
            findings=[{"check": "ROOT_CAUSE", "severity": "P1"}],
        ),
    )
    assert first["classification"] == "VERIFIED"
    assert second["deduplicated"] is False
    assert second["classification"] == "FAILED"
    assert second["content_address"] != first["content_address"]


@pytest.mark.parametrize(
    "overrides,expected_reason",
    [
        ({"reviewed_commit_sha": None}, "NATIVE_REVIEWED_BASE_UNKNOWN"),
        (
            {"reviewed_commit_sha": "b2c3d4e5f60718293a4b5c6d7e8f901122334455"},
            "NATIVE_REVIEWED_BASE_STALE",
        ),
        ({"inspected_base_sha": None}, "NATIVE_INSPECTED_BASE_UNKNOWN"),
        (
            {"inspected_base_sha": "b2c3d4e5f60718293a4b5c6d7e8f901122334455"},
            "NATIVE_INSPECTED_BASE_STALE",
        ),
        ({"repository": "someone/else"}, "NATIVE_REPOSITORY_MISMATCH"),
        ({"pull_request": "#999"}, "NATIVE_PULL_REQUEST_MISMATCH"),
        ({"inspected_paths": []}, "NATIVE_COVERAGE_INSUFFICIENT_FOR_GRANT_SCOPE"),
    ],
    ids=[
        "base-unknown-never-fabricated",
        "base-stale-distinct-from-unknown",
        "inspected-base-unknown-never-fabricated",
        "inspected-base-stale-distinct-from-unknown",
        "repository-mismatch",
        "pull-request-mismatch",
        "coverage-insufficient",
    ],
)
def test_native_reuse_an_irrelevant_review_is_refused_before_any_classification(
    tmp_path: Path, overrides: dict[str, Any], expected_reason: str
) -> None:
    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        native_evidence=_native_evidence(**overrides),
    )
    assert result["stage"] == "native-relevance"
    assert expected_reason in result["decision"]["decision_reason_codes"]


def test_native_reuse_a_commented_review_with_no_findings_is_not_auto_verified(
    tmp_path: Path,
) -> None:
    """The design supplement's own explicit requirement: absence of findings is never itself
    VERIFIED -- only an affirmative ``APPROVED`` disposition is."""

    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        native_evidence=_native_evidence(review_state="COMMENTED"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "INSUFFICIENT"


def test_native_reuse_a_still_running_review_is_unavailable_and_triggers_no_local_launch(
    tmp_path: Path,
) -> None:
    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        native_evidence=_native_evidence(review_state="PENDING"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "UNAVAILABLE"


def test_native_reuse_a_changes_requested_review_is_failed(tmp_path: Path) -> None:
    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        native_evidence=_native_evidence(review_state="CHANGES_REQUESTED"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "FAILED"


def test_native_reuse_unreadable_evidence_raises_rather_than_silently_proceeding(
    tmp_path: Path,
) -> None:
    with pytest.raises(ReviewAdapterError):
        bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
            grant=_native_reuse_grant(),
            now=_NOW,
            ledger_path=tmp_path / "ledger.json",
            native_evidence={"not": "the right shape"},
        )


def test_native_reuse_never_claims_a_local_concurrency_slot_or_daily_budget(
    tmp_path: Path,
) -> None:
    """Zero local launch reservation (the design supplement's own requirement): the ledger's
    own ``claims``/``jst_day_counts``/``active_lock`` stay completely empty after a native
    import -- only ``native_imports`` is ever written by this route."""

    ledger_path = tmp_path / "ledger.json"
    bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=ledger_path,
        native_evidence=_native_evidence(),
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["claims"] == {}
    assert ledger["jst_day_counts"] == {}
    assert ledger["active_lock"] is None
    assert len(ledger["native_imports"]) == 1
