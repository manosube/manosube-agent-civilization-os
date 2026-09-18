"""Admit SHUKOU's real, Windows-executed independent reproduction submission for PR #90's
corrected Round 6 rebind frozen protocol (P90-R6-WINDOWS-F1, `ADOPT_P90_R6_WINDOWS_PORTABILITY_
FIX`, comment 5723625948; submission handed off in comment 5725221638, author `manosube`,
`OWNER`).

Rebuilds this round's own already-published `protocol_freeze`/`independent_reproducer_trust_
anchor` deterministically (via the production builder routes -- neither record's identity
depends on anything process-local, so rebuilding from the identical declared fields/`generated_
at` reproduces a byte-identical record) into a fresh, disposable `FileStateStore` -- the identical
checked-in-artifact pattern `scripts/admit_comparative_benchmark_independent_reproducer_trust_
anchor.py` already establishes (this repository's own Store is always ephemeral/disposable,
never a persistent cross-session backend). The `result_bundle`, by contrast, embeds `generation_
process_id = os.getpid()` in its own semantic fingerprint by design (`engine.build_result_bundle`'s
own same-process-reuse detector) -- no later process can ever rebuild it byte-identically via the
builder route, so this script instead commits the already-published `result_bundle.json` body
verbatim through the identical `commit_coordination_record_at_tip` primitive `route.
commit_result_bundle` itself uses internally, preserving its original identity exactly rather than
re-deriving a new one.

Verifies every rebuilt/committed record's id matches the already-published JSON under
`examples/comparative_benchmark/frozen_protocol_r6/`, then admits SHUKOU's own exact submission
(read verbatim from `--submission-path`, never hand-authored or field-adjusted by this script)
through the production `route.admit_independent_reproduction_submission` path against the
freshly-rebuilt trust anchor, and finally resolves the admitted record back to prove the round
trip.

This script never touches, requests, or reads any private-key material -- the submission it
admits is already fully signed and was already locally verified by SHUKOU's own generator
script before being posted."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "examples" / "comparative_benchmark" / "frozen_protocol_r6"


def _load_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def admit(*, submission_path: Path, output_dir: Path) -> Path:
    sys.path.insert(0, str(ROOT))
    from tests.fixtures import comparative_benchmark_rebind_protocol as rb
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.comparative_benchmark import route as cb_route
    from manosube_agent_civilization.store import FileStateStore

    published_freeze = _load_json(output_dir / "protocol_freeze.json")
    published_bundle = _load_json(output_dir / "result_bundle.json")
    published_trust_anchor = _load_json(output_dir / "independent_reproducer_trust_anchor.json")
    submission = _load_json(submission_path)

    import tempfile

    with tempfile.TemporaryDirectory(prefix="cb21-r6-submission-admission-") as tmp:
        store = FileStateStore(Path(tmp) / "backend", schema_root=SCHEMA_ROOT)

        freeze = cb_route.commit_protocol_freeze(
            store,
            project_id=rb.CB_PROJECT_ID,
            **rb.protocol_freeze_kwargs(generated_at=published_freeze["generated_at"]),
        )
        if freeze["protocol_freeze_id"] != published_freeze["protocol_freeze_id"]:
            raise SystemExit(
                "rebuilt protocol_freeze_id does not match the already-published artifact -- "
                f"rebuilt={freeze['protocol_freeze_id']!r} "
                f"published={published_freeze['protocol_freeze_id']!r}"
            )

        bundle_id = published_bundle["result_bundle_id"]
        bundle = store.commit_coordination_record_at_tip(
            rb.CB_PROJECT_ID,
            bundle_id,
            cb_route.RESULT_BUNDLE_RECORD_KIND,
            bundle_id,
            dict(published_bundle),
            expected_predecessor=None,
        )
        if bundle != published_bundle:
            raise SystemExit(
                "committed result_bundle diverges from the already-published artifact byte-for-byte"
            )

        trust_anchor = cb_route.admit_independent_reproducer_trust_anchor(
            store,
            project_id=rb.CB_PROJECT_ID,
            project_binding_ref={"kind": "project_binding", "id": rb.CB_PROJECT_BINDING_ID},
            reproducer_actor_or_authority_id=published_trust_anchor[
                "reproducer_actor_or_authority_id"
            ],
            ed25519_public_key=published_trust_anchor["ed25519_public_key"],
            key_id=published_trust_anchor["key_id"],
            adoption_ref=dict(published_trust_anchor["adoption_ref"]),
            authorized_protocol_or_corpus_ref=dict(
                published_trust_anchor["authorized_protocol_or_corpus_ref"]
            ),
            valid_from=published_trust_anchor["valid_from"],
            valid_until=published_trust_anchor["valid_until"],
            revocation_status=published_trust_anchor["revocation_status"],
            generated_at=published_trust_anchor["generated_at"],
        )
        if trust_anchor["trust_anchor_id"] != published_trust_anchor["trust_anchor_id"]:
            raise SystemExit(
                "rebuilt trust_anchor_id does not match the already-published artifact -- "
                f"rebuilt={trust_anchor['trust_anchor_id']!r} "
                f"published={published_trust_anchor['trust_anchor_id']!r}"
            )

        committed = cb_route.admit_independent_reproduction_submission(
            store, project_id=rb.CB_PROJECT_ID, submission=submission
        )

        resolved = cb_route.resolve_independent_reproduction_submission(
            store,
            project_id=rb.CB_PROJECT_ID,
            independent_reproduction_submission_id=committed[
                "independent_reproduction_submission_id"
            ],
        )
        if resolved != committed:
            raise SystemExit(
                "resolve_independent_reproduction_submission did not round-trip the just-"
                "admitted record"
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "independent_reproduction_submission.json"
    _write_json(path, committed)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submission-path",
        required=True,
        type=Path,
        help="path to SHUKOU's own exact, already-signed submission JSON (verbatim, never "
        "hand-authored or field-adjusted by this script)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ARTIFACT_DIR),
        help=f"directory to read the published protocol_freeze/result_bundle/trust_anchor from "
        f"and write the admitted submission to (default: {ARTIFACT_DIR})",
    )
    args = parser.parse_args(argv)

    path = admit(submission_path=args.submission_path, output_dir=Path(args.output_dir))
    print(f"INDEPENDENT_REPRODUCTION_SUBMISSION_WRITTEN={path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
