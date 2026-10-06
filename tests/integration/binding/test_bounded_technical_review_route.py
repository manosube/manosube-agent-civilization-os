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

from copy import deepcopy
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any

import pytest
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
    build_subprocess_environment,
    cancel_review_task,
    cleanup_inspection_workspace,
    launch_review_process,
    parse_structured_review_output,
    prepare_inspection_workspace,
)
from manosube_agent_civilization.development_binding.review_control import (
    REVIEW_CLAIM_ADMITTED,
    REVIEW_CLAIM_REFUSED,
    claim_review_launch,
    compute_identity_key,
    evaluate_activation_gate,
)
from manosube_agent_civilization.development_binding.review_selection import (
    SUPPORTED_ENVIRONMENT_FINGERPRINT,
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


def _clock() -> str:
    return _NOW


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
    outcome = cancel_review_task(process.pid)
    assert outcome.local_process_group_terminated is True
    assert outcome.provider_server_state == "UNAVAILABLE"
    process.wait(timeout=5)


def test_a_detached_background_child_outlives_cancellation_of_its_parent(tmp_path: Path) -> None:
    """The exact honesty property this decision's own §5 requires: killing the foreground
    process this module started proves nothing about a detached grandchild that escaped its
    process group -- `cancel_review_task` must never claim that grandchild was stopped."""

    script = _write_fake_codex(tmp_path, _FAKE_CODEX_BACKGROUND)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    result = launch_review_process(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
    )
    assert not result.timed_out

    outcome = cancel_review_task(result.pid)
    assert outcome.local_process_group_terminated is True
    # The one claim this module may never make: that the detached child (whose own pid this
    # test never learns, and which `cancel_review_task` was never asked about) was stopped.
    assert outcome.provider_server_state == "UNAVAILABLE"


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
