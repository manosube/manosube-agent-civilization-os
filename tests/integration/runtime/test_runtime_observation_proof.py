"""Issue #105 follow-on: the isolated Actions real-VPS proof trial orchestration script
(``scripts/runtime_observation_proof.py``), adopted ``ADOPT_I105_ISOLATED_ACTIONS_PROOF_
SETTINGS_20261006``.

This file proves the one new script's own actual shared-route orchestration -- never a live
network call, exactly as that script's own ``run-local-proof`` subcommand discloses
(``"transport": "LOCAL_SUBPROCESS_STAND_IN"``, ``"live_network_call_made": false``) -- against
a real, isolated local Store and the real, shipped ``scripts/runtime_observation_probe.py``,
run as a real local subprocess. Every positive path below reaches the identical canonical
:func:`~manosube_agent_civilization.runtime.observe_runtime_target`/
:func:`~manosube_agent_civilization.runtime.route_runtime_observation_to_evidence` routes every
other Runtime Observation test in this repository already reaches; every refusal path below is
the existing, unmodified refusal logic those routes and the shipped probe already keep, never a
second implementation this new script introduces.

The probe script's own bounded-read, pre-read-authorization, and symlink/ancestor-refusal
guarantees are exhaustively covered by ``tests/integration/runtime/
test_runtime_unattended_ssh.py`` and are not re-proven here; this file is scoped to what is
actually new -- the bootstrap script's own isolated-Authority minting and its composition with
those existing, unchanged routes.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "runtime_observation_proof.py"
)
_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3]
    / ".github"
    / "workflows"
    / "runtime_observation.yml"
)
_DOCS_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "runtime_observation_transports.md"
)
_PROBE_SCRIPT_SOURCE_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "runtime_observation_probe.py"
)

_HAS_SSH_TOOLCHAIN = (
    shutil.which("ssh") is not None
    and shutil.which("ssh-keygen") is not None
)


def _load_proof_module() -> Any:
    """Import ``scripts/runtime_observation_proof.py`` as a real module via ``importlib`` --
    the identical, already-licensed technique this file's own sibling
    (``test_runtime_unattended_ssh.py``'s ``_load_transport_module``) uses for
    ``runtime_observation_transport.py``, so this file exercises the real script's own actual
    functions directly, never a reimplementation of them."""

    spec = importlib.util.spec_from_file_location("runtime_observation_proof", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PROOF = _load_proof_module()


def _extract_workflow_step_run_block(step_name: str) -> str:
    """Return exactly the ``run:`` script text of the first step named *step_name* in
    ``.github/workflows/runtime_observation.yml`` -- found and dedented by plain text
    inspection, never by adding a YAML-parsing dependency this repository's own existing
    workflow-contract tests (``tests/contract/governance/
    test_merge_source_reflow_workflows.py``) deliberately avoid. Executing this exact text in
    a controlled subprocess (PR #111 Structural Review Round 1, F1's own tests below) proves
    the real, live workflow step -- never a hand-copied stand-in that could silently drift from
    it."""

    lines = _WORKFLOW_PATH.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == f"- name: {step_name}")
    run_index = next(
        i for i in range(start + 1, len(lines)) if lines[i].strip() == "run: |"
    )
    run_indent = len(lines[run_index]) - len(lines[run_index].lstrip(" "))
    body: list[str] = []
    for line in lines[run_index + 1 :]:
        indent = len(line) - len(line.lstrip(" "))
        if line.strip() and indent <= run_indent:
            break
        body.append(line[run_indent + 2 :] if line.strip() else "")
    return "\n".join(body) + "\n"


def _extract_markdown_fenced_block(anchor: str, language: str) -> str:
    """Return the body of the first ```*language* fenced block appearing after the literal
    text *anchor* in ``docs/runtime_observation_transports.md`` -- plain text inspection,
    identical discipline to :func:`_extract_workflow_step_run_block` above, so PR #111
    Structural Review Round 1, F2's own tests below exercise the exact documented wrapper
    script text, never a hand-copied stand-in that could silently drift from it."""

    import textwrap

    text = _DOCS_PATH.read_text(encoding="utf-8")
    anchor_index = text.index(anchor)
    fence_start = text.index(f"```{language}", anchor_index)
    body_start = text.index("\n", fence_start) + 1
    fence_end = text.index("```", body_start)
    return textwrap.dedent(text[body_start:fence_end])

_HOST = "127.0.0.1"
_PORT = 22
_USER = "probe"
_NOW = "2026-10-06T06:00:00Z"
_IDENTITY_VALUE = "sha256:" + "e" * 64


def _write_probe_fixtures(probe_config_dir: Path, *, identity_value: str) -> dict[str, str]:
    """Write a neutral identity/source/log fixture set plus the sibling
    ``runtime_observation_probe.config.json`` naming them, and return the three paths used --
    the identical sibling-config shape Issue #105's own isolated-deployment-identity
    correction (§24/§93) already established, reused here unchanged."""

    probe_config_dir.mkdir(parents=True, exist_ok=True)
    identity_path = probe_config_dir / "identity.txt"
    source_path = probe_config_dir / "source.txt"
    log_path = probe_config_dir / "log.txt"
    identity_path.write_text(identity_value, encoding="utf-8")
    source_path.write_text("line one\nline two\n", encoding="utf-8")
    log_path.write_text("log line\n", encoding="utf-8")
    config = {
        "deployment_identity_path": str(identity_path),
        "source_excerpt_path": str(source_path),
        "log_excerpt_path": str(log_path),
    }
    (probe_config_dir / "runtime_observation_probe.config.json").write_text(
        json.dumps(config), encoding="utf-8"
    )
    return config


def _config_fingerprint(config: dict[str, str]) -> str:
    import hashlib

    payload = json.dumps(
        {
            "deployment_identity_path": config["deployment_identity_path"],
            "source_excerpt_path": config["source_excerpt_path"],
            "log_excerpt_path": config["log_excerpt_path"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bootstrap(
    tmp_path: Path,
    *,
    suffix: str,
    grant_validity_seconds: float = 600.0,
    now: str = _NOW,
) -> dict:
    probe_config_dir = tmp_path / f"probe-config-{suffix}"
    config = _write_probe_fixtures(probe_config_dir, identity_value=_IDENTITY_VALUE)
    fingerprint = _config_fingerprint(config)
    store_root = tmp_path / f"store-{suffix}"
    result = _PROOF.bootstrap_isolated_world(
        store_root=store_root,
        now=now,
        grant_validity_seconds=grant_validity_seconds,
        host=_HOST,
        port=_PORT,
        user=_USER,
        probe_identity="OS_HEALTH_SNAPSHOT_BOUNDED",
        deployment_fingerprint=_IDENTITY_VALUE,
        deployment_config_fingerprint=fingerprint,
        probe_script_sha256=_PROOF.SSH_PROBE_SCRIPT_SHA256,
        permitted_fields=["hostname"],
        redaction_fields=[],
        permitted_transports=["GITHUB_ACTIONS", "PREAUTHORIZED_UNATTENDED_SSH", "MANUAL_SSH"],
        max_output_bytes=1_048_576,
        max_lines=200,
        max_timeout_seconds=30,
    )
    return {
        "store_root": store_root,
        "probe_config_dir": probe_config_dir,
        "project_id": result["project_id"],
        "project_binding_id": result["project_binding_id"],
        "grant": result["grant"],
        "target_identity": result["target_identity"],
    }


def test_bootstrap_signs_with_a_fresh_random_key_each_run_never_a_fixture_key(
    tmp_path: Path,
) -> None:
    """Obligation B's own decisive fact: two separate bootstrap calls, given the identical
    ``now`` (so every signed semantic field -- including ``grant_id``, which this script
    derives from ``now`` when not given explicitly -- is byte-identical across both) still
    produce two genuinely *different* grant signatures, because each run generates its own
    fresh ``Ed25519PrivateKey.generate()`` key in RAM rather than reusing a deterministic
    fixture key or any key from a prior run."""

    first = _bootstrap(tmp_path, suffix="a")
    second = _bootstrap(tmp_path, suffix="b")

    assert first["grant"]["grant_id"] == second["grant"]["grant_id"]
    assert first["grant"]["signature"]["value"] != second["grant"]["signature"]["value"]
    # Each run's own grant verifies only against its own freshly bootstrapped Store -- proven
    # below by the positive run-local-proof path reaching VERIFIED for each store separately.


def test_bootstrap_then_run_local_proof_reaches_observed_verified_and_derived_evidence(
    tmp_path: Path,
) -> None:
    """The positive completion proof: the real shipped probe script, run as a real local
    subprocess (never a live network call -- asserted explicitly below), over the exact world
    :func:`~runtime_observation_proof.bootstrap_isolated_world` just minted, reaches a genuine
    ``OBSERVED``/``VERIFIED`` outcome through the real, unchanged canonical route, and a
    genuine *derived* Evidence record through the real, unchanged
    :func:`~manosube_agent_civilization.runtime.route_runtime_observation_to_evidence`."""

    world = _bootstrap(tmp_path, suffix="positive")
    grant_file = tmp_path / "grant.json"
    target_identity_file = tmp_path / "target_identity.json"
    project_file = tmp_path / "project.json"
    grant_file.write_text(json.dumps(world["grant"]), encoding="utf-8")
    target_identity_file.write_text(json.dumps(world["target_identity"]), encoding="utf-8")
    project_file.write_text(
        json.dumps(
            {"project_id": world["project_id"], "project_binding_id": world["project_binding_id"]}
        ),
        encoding="utf-8",
    )

    with open(grant_file, encoding="utf-8") as stream:
        grant = json.load(stream)
    with open(target_identity_file, encoding="utf-8") as stream:
        target_identity = json.load(stream)

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr

    from tests.evidence_helpers import change_free_verification_evidence_request

    from manosube_agent_civilization.runtime import route_runtime_observation_to_evidence
    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.runtime.route import observe_runtime_target
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": list(grant["permitted_fields"]),
        "time_window": {"issued_at": grant["issued_at"], "expires_at": grant["expires_at"]},
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": 30,
        "redaction_fields": list(grant.get("redaction_fields", [])),
    }
    outcome = observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=target_identity,
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    assert outcome["receipt"].status == "VERIFIED"

    reopened_store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    raw_request = change_free_verification_evidence_request(provenance=None)
    rewritten = json.loads(json.dumps(raw_request).replace("PRJ-0001", world["project_id"]))
    evidence = route_runtime_observation_to_evidence(
        reopened_store, outcome["receipt"], world["project_id"], rewritten
    )
    assert evidence["evidence_position"] == "CHANGE_FREE_VERIFICATION_EVIDENCE"
    assert (
        evidence["verification_result_provenance"]["requirement_id"]
        == outcome["envelope"]["runtime_observation_envelope_id"]
    )


def test_cli_run_local_proof_discloses_no_live_network_call_and_derived_evidence(
    tmp_path: Path,
) -> None:
    """The real CLI entry point (``main``), invoked in-process (never a second subprocess
    layer this test would then have to trust blindly) -- confirms its own JSON output
    explicitly discloses ``transport: LOCAL_SUBPROCESS_STAND_IN`` /
    ``live_network_call_made: false``, and that the Evidence hand-off it reports is labelled
    ``DERIVED`` with ``store_committed_by_this_script: False`` -- obligation E's own "never
    conflate derived/file-saved Evidence with Store-committed Evidence" requirement, honestly
    kept by this script's own reported status rather than merely by this test's own
    assumption."""

    # This CLI call exercises _cmd_run_local_proof's own unmodified adapter construction,
    # which (correctly, matching SR3-F2's own live-reverification discipline) never accepts a
    # caller-suppliable now_fn override -- it always reads the real system clock. This world's
    # own grant window must therefore genuinely bracket that real clock, so it is bootstrapped
    # against the real current instant rather than this file's fixed _NOW fixture constant.
    from manosube_agent_civilization.runtime.engine import current_utc_instant

    live_now = current_utc_instant()
    world = _bootstrap(tmp_path, suffix="cli", now=live_now, grant_validity_seconds=600.0)
    out_dir = tmp_path / "cli-out"
    out_dir.mkdir()
    grant_file = out_dir / "grant.json"
    target_identity_file = out_dir / "target_identity.json"
    project_file = out_dir / "project.json"
    grant_file.write_text(json.dumps(world["grant"]), encoding="utf-8")
    target_identity_file.write_text(json.dumps(world["target_identity"]), encoding="utf-8")
    project_file.write_text(
        json.dumps(
            {"project_id": world["project_id"], "project_binding_id": world["project_binding_id"]}
        ),
        encoding="utf-8",
    )

    captured: dict[str, str] = {}

    class _CapturingStdout:
        def write(self, text: str) -> int:
            captured["text"] = captured.get("text", "") + text
            return len(text)

        def flush(self) -> None:
            return None

    real_stdout = sys.stdout
    sys.stdout = _CapturingStdout()  # type: ignore[assignment]
    try:
        exit_code = _PROOF.main(
            [
                "run-local-proof",
                "--grant-file",
                str(grant_file),
                "--target-identity-file",
                str(target_identity_file),
                "--project-file",
                str(project_file),
                "--store-root",
                str(world["store_root"]),
                "--now",
                live_now,
                "--probe-config-dir",
                str(world["probe_config_dir"]),
                "--with-evidence-handoff",
            ]
        )
    finally:
        sys.stdout = real_stdout

    assert exit_code == 0
    report = json.loads(captured["text"])
    assert report["ok"] is True
    assert report["transport"] == "LOCAL_SUBPROCESS_STAND_IN"
    assert report["live_network_call_made"] is False
    assert report["observation_outcome"] == "OBSERVED"
    assert report["receipt_status"] == "VERIFIED"
    assert report["evidence_handoff"]["status"] == "DERIVED"
    assert report["evidence_handoff"]["store_committed_by_this_script"] is False


def test_run_local_proof_refuses_when_the_targets_configuration_no_longer_matches_the_grant(
    tmp_path: Path,
) -> None:
    """The decisive replay-refusal proof: the real target's own sibling configuration has
    genuinely changed (different source/log paths) since the grant was signed, so the probe's
    own freshly computed ``deployment_config_fingerprint`` no longer matches what the grant's
    signed commitment names -- refused before the canonical route can ever reach ``OBSERVED``,
    exactly the discipline Issue #105's own isolated-deployment-identity correction requires."""

    world = _bootstrap(tmp_path, suffix="stale-config")
    grant = world["grant"]

    # Mutate the real target's own sibling config to name different excerpt paths -- never the
    # grant itself, which stays genuinely, validly signed for the *original* configuration.
    changed_source = world["probe_config_dir"] / "changed-source.txt"
    changed_source.write_text("a different file entirely\n", encoding="utf-8")
    config_path = world["probe_config_dir"] / "runtime_observation_probe.config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["source_excerpt_path"] = str(changed_source)
    config_path.write_text(json.dumps(config), encoding="utf-8")

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr
    probe_report = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
    assert probe_report["ok"] is False
    assert probe_report["reason"] == "CONFIG_NOT_AUTHORIZED"

    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.runtime.route import observe_runtime_target
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": list(grant["permitted_fields"]),
        "time_window": {"issued_at": grant["issued_at"], "expires_at": grant["expires_at"]},
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": 30,
        "redaction_fields": [],
    }
    outcome = observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] != "OBSERVED"
    assert outcome["receipt"].status != "VERIFIED"


def test_run_local_proof_refuses_a_wrong_reported_identity_against_the_declared_target(
    tmp_path: Path,
) -> None:
    """Obligation D, proved through the real canonical route directly: the real target's own
    configured identity file now reports a *different* value than the one this world's own
    committed ``runtime_deployment_declaration`` declared -- an honest ``IDENTITY_MISMATCH``,
    never promoted to ``VERIFIED`` merely because the probe itself ran successfully and the
    configuration commitment still matches (only the identity *content* changed, not the path
    the fingerprint covers)."""

    world = _bootstrap(tmp_path, suffix="wrong-identity")
    grant = world["grant"]

    identity_path = world["probe_config_dir"] / "identity.txt"
    identity_path.write_text("sha256:" + "f" * 64, encoding="utf-8")

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr
    probe_report = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
    assert probe_report["ok"] is True
    assert probe_report["deployment_identity"] == "sha256:" + "f" * 64

    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.runtime.route import observe_runtime_target
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": list(grant["permitted_fields"]),
        "time_window": {"issued_at": grant["issued_at"], "expires_at": grant["expires_at"]},
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": 30,
        "redaction_fields": [],
    }
    outcome = observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "IDENTITY_MISMATCH"
    assert outcome["receipt"].status == "FAILED"


def test_run_local_proof_refuses_an_expired_grant(tmp_path: Path) -> None:
    """A bounded short-lived grant (obligation B) genuinely expires -- an attempt made after
    its own ``expires_at`` must be refused at the adapter's own construction-time/live
    re-verification gate, never silently accepted because the signature itself still verifies
    (a stale signature is not the same thing as a currently valid grant)."""

    world = _bootstrap(tmp_path, suffix="expired", grant_validity_seconds=1.0)
    grant = world["grant"]

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr

    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    # Far past the grant's own 1-second validity window set above.
    long_after_expiry = "2026-10-06T07:00:00Z"
    with pytest.raises(RuntimeRequirementError):
        CapturedProbeReportRuntimeAdapter(
            captured_stdout=stdout,
            captured_stderr=stderr,
            captured_returncode=returncode,
            grant=grant,
            store=store,
            project_id=world["project_id"],
            project_binding_id=world["project_binding_id"],
            now=long_after_expiry,
        )


def test_run_local_proof_refuses_when_the_sibling_configuration_is_missing_entirely(
    tmp_path: Path,
) -> None:
    """Setup-missing fails closed: the operator never actually placed the trial's own sibling
    ``runtime_observation_probe.config.json`` on the real target (a genuine setup omission),
    so the probe falls back to its own shipped defaults -- which this world's own grant was
    never signed against -- and refuses before any read, exactly as an unauthorized
    configuration change would."""

    world = _bootstrap(tmp_path, suffix="missing-setup")
    grant = world["grant"]

    (world["probe_config_dir"] / "runtime_observation_probe.config.json").unlink()

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr
    probe_report = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
    assert probe_report["ok"] is False
    assert probe_report["reason"] == "CONFIG_NOT_AUTHORIZED"


def test_run_local_proof_subprocess_call_is_bounded_by_an_explicit_timeout() -> None:
    """A structural, static proof that the real local subprocess invocation
    :func:`~runtime_observation_proof._run_real_probe_locally` makes is never unbounded --
    this script's own one new subprocess call site must carry an explicit ``timeout=`` just as
    every other bounded subprocess call in this repository's own scripts already does."""

    import inspect

    source = inspect.getsource(_PROOF._run_real_probe_locally)
    assert "timeout=" in source


# --------------------------------------------------------------------------------------- #
# PR #111 Structural Review Round 1 correction (ADOPT_I105_PR111_SR1_F1_F4_20261006).
# --------------------------------------------------------------------------------------- #


@pytest.mark.skipif(
    not _HAS_SSH_TOOLCHAIN, reason="no real ssh/ssh-keygen toolchain available in this environment"
)
def test_f1_workflow_generated_ssh_config_genuinely_selects_the_trial_identity_for_the_host(
    tmp_path: Path,
) -> None:
    """F1: run the real, live text of the workflow's own "Set up the trial-only SSH key,
    pinned host verification, and identity selection" step (extracted verbatim, never a
    hand-copied stand-in) against a real, freshly generated Ed25519 key pair and a real local
    HOME, then independently re-derive identity selection with a real ``ssh -G`` resolution --
    never a mere assertion that the key/config files exist."""

    script = _extract_workflow_step_run_block(
        "Set up the trial-only SSH key, pinned host verification, and identity selection"
    )

    fake_home = tmp_path / "home"
    fake_home.mkdir()
    key_path = tmp_path / "generated_trial_key"
    subprocess.run(  # noqa: S603 -- fixed executable/argv, local test-only key generation
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(key_path), "-C", "trial"],  # noqa: S607
        check=True,
        capture_output=True,
        timeout=30,
    )
    private_key_text = key_path.read_text(encoding="utf-8")

    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["TRIAL_SSH_PRIVATE_KEY"] = private_key_text
    env["TRIAL_SSH_KNOWN_HOSTS"] = "runtime-observation-isolated-trial.test ssh-ed25519 AAAA"
    env["TRIAL_SSH_HOST"] = "runtime-observation-isolated-trial.test"
    env["TRIAL_SSH_PORT"] = "2222"
    env["TRIAL_SSH_USER"] = "trialuser"

    result = subprocess.run(  # noqa: S603 -- fixed executable, extracted workflow step text
        ["bash", "-c", script], env=env, capture_output=True, timeout=30, text=True  # noqa: S607
    )
    assert result.returncode == 0, result.stderr

    # Independent re-check, directly, never trusting the script's own internal assertion
    # alone: a fresh ssh -G resolution against the generated config.
    selected = subprocess.run(  # noqa: S603 -- fixed executable/argv, local test-only resolution
        ["ssh", "-G", "-F", str(fake_home / ".ssh" / "config"), env["TRIAL_SSH_HOST"]],  # noqa: S607
        env=env,
        capture_output=True,
        timeout=30,
        text=True,
    )
    assert selected.returncode == 0, selected.stderr
    identity_lines = [
        line for line in selected.stdout.splitlines() if line.startswith("identityfile ")
    ]
    assert identity_lines, selected.stdout
    # `ssh -G` prints an IdentityFile value verbatim, never tilde-expanded -- resolve it the
    # same way a real ssh client would before comparing, and confirm the resolved path is a
    # real file (never merely a string match against an unexpanded literal).
    raw_identity = identity_lines[-1].split(" ", 1)[1]
    resolved_identity = (
        str(fake_home) + raw_identity[1:] if raw_identity.startswith("~") else raw_identity
    )
    assert resolved_identity == str(fake_home / ".ssh" / "isolated_trial_proof_key")
    assert Path(resolved_identity).is_file()


@pytest.mark.skipif(
    not _HAS_SSH_TOOLCHAIN, reason="no real ssh/ssh-keygen toolchain available in this environment"
)
def test_f1_workflow_setup_step_refuses_closed_on_a_missing_or_invalid_trial_key(
    tmp_path: Path,
) -> None:
    """F1 obligation: "a file-exists assertion is insufficient" -- the written key material
    must actually parse as a valid private key, or this step must fail closed, before it ever
    writes the ~/.ssh/config that would otherwise make *some* identity selectable."""

    script = _extract_workflow_step_run_block(
        "Set up the trial-only SSH key, pinned host verification, and identity selection"
    )
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["TRIAL_SSH_PRIVATE_KEY"] = "not a real private key"
    env["TRIAL_SSH_KNOWN_HOSTS"] = "runtime-observation-isolated-trial.test ssh-ed25519 AAAA"
    env["TRIAL_SSH_HOST"] = "runtime-observation-isolated-trial.test"
    env["TRIAL_SSH_PORT"] = "2222"
    env["TRIAL_SSH_USER"] = "trialuser"

    result = subprocess.run(  # noqa: S603 -- fixed executable, extracted workflow step text
        ["bash", "-c", script], env=env, capture_output=True, timeout=30, text=True  # noqa: S607
    )
    assert result.returncode != 0
    assert "the trial-only SSH key is missing or is not a valid private key" in result.stdout
    # Fail-closed, before the config that would select *some* identity was ever written.
    assert not (fake_home / ".ssh" / "config").exists()


@pytest.mark.skipif(
    not _HAS_SSH_TOOLCHAIN, reason="no real ssh/ssh-keygen toolchain available in this environment"
)
def test_f1_generated_config_never_falls_back_to_an_unrelated_ambient_identity(
    tmp_path: Path,
) -> None:
    """F1 obligation: "unintended ambient identities cannot satisfy the trial" -- with a
    *different*, ambient default identity already present at ``~/.ssh/id_ed25519`` before the
    workflow step ever runs, the generated config for the trial host must still resolve to
    *only* the trial-only key, never falling back to (or even considering) the ambient one."""

    script = _extract_workflow_step_run_block(
        "Set up the trial-only SSH key, pinned host verification, and identity selection"
    )

    fake_home = tmp_path / "home"
    (fake_home / ".ssh").mkdir(parents=True)
    ambient_key_path = fake_home / ".ssh" / "id_ed25519"
    subprocess.run(  # noqa: S603 -- fixed executable/argv, local test-only key generation
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(ambient_key_path), "-C", "ambient"],  # noqa: S607
        check=True,
        capture_output=True,
        timeout=30,
    )
    trial_key_path = tmp_path / "generated_trial_key"
    subprocess.run(  # noqa: S603 -- fixed executable/argv, local test-only key generation
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-f", str(trial_key_path), "-C", "trial"],  # noqa: S607
        check=True,
        capture_output=True,
        timeout=30,
    )

    env = dict(os.environ)
    env["HOME"] = str(fake_home)
    env["TRIAL_SSH_PRIVATE_KEY"] = trial_key_path.read_text(encoding="utf-8")
    env["TRIAL_SSH_KNOWN_HOSTS"] = "runtime-observation-isolated-trial.test ssh-ed25519 AAAA"
    env["TRIAL_SSH_HOST"] = "runtime-observation-isolated-trial.test"
    env["TRIAL_SSH_PORT"] = "2222"
    env["TRIAL_SSH_USER"] = "trialuser"

    result = subprocess.run(  # noqa: S603 -- fixed executable, extracted workflow step text
        ["bash", "-c", script], env=env, capture_output=True, timeout=30, text=True  # noqa: S607
    )
    assert result.returncode == 0, result.stderr

    selected = subprocess.run(  # noqa: S603 -- fixed executable/argv, local test-only resolution
        ["ssh", "-G", "-F", str(fake_home / ".ssh" / "config"), env["TRIAL_SSH_HOST"]],  # noqa: S607
        env=env,
        capture_output=True,
        timeout=30,
        text=True,
    )
    identity_lines = [
        line for line in selected.stdout.splitlines() if line.startswith("identityfile ")
    ]
    # ssh -G prints IdentityFile verbatim, never tilde-expanded -- exactly one identity, the
    # trial-only one, and never the ambient default this test deliberately planted.
    assert identity_lines == ["identityfile ~/.ssh/isolated_trial_proof_key"]
    assert str(ambient_key_path) not in selected.stdout


def test_f2_render_expected_ssh_command_matches_the_real_render_ssh_command_argv() -> None:
    """F2: the forced-command wrapper's own expected-value generator must print *exactly* what
    the real, unmodified ``render_ssh_command_argv`` -- the identical function
    :class:`~manosube_agent_civilization.runtime.adapter.SshRuntimeAdapter` itself calls --
    builds for the given endpoint, never a second, independently-maintained copy of that text
    that could silently drift from it."""

    from manosube_agent_civilization.runtime.network import render_ssh_command_argv

    fingerprint = "b" * 64
    expected_argv = render_ssh_command_argv(
        host="trial.example.test",
        port=2222,
        user="trialuser",
        probe_identity="OS_HEALTH_SNAPSHOT_BOUNDED",
        expected_probe_script_sha256=_PROOF.SSH_PROBE_SCRIPT_SHA256,
        expected_deployment_config_fingerprint=fingerprint,
    )

    captured: dict[str, str] = {}

    class _CapturingStdout:
        def write(self, text: str) -> int:
            captured["text"] = captured.get("text", "") + text
            return len(text)

        def flush(self) -> None:
            return None

    real_stdout = sys.stdout
    sys.stdout = _CapturingStdout()  # type: ignore[assignment]
    try:
        exit_code = _PROOF.main(
            [
                "render-expected-ssh-command",
                "--host",
                "trial.example.test",
                "--port",
                "2222",
                "--user",
                "trialuser",
                "--probe-identity",
                "OS_HEALTH_SNAPSHOT_BOUNDED",
                "--deployment-config-fingerprint",
                fingerprint,
            ]
        )
    finally:
        sys.stdout = real_stdout

    assert exit_code == 0
    assert captured["text"] == expected_argv[-1] + "\n"


def test_f2_documented_forced_command_wrapper_executes_the_real_launcher_for_the_authorized_command(
    tmp_path: Path,
) -> None:
    """F2's positive path, run for real and end to end: the exact, documented wrapper script
    (extracted verbatim from docs/runtime_observation_transports.md §7.1 step 4, never a
    hand-copied stand-in), given the one real, exact ``$SSH_ORIGINAL_COMMAND`` the real
    launcher-wrapped invocation renders, genuinely re-executes it -- reaching the real,
    unmodified ``scripts/runtime_observation_probe.py`` (never the wrapper's own stub output)
    and a genuine positive probe report, proving the launcher's own verify-before-execute
    discipline is exercised intact underneath this wrapper."""

    from manosube_agent_civilization.runtime.network import render_ssh_command_argv

    neutral_dir = tmp_path / "neutral"
    neutral_dir.mkdir()
    probe_copy = neutral_dir / "runtime_observation_probe.py"
    probe_copy.write_bytes(_PROBE_SCRIPT_SOURCE_PATH.read_bytes())
    config = _write_probe_fixtures(neutral_dir, identity_value=_IDENTITY_VALUE)
    fingerprint = _config_fingerprint(config)

    expected_argv = render_ssh_command_argv(
        host="trial.example.test",
        port=2222,
        user="trialuser",
        probe_identity="OS_HEALTH_SNAPSHOT_BOUNDED",
        expected_probe_script_sha256=_PROOF.SSH_PROBE_SCRIPT_SHA256,
        expected_deployment_config_fingerprint=fingerprint,
    )
    expected_command = expected_argv[-1]
    (neutral_dir / "expected_command.txt").write_text(expected_command, encoding="utf-8")

    wrapper_script = _extract_markdown_fenced_block("verify_and_exec.sh`", "sh").replace(
        "/opt/runtime-observation-isolated-trial", str(neutral_dir)
    )
    wrapper_path = tmp_path / "verify_and_exec.sh"
    wrapper_path.write_text(wrapper_script, encoding="utf-8")
    wrapper_path.chmod(0o700)

    env = dict(os.environ)
    env["SSH_ORIGINAL_COMMAND"] = expected_command

    result = subprocess.run(  # noqa: S603 -- fixed executable, test-controlled extracted wrapper
        ["bash", str(wrapper_path)], env=env, capture_output=True, timeout=30, text=True  # noqa: S607
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    # Genuinely reached the real probe script's own report -- never the wrapper's own refusal
    # stub, and never the launcher's own ARTIFACT_NOT_AUTHORIZED stub.
    assert report.get("reason") not in {"COMMAND_NOT_AUTHORIZED", "ARTIFACT_NOT_AUTHORIZED"}
    assert report["ok"] is True
    assert report["deployment_identity"] == _IDENTITY_VALUE


def test_f2_documented_forced_command_wrapper_refuses_any_other_command_before_any_execution(
    tmp_path: Path,
) -> None:
    """F2's negative path: a connecting client requesting *any* command other than the one
    exact, expected launcher invocation is refused by the wrapper itself, with the launcher
    (and the real probe script) never reached at all -- never "runs and is reported as
    untrusted afterward"."""

    neutral_dir = tmp_path / "neutral"
    neutral_dir.mkdir()
    # Deliberately no probe script copy placed here -- if the wrapper ever tried to exec
    # anything, a missing script would itself prove the refusal did not happen before exec.
    (neutral_dir / "expected_command.txt").write_text("python3 -c \"x\" a b c", encoding="utf-8")

    wrapper_script = _extract_markdown_fenced_block("verify_and_exec.sh`", "sh").replace(
        "/opt/runtime-observation-isolated-trial", str(neutral_dir)
    )
    wrapper_path = tmp_path / "verify_and_exec.sh"
    wrapper_path.write_text(wrapper_script, encoding="utf-8")
    wrapper_path.chmod(0o700)

    for tampered_command in [
        "python3 -c \"y\" a b c",  # different code string
        "rm -rf /",  # an entirely unrelated command
        "",  # client sent no command at all
    ]:
        env = dict(os.environ)
        if tampered_command:
            env["SSH_ORIGINAL_COMMAND"] = tampered_command
        else:
            env.pop("SSH_ORIGINAL_COMMAND", None)
        result = subprocess.run(  # noqa: S603 -- fixed executable, test-controlled extracted wrapper
            ["bash", str(wrapper_path)], env=env, capture_output=True, timeout=30, text=True  # noqa: S607
        )
        assert result.returncode != 0, tampered_command
        assert json.loads(result.stdout.strip()) == {
            "ok": False,
            "reason": "COMMAND_NOT_AUTHORIZED",
        }


def test_f3_evidence_from_receipt_derives_evidence_from_the_real_envelope_with_zero_new_probe_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F3's decisive proof: given a Store a real observation already, genuinely committed an
    envelope to (built here the identical way the positive completion test above does), the
    ``evidence-from-receipt`` subcommand derives Evidence from that exact, already-durable
    record -- while this test actively monkeypatches
    :func:`runtime_observation_proof._run_real_probe_locally` to raise if it is ever called
    again, so a probe re-invocation inside this subcommand's own call graph would fail this
    test immediately, rather than merely going unnoticed."""

    world = _bootstrap(tmp_path, suffix="f3-positive")
    grant = world["grant"]

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr

    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.runtime.route import observe_runtime_target
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": list(grant["permitted_fields"]),
        "time_window": {"issued_at": grant["issued_at"], "expires_at": grant["expires_at"]},
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": 30,
        "redaction_fields": [],
    }
    outcome = observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    assert outcome["envelope"]["observation_outcome"] == "OBSERVED"
    envelope_id = outcome["envelope"]["runtime_observation_envelope_id"]

    def _fail_if_called(**_kwargs: Any) -> None:
        raise AssertionError(
            "evidence-from-receipt must never re-invoke the probe -- zero new observation calls"
        )

    monkeypatch.setattr(_PROOF, "_run_real_probe_locally", _fail_if_called)

    project_file = tmp_path / "f3-project.json"
    project_file.write_text(
        json.dumps(
            {"project_id": world["project_id"], "project_binding_id": world["project_binding_id"]}
        ),
        encoding="utf-8",
    )

    captured: dict[str, str] = {}

    class _CapturingStdout:
        def write(self, text: str) -> int:
            captured["text"] = captured.get("text", "") + text
            return len(text)

        def flush(self) -> None:
            return None

    real_stdout = sys.stdout
    sys.stdout = _CapturingStdout()  # type: ignore[assignment]
    try:
        exit_code = _PROOF.main(
            [
                "evidence-from-receipt",
                "--store-root",
                str(world["store_root"]),
                "--project-file",
                str(project_file),
                "--envelope-id",
                envelope_id,
            ]
        )
    finally:
        sys.stdout = real_stdout

    assert exit_code == 0
    report = json.loads(captured["text"])
    assert report["ok"] is True
    assert report["live_probe_or_observation_invoked"] is False
    assert report["evidence_handoff"]["status"] == "DERIVED"
    assert report["evidence_handoff"]["store_committed_by_this_script"] is False
    assert report["evidence_handoff"]["evidence_id"]


def test_f3_evidence_from_receipt_refuses_for_an_envelope_id_that_never_resolved(
    tmp_path: Path,
) -> None:
    """F3 refusal path: an ``--envelope-id`` naming a record that was never actually committed
    to this exact Store is refused, never silently treated as an empty/absent Evidence."""

    world = _bootstrap(tmp_path, suffix="f3-missing-envelope")
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    with pytest.raises(RuntimeRequirementError):
        _PROOF.resolve_live_receipt_from_store(
            store, project_id=world["project_id"], envelope_id="does-not-exist"
        )


def test_f3_evidence_from_receipt_refuses_for_a_tampered_committed_envelope(
    tmp_path: Path,
) -> None:
    """F3 refusal path: an Envelope record whose own declared semantic fingerprint no longer
    equals its own recomputed one (a genuine tamper, or a hash collision) must refuse before
    this script ever reconstitutes a receipt from it -- never trusting a resolved record's own
    fields unconditionally."""

    world = _bootstrap(tmp_path, suffix="f3-tampered-envelope")
    grant = world["grant"]

    stdout, stderr, returncode = _PROOF._run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=world["probe_config_dir"],
    )
    assert returncode == 0, stderr

    from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
    from manosube_agent_civilization.runtime.route import observe_runtime_target
    from manosube_agent_civilization.store import FileStateStore

    store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        now=_NOW,
        now_fn=lambda: _NOW,
    )
    boundary = {
        "observation_method": "SSH_EXEC_BOUNDED",
        "endpoint": {
            "host": grant["host"],
            "port": grant["port"],
            "user": grant["user"],
            "probe_identity": grant["probe_identity"],
        },
        "permitted_fields": list(grant["permitted_fields"]),
        "time_window": {"issued_at": grant["issued_at"], "expires_at": grant["expires_at"]},
        "network_scope": {"allowed_hosts": [grant["host"]]},
        "timeout_seconds": 30,
        "redaction_fields": [],
    }
    outcome = observe_runtime_target(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        target_identity=world["target_identity"],
        boundary=boundary,
        adapter=adapter,
        observed_at=_NOW,
    )
    envelope_id = outcome["envelope"]["runtime_observation_envelope_id"]

    # Tamper the one canonical record file directly on disk -- never through any
    # Store-sanctioned committer -- the identical "simulate a genuine content tamper"
    # technique this repository's own other Envelope-integrity tests already use.
    raw_record = store.resolve_record(
        world["project_id"], "runtime_observation_envelope", envelope_id
    )
    assert raw_record is not None
    tampered = dict(raw_record)
    tampered["observed_fields"] = {"hostname": "tampered-value"}
    tampered_bytes = json.dumps(tampered).encode("utf-8")

    project_root = Path(world["store_root"]) / "projects" / world["project_id"]
    record_path = (
        project_root / "records" / "runtime_observation_envelope" / f"{envelope_id}.json"
    )
    assert record_path.is_file(), record_path
    record_path.write_bytes(tampered_bytes)

    # The Store's own cross-claimant divergence check (CorruptStoreError) compares this
    # permanent record against every recovery journal's own staged copy of it -- tampering
    # only the permanent file trips that check first, before this script's own semantic-
    # fingerprint recomputation ever runs. Tamper every staged copy identically too, so this
    # test isolates the one check it actually means to exercise: this script's own refusal
    # to reconstitute a receipt from an internally self-inconsistent (but Store-consistent)
    # record.
    staged_name = f"runtime_observation_envelope__{envelope_id}.json"
    for staged_path in (project_root / "state" / "recovery").rglob(staged_name):
        staged_path.write_bytes(tampered_bytes)

    reopened_store = FileStateStore(world["store_root"], schema_root=_PROOF.SCHEMA_ROOT)
    with pytest.raises(RuntimeRequirementError):
        _PROOF.resolve_live_receipt_from_store(
            reopened_store, project_id=world["project_id"], envelope_id=envelope_id
        )


def test_f3_exported_bundle_never_carries_private_key_material(tmp_path: Path) -> None:
    """F3 obligation: the bounded export bundle a receiver reopens must never carry a signing
    or SSH private key -- structurally proven here by scanning every file this trial's own
    bootstrap writes for the one unambiguous textual marker any PEM/OpenSSH private key must
    carry."""

    world = _bootstrap(tmp_path, suffix="f3-no-private-key")
    out_dir = tmp_path / "f3-no-private-key-out"
    out_dir.mkdir()
    (out_dir / "grant.json").write_text(json.dumps(world["grant"]), encoding="utf-8")
    (out_dir / "target_identity.json").write_text(
        json.dumps(world["target_identity"]), encoding="utf-8"
    )
    (out_dir / "project.json").write_text(
        json.dumps(
            {"project_id": world["project_id"], "project_binding_id": world["project_binding_id"]}
        ),
        encoding="utf-8",
    )

    for directory in (Path(world["store_root"]), out_dir):
        for path in directory.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert "PRIVATE KEY" not in text, path


def test_f4_check_proof_verdict_is_positive_only_when_both_trials_genuinely_observed() -> None:
    actions_trial = {
        "ok": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host"},
    }
    fallback_trial = {
        "ok": True,
        "decision": "FALLBACK_AUTHORIZED",
        "executed": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host"},
    }
    verdict = _PROOF.check_proof_verdict(actions_trial, fallback_trial)
    assert verdict == {"ok": True, "reasons": []}


def test_f4_check_proof_verdict_rejects_ok_true_alone_as_insufficient() -> None:
    """F4's core distinction: an honest, refused/UNAVAILABLE observation can report
    ``"ok": true`` exactly as genuinely as a real positive one -- this must never pass."""

    actions_trial = {
        "ok": True,
        "observation_outcome": "UNAVAILABLE",
        "receipt_status": "UNAVAILABLE",
        "observed_fields": None,
    }
    fallback_trial = {
        "ok": True,
        "decision": "FALLBACK_AUTHORIZED",
        "executed": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host"},
    }
    verdict = _PROOF.check_proof_verdict(actions_trial, fallback_trial)
    assert verdict["ok"] is False
    assert any("actions_trial" in reason for reason in verdict["reasons"])


def test_f4_check_proof_verdict_rejects_a_fallback_that_never_reached_authorized_execution() -> (
    None
):
    actions_trial = {
        "ok": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host"},
    }
    fallback_trial = {
        "ok": True,
        "decision": "ACTIONS_AVAILABLE_DEFER",
        "executed": False,
    }
    verdict = _PROOF.check_proof_verdict(actions_trial, fallback_trial)
    assert verdict["ok"] is False
    assert any("FALLBACK_AUTHORIZED" in reason for reason in verdict["reasons"])


def test_f4_check_proof_verdict_rejects_mismatched_stable_fields_between_both_trials() -> None:
    actions_trial = {
        "ok": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host-a"},
    }
    fallback_trial = {
        "ok": True,
        "decision": "FALLBACK_AUTHORIZED",
        "executed": True,
        "observation_outcome": "OBSERVED",
        "receipt_status": "VERIFIED",
        "observed_fields": {"hostname": "trial-host-b"},
    }
    verdict = _PROOF.check_proof_verdict(actions_trial, fallback_trial)
    assert verdict["ok"] is False
    assert any("disagree" in reason for reason in verdict["reasons"])


def test_f4_check_proof_verdict_cli_exits_nonzero_on_a_negative_verdict(tmp_path: Path) -> None:
    actions_result = tmp_path / "actions_trial_result.json"
    fallback_result = tmp_path / "fallback_trial_result.json"
    actions_result.write_text(
        json.dumps({"ok": True, "observation_outcome": "TIMEOUT", "receipt_status": "UNAVAILABLE"}),
        encoding="utf-8",
    )
    fallback_result.write_text(
        json.dumps({"ok": True, "decision": "FALLBACK_REFUSED_NO_GRANT", "executed": False}),
        encoding="utf-8",
    )

    exit_code = _PROOF.main(
        [
            "check-proof-verdict",
            "--actions-trial-result",
            str(actions_result),
            "--fallback-trial-result",
            str(fallback_result),
        ]
    )
    assert exit_code == 1


def test_f4_render_command_and_observe_jobs_never_run_on_a_proof_mode_dispatch() -> None:
    """F4: the two generic jobs must carry an `if:` that excludes a `proof_mode: "true"`
    dispatch, and the isolated-actions-proof job must carry the exact inverse -- a plain text
    check, the identical discipline this repository's own workflow-contract tests already use,
    never a YAML-parsing dependency added for this file alone."""

    text = _WORKFLOW_PATH.read_text(encoding="utf-8")
    render_command_index = text.index("\n  render-command:")
    observe_index = text.index("\n  observe:")
    proof_index = text.index("\n  isolated-actions-proof:")
    assert render_command_index < observe_index < proof_index

    render_command_body = text[render_command_index:observe_index]
    observe_body = text[observe_index:proof_index]
    proof_body = text[proof_index:]

    assert "if: github.event.inputs.proof_mode != 'true'" in render_command_body
    assert "if: github.event.inputs.proof_mode != 'true'" in observe_body
    assert "if: github.event.inputs.proof_mode == 'true'" in proof_body
    assert "if: github.event.inputs.proof_mode != 'true'" not in proof_body
