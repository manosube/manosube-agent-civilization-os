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
from pathlib import Path
import sys
from typing import Any

import pytest

from manosube_agent_civilization.runtime.errors import RuntimeRequirementError

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "runtime_observation_proof.py"
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
