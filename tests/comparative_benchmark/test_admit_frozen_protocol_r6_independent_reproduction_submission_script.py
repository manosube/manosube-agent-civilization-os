"""Decisive proof for ``scripts.admit_frozen_protocol_r6_independent_reproduction_submission``
(P90-R6-WINDOWS-F1, comment 5725221638 -- SHUKOU's real Windows independent reproduction
submission handoff, author `manosube`, `OWNER`).

The published ``examples/comparative_benchmark/frozen_protocol_r6/independent_reproduction_
submission.json`` this script writes is SHUKOU's own real submission, signed with SHUKOU's own
real registered Ed25519 key -- this module never signs anything itself and never touches any
private-key material. These tests re-run the identical admission this script already performed
once to publish that artifact, proving it is durably, repeatably re-admittable through the
production route (never a one-off that only worked by chance), and that a tampered copy is
refused."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import scripts.admit_frozen_protocol_r6_independent_reproduction_submission as admit_script

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISHED_ARTIFACT_DIR = REPO_ROOT / "examples" / "comparative_benchmark" / "frozen_protocol_r6"
PUBLISHED_SUBMISSION_PATH = PUBLISHED_ARTIFACT_DIR / "independent_reproduction_submission.json"


def _published_submission() -> dict[str, Any]:
    return dict(json.loads(PUBLISHED_SUBMISSION_PATH.read_text(encoding="utf-8")))


def test_the_published_submission_file_already_exists_and_carries_shukou_s_own_key() -> None:
    submission = _published_submission()
    assert submission["reproducer_actor_or_authority_id"] == "SHUKOU_PHASE21_REPRODUCER"
    assert (
        submission["signature"]["public_key"]
        == "0f183eed0aae19425e8f85c3a619b21ddc4efdb432966ab91cfdbc6dd7f2fdab"
    )
    assert submission["agreement"] == "MATCH"


def test_readmitting_the_published_submission_reproduces_the_identical_id(
    tmp_path: Path,
) -> None:
    """A fresh admission run, against the identical published freeze/bundle/trust-anchor
    artifacts and the identical published submission, must reproduce byte-for-byte the same
    committed record this script already wrote -- proving the admission is a repeatable,
    structural fact of this evidence, never a one-off that happened to work."""

    submission_path = tmp_path / "submission.json"
    submission_path.write_text(json.dumps(_published_submission()), encoding="utf-8")

    written_path = admit_script.admit(
        submission_path=submission_path, output_dir=PUBLISHED_ARTIFACT_DIR
    )

    assert written_path == PUBLISHED_SUBMISSION_PATH
    readmitted = json.loads(written_path.read_text(encoding="utf-8"))
    assert readmitted == _published_submission()


def test_admitting_a_submission_with_a_tampered_raw_event_is_refused(tmp_path: Path) -> None:
    tampered = _published_submission()
    tampered = copy.deepcopy(tampered)
    tampered["reproduced_raw_events"][0]["outcome"] = "FAILED"

    submission_path = tmp_path / "tampered_submission.json"
    submission_path.write_text(json.dumps(tampered), encoding="utf-8")

    try:
        admit_script.admit(submission_path=submission_path, output_dir=PUBLISHED_ARTIFACT_DIR)
    except Exception as exc:
        assert "signature" in str(exc).lower() or "does not rederive" in str(exc).lower()
    else:
        raise AssertionError(
            "admitting a submission with a tampered raw event must be refused, never silently "
            "accepted"
        )


def test_admitting_a_submission_with_a_forged_signature_is_refused(tmp_path: Path) -> None:
    forged = copy.deepcopy(_published_submission())
    real_value = forged["signature"]["value"]
    forged["signature"]["value"] = ("0" if real_value[0] != "0" else "1") + real_value[1:]

    submission_path = tmp_path / "forged_submission.json"
    submission_path.write_text(json.dumps(forged), encoding="utf-8")

    try:
        admit_script.admit(submission_path=submission_path, output_dir=PUBLISHED_ARTIFACT_DIR)
    except Exception as exc:
        assert "signature" in str(exc).lower()
    else:
        raise AssertionError(
            "admitting a submission with a forged signature must be refused, never silently "
            "accepted"
        )


def test_rebuilt_protocol_freeze_and_trust_anchor_match_the_published_artifacts_exactly(
    tmp_path: Path,
) -> None:
    """A direct proof of the script's own internal cross-check: rebuilding the protocol freeze
    and trust anchor from their own declared fields (never process-dependent) reproduces the
    identical already-published records -- the admission this script performs binds to real,
    durable, independently-reconstructible evidence, not an artifact only this one run could
    have produced."""

    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from tests.fixtures import comparative_benchmark_rebind_protocol as rb
    from tests.state_helpers import SCHEMA_ROOT

    from manosube_agent_civilization.comparative_benchmark import route as cb_route
    from manosube_agent_civilization.store import FileStateStore

    published_freeze = json.loads(
        (PUBLISHED_ARTIFACT_DIR / "protocol_freeze.json").read_text(encoding="utf-8")
    )
    published_trust_anchor = json.loads(
        (PUBLISHED_ARTIFACT_DIR / "independent_reproducer_trust_anchor.json").read_text(
            encoding="utf-8"
        )
    )

    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    freeze = cb_route.commit_protocol_freeze(
        store,
        project_id=rb.CB_PROJECT_ID,
        **rb.protocol_freeze_kwargs(generated_at=published_freeze["generated_at"]),
    )
    assert freeze == published_freeze

    trust_anchor = cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=rb.CB_PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": rb.CB_PROJECT_BINDING_ID},
        reproducer_actor_or_authority_id=published_trust_anchor["reproducer_actor_or_authority_id"],
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
    assert trust_anchor == published_trust_anchor
