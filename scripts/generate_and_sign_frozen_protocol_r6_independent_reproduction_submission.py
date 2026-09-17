"""Generate and locally sign one genuine independent reproduction submission for PR #90's
corrected Round 6 rebind frozen protocol (Issue #89,
`ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN`, comment 5715652626).

Adapted from `scripts/generate_and_sign_comparative_benchmark_independent_reproduction_
submission.py` (the Round 5 script for the historical Round 1-5 8-task protocol), pointed
instead at this round's own published artifacts
(`examples/comparative_benchmark/frozen_protocol_r6/`) and this round's own predeclared,
native-Agent-free mechanical reproduction procedure
(`tests.comparative_benchmark.frozen_protocol_reproduction.reproduce_raw_events`) -- never the
historical protocol's own `tests.comparative_benchmark.orchestrator.run_comparative_benchmark`.

Runs entirely on the machine that holds the real private key (SHUKOU's own Windows PC). It
never requests, accepts, prints, logs, or persists raw private-key hex, and never touches the
private key at all except to open the caller-supplied encrypted PKCS8 PEM file in memory for
the one `sign()` call -- the key material is never written to this script's own output, and the
PEM path/passphrase are never included in `--output`.

Every field of the emitted submission is produced mechanically by this package's own shipped
identity/engine functions -- never hand-authored. Before ever writing the completed submission
to `--output`, this script verifies the signature itself, locally, against the already-
registered public key (`verify_ed25519_signature`) -- a submission this script itself cannot
verify is never written.

One end-to-end entrypoint: `scripts/reproduce_and_sign_frozen_protocol_r6_submission.ps1` wraps
this script for PowerShell/Windows."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "examples" / "comparative_benchmark" / "frozen_protocol_r6"

#: SHUKOU's own real, already-verified, pre-registered public key for the Phase 21 independent
#: reproducer (PR #90 comment 5709021178, author `manosube`, `OWNER`) -- unchanged from the
#: Round 5 script; this script only ever reads this constant to confirm the caller's own PEM
#: matches it, never to derive or guess the private key.
REPRODUCER_ACTOR_OR_AUTHORITY_ID = "SHUKOU_PHASE21_REPRODUCER"
REGISTERED_ED25519_PUBLIC_KEY_HEX = (
    "0f183eed0aae19425e8f85c3a619b21ddc4efdb432966ab91cfdbc6dd7f2fdab"
)


def _agent_runtime_model_configuration_identity() -> dict[str, str]:
    return {
        "agent_family": "independent-reproducer-shukou",
        "version": "0.1",
        "runtime": "cpython",
        "model": "n/a",
        "configuration": "default",
        "tool_surface": "none",
    }


def _execution_environment_manifest() -> dict[str, str]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }


def _reproduce_raw_events() -> list[dict[str, Any]]:
    """Mechanically reproduce this round's own frozen corpus via its own predeclared,
    native-Agent-free reproduction procedure -- never hand-authored raw events, and never a
    re-invocation of a native Agent capability this repository has no way to offer a third
    party (see `tests.fixtures.comparative_benchmark_rebind_protocol`'s own
    `comparability_loss_receipts`)."""

    sys.path.insert(0, str(ROOT))
    from tests.comparative_benchmark.frozen_protocol_reproduction import reproduce_raw_events

    return list(reproduce_raw_events())


def _build_draft_submission(
    *, reproduced_raw_events: list[dict[str, Any]], submission_time: str
) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    import hashlib

    from manosube_agent_civilization.comparative_benchmark.engine import aggregate_metrics
    from manosube_agent_civilization.comparative_benchmark.identity import (
        independent_reproduction_submission_id,
        independent_reproduction_submission_semantic_fingerprint,
    )
    from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

    protocol_freeze = json.loads((ARTIFACT_DIR / "protocol_freeze.json").read_text())
    result_bundle = json.loads((ARTIFACT_DIR / "result_bundle.json").read_text())

    reproduced_metrics = aggregate_metrics(reproduced_raw_events, protocol_freeze)
    content_address = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(list(reproduced_raw_events))).hexdigest()
    )

    original_metrics = result_bundle["metrics"]
    if set(reproduced_metrics) != set(original_metrics):
        agreement = "INCOMPARABLE"
    elif reproduced_metrics == original_metrics:
        agreement = "MATCH"
    else:
        agreement = "DIVERGENT"

    draft: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": protocol_freeze["project_id"],
        "project_binding_ref": dict(result_bundle["project_binding_ref"]),
        "reproducer_actor_or_authority_id": REPRODUCER_ACTOR_OR_AUTHORITY_ID,
        "provenance_mechanism": "ED25519_SIGNATURE",
        "original_result_bundle_ref": {
            "result_bundle_id": result_bundle["result_bundle_id"],
            "result_bundle_semantic_fingerprint": result_bundle[
                "result_bundle_semantic_fingerprint"
            ],
        },
        "protocol_freeze_ref": {
            "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
            "protocol_freeze_semantic_fingerprint": protocol_freeze[
                "protocol_freeze_semantic_fingerprint"
            ],
        },
        "reproduced_raw_events": reproduced_raw_events,
        "reproduced_raw_events_content_address": content_address,
        "agent_runtime_model_configuration_identity": _agent_runtime_model_configuration_identity(),
        "execution_environment_manifest": _execution_environment_manifest(),
        "reproduced_metrics": reproduced_metrics,
        "agreement": agreement,
        "submission_time": submission_time,
    }
    draft["independent_reproduction_submission_id"] = independent_reproduction_submission_id(draft)
    draft["independent_reproduction_submission_semantic_fingerprint"] = (
        independent_reproduction_submission_semantic_fingerprint(draft)
    )
    return draft


def _load_encrypted_pem_private_key(pem_path: Path, passphrase: str) -> Any:
    """Load *pem_path* as an encrypted PKCS8 PEM Ed25519 private key using *passphrase*. Never
    logs, prints, or returns the passphrase or the key's own raw bytes."""

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        PublicFormat,
        load_pem_private_key,
    )

    pem_bytes = pem_path.read_bytes()
    private_key = load_pem_private_key(pem_bytes, password=passphrase.encode("utf-8"))
    if not isinstance(private_key, Ed25519PrivateKey):
        raise SystemExit(f"{pem_path} is not an Ed25519 private key")

    public_key_hex = (
        private_key.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
    )
    if public_key_hex != REGISTERED_ED25519_PUBLIC_KEY_HEX:
        raise SystemExit(
            f"{pem_path} does not match the registered public key "
            f"{REGISTERED_ED25519_PUBLIC_KEY_HEX} -- refusing to sign with the wrong key"
        )
    return private_key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pem-path",
        required=True,
        type=Path,
        help="path to SHUKOU's own encrypted PKCS8 PEM private key file (read only on this "
        "machine, never uploaded, copied, or logged by this script)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="path to write the completed, publicly-safe submission JSON to (default: stdout). "
        "Never contains the private key or passphrase.",
    )
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    from manosube_agent_civilization.comparative_benchmark.engine import verify_ed25519_signature
    from manosube_agent_civilization.comparative_benchmark.identity import (
        independent_reproduction_submission_signing_payload,
    )
    from manosube_agent_civilization.work_time_transparency.clock import default_clock

    print(  # noqa: T201 -- this script's own CLI progress report, to stderr
        "Reproducing the frozen corpus (this round's own mechanical, native-Agent-free "
        "reproduction procedure)...",
        file=sys.stderr,
    )
    reproduced_raw_events = _reproduce_raw_events()

    submission_time = default_clock()
    draft = _build_draft_submission(
        reproduced_raw_events=reproduced_raw_events, submission_time=submission_time
    )
    payload = independent_reproduction_submission_signing_payload(draft)

    passphrase = getpass.getpass(f"Passphrase for {args.pem_path} (input hidden): ")
    private_key = _load_encrypted_pem_private_key(args.pem_path, passphrase)
    del passphrase  # never retained beyond the one load call above

    signature_hex = private_key.sign(payload).hex()
    del private_key  # never retained beyond the one sign() call above

    if not verify_ed25519_signature(
        public_key_hex=REGISTERED_ED25519_PUBLIC_KEY_HEX,
        message=payload,
        signature_hex=signature_hex,
    ):
        raise SystemExit(
            "local signature verification failed -- refusing to emit an unverifiable submission"
        )

    submission = dict(draft)
    submission["signature"] = {
        "algorithm": "ed25519",
        "public_key": REGISTERED_ED25519_PUBLIC_KEY_HEX,
        "value": signature_hex,
    }

    output_text = json.dumps(submission, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(output_text, encoding="utf-8")
        print(f"SUBMISSION_WRITTEN={args.output}", file=sys.stderr)  # noqa: T201
    else:
        print(output_text)  # noqa: T201 -- this script's own CLI output, the completed submission

    print(  # noqa: T201 -- this script's own CLI progress report, to stderr
        "Locally verified. This submission is safe to publish and hand to "
        "route.admit_independent_reproduction_submission -- it contains no private-key material.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
