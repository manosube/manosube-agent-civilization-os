"""P90-R3-F2 (PR #90 Round 3, ``ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE``)
and P90-R4-F2 (PR #90 Round 4, ``ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_
REPRODUCER``): decisive proof for the independent reproduction submission admission surface.

Claude Code never builds or signs a submission itself here -- every submission this suite
constructs is signed with a fresh, ephemeral test-double keypair
(``tests.fixtures.comparative_benchmark.generate_test_ed25519_keypair``), standing in for the
*shape* a genuinely separate, self-keyed actor would submit. Since P90-R4-F2, admission also
requires a Store-resolved ``comparative_benchmark_independent_reproducer_trust_anchor`` to
already be committed for the submission's own declared reproducer/protocol before any submission
can be admitted at all -- every test below that expects admission to reach its own real check
(rather than the trust-anchor-missing refusal) first admits one test-only trust anchor via
``_admit_trust_anchor`` below, itself built exclusively from test-double key material, never a
real independent reproducer's key. The point of every test below is that
``admit_independent_reproduction_submission`` verifies, and only verifies, an externally-supplied
record against Store-resolved parents/trust anchor -- it never trusts a caller's own claimed
identity, aggregate, or agreement, and it refuses fail-closed the moment any one of its
independent checks fails."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import comparative_benchmark as cb
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.engine import aggregate_metrics
from manosube_agent_civilization.comparative_benchmark.errors import (
    IndependentReproductionSubmissionValidationError,
)
from manosube_agent_civilization.comparative_benchmark.identity import (
    independent_reproduction_submission_id,
    independent_reproduction_submission_semantic_fingerprint,
    independent_reproduction_submission_signing_payload,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.store import FileStateStore
from manosube_agent_civilization.store.errors import RecordConflictError

_GENERATED_AT = "2026-01-01T00:00:00.000001Z"
_SUBMISSION_TIME = "2026-01-02T00:00:00.000001Z"
_PROJECT_BINDING_REF = {"kind": "project_binding", "id": cb.PROJECT_BINDING_ID}
_ENVIRONMENT_MANIFEST = {
    "python_implementation": "CPython",
    "python_version": "3.12.0",
    "platform": "test-platform",
}


def _store(tmp_path: Path) -> FileStateStore:
    return FileStateStore(tmp_path / "backend", schema_root=SCHEMA_ROOT)


def _freeze_kwargs() -> dict[str, Any]:
    return cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)


def _minimal_raw_events(
    protocol_freeze: dict[str, Any], *, outcome: str = "FAILED"
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for group in protocol_freeze["comparison_groups"]:
        for task_id in protocol_freeze["corpus_manifest"]["task_ids"]:
            events.append(
                {
                    "kind": "task_attempt",
                    "comparison_group_id": group["comparison_group_id"],
                    "task_id": task_id,
                    "outcome": outcome,
                }
            )
    return events


def _committed_freeze_and_bundle(store: FileStateStore) -> tuple[dict[str, Any], dict[str, Any]]:
    protocol_freeze = cb_route.commit_protocol_freeze(
        store, project_id=cb.PROJECT_ID, **_freeze_kwargs()
    )
    raw_events = _minimal_raw_events(protocol_freeze)
    original_bundle = cb_route.commit_result_bundle(
        store,
        project_id=cb.PROJECT_ID,
        project_binding_ref=_PROJECT_BINDING_REF,
        protocol_freeze=protocol_freeze,
        raw_events=raw_events,
        environment_manifest=_ENVIRONMENT_MANIFEST,
        generated_at=_GENERATED_AT,
    )
    return protocol_freeze, original_bundle


def _admit_trust_anchor(
    store: FileStateStore,
    *,
    protocol_freeze: dict[str, Any],
    public_key_hex: str,
    reproducer_actor_or_authority_id: str = "independent-reproducer-a",
    valid_from: str = _GENERATED_AT,
    valid_until: str | None = None,
    revocation_status: str = "ACTIVE",
) -> dict[str, Any]:
    """Pre-register one P90-R4-F2 trust anchor -- SHUKOU's own admission, standing in here for
    a test-only keypair -- authorizing *reproducer_actor_or_authority_id* to submit against
    *protocol_freeze*, before any submission naming that same (actor, protocol) pair can be
    admitted at all (``SELF_DECLARED_UNREGISTERED_KEY_REFUSED=true``)."""

    freeze_ref = {
        "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": protocol_freeze[
            "protocol_freeze_semantic_fingerprint"
        ],
    }
    kwargs = cb.independent_reproducer_trust_anchor_kwargs(
        reproducer_actor_or_authority_id=reproducer_actor_or_authority_id,
        ed25519_public_key=public_key_hex,
        key_id="test-key-1",
        authorized_protocol_or_corpus_ref=freeze_ref,
        valid_from=valid_from,
        valid_until=valid_until,
        revocation_status=revocation_status,
        generated_at=_GENERATED_AT,
    )
    return cb_route.admit_independent_reproducer_trust_anchor(
        store, project_id=cb.PROJECT_ID, **kwargs
    )


def _submission(
    *,
    protocol_freeze: dict[str, Any],
    original_result_bundle: dict[str, Any],
    private_key: Any,
    public_key_hex: str,
    reproduced_raw_events: list[dict[str, Any]] | None = None,
    reproducer_actor_or_authority_id: str = "independent-reproducer-a",
    submission_time: str = _SUBMISSION_TIME,
    reproduced_metrics_override: dict[str, Any] | None = None,
    agreement_override: str | None = None,
) -> dict[str, Any]:
    """Build one fully self-consistent, genuinely-signed independent reproduction submission --
    the honest path every decisive negative-control test below deviates from in exactly one
    dimension. *_override* parameters let a test construct a submission whose declared
    ``reproduced_metrics``/``agreement`` is wrong relative to the real recomputation, while
    still being internally self-consistent (its own id/fingerprint/signature all agree with
    what it declares) -- the only way to isolate the recomputation checks from the
    self-consistency checks."""

    if reproduced_raw_events is None:
        reproduced_raw_events = _minimal_raw_events(protocol_freeze)

    reproduced_metrics = (
        reproduced_metrics_override
        if reproduced_metrics_override is not None
        else aggregate_metrics(reproduced_raw_events, protocol_freeze)
    )
    if agreement_override is not None:
        agreement = agreement_override
    else:
        original_metrics = original_result_bundle["metrics"]
        if set(reproduced_metrics) != set(original_metrics):
            agreement = "INCOMPARABLE"
        elif reproduced_metrics == original_metrics:
            agreement = "MATCH"
        else:
            agreement = "DIVERGENT"

    content_address = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(list(reproduced_raw_events))).hexdigest()
    )

    draft: dict[str, Any] = {
        "schema_version": "0.1",
        "project_id": cb.PROJECT_ID,
        "project_binding_ref": dict(_PROJECT_BINDING_REF),
        "reproducer_actor_or_authority_id": reproducer_actor_or_authority_id,
        "provenance_mechanism": "ED25519_SIGNATURE",
        "original_result_bundle_ref": {
            "result_bundle_id": original_result_bundle["result_bundle_id"],
            "result_bundle_semantic_fingerprint": original_result_bundle[
                "result_bundle_semantic_fingerprint"
            ],
        },
        "protocol_freeze_ref": {
            "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
            "protocol_freeze_semantic_fingerprint": protocol_freeze[
                "protocol_freeze_semantic_fingerprint"
            ],
        },
        "reproduced_raw_events": list(reproduced_raw_events),
        "reproduced_raw_events_content_address": content_address,
        "agent_runtime_model_configuration_identity": (
            cb.independent_reproducer_agent_runtime_model_configuration_identity()
        ),
        "execution_environment_manifest": cb.independent_reproducer_execution_environment_manifest(),
        "reproduced_metrics": reproduced_metrics,
        "agreement": agreement,
        "submission_time": submission_time,
    }
    draft["independent_reproduction_submission_id"] = independent_reproduction_submission_id(draft)
    draft["independent_reproduction_submission_semantic_fingerprint"] = (
        independent_reproduction_submission_semantic_fingerprint(draft)
    )
    payload = independent_reproduction_submission_signing_payload(draft)
    draft["signature"] = {
        "algorithm": "ed25519",
        "public_key": public_key_hex,
        "value": private_key.sign(payload).hex(),
    }
    return draft


# --- valid admission, idempotent replay, conflict refusal --------------------------------------- #


def test_admit_independent_reproduction_submission_commits_and_resolves(tmp_path: Path) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )

    committed = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=submission
    )
    assert committed == submission
    assert committed["agreement"] == "MATCH"

    resolved = cb_route.resolve_independent_reproduction_submission(
        store,
        project_id=cb.PROJECT_ID,
        independent_reproduction_submission_id=committed["independent_reproduction_submission_id"],
    )
    assert resolved == committed


def test_admit_independent_reproduction_submission_is_idempotent_for_an_identical_body(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )

    first = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=submission
    )
    second = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=dict(submission)
    )
    assert first == second


def test_admit_independent_reproduction_submission_refuses_a_conflicting_resubmission(
    tmp_path: Path,
) -> None:
    """`INDEPENDENT_REPRODUCTION_SUBMISSION_ID_FIELDS` excludes `submission_time` -- two
    genuinely different submission bodies at the identical (project_id, original_result_bundle_ref,
    reproducer_actor_or_authority_id) collide at the identical id and must be refused, not
    silently overwritten."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    first_submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        submission_time=_SUBMISSION_TIME,
    )
    cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=first_submission
    )

    conflicting_submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        submission_time="2026-01-03T00:00:00.000001Z",
    )
    with pytest.raises(RecordConflictError):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=conflicting_submission
        )


# --- refuses binding to a parent that was never genuinely committed ----------------------------- #


def test_admit_independent_reproduction_submission_refuses_an_uncommitted_original_result_bundle(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    foreign_bundle = {
        **original_bundle,
        "result_bundle_id": "CBRB-" + ("9" * 64),
        "result_bundle_semantic_fingerprint": "sha256:" + ("9" * 64),
    }
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=foreign_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="genuinely exists in the Store"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_an_uncommitted_protocol_freeze(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    foreign_freeze = {
        **protocol_freeze,
        "protocol_freeze_id": "CBPF-" + ("9" * 64),
        "protocol_freeze_semantic_fingerprint": "sha256:" + ("9" * 64),
    }
    submission = _submission(
        protocol_freeze=foreign_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="genuinely exists in the Store"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


# --- signature is the structural proof of a distinct actor -------------------------------------- #


def test_admit_independent_reproduction_submission_refuses_a_tampered_signature_value(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    tampered_value = ("0" if submission["signature"]["value"][0] != "0" else "1") + submission[
        "signature"
    ]["value"][1:]
    submission = {**submission, "signature": {**submission["signature"], "value": tampered_value}}
    with pytest.raises(IndependentReproductionSubmissionValidationError, match="signature"):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_signature_from_a_different_key(
    tmp_path: Path,
) -> None:
    """The submission's own declared `signature.public_key` must be the key that actually
    produced `signature.value` -- signing with one key and then declaring a *different* public
    key (impersonation) must fail exactly like a garbled signature."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    real_private_key, _real_public_key_hex = cb.generate_test_ed25519_keypair()
    _other_private_key, other_public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=other_public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=real_private_key,
        public_key_hex=other_public_key_hex,
    )
    with pytest.raises(IndependentReproductionSubmissionValidationError, match="signature"):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_post_signature_field_tamper(
    tmp_path: Path,
) -> None:
    """A submitter cannot sign one body and then mutate a semantic field afterward -- the
    self-consistency check (`independent_reproduction_submission_semantic_fingerprint` no longer
    rederives) catches this before the signature check would even need to."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    tampered_metrics = {
        group_id: {**metrics, "FAILED": metrics["FAILED"] + 1}
        for group_id, metrics in submission["reproduced_metrics"].items()
    }
    submission = {**submission, "reproduced_metrics": tampered_metrics}
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="semantic_fingerprint"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


# --- P90-R2-F4-equivalent corpus fidelity, never bypassable through this surface either ---------- #


def test_admit_independent_reproduction_submission_refuses_a_partial_reproduced_corpus(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    partial_events = _minimal_raw_events(protocol_freeze)[:-1]
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        reproduced_raw_events=partial_events,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="expected exactly the frozen corpus"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


# --- independent recomputation, never a submitter's own claimed aggregate/verdict ---------------- #


def test_admit_independent_reproduction_submission_refuses_a_reproduced_metrics_that_does_not_rederive(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    raw_events = _minimal_raw_events(protocol_freeze)
    real_metrics = aggregate_metrics(raw_events, protocol_freeze)
    false_metrics = {
        group_id: {**metrics, "FAILED": 0, "COMPLETED_VERIFIED": metrics["FAILED"]}
        for group_id, metrics in real_metrics.items()
    }
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        reproduced_raw_events=raw_events,
        reproduced_metrics_override=false_metrics,
    )
    with pytest.raises(IndependentReproductionSubmissionValidationError, match="does not rederive"):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_declared_agreement_that_does_not_rederive(
    tmp_path: Path,
) -> None:
    """The original bundle's raw events are all `FAILED` and the honest reproduction below
    reproduces that identically (`MATCH`) -- a submitter declaring `DIVERGENT` instead, while its
    own `reproduced_metrics` genuinely matches the original, must be refused: `agreement` is
    always this route's own independent recomputation, never a submitter's own claimed verdict."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        agreement_override="DIVERGENT",
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError,
        match="does not match the recomputed agreement",
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_records_a_genuinely_divergent_reproduction(
    tmp_path: Path,
) -> None:
    """The positive control for `DIVERGENT`: an honest reproducer whose own raw events genuinely
    differ from the original bundle's own must still be admitted -- `agreement=DIVERGENT` is a
    real, acceptable outcome, never treated as a failure to admit."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    _admit_trust_anchor(store, protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    divergent_events = _minimal_raw_events(protocol_freeze, outcome="TIMED_OUT")
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        reproduced_raw_events=divergent_events,
    )
    committed = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=submission
    )
    assert committed["agreement"] == "DIVERGENT"
