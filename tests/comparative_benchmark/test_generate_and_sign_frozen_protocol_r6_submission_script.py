"""Decisive proof for ``scripts.generate_and_sign_frozen_protocol_r6_independent_reproduction_
submission`` (PR #90 corrected Round 6 rebind, ``ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_
FRESH_RUN``, comment 5715652626).

Every test below signs with a fresh, disposable, ephemeral Ed25519 test keypair (never SHUKOU's
own real key) wrapped in a genuine encrypted PKCS8 PEM file, standing in for what a real
reproducer's own PEM/passphrase pair looks like to this script -- identical discipline to
``test_generate_and_sign_independent_reproduction_submission_script.py``'s own proof for the
historical Round 1-5 script, adapted to this round's own frozen protocol and its own mechanical,
native-Agent-free reproduction procedure."""

from __future__ import annotations

import json
from pathlib import Path
import platform
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    PublicFormat,
)
import pytest
import scripts.generate_and_sign_frozen_protocol_r6_independent_reproduction_submission as gen
from tests.comparative_benchmark import frozen_protocol_reproduction as reproduction
from tests.fixtures import comparative_benchmark_rebind_protocol as rb
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.identity import (
    independent_reproduction_submission_id,
    independent_reproduction_submission_semantic_fingerprint,
)
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.work_time_transparency.clock import default_clock

_PASSPHRASE = "test-passphrase-never-the-real-one"  # noqa: S105 -- disposable test-only literal


def _disposable_encrypted_pem(tmp_path: Path) -> tuple[Path, str, Ed25519PrivateKey]:
    private_key = Ed25519PrivateKey.generate()
    public_key_hex = (
        private_key.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
    )
    pem_path = tmp_path / "disposable_test_key.pem"
    pem_path.write_bytes(
        private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=BestAvailableEncryption(_PASSPHRASE.encode("utf-8")),
        )
    )
    return pem_path, public_key_hex, private_key


def _committed_freeze_and_bundle(
    tmp_path: Path,
) -> tuple[FileStateStore, dict[str, Any], dict[str, Any]]:
    store = FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)
    freeze = cb_route.commit_protocol_freeze(
        store,
        project_id=rb.CB_PROJECT_ID,
        **rb.protocol_freeze_kwargs(generated_at=default_clock()),
    )
    raw_events = reproduction.reproduce_raw_events()
    bundle = cb_route.commit_result_bundle(
        store,
        project_id=rb.CB_PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": rb.CB_PROJECT_BINDING_ID},
        protocol_freeze=freeze,
        raw_events=raw_events,
        environment_manifest={
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        generated_at=default_clock(),
    )
    return store, freeze, bundle


# --- PEM loading: wrong key / wrong passphrase / correct key ------------------------------------ #


def test_load_encrypted_pem_private_key_refuses_a_key_that_is_not_the_registered_one(
    tmp_path: Path,
) -> None:
    pem_path, _public_key_hex, _private_key = _disposable_encrypted_pem(tmp_path)

    with pytest.raises(SystemExit, match="does not match the registered public key"):
        gen._load_encrypted_pem_private_key(pem_path, _PASSPHRASE)


def test_load_encrypted_pem_private_key_raises_on_a_wrong_passphrase(tmp_path: Path) -> None:
    pem_path, _public_key_hex, _private_key = _disposable_encrypted_pem(tmp_path)

    with pytest.raises(ValueError):
        gen._load_encrypted_pem_private_key(pem_path, "definitely-the-wrong-passphrase")


def test_load_encrypted_pem_private_key_accepts_the_matching_registered_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pem_path, public_key_hex, _private_key = _disposable_encrypted_pem(tmp_path)
    monkeypatch.setattr(gen, "REGISTERED_ED25519_PUBLIC_KEY_HEX", public_key_hex)

    loaded = gen._load_encrypted_pem_private_key(pem_path, _PASSPHRASE)

    assert (
        loaded.public_key().public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw).hex()
        == public_key_hex
    )


# --- draft submission construction (mechanical, never hand-authored) ---------------------------- #


def test_build_draft_submission_produces_a_self_consistent_mechanically_derived_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _store, freeze, bundle = _committed_freeze_and_bundle(tmp_path)
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "protocol_freeze.json").write_text(json.dumps(freeze))
    (artifact_dir / "result_bundle.json").write_text(json.dumps(bundle))
    monkeypatch.setattr(gen, "ARTIFACT_DIR", artifact_dir)

    reproduced_raw_events = reproduction.reproduce_raw_events()
    draft = gen._build_draft_submission(
        reproduced_raw_events=reproduced_raw_events, submission_time="2026-09-17T15:00:00Z"
    )

    assert draft["reproducer_actor_or_authority_id"] == gen.REPRODUCER_ACTOR_OR_AUTHORITY_ID
    assert draft["reproduced_raw_events"] == reproduced_raw_events
    assert draft["independent_reproduction_submission_id"].startswith("CBIRS-")
    assert draft["agreement"] == "MATCH"
    assert (
        independent_reproduction_submission_id(draft)
        == draft["independent_reproduction_submission_id"]
    )
    assert (
        independent_reproduction_submission_semantic_fingerprint(draft)
        == draft["independent_reproduction_submission_semantic_fingerprint"]
    )


# --- full end-to-end round trip: reproduce -> sign -> locally verify -> emit -> real admission --- #


def test_main_end_to_end_sign_verify_emit_and_real_admission_round_trip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The complete round trip against a disposable test key, ending in a real admission
    through the production route -- a successful admission is the decisive proof this
    reproduction is genuine."""

    store, freeze, bundle = _committed_freeze_and_bundle(tmp_path)
    pem_path, public_key_hex, _private_key = _disposable_encrypted_pem(tmp_path)
    out_path = tmp_path / "submission.json"

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "protocol_freeze.json").write_text(json.dumps(freeze))
    (artifact_dir / "result_bundle.json").write_text(json.dumps(bundle))

    monkeypatch.setattr(gen, "ARTIFACT_DIR", artifact_dir)
    monkeypatch.setattr(gen, "REGISTERED_ED25519_PUBLIC_KEY_HEX", public_key_hex)
    monkeypatch.setattr("getpass.getpass", lambda *_a, **_kw: _PASSPHRASE)

    exit_code = gen.main(["--pem-path", str(pem_path), "--output", str(out_path)])
    assert exit_code == 0

    raw_output = out_path.read_text(encoding="utf-8")
    assert _PASSPHRASE not in raw_output
    submission = json.loads(raw_output)
    assert not any("private" in key.lower() for key in submission)
    assert submission["signature"]["public_key"] == public_key_hex
    assert submission["agreement"] == "MATCH"

    freeze_ref = {
        "protocol_freeze_id": freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": freeze["protocol_freeze_semantic_fingerprint"],
    }
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=rb.CB_PROJECT_ID,
        project_binding_ref={"kind": "project_binding", "id": rb.CB_PROJECT_BINDING_ID},
        reproducer_actor_or_authority_id=gen.REPRODUCER_ACTOR_OR_AUTHORITY_ID,
        ed25519_public_key=public_key_hex,
        key_id="disposable-test-key-for-frozen-protocol-r6",
        adoption_ref={"adoption_id": "TEST-ONLY", "comment_id": "0", "comment_url": "n/a"},
        authorized_protocol_or_corpus_ref=freeze_ref,
        valid_from="2026-01-01T00:00:00.000001Z",
        valid_until=None,
        revocation_status="ACTIVE",
        generated_at="2026-01-01T00:00:00.000001Z",
    )

    committed = cb_route.admit_independent_reproduction_submission(
        store, project_id=rb.CB_PROJECT_ID, submission=submission
    )

    assert (
        committed["independent_reproduction_submission_id"]
        == submission["independent_reproduction_submission_id"]
    )
