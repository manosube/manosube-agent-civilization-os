"""Isolated Actions real-VPS proof trial orchestration (Issue #105 follow-on, adopted
``ADOPT_I105_ISOLATED_ACTIONS_PROOF_SETTINGS_20261006``).

**What this script is.** A standalone trial-orchestration tool, never part of the installed
`manosube_agent_civilization` package and never a second Runtime/Authority/Evidence owner. Its
one job is narrow: bootstrap a disposable, isolated Project Binding and Store under a
genuinely random, in-RAM Ed25519 "isolated test Authority" key -- never a publicly known,
deterministic fixture signing key standing in for deployed Authority -- commit a real
``runtime_deployment_declaration`` under it, and sign one bounded, short-lived
``runtime_observation_grant``. Everything downstream of that point -- the actual observation
(real SSH or a real Actions execution), the independent Actions-to-SSH fallback controller
exercise, and the receipt-to-Evidence hand-off -- already exists, unmodified, in
``scripts/runtime_observation_transport.py`` (``observe``/``run-controller`` subcommands) and
in :mod:`manosube_agent_civilization.runtime`. This script produces exactly the inputs those
existing, shipped routes already know how to consume (a grant file, a target-identity file,
and a Store root) -- it introduces no parallel implementation of either.

**Why a random key, never a fixture key, here.** Every other Runtime Observation test in this
repository signs against ``tests.fixtures.product_binding``'s own fixed, deterministic,
publicly-known Ed25519 seed -- exactly right for a test that must be reproducible, and exactly
wrong for anything that will touch a real network target: a publicly known private key can
never stand in for genuine deployed Authority. This script instead calls
``Ed25519PrivateKey.generate()`` fresh, in process memory, every single run; that key is never
written to disk, never logged, and never appears in this script's own output -- only its
*public* half (embedded in the Project Binding it signs) and the hex-encoded *signatures* it
produces over the declaration/grant are ever persisted.

**Deliberate, disclosed test-fixture reuse.** This script imports
``tests.fixtures.product_binding`` (for the Project Binding's own Objective/Boundary/Source-
Registration/Command-Policy/Secret-Exclusion-Policy/genesis-State shapes -- Kernel-wide,
already-pinned scaffolding that re-deriving a second copy of here would itself duplicate) and
``tests.evidence_helpers`` (for the Change-Free Verification Evidence request shape the real,
unchanged :func:`~manosube_agent_civilization.runtime.evidence_handoff.
route_runtime_observation_to_evidence` requires). This is the identical reuse the adopted V2
proof checkpoint itself already performed by hand (Issue #105 comment 6009496416: "The
Evidence request's Objective/Difference context uses existing test fixtures... while its
observation provenance comes from the real saved envelope") -- never a claim that any Human
Authority, Project Binding, or Evidence record this script produces is a production one. Every
object this script constructs is labelled, in its own `project_id`/`grant_id`/`key_id` fields
and in this script's own printed output, as an isolated test artifact.

**What this script never does.** It never reads, writes, or logs a production credential; it
never provisions, rotates, or uploads an SSH key, a GitHub secret, or any other production
material; it never makes an actual network connection of its own (every real SSH/Actions call
happens in the *existing*, unmodified ``runtime_observation_transport.py``, fed only the files
this script writes); it never mutates a deployed application or service; it never merges,
closes an Issue, or declares completion of anything.

Subcommands::

    bootstrap          mint a disposable isolated Project Binding + Store, commit a genesis
                        runtime_deployment_declaration, and sign one bounded short-lived
                        runtime_observation_grant naming a real target -- writes grant.json,
                        target_identity.json, and project.json to --out-dir
    run-local-proof     run the real, shipped scripts/runtime_observation_probe.py as a real
                        LOCAL subprocess (explicitly never a live network call) against a
                        --bootstrap'd grant/target/store, through
                        CapturedProbeReportRuntimeAdapter and the real observe_runtime_target,
                        reopening the Store before an optional Evidence hand-off -- the one
                        local, fully offline proof that the bootstrapped world and the shipped
                        probe genuinely compose, before any real network attempt is made
"""

from __future__ import annotations

import argparse
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, TextIO

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.runtime import (
    commit_runtime_deployment_declaration,
    observe_runtime_target,
    route_runtime_observation_to_evidence,
)
from manosube_agent_civilization.runtime.adapter import CapturedProbeReportRuntimeAdapter
from manosube_agent_civilization.runtime.engine import parse_utc_instant
from manosube_agent_civilization.runtime.identity import (
    runtime_deployment_declaration_id,
    runtime_deployment_declaration_semantic_fingerprint,
    runtime_deployment_declaration_signing_payload,
    runtime_observation_grant_signing_payload,
)
from manosube_agent_civilization.runtime.types import SSH_PROBE_SCRIPT_SHA256
from manosube_agent_civilization.store import FileStateStore

#: A plain ``python scripts/runtime_observation_proof.py`` invocation puts this script's own
#: directory, never the repository root, at ``sys.path[0]`` -- so ``tests`` (an unpackaged,
#: namespace-only directory with no top-level installed entry point) would otherwise never
#: resolve, however this script is actually launched (a local shell, or the exact identical
#: launch form the Actions workflow job uses). This is the one, narrow, repo-root insertion
#: this script performs; it reads no file and imports nothing else from it. Every other import
#: above resolves without it, since this package itself is installed (``pip install -e .``).
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Deliberate, disclosed test-fixture reuse -- see the module docstring's own "Deliberate,
# disclosed test-fixture reuse" section. Must follow the sys.path insertion immediately above.
from tests.evidence_helpers import change_free_verification_evidence_request  # noqa: E402
from tests.fixtures import product_binding as pb  # noqa: E402
from tests.state_helpers import SCHEMA_ROOT  # noqa: E402

#: This script's own labelled isolated test Authority key id -- never a production Project
#: Binding's own key id, and never reused across runs for the signature itself (the
#: *identity reference string* is stable; the *key material* behind it is fresh every run).
_ISOLATED_AUTHORITY_KEY_ID = "AUTH-KEY-ISOLATED-ACTIONS-PROOF-0001"

_PROBE_SCRIPT_PATH = Path(__file__).resolve().parent / "runtime_observation_probe.py"


def _add_seconds(instant: str, seconds: float) -> str:
    parsed = parse_utc_instant(instant, "runtime_observation_proof --now")
    return (parsed + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


def _isolated_signing_key() -> tuple[Ed25519PrivateKey, dict[str, Any]]:
    """Generate a genuinely random, in-RAM Ed25519 key pair and return ``(private_key,
    human_authority_signing_key)`` -- the private half is never persisted, logged, or returned
    in any serializable form by this function's own caller chain; only the public half,
    embedded in *human_authority_signing_key*, is ever written to a Store or a file."""

    private_key = Ed25519PrivateKey.generate()
    public_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return private_key, {
        "algorithm": "ed25519",
        "key_id": _ISOLATED_AUTHORITY_KEY_ID,
        "public_key": public_hex,
    }


def _bootstrap_isolated_project(store: FileStateStore) -> dict[str, Any]:
    """Bind one disposable, isolated Project under a fresh random Authority key, reusing this
    repository's own Kernel-wide Project Binding genesis scaffolding
    (:mod:`tests.fixtures.product_binding`) for every field *except* the signing key itself,
    which this function always replaces with a key :func:`_isolated_signing_key` just
    generated -- the one substitution obligation B of the adopted handoff requires ("do not use
    publicly known deterministic fixture signing keys as deployed Authority").

    Returns ``{"project_id", "project_binding_id", "signing_key"}`` -- *signing_key* is the
    live :class:`Ed25519PrivateKey` object itself, kept only in this process's own memory for
    the remainder of this run, never serialized.
    """

    private_key, signing_key_dict = _isolated_signing_key()
    kwargs = pb.bind_project_kwargs()
    kwargs["human_authority_signing_key"] = signing_key_dict
    result = bind_project(
        store, **kwargs, additional_genesis_records=pb.genesis_records(), schema_root=SCHEMA_ROOT
    )
    return {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "human_authority_ref": kwargs["human_authority_ref"],
        "signing_key": private_key,
    }


def _commit_isolated_declaration(
    store: FileStateStore,
    *,
    project_id: str,
    project_binding_id: str,
    human_authority_ref: dict[str, Any],
    signing_key: Ed25519PrivateKey,
    deployment_fingerprint: str,
    now: str,
    valid_until: str,
    provider: str,
    deployment_id: str,
    instance_identity: str,
) -> dict[str, Any]:
    """Build, sign, and commit one genesis ``runtime_deployment_declaration`` naming the real
    target's own currently-declared identity (*deployment_fingerprint* -- the exact value the
    real target's probe is configured to self-report; never fabricated or echoed from anywhere
    else, the identical discipline Issue #105's own isolated-deployment-identity correction
    requires) through the real, unchanged
    :func:`~manosube_agent_civilization.runtime.commit_runtime_deployment_declaration`."""

    declaration: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": project_id,
        "project_binding_ref": {"kind": "project_binding", "id": project_binding_id},
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "deployment_fingerprint": deployment_fingerprint,
        "human_authority_ref": dict(human_authority_ref),
        "status": "ACTIVE",
        "declared_at": now,
        "valid_from": now,
        "valid_until": valid_until,
        "generation": 0,
        "predecessor_ref": None,
    }
    message = runtime_deployment_declaration_signing_payload(declaration)
    declaration["signature"] = {
        "algorithm": "ed25519",
        "key_id": _ISOLATED_AUTHORITY_KEY_ID,
        "value": signing_key.sign(message).hex(),
    }
    declaration["runtime_deployment_declaration_id"] = runtime_deployment_declaration_id(
        declaration
    )
    declaration["runtime_deployment_declaration_semantic_fingerprint"] = (
        runtime_deployment_declaration_semantic_fingerprint(declaration)
    )
    return commit_runtime_deployment_declaration(
        store, project_id, declaration, committed_at=now
    )


def _sign_isolated_grant(
    *,
    signing_key: Ed25519PrivateKey,
    grant_id: str,
    project_id: str,
    project_binding_id: str,
    provider: str,
    deployment_id: str,
    instance_identity: str,
    deployment_fingerprint: str,
    host: str,
    port: int,
    user: str,
    probe_identity: str,
    probe_script_sha256: str,
    deployment_config_fingerprint: str,
    permitted_fields: list[str],
    redaction_fields: list[str],
    max_output_bytes: int,
    max_lines: int,
    max_timeout_seconds: int,
    permitted_transports: list[str],
    issued_at: str,
    expires_at: str,
) -> dict[str, Any]:
    """Build and sign one bounded, short-lived ``runtime_observation_grant`` -- *issued_at*/
    *expires_at* are this exact trial's own narrow window, never a wide or recurring one, and
    this function fabricates no second grant-shaped owner: it is the identical closed field set
    :func:`~manosube_agent_civilization.runtime.identity.
    runtime_observation_grant_signing_payload` already signs over for every other grant in this
    repository."""

    grant: dict[str, Any] = {
        "schema_version": "0.1",
        "grant_id": grant_id,
        "project_id": project_id,
        "project_binding_id": project_binding_id,
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "deployment_fingerprint": deployment_fingerprint,
        "host": host,
        "port": port,
        "user": user,
        "probe_identity": probe_identity,
        "probe_script_sha256": probe_script_sha256,
        "deployment_config_fingerprint": deployment_config_fingerprint,
        "permitted_fields": list(permitted_fields),
        "redaction_fields": list(redaction_fields),
        "max_output_bytes": max_output_bytes,
        "max_lines": max_lines,
        "max_timeout_seconds": max_timeout_seconds,
        "permitted_transports": list(permitted_transports),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "decision_status": "RATIFIED",
    }
    message = runtime_observation_grant_signing_payload(grant)
    grant["signature"] = {
        "algorithm": "ed25519",
        "key_id": _ISOLATED_AUTHORITY_KEY_ID,
        "value": signing_key.sign(message).hex(),
    }
    return grant


def bootstrap_isolated_world(
    *,
    store_root: Path,
    now: str,
    grant_validity_seconds: float,
    host: str,
    port: int,
    user: str,
    probe_identity: str,
    deployment_fingerprint: str,
    deployment_config_fingerprint: str,
    probe_script_sha256: str,
    permitted_fields: list[str],
    redaction_fields: list[str],
    permitted_transports: list[str],
    max_output_bytes: int,
    max_lines: int,
    max_timeout_seconds: int,
    provider: str = "isolated-actions-proof",
    deployment_id: str = "isolated-actions-proof-target",
    instance_identity: str = "isolated-actions-proof-target-1",
    grant_id: str | None = None,
) -> dict[str, Any]:
    """The one function both the ``bootstrap`` subcommand and this script's own test suite
    call -- mint a disposable isolated Project/Store/Authority, commit a genesis deployment
    declaration naming *deployment_fingerprint*, and sign a *grant_validity_seconds*-bounded
    grant naming the real target's own *host*/*port*/*user*/*probe_identity*. Returns
    ``{"project_id", "project_binding_id", "grant", "target_identity"}`` -- never the signing
    key itself, which stays inside this call and is discarded the moment it returns."""

    store = FileStateStore(store_root, schema_root=SCHEMA_ROOT)
    world = _bootstrap_isolated_project(store)
    valid_until = _add_seconds(now, grant_validity_seconds)

    declaration_commit = _commit_isolated_declaration(
        store,
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        human_authority_ref=world["human_authority_ref"],
        signing_key=world["signing_key"],
        deployment_fingerprint=deployment_fingerprint,
        now=now,
        valid_until=valid_until,
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
    )
    target_identity = {
        "provider": provider,
        "deployment_id": deployment_id,
        "instance_identity": instance_identity,
        "project_binding_ref": {"kind": "project_binding", "id": world["project_binding_id"]},
        "deployment_declaration_ref": declaration_commit["runtime_deployment_declaration_ref"],
        "deployment_fingerprint": deployment_fingerprint,
    }

    grant = _sign_isolated_grant(
        signing_key=world["signing_key"],
        grant_id=grant_id or f"GRANT-ISOLATED-ACTIONS-PROOF-{now}",
        project_id=world["project_id"],
        project_binding_id=world["project_binding_id"],
        provider=provider,
        deployment_id=deployment_id,
        instance_identity=instance_identity,
        deployment_fingerprint=deployment_fingerprint,
        host=host,
        port=port,
        user=user,
        probe_identity=probe_identity,
        probe_script_sha256=probe_script_sha256,
        deployment_config_fingerprint=deployment_config_fingerprint,
        permitted_fields=permitted_fields,
        redaction_fields=redaction_fields,
        max_output_bytes=max_output_bytes,
        max_lines=max_lines,
        max_timeout_seconds=max_timeout_seconds,
        permitted_transports=permitted_transports,
        issued_at=now,
        expires_at=valid_until,
    )

    return {
        "project_id": world["project_id"],
        "project_binding_id": world["project_binding_id"],
        "grant": grant,
        "target_identity": target_identity,
    }


def _cmd_bootstrap(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = bootstrap_isolated_world(
        store_root=Path(args.store_root),
        now=args.now,
        grant_validity_seconds=args.grant_validity_seconds,
        host=args.host,
        port=args.port,
        user=args.user,
        probe_identity=args.probe_identity,
        deployment_fingerprint=args.deployment_fingerprint,
        deployment_config_fingerprint=args.deployment_config_fingerprint,
        probe_script_sha256=args.probe_script_sha256,
        permitted_fields=args.permitted_fields.split(","),
        redaction_fields=(args.redaction_fields.split(",") if args.redaction_fields else []),
        permitted_transports=args.permitted_transports.split(","),
        max_output_bytes=args.max_output_bytes,
        max_lines=args.max_lines,
        max_timeout_seconds=args.max_timeout_seconds,
    )
    _write_json_file(out_dir / "grant.json", result["grant"])
    _write_json_file(out_dir / "target_identity.json", result["target_identity"])
    _write_json_file(
        out_dir / "project.json",
        {"project_id": result["project_id"], "project_binding_id": result["project_binding_id"]},
    )
    _write_json(
        sys.stdout,
        {
            "ok": True,
            "project_id": result["project_id"],
            "project_binding_id": result["project_binding_id"],
            "store_root": str(args.store_root),
            "grant_file": str(out_dir / "grant.json"),
            "target_identity_file": str(out_dir / "target_identity.json"),
            "project_file": str(out_dir / "project.json"),
            "grant_expires_at": result["grant"]["expires_at"],
            "note": (
                "isolated test Authority only -- no production credential, key, or Store "
                "was read, written, or provisioned by this command"
            ),
        },
    )
    return 0


def _run_real_probe_locally(
    *, probe_identity: str, expected_deployment_config_fingerprint: str, probe_config_dir: Path
) -> tuple[bytes, bytes, int]:
    """Run the real, shipped probe script as a real **local** subprocess -- explicitly never a
    live network call -- against a sibling ``runtime_observation_probe.config.json`` already
    prepared in *probe_config_dir* (the neutral identity/source/log fixture files this trial's
    operator set up on the real target; here, read locally for the offline composition proof).
    Returns the genuine, unmodified ``(stdout, stderr, returncode)`` triple -- never a
    hand-written stand-in for a successful report."""

    script_copy = probe_config_dir / "runtime_observation_probe.py"
    if not script_copy.exists():
        script_copy.write_bytes(_PROBE_SCRIPT_PATH.read_bytes())
    result = subprocess.run(  # noqa: S603 -- fixed executable/argv, local trial-only invocation
        [sys.executable, str(script_copy), probe_identity, expected_deployment_config_fingerprint],
        capture_output=True,
        timeout=30.0,
    )
    return result.stdout, result.stderr, result.returncode


def _cmd_run_local_proof(args: argparse.Namespace) -> int:
    with open(args.grant_file, encoding="utf-8") as stream:
        grant = json.load(stream)
    with open(args.target_identity_file, encoding="utf-8") as stream:
        target_identity = json.load(stream)
    with open(args.project_file, encoding="utf-8") as stream:
        project = json.load(stream)

    stdout, stderr, returncode = _run_real_probe_locally(
        probe_identity=grant["probe_identity"],
        expected_deployment_config_fingerprint=grant["deployment_config_fingerprint"],
        probe_config_dir=Path(args.probe_config_dir),
    )

    store = FileStateStore(Path(args.store_root), schema_root=SCHEMA_ROOT)
    adapter = CapturedProbeReportRuntimeAdapter(
        captured_stdout=stdout,
        captured_stderr=stderr,
        captured_returncode=returncode,
        grant=grant,
        store=store,
        project_id=project["project_id"],
        project_binding_id=project["project_binding_id"],
        now=args.now,
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
        "timeout_seconds": args.timeout_seconds,
        "redaction_fields": list(grant.get("redaction_fields", [])),
    }

    try:
        outcome = observe_runtime_target(
            store,
            project_id=project["project_id"],
            project_binding_id=project["project_binding_id"],
            target_identity=target_identity,
            boundary=boundary,
            adapter=adapter,
            observed_at=args.now,
        )
    except Exception as error:
        _write_json(sys.stdout, {"ok": False, "error": str(error)})
        return 1

    # Obligation E ("reopen Store to attest envelope"): a *second*, freshly constructed
    # FileStateStore instance, never the one the observation above already held open, proves
    # this receipt genuinely persisted rather than only existing in this process's own memory.
    reopened_store = FileStateStore(Path(args.store_root), schema_root=SCHEMA_ROOT)

    evidence_result: dict[str, Any] = {"status": "NOT_REQUESTED"}
    if args.with_evidence_handoff:
        raw_request = change_free_verification_evidence_request(provenance=None)
        rewritten = json.loads(
            json.dumps(raw_request).replace("PRJ-0001", project["project_id"])
        )
        try:
            evidence = route_runtime_observation_to_evidence(
                reopened_store, outcome["receipt"], project["project_id"], rewritten
            )
        except Exception as error:
            evidence_result = {"status": "REFUSED", "reason": str(error)}
        else:
            # Obligation E ("distinguish derived/file-saved Evidence from Store-committed
            # Evidence"): this call returns a *derived* Evidence record
            # route_runtime_observation_to_evidence itself hands back -- this script neither
            # claims nor performs any additional Store-commitment of that record on its own
            # behalf; whatever that function actually did is reported exactly as it did it.
            evidence_result = {
                "status": "DERIVED",
                "evidence_id": evidence.get("evidence_id"),
                "evidence_position": evidence.get("evidence_position"),
                "store_committed_by_this_script": False,
            }

    _write_json(
        sys.stdout,
        {
            "ok": True,
            "transport": "LOCAL_SUBPROCESS_STAND_IN",
            "live_network_call_made": False,
            "envelope_id": outcome["envelope"]["runtime_observation_envelope_id"],
            "observation_outcome": outcome["envelope"]["observation_outcome"],
            "receipt_status": outcome["receipt"].status,
            "observed_fields": outcome["envelope"]["observed_fields"],
            "evidence_handoff": evidence_result,
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser(
        "bootstrap",
        help=(
            "mint a disposable isolated Project Binding + Store under a fresh random "
            "Ed25519 key, commit a genesis deployment declaration, and sign one bounded "
            "short-lived runtime_observation_grant for a real target"
        ),
    )
    bootstrap.add_argument(
        "--store-root",
        required=True,
        help="a fresh, disposable directory (outside this checkout) for the isolated Store",
    )
    bootstrap.add_argument("--out-dir", required=True, help="where to write the output files")
    bootstrap.add_argument("--now", required=True)
    bootstrap.add_argument("--grant-validity-seconds", type=float, default=600.0)
    bootstrap.add_argument("--host", required=True)
    bootstrap.add_argument("--port", type=int, default=22)
    bootstrap.add_argument("--user", required=True)
    bootstrap.add_argument(
        "--probe-identity",
        required=True,
        choices=["OS_HEALTH_SNAPSHOT_BOUNDED", "SOURCE_LOG_EXCERPT_BOUNDED"],
    )
    bootstrap.add_argument(
        "--deployment-fingerprint",
        required=True,
        help="the real target's own currently-configured identity value -- never fabricated",
    )
    bootstrap.add_argument(
        "--deployment-config-fingerprint",
        required=True,
        help="the real target's own effective three-path deployment_config_fingerprint",
    )
    bootstrap.add_argument("--probe-script-sha256", default=SSH_PROBE_SCRIPT_SHA256)
    bootstrap.add_argument("--permitted-fields", default="hostname")
    bootstrap.add_argument("--redaction-fields", default="")
    bootstrap.add_argument(
        "--permitted-transports",
        default="GITHUB_ACTIONS,PREAUTHORIZED_UNATTENDED_SSH,MANUAL_SSH",
        help=(
            "comma-separated transport modes this grant permits. MANUAL_SSH is included by "
            "default alongside the two obligation B names so the identical grant also "
            "constructs CapturedProbeReportRuntimeAdapter for run-local-proof's own offline "
            "stand-in exercise, exactly the existing restriction that adapter already enforces"
        ),
    )
    bootstrap.add_argument("--max-output-bytes", type=int, default=1_048_576)
    bootstrap.add_argument("--max-lines", type=int, default=200)
    bootstrap.add_argument("--max-timeout-seconds", type=int, default=30)
    bootstrap.set_defaults(func=_cmd_bootstrap)

    run_local = subparsers.add_parser(
        "run-local-proof",
        help=(
            "run the real shipped probe script as a real LOCAL subprocess (never a live "
            "network call) against a --bootstrap'd grant/target/store, through the real "
            "canonical observe_runtime_target route"
        ),
    )
    run_local.add_argument("--grant-file", required=True)
    run_local.add_argument("--target-identity-file", required=True)
    run_local.add_argument("--project-file", required=True)
    run_local.add_argument("--store-root", required=True)
    run_local.add_argument("--now", required=True)
    run_local.add_argument("--timeout-seconds", type=int, default=30)
    run_local.add_argument(
        "--probe-config-dir",
        required=True,
        help=(
            "directory already holding a sibling runtime_observation_probe.config.json plus "
            "the neutral identity/source/log fixture files it names"
        ),
    )
    run_local.add_argument("--with-evidence-handoff", action="store_true")
    run_local.set_defaults(func=_cmd_run_local_proof)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
