"""P90-R4-F2 (PR #90 Round 4, ``ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_
REPRODUCER``): decisive proof for the independent reproducer trust-anchor admission/verification
surface.

Every trust anchor this suite admits is built from test-double key material
(``tests.fixtures.comparative_benchmark.generate_test_ed25519_keypair``) -- Claude Code never
generates, requests, receives, or inspects a *real* independent reproducer's private key here
(``ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_REPRODUCER``'s own explicit
prohibition). The point of every test below is that a submission can only ever be admitted
against a trust anchor SHUKOU pre-registered in this Store before the submission arrives, never
the submission's own self-declared key alone, and that a trust anchor once admitted can never be
silently mutated to a different key for the same identity."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from tests.fixtures import comparative_benchmark as cb
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.comparative_benchmark import engine as cb_engine, route as cb_route
from manosube_agent_civilization.comparative_benchmark.errors import (
    IndependentReproducerTrustAnchorValidationError,
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
        store, project_id=cb.PROJECT_ID, **cb.protocol_freeze_kwargs(generated_at=_GENERATED_AT)
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


def _freeze_ref(protocol_freeze: dict[str, Any]) -> dict[str, str]:
    return {
        "protocol_freeze_id": protocol_freeze["protocol_freeze_id"],
        "protocol_freeze_semantic_fingerprint": protocol_freeze[
            "protocol_freeze_semantic_fingerprint"
        ],
    }


def _trust_anchor_kwargs(
    *,
    protocol_freeze: dict[str, Any],
    public_key_hex: str,
    reproducer_actor_or_authority_id: str = "independent-reproducer-a",
    valid_from: str = _GENERATED_AT,
    valid_until: str | None = None,
    revocation_status: str = "ACTIVE",
) -> dict[str, Any]:
    return cb.independent_reproducer_trust_anchor_kwargs(
        reproducer_actor_or_authority_id=reproducer_actor_or_authority_id,
        ed25519_public_key=public_key_hex,
        key_id="test-key-1",
        authorized_protocol_or_corpus_ref=_freeze_ref(protocol_freeze),
        valid_from=valid_from,
        valid_until=valid_until,
        revocation_status=revocation_status,
        generated_at=_GENERATED_AT,
    )


def _submission(
    *,
    protocol_freeze: dict[str, Any],
    original_result_bundle: dict[str, Any],
    private_key: Any,
    public_key_hex: str,
    reproducer_actor_or_authority_id: str = "independent-reproducer-a",
    submission_time: str = _SUBMISSION_TIME,
) -> dict[str, Any]:
    """Build one fully self-consistent, genuinely-signed independent reproduction submission
    whose own reproduced_raw_events honestly rederive the original bundle's own MATCH agreement
    -- the one honest shape every test below either admits outright or deviates from in exactly
    the one dimension its own trust-anchor check isolates."""

    raw_events = _minimal_raw_events(protocol_freeze)
    reproduced_metrics = cb_engine.aggregate_metrics(raw_events, protocol_freeze)
    content_address = "sha256:" + hashlib.sha256(canonical_json_bytes(list(raw_events))).hexdigest()
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
        "protocol_freeze_ref": _freeze_ref(protocol_freeze),
        "reproduced_raw_events": list(raw_events),
        "reproduced_raw_events_content_address": content_address,
        "agent_runtime_model_configuration_identity": (
            cb.independent_reproducer_agent_runtime_model_configuration_identity()
        ),
        "execution_environment_manifest": cb.independent_reproducer_execution_environment_manifest(),
        "reproduced_metrics": reproduced_metrics,
        "agreement": "MATCH",
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


# --- build_independent_reproducer_trust_anchor: schema-shape and its own fail-closed checks ----- #


def test_build_independent_reproducer_trust_anchor_produces_a_schema_valid_record(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    record = cb_engine.build_independent_reproducer_trust_anchor(
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(protocol_freeze=protocol_freeze, public_key_hex=public_key_hex),
    )
    assert record["trust_anchor_id"].startswith("CBTA-")
    assert record["role"] == "INDEPENDENT_PHASE_21_REPRODUCER"
    assert record["admitted_by"] == "HUMAN_AUTHORITY"
    assert record["revocation_status"] == "ACTIVE"


def test_build_independent_reproducer_trust_anchor_refuses_a_malformed_ed25519_public_key(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    kwargs = _trust_anchor_kwargs(protocol_freeze=protocol_freeze, public_key_hex="not-a-hex-key")
    with pytest.raises(
        IndependentReproducerTrustAnchorValidationError, match="not a structurally valid Ed25519"
    ):
        cb_engine.build_independent_reproducer_trust_anchor(project_id=cb.PROJECT_ID, **kwargs)


def test_build_independent_reproducer_trust_anchor_refuses_valid_until_not_after_valid_from(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    kwargs = _trust_anchor_kwargs(
        protocol_freeze=protocol_freeze,
        public_key_hex=public_key_hex,
        valid_from=_GENERATED_AT,
        valid_until=_GENERATED_AT,
    )
    with pytest.raises(
        IndependentReproducerTrustAnchorValidationError, match="must be strictly after valid_from"
    ):
        cb_engine.build_independent_reproducer_trust_anchor(project_id=cb.PROJECT_ID, **kwargs)


def test_build_independent_reproducer_trust_anchor_never_accepts_a_role_or_admitted_by_override(
    tmp_path: Path,
) -> None:
    """P90-R4-F2's own `ORIGINAL_OPERATOR_IDENTITY_REFUSED`/`CLAUDE_CODE_SESSION_IDENTITY_
    REFUSED`-equivalent: `role` and `admitted_by` are not parameters of this production builder
    at all -- a caller attempting to pass either raises `TypeError` before any record is even
    assembled, never a record silently admitted under a different label."""

    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    kwargs = _trust_anchor_kwargs(protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    with pytest.raises(TypeError):
        cb_engine.build_independent_reproducer_trust_anchor(
            project_id=cb.PROJECT_ID,
            role="CLAUDE_CODE_SESSION",  # type: ignore[call-arg]
            **kwargs,
        )
    with pytest.raises(TypeError):
        cb_engine.build_independent_reproducer_trust_anchor(
            project_id=cb.PROJECT_ID,
            admitted_by="CLAUDE_CODE",  # type: ignore[call-arg]
            **kwargs,
        )


def test_engine_module_never_imports_ed25519_private_key() -> None:
    """This module builds a trust anchor's own `ed25519_public_key`, and only ever imports
    `Ed25519PublicKey` -- never `Ed25519PrivateKey` -- so this package's own production code has
    no import surface through which it could generate, hold, or sign with an independent
    reproducer's private key. A real AST import scan, not a raw substring search, since this
    module's own docstrings genuinely mention the word `Ed25519PrivateKey` while explaining
    exactly this guarantee."""

    import ast
    import inspect

    tree = ast.parse(inspect.getsource(cb_engine))
    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.ImportFrom, ast.Import)):
            imported_names.update(alias.name for alias in node.names)
    assert "Ed25519PrivateKey" not in imported_names
    assert "Ed25519PublicKey" in imported_names


# --- admit_independent_reproducer_trust_anchor: idempotency + key-substitution refusal ---------- #


def test_admit_independent_reproducer_trust_anchor_commits_and_resolves(tmp_path: Path) -> None:
    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    committed = cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(protocol_freeze=protocol_freeze, public_key_hex=public_key_hex),
    )
    resolved = cb_route.resolve_independent_reproducer_trust_anchor(
        store, project_id=cb.PROJECT_ID, trust_anchor_id=committed["trust_anchor_id"]
    )
    assert resolved == committed


def test_admit_independent_reproducer_trust_anchor_is_idempotent_for_an_identical_body(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    kwargs = _trust_anchor_kwargs(protocol_freeze=protocol_freeze, public_key_hex=public_key_hex)
    first = cb_route.admit_independent_reproducer_trust_anchor(
        store, project_id=cb.PROJECT_ID, **kwargs
    )
    second = cb_route.admit_independent_reproducer_trust_anchor(
        store, project_id=cb.PROJECT_ID, **kwargs
    )
    assert first == second


def test_admit_independent_reproducer_trust_anchor_refuses_key_substitution_for_the_same_identity(
    tmp_path: Path,
) -> None:
    """`ACTOR_KEY_SUBSTITUTION_REFUSED=true`/`POST_ADMISSION_KEY_MUTATION_REFUSED=true`:
    `identity.TRUST_ANCHOR_ID_FIELDS` excludes the key itself, so re-admitting a trust anchor for
    the identical (project, actor, role, protocol) with a *different* key collides at the
    identical `trust_anchor_id` and must be refused as a same-id-different-body conflict, never
    silently overwritten."""

    store = _store(tmp_path)
    protocol_freeze, _original_bundle = _committed_freeze_and_bundle(store)
    _first_private_key, first_public_key_hex = cb.generate_test_ed25519_keypair()
    _second_private_key, second_public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze, public_key_hex=first_public_key_hex
        ),
    )
    with pytest.raises(RecordConflictError):
        cb_route.admit_independent_reproducer_trust_anchor(
            store,
            project_id=cb.PROJECT_ID,
            **_trust_anchor_kwargs(
                protocol_freeze=protocol_freeze, public_key_hex=second_public_key_hex
            ),
        )


# --- admit_independent_reproduction_submission: the trust anchor is the only trusted key -------- #


def test_admit_independent_reproduction_submission_refuses_when_no_trust_anchor_is_registered(
    tmp_path: Path,
) -> None:
    """`SELF_DECLARED_UNREGISTERED_KEY_REFUSED=true`: a genuinely, correctly self-consistent and
    self-signed submission is still refused when no trust anchor was ever pre-registered for its
    declared (actor, protocol) -- a submission's own self-declared key is never, by itself,
    sufficient grounds for admission."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError,
        match="no comparative_benchmark_independent_reproducer_trust_anchor is registered",
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_key_not_equal_to_the_registered_key(
    tmp_path: Path,
) -> None:
    """`WRONG_REGISTERED_KEY_REFUSED=true`: a submission genuinely self-signed and self-
    consistent, whose declared `signature.public_key` is a real, validly-formed Ed25519 key, is
    still refused when that key is not the one key SHUKOU pre-registered for this (actor,
    protocol) pair."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    _registered_private_key, registered_public_key_hex = cb.generate_test_ed25519_keypair()
    other_private_key, other_public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze, public_key_hex=registered_public_key_hex
        ),
    )
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=other_private_key,
        public_key_hex=other_public_key_hex,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError,
        match="diverges from the resolved independent reproducer trust anchor",
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_revoked_trust_anchor(
    tmp_path: Path,
) -> None:
    """`REVOKED_OR_EXPIRED_KEY_REFUSED=true` (revocation case): a trust anchor's own
    `revocation_status="REVOKED"` refuses every submission against it, however genuine that
    submission's own signature."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze,
            public_key_hex=public_key_hex,
            revocation_status="REVOKED",
        ),
    )
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    with pytest.raises(IndependentReproductionSubmissionValidationError, match="not ACTIVE"):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_submission_before_valid_from(
    tmp_path: Path,
) -> None:
    """`REVOKED_OR_EXPIRED_KEY_REFUSED=true` (not-yet-in-force case): a submission whose own
    `submission_time` is before the trust anchor's own `valid_from` is refused -- the trust
    anchor was not yet in force at the time this submission claims to have been made."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze,
            public_key_hex=public_key_hex,
            valid_from="2026-06-01T00:00:00.000001Z",
        ),
    )
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        submission_time=_SUBMISSION_TIME,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="before the resolved"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_refuses_a_submission_at_or_after_valid_until(
    tmp_path: Path,
) -> None:
    """`REVOKED_OR_EXPIRED_KEY_REFUSED=true` (expired case): a submission whose own
    `submission_time` is at or after the trust anchor's own `valid_until` is refused as made
    under a revoked or expired trust anchor."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze,
            public_key_hex=public_key_hex,
            valid_until="2026-01-01T12:00:00.000001Z",
        ),
    )
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        submission_time=_SUBMISSION_TIME,
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="revoked or expired"
    ):
        cb_route.admit_independent_reproduction_submission(
            store, project_id=cb.PROJECT_ID, submission=submission
        )


def test_admit_independent_reproduction_submission_succeeds_within_the_trust_anchor_validity_window(
    tmp_path: Path,
) -> None:
    """Positive control: a genuinely signed submission against a registered, ACTIVE trust
    anchor, made inside its own `[valid_from, valid_until)` window, is admitted."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    cb_route.admit_independent_reproducer_trust_anchor(
        store,
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze,
            public_key_hex=public_key_hex,
            valid_from="2025-01-01T00:00:00.000001Z",
            valid_until="2027-01-01T00:00:00.000001Z",
        ),
    )
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        submission_time=_SUBMISSION_TIME,
    )
    committed = cb_route.admit_independent_reproduction_submission(
        store, project_id=cb.PROJECT_ID, submission=submission
    )
    assert committed["agreement"] == "MATCH"


# --- engine.verify_independent_reproduction_submission: cross-actor/cross-protocol replay -------- #


def test_verify_independent_reproduction_submission_refuses_a_trust_anchor_for_a_different_actor(
    tmp_path: Path,
) -> None:
    """A hand-assembled `trust_anchor` whose own `reproducer_actor_or_authority_id` diverges
    from the submission's declared one is refused -- exercised directly against
    `engine.verify_independent_reproduction_submission`, since `route.py`'s own trust-anchor id
    derivation makes this actor mismatch unreachable through the public route alone."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
        reproducer_actor_or_authority_id="independent-reproducer-a",
    )
    foreign_trust_anchor = cb_engine.build_independent_reproducer_trust_anchor(
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(
            protocol_freeze=protocol_freeze,
            public_key_hex=public_key_hex,
            reproducer_actor_or_authority_id="independent-reproducer-b",
        ),
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="diverges from this submission"
    ):
        cb_engine.verify_independent_reproduction_submission(
            submission,
            protocol_freeze=protocol_freeze,
            original_result_bundle=original_bundle,
            trust_anchor=foreign_trust_anchor,
        )


def test_verify_independent_reproduction_submission_refuses_cross_protocol_replay(
    tmp_path: Path,
) -> None:
    """`CROSS_PROTOCOL_OR_CORPUS_REPLAY_REFUSED=true`: a hand-assembled `trust_anchor` admitted
    for a *different* frozen protocol is refused, exercised directly against
    `engine.verify_independent_reproduction_submission` -- `route.py`'s own trust-anchor id
    derivation makes this protocol mismatch unreachable through the public route alone, since a
    trust anchor's own id already binds it to one exact `authorized_protocol_or_corpus_ref`."""

    store = _store(tmp_path)
    protocol_freeze, original_bundle = _committed_freeze_and_bundle(store)
    private_key, public_key_hex = cb.generate_test_ed25519_keypair()
    submission = _submission(
        protocol_freeze=protocol_freeze,
        original_result_bundle=original_bundle,
        private_key=private_key,
        public_key_hex=public_key_hex,
    )
    other_freeze_kwargs = cb.protocol_freeze_kwargs(generated_at="2026-02-01T00:00:00.000001Z")
    other_freeze_kwargs["resource_budget_manifest"] = {
        **other_freeze_kwargs["resource_budget_manifest"],
        "total_time_budget_seconds": 601.0,
    }
    other_freeze = cb_route.commit_protocol_freeze(
        store, project_id=cb.PROJECT_ID, **other_freeze_kwargs
    )
    foreign_trust_anchor = cb_engine.build_independent_reproducer_trust_anchor(
        project_id=cb.PROJECT_ID,
        **_trust_anchor_kwargs(protocol_freeze=other_freeze, public_key_hex=public_key_hex),
    )
    with pytest.raises(
        IndependentReproductionSubmissionValidationError, match="different protocol_freeze_ref"
    ):
        cb_engine.verify_independent_reproduction_submission(
            submission,
            protocol_freeze=protocol_freeze,
            original_result_bundle=original_bundle,
            trust_anchor=foreign_trust_anchor,
        )
