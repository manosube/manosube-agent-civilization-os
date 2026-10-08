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
from collections.abc import Mapping, Sequence
from copy import deepcopy
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
import tempfile
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
    LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON,
    build_codex_review_argv,
    build_isolated_argv,
    build_subprocess_environment,
    cancel_review_task,
    check_isolation_capability,
    cleanup_inspection_workspace,
    collect_review_process_result,
    default_sensitive_mask_roots,
    fetch_trusted_live_review_state,
    fetch_trusted_native_review_evidence,
    launch_review_process,
    parse_structured_review_output,
    prepare_inspection_workspace,
    process_identity_token,
    require_authenticated_review_launch_admission,
    spawn_review_process,
    validate_native_review_evidence,
    validate_review_launch_preconditions,
)
from manosube_agent_civilization.development_binding.review_control import (
    REVIEW_CLAIM_ADMITTED,
    REVIEW_CLAIM_REFUSED,
    STATUS_ABANDONED_UNSENT,
    STATUS_CLAIMED,
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
    canonical_list_digest,
    compute_launch_envelope_digest,
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

#: SR9-F1 correction (PR #112 comment 6053084718): the former
#: ``mint_review_launch_admission_for_controlled_mechanics_test``/``spawn_review_process_for_
#: controlled_mechanics_test``/``launch_review_process_for_controlled_mechanics_test`` fixtures
#: lived in ``review_adapter.py`` itself -- still shipped in the installed wheel, still
#: reachable with the exact SR6-F1/SR7-F1/SR8-F1 hand-typed-decision reproduction under their
#: new names. "Calling it a fixture does not remove the shipped effect." The identical
#: ceiling/mask-coverage/isolation-capability mechanics those functions implemented now live
#: only here -- a test-local module, never imported by, or shipped inside,
#: ``manosube_agent_civilization``/``scripts``. Nothing below this point is a production
#: capability; it exists solely so this delivery's own tests can still exercise the real
#: ``subprocess.Popen``/``build_isolated_argv`` mechanics for a controlled, harmless local
#: fake executable.
_TEST_ONLY_ADMISSION_TOKENS: dict[str, str] = {}


def _test_only_operation_fingerprint(
    *, argv: Sequence[str], cwd: Path, mask_paths: Sequence[Path], require_isolation: bool
) -> str:
    payload = json.dumps(
        {
            "argv": list(argv),
            "cwd": str(cwd),
            "mask_paths": sorted(str(path) for path in mask_paths),
            "require_isolation": require_isolation,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _test_only_path_is_masked(root: Path, mask_paths: Sequence[Path]) -> bool:
    resolved_root = root.resolve()
    for masked in mask_paths:
        resolved_masked = masked.resolve()
        if resolved_root == resolved_masked or resolved_root.is_relative_to(resolved_masked):
            return True
    return False


def mint_review_launch_admission_for_test_only_mechanics(
    *,
    argv: Sequence[str],
    cwd: Path,
    max_seconds: int,
    max_output_bytes: int,
    mask_paths: Sequence[Path],
    require_isolation: bool,
    authentication_decision: Mapping[str, Any],
    claim_decision: Mapping[str, Any],
    required_mask_roots: Sequence[Path] = (),
) -> str:
    """Test-local-only stand-in for the mechanics
    :func:`~manosube_agent_civilization.development_binding.review_adapter.
    validate_review_launch_preconditions` genuinely enforced before SR8-F1/SR9-F1 -- never
    shipped in, or imported from, any production package. Proves this delivery's own ceiling/
    mask-coverage/isolation-capability checks directly, without claiming local review
    process launch is an available production capability, which it is not."""

    if authentication_decision.get("decision") != REVIEW_SELECTION_ADMITTED:
        raise ReviewAdapterError(
            "authentication_decision does not report REVIEW_SELECTION_ADMITTED -- test-only "
            f"mechanics refuse without a real-shaped authenticated admission: "
            f"{authentication_decision!r}"
        )
    if claim_decision.get("decision") != REVIEW_CLAIM_ADMITTED:
        raise ReviewAdapterError(
            "claim_decision does not report REVIEW_CLAIM_ADMITTED -- test-only mechanics "
            f"refuse without a real-shaped claim decision: {claim_decision!r}"
        )
    if max_seconds > BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"]:
        raise ReviewAdapterError(
            f"max_seconds {max_seconds} exceeds the ratified ceiling "
            f"{BOUNDED_REVIEW_NUMERIC_LIMITS['max_process_seconds']}"
        )
    if max_output_bytes > BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"]:
        raise ReviewAdapterError(
            f"max_output_bytes {max_output_bytes} exceeds the ratified ceiling "
            f"{BOUNDED_REVIEW_NUMERIC_LIMITS['max_result_bytes']}"
        )
    if require_isolation:
        if not mask_paths:
            raise ReviewAdapterError(
                "require_isolation is true but mask_paths is empty -- refusing rather than "
                "launching under an isolation label with nothing masked"
            )
        if not required_mask_roots:
            raise ReviewAdapterError(
                "require_isolation is true but required_mask_roots is empty -- a caller "
                "must explicitly declare at least one root mask_paths is relied on to cover"
            )
        uncovered_roots = [
            str(root)
            for root in required_mask_roots
            if not _test_only_path_is_masked(root, mask_paths)
        ]
        if uncovered_roots:
            raise ReviewAdapterError(
                "require_isolation is true but mask_paths does not cover every required "
                f"root: {uncovered_roots!r}"
            )
        capability = check_isolation_capability()
        if not capability.available:
            raise ReviewAdapterError(
                "genuine filesystem/network isolation is unavailable in this environment "
                f"({capability.reason})"
            )

    token = secrets.token_hex(32)
    _TEST_ONLY_ADMISSION_TOKENS[token] = _test_only_operation_fingerprint(
        argv=argv, cwd=cwd, mask_paths=mask_paths, require_isolation=require_isolation
    )
    return token


def spawn_review_process_for_test_only_mechanics(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    admission_token: str,
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
) -> subprocess.Popen[bytes]:
    """Test-local-only stand-in for the mechanics
    :func:`~manosube_agent_civilization.development_binding.review_adapter.
    spawn_review_process` genuinely enforced before SR8-F1/SR9-F1 -- never shipped in, or
    imported from, any production package. Only :func:`mint_review_launch_admission_for_
    test_only_mechanics` can ever mint a token this function accepts."""

    expected_fingerprint = _TEST_ONLY_ADMISSION_TOKENS.get(admission_token)
    if expected_fingerprint is None:
        raise ReviewAdapterError(
            "admission_token is not a currently valid token from "
            "mint_review_launch_admission_for_test_only_mechanics"
        )
    actual_fingerprint = _test_only_operation_fingerprint(
        argv=argv, cwd=cwd, mask_paths=mask_paths, require_isolation=require_isolation
    )
    if actual_fingerprint != expected_fingerprint:
        raise ReviewAdapterError(
            "admission_token was validated for a different argv/cwd/mask_paths/"
            "require_isolation configuration"
        )
    del _TEST_ONLY_ADMISSION_TOKENS[admission_token]

    if require_isolation:
        effective_argv = build_isolated_argv(list(argv), mask_paths=mask_paths, workspace_path=cwd)
    else:
        effective_argv = list(argv)

    return subprocess.Popen(  # noqa: S603 -- effective_argv is a literal list, never shell-interpreted
        effective_argv,
        cwd=str(cwd),
        env=dict(env),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


def launch_review_process_for_test_only_mechanics(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    max_seconds: int,
    max_output_bytes: int,
    clock: Any,
    authentication_decision: Mapping[str, Any],
    claim_decision: Mapping[str, Any],
    mask_paths: Sequence[Path] = (),
    require_isolation: bool = True,
    required_mask_roots: Sequence[Path] = (),
) -> Any:
    """Test-local-only composition of the two mechanics stand-ins above plus the real,
    production :func:`~manosube_agent_civilization.development_binding.review_adapter.
    collect_review_process_result` -- mirroring the former
    ``launch_review_process_for_controlled_mechanics_test`` convenience wrapper, now defined
    only here."""

    admission_token = mint_review_launch_admission_for_test_only_mechanics(
        argv=argv,
        cwd=cwd,
        max_seconds=max_seconds,
        max_output_bytes=max_output_bytes,
        mask_paths=mask_paths,
        require_isolation=require_isolation,
        required_mask_roots=required_mask_roots,
        authentication_decision=authentication_decision,
        claim_decision=claim_decision,
    )
    started_at = clock()
    process = spawn_review_process_for_test_only_mechanics(
        argv,
        cwd=cwd,
        env=env,
        admission_token=admission_token,
        mask_paths=mask_paths,
        require_isolation=require_isolation,
    )
    return collect_review_process_result(
        process,
        max_seconds=max_seconds,
        max_output_bytes=max_output_bytes,
        clock=clock,
        started_at=started_at,
    )


#: SR6-F1 correction (PR #112 comment 6036263982): the two real Decision shapes
#: ``validate_review_launch_preconditions``/``launch_review_process`` now require. For a test
#: exercising only the generic primitive's own mechanics (never claiming genuine authority),
#: these fixed, well-shaped "admitted" dicts are this file's own stand-in; a test exercising
#: the real composed route instead threads through that route's own genuinely-computed
#: decisions, unchanged.
_GENERIC_TEST_AUTHENTICATION_DECISION = {"decision": REVIEW_SELECTION_ADMITTED}
_GENERIC_TEST_CLAIM_DECISION = {"decision": REVIEW_CLAIM_ADMITTED}


def _write_fake_codex(tmp_path: Path, body: str) -> Path:
    script = tmp_path / "fake_codex.py"
    script.write_text(body, encoding="utf-8")
    return script


#: SR4-F2 correction (PR #112 comment 6032479337): this fake review process now self-reports
#: ``observed_input_digest`` -- computed over its own working directory the identical way
#: ``digest_inspection_input`` computes it -- so a result's own claim to have reviewed
#: something is genuinely correlated to the staged input it actually ran against, never a
#: bare, context-free assertion.
_FAKE_CODEX_NORMAL = """
import hashlib, json, sys
from pathlib import Path
workspace = Path(".")
hasher = hashlib.sha256()
for rel in sorted(str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()):
    hasher.update(rel.encode("utf-8"))
    hasher.update(b"\\0")
    hasher.update((workspace / rel).read_bytes())
    hasher.update(b"\\0")
print(json.dumps({
    "review_status": "COMPLETED",
    "findings": [
        {"check": "CORRECTNESS", "status": "PASS", "procedure": "static read of every staged file"}
    ],
    "inspected_paths": sys.argv[1:],
    "observed_input_digest": hasher.hexdigest(),
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

#: The one fixed sha every ``_bounded_review_grant_record`` fixture in this file uses for both
#: ``authorized_base_sha``/``authorized_head_sha`` and their own ``current_*`` counterparts.
_LIVE_REVIEW_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344"

#: A fixed, arbitrary 64-char hex digest for ``classify_review_result``'s own unit-level
#: tests below (SR4-F2) -- these never run a real staged workspace, so there is no genuine
#: ``digest_inspection_input`` value to match; the test's own ``expected_input_digest`` and the
#: hand-built structured output's own ``observed_input_digest`` are simply set equal.
_TEST_INPUT_DIGEST = "d" * 64

#: SR5-F2 correction (PR #112 comment 6034603745): arbitrary, fixed values for
#: ``classify_review_result``'s own new *identity_key*/*requirement_id*/*inspector_identity*
#: parameters in its unit-level tests below -- these are the trusted caller's own already-known
#: facts about the launch, never asserted by the reviewed subprocess, so there is nothing for
#: these unit tests to correlate them against beyond passing them through consistently.
_TEST_IDENTITY_KEY = "e" * 64
_TEST_REQUIREMENT_ID = "REQ-SR5-F2-UNIT-TEST"
_TEST_INSPECTOR_IDENTITY = {
    "kind": "bounded_codex_technical_reviewer",
    "id": "CODEX-SR5-F2-UNIT-TEST",
}


class _FakeLiveReviewStateTransport:
    """SR4-F1 correction (PR #112 comment 6032479337): a controlled fake standing in for a
    caller's own real GitHub API/MCP client -- this delivery's own tests never make a network
    call, exactly the identical pattern already established for ``_FakeNativeReviewTransport``.
    """

    def __init__(
        self,
        *,
        current_base_sha: str = _LIVE_REVIEW_SHA,
        current_head_sha: str = _LIVE_REVIEW_SHA,
        kill_switch_engaged: bool = False,
        pr_state: str = "open",
        pr_draft: bool = False,
        observed_at: str = _NOW,
    ) -> None:
        self._current_base_sha = current_base_sha
        self._current_head_sha = current_head_sha
        self._kill_switch_engaged = kill_switch_engaged
        self._pr_state = pr_state
        self._pr_draft = pr_draft
        self._observed_at = observed_at

    def fetch_live_review_state(self, *, repository: str, pull_request: str) -> dict[str, Any]:
        return {
            "repository": repository,
            "pull_request": pull_request,
            "current_base_sha": self._current_base_sha,
            "current_head_sha": self._current_head_sha,
            "kill_switch_engaged": self._kill_switch_engaged,
            "pr_state": self._pr_state,
            "pr_draft": self._pr_draft,
            "observed_at": self._observed_at,
        }


#: The one default live-state transport every ``compose_bounded_technical_review_dispatch``
#: call in this file supplies unless a test is specifically exercising SR4-F1 itself -- it
#: reports the identical, still-current sha every fixture grant's own ``authorized_base_sha``/
#: ``authorized_head_sha`` already uses, and no kill switch engaged.
_DEFAULT_LIVE_TRANSPORT = _FakeLiveReviewStateTransport()


# --------------------------------------------------------------------------- #
# review_adapter: real subprocess, bounded time/output
# --------------------------------------------------------------------------- #


def test_the_launch_completes_and_the_result_parses_as_structured_json(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_NORMAL)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    result = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    assert result.exit_code == 0
    assert not result.timed_out
    parsed = parse_structured_review_output(result.stdout)
    assert parsed["review_status"] == "COMPLETED"


def test_output_beyond_the_cap_is_truncated_not_buffered_unbounded(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_BIG_OUTPUT)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    result = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=1024,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    assert result.stdout_truncated
    assert len(result.stdout) == 1024


def test_a_hung_process_group_is_killed_at_the_deadline_not_left_running(tmp_path: Path) -> None:
    script = _write_fake_codex(tmp_path, _FAKE_CODEX_HANG)
    env = build_subprocess_environment({"PATH": os.environ.get("PATH", "/usr/bin")})
    started = time.monotonic()
    result = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=1,
        max_output_bytes=1024,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
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
    result = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=child_env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
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
        result = launch_review_process_for_test_only_mechanics(
            [sys.executable, str(script), str(staged)],
            cwd=workspace,
            env=env,
            max_seconds=5,
            max_output_bytes=4096,
            clock=_clock,
            mask_paths=_DEFAULT_TEST_MASK_PATHS,
            required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
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


def test_sr4_f2_prepare_inspection_workspace_never_uses_an_unbounded_copy_primitive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact SR4-F2 reproduction (PR #112 comment 6032479337): the ceiling was previously
    enforced against a pre-copy ``stat()`` size, while the real copy (``shutil.copyfile``)
    then read and wrote whatever the source file *actually* contained by the time it was
    opened -- with no bound of its own. A source file that grows between the ``stat()`` call
    and the real copy (reproduced via a deterministic controlled fixture) staged more bytes
    than the ceiling had ever permitted. This proves the real copy path no longer calls
    ``shutil.copyfile`` at all -- every byte copied is counted as it is actually read, in
    bounded chunks, so nothing a source file does between any two syscalls can ever desync
    "bytes the ceiling saw" from "bytes genuinely staged"."""

    import manosube_agent_civilization.development_binding.review_adapter as review_adapter_module

    def _forbidden_copyfile(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("prepare_inspection_workspace must never call shutil.copyfile")

    monkeypatch.setattr(review_adapter_module.shutil, "copyfile", _forbidden_copyfile)

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "small.py").write_text("ORIGINAL\n", encoding="utf-8")
    workspace = prepare_inspection_workspace(source_root, permitted_paths=["small.py"])
    try:
        assert (workspace / "small.py").read_text(encoding="utf-8") == "ORIGINAL\n"
    finally:
        cleanup_inspection_workspace(workspace)


def test_sr4_f2_a_file_exactly_at_the_ceiling_stages_successfully(tmp_path: Path) -> None:
    """Boundary correctness for the SR4-F2 chunked, real-bytes-counted copy: a file of exactly
    ``max_input_bytes`` stages successfully (never off-by-one refused merely because the
    ceiling is now enforced against genuinely-read chunks rather than one pre-copy size)."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    exact_ceiling_bytes = BOUNDED_REVIEW_NUMERIC_LIMITS["max_input_bytes"]
    (source_root / "at_ceiling.py").write_bytes(b"x" * exact_ceiling_bytes)
    workspace = prepare_inspection_workspace(source_root, permitted_paths=["at_ceiling.py"])
    try:
        assert (workspace / "at_ceiling.py").stat().st_size == exact_ceiling_bytes
    finally:
        cleanup_inspection_workspace(workspace)


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


def test_sr3_f4_cancellation_confirms_the_whole_process_group_not_just_the_leader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact SR3-F4 reproduction (PR #112 comment 6030487245): before this correction,
    the confirmation loop probed only the process-group leader's own pid (`os.kill(pid, 0)`)
    -- a leader confirmed dead said nothing at all about whether every other member of its
    own process group had actually terminated. This proves the real syscall the confirmation
    loop now issues is a *group* existence probe (`os.killpg(pgid, 0)`): a still-live group
    member (simulated here -- the probe never stops reporting the group alive) means
    ``local_process_group_terminated`` is honestly ``False``, never claimed ``True`` merely
    because a bare leader-pid probe would have said so."""

    from manosube_agent_civilization.development_binding import review_adapter as adapter_module

    monkeypatch.setattr(adapter_module, "process_identity_token", lambda pid: "OWNED")
    monkeypatch.setattr(adapter_module.os, "getpgid", lambda pid: 424242)

    killpg_signals: list[int] = []

    def fake_killpg(pgid: int, sig: int) -> None:
        killpg_signals.append(sig)
        # A live group member always answers the existence probe (sig == 0) -- it is never
        # reported gone, exactly as a genuinely still-running sibling process would behave.

    def fake_waitpid(pid: int, flags: int) -> tuple[int, int]:
        raise ChildProcessError

    monkeypatch.setattr(adapter_module.os, "killpg", fake_killpg)
    monkeypatch.setattr(adapter_module.os, "waitpid", fake_waitpid)

    outcome = adapter_module.cancel_review_task(
        pid=999999, owned_process_identity="OWNED", confirmation_timeout_seconds=0.2
    )
    assert outcome.ownership_confirmed is True
    assert outcome.local_process_group_terminated is False
    # The confirmation loop's own existence probe is a *group* probe (signal 0 against
    # `pgid`), never a bare single-pid `os.kill` -- the one real syscall surface this
    # correction changed.
    assert 0 in killpg_signals


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
    launch = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script), "src/some_reviewed_file.py"],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
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
    launch = launch_review_process_for_test_only_mechanics(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=env,
        max_seconds=5,
        max_output_bytes=4096,
        clock=_clock,
        mask_paths=_DEFAULT_TEST_MASK_PATHS,
        required_mask_roots=_DEFAULT_TEST_MASK_PATHS,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
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


def test_sr3_f1_a_grant_signed_for_a_different_envelope_is_refused_despite_identical_paths(
    _bound_route: dict[str, Any],
) -> None:
    """The exact SR3-F1 gap: before this correction, ``permitted_boundary`` bound only the
    inspection scope -- a Human-signed grant for the *identical* ``permitted_paths``/
    ``permitted_checks`` could be silently reused to authenticate a request against a
    different pull request, since nothing about that other repository/PR/base/head/
    requirement/input-digest/window/provenance was ever part of what Authority's own
    exact-equality check compared. ``launch_envelope_digest`` now folds the complete envelope
    in, so a grant signed for PR ``#999`` is refused outright for a request naming PR
    ``#109``, even though both share the identical inspection scope."""

    signed_for_pr_999 = _bounded_review_grant_record(
        authorized_pull_request="#999", input_digest="a" * 64
    )
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR3-F1-ENVELOPE-MISMATCH",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary={
            "permitted_paths": ["reviewed_f1_f2.py"],
            "permitted_checks": ["CORRECTNESS"],
            "launch_envelope_digest": compute_launch_envelope_digest(signed_for_pr_999),
        },
    )

    requested_for_pr_109 = _bounded_review_grant_record(
        authorized_pull_request="#109", input_digest="a" * 64
    )
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
            "launch_envelope_digest": compute_launch_envelope_digest(requested_for_pr_109),
        },
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
    )
    assert decision["decision"] == REVIEW_SELECTION_REFUSED


def test_sr3_f1_spawn_review_process_refuses_an_invalid_or_missing_admission_token(
    tmp_path: Path,
) -> None:
    """The exact SR3-F1 public-surface-bypass gap: before this correction,
    ``spawn_review_process`` performed no precondition check of its own -- a caller could
    reach the one real external effect through this public function while skipping
    ``validate_review_launch_preconditions`` entirely. A forged or stale token is now
    refused, and only a token that function itself just returned is accepted."""

    with pytest.raises(ReviewAdapterError):
        spawn_review_process_for_test_only_mechanics(
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            env={},
            admission_token="forged-token-never-issued-by-validate",  # noqa: S106
            mask_paths=(tmp_path,),
            require_isolation=True,
        )

    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=[sys.executable, "-c", "pass"],
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=4096,
        mask_paths=(tmp_path,),
        require_isolation=True,
        required_mask_roots=(tmp_path,),
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    # The real token is consumed exactly once -- a second spawn with the same token refuses.
    process = spawn_review_process_for_test_only_mechanics(
        [sys.executable, "-c", "pass"],
        cwd=tmp_path,
        env={},
        admission_token=token,
        mask_paths=(tmp_path,),
        require_isolation=True,
    )
    try:
        process.wait(timeout=10)
    finally:
        assert process.stdout is not None
        assert process.stderr is not None
        process.stdout.close()
        process.stderr.close()
    with pytest.raises(ReviewAdapterError):
        spawn_review_process_for_test_only_mechanics(
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            env={},
            admission_token=token,
            mask_paths=(tmp_path,),
            require_isolation=True,
        )


def test_f2_compose_bounded_technical_review_dispatch_refuses_at_the_filesystem_boundary(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR9-F1 correction (PR #112 comment 6053084718): this test previously asserted the
    composed route reached ``"complete"``/``"VERIFIED"`` against a real authenticated grant --
    that outcome required the now-removed ``build_argv``/``proceed_past_filesystem_boundary``
    escape hatch this correction deleted entirely (see the module docstring of
    ``scripts/bounded_technical_review.py``). There is no longer any configuration, grant, or
    evidence that makes :func:`~scripts.bounded_technical_review.compose_bounded_technical_
    review_dispatch` reach a real launch; even a fully valid, fully authenticated grant now
    reaches only the unconditional ``"local-dispatch-boundary"``/``INCOMPLETE_FILESYSTEM_
    BOUNDARY`` refusal, with the claim released as genuinely unsent rather than recorded as a
    false outcome."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(["reviewed_f1_f2.py"]),
        "permitted_checks_digest": canonical_list_digest(["CORRECTNESS"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-F2-POSITIVE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

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
        now_provider=lambda: _NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        mask_paths=(*_DEFAULT_TEST_MASK_PATHS, source_root),
    )
    assert result["stage"] == "local-dispatch-boundary", result
    assert result["reason"] == "INCOMPLETE_FILESYSTEM_BOUNDARY", result

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

    grant = _bounded_review_grant_record(input_digest="f" * 64)
    grant["api_read_back_receipt"]["input_digest"] = "f" * 64
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(["reviewed_f1_f2.py"]),
        "permitted_checks_digest": canonical_list_digest(["CORRECTNESS"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-F2-NEGATIVE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

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
        now_provider=lambda: _NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        mask_paths=(*_DEFAULT_TEST_MASK_PATHS, source_root),
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


def test_sr2_f1_a_pre_send_live_recheck_refusal(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """The exact SR2-F1 gap: before this correction, nothing re-checked activation/admission
    between the top-of-call admission check and the one external-effect send -- a caller's own
    static ``activation_evidence`` string, read once, stood in for a live check forever. Here,
    *activation_evidence_provider* reports the activation gate as no longer active at the
    pre-send checkpoint even though the top-of-call *activation_evidence* itself still reports
    active -- simulating activation being revoked in the window between admission and send.

    SR9-F1 correction (PR #112 comment 6053084718): this test previously drove the scenario
    through the full composed dispatch route, past the filesystem boundary, via the now-removed
    ``compose_bounded_technical_review_dispatch_for_controlled_mechanics_test``/
    ``_compose_bounded_technical_review_dispatch_core`` -- both removed entirely (see
    `docs/bounded_technical_review.md`). The recheck mechanic this test exists to prove is
    :func:`~scripts.bounded_technical_review._recheck_live_authorization`'s own; this test now
    calls that real, production function directly, never through any launch-reachable route.
    The composed route's own ``release_unsent_claim``-on-refusal plumbing (unchanged, pure
    ledger bookkeeping) is already independently proven by this file's digest-mismatch and
    filesystem-boundary tests."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F1-PRE-SEND",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }

    revoked_activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": False,
    }
    refusal = bounded_review_script._recheck_live_authorization(
        grant=grant,
        now_provider=lambda: _NOW,
        activation_evidence_provider=lambda: revoked_activation_evidence,
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        grant_provider=None,
    )
    assert refusal is not None
    assert refusal["reason"] == "ACTIVATION_NO_LONGER_ACTIVE", refusal


def test_sr2_f1_a_changed_grant_envelope_is_refused_by_the_live_recheck(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """*grant_provider* lets a caller re-fetch the grant fresh at each live-recheck checkpoint;
    a grant whose own authorized envelope (here, ``authorized_head_sha``) no longer matches the
    snapshot this call started from is refused as ``GRANT_ENVELOPE_CHANGED`` -- never silently
    trusted merely because it was read once, at the top of the call.

    SR9-F1 correction (PR #112 comment 6053084718): see
    ``test_sr2_f1_a_pre_send_live_recheck_refusal``'s own docstring -- this test now calls
    :func:`~scripts.bounded_technical_review._recheck_live_authorization` directly instead of
    driving it through the removed mechanics-test composed route."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F1-ENVELOPE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    changed_grant = {**grant, "authorized_head_sha": "f" * 40}
    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }

    refusal = bounded_review_script._recheck_live_authorization(
        grant=grant,
        now_provider=lambda: _NOW,
        activation_evidence_provider=lambda: {"activation_enabled": True},
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        grant_provider=lambda: changed_grant,
    )
    assert refusal is not None
    assert refusal["reason"] == "GRANT_ENVELOPE_CHANGED", refusal
    assert refusal["field"] == "authorized_head_sha", refusal


def test_sr4_f1_an_engaged_kill_switch_refuses_the_pre_send_recheck(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """The exact SR4-F1 reproduction (PR #112 comment 6032479337): before this correction,
    nothing ever called a genuinely live reader at all -- the pre-send recheck evaluated
    ``evaluate_review_selection`` against the grant's own static ``current_*`` fields, never a
    fresh observation. Here a controlled fake ``LiveReviewStateTransport`` reports the kill
    switch engaged; the recheck is refused, never silently proceeding because the grant's own
    static fields still "matched".

    SR9-F1 correction (PR #112 comment 6053084718): see
    ``test_sr2_f1_a_pre_send_live_recheck_refusal``'s own docstring -- calls
    :func:`~scripts.bounded_technical_review._recheck_live_authorization` directly instead of
    driving it through the removed mechanics-test composed route."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR4-F1-KILL-SWITCH",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }
    full_activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }
    engaged_transport = _FakeLiveReviewStateTransport(kill_switch_engaged=True)

    refusal = bounded_review_script._recheck_live_authorization(
        grant=grant,
        now_provider=lambda: _NOW,
        activation_evidence_provider=lambda: full_activation_evidence,
        live_state_transport=engaged_transport,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        grant_provider=None,
    )
    assert refusal is not None
    assert refusal["reason"] == "KILL_SWITCH_ENGAGED", refusal


def test_sr4_f1_a_live_head_change_is_refused_by_a_genuinely_fresh_observation(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """The exact SR4-F1 reproduction: before this correction, the live recheck compared the
    grant's own static ``current_head_sha`` against its own static ``authorized_head_sha`` --
    two fields nothing ever refreshed, so they always agreed. Here a controlled fake
    ``LiveReviewStateTransport`` reports a genuinely different, fresh ``current_head_sha`` (the
    PR having moved to a new commit); the recheck is refused as ``SELECTION_NO_LONGER_
    ADMITTED``, proving the live observation is what the recheck now actually uses, never the
    grant's own unchanging fields.

    SR9-F1 correction (PR #112 comment 6053084718): see
    ``test_sr2_f1_a_pre_send_live_recheck_refusal``'s own docstring -- calls
    :func:`~scripts.bounded_technical_review._recheck_live_authorization` directly instead of
    driving it through the removed mechanics-test composed route."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR4-F1-LIVE-HEAD-MOVED",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }
    full_activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }
    moved_on_transport = _FakeLiveReviewStateTransport(current_head_sha="f" * 40)

    refusal = bounded_review_script._recheck_live_authorization(
        grant=grant,
        now_provider=lambda: _NOW,
        activation_evidence_provider=lambda: full_activation_evidence,
        live_state_transport=moved_on_transport,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        grant_provider=None,
    )
    assert refusal is not None
    assert refusal["reason"] == "SELECTION_NO_LONGER_ADMITTED", refusal


def test_sr4_f1_fetch_trusted_live_review_state_refuses_a_mismatched_pull_request(
    tmp_path: Path,
) -> None:
    """The exact SR4-F1 cross-check: a transport that returns live state for a different
    pull request than the one requested is refused outright, never silently accepted."""

    class _WrongPullRequestTransport:
        def fetch_live_review_state(self, *, repository: str, pull_request: str) -> dict[str, Any]:
            return {
                "repository": repository,
                "pull_request": "#not-the-one-requested",
                "current_base_sha": _LIVE_REVIEW_SHA,
                "current_head_sha": _LIVE_REVIEW_SHA,
                "kill_switch_engaged": False,
                "pr_state": "open",
                "pr_draft": False,
                "observed_at": _NOW,
            }

    with pytest.raises(ReviewAdapterError):
        fetch_trusted_live_review_state(
            _WrongPullRequestTransport(), repository=_REPO, pull_request="#999"
        )


def test_sr4_f1_admission_token_is_bound_to_the_exact_validated_configuration(
    tmp_path: Path,
) -> None:
    """The exact SR4-F1 reproduction (PR #112 comment 6032479337): before this correction, the
    admission token was bare set membership -- a token minted for ``require_isolation=False``
    was happily consumed by a ``spawn_review_process`` call independently supplying
    ``require_isolation=True`` (or a changed argv/cwd/mask_paths). The token is now bound to
    the exact configuration it was validated for; any mismatch at spawn time is refused."""

    argv = [sys.executable, "-c", "pass"]

    # Minted for require_isolation=False -- never consumed by a spawn call that supplies
    # require_isolation=True instead.
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=argv,
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=4096,
        mask_paths=(),
        require_isolation=False,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    with pytest.raises(ReviewAdapterError):
        spawn_review_process_for_test_only_mechanics(
            argv,
            cwd=tmp_path,
            env={},
            admission_token=token,
            mask_paths=(tmp_path,),
            require_isolation=True,
        )

    # Minted for one argv -- never consumed by a spawn call supplying a different one.
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=argv,
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=4096,
        mask_paths=(tmp_path,),
        require_isolation=True,
        required_mask_roots=(tmp_path,),
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    with pytest.raises(ReviewAdapterError):
        spawn_review_process_for_test_only_mechanics(
            [sys.executable, "-c", "print('different')"],
            cwd=tmp_path,
            env={},
            admission_token=token,
            mask_paths=(tmp_path,),
            require_isolation=True,
        )

    # The identical configuration the token was minted for is genuinely admitted.
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=argv,
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=4096,
        mask_paths=(tmp_path,),
        require_isolation=True,
        required_mask_roots=(tmp_path,),
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    process = spawn_review_process_for_test_only_mechanics(
        argv,
        cwd=tmp_path,
        env={},
        admission_token=token,
        mask_paths=(tmp_path,),
        require_isolation=True,
    )
    try:
        process.wait(timeout=10)
    finally:
        assert process.stdout is not None
        assert process.stderr is not None
        process.stdout.close()
        process.stderr.close()


# --------------------------------------------------------------------------- #
# SR5-F1 corrections (PR #112 comment 6034603745), adopted
# ADOPT_I109_PR112_SR5_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def _sr5_f1_recheck_with_live_transport(
    *, bound_route: dict[str, Any], transaction_id: str, transport: Any
) -> dict[str, Any] | None:
    """Shared setup for the SR5-F1 not-ready/stale-observation tests -- identical in shape to
    the existing SR4-F1 kill-switch/head-change tests above, parameterized only by the live
    transport under test.

    SR9-F1 correction (PR #112 comment 6053084718): see
    ``test_sr2_f1_a_pre_send_live_recheck_refusal``'s own docstring -- calls
    :func:`~scripts.bounded_technical_review._recheck_live_authorization` directly instead of
    driving it through the removed mechanics-test composed route."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        bound_route,
        transaction_id=transaction_id,
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }
    full_activation_evidence = {
        "auth_confirmed": True,
        "cli_version": SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"],
        "model": SUPPORTED_ENVIRONMENT_FINGERPRINT["model"],
        "allowance_confirmed_adequate": True,
        "auto_recharge_verified_disabled": True,
        "native_github_dedup_disposition": "DISABLED",
        "live_bounded_review_grant_admitted": True,
        "activation_enabled": True,
    }

    return bounded_review_script._recheck_live_authorization(
        grant=grant,
        now_provider=lambda: _NOW,
        activation_evidence_provider=lambda: full_activation_evidence,
        live_state_transport=transport,
        store=bound_route["store"],
        project_id=bound_route["project_id"],
        project_binding_id=bound_route["project_binding_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        grant_provider=None,
    )


@pytest.mark.parametrize(
    "transport_kwargs,transaction_suffix",
    [({"pr_draft": True}, "DRAFT-TRUE"), ({"pr_state": "closed"}, "STATE-CLOSED")],
    ids=["draft-true", "state-closed"],
)
def test_sr5_f1_a_live_pr_that_is_draft_or_closed_refuses_the_pre_send_recheck(
    _bound_route: dict[str, Any],
    transport_kwargs: dict[str, Any],
    transaction_suffix: str,
) -> None:
    """The exact SR5-F1 reproduction (PR #112 comment 6034603745): before this correction, a
    live state carrying matching shas but ``pr_draft=True`` or ``pr_state="closed"`` still
    reached ``evaluate_review_selection`` unrefused -- a matching sha was never itself proof
    the PR was still a live, reviewable target. Fixed: the pre-send recheck now refuses
    outright on a live PR that is no longer open or still a draft."""

    transport = _FakeLiveReviewStateTransport(**transport_kwargs)
    refusal = _sr5_f1_recheck_with_live_transport(
        bound_route=_bound_route,
        transaction_id=f"TX-I109-SR5-F1-NOT-READY-{transaction_suffix}",
        transport=transport,
    )
    assert refusal is not None
    assert refusal["reason"] == "LIVE_PR_NOT_READY", refusal


def test_sr5_f1_a_stale_live_observation_refuses_the_pre_send_recheck(
    _bound_route: dict[str, Any],
) -> None:
    """The exact SR5-F1 reproduction: an ``observed_at`` from 1900 -- a transport response
    that is well-shaped and carries matching shas, but was (impossibly) observed long before
    this call -- still reached ``evaluate_review_selection`` unrefused before this correction.
    Fixed: an observation older than the ratified ``max_live_state_observation_age_seconds``
    is refused as stale, never trusted merely because the sha comparison would pass."""

    transport = _FakeLiveReviewStateTransport(observed_at="1900-01-01T00:00:00Z")
    refusal = _sr5_f1_recheck_with_live_transport(
        bound_route=_bound_route,
        transaction_id="TX-I109-SR5-F1-STALE-OBSERVATION",
        transport=transport,
    )
    assert refusal is not None
    assert refusal["reason"] == "LIVE_STATE_OBSERVATION_STALE", refusal
    assert refusal["observation_age_seconds"] > 0


def test_sr5_f1_a_live_observation_claiming_to_be_from_the_future_is_also_refused(
    _bound_route: dict[str, Any],
) -> None:
    """The symmetric case: an ``observed_at`` impossibly *after* the real clock this call's
    own ``now_provider`` reports is equally never trusted -- staleness is never one-sided."""

    transport = _FakeLiveReviewStateTransport(observed_at="2099-01-01T00:00:00Z")
    refusal = _sr5_f1_recheck_with_live_transport(
        bound_route=_bound_route,
        transaction_id="TX-I109-SR5-F1-FUTURE-OBSERVATION",
        transport=transport,
    )
    assert refusal is not None
    assert refusal["reason"] == "LIVE_STATE_OBSERVATION_STALE", refusal
    assert refusal["observation_age_seconds"] < 0


def test_sr5_f1_fetch_trusted_live_review_state_refuses_a_malformed_readiness_shape() -> None:
    """Unit-level proof of :func:`fetch_trusted_live_review_state`'s own new shape checks,
    independent of the composed route: an invalid ``pr_state``, a non-bool ``pr_draft``, and
    an unparseable ``observed_at`` are each refused outright."""

    base_shape = {
        "repository": _REPO,
        "pull_request": "#109",
        "current_base_sha": _LIVE_REVIEW_SHA,
        "current_head_sha": _LIVE_REVIEW_SHA,
        "kill_switch_engaged": False,
        "pr_state": "open",
        "pr_draft": False,
        "observed_at": _NOW,
    }

    class _FixedShapeTransport:
        def __init__(self, shape: dict[str, Any]) -> None:
            self._shape = shape

        def fetch_live_review_state(self, *, repository: str, pull_request: str) -> dict[str, Any]:
            return self._shape

    for override in (
        {"pr_state": "merged"},
        {"pr_draft": "yes"},
        {"observed_at": "not-a-timestamp"},
        {"observed_at": ""},
    ):
        with pytest.raises(ReviewAdapterError):
            fetch_trusted_live_review_state(
                _FixedShapeTransport({**base_shape, **override}),
                repository=_REPO,
                pull_request="#109",
            )

    # The identical, fully well-shaped state is genuinely accepted.
    accepted = fetch_trusted_live_review_state(
        _FixedShapeTransport(base_shape), repository=_REPO, pull_request="#109"
    )
    assert accepted["pr_state"] == "open"
    assert accepted["pr_draft"] is False


def test_sr3_f2_an_oversize_staged_input_is_refused_at_the_real_staging_point(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR3-F2 correction (PR #112 comment 6030487245): the ratified ``max_input_bytes``
    ceiling is now enforced by ``prepare_inspection_workspace`` itself -- per file, before any
    byte is staged -- never only against the whole bundle after it was already fully copied,
    and never a parameter this route (or any caller) can widen. A file one byte over the real
    ratified ceiling is refused, and the slot released unsent, before any process starts."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    oversize_bytes = BOUNDED_REVIEW_NUMERIC_LIMITS["max_input_bytes"] + 1
    (source_root / "reviewed_f1_f2.py").write_bytes(b"x" * oversize_bytes)

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    grant["api_read_back_receipt"]["input_digest"] = "a" * 64
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(["reviewed_f1_f2.py"]),
        "permitted_checks_digest": canonical_list_digest(["CORRECTNESS"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR3-F2-SIZE-CAP",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

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
        now_provider=lambda: _NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        mask_paths=(*_DEFAULT_TEST_MASK_PATHS, source_root),
    )
    assert result["stage"] == "input-staging", result
    assert "max_input_bytes" in result["error"]

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
        {
            "review_status": "COMPLETED",
            "findings": [],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
        }
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=[],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == expected_classification


@pytest.mark.parametrize(
    "finding",
    [
        {"check": "ROOT_CAUSE", "status": "FAIL", "severity": "P0", "procedure": "trace review"},
        {"check": "ROOT_CAUSE", "status": "FAIL", "severity": "P1", "procedure": "trace review"},
        # SR3-F2's own exact reproduction: a failed condition with no severity at all.
        {"check": "ROOT_CAUSE", "status": "FAIL", "procedure": "trace review"},
    ],
    ids=["p0-finding", "p1-finding", "failed-status-no-severity"],
)
def test_sr3_f2_a_completed_result_with_a_failed_or_blocking_finding_is_failed_not_verified(
    finding: dict[str, Any],
) -> None:
    """The exact SR2-F2/SR3-F2 reproductions: a result carrying a P0 finding (outside the
    prior P1/BLOCKING/CRITICAL-only allowlist), and a finding declaring
    ``status=FAILED``/no severity at all, were both still reported VERIFIED because the
    classifier either never read severities at all, or read severity alone and ignored
    ``status`` entirely."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [finding],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["ROOT_CAUSE"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "FAILED"


def test_sr4_f2_a_later_pass_never_overwrites_an_earlier_fail_for_the_identical_check() -> None:
    """The exact SR4-F2 reproduction (PR #112 comment 6032479337): a later finding's PASS for
    the identical check silently overwrote an earlier FAIL for that same check -- reproduced
    with CORRECTNESS FAIL followed by CORRECTNESS PASS, still reported VERIFIED. The result is
    now FAILED regardless of finding order."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [
                {"check": "CORRECTNESS", "status": "FAIL", "procedure": "static read"},
                {"check": "CORRECTNESS", "status": "PASS", "procedure": "static read"},
            ],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "FAILED"


def test_sr4_f2_a_fail_with_no_recognized_check_is_never_silently_ignored() -> None:
    """The exact SR4-F2 reproduction: a FAIL finding naming no recognized check (``condition=
    CORRECTNESS``, no ``check`` key) was silently dropped -- reproduced alongside a *separate*
    check=CORRECTNESS/PASS finding, still reported VERIFIED. An unattributed FAIL now fails the
    whole result, never ignored merely because it cannot be coverage-matched by name."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [
                {"condition": "CORRECTNESS", "status": "FAIL", "procedure": "static read"},
                {"check": "CORRECTNESS", "status": "PASS", "procedure": "static read"},
            ],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "FAILED"


def test_sr4_f2_a_result_with_no_identity_correlation_is_insufficient_not_verified() -> None:
    """The exact SR4-F2 reproduction: ``{review_status:COMPLETED, inspected_paths:[x.py],
    findings:[{check:CORRECTNESS,status:PASS}]}`` returned VERIFIED with zero correlation to
    which staged input was actually inspected. A result that omits (or mismatches)
    ``observed_input_digest`` is now INSUFFICIENT, never VERIFIED merely because its findings
    otherwise look clean."""

    stdout_no_digest = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [{"check": "CORRECTNESS", "status": "PASS"}],
            "inspected_paths": ["x.py"],
        }
    ).encode("utf-8")
    stdout_wrong_digest = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [{"check": "CORRECTNESS", "status": "PASS"}],
            "inspected_paths": ["x.py"],
            "observed_input_digest": "0" * 64,
        }
    ).encode("utf-8")
    base = {
        "exit_code": 0,
        "stderr": b"",
        "stdout_truncated": False,
        "stderr_truncated": False,
        "timed_out": False,
        "pid": 1,
        "process_identity": "1:0",
        "started_at": _NOW,
        "ended_at": _NOW,
    }
    for stdout in (stdout_no_digest, stdout_wrong_digest):
        launch_result = argparse.Namespace(**{**base, "stdout": stdout})
        classification, _codex_result = bounded_review_script.classify_review_result(
            launch_result,
            permitted_paths=["x.py"],
            permitted_checks=["CORRECTNESS"],
            expected_input_digest=_TEST_INPUT_DIGEST,
            identity_key=_TEST_IDENTITY_KEY,
            requirement_id=_TEST_REQUIREMENT_ID,
            inspector_identity=_TEST_INSPECTOR_IDENTITY,
            launch_started_at=_NOW,
            launch_ended_at=_NOW,
        )
        assert classification == "INSUFFICIENT"


def test_sr3_f2_a_completed_result_with_no_finding_for_a_permitted_check_is_insufficient() -> None:
    """The exact SR3-F2 reproduction: ``COMPLETED`` with full path coverage but zero finding
    results for the grant's own permitted checks was accepted as VERIFIED purely because
    nothing explicitly failed -- never itself evidence that any required check was performed
    at all."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "INSUFFICIENT"


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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=[],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "INSUFFICIENT"


# --------------------------------------------------------------------------- #
# SR5-F2 corrections (PR #112 comment 6034603745), adopted
# ADOPT_I109_PR112_SR5_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr5_f2_a_check_and_status_with_no_procedure_is_insufficient_not_verified() -> None:
    """The exact SR5-F2 reproduction (PR #112 comment 6034603745): a well-shaped
    ``COMPLETED``/exit-0 result naming only ``inspected_paths``, a matching
    ``observed_input_digest``, and ``check=CORRECTNESS``/``status=PASS`` -- with no
    ``procedure`` at all -- was still fully ``VERIFIED``; a check/status pair alone is never
    itself evidence of what was actually examined. Fixed: a finding with no non-empty
    ``procedure`` is now ``INSUFFICIENT``, never silently accepted as sufficient outcome
    evidence."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [{"check": "CORRECTNESS", "status": "PASS"}],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "INSUFFICIENT"


@pytest.mark.parametrize(
    "procedure_override",
    [None, "", 42],
    ids=["missing", "empty-string", "non-string"],
)
def test_sr5_f2_a_malformed_procedure_is_also_insufficient(procedure_override: Any) -> None:
    """The same SR5-F2 requirement, exercised against the shape variants a real subprocess
    could plausibly emit: an explicit ``null``, an empty string, and a non-string value are
    each refused exactly like an entirely absent ``procedure`` key."""

    finding: dict[str, Any] = {"check": "CORRECTNESS", "status": "PASS"}
    if procedure_override is not None:
        finding["procedure"] = procedure_override
    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [finding],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
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
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at=_NOW,
        launch_ended_at=_NOW,
    )
    assert classification == "INSUFFICIENT"


@pytest.mark.parametrize(
    "overrides,expected_classification",
    [
        ({}, "VERIFIED"),
        ({"exit_code": 1}, "FAILED"),
        ({"timed_out": True}, "INSUFFICIENT"),
    ],
    ids=["verified", "failed", "insufficient"],
)
def test_sr5_f2_correlated_launch_identity_is_attached_on_every_return_path(
    overrides: dict[str, Any], expected_classification: str
) -> None:
    """The exact SR5-F2 fix: *identity_key*/*requirement_id*/*inspector_identity*/the real
    observed launch window -- every one of them already known to this function's own trusted
    caller, never asserted by the reviewed subprocess -- are folded into the returned
    ``codex_result`` under ``correlated_launch`` on *every* return path, not only
    ``VERIFIED``, so a classification this function hands back is never severed from which
    exact attempt/requirement/launch window it was ever about."""

    stdout = json.dumps(
        {
            "review_status": "COMPLETED",
            "findings": [{"check": "CORRECTNESS", "status": "PASS", "procedure": "static read"}],
            "inspected_paths": ["x.py"],
            "observed_input_digest": _TEST_INPUT_DIGEST,
        }
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
        "started_at": "2026-10-07T09:00:00Z",
        "ended_at": "2026-10-07T09:05:00Z",
    }
    launch_result = argparse.Namespace(**{**base, **overrides})
    classification, codex_result = bounded_review_script.classify_review_result(
        launch_result,
        permitted_paths=["x.py"],
        permitted_checks=["CORRECTNESS"],
        expected_input_digest=_TEST_INPUT_DIGEST,
        identity_key=_TEST_IDENTITY_KEY,
        requirement_id=_TEST_REQUIREMENT_ID,
        inspector_identity=_TEST_INSPECTOR_IDENTITY,
        launch_started_at="2026-10-07T09:00:00Z",
        launch_ended_at="2026-10-07T09:05:00Z",
    )
    assert classification == expected_classification
    assert codex_result["correlated_launch"] == {
        "identity_key": _TEST_IDENTITY_KEY,
        "requirement_id": _TEST_REQUIREMENT_ID,
        "inspector_identity": _TEST_INSPECTOR_IDENTITY,
        "observed_window": {
            "started_at": "2026-10-07T09:00:00Z",
            "ended_at": "2026-10-07T09:05:00Z",
        },
    }


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


def test_sr3_f2_the_composed_route_still_refuses_at_the_boundary_when_an_evidence_handoff_is_asked(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR2-F2/SR3-F2 originally proved *evidence_handoff*, when given, performs the real
    ``run_independent_verification``/``route_verification_result_to_evidence`` chain itself,
    inside the shared local-dispatch composed route, for *this exact* launch's own
    (requirement, permitted_boundary) scope.

    SR9-F1 correction (PR #112 comment 6053084718): that outcome required the now-removed
    ``build_argv``/``proceed_past_filesystem_boundary`` escape hatch -- see the module
    docstring of ``scripts/bounded_technical_review.py``. :func:`~scripts.
    bounded_technical_review.compose_bounded_technical_review_dispatch` now always refuses at
    the unconditional ``"local-dispatch-boundary"`` before it would ever reach the evidence
    handoff, so *evidence_handoff* is inert for this route regardless of how genuinely it is
    authorized -- this test now proves exactly that: a fully valid, same-scope handoff request
    still never performs any handoff. The identical real handoff, through the identical
    unmodified ``_hand_off_to_evidence``, is already independently proven live by
    ``test_sr5_f3_the_native_reuse_route_performs_a_correlated_real_evidence_handoff_when_asked``
    (the still-live REUSE_NATIVE_ONLY route, which never reaches a local launch at all)."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(["reviewed_f1_f2.py"]),
        "permitted_checks_digest": canonical_list_digest(["CORRECTNESS"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR2-F2-EVIDENCE",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

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

    # A fully valid, same-scope handoff request -- the identical one SR3-F2 originally proved
    # was performed. It is still accepted as a parameter; the route still never reaches it.
    requirement = VerificationRequirement(
        requirement_id=grant["requirement_id"],
        project_id=_bound_route["project_id"],
        target_refs=[{"kind": "observation_evidence", "id": _bound_route["evidence_id"]}],
        verification_boundary=dict(permitted_boundary),
        required_conditions={"minimum_distinctness": "DISTINCT_LINEAGE"},
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
    )
    selection = VerifierSelection(
        selection_id=grant["work_unit_id"],
        project_id=_bound_route["project_id"],
        requirement_id=grant["requirement_id"],
        status="ACTIVE",
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
        verifier_identity=dict(_F1_F2_VERIFIER_IDENTITY),
        permitted_boundary=dict(permitted_boundary),
    )

    result = bounded_review_script.compose_bounded_technical_review_dispatch(
        grant=grant,
        now=_NOW,
        now_provider=lambda: _NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        mask_paths=(*_DEFAULT_TEST_MASK_PATHS, source_root),
        evidence_handoff={
            "verification_requirement": requirement,
            "verifier_selection": selection,
            "evidence_request": _evidence_request_for_project(_bound_route["project_id"]),
        },
    )
    assert result["stage"] == "local-dispatch-boundary", result
    assert result["reason"] == "INCOMPLETE_FILESYSTEM_BOUNDARY", result
    assert "evidence" not in result, result


def test_sr3_f2_hand_off_to_evidence_refuses_a_genuinely_different_requirement(
    _bound_route: dict[str, Any],
) -> None:
    """The exact SR3-F2 reproduction: a ``VerifierSelection``/``VerificationRequirement`` that
    is genuinely, independently authorized -- but for a *different* requirement/scope than the
    one this launch itself inspected -- must never be accepted as this launch's own Evidence
    handoff. Genuine authority for two separate scopes is never interchangeable.

    SR9-F1 correction (PR #112 comment 6053084718): this test previously drove the mismatch
    through the now-removed local-dispatch mechanics-test composed route. The mismatch check
    this test exists to prove is :func:`~scripts.bounded_technical_review._hand_off_to_evidence`
    's own -- the identical, unmodified function both the local-dispatch route (inert, see
    ``test_sr3_f2_the_composed_route_still_refuses_at_the_boundary_when_an_evidence_handoff_is_
    asked``) and the still-live native-reuse route call -- so this test now calls it directly,
    never through either composed route."""

    grant = _bounded_review_grant_record(input_digest="a" * 64)
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR3-F2-MISMATCH",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )
    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )

    # Genuinely, independently authorized -- but for _bound_route's own separate
    # requirement/grant, never this launch's own.
    mismatched_requirement = VerificationRequirement(
        requirement_id=_bound_route["grant"]["requirement_id"],
        project_id=_bound_route["project_id"],
        target_refs=[{"kind": "observation_evidence", "id": _bound_route["evidence_id"]}],
        verification_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
        required_conditions={"minimum_distinctness": "DISTINCT_LINEAGE"},
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
    )
    mismatched_selection = VerifierSelection(
        selection_id=_bound_route["grant"]["selection_id"],
        project_id=_bound_route["project_id"],
        requirement_id=_bound_route["grant"]["requirement_id"],
        status="ACTIVE",
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
        verifier_identity=dict(_DEFAULT_VERIFIER_IDENTITY),
        permitted_boundary=dict(_bound_route["grant"]["permitted_boundary"]),
    )

    with pytest.raises(ReviewAdapterError):
        bounded_review_script._hand_off_to_evidence(
            evidence_handoff={
                "verification_requirement": mismatched_requirement,
                "verifier_selection": mismatched_selection,
                "evidence_request": _evidence_request_for_project(_bound_route["project_id"]),
            },
            store=_bound_route["store"],
            project_id=_bound_route["project_id"],
            project_binding_id=_bound_route["project_binding_id"],
            verifier_selection_grant_refs=[committed["grant_ref"]],
            human_grant_declaration_refs=[committed["declaration_ref"]],
            grant=grant,
            permitted_boundary=permitted_boundary,
            identity_key=identity_key,
            classification="VERIFIED",
            codex_result={},
        )


def test_sr2_f4_a_successful_dispatch_attaches_the_real_pid_before_collection(
    tmp_path: Path,
) -> None:
    """SR2-F4: the real pid/process identity is attached (``confirm_dispatch_sent``) the
    instant the process starts, before the collection wait ever begins -- proven here by
    reading the ledger claim right after the spawn, before collection, and confirming it
    already carries the real pid, never ``None``.

    SR9-F1 correction (PR #112 comment 6053084718): this test previously drove the scenario
    through the now-removed local-dispatch mechanics-test composed route -- the production
    route this correction removes never reaches a real spawn at all any more (see the module
    docstring of ``scripts/bounded_technical_review.py``). The ``record_dispatch_attempt``/
    ``confirm_dispatch_sent`` ordering this test exists to prove is real, unchanged,
    non-launch-capable :mod:`~manosube_agent_civilization.development_binding.review_control`
    ledger plumbing (the identical functions ``test_sr2_f5_cancellation_refuses_an_unrelated_
    processs_own_real_pid_and_identity`` already calls this same way); the one actual process
    spawn needed to exercise a real pid now uses this file's own test-local-only
    ``spawn_review_process_for_test_only_mechanics`` helper (never any production launch
    capability) instead of the removed composed route."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR2-F4-PID",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR2-F4-PID",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    argv = [sys.executable, "-c", "import time; time.sleep(30)"]
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=argv,
        cwd=tmp_path,
        max_seconds=30,
        max_output_bytes=4096,
        mask_paths=(),
        require_isolation=False,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    process = spawn_review_process_for_test_only_mechanics(
        argv, cwd=tmp_path, env={}, admission_token=token, require_isolation=False
    )
    try:
        process_identity = process_identity_token(process.pid)
        assert process_identity is not None

        bounded_review_script.record_dispatch_attempt(
            ledger_path, identity_key, repository=repository, acknowledged=False
        )
        bounded_review_script.confirm_dispatch_sent(
            ledger_path,
            identity_key,
            repository=repository,
            pid=process.pid,
            process_identity=process_identity,
        )

        # The pid/process identity are already attached -- before any collection wait that
        # would follow (:func:`collect_review_process_result`) ever begins.
        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["pid"] == process.pid
        assert claim["process_identity"] == process_identity
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=10)
        assert process.stdout is not None
        assert process.stderr is not None
        process.stdout.close()
        process.stderr.close()


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
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
        assert confirmed["local_process_group_terminated"] is True
        # SR5-F4 correction (PR #112 comment 6034603745): a confirmed *local* cancellation
        # never resolves the claim or releases the concurrency slot -- provider/task state
        # remains genuinely unknown, so the slot is retained.
        assert confirmed["concurrency_slot_retained"] is True

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
        assert claim["resolution_kind"] is None
        assert claim["result_digest"] is None
        assert claim["local_cancellation_confirmed_at"] is not None
    finally:
        for process in (owned_process, unrelated_process):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


def test_sr3_f4_a_confirmed_owner_but_unterminated_group_is_not_confirmed_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact SR3-F4 reproduction (PR #112 comment 6030487245): before this correction,
    ``compose_bounded_technical_review_cancellation`` reached ``CANCELLATION_CONFIRMED`` on
    ``outcome.ownership_confirmed`` alone -- a controlled fixture reporting ownership
    confirmed but the process group *not* actually terminated
    (``local_process_group_terminated=False``, ``provider_server_state=UNAVAILABLE``) still
    recorded a terminal outcome for a process this route never actually confirmed was gone."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR3-F4-UNTERMINATED",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR3-F4-UNTERMINATED",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )
    bounded_review_script.confirm_dispatch_sent(
        ledger_path, identity_key, repository=repository, pid=424242, process_identity="424242:1"
    )

    monkeypatch.setattr(
        bounded_review_script,
        "cancel_review_task",
        lambda *, pid, owned_process_identity: bounded_review_script.CancellationOutcome(
            local_process_group_terminated=False,
            provider_server_state="UNAVAILABLE",
            ownership_confirmed=True,
        ),
    )

    refusal = bounded_review_script.compose_bounded_technical_review_cancellation(
        ledger_path=ledger_path,
        identity_key=identity_key,
        repository=repository,
        pid=424242,
        owned_process_identity="424242:1",
    )
    assert refusal["decision"] == "CANCELLATION_REFUSED", refusal
    assert refusal["reason"] == "PROCESS_GROUP_NOT_CONFIRMED_TERMINATED", refusal

    # Never recorded as a terminal outcome -- the claim is still cancellable, never silently
    # resolved by a cancellation this route never actually confirmed.
    claim = read_claim(ledger_path, identity_key, repository=repository)
    assert claim is not None
    assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
    assert claim["resolution_kind"] is None


def test_sr3_f4_cmd_cancel_cli_routes_through_the_composed_cancellation_route(
    tmp_path: Path,
) -> None:
    """The exact SR3-F4 reproduction (PR #112 comment 6030487245): before this correction,
    the CLI's own ``cancel`` subcommand called the generic ``cancel_review_task`` adapter
    primitive directly -- the one real CLI effect this delivery's own cancel surface could
    reach completely bypassed the claim-bound ``compose_bounded_technical_review_cancellation``
    route, so an unrelated process's own genuine pid/identity (never bound to any ledger
    claim) could still be cancelled through this CLI, with no claim check at all."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR3-F4-CLI",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR3-F4-CLI",
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

        refused_args = argparse.Namespace(
            ledger_file=ledger_path,
            identity_key=identity_key,
            pid=unrelated_process.pid,
            owned_process_identity=unrelated_identity,
            repository=repository,
        )
        refused_exit_code = bounded_review_script.cmd_cancel(refused_args, io.StringIO())
        assert refused_exit_code != 0
        # The unrelated process -- never bound to this claim -- was never touched.
        assert unrelated_process.poll() is None

        confirmed_args = argparse.Namespace(
            ledger_file=ledger_path,
            identity_key=identity_key,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            repository=repository,
        )
        confirmed_out = io.StringIO()
        confirmed_exit_code = bounded_review_script.cmd_cancel(confirmed_args, confirmed_out)
        assert confirmed_exit_code == 0
        confirmed = json.loads(confirmed_out.getvalue())
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed

        # SR5-F4 correction (PR #112 comment 6034603745): the claim is never resolved by a
        # confirmed local-only cancellation -- the slot stays retained.
        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
        assert claim["resolution_kind"] is None
        assert claim["local_cancellation_confirmed_at"] is not None
    finally:
        for process in (owned_process, unrelated_process):
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)


# --------------------------------------------------------------------------- #
# SR4-F4 corrections (PR #112 comment 6032479337), adopted
# ADOPT_I109_PR112_SR4_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr4_f4_a_cancellation_is_never_reported_as_the_unqualified_confirmed_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact SR4-F4 reproduction (PR #112 comment 6032479337): a controlled fixture with
    ``local_process_group_terminated=True`` but ``provider_server_state=UNAVAILABLE`` (this
    delivery's own permanent, never-anything-else report of the provider/task's own state)
    still reached the unqualified ``"CANCELLATION_CONFIRMED"`` decision -- overclaiming across
    two facts the adapter itself never conflates. Fixed: the success decision is now
    ``"CANCELLATION_CONFIRMED_LOCAL_ONLY"``, never the unqualified string, for every real
    cancellation this route can ever confirm (``provider_server_state`` is always
    ``"UNAVAILABLE"`` in this delivery -- see ``review_adapter``'s own module docstring)."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR4-F4-CONFIRMED-LOCAL-ONLY",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR4-F4-CONFIRMED-LOCAL-ONLY",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )
    bounded_review_script.confirm_dispatch_sent(
        ledger_path, identity_key, repository=repository, pid=525252, process_identity="525252:1"
    )

    monkeypatch.setattr(
        bounded_review_script,
        "cancel_review_task",
        lambda *, pid, owned_process_identity: bounded_review_script.CancellationOutcome(
            local_process_group_terminated=True,
            provider_server_state="UNAVAILABLE",
            ownership_confirmed=True,
        ),
    )

    confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
        ledger_path=ledger_path,
        identity_key=identity_key,
        repository=repository,
        pid=525252,
        owned_process_identity="525252:1",
    )
    assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
    assert confirmed["decision"] != "CANCELLATION_CONFIRMED"
    assert confirmed["provider_server_state"] == "UNAVAILABLE"


def test_sr4_f4_record_outcome_cli_refuses_an_unbound_pid_and_identity(tmp_path: Path) -> None:
    """The exact SR4-F4 reproduction (PR #112 comment 6032479337): before this correction, the
    CLI's own ``record-outcome`` subcommand called the generic ``record_review_outcome`` ledger
    primitive directly -- a caller could resolve any ``DISPATCHED``/``ACK_UNKNOWN`` claim as
    ``FAILED``/``COLLECTED_RESULT`` with an arbitrary, invented ``result_bytes``, releasing the
    concurrency slot for a different identity with zero correlation to any actually-collected,
    actually-owned operation. Fixed: this CLI subcommand now requires the caller-supplied
    ``pid``/``owned_process_identity`` to exactly match the claim's own recorded launch
    identity, mirroring the identical ownership check ``cancel`` already enforces -- an
    unrelated pid/identity (never bound to this claim) is refused outright, before
    ``record_review_outcome`` is ever reached."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR4-F4-OUTCOME-UNBOUND",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR4-F4-OUTCOME-UNBOUND",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )
    bounded_review_script.confirm_dispatch_sent(
        ledger_path, identity_key, repository=repository, pid=636363, process_identity="636363:1"
    )

    result_bytes_file = tmp_path / "fabricated_result.txt"
    result_bytes_file.write_bytes(b"not a collected result")

    args = argparse.Namespace(
        ledger_file=ledger_path,
        identity_key=identity_key,
        pid=999999,
        owned_process_identity="999999:1",
        repository=repository,
        status="FAILED",
        resolution_kind=bounded_review_script.RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes_file=result_bytes_file,
    )
    exit_code = bounded_review_script.cmd_record_outcome(args, io.StringIO())
    assert exit_code != 0

    # Never recorded as a terminal outcome -- the claim is still exactly as dispatched, and the
    # concurrency slot is never released by an unbound caller's own fabricated bytes.
    claim = read_claim(ledger_path, identity_key, repository=repository)
    assert claim is not None
    assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
    assert claim["resolution_kind"] is None


def test_sr4_f4_record_outcome_cli_refuses_collected_result_even_for_the_genuinely_bound_pid(
    tmp_path: Path,
) -> None:
    """SR7-F2 correction (PR #112 comment 6037312445), superseding this test's own prior
    premise: this route previously accepted COLLECTED_RESULT for the real, bound pid/process
    identity this ledger itself recorded at dispatch time -- but matching pid/token ownership
    has never been, and can never be made, evidence that *result_bytes* was genuinely
    collected from that process; this external/CLI route has no provider API and keeps no
    durable record of what was actually captured, so it can never correlate caller-supplied
    bytes to anything real, regardless of how genuinely the pid/token themselves are bound.
    COLLECTED_RESULT is now refused unconditionally through this route; only the composed
    dispatch route itself, holding the real bytes at the moment of collection, ever records
    one."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR4-F4-OUTCOME-BOUND",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR4-F4-OUTCOME-BOUND",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )
    bounded_review_script.confirm_dispatch_sent(
        ledger_path, identity_key, repository=repository, pid=747474, process_identity="747474:1"
    )

    result_bytes_file = tmp_path / "real_result.txt"
    result_bytes_file.write_bytes(b"asserted without ever actually collecting it")

    args = argparse.Namespace(
        ledger_file=ledger_path,
        identity_key=identity_key,
        pid=747474,
        owned_process_identity="747474:1",
        repository=repository,
        status="FAILED",
        resolution_kind=bounded_review_script.RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes_file=result_bytes_file,
    )
    stdout = io.StringIO()
    exit_code = bounded_review_script.cmd_record_outcome(args, stdout)
    assert exit_code != 0
    assert "COLLECTED_RESULT_UNSUPPORTED_EXTERNALLY" in stdout.getvalue()

    claim = read_claim(ledger_path, identity_key, repository=repository)
    assert claim is not None
    assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
    assert claim["resolution_kind"] is None


def test_sr4_f4_a_claim_with_no_confirmed_pid_can_never_be_resolved_through_this_route(
    tmp_path: Path,
) -> None:
    """A claim left ``ACK_UNKNOWN`` with no real pid ever confirmed (``claim["pid"] is None``)
    -- e.g. a crash between ``record_dispatch_attempt`` and ``confirm_dispatch_sent`` -- has
    nothing real to correlate to, and this route never invents one: it is refused regardless of
    what the caller supplies, exactly the module's own "never auto-release" design for an
    abandoned claim."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR4-F4-OUTCOME-NO-PID",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR4-F4-OUTCOME-NO-PID",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    # Dispatch attempted, acknowledgement never confirmed, and the controller crashed before
    # ever calling `confirm_dispatch_sent` -- the claim's own `pid`/`process_identity` are both
    # still `None`.
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )

    # SR7-F2 correction (PR #112 comment 6037312445): RESOLUTION_KIND_COLLECTED_RESULT is now
    # refused unconditionally through this route before pid is ever checked --
    # CONFIRMED_CANCELLATION is the one resolution_kind still reachable here. SR8-F2
    # correction (PR #112 comment 6050757530): CONFIRMED_CANCELLATION is now *also* refused
    # unconditionally for this claim, since it never went through the real cancellation route
    # (no ``local_cancellation_confirmed_at`` marker was ever set) -- the former pid/token-
    # match check this test used to reach is no longer run at all, for any claim.
    decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
        ledger_path=ledger_path,
        identity_key=identity_key,
        repository=repository,
        status="FAILED",
        resolution_kind=bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION,
        pid=0,
        owned_process_identity="0:1",
        result_bytes=None,
    )
    assert decision["decision"] == "OUTCOME_REFUSED", decision
    assert decision["reason"] == "CONFIRMED_CANCELLATION_UNSUPPORTED_EXTERNALLY", decision

    claim = read_claim(ledger_path, identity_key, repository=repository)
    assert claim is not None
    assert claim["status"] == bounded_review_script.STATUS_ACK_UNKNOWN
    assert claim["resolution_kind"] is None


# --------------------------------------------------------------------------- #
# SR5-F4 corrections (PR #112 comment 6034603745), adopted
# ADOPT_I109_PR112_SR5_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr5_f4_a_confirmed_local_only_cancellation_retains_the_concurrency_slot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact SR5-F4 reproduction: before this correction, a confirmed local-only
    cancellation (``ownership_confirmed=True``, ``local_process_group_terminated=True``,
    ``provider_server_state=UNAVAILABLE``) still resolved the claim and released
    ``active_lock`` -- permitting a genuinely *different* identity to claim the repository's
    one concurrency slot while the provider/task's own state remained entirely unknown. Fixed:
    the slot is now retained, so a second, different identity is refused exactly as if the
    first claim were still live."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR5-F4-RETENTION",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR5-F4-RETENTION",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=repository, acknowledged=False
    )
    bounded_review_script.confirm_dispatch_sent(
        ledger_path, identity_key, repository=repository, pid=818181, process_identity="818181:1"
    )

    monkeypatch.setattr(
        bounded_review_script,
        "cancel_review_task",
        lambda *, pid, owned_process_identity: bounded_review_script.CancellationOutcome(
            local_process_group_terminated=True,
            provider_server_state="UNAVAILABLE",
            ownership_confirmed=True,
        ),
    )
    confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
        ledger_path=ledger_path,
        identity_key=identity_key,
        repository=repository,
        pid=818181,
        owned_process_identity="818181:1",
    )
    assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
    assert confirmed["concurrency_slot_retained"] is True

    claim = read_claim(ledger_path, identity_key, repository=repository)
    assert claim is not None
    assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
    assert claim["resolution_kind"] is None
    assert isinstance(claim["local_cancellation_confirmed_at"], str)
    assert claim["local_cancellation_confirmed_at"]

    # A genuinely different identity is refused the slot -- never silently released.
    other_identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR5-F4-RETENTION-OTHER",
        input_digest="a" * 64,
    )
    other_claim = claim_review_launch(
        ledger_path,
        identity_key=other_identity_key,
        work_unit_id="WORK-UNIT-SR5-F4-RETENTION-OTHER",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    assert other_claim["decision"] == REVIEW_CLAIM_REFUSED, other_claim
    assert "CONCURRENT_REVIEW_ACTIVE" in other_claim["reason_codes"], other_claim


def test_sr5_f4_outcome_recording_refuses_a_terminal_outcome_for_a_still_running_process(
    tmp_path: Path,
) -> None:
    """The exact SR5-F4 outcome-recording reproduction: matching ``pid``/
    ``owned_process_identity`` alone was previously sufficient to accept *any* caller-asserted
    terminal outcome, with no fresh check that the process genuinely terminated. A process that
    is -- freshly, independently re-verified at this exact instant -- still alive under the
    exact identity this claim owns is refused, never resolved on the caller's bare assertion.

    SR8-F2 correction (PR #112 comment 6050757530): the pid/token-match and fresh-liveness
    checks this test originally exercised are themselves now removed from :func:`compose_
    bounded_technical_review_outcome_recording` -- a claim with no genuine ``local_
    cancellation_confirmed_at`` marker refuses ``CONFIRMED_CANCELLATION`` unconditionally,
    before pid/liveness is ever inspected, regardless of whether the owned process happens to
    still be running. This still-running case is kept as its own regression precisely to prove
    that: the blanket refusal applies even here, where the former liveness check would also
    have refused it, for an entirely different (now-removed) reason."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR5-F4-STILL-RUNNING",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR5-F4-STILL-RUNNING",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen(
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

        # SR8-F2 correction (PR #112 comment 6050757530): CONFIRMED_CANCELLATION is refused
        # unconditionally here -- no local_cancellation_confirmed_at marker was ever set for
        # this claim -- before pid/liveness is ever inspected, so the still-running process
        # never even needs to be observed to be refused.
        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status="FAILED",
            resolution_kind=bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=None,
        )
        assert decision["decision"] == "OUTCOME_REFUSED", decision
        assert decision["reason"] == "CONFIRMED_CANCELLATION_UNSUPPORTED_EXTERNALLY", decision

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
        assert claim["resolution_kind"] is None
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
        owned_process.wait(timeout=5)


def test_sr6_f3_a_confirmed_local_cancellation_is_permanently_unresolvable_through_this_route(
    tmp_path: Path,
) -> None:
    """SR6-F3 correction (PR #112 comment 6036263982), adopted ADOPT_I109_PR112_SR6_F1_F4_20261007:
    this test's own prior premise -- that a genuinely, freshly confirmed-dead owned process let
    an operator still resolve a retained claim through ``compose_bounded_technical_review_
    outcome_recording`` -- was itself the SR6-F3 gap. Local process absence (whether natural
    exit or this ledger's own confirmed local-only cancellation) is not correlated collected-
    result evidence and not provider terminal confirmation, so a claim this ledger ever recorded
    a confirmed local-only cancellation for is now refused ``CLAIM_RETAINED_UNKNOWN_STATE``
    through this route forever, even once the owned process is confirmed genuinely gone -- the
    concurrency slot stays retained, resolvable only out-of-band."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR6-F3-RETAINED-UNKNOWN",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR6-F3-RETAINED-UNKNOWN",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen(
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

        confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
        )
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
        assert confirmed["concurrency_slot_retained"] is True
        owned_process.wait(timeout=5)

        # SR6-F3: even now the process is genuinely, freshly confirmed gone, this route
        # refuses outright -- local absence is not correlated terminal evidence.
        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status=bounded_review_script.STATUS_FAILED,
            resolution_kind=bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=None,
        )
        assert decision == {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "CLAIM_RETAINED_UNKNOWN_STATE",
        }, decision

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == "DISPATCHED"
        assert claim["resolution_kind"] is None

        other_identity_key = compute_identity_key(
            repository=repository,
            pull_request="#109",
            base_sha="a" * 40,
            head_sha="a" * 40,
            requirement_id="REQ-SR6-F3-RETAINED-UNKNOWN-OTHER",
            input_digest="a" * 64,
        )
        other_claim = claim_review_launch(
            ledger_path,
            identity_key=other_identity_key,
            work_unit_id="WORK-UNIT-SR6-F3-RETAINED-UNKNOWN-OTHER",
            repository=repository,
            now=_NOW,
            numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
        )
        assert other_claim["decision"] == REVIEW_CLAIM_REFUSED, other_claim
        assert other_claim["reason_codes"] == ["CONCURRENT_REVIEW_ACTIVE"], other_claim
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)


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


def test_sr3_f5_a_mask_list_that_omits_a_required_root_is_refused(tmp_path: Path) -> None:
    """The exact SR3-F5 reproduction (PR #112 comment 6030487245): before this correction, a
    non-empty ``mask_paths`` was itself sufficient -- it was never checked against anything
    the caller actually needed masked. A caller declaring the orchestrator's own source
    checkout as a required root, while a stale or incomplete ``mask_paths`` never actually
    covers it, is now refused outright rather than silently admitted."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    unrelated_mask = tmp_path / "unrelated"
    unrelated_mask.mkdir()

    with pytest.raises(ReviewAdapterError):
        mint_review_launch_admission_for_test_only_mechanics(
            argv=[sys.executable, "-c", "pass"],
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(unrelated_mask,),
            require_isolation=True,
            required_mask_roots=(source_root,),
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )

    # Once mask_paths genuinely covers every required root, the identical call is admitted.
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=[sys.executable, "-c", "pass"],
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=1024,
        mask_paths=(unrelated_mask, source_root),
        require_isolation=True,
        required_mask_roots=(source_root,),
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    assert token


# --------------------------------------------------------------------------- #
# SR4-F5 corrections (PR #112 comment 6032479337), adopted
# ADOPT_I109_PR112_SR4_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr4_f5_an_empty_required_mask_roots_is_refused_even_with_a_non_empty_mask_paths(
    tmp_path: Path,
) -> None:
    """The exact SR4-F5 reproduction (PR #112 comment 6032479337): before this correction,
    ``required_mask_roots`` defaulted to empty and this function never refused merely for it
    being empty -- a non-empty but entirely unrelated ``mask_paths`` (nothing sensitive ever
    named) was fully admitted under ``require_isolation=True``, with the SR3-F5 coverage check
    trivially satisfied by declaring zero required roots. Fixed: ``require_isolation=True``
    with an empty ``required_mask_roots`` is now refused outright, independent of whatever
    ``mask_paths`` itself contains."""

    unrelated_mask = tmp_path / "unrelated"
    unrelated_mask.mkdir()

    with pytest.raises(ReviewAdapterError):
        mint_review_launch_admission_for_test_only_mechanics(
            argv=[sys.executable, "-c", "pass"],
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(unrelated_mask,),
            require_isolation=True,
            required_mask_roots=(),
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )

    with pytest.raises(ReviewAdapterError):
        # required_mask_roots omitted entirely -- the same refusal, not merely one triggered
        # by explicitly passing an empty tuple.
        mint_review_launch_admission_for_test_only_mechanics(
            argv=[sys.executable, "-c", "pass"],
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(unrelated_mask,),
            require_isolation=True,
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )


def test_sr4_f5_launch_review_process_also_refuses_an_empty_required_mask_roots(
    tmp_path: Path,
) -> None:
    """The identical SR4-F5 refusal, proven through ``launch_review_process`` itself -- the
    thin composition wrapper this delivery's own tests use directly is bound by the same real
    gate as the composed route, never a separate, weaker one."""

    with pytest.raises(ReviewAdapterError):
        launch_review_process_for_test_only_mechanics(
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            env={},
            max_seconds=5,
            max_output_bytes=1024,
            clock=_clock,
            mask_paths=(tmp_path,),
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )


def test_sr3_f5_a_real_launched_namespace_masks_the_source_checkout_not_just_the_workspace(
    tmp_path: Path,
) -> None:
    """The exact SR3-F5 reproduction (PR #112 comment 6030487245): the read-only-remounted
    copied *workspace* alone never masked the original *source checkout* it was copied from --
    a launched process could still read a secret-shaped file there via its own absolute path.
    This proves the real launched namespace now masks the source checkout too, once it is
    named in ``mask_paths`` (as ``compose_bounded_technical_review_dispatch`` now requires via
    ``required_mask_roots``), not merely the separate staged workspace."""

    capability = check_isolation_capability()
    if not capability.available:
        pytest.skip(f"isolation unavailable in this environment: {capability.reason}")

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "SECRET.txt").write_text("not-a-real-secret\n", encoding="utf-8")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "staged.txt").write_text("staged\n", encoding="utf-8")

    probe_script = tmp_path / "probe.py"
    probe_script.write_text(
        textwrap.dedent(
            """
            import json, sys
            source_secret_path = sys.argv[1]
            results = {}
            try:
                with open(source_secret_path, encoding="utf-8") as handle:
                    handle.read()
                results["source_checkout_readable"] = True
            except OSError:
                results["source_checkout_readable"] = False
            print(json.dumps(results))
            """
        ),
        encoding="utf-8",
    )

    argv = build_isolated_argv(
        [sys.executable, str(probe_script), str(source_root / "SECRET.txt")],
        mask_paths=(source_root,),
        workspace_path=workspace,
    )
    completed = subprocess.run(  # noqa: S603 -- argv is a literal list this test built itself
        argv, capture_output=True, text=True, timeout=30
    )
    results = json.loads(completed.stdout.strip().splitlines()[-1])
    assert results["source_checkout_readable"] is False, results


# --------------------------------------------------------------------------- #
# SR5-F5 corrections (PR #112 comment 6034603745), adopted
# ADOPT_I109_PR112_SR5_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr5_f5_default_sensitive_mask_roots_always_includes_var_tmp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unit-level proof of :func:`default_sensitive_mask_roots` itself: ``/var/tmp`` is always
    present, and ``XDG_RUNTIME_DIR`` is folded in whenever the environment declares one."""

    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    roots = default_sensitive_mask_roots()
    assert Path("/var/tmp") in roots  # noqa: S108 -- asserting the ratified baseline root itself

    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/999999")
    roots_with_runtime_dir = default_sensitive_mask_roots()
    assert Path("/run/user/999999") in roots_with_runtime_dir
    assert Path("/var/tmp") in roots_with_runtime_dir  # noqa: S108


def test_sr5_f5_a_real_launched_namespace_hides_a_preexisting_same_uid_file_under_var_tmp(
    tmp_path: Path,
) -> None:
    """The exact SR5-F5 reproduction (PR #112 comment 6034603745): before this correction,
    ``build_isolated_argv`` masked only caller-selected ``mask_paths`` and remounted the
    staging workspace read-only -- a same-UID file elsewhere under ``/var/tmp``, never named by
    any caller's own ``required_mask_roots`` (the composed route's own ``[source_root,
    Path.home()]`` never named it either), remained fully readable from inside a launched
    process. This proves a real launched namespace now hides it unconditionally, with zero
    caller declaration of ``/var/tmp`` at all."""

    capability = check_isolation_capability()
    if not capability.available:
        pytest.skip(f"isolation unavailable in this environment: {capability.reason}")

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "staged.txt").write_text("staged\n", encoding="utf-8")

    same_uid_file = Path(
        tempfile.mkstemp(dir="/var/tmp", prefix="sr5-f5-same-uid-probe-", suffix=".txt")[1]
    )
    same_uid_file.write_text("not-a-real-secret\n", encoding="utf-8")
    try:
        probe_script = tmp_path / "probe.py"
        probe_script.write_text(
            textwrap.dedent(
                """
                import json, sys
                same_uid_path = sys.argv[1]
                results = {}
                try:
                    with open(same_uid_path, encoding="utf-8") as handle:
                        handle.read()
                    results["var_tmp_file_readable"] = True
                except OSError:
                    results["var_tmp_file_readable"] = False
                print(json.dumps(results))
                """
            ),
            encoding="utf-8",
        )

        # Zero mask_paths/required_mask_roots declared for /var/tmp at all -- this delivery's
        # own build_isolated_argv must hide it unconditionally, never dependent on a caller's
        # own declaration.
        argv = build_isolated_argv(
            [sys.executable, str(probe_script), str(same_uid_file)],
            mask_paths=(),
            workspace_path=workspace,
        )
        completed = subprocess.run(  # noqa: S603 -- argv is a literal list this test built itself
            argv, capture_output=True, text=True, timeout=30
        )
        results = json.loads(completed.stdout.strip().splitlines()[-1])
        assert results["var_tmp_file_readable"] is False, results
    finally:
        same_uid_file.unlink(missing_ok=True)


# --------------------------------------------------------------------------- #
# SR6-F1 corrections (PR #112 comment 6036263982), adopted
# ADOPT_I109_PR112_SR6_F1_F4_20261007.
# --------------------------------------------------------------------------- #

_GENERIC_TEST_AUTHENTICATION_REFUSED = {"decision": REVIEW_SELECTION_REFUSED}
_GENERIC_TEST_CLAIM_REFUSED = {"decision": REVIEW_CLAIM_REFUSED}


def test_sr6_f1_a_harmless_process_with_zero_authority_is_now_refused(tmp_path: Path) -> None:
    """The exact SR6-F1 reproduction (PR #112 comment 6036263982): before this correction, the
    identical argv/cwd/mask_paths/``require_isolation=False`` at both validation and spawn --
    not substitution, genuinely matching -- launched a real, harmless local subprocess with no
    selection/Authority/activation/claim check at all. Fixed: omitting either real Decision now
    refuses outright, before anything else is ever checked, closing the exact zero-context
    reproduction for every caller, including a future one that supplies no decisions at all."""

    harmless_argv = [sys.executable, "-c", "print('HARMLESS_NO_AUTHORITY')"]

    with pytest.raises(TypeError):
        mint_review_launch_admission_for_test_only_mechanics(  # type: ignore[call-arg]
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(),
            require_isolation=False,
        )

    with pytest.raises(ReviewAdapterError):
        mint_review_launch_admission_for_test_only_mechanics(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(),
            require_isolation=False,
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_REFUSED,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )

    with pytest.raises(ReviewAdapterError):
        mint_review_launch_admission_for_test_only_mechanics(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(),
            require_isolation=False,
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
            claim_decision=_GENERIC_TEST_CLAIM_REFUSED,
        )

    # The identical configuration, with both Decisions genuinely reporting admitted, is the
    # one case this remains the generic, directly-testable primitive for.
    token = mint_review_launch_admission_for_test_only_mechanics(
        argv=harmless_argv,
        cwd=tmp_path,
        max_seconds=5,
        max_output_bytes=1024,
        mask_paths=(),
        require_isolation=False,
        authentication_decision=_GENERIC_TEST_AUTHENTICATION_DECISION,
        claim_decision=_GENERIC_TEST_CLAIM_DECISION,
    )
    assert token


def test_sr6_f1_launch_review_process_also_requires_both_real_decisions(tmp_path: Path) -> None:
    """The identical SR6-F1 gate, proven through ``launch_review_process`` itself -- the thin
    composition wrapper this delivery's own tests use directly is bound by the same real gate
    as every other caller, never a separate, weaker one."""

    with pytest.raises(TypeError):
        launch_review_process_for_test_only_mechanics(  # type: ignore[call-arg]
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            env={},
            max_seconds=5,
            max_output_bytes=1024,
            clock=_clock,
            mask_paths=(tmp_path,),
            required_mask_roots=(tmp_path,),
        )

    with pytest.raises(ReviewAdapterError):
        launch_review_process_for_test_only_mechanics(
            [sys.executable, "-c", "pass"],
            cwd=tmp_path,
            env={},
            max_seconds=5,
            max_output_bytes=1024,
            clock=_clock,
            mask_paths=(tmp_path,),
            required_mask_roots=(tmp_path,),
            authentication_decision=_GENERIC_TEST_AUTHENTICATION_REFUSED,
            claim_decision=_GENERIC_TEST_CLAIM_DECISION,
        )


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
        "review_id": "6030487245",
        "reviewed_commit_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "inspected_base_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9011223344",
        "review_state": "APPROVED",
        "submitted_at": "2026-10-06T10:30:00Z",
        "inspected_paths": ["reviewed_native.py"],
        # SR4-F3 correction (PR #112 comment 6032479337): APPROVED + empty findings is no
        # longer VERIFIED on its own -- the default "genuinely complete" fixture now reports a
        # real PASS for the default grant's own permitted_checks (["CORRECTNESS"]).
        "findings": [{"check": "CORRECTNESS", "status": "PASS"}],
        "fetched_via": "github_mcp_pull_request_read",
        # SR5-F3 correction (PR #112 comment 6034603745): source_url/author/fetched_at are now
        # required -- the default fixture names a real-shaped review URL on the identical
        # (repository, pull_request) and a fresh fetched_at (identical to _NOW: zero age).
        "source_url": f"https://github.com/{_REPO}/pull/109#pullrequestreview-6030487245",
        # SR6-F2 correction (PR #112 comment 6036263982): author must now exactly match the
        # expected reviewer provenance the composed route cross-checks it against -- the
        # default grant's own inspector_session_ref (_F1_F2_VERIFIER_IDENTITY["id"]).
        "author": _F1_F2_VERIFIER_IDENTITY["id"],
        "fetched_at": _NOW,
    }
    base.update(overrides)
    return base


def _native_reuse_grant(**overrides: Any) -> dict[str, Any]:
    grant = _bounded_review_grant_record(permitted_paths=["reviewed_native.py"], **overrides)
    grant["api_read_back_receipt"]["permitted_paths"] = ["reviewed_native.py"]
    if "requirement_id" in overrides:
        grant["api_read_back_receipt"]["requirement_id"] = overrides["requirement_id"]
    return grant


def _compose_native_reuse(
    *, grant: dict[str, Any], now: str, ledger_path: Path, evidence: Mapping[str, Any]
) -> dict[str, Any]:
    """SR4-F3 correction (PR #112 comment 6032479337): the composed route no longer accepts a
    bare caller-supplied evidence mapping directly -- it requires a real (here, controlled
    fake) ``NativeReviewTransport`` and cross-checks what it returns. This helper is this
    file's own equivalent of a caller handing it a transport that happens to already have the
    evidence in hand."""

    return bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant,
        now=now,
        ledger_path=ledger_path,
        transport=_FakeNativeReviewTransport(evidence),
        review_id=evidence["review_id"],
    )


def test_native_reuse_a_relevant_approved_review_is_verified_and_not_deduplicated(
    tmp_path: Path,
) -> None:
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "VERIFIED"
    assert result["deduplicated"] is False


def test_native_reuse_the_identical_review_is_deduplicated_on_a_second_import(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "ledger.json"
    grant = _native_reuse_grant()
    first = _compose_native_reuse(
        grant=grant, now=_NOW, ledger_path=ledger_path, evidence=_native_evidence()
    )
    second = _compose_native_reuse(
        grant=grant, now=_NOW, ledger_path=ledger_path, evidence=_native_evidence()
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
    first = _compose_native_reuse(
        grant=grant, now=_NOW, ledger_path=ledger_path, evidence=_native_evidence()
    )
    second = _compose_native_reuse(
        grant=grant,
        now=_NOW,
        ledger_path=ledger_path,
        evidence=_native_evidence(
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
        ({"inspected_paths": []}, "NATIVE_COVERAGE_INSUFFICIENT_FOR_GRANT_SCOPE"),
    ],
    ids=[
        "base-unknown-never-fabricated",
        "base-stale-distinct-from-unknown",
        "inspected-base-unknown-never-fabricated",
        "inspected-base-stale-distinct-from-unknown",
        "coverage-insufficient",
    ],
)
def test_native_reuse_an_irrelevant_review_is_refused_before_any_classification(
    tmp_path: Path, overrides: dict[str, Any], expected_reason: str
) -> None:
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(**overrides),
    )
    assert result["stage"] == "native-relevance"
    assert expected_reason in result["decision"]["decision_reason_codes"]


@pytest.mark.parametrize(
    "overrides",
    [{"repository": "someone/else"}, {"pull_request": "#999"}],
    ids=["repository-mismatch", "pull-request-mismatch"],
)
def test_sr4_f3_a_repository_or_pull_request_mismatch_is_refused_at_acquisition_not_relevance(
    tmp_path: Path, overrides: dict[str, Any]
) -> None:
    """SR4-F3 correction (PR #112 comment 6032479337): now that the composed route acquires
    evidence through :func:`~manosube_agent_civilization.development_binding.review_adapter.
    fetch_trusted_native_review_evidence`, a transport response whose own ``repository``/
    ``pull_request`` fields do not match what was actually requested is refused at the
    acquisition stage itself -- it never reaches the relevance stage's own (now redundant for
    this specific case) checks at all."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(**overrides),
    )
    assert result["stage"] == "native-acquisition"
    assert "error" in result


def test_native_reuse_a_commented_review_with_no_findings_is_not_auto_verified(
    tmp_path: Path,
) -> None:
    """The design supplement's own explicit requirement: absence of findings is never itself
    VERIFIED -- only an affirmative ``APPROVED`` disposition is."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(review_state="COMMENTED"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "INSUFFICIENT"


def test_native_reuse_a_still_running_review_is_unavailable_and_triggers_no_local_launch(
    tmp_path: Path,
) -> None:
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(review_state="PENDING"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "UNAVAILABLE"


def test_native_reuse_a_changes_requested_review_is_failed(tmp_path: Path) -> None:
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(review_state="CHANGES_REQUESTED"),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "FAILED"


def test_native_reuse_unreadable_evidence_raises_rather_than_silently_proceeding(
    tmp_path: Path,
) -> None:
    """SR4-F3 correction (PR #112 comment 6032479337): the composed route now wraps the
    *acquisition* step itself -- malformed evidence from the transport is refused as a
    reported ``native-acquisition`` stage, never silently proceeding, and never an uncaught
    exception escaping this function's own callers."""

    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        transport=_FakeNativeReviewTransport({"not": "the right shape"}),
        review_id="6030487245",
    )
    assert result["stage"] == "native-acquisition"
    assert "error" in result


def test_native_reuse_never_claims_a_local_concurrency_slot_or_daily_budget(
    tmp_path: Path,
) -> None:
    """Zero local launch reservation (the design supplement's own requirement): the ledger's
    own ``claims``/``jst_day_counts``/``active_lock`` stay completely empty after a native
    import -- only ``native_imports`` is ever written by this route."""

    ledger_path = tmp_path / "ledger.json"
    _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=ledger_path,
        evidence=_native_evidence(),
    )
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["claims"] == {}
    assert ledger["jst_day_counts"] == {}
    assert ledger["active_lock"] is None
    assert len(ledger["native_imports"]) == 1


# --------------------------------------------------------------------------- #
# SR3-F3 corrections (PR #112 comment 6030487245), adopted
# ADOPT_I109_PR112_SR3_F1_F5_E1_20261007.
# --------------------------------------------------------------------------- #


def test_sr3_f3_an_invented_non_numeric_review_id_is_refused() -> None:
    """The exact SR3-F3 reproduction: before this correction, any non-empty string --
    including an obviously invented one -- satisfied `review_id`."""

    with pytest.raises(ReviewAdapterError):
        validate_native_review_evidence(_native_evidence(review_id="NATIVE-REVIEW-ROUTE-1"))


def test_sr3_f3_an_invalid_submitted_at_timestamp_is_refused() -> None:
    """The exact SR3-F3 reproduction: `submitted_at="not-a-time"` previously passed shape
    validation merely by being a non-empty string."""

    with pytest.raises(ReviewAdapterError):
        validate_native_review_evidence(_native_evidence(submitted_at="not-a-time"))


class _FakeNativeReviewTransport:
    def __init__(self, evidence: Mapping[str, Any]) -> None:
        self._evidence = evidence

    def fetch_native_review(
        self, *, repository: str, pull_request: str, review_id: str
    ) -> Mapping[str, Any]:
        return self._evidence


def test_sr3_f3_fetch_trusted_native_review_evidence_succeeds_for_a_matching_transport() -> None:
    evidence = _native_evidence()
    transport = _FakeNativeReviewTransport(evidence)
    fetched = fetch_trusted_native_review_evidence(
        transport,
        repository=evidence["repository"],
        pull_request=evidence["pull_request"],
        review_id=evidence["review_id"],
        expected_author=evidence["author"],
    )
    assert fetched["review_id"] == evidence["review_id"]


def test_sr3_f3_fetch_trusted_native_review_evidence_refuses_a_mismatched_review_id() -> None:
    """A transport that returns evidence for a *different* review than the one requested is
    refused outright, never silently accepted as if it answered the request actually made."""

    evidence = _native_evidence()
    transport = _FakeNativeReviewTransport(evidence)
    with pytest.raises(ReviewAdapterError):
        fetch_trusted_native_review_evidence(
            transport,
            repository=evidence["repository"],
            pull_request=evidence["pull_request"],
            review_id="999999999",
            expected_author=evidence["author"],
        )


def test_sr3_f3_an_approved_review_with_a_blocking_finding_is_failed_not_verified(
    tmp_path: Path,
) -> None:
    """The exact SR3-F3 reproduction (PR #112 comment 6030487245): `review_state == "APPROVED"`
    mapped straight to VERIFIED with no check of the evidence's own findings at all."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(
            findings=[{"check": "CORRECTNESS", "status": "FAIL", "severity": "P1"}]
        ),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "FAILED"


def test_sr3_f3_a_different_requirement_reusing_identical_evidence_is_not_deduplicated(
    tmp_path: Path,
) -> None:
    """The exact SR3-F3 reproduction: a second grant naming a genuinely different
    `requirement_id`, reusing byte-identical already-fetched native evidence, previously
    content-addressed identically to the first import and so returned the first import's own
    cached classification -- a dedup collision across requests, never a real check for the new
    request's own identity."""

    ledger_path = tmp_path / "ledger.json"
    evidence = _native_evidence()
    first = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=ledger_path,
        evidence=evidence,
    )
    second = _compose_native_reuse(
        grant=_native_reuse_grant(requirement_id="DIFFERENT-REQUIREMENT-ID"),
        now=_NOW,
        ledger_path=ledger_path,
        evidence=evidence,
    )
    assert first["deduplicated"] is False
    assert second["deduplicated"] is False
    assert second["content_address"] != first["content_address"]


# --------------------------------------------------------------------------- #
# SR4-F3 corrections (PR #112 comment 6032479337), adopted
# ADOPT_I109_PR112_SR4_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr4_f3_the_composed_route_no_longer_accepts_a_bare_evidence_mapping() -> None:
    """The exact SR4-F3 reproduction (PR #112 comment 6032479337): a hand-typed, invented
    mapping -- an obviously fabricated numeric ``review_id``, ``fetched_via="I_TYPED_THIS"`` --
    satisfied every shape check and was fully imported with zero acquisition this route could
    ever distinguish from a genuine one. Fixed: ``native_evidence`` is no longer a parameter of
    this route at all -- a caller attempting the exact prior call shape now fails structurally,
    before any evidence (fabricated or genuine) is ever evaluated."""

    fabricated_evidence = _native_evidence(review_id="999999999", fetched_via="I_TYPED_THIS")
    with pytest.raises(TypeError):
        bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
            grant=_native_reuse_grant(),
            now=_NOW,
            ledger_path=Path("/nonexistent/ledger.json"),
            native_evidence=fabricated_evidence,  # type: ignore[call-arg]
        )


def test_sr4_f3_an_approved_review_with_no_findings_for_the_permitted_check_is_insufficient(
    tmp_path: Path,
) -> None:
    """The exact SR4-F3 reproduction: an ``APPROVED`` review with ``findings=[]`` (no condition
    evidence whatsoever for the grant's own ``permitted_checks``) was still fully
    :data:`VERIFICATION_VERIFIED`. Fixed: every one of the grant's ``permitted_checks`` must
    have at least one finding reporting on it, by name, or the result is
    :data:`VERIFICATION_INSUFFICIENT`."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(findings=[]),
    )
    assert result["stage"] == "complete"
    assert result["classification"] == "INSUFFICIENT"


def test_sr4_f3_the_transport_is_genuinely_invoked_not_merely_accepted_as_a_parameter(
    tmp_path: Path,
) -> None:
    """Proves the transport is actually called -- not merely accepted and ignored -- by having
    a controlled fake transport raise if its own ``fetch_native_review`` method is never
    reached, and asserting the resulting evidence (only obtainable through that call) is the
    one actually classified."""

    call_count = 0
    evidence = _native_evidence(review_id="123456789")

    class _CountingTransport:
        def fetch_native_review(
            self, *, repository: str, pull_request: str, review_id: str
        ) -> Mapping[str, Any]:
            nonlocal call_count
            call_count += 1
            return evidence

    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        transport=_CountingTransport(),
        review_id="123456789",
    )
    assert call_count == 1
    assert result["stage"] == "complete"
    assert result["classification"] == "VERIFIED"


def test_sr4_f3_classify_native_review_result_requires_every_permitted_check_by_name() -> None:
    """Unit-level proof of the coverage logic itself, independent of the composed route:
    an ``APPROVED`` review reporting only ``CORRECTNESS`` is insufficient for a grant that also
    requires ``ROOT_CAUSE`` coverage."""

    evidence = _native_evidence(findings=[{"check": "CORRECTNESS", "status": "PASS"}])
    assert (
        bounded_review_script.classify_native_review_result(
            evidence, required_checks=["CORRECTNESS", "ROOT_CAUSE"]
        )
        == "INSUFFICIENT"
    )
    assert (
        bounded_review_script.classify_native_review_result(
            evidence, required_checks=["CORRECTNESS"]
        )
        == "VERIFIED"
    )


def test_sr4_f3_a_later_pass_never_overwrites_an_earlier_fail_for_the_identical_check() -> None:
    """The identical SR4-F2 monotonic-failure design, enforced here for native evidence too: a
    ``FAIL`` recorded for a check must never be silently superseded by a later ``PASS`` for that
    same check within the same evidence's own findings."""

    evidence = _native_evidence(
        findings=[
            {"check": "CORRECTNESS", "status": "FAIL"},
            {"check": "CORRECTNESS", "status": "PASS"},
        ]
    )
    assert (
        bounded_review_script.classify_native_review_result(
            evidence, required_checks=["CORRECTNESS"]
        )
        == "FAILED"
    )


def test_sr4_f3_an_unattributed_fail_is_never_silently_dropped() -> None:
    """A ``FAIL`` finding with no recognized ``check`` name must still fail the whole result,
    even when every named, required check otherwise reports ``PASS``."""

    evidence = _native_evidence(
        findings=[
            {"check": "CORRECTNESS", "status": "PASS"},
            {"status": "FAIL"},
        ]
    )
    assert (
        bounded_review_script.classify_native_review_result(
            evidence, required_checks=["CORRECTNESS"]
        )
        == "FAILED"
    )


# --------------------------------------------------------------------------- #
# SR5-F3 corrections (PR #112 comment 6034603745), adopted
# ADOPT_I109_PR112_SR5_F1_F5_20261007.
# --------------------------------------------------------------------------- #


def test_sr5_f3_native_evidence_with_no_source_url_author_or_fetched_at_is_refused() -> None:
    """The exact SR5-F3 reproduction: before this correction, native review evidence carried
    no ``source_url``/``author``/``fetched_at`` at all -- a hand-typed mapping with matching
    ids/base/head and ``fetched_via="I_TYPED_THIS"`` satisfied every shape check. Each of the
    three new required fields, when missing or malformed, is now refused outright."""

    evidence = _native_evidence()
    del evidence["source_url"]
    with pytest.raises(ReviewAdapterError):
        validate_native_review_evidence(evidence)

    with pytest.raises(ReviewAdapterError):
        validate_native_review_evidence(_native_evidence(author=""))

    with pytest.raises(ReviewAdapterError):
        validate_native_review_evidence(_native_evidence(fetched_at="not-a-time"))


def test_sr5_f3_fetch_trusted_native_review_evidence_refuses_a_source_url_for_a_different_pr() -> (
    None
):
    """A transport that returns a well-shaped ``source_url`` -- naming a *different* PR than
    the one actually requested -- is refused outright, never silently accepted merely because
    every other field (ids, base/head) happened to match."""

    evidence = _native_evidence(
        source_url=f"https://github.com/{_REPO}/pull/999#pullrequestreview-6030487245"
    )
    transport = _FakeNativeReviewTransport(evidence)
    with pytest.raises(ReviewAdapterError):
        fetch_trusted_native_review_evidence(
            transport,
            repository=evidence["repository"],
            pull_request=evidence["pull_request"],
            review_id=evidence["review_id"],
            expected_author=evidence["author"],
        )


def test_sr5_f3_a_stale_native_fetch_is_refused_at_the_freshness_stage(tmp_path: Path) -> None:
    """The exact SR5-F3 freshness reproduction: a fetched_at far in the past (never itself
    grounds to doubt submitted_at, which may legitimately be old) is refused before relevance
    or classification is ever reached."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(fetched_at="1900-01-01T00:00:00Z"),
    )
    assert result["stage"] == "native-freshness", result
    assert result["reason"] == "NATIVE_FETCH_STALE", result
    assert result["fetched_at_age_seconds"] > 0


def test_sr5_f3_a_native_fetch_claiming_to_be_from_the_future_is_also_refused(
    tmp_path: Path,
) -> None:
    """The symmetric case: a ``fetched_at`` impossibly after *now* is equally never trusted."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(fetched_at="2099-01-01T00:00:00Z"),
    )
    assert result["stage"] == "native-freshness", result
    assert result["reason"] == "NATIVE_FETCH_STALE", result
    assert result["fetched_at_age_seconds"] < 0


def test_sr5_f3_a_fresh_native_fetch_still_reaches_complete(tmp_path: Path) -> None:
    """The positive control: a genuinely fresh ``fetched_at`` (identical to the default fixture)
    is never itself refused -- this correction narrows nothing beyond the exact stale/future
    reproduction above."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(),
    )
    assert result["stage"] == "complete", result
    assert result["classification"] == "VERIFIED", result


_SR5_F3_VERIFIER_IDENTITY = {
    "kind": "bounded_codex_technical_reviewer",
    "id": "codex-session-sr5-f3-native-evidence",
}
_SR5_F3_REQUIREMENT_ID = "REQ-I109-SR5-F3-NATIVE-EVIDENCE"
_SR5_F3_WORK_UNIT_ID = "WORK-UNIT-I109-SR5-F3-NATIVE-EVIDENCE"


def test_sr5_f3_the_native_reuse_route_performs_a_correlated_real_evidence_handoff_when_asked(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """Before this correction, ``compose_bounded_technical_review_native_reuse_dispatch`` had
    no Evidence-layer handoff of its own at all -- it stopped at the ledger import/
    classification, leaving every caller wanting a real :mod:`~manosube_agent_civilization.
    independent_verification` record to hand-assemble the identical sequence the local
    dispatch route's own ``evidence_handoff`` already performs. Fixed: this route now performs
    the identical real handoff, through the identical unmodified ``_hand_off_to_evidence``,
    for this exact (requirement, permitted_boundary) scope."""

    grant = _native_reuse_grant(
        requirement_id=_SR5_F3_REQUIREMENT_ID,
        work_unit_id=_SR5_F3_WORK_UNIT_ID,
        invoked_work_unit_id=_SR5_F3_WORK_UNIT_ID,
    )
    grant["api_read_back_receipt"]["work_unit_id"] = _SR5_F3_WORK_UNIT_ID
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR5-F3-NATIVE-EVIDENCE",
        requirement_id=_SR5_F3_REQUIREMENT_ID,
        selection_id=_SR5_F3_WORK_UNIT_ID,
        verifier_identity=_SR5_F3_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

    requirement = VerificationRequirement(
        requirement_id=grant["requirement_id"],
        project_id=_bound_route["project_id"],
        target_refs=[{"kind": "observation_evidence", "id": _bound_route["evidence_id"]}],
        verification_boundary=dict(permitted_boundary),
        required_conditions={"minimum_distinctness": "DISTINCT_LINEAGE"},
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
    )
    selection = VerifierSelection(
        selection_id=grant["work_unit_id"],
        project_id=_bound_route["project_id"],
        requirement_id=grant["requirement_id"],
        status="ACTIVE",
        selection_authority_ref=dict(_bound_route["human_authority_ref"]),
        verifier_identity=dict(_SR5_F3_VERIFIER_IDENTITY),
        permitted_boundary=dict(permitted_boundary),
    )

    result = bounded_review_script.compose_bounded_technical_review_native_reuse_dispatch(
        grant=grant,
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        transport=_FakeNativeReviewTransport(_native_evidence()),
        review_id=_native_evidence()["review_id"],
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        evidence_handoff={
            "verification_requirement": requirement,
            "verifier_selection": selection,
            "evidence_request": _evidence_request_for_project(_bound_route["project_id"]),
        },
    )
    assert result["stage"] == "complete", result
    assert result["classification"] == "VERIFIED", result
    assert "evidence" in result, result
    assert result["evidence"]["target"]["project_id"] == _bound_route["project_id"]


# --------------------------------------------------------------------------- #
# SR6-F2 corrections (PR #112 comment 6036263982), adopted
# ADOPT_I109_PR112_SR6_F1_F4_20261007.
# --------------------------------------------------------------------------- #


def test_sr6_f2_a_different_origin_is_refused_despite_a_matching_path(tmp_path: Path) -> None:
    """The exact SR6-F2 reproduction (PR #112 comment 6036263982): before this correction, the
    source_url cross-check was a bare substring test with no check of the URL's own origin at
    all -- a transport returning ``https://example.invalid/{repository}/pull/{pull_request}``
    (a real path fragment, on a completely different origin) still satisfied it."""

    evidence = _native_evidence(
        source_url=f"https://example.invalid/{_REPO}/pull/109#pullrequestreview-6030487245"
    )
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=evidence,
    )
    assert result["stage"] == "native-acquisition", result


def test_sr6_f2_a_pull_request_number_that_merely_begins_with_the_requested_one_is_refused(
    tmp_path: Path,
) -> None:
    """The exact SR6-F2 reproduction: the old substring check let a PR number with an extra
    ``999`` suffix (``109999`` for a requested ``109``) satisfy it, since ``"/pull/109"`` is a
    substring of ``"/pull/109999"``. The new exact-path-segment check refuses this."""

    evidence = _native_evidence(
        source_url=f"https://github.com/{_REPO}/pull/109999#pullrequestreview-6030487245"
    )
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=evidence,
    )
    assert result["stage"] == "native-acquisition", result


def test_sr6_f2_an_unrelated_author_is_refused_even_with_every_other_field_matching(
    tmp_path: Path,
) -> None:
    """The exact SR6-F2 reproduction: ``author`` was previously required only to be a
    non-empty string -- any value, including a genuinely unrelated account's own real login,
    satisfied it. The composed route now cross-checks it against the grant's own declared
    ``inspector_session_ref``."""

    evidence = _native_evidence(author="unrelated-user")
    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=evidence,
    )
    assert result["stage"] == "native-acquisition", result
    assert "error" in result, result


def test_sr6_f2_a_genuinely_matching_origin_path_and_author_still_reaches_complete(
    tmp_path: Path,
) -> None:
    """The positive control: the default fixture's own real-shaped ``source_url`` (``https://
    github.com/...``, exact repository/PR path) and matching ``author`` are never themselves
    refused -- this correction narrows nothing beyond the exact reproductions above."""

    result = _compose_native_reuse(
        grant=_native_reuse_grant(),
        now=_NOW,
        ledger_path=tmp_path / "ledger.json",
        evidence=_native_evidence(),
    )
    assert result["stage"] == "complete", result
    assert result["classification"] == "VERIFIED", result


def test_sr6_f2_fetch_trusted_native_review_evidence_refuses_a_non_https_source_url() -> None:
    """Unit-level proof of :func:`_require_genuine_native_review_source_url`'s own origin
    check, independent of the composed route: a non-``https`` scheme is refused outright."""

    evidence = _native_evidence(source_url=f"http://github.com/{_REPO}/pull/109")
    transport = _FakeNativeReviewTransport(evidence)
    with pytest.raises(ReviewAdapterError):
        fetch_trusted_native_review_evidence(
            transport,
            repository=evidence["repository"],
            pull_request=evidence["pull_request"],
            review_id=evidence["review_id"],
            expected_author=evidence["author"],
        )


# --------------------------------------------------------------------------- #
# SR6-F3 corrections (PR #112 comment 6036263982), adopted
# ADOPT_I109_PR112_SR6_F1_F4_20261007.
# --------------------------------------------------------------------------- #


def test_sr6_f3_an_invented_collected_result_after_local_cancellation_is_refused(
    tmp_path: Path,
) -> None:
    """The exact SR6-F3 reproduction: in the identical ledger a confirmed local-only
    cancellation had just retained (``provider_server_state=UNAVAILABLE``, the concurrency
    slot still held), the owned process's now-absent identity token previously let through an
    invented, never-actually-collected ``result_bytes`` as a genuine ``COLLECTED_RESULT`` --
    releasing the slot with the provider/task's own state still genuinely unknown. This route
    now refuses outright, ``CLAIM_RETAINED_UNKNOWN_STATE``, before ever looking at
    *result_bytes* at all."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR6-F3-INVENTED-COLLECTED-RESULT",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR6-F3-INVENTED-COLLECTED-RESULT",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen(
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

        confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
        )
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
        assert confirmed["concurrency_slot_retained"] is True
        owned_process.wait(timeout=5)
        assert process_identity_token(owned_process.pid) is None

        # SR7-F2 correction (PR #112 comment 6037312445): COLLECTED_RESULT is now refused
        # unconditionally through this route, before claim["local_cancellation_confirmed_at"]
        # is ever inspected -- the identical invented-bytes reproduction below is still
        # refused, now for the broader reason; test_sr7_f2_* below separately proves
        # CLAIM_RETAINED_UNKNOWN_STATE itself remains reachable for a CONFIRMED_CANCELLATION
        # re-attempt against an already-cancellation-marked claim.
        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status=bounded_review_script.STATUS_FAILED,
            resolution_kind=bounded_review_script.RESOLUTION_KIND_COLLECTED_RESULT,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=b"not a collected result",
        )
        assert decision == {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "COLLECTED_RESULT_UNSUPPORTED_EXTERNALLY",
        }, decision

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == "DISPATCHED"
        assert claim["result_digest"] is None

        other_identity_key = compute_identity_key(
            repository=repository,
            pull_request="#109",
            base_sha="a" * 40,
            head_sha="a" * 40,
            requirement_id="REQ-SR6-F3-INVENTED-COLLECTED-RESULT-OTHER",
            input_digest="a" * 64,
        )
        other_claim = claim_review_launch(
            ledger_path,
            identity_key=other_identity_key,
            work_unit_id="WORK-UNIT-SR6-F3-INVENTED-COLLECTED-RESULT-OTHER",
            repository=repository,
            now=_NOW,
            numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
        )
        assert other_claim["decision"] == REVIEW_CLAIM_REFUSED, other_claim
        assert other_claim["reason_codes"] == ["CONCURRENT_REVIEW_ACTIVE"], other_claim
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)


# --------------------------------------------------------------------------- #
# SR6-F4 correction (PR #112 comment 6036263982), adopted
# ADOPT_I109_PR112_SR6_F1_F4_20261007.
# --------------------------------------------------------------------------- #


def test_sr6_f4_omitting_build_argv_refuses_before_any_process_is_started(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR6-F4 correction: a real local launch's own argv would reference *prompt_path* and
    *codex_executable*, neither of which lives under *workspace* -- the one root this module's
    own isolation ever explicitly preserves before masking the rest of the platform temp
    directory. This delivery has never consolidated those paths under one explicitly preserved
    root, so the composed route now refuses outright, before send, whenever *build_argv* is
    omitted -- the slot is released unsent, never recorded as a false outcome, and no process
    is ever started."""

    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "reviewed_f1_f2.py").write_text("ORIGINAL\n", encoding="utf-8")

    workspace = prepare_inspection_workspace(source_root, permitted_paths=["reviewed_f1_f2.py"])
    try:
        real_digest = bounded_review_script.digest_inspection_input(workspace)
    finally:
        cleanup_inspection_workspace(workspace)

    grant = _bounded_review_grant_record(input_digest=real_digest)
    grant["api_read_back_receipt"]["input_digest"] = real_digest
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(["reviewed_f1_f2.py"]),
        "permitted_checks_digest": canonical_list_digest(["CORRECTNESS"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR6-F4",
        requirement_id=_F1_F2_REQUIREMENT_ID,
        selection_id=_F1_F2_WORK_UNIT_ID,
        verifier_identity=_F1_F2_VERIFIER_IDENTITY,
        permitted_boundary=permitted_boundary,
    )

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
        now_provider=lambda: _NOW,
        ledger_path=ledger_path,
        activation_evidence=activation_evidence,
        store=_bound_route["store"],
        project_id=_bound_route["project_id"],
        project_binding_id=_bound_route["project_binding_id"],
        verifier_selection_grant_refs=[committed["grant_ref"]],
        human_grant_declaration_refs=[committed["declaration_ref"]],
        live_state_transport=_DEFAULT_LIVE_TRANSPORT,
        source_root=source_root,
        codex_executable=sys.executable,
        prompt_path=tmp_path / "prompt.md",
        orchestrator_env={"PATH": os.environ.get("PATH", "/usr/bin")},
        mask_paths=(*_DEFAULT_TEST_MASK_PATHS, source_root),
    )

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    assert result == {
        "stage": "local-dispatch-boundary",
        "identity_key": identity_key,
        "reason": "INCOMPLETE_FILESYSTEM_BOUNDARY",
    }, result

    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_ABANDONED_UNSENT
    assert claim["dispatch_attempts"] == 0
    assert claim["pid"] is None


# --------------------------------------------------------------------------- #
# SR7-F3 correction (PR #112 comment 6037312445), adopted
# ADOPT_I109_PR112_SR7_F1_F3_20261008.
# --------------------------------------------------------------------------- #


def test_sr8_f3_the_production_dispatch_entry_accepts_no_filesystem_boundary_opt_out(
    tmp_path: Path,
) -> None:
    """The exact SR7-F3 reproduction (PR #112 comment 6037312445) -- a caller supplying *any*
    ``build_argv`` callable, including one constructing the identical real local Codex argv the
    omitted default would have built, bypassing the boundary refusal -- was closed at that
    round only by an explicit, test-only ``acknowledge_incomplete_filesystem_boundary_for_
    test_only`` flag, which the independent review then named as the next gap in its own right
    (SR8-F3, PR #112 comment 6050757530): "setting it ``True`` plus supplying any ``build_
    argv`` bypasses the ``INCOMPLETE_FILESYSTEM_BOUNDARY`` refusal entirely... Remove this
    caller opt-out from production capability."

    Fixed: ``compose_bounded_technical_review_dispatch``'s own public signature has no
    ``build_argv`` parameter, and no boundary-acknowledgement parameter of any kind -- there is
    nothing a caller, including a future one, could ever pass to this function to reach past
    its own ``INCOMPLETE_FILESYSTEM_BOUNDARY`` refusal
    (``test_sr6_f4_omitting_build_argv_refuses_before_any_process_is_started`` proves that
    refusal itself still fires). This is proven two ways: statically, the signature itself
    carries neither parameter; dynamically, supplying either one by keyword is rejected by
    Python's own argument binding -- a ``TypeError``, not a runtime refusal dict -- before this
    function's body, or any ledger/filesystem effect, ever runs."""

    signature_params = inspect.signature(
        bounded_review_script.compose_bounded_technical_review_dispatch
    ).parameters
    assert "build_argv" not in signature_params
    assert "acknowledge_incomplete_filesystem_boundary_for_test_only" not in signature_params

    common_kwargs: dict[str, Any] = {
        "grant": {},
        "now": _NOW,
        "ledger_path": tmp_path / "ledger.json",
        "activation_evidence": {},
        "store": None,
        "project_id": "",
        "project_binding_id": "",
        "verifier_selection_grant_refs": [],
        "human_grant_declaration_refs": [],
        "live_state_transport": _DEFAULT_LIVE_TRANSPORT,
        "source_root": tmp_path,
        "codex_executable": sys.executable,
        "prompt_path": tmp_path / "prompt.md",
        "orchestrator_env": {},
    }

    with pytest.raises(TypeError):
        bounded_review_script.compose_bounded_technical_review_dispatch(
            **common_kwargs,
            build_argv=lambda workspace: build_codex_review_argv(
                codex_executable=sys.executable,
                workspace=workspace,
                prompt_path=tmp_path / "prompt.md",
            ),
        )

    with pytest.raises(TypeError):
        bounded_review_script.compose_bounded_technical_review_dispatch(
            **common_kwargs,
            acknowledge_incomplete_filesystem_boundary_for_test_only=True,
        )


# --------------------------------------------------------------------------- #
# SR7-F1 correction (PR #112 comment 6037312445), adopted
# ADOPT_I109_PR112_SR7_F1_F3_20261008.
# --------------------------------------------------------------------------- #

_SR7_F1_VERIFIER_IDENTITY = {
    "kind": "bounded_codex_technical_reviewer",
    "id": "codex-session-sr7-f1-route-1",
}
_SR7_F1_REQUIREMENT_ID = "REQ-I109-SR7-F1-ROUTE-1"
_SR7_F1_WORK_UNIT_ID = "WORK-UNIT-I109-SR7-F1-ROUTE-1"
_SR7_F1_PERMITTED_BOUNDARY = {
    "permitted_paths": ["reviewed_sr7_f1.py"],
    "permitted_checks": ["CORRECTNESS"],
}


def test_sr7_f1_a_caller_with_no_real_grant_is_refused_zero_subprocess_effects(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """The exact SR7-F1 reproduction (PR #112 comment 6037312445): SR6-F1's own
    ``authentication_decision``/``claim_decision`` parameters were satisfied by two hand-typed
    dicts, ``{"decision": "REVIEW_SELECTION_ADMITTED"}``/``{"decision":
    "REVIEW_CLAIM_ADMITTED"}``, with no Authority/Store/ledger operation ever performed.
    ``require_authenticated_review_launch_admission`` is now the one function that can ever
    mint a local-launch admission token -- it calls the real ``authenticate_bounded_review_
    grant`` itself, so a caller supplying no genuine Store-resolved grant (the identical
    ``verifier_selection_grant_refs=[]`` forged-grant negative control F1's own test above
    already proves refuses ``authenticate_bounded_review_grant`` directly) is refused here
    too, before any admission token is ever minted and before any subprocess is ever
    started."""

    harmless_argv = [sys.executable, "-c", "print('HARMLESS_NO_AUTHORITY')"]
    ledger_path = tmp_path / "ledger.json"

    with pytest.raises(ReviewAdapterError):
        require_authenticated_review_launch_admission(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(tmp_path,),
            require_isolation=False,
            store=_bound_route["store"],
            project_id=_bound_route["project_id"],
            project_binding_id=_bound_route["project_binding_id"],
            requirement_id=_SR7_F1_REQUIREMENT_ID,
            selection_id=_SR7_F1_WORK_UNIT_ID,
            verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
            permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
            verifier_selection_grant_refs=[],
            human_grant_declaration_refs=[],
            ledger_path=ledger_path,
            identity_key="never-claimed-identity-key",
            repository=_REPO,
        )


def test_sr7_f1_a_genuine_grant_with_no_real_claim_is_refused(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """Authentication alone is never sufficient: a genuinely admitted grant, over a ledger
    this identity_key was never actually claimed in, is still refused -- a caller cannot
    merely assert a claim exists; this function independently re-reads the real ledger."""

    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR7-F1-NO-CLAIM",
        requirement_id=_SR7_F1_REQUIREMENT_ID,
        selection_id=_SR7_F1_WORK_UNIT_ID,
        verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
        permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
    )
    harmless_argv = [sys.executable, "-c", "print('HARMLESS_NO_AUTHORITY')"]
    ledger_path = tmp_path / "ledger.json"

    with pytest.raises(ReviewAdapterError):
        require_authenticated_review_launch_admission(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(tmp_path,),
            require_isolation=False,
            store=_bound_route["store"],
            project_id=_bound_route["project_id"],
            project_binding_id=_bound_route["project_binding_id"],
            requirement_id=_SR7_F1_REQUIREMENT_ID,
            selection_id=_SR7_F1_WORK_UNIT_ID,
            verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
            permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
            verifier_selection_grant_refs=[committed["grant_ref"]],
            human_grant_declaration_refs=[committed["declaration_ref"]],
            ledger_path=ledger_path,
            identity_key="never-claimed-identity-key",
            repository=_REPO,
        )


def test_sr7_f1_a_claim_already_terminally_resolved_is_refused(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """A claim this ledger already recorded a terminal outcome for is genuinely claimed, once
    -- but not *currently, still-claimable*; this function refuses it exactly as it would
    refuse an identity never claimed at all, never treating a stale real claim as a live one."""

    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR7-F1-RESOLVED-CLAIM",
        requirement_id=_SR7_F1_REQUIREMENT_ID,
        selection_id=_SR7_F1_WORK_UNIT_ID,
        verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
        permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
    )
    ledger_path = tmp_path / "ledger.json"
    identity_key = compute_identity_key(
        repository=_REPO,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id=_SR7_F1_REQUIREMENT_ID,
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id=_SR7_F1_WORK_UNIT_ID,
        repository=_REPO,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    bounded_review_script.record_dispatch_attempt(
        ledger_path, identity_key, repository=_REPO, acknowledged=True
    )
    bounded_review_script.record_review_outcome(
        ledger_path,
        identity_key,
        repository=_REPO,
        status=bounded_review_script.STATUS_COMPLETED,
        resolution_kind=bounded_review_script.RESOLUTION_KIND_COLLECTED_RESULT,
        result_bytes=b"genuinely collected",
    )

    harmless_argv = [sys.executable, "-c", "print('HARMLESS_NO_AUTHORITY')"]
    with pytest.raises(ReviewAdapterError):
        require_authenticated_review_launch_admission(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(tmp_path,),
            require_isolation=False,
            store=_bound_route["store"],
            project_id=_bound_route["project_id"],
            project_binding_id=_bound_route["project_binding_id"],
            requirement_id=_SR7_F1_REQUIREMENT_ID,
            selection_id=_SR7_F1_WORK_UNIT_ID,
            verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
            permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
            verifier_selection_grant_refs=[committed["grant_ref"]],
            human_grant_declaration_refs=[committed["declaration_ref"]],
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=_REPO,
        )


def test_sr8_f1_a_genuine_grant_and_claim_still_refuses_local_launch_remains_unavailable(
    tmp_path: Path, _bound_route: dict[str, Any]
) -> None:
    """SR8-F1 correction (PR #112 comment 6050757530), superseding this test's own prior
    premise: a genuinely Store-admitted grant plus a genuinely claimed, not-yet-resolved
    ledger record previously minted a real admission token here, proven by actually spawning
    and completing a real harmless subprocess with it, end to end -- exactly the "disclosed
    residual, generic test primitive, never the admission gate" framing the independent review
    rejected outright: "Merely calling the genuine helper from one composed route does not
    remove the alternate token-issuance/launch surface the handoff explicitly required
    testing... production effect must only consume genuine admitted operations or remain
    unavailable."

    Fixed: both genuine checks below still run -- :func:`require_authenticated_review_launch_
    admission` still calls the real :func:`authenticate_bounded_review_grant` and still
    independently re-reads the real, durable ledger claim, exactly as SR7-F1 left it -- but a
    real local launch remains unavailable even once both succeed. This is the one case this
    test now proves: not merely refused for insufficient authority (``test_sr7_f1_a_caller_
    with_no_real_grant_is_refused_zero_subprocess_effects``/``test_sr7_f1_a_genuine_grant_
    with_no_real_claim_is_refused`` already prove that), but refused *even with* fully genuine
    authority -- zero subprocess effects, for any caller, regardless of how real its own
    authentication/claim are. ``spawn_review_process`` itself, called directly with a
    forged/unconsumed token, is refused the identical unconditional way, never reachable
    through any surface this module exposes."""

    committed = _commit_additional_grant(
        _bound_route,
        transaction_id="TX-I109-SR8-F1-STILL-UNAVAILABLE",
        requirement_id=_SR7_F1_REQUIREMENT_ID,
        selection_id=_SR7_F1_WORK_UNIT_ID,
        verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
        permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
    )
    ledger_path = tmp_path / "ledger.json"
    identity_key = compute_identity_key(
        repository=_REPO,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id=_SR7_F1_REQUIREMENT_ID,
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id=_SR7_F1_WORK_UNIT_ID,
        repository=_REPO,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    harmless_argv = [sys.executable, "-c", "print('HARMLESS_WITH_REAL_AUTHORITY')"]
    with pytest.raises(ReviewAdapterError, match=LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON):
        require_authenticated_review_launch_admission(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(tmp_path,),
            require_isolation=False,
            store=_bound_route["store"],
            project_id=_bound_route["project_id"],
            project_binding_id=_bound_route["project_binding_id"],
            requirement_id=_SR7_F1_REQUIREMENT_ID,
            selection_id=_SR7_F1_WORK_UNIT_ID,
            verifier_identity=_SR7_F1_VERIFIER_IDENTITY,
            permitted_boundary=_SR7_F1_PERMITTED_BOUNDARY,
            verifier_selection_grant_refs=[committed["grant_ref"]],
            human_grant_declaration_refs=[committed["declaration_ref"]],
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=_REPO,
        )

    # The claim is untouched -- no admission token was ever minted, no slot consumed, no
    # process ever started.
    claim = read_claim(ledger_path, identity_key, repository=_REPO)
    assert claim is not None
    assert claim["status"] == STATUS_CLAIMED

    # SR8-F1: every other local-launch entrance refuses the identical way, unconditionally.
    with pytest.raises(ReviewAdapterError, match=LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON):
        validate_review_launch_preconditions(
            argv=harmless_argv,
            cwd=tmp_path,
            max_seconds=5,
            max_output_bytes=1024,
            mask_paths=(tmp_path,),
            require_isolation=False,
            authentication_decision={"decision": "REVIEW_SELECTION_ADMITTED"},
            claim_decision={"decision": "REVIEW_CLAIM_ADMITTED"},
        )
    with pytest.raises(ReviewAdapterError, match=LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON):
        spawn_review_process(
            harmless_argv,
            cwd=tmp_path,
            env={},
            admission_token="not-a-real-token",  # noqa: S106
            mask_paths=(tmp_path,),
            require_isolation=False,
        )
    with pytest.raises(ReviewAdapterError, match=LOCAL_PRODUCTION_LAUNCH_UNAVAILABLE_REASON):
        launch_review_process(
            harmless_argv,
            cwd=tmp_path,
            env={},
            max_seconds=5,
            max_output_bytes=1024,
            clock=_clock,
            mask_paths=(tmp_path,),
            require_isolation=False,
            authentication_decision={"decision": "REVIEW_SELECTION_ADMITTED"},
            claim_decision={"decision": "REVIEW_CLAIM_ADMITTED"},
        )


# --------------------------------------------------------------------------- #
# SR7-F2 correction (PR #112 comment 6037312445), adopted
# ADOPT_I109_PR112_SR7_F1_F3_20261008.
# --------------------------------------------------------------------------- #


def test_sr7_f2_an_invented_collected_result_for_a_naturally_exited_process_is_refused(
    tmp_path: Path,
) -> None:
    """The exact SR7-F2 reproduction (PR #112 comment 6037312445): a claim dispatched and
    genuinely bound to a real process -- never cancelled through the canonical cancellation
    route, no ``local_cancellation_confirmed_at`` marker ever set -- whose process then simply
    exits on its own (a crash, a lost acknowledgement, or ordinary completion outside this
    adapter's own knowledge). The matching recorded pid/token, now absent, previously let
    through an invented, never-collected ``COLLECTED_RESULT``. Fixed: this route refuses
    COLLECTED_RESULT unconditionally, before pid/liveness is ever inspected -- and the
    repository's one concurrency slot remains retained, refusing a second, different identity,
    exactly as an unresolved claim always has."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR7-F2-NATURAL-EXIT",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR7-F2-NATURAL-EXIT",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
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
        # The process exits entirely on its own -- never cancelled, never marked.
        owned_process.wait(timeout=10)
        assert process_identity_token(owned_process.pid) is None

        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status=bounded_review_script.STATUS_FAILED,
            resolution_kind=bounded_review_script.RESOLUTION_KIND_COLLECTED_RESULT,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=b"never actually collected from that process",
        )
        assert decision == {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "COLLECTED_RESULT_UNSUPPORTED_EXTERNALLY",
        }, decision

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
        assert claim["resolution_kind"] is None

        other_identity_key = compute_identity_key(
            repository=repository,
            pull_request="#109",
            base_sha="a" * 40,
            head_sha="a" * 40,
            requirement_id="REQ-SR7-F2-NATURAL-EXIT-OTHER",
            input_digest="a" * 64,
        )
        other_claim = claim_review_launch(
            ledger_path,
            identity_key=other_identity_key,
            work_unit_id="WORK-UNIT-SR7-F2-NATURAL-EXIT-OTHER",
            repository=repository,
            now=_NOW,
            numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
        )
        assert other_claim["decision"] == REVIEW_CLAIM_REFUSED, other_claim
        assert other_claim["reason_codes"] == ["CONCURRENT_REVIEW_ACTIVE"], other_claim
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)


def test_sr8_f2_confirmed_cancellation_without_a_genuine_local_cancellation_marker_is_refused(
    tmp_path: Path,
) -> None:
    """SR8-F2 correction (PR #112 comment 6050757530), superseding this test's own prior
    premise: this was the SR7-F2 positive control, asserting CONFIRMED_CANCELLATION --
    "an operator-asserted status label, never a caller-asserted payload" -- remained reachable
    for a claim whose genuinely bound pid/token this route itself independently confirmed was
    no longer running. The independent review named this exact premise as the SR8-F2 gap:
    genuinely-bound-and-not-running was never itself evidence of *cancellation specifically*,
    only of absence (here, a natural exit -- ``pass`` -- never a cancellation through
    :func:`compose_bounded_technical_review_cancellation` at all, no ``local_cancellation_
    confirmed_at`` marker ever set). "Refuse unsupported external resolution for all labels,
    or require genuinely correlated terminal evidence... fail-closed retention is sufficient."

    Fixed: this route now refuses ``CONFIRMED_CANCELLATION`` unconditionally whenever this
    ledger's own ``local_cancellation_confirmed_at`` marker was never set for this claim --
    before pid/token/liveness is ever inspected -- so the identical genuinely-bound-and-dead
    process this test still constructs no longer releases the slot."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR8-F2-CANCELLATION-STILL-REFUSED",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR8-F2-CANCELLATION-STILL-REFUSED",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
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
        # The process exits entirely on its own -- never cancelled, never marked.
        owned_process.wait(timeout=10)
        assert process_identity_token(owned_process.pid) is None

        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status=bounded_review_script.STATUS_FAILED,
            resolution_kind=bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=None,
        )
        assert decision == {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "CONFIRMED_CANCELLATION_UNSUPPORTED_EXTERNALLY",
        }, decision

        claim = read_claim(ledger_path, identity_key, repository=repository)
        assert claim is not None
        assert claim["status"] == bounded_review_script.STATUS_DISPATCHED
        assert claim["resolution_kind"] is None

        # The repository's one concurrency slot remains retained -- never released by a
        # caller-chosen label this route could not verify.
        other_identity_key = compute_identity_key(
            repository=repository,
            pull_request="#109",
            base_sha="a" * 40,
            head_sha="a" * 40,
            requirement_id="REQ-SR8-F2-CANCELLATION-STILL-REFUSED-OTHER",
            input_digest="a" * 64,
        )
        other_claim = claim_review_launch(
            ledger_path,
            identity_key=other_identity_key,
            work_unit_id="WORK-UNIT-SR8-F2-CANCELLATION-STILL-REFUSED-OTHER",
            repository=repository,
            now=_NOW,
            numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
        )
        assert other_claim["decision"] == REVIEW_CLAIM_REFUSED, other_claim
        assert other_claim["reason_codes"] == ["CONCURRENT_REVIEW_ACTIVE"], other_claim
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)


def test_sr7_f2_claim_retained_unknown_state_still_refuses_a_confirmed_cancellation_reattempt(
    tmp_path: Path,
) -> None:
    """``CLAIM_RETAINED_UNKNOWN_STATE`` (SR6-F3) remains genuinely enforced for the one
    resolution_kind still reachable through this route: a second CONFIRMED_CANCELLATION
    attempt against a claim this ledger already recorded a confirmed local-only cancellation
    for is refused permanently, exactly as a COLLECTED_RESULT attempt against it always was."""

    ledger_path = tmp_path / "ledger.json"
    repository = _REPO
    identity_key = compute_identity_key(
        repository=repository,
        pull_request="#109",
        base_sha="a" * 40,
        head_sha="a" * 40,
        requirement_id="REQ-SR7-F2-RETAINED-REATTEMPT",
        input_digest="a" * 64,
    )
    claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id="WORK-UNIT-SR7-F2-RETAINED-REATTEMPT",
        repository=repository,
        now=_NOW,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )

    owned_process = subprocess.Popen(
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

        confirmed = bounded_review_script.compose_bounded_technical_review_cancellation(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
        )
        assert confirmed["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY", confirmed
        owned_process.wait(timeout=5)

        decision = bounded_review_script.compose_bounded_technical_review_outcome_recording(
            ledger_path=ledger_path,
            identity_key=identity_key,
            repository=repository,
            status=bounded_review_script.STATUS_FAILED,
            resolution_kind=bounded_review_script.RESOLUTION_KIND_CONFIRMED_CANCELLATION,
            pid=owned_process.pid,
            owned_process_identity=owned_identity,
            result_bytes=None,
        )
        assert decision == {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "CLAIM_RETAINED_UNKNOWN_STATE",
        }, decision
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)
