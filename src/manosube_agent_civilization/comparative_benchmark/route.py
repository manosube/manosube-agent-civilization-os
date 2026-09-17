"""Canonical commit/resolve entrypoints for the Comparative Benchmark package (Issue #89,
`ADOPT_PHASE_21_COMPARATIVE_BENCHMARK`).

**This is not a Change Executor, not an Evidence producer, and not a Canonical State owner.**
Every record this module commits goes through the Store's own orthogonal, append-only
coordination ledger -- `FileStateStore.commit_coordination_record_at_tip`, the identical
mechanism `long_running_proof_artifact/route.py` and `work_time_transparency/route.py` already
establish -- never `commit_state_transition`. A commit here therefore never reads or advances
`state_revision`, and stages no Project-State transition: this package structurally cannot
mutate or authorize canonical Project State, Authority, Evidence, Reflow, or Completion, since
no code path here ever reaches `commit_state_transition`/`store.commit` at all (Issue #89
section 7: "the benchmark must never become a new owner of Canonical State, Authority, Evidence
sufficiency, Reflow closure, or Project Completion"). MANOSUBE's own timing/WTT/artifact records
likewise never become Completion Evidence through this package -- there is deliberately no
`evidence_handoff.py` here.

Each of the five record kinds (protocol freeze, result bundle, reproduction receipt,
independent reproducer trust anchor, independent reproduction submission) is committed as the
single, self-chained entry of its own coordination chain
(`chain_id == <record>_id`, `expected_predecessor=None`): a same-id-same-body re-commit is an
idempotent replay; a same-id-different-body re-commit collides and is refused
(`RecordConflictError`) -- exactly the discipline that makes `POST_HOC_PROTOCOL_MUTATION_
ALLOWED=false` and `RAW_RESULT_DELETION_ALLOWED=false` structural facts, not merely stated
policy: a protocol freeze or a result bundle, once committed, is immutable at that identity.

`commit_result_bundle` and `commit_reproduction_receipt` never trust a caller-supplied parent
record body on its own (P90-R1-F6): each first resolves its own declared parent
(`protocol_freeze`/`original_result_bundle`) from this Store's own coordination ledger by the
id the caller supplied, refuses fail-closed if that parent was never genuinely committed there,
refuses fail-closed if the caller's own copy diverges byte-for-byte from the ledger's
authoritative body, and then builds the child exclusively from the *resolved* body -- a caller
can never fabricate an unlisted or tampered parent and have a child record accepted merely
because it happens to be shaped correctly.

Every `resolve_*` function is a thin, direct wrapper over `FileStateStore.
resolve_coordination_record`, which always re-derives the record's authoritative body from the
coordination ledger itself, never trusting a materialized cache file on its own."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from .engine import (
    build_independent_reproducer_trust_anchor,
    build_protocol_freeze,
    build_reproduction_receipt,
    build_result_bundle,
    verify_independent_reproduction_submission,
)
from .errors import (
    IndependentReproductionSubmissionValidationError,
    ReproductionReceiptValidationError,
    ResultBundleValidationError,
)
from .identity import independent_reproducer_trust_anchor_id

PROTOCOL_FREEZE_RECORD_KIND = "comparative_benchmark_protocol_freeze"
RESULT_BUNDLE_RECORD_KIND = "comparative_benchmark_result_bundle"
REPRODUCTION_RECEIPT_RECORD_KIND = "comparative_benchmark_reproduction_receipt"
INDEPENDENT_REPRODUCTION_SUBMISSION_RECORD_KIND = (
    "comparative_benchmark_independent_reproduction_submission"
)
INDEPENDENT_REPRODUCER_TRUST_ANCHOR_RECORD_KIND = (
    "comparative_benchmark_independent_reproducer_trust_anchor"
)


def commit_protocol_freeze(store: Any, *, project_id: str, **build_kwargs: Any) -> dict[str, Any]:
    """Build and durably commit one protocol freeze -- must be called, and its return value's
    `protocol_freeze_id` bound into every later result bundle, before any benchmark result is
    executed or observed (`PROTOCOL_FROZEN_BEFORE_RESULTS=true`)."""

    record = build_protocol_freeze(project_id=project_id, **build_kwargs)
    freeze_id = record["protocol_freeze_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            freeze_id,
            PROTOCOL_FREEZE_RECORD_KIND,
            freeze_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_protocol_freeze(
    store: Any, *, project_id: str, protocol_freeze_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, PROTOCOL_FREEZE_RECORD_KIND, protocol_freeze_id
    )
    return cast("dict[str, Any] | None", result)


def commit_result_bundle(store: Any, *, project_id: str, **build_kwargs: Any) -> dict[str, Any]:
    """Build and durably commit one result bundle against an already-committed protocol
    freeze. *build_kwargs* must include `protocol_freeze` -- the caller's own belief about
    which freeze this bundle ran against. This route itself resolves the authoritative
    `protocol_freeze_id` from the Store's own coordination ledger and refuses fail-closed
    (`ResultBundleValidationError`) both when no such freeze was ever committed there and when
    the caller's own copy diverges from the ledger's body (P90-R1-F6) -- the child record is
    always built from the *resolved* body, never the caller-supplied one."""

    caller_protocol_freeze = build_kwargs.get("protocol_freeze")
    if not isinstance(caller_protocol_freeze, Mapping):
        raise ResultBundleValidationError("commit_result_bundle requires a protocol_freeze mapping")
    freeze_id = caller_protocol_freeze.get("protocol_freeze_id")
    if not isinstance(freeze_id, str) or not freeze_id:
        raise ResultBundleValidationError(
            "commit_result_bundle requires protocol_freeze to carry a non-empty string "
            "protocol_freeze_id"
        )
    resolved_freeze = resolve_protocol_freeze(
        store, project_id=project_id, protocol_freeze_id=freeze_id
    )
    if resolved_freeze is None:
        raise ResultBundleValidationError(
            f"no comparative_benchmark_protocol_freeze is committed at protocol_freeze_id "
            f"{freeze_id!r} in this project's own coordination ledger -- a result bundle can "
            "only bind to a protocol freeze that genuinely exists in the Store, never a "
            "caller-supplied body accepted on trust"
        )
    if resolved_freeze != dict(caller_protocol_freeze):
        raise ResultBundleValidationError(
            "the protocol_freeze passed to commit_result_bundle diverges from the Store's own "
            f"committed record at protocol_freeze_id {freeze_id!r} -- a result bundle must "
            "bind to the ledger's own authoritative freeze body, never a caller-supplied "
            "look-alike"
        )

    record = build_result_bundle(
        project_id=project_id, **{**build_kwargs, "protocol_freeze": resolved_freeze}
    )
    bundle_id = record["result_bundle_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            bundle_id,
            RESULT_BUNDLE_RECORD_KIND,
            bundle_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_result_bundle(
    store: Any, *, project_id: str, result_bundle_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, RESULT_BUNDLE_RECORD_KIND, result_bundle_id
    )
    return cast("dict[str, Any] | None", result)


def commit_reproduction_receipt(
    store: Any, *, project_id: str, **build_kwargs: Any
) -> dict[str, Any]:
    """Build and durably commit one independent reproduction receipt against an
    already-committed protocol freeze and original result bundle. *build_kwargs* must include
    `protocol_freeze` and `original_result_bundle` -- the caller's own belief about which
    records this reproduction ran against. This route itself resolves both parents'
    authoritative bodies from the Store's own coordination ledger and refuses fail-closed
    (`ReproductionReceiptValidationError`) whenever either parent was never genuinely committed
    there or the caller's own copy diverges from the ledger's body (P90-R1-F6); the child
    record is always built from the *resolved* bodies. `engine.build_reproduction_receipt`
    itself still recomputes `agreement` and enforces the separate-process boundary
    (P90-R1-F3) -- this route never overrides either."""

    caller_protocol_freeze = build_kwargs.get("protocol_freeze")
    if not isinstance(caller_protocol_freeze, Mapping):
        raise ReproductionReceiptValidationError(
            "commit_reproduction_receipt requires a protocol_freeze mapping"
        )
    freeze_id = caller_protocol_freeze.get("protocol_freeze_id")
    if not isinstance(freeze_id, str) or not freeze_id:
        raise ReproductionReceiptValidationError(
            "commit_reproduction_receipt requires protocol_freeze to carry a non-empty string "
            "protocol_freeze_id"
        )
    resolved_freeze = resolve_protocol_freeze(
        store, project_id=project_id, protocol_freeze_id=freeze_id
    )
    if resolved_freeze is None:
        raise ReproductionReceiptValidationError(
            f"no comparative_benchmark_protocol_freeze is committed at protocol_freeze_id "
            f"{freeze_id!r} in this project's own coordination ledger -- a reproduction "
            "receipt can only bind to a protocol freeze that genuinely exists in the Store, "
            "never a caller-supplied body accepted on trust"
        )
    if resolved_freeze != dict(caller_protocol_freeze):
        raise ReproductionReceiptValidationError(
            "the protocol_freeze passed to commit_reproduction_receipt diverges from the "
            f"Store's own committed record at protocol_freeze_id {freeze_id!r} -- a "
            "reproduction receipt must bind to the ledger's own authoritative freeze body, "
            "never a caller-supplied look-alike"
        )

    caller_original_result_bundle = build_kwargs.get("original_result_bundle")
    if not isinstance(caller_original_result_bundle, Mapping):
        raise ReproductionReceiptValidationError(
            "commit_reproduction_receipt requires an original_result_bundle mapping"
        )
    bundle_id = caller_original_result_bundle.get("result_bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise ReproductionReceiptValidationError(
            "commit_reproduction_receipt requires original_result_bundle to carry a non-empty "
            "string result_bundle_id"
        )
    resolved_bundle = resolve_result_bundle(
        store, project_id=project_id, result_bundle_id=bundle_id
    )
    if resolved_bundle is None:
        raise ReproductionReceiptValidationError(
            f"no comparative_benchmark_result_bundle is committed at result_bundle_id "
            f"{bundle_id!r} in this project's own coordination ledger -- a reproduction "
            "receipt can only bind to an original result bundle that genuinely exists in the "
            "Store, never a caller-supplied body accepted on trust"
        )
    if resolved_bundle != dict(caller_original_result_bundle):
        raise ReproductionReceiptValidationError(
            "the original_result_bundle passed to commit_reproduction_receipt diverges from "
            f"the Store's own committed record at result_bundle_id {bundle_id!r} -- a "
            "reproduction receipt must bind to the ledger's own authoritative bundle body, "
            "never a caller-supplied look-alike"
        )

    record = build_reproduction_receipt(
        project_id=project_id,
        **{
            **build_kwargs,
            "protocol_freeze": resolved_freeze,
            "original_result_bundle": resolved_bundle,
        },
    )
    receipt_id = record["reproduction_receipt_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            receipt_id,
            REPRODUCTION_RECEIPT_RECORD_KIND,
            receipt_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_reproduction_receipt(
    store: Any, *, project_id: str, reproduction_receipt_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, REPRODUCTION_RECEIPT_RECORD_KIND, reproduction_receipt_id
    )
    return cast("dict[str, Any] | None", result)


def admit_independent_reproducer_trust_anchor(
    store: Any, *, project_id: str, **build_kwargs: Any
) -> dict[str, Any]:
    """Build and durably commit one independent reproducer trust anchor (P90-R4-F2) --
    SHUKOU's own pre-registration of a distinct reproducer actor/authority's Ed25519 public
    key, before that actor ever submits a reproduction. Committed through the identical
    `commit_coordination_record_at_tip` mechanism every other record kind in this package uses;
    `identity.TRUST_ANCHOR_ID_FIELDS` excludes the key itself, so a same-identity re-admission
    that declares a *different* key for the same (project, actor, protocol) is a same-id-
    different-body conflict (`RecordConflictError`), never a silent overwrite
    (`POST_ADMISSION_KEY_MUTATION_REFUSED=true`, `ACTOR_KEY_SUBSTITUTION_REFUSED=true`)."""

    record = build_independent_reproducer_trust_anchor(project_id=project_id, **build_kwargs)
    trust_anchor_id = record["trust_anchor_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            trust_anchor_id,
            INDEPENDENT_REPRODUCER_TRUST_ANCHOR_RECORD_KIND,
            trust_anchor_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_independent_reproducer_trust_anchor(
    store: Any, *, project_id: str, trust_anchor_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id, INDEPENDENT_REPRODUCER_TRUST_ANCHOR_RECORD_KIND, trust_anchor_id
    )
    return cast("dict[str, Any] | None", result)


def admit_independent_reproduction_submission(
    store: Any, *, project_id: str, submission: Mapping[str, Any]
) -> dict[str, Any]:
    """Admit one externally-supplied, already-signed independent reproduction submission
    (P90-R3-F2, `ADOPT_P90_R3_BOUNDED_REAL_AGENT_AND_INDEPENDENT_REPRODUCER_LANE`) against this
    project's own already-committed protocol freeze and original result bundle. This route
    never builds, signs, or in any way authors *submission* itself
    (`CLAUDE_CODE_MAY_SELF_ISSUE_INDEPENDENT_RECEIPT=false`,
    `SEPARATE_PROCESS_ALONE_SUFFICIENT=false`) -- it only resolves *submission*'s own declared
    parents from the Store's own coordination ledger exactly like `commit_reproduction_receipt`
    already does, refuses fail-closed
    (`IndependentReproductionSubmissionValidationError`) if either parent was never genuinely
    committed there, hands the unmodified, externally-supplied record to
    `engine.verify_independent_reproduction_submission` for a total check (schema,
    self-consistent identity, exact ref binding to the *resolved* parents, exact corpus
    fidelity, independently rederived content-address/metrics/agreement, and a genuine Ed25519
    signature over the submission's own payload against its own declared public key), and
    commits *submission* verbatim -- byte-for-byte, no field added, removed, or recomputed by
    this route -- once every check passes."""

    freeze_ref = submission.get("protocol_freeze_ref")
    if not isinstance(freeze_ref, Mapping):
        raise IndependentReproductionSubmissionValidationError(
            "admit_independent_reproduction_submission requires a protocol_freeze_ref mapping"
        )
    freeze_id = freeze_ref.get("protocol_freeze_id")
    if not isinstance(freeze_id, str) or not freeze_id:
        raise IndependentReproductionSubmissionValidationError(
            "admit_independent_reproduction_submission requires protocol_freeze_ref to carry a "
            "non-empty string protocol_freeze_id"
        )
    resolved_freeze = resolve_protocol_freeze(
        store, project_id=project_id, protocol_freeze_id=freeze_id
    )
    if resolved_freeze is None:
        raise IndependentReproductionSubmissionValidationError(
            f"no comparative_benchmark_protocol_freeze is committed at protocol_freeze_id "
            f"{freeze_id!r} in this project's own coordination ledger -- an independent "
            "reproduction submission can only bind to a protocol freeze that genuinely exists "
            "in the Store, never a caller-supplied body accepted on trust"
        )

    bundle_ref = submission.get("original_result_bundle_ref")
    if not isinstance(bundle_ref, Mapping):
        raise IndependentReproductionSubmissionValidationError(
            "admit_independent_reproduction_submission requires an original_result_bundle_ref "
            "mapping"
        )
    bundle_id = bundle_ref.get("result_bundle_id")
    if not isinstance(bundle_id, str) or not bundle_id:
        raise IndependentReproductionSubmissionValidationError(
            "admit_independent_reproduction_submission requires original_result_bundle_ref to "
            "carry a non-empty string result_bundle_id"
        )
    resolved_bundle = resolve_result_bundle(
        store, project_id=project_id, result_bundle_id=bundle_id
    )
    if resolved_bundle is None:
        raise IndependentReproductionSubmissionValidationError(
            f"no comparative_benchmark_result_bundle is committed at result_bundle_id "
            f"{bundle_id!r} in this project's own coordination ledger -- an independent "
            "reproduction submission can only bind to an original result bundle that genuinely "
            "exists in the Store, never a caller-supplied body accepted on trust"
        )

    record = dict(submission)
    reproducer_actor_or_authority_id = record.get("reproducer_actor_or_authority_id")
    if (
        not isinstance(reproducer_actor_or_authority_id, str)
        or not reproducer_actor_or_authority_id
    ):
        raise IndependentReproductionSubmissionValidationError(
            "admit_independent_reproduction_submission requires a non-empty string "
            "reproducer_actor_or_authority_id"
        )
    expected_trust_anchor_id = independent_reproducer_trust_anchor_id(
        {
            "project_id": project_id,
            "reproducer_actor_or_authority_id": reproducer_actor_or_authority_id,
            "role": "INDEPENDENT_PHASE_21_REPRODUCER",
            "authorized_protocol_or_corpus_ref": freeze_ref,
        }
    )
    resolved_trust_anchor = resolve_independent_reproducer_trust_anchor(
        store, project_id=project_id, trust_anchor_id=expected_trust_anchor_id
    )
    if resolved_trust_anchor is None:
        raise IndependentReproductionSubmissionValidationError(
            "no comparative_benchmark_independent_reproducer_trust_anchor is registered for "
            f"reproducer_actor_or_authority_id {reproducer_actor_or_authority_id!r} against "
            f"protocol_freeze_ref {freeze_ref!r} -- an independent reproduction submission can "
            "only be admitted against a trust anchor SHUKOU pre-registered before this "
            "submission, never the submission's own self-declared key alone "
            "(SELF_DECLARED_UNREGISTERED_KEY_REFUSED=true)"
        )

    verify_independent_reproduction_submission(
        record,
        protocol_freeze=resolved_freeze,
        original_result_bundle=resolved_bundle,
        trust_anchor=resolved_trust_anchor,
    )
    submission_id = record["independent_reproduction_submission_id"]
    return cast(
        "dict[str, Any]",
        store.commit_coordination_record_at_tip(
            project_id,
            submission_id,
            INDEPENDENT_REPRODUCTION_SUBMISSION_RECORD_KIND,
            submission_id,
            record,
            expected_predecessor=None,
        ),
    )


def resolve_independent_reproduction_submission(
    store: Any, *, project_id: str, independent_reproduction_submission_id: str
) -> dict[str, Any] | None:
    result = store.resolve_coordination_record(
        project_id,
        INDEPENDENT_REPRODUCTION_SUBMISSION_RECORD_KIND,
        independent_reproduction_submission_id,
    )
    return cast("dict[str, Any] | None", result)


__all__ = [
    "INDEPENDENT_REPRODUCER_TRUST_ANCHOR_RECORD_KIND",
    "INDEPENDENT_REPRODUCTION_SUBMISSION_RECORD_KIND",
    "PROTOCOL_FREEZE_RECORD_KIND",
    "REPRODUCTION_RECEIPT_RECORD_KIND",
    "RESULT_BUNDLE_RECORD_KIND",
    "admit_independent_reproducer_trust_anchor",
    "admit_independent_reproduction_submission",
    "commit_protocol_freeze",
    "commit_reproduction_receipt",
    "commit_result_bundle",
    "resolve_independent_reproducer_trust_anchor",
    "resolve_independent_reproduction_submission",
    "resolve_protocol_freeze",
    "resolve_reproduction_receipt",
    "resolve_result_bundle",
]
