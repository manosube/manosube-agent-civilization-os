"""P90-R5-F3 (PR #90 Round 5, ``ADOPT_P90_R5_REAL_AGENT_FINAL_PROTOCOL_AND_EXECUTABLE_
REPRODUCTION``): decisive proof for ``scripts.generate_and_sign_comparative_benchmark_
independent_reproduction_submission``.

Every test below signs with a fresh, disposable, ephemeral Ed25519 test keypair
(never SHUKOU's own real key) wrapped in a genuine encrypted PKCS8 PEM file, standing in for
what a real reproducer's own PEM/passphrase pair looks like to this script. This module never
holds SHUKOU's own private key and never will -- the script under test is itself designed to
never request, accept, print, log, or persist that key or its passphrase; these tests exercise
exactly that discipline (wrong-key refusal, wrong-passphrase failure, no leakage into the
emitted output) plus the full mechanical reproduce -> build -> sign -> locally-verify -> emit ->
admit round trip, reusing this package's own session-scoped ``comparative_benchmark_run``
fixture so the expensive real corpus run is paid for once, not once per test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    PublicFormat,
)
import pytest
import scripts.generate_and_sign_comparative_benchmark_independent_reproduction_submission as gen
from tests.fixtures import comparative_benchmark as cb

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.identity import (
    independent_reproduction_submission_id,
    independent_reproduction_submission_semantic_fingerprint,
)

_PASSPHRASE = "test-passphrase-never-the-real-one"  # noqa: S105 -- disposable test-only literal


def _disposable_encrypted_pem(tmp_path: Path) -> tuple[Path, str, Ed25519PrivateKey]:
    """A fresh, ephemeral Ed25519 keypair wrapped in a genuine encrypted PKCS8 PEM file --
    never SHUKOU's own real key."""

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
    comparative_benchmark_run: dict[str, Any],
) -> None:
    reproduced_raw_events = list(comparative_benchmark_run["reproduced_raw_events"])

    draft = gen._build_draft_submission(
        reproduced_raw_events=reproduced_raw_events, submission_time="2026-09-17T10:00:00Z"
    )

    assert draft["reproducer_actor_or_authority_id"] == gen.REPRODUCER_ACTOR_OR_AUTHORITY_ID
    assert draft["reproduced_raw_events"] == reproduced_raw_events
    assert draft["independent_reproduction_submission_id"].startswith("CBIRS-")
    assert draft["agreement"] in {"MATCH", "DIVERGENT", "INCOMPARABLE"}
    # id/fingerprint are recomputed from the draft's own body, never hand-set -- recomputing them
    # again from the returned draft must reproduce the identical values
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
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, comparative_benchmark_run: dict[str, Any]
) -> None:
    """The complete P90-R5-F3 round trip against a disposable test key, ending in a real
    admission through the production route -- a successful admission is the decisive proof this
    reproduction is genuine (see ``COMPARATIVE_BENCHMARK_CONTRACT.md`` section 8c)."""

    pem_path, public_key_hex, _private_key = _disposable_encrypted_pem(tmp_path)
    out_path = tmp_path / "submission.json"

    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    protocol_freeze = comparative_benchmark_run["protocol_freeze"]
    result_bundle = comparative_benchmark_run["result_bundle"]
    (artifact_dir / "protocol_freeze.json").write_text(json.dumps(protocol_freeze))
    (artifact_dir / "result_bundle.json").write_text(json.dumps(result_bundle))

    monkeypatch.setattr(gen, "ARTIFACT_DIR", artifact_dir)
    monkeypatch.setattr(gen, "REGISTERED_ED25519_PUBLIC_KEY_HEX", public_key_hex)
    monkeypatch.setattr(
        gen,
        "_reproduce_raw_events",
        lambda: list(comparative_benchmark_run["reproduced_raw_events"]),
    )
    monkeypatch.setattr("getpass.getpass", lambda *_a, **_kw: _PASSPHRASE)

    exit_code = gen.main(["--pem-path", str(pem_path), "--output", str(out_path)])
    assert exit_code == 0

    raw_output = out_path.read_text(encoding="utf-8")
    assert _PASSPHRASE not in raw_output
    submission = json.loads(raw_output)
    assert not any("private" in key.lower() for key in submission)
    assert submission["signature"]["public_key"] == public_key_hex

    store = comparative_benchmark_run["store"]

    freeze_ref = {
        "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": protocol_freeze[
            "protocol_freeze_semantic_fingerprint"
        ],
    }
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **cb.independent_reproducer_trust_anchor_kwargs(
            reproducer_actor_or_authority_id=gen.REPRODUCER_ACTOR_OR_AUTHORITY_ID,
            ed25519_public_key=public_key_hex,
            key_id="disposable-test-key-for-p90-r5-f3",
            authorized_protocol_or_corpus_ref=freeze_ref,
            valid_from="2026-01-01T00:00:00.000001Z",
            generated_at="2026-01-01T00:00:00.000001Z",
        ),
    )

    committed = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=submission
    )

    assert (
        committed["independent_reproduction_submission_id"]
        == submission["independent_reproduction_submission_id"]
    )
