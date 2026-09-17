"""Admit and publish the real Phase 21 independent-reproducer trust anchor (Issue #89, PR #90
Round 4, ``ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER``).

SHUKOU independently pre-registered a real Ed25519 public key for the Phase 21 independent
reproducer via PR #90 comment
https://github.com/manosube/manosube-agent-civilization-os/pull/90#issuecomment-5709021178
(author ``manosube``, ``OWNER``). This script incorporates that already-verified public key into
one ``comparative_benchmark_independent_reproducer_trust_anchor`` record through the existing
production route (``manosube_agent_civilization.comparative_benchmark.route.
admit_independent_reproducer_trust_anchor``) against a fresh, disposable ``FileStateStore`` --
the identical checked-in-artifact pattern ``scripts/generate_comparative_benchmark_artifacts.py``
already establishes, since this repository's own Store is always ephemeral/disposable, never a
persistent cross-session backend (see ``examples/comparative_benchmark/README.md``).

**This script never touches, requests, reads, or logs any private key material.** It only
consumes the public key hex and key id SHUKOU already disclosed in the plaintext PR comment
above; ``engine.build_independent_reproducer_trust_anchor`` itself imports only
``Ed25519PublicKey``, never the private-key counterpart (see the package's own static-conformance
proof)."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "examples" / "comparative_benchmark"

#: SHUKOU's own real, already-verified pre-registration for the Phase 21 independent reproducer
#: (PR #90 comment 5709021178, author ``manosube``, ``OWNER``) -- never a test-double keypair.
REPRODUCER_ACTOR_OR_AUTHORITY_ID = "SHUKOU_PHASE21_REPRODUCER"
ED25519_PUBLIC_KEY_HEX = "0f183eed0aae19425e8f85c3a619b21ddc4efdb432966ab91cfdbc6dd7f2fdab"
KEY_ID = "sha256:447776a9aaad1ebf2bc6936f169e494e418187fb71553086680b355a7d9f3f49"
VALID_FROM = "2026-09-17T05:05:49Z"
VALID_UNTIL: str | None = None
REVOCATION_STATUS = "ACTIVE"

ADOPTION_REF = {
    "adoption_id": "ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER",
    "comment_id": "5709021178",
    "comment_url": (
        "https://github.com/manosube/manosube-agent-civilization-os/pull/90#issuecomment-5709021178"
    ),
}


def _write_json(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def admit(*, output_dir: Path) -> Path:
    sys.path.insert(0, str(ROOT))
    from tests.fixtures import comparative_benchmark as cb
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.comparative_benchmark import route as cb_route
    from manosube_agent_civilization.store import FileStateStore

    published_protocol_freeze = json.loads(
        (output_dir / "protocol_freeze.json").read_text(encoding="utf-8")
    )
    authorized_protocol_or_corpus_ref = {
        "protocol_freeze_id": published_protocol_freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": published_protocol_freeze[
            "protocol_freeze_semantic_fingerprint"
        ],
    }

    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    with tempfile.TemporaryDirectory(prefix="cb21-trust-anchor-admission-") as tmp:
        store = FileStateStore(Path(tmp) / "backend", schema_root=SCHEMA_ROOT)
        trust_anchor = cb_route.admit_independent_reproducer_trust_anchor(
            store,
            project_id=cb.PROJECT_ID,
            project_binding_ref={"kind": "project_binding", "id": cb.PROJECT_BINDING_ID},
            reproducer_actor_or_authority_id=REPRODUCER_ACTOR_OR_AUTHORITY_ID,
            ed25519_public_key=ED25519_PUBLIC_KEY_HEX,
            key_id=KEY_ID,
            adoption_ref=dict(ADOPTION_REF),
            authorized_protocol_or_corpus_ref=authorized_protocol_or_corpus_ref,
            valid_from=VALID_FROM,
            valid_until=VALID_UNTIL,
            revocation_status=REVOCATION_STATUS,
            generated_at=generated_at,
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "independent_reproducer_trust_anchor.json"
    _write_json(path, trust_anchor)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=str(ARTIFACT_DIR),
        help=f"directory to read protocol_freeze.json from and write the trust anchor to "
        f"(default: {ARTIFACT_DIR})",
    )
    args = parser.parse_args(argv)

    path = admit(output_dir=Path(args.output_dir))
    print(f"INDEPENDENT_REPRODUCER_TRUST_ANCHOR_WRITTEN={path}")  # noqa: T201 -- this script's own CLI report
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
