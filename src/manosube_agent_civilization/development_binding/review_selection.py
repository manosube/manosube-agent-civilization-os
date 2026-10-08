"""The Bounded Review Grant: whether one specific Codex technical-review request is admitted
(Decision 0004, Issue #109).

Codex is never an implementation executor and never eligible for ``EXECUTOR_PROVIDERS``
(`development_binding.policy`). It holds one capability, ``BOUNDED_TECHNICAL_REVIEWER``, and
one action, ``BOUNDED_TECHNICAL_REVIEW`` -- and role membership in that capability is
eligibility, never authority, for exactly the same reason Decision 0003 already states for
``GITHUB_COPILOT``:

```text
ELIGIBLE  = CODEX names the bounded technical reviewer capability in the ratified policy
ADMITTED  = ELIGIBLE, and this exact request is bound by this module to its exact scope,
            freshness, environment and provenance
```

This module is :mod:`.executor_selection`'s own sibling, built to the identical discipline: a
structured record, checked offline, with no network call, no credential, and no default-admit
path. It answers one question only -- is *this* Bounded Review Grant internally consistent and
still live -- never whether a concurrency slot or a daily reservation is actually available
right now (:mod:`.review_control` owns that, over a durable ledger this module never reads or
writes) and never whether the external review itself may launch (:mod:`.review_adapter` owns
that one side effect, gated by both this module's admission and the separate activation/
spending gate `review_control.evaluate_activation_gate` requires).

Following this repository's own admission grammar (`adoption_record`, `executor_selection`):
an **unreadable** record -- the wrong Python shape, an unknown key, a missing required key, a
non-string field where one is required -- raises :class:`~.errors.ReviewSelectionError`, since
there is no admission question to answer. A **readable-but-insufficient** record -- an expired
or revoked window, a scope mismatch, an unsupported CLI/model fingerprint, a read-back receipt
that disagrees with the record's own declared fields -- is never an exception; it is the
decision ``REVIEW_SELECTION_REFUSED``, with the specific reason codes this module can name.

Bindings this module checks, each answering one of the handoff's own required counterexamples
(comment 6017544351, §3/§4/§5):

- ``decision_authority``/``decision_status`` must be ``SHUKOU``/``RATIFIED`` -- a caller's own
  ``decision_status=RATIFIED`` does not, by itself, authenticate anything; it is one field this
  module checks alongside every other, and a grant whose ``api_read_back_receipt`` does not
  independently agree with it is refused the same as any other declared-vs-received mismatch.
- ``authorized_repository``/``authorized_pull_request``/``authorized_base_sha``/
  ``authorized_head_sha`` are receipt-bound identically to `executor_selection`'s own four scope
  fields, then compared against ``current_repository``/``current_pull_request``/
  ``current_base_sha``/``current_head_sha`` -- a scope mismatch, including a changed base or a
  head that has moved since the grant was issued, is refused (``HEAD_SHA_STALE``: "head/base
  変更で旧PASSを継承しない", the handoff's own §7).
- ``not_before``/``not_after`` bound a real validity window, checked against an explicit *now*
  the caller supplies (never this module's own clock read -- the identical discipline
  `work_time_transparency`'s injected-clock convention already uses) -- a window not yet open,
  or already closed, is refused, never silently treated as still current.
- ``revoked`` is checked as a live kill-switch field on the grant itself -- ``true`` refuses
  unconditionally, whatever else about the record is otherwise admissible.
- ``environment_fingerprint`` must declare, exactly, the one CLI/model/auth/provider/reasoning
  configuration this module pins as :data:`SUPPORTED_ENVIRONMENT_FINGERPRINT` -- a different or
  partially-matching configuration is refused rather than silently accepted as "close enough",
  per the handoff's own §5 instruction to "refuse unsupported/different configurations rather
  than silently selecting a different provider or model".
- ``implementation_provider`` must be one of :data:`.policy.EXECUTOR_PROVIDERS`;
  ``inspector_provider`` must be :data:`.policy.BOUNDED_TECHNICAL_REVIEWER` exactly -- Codex
  reviewing on behalf of a different, unratified "inspector" name is refused.
- ``permitted_paths`` must be a non-empty list of safe, repository-relative paths (the identical
  grammar `executor_selection.is_safe_repository_relative_path` already enforces for an
  implementation executor's own grant, reused here rather than re-implemented, so the two can
  never silently diverge); ``permitted_checks`` must be a non-empty subset of
  :data:`ALLOWED_CHECK_CATEGORIES`.
- ``input_digest`` must be a 64-character lowercase hex SHA-256 digest -- the bound input
  bundle's own identity, never merely present.
- ``work_unit_id`` must equal ``invoked_work_unit_id`` (a grant issued for one work unit is
  refused when replayed to authorize a different one, mirroring `executor_selection`'s own
  ``CROSS_WORK_UNIT_REPLAY``).

**What "verified" does and does not mean here.** Every binding above proves *internal
consistency*: the record's own declared fields agree with the caller's own claimed receipt, and
with the caller-supplied, trusted-clock *now*. Matching the comment-URL pattern is a shape
check, not proof that the comment exists or reads as claimed -- this module performs no network
call and holds no credential, exactly as `executor_selection` and `adoption_record` state for
themselves. A fixture or caller must never describe a record this module admits as
independently "verified" against live GitHub state or live provider account state; it has only
been shown not to contradict itself.

**F1 correction (PR #112 comment 6019024445).** :func:`evaluate_review_selection` above stays
exactly what it always was -- a pure, offline, internal-consistency check, never itself
authority for anything. That pure check alone was never enough to gate :mod:`.review_adapter`'s
one external-effect call: nothing stood between an internally-consistent-looking record and a
real subprocess launch. :func:`authenticate_bounded_review_grant` is the separate, additional
layer this correction adds, answering a different question -- did a real Human Authority
actually grant *this exact* CODEX review scope -- by reusing the identical, already-established
owners :mod:`manosube_agent_civilization.independent_verification.route` already composes for
the identical question about a ``VerifierSelection``: the existing Boot owner's own
``boot_project`` (never re-derived here), the existing Authority owner's own dedicated
``evaluate_verifier_selection`` (never a second Authority owner), and the Store's own read-only
``resolve_record`` for every ``verifier_selection_grant``/``human_grant_declaration`` reference
(never grant *content* accepted from a caller). No new Kernel record type is introduced: CODEX's
exact review scope is encoded entirely through the existing ``verifier_identity``/
``permitted_boundary`` fields that contract already carries for any verifier, CODEX included.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import re
from typing import Any

from .errors import ReviewSelectionError
from .executor_selection import is_safe_repository_relative_path
from .policy import BOUNDED_TECHNICAL_REVIEWER, EXECUTOR_PROVIDERS

SCHEMA_VERSION = "0.1"

REVIEW_SELECTION_ADMITTED = "REVIEW_SELECTION_ADMITTED"
REVIEW_SELECTION_REFUSED = "REVIEW_SELECTION_REFUSED"
DECISIONS: frozenset[str] = frozenset({REVIEW_SELECTION_ADMITTED, REVIEW_SELECTION_REFUSED})

#: Matches `development_binding.policy.HUMAN_AUTHORITY`/`.executor_selection.HUMAN_AUTHORITY`
#: by value, not by import -- this module stays a self-contained extension of the same grant
#: grammar rather than a second owner that happens to agree today.
HUMAN_AUTHORITY = "SHUKOU"

#: This repository, and no other -- matches `.executor_selection.THIS_REPOSITORY` by value.
THIS_REPOSITORY = "manosube/manosube-agent-civilization-os"

#: The one supported local execution environment this delivery was adopted against (Issue
#: #109 handoff, comment 6017544351, "Observed environment and spending disposition" and §5).
#: A grant naming anything else is refused (``ENVIRONMENT_FINGERPRINT_UNSUPPORTED``) rather
#: than silently accepted -- "independently validate the exact CLI model identifier/config
#: supported by that version before using it, and refuse unsupported/different configurations
#: rather than silently selecting a different provider or model."
SUPPORTED_ENVIRONMENT_FINGERPRINT: dict[str, str] = {
    "cli_version": "0.160.1",
    "model": "GPT-6.1-Sol",
    "auth_method": "CHATGPT_LOGIN",
    "provider": "OPENAI",
    "reasoning_effort": "low",
}

#: The closed set of inspection categories a Bounded Review Grant may ever name -- a reviewer
#: that could name an arbitrary category could just as easily name one this Binding never
#: ratified (e.g. an implementation instruction in disguise).
ALLOWED_CHECK_CATEGORIES: frozenset[str] = frozenset(
    {
        "CORRECTNESS",
        "SECURITY",
        "PERFORMANCE",
        "MAINTAINABILITY",
        "TEST_COVERAGE",
    }
)

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "work_unit_id",
    "invoked_work_unit_id",
    "difference_id",
    "governing_issue",
    "adoption_id",
    "comment_url",
    "decision_authority",
    "decision_status",
    "api_read_back_receipt",
    "authorized_repository",
    "authorized_pull_request",
    "authorized_base_sha",
    "authorized_head_sha",
    "current_repository",
    "current_pull_request",
    "current_base_sha",
    "current_head_sha",
    "requirement_id",
    "implementation_provider",
    "implementation_session_ref",
    "inspector_provider",
    "inspector_session_ref",
    "permitted_paths",
    "permitted_checks",
    "environment_fingerprint",
    "input_digest",
    "not_before",
    "not_after",
    "revoked",
)

#: The read-back receipt's closed shape -- every declared field this module binds *except*
#: the two live/mutable fields a receipt taken at grant-issuance time cannot meaningfully
#: speak to: ``current_*`` (this invocation's own live scope, re-checked separately against
#: the authorized_* fields the receipt *does* bind) and ``revoked`` (a live kill-switch, not a
#: fact the original read-back could have observed in advance).
RECEIPT_KEYS: frozenset[str] = frozenset(
    {
        "work_unit_id",
        "difference_id",
        "governing_issue",
        "adoption_id",
        "comment_url",
        "decision_authority",
        "decision_status",
        "authorized_repository",
        "authorized_pull_request",
        "authorized_base_sha",
        "authorized_head_sha",
        "requirement_id",
        "implementation_provider",
        "implementation_session_ref",
        "inspector_provider",
        "inspector_session_ref",
        "permitted_paths",
        "permitted_checks",
        "environment_fingerprint",
        "input_digest",
        "not_before",
        "not_after",
    }
)

_COMMENT_URL_PATTERN = re.compile(
    r"^https://github\.com/manosube/manosube-agent-civilization-os"
    r"/(?:issues|pull)/[0-9]+#issuecomment-[0-9]+$"
)
_WORK_UNIT_ID_PATTERN = re.compile(r"^WORK-UNIT-[A-Z0-9][A-Z0-9-]*$")
_DIFFERENCE_ID_PATTERN = re.compile(r"^D-[A-Z0-9][A-Z0-9-]*$")
_GOVERNING_REFERENCE_PATTERN = re.compile(r"^#[0-9]+$")
_ADOPTION_ID_PATTERN = re.compile(r"^ADOPT_[A-Z0-9_]+$")
_PULL_REQUEST_PATTERN = re.compile(r"^#[0-9]+$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")
_SESSION_REF_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_INPUT_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _looks_like_git_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in (40, 64)
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewSelectionError(f"{context} is not an object: {type(value).__name__}")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise ReviewSelectionError(f"{context} is not a string: {type(value).__name__}")
    return value


def _require_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ReviewSelectionError(f"{context} is not a boolean: {type(value).__name__}")
    return value


def _require_string_list(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ReviewSelectionError(f"{context} must be an array")
    if not value:
        raise ReviewSelectionError(f"{context} must not be empty")
    if not all(isinstance(item, str) and item for item in value):
        raise ReviewSelectionError(f"{context} must contain only non-empty strings")
    return tuple(value)


def _require_request_shape(record: Any) -> dict[str, Any]:
    shaped = _require_object(record, "review selection record")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise ReviewSelectionError(
            f"review selection record carries unknown keys: {sorted(unknown)}"
        )
    missing = set(REQUIRED_REQUEST_KEYS) - set(shaped)
    if missing:
        raise ReviewSelectionError(
            f"review selection record omits required keys: {sorted(missing)}"
        )
    version = _require_string(shaped["schema_version"], "review selection schema_version")
    if version != SCHEMA_VERSION:
        raise ReviewSelectionError(f"unsupported review selection schema_version: {version!r}")
    return shaped


def _require_receipt_shape(value: Any, context: str) -> dict[str, Any]:
    shaped = _require_object(value, context)
    unknown = set(shaped) - RECEIPT_KEYS
    if unknown:
        raise ReviewSelectionError(f"{context} carries unknown keys: {sorted(unknown)}")
    missing = RECEIPT_KEYS - set(shaped)
    if missing:
        raise ReviewSelectionError(f"{context} omits required keys: {sorted(missing)}")
    return shaped


def _require_environment_fingerprint(value: Any, context: str) -> dict[str, str]:
    shaped = _require_object(value, context)
    unknown = set(shaped) - set(SUPPORTED_ENVIRONMENT_FINGERPRINT)
    if unknown:
        raise ReviewSelectionError(f"{context} carries unknown keys: {sorted(unknown)}")
    missing = set(SUPPORTED_ENVIRONMENT_FINGERPRINT) - set(shaped)
    if missing:
        raise ReviewSelectionError(f"{context} omits required keys: {sorted(missing)}")
    return {key: _require_string(shaped[key], f"{context}[{key!r}]") for key in shaped}


def _require_timestamp(value: Any, context: str) -> str:
    """Return *value* unchanged once confirmed a real, timezone-aware ISO-8601 timestamp.

    NRC1-F3 correction (Issue #109 post-merge native-reuse adoption, comment 6054935084):
    before this correction, a timezone-naive value (e.g. ``"2026-10-08T00:00:00"``, no ``Z``
    and no numeric offset) satisfied this check -- :func:`datetime.fromisoformat` parses it
    without complaint -- but every caller of this function (:func:`evaluate_review_selection`'s
    own *now*/*not_before*/*not_after*) later compares the parsed value against another one it
    assumes is also aware, which raises an uncaught ``TypeError`` the instant the two disagree,
    not the established :class:`ReviewSelectionError` refusal contract every other malformed
    timestamp here already gets (and that :func:`.evaluation._evaluate_review_selection`'s own
    existing ``except ReviewSelectionError`` already converts to a clean refusal, so this fix
    also closes the identical gap at that outer consumer). Fixed: a value that parses but
    carries no timezone at all is refused the identical way a value that does not parse at all
    already is -- *Z*/numeric-offset forms are accepted exactly as before.
    """

    text = _require_string(value, context)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewSelectionError(
            f"{context} is not a real ISO-8601 timestamp: {text!r}"
        ) from error
    if parsed.tzinfo is None:
        raise ReviewSelectionError(
            f"{context} is not a timezone-aware ISO-8601 timestamp (no 'Z' or numeric "
            f"offset): {text!r}"
        )
    return text


def evaluate_review_selection(record: dict[str, Any], *, now: str) -> dict[str, Any]:
    """Return one canonical Bounded Review Grant Decision for one exact record, as of *now*.

    *record* is never mutated. *now* is the caller's own trusted-clock reading (an ISO-8601
    timestamp) -- this module never calls a clock itself, the identical discipline
    `work_time_transparency`'s injected-clock convention already uses throughout this
    repository. The same ``(record, now)`` pair always produces the same decision and the
    same ``decision_reason_codes``.
    """

    shaped = _require_request_shape(deepcopy(record))
    now_text = _require_timestamp(now, "now")
    now_value = datetime.fromisoformat(now_text.replace("Z", "+00:00"))

    work_unit_id = _require_string(shaped["work_unit_id"], "review selection work_unit_id")
    invoked_work_unit_id = _require_string(
        shaped["invoked_work_unit_id"], "review selection invoked_work_unit_id"
    )
    difference_id = _require_string(shaped["difference_id"], "review selection difference_id")
    governing_issue = _require_string(shaped["governing_issue"], "review selection governing_issue")
    adoption_id = _require_string(shaped["adoption_id"], "review selection adoption_id")
    comment_url = _require_string(shaped["comment_url"], "review selection comment_url")
    decision_authority = _require_string(
        shaped["decision_authority"], "review selection decision_authority"
    )
    decision_status = _require_string(shaped["decision_status"], "review selection decision_status")
    receipt = _require_receipt_shape(
        shaped["api_read_back_receipt"], "review selection api_read_back_receipt"
    )
    authorized_repository = _require_string(
        shaped["authorized_repository"], "review selection authorized_repository"
    )
    authorized_pull_request = _require_string(
        shaped["authorized_pull_request"], "review selection authorized_pull_request"
    )
    authorized_base_sha = _require_string(
        shaped["authorized_base_sha"], "review selection authorized_base_sha"
    )
    authorized_head_sha = _require_string(
        shaped["authorized_head_sha"], "review selection authorized_head_sha"
    )
    current_repository = _require_string(
        shaped["current_repository"], "review selection current_repository"
    )
    current_pull_request = _require_string(
        shaped["current_pull_request"], "review selection current_pull_request"
    )
    current_base_sha = _require_string(
        shaped["current_base_sha"], "review selection current_base_sha"
    )
    current_head_sha = _require_string(
        shaped["current_head_sha"], "review selection current_head_sha"
    )
    requirement_id = _require_string(shaped["requirement_id"], "review selection requirement_id")
    implementation_provider = _require_string(
        shaped["implementation_provider"], "review selection implementation_provider"
    )
    implementation_session_ref = _require_string(
        shaped["implementation_session_ref"], "review selection implementation_session_ref"
    )
    inspector_provider = _require_string(
        shaped["inspector_provider"], "review selection inspector_provider"
    )
    inspector_session_ref = _require_string(
        shaped["inspector_session_ref"], "review selection inspector_session_ref"
    )
    permitted_paths = _require_string_list(
        shaped["permitted_paths"], "review selection permitted_paths"
    )
    permitted_checks = _require_string_list(
        shaped["permitted_checks"], "review selection permitted_checks"
    )
    environment_fingerprint = _require_environment_fingerprint(
        shaped["environment_fingerprint"], "review selection environment_fingerprint"
    )
    input_digest = _require_string(shaped["input_digest"], "review selection input_digest")
    not_before = _require_timestamp(shaped["not_before"], "review selection not_before")
    not_after = _require_timestamp(shaped["not_after"], "review selection not_after")
    revoked = _require_bool(shaped["revoked"], "review selection revoked")

    reasons: list[str] = []

    if not _WORK_UNIT_ID_PATTERN.match(work_unit_id):
        reasons.append("WORK_UNIT_ID_MALFORMED")
    if not _DIFFERENCE_ID_PATTERN.match(difference_id):
        reasons.append("DIFFERENCE_ID_MALFORMED")
    if not _GOVERNING_REFERENCE_PATTERN.match(governing_issue):
        reasons.append("GOVERNING_REFERENCE_MALFORMED")
    if not _ADOPTION_ID_PATTERN.match(adoption_id):
        reasons.append("ADOPTION_ID_MALFORMED")
    if not _COMMENT_URL_PATTERN.match(comment_url):
        reasons.append("COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT")
    if not _PULL_REQUEST_PATTERN.match(authorized_pull_request):
        reasons.append("AUTHORIZED_PULL_REQUEST_MALFORMED")
    if not _REQUIREMENT_ID_PATTERN.match(requirement_id):
        reasons.append("REQUIREMENT_ID_MALFORMED")
    if not _SESSION_REF_PATTERN.match(implementation_session_ref):
        reasons.append("IMPLEMENTATION_SESSION_REF_MALFORMED")
    if not _SESSION_REF_PATTERN.match(inspector_session_ref):
        reasons.append("INSPECTOR_SESSION_REF_MALFORMED")
    if not _INPUT_DIGEST_PATTERN.match(input_digest):
        reasons.append("INPUT_DIGEST_MALFORMED")
    if not all(is_safe_repository_relative_path(path) for path in permitted_paths):
        reasons.append("PERMITTED_PATHS_MALFORMED")
    if not set(permitted_checks) <= ALLOWED_CHECK_CATEGORIES:
        reasons.append("PERMITTED_CHECKS_OUTSIDE_RATIFIED_CATEGORIES")
    if implementation_provider not in EXECUTOR_PROVIDERS:
        reasons.append("UNKNOWN_IMPLEMENTATION_PROVIDER")
    if inspector_provider != BOUNDED_TECHNICAL_REVIEWER:
        reasons.append("INSPECTOR_PROVIDER_NOT_THE_RATIFIED_REVIEWER")
    if environment_fingerprint != SUPPORTED_ENVIRONMENT_FINGERPRINT:
        reasons.append("ENVIRONMENT_FINGERPRINT_UNSUPPORTED")

    # Receipt binding: the record's own declared fields must agree, field by field, with the
    # caller's own structured claim of what the independent read-back showed. Generated from
    # the one closed RECEIPT_KEYS set, rather than hand-listed, so no field can be bound in
    # the record's own shape above while silently never being checked for receipt agreement.
    declared: dict[str, Any] = {
        "work_unit_id": work_unit_id,
        "difference_id": difference_id,
        "governing_issue": governing_issue,
        "adoption_id": adoption_id,
        "comment_url": comment_url,
        "decision_authority": decision_authority,
        "decision_status": decision_status,
        "authorized_repository": authorized_repository,
        "authorized_pull_request": authorized_pull_request,
        "authorized_base_sha": authorized_base_sha,
        "authorized_head_sha": authorized_head_sha,
        "requirement_id": requirement_id,
        "implementation_provider": implementation_provider,
        "implementation_session_ref": implementation_session_ref,
        "inspector_provider": inspector_provider,
        "inspector_session_ref": inspector_session_ref,
        "permitted_paths": list(permitted_paths),
        "permitted_checks": list(permitted_checks),
        "environment_fingerprint": environment_fingerprint,
        "input_digest": input_digest,
        "not_before": not_before,
        "not_after": not_after,
    }
    for field in sorted(RECEIPT_KEYS):
        if receipt[field] != declared[field]:
            reasons.append(f"API_READ_BACK_RECEIPT_{field.upper()}_MISMATCH")

    if decision_authority != HUMAN_AUTHORITY:
        reasons.append("DECISION_AUTHORITY_NOT_HUMAN")
    if decision_status != "RATIFIED":
        reasons.append("DECISION_STATUS_NOT_RATIFIED")

    if authorized_repository != THIS_REPOSITORY:
        reasons.append("AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY")
    if current_repository != authorized_repository:
        reasons.append("REPOSITORY_SCOPE_MISMATCH")
    if current_pull_request != authorized_pull_request:
        reasons.append("PULL_REQUEST_SCOPE_MISMATCH")

    base_sha_ok = _looks_like_git_sha(authorized_base_sha)
    if not base_sha_ok:
        reasons.append("AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA")
    head_sha_ok = _looks_like_git_sha(authorized_head_sha)
    if not head_sha_ok:
        reasons.append("AUTHORIZED_HEAD_SHA_NOT_A_COMMIT_SHA")
    current_base_sha_ok = _looks_like_git_sha(current_base_sha)
    if not current_base_sha_ok:
        reasons.append("CURRENT_BASE_SHA_NOT_A_COMMIT_SHA")
    current_head_sha_ok = _looks_like_git_sha(current_head_sha)
    if not current_head_sha_ok:
        reasons.append("CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA")
    if base_sha_ok and current_base_sha_ok and authorized_base_sha != current_base_sha:
        reasons.append("BASE_SHA_SCOPE_MISMATCH")
    if head_sha_ok and current_head_sha_ok and authorized_head_sha != current_head_sha:
        reasons.append("HEAD_SHA_STALE")

    if work_unit_id != invoked_work_unit_id:
        reasons.append("CROSS_WORK_UNIT_REPLAY")

    if revoked:
        reasons.append("REVIEW_GRANT_REVOKED")

    not_before_value = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
    not_after_value = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
    if not_before_value > not_after_value:
        reasons.append("REVIEW_GRANT_WINDOW_INVERTED")
    elif now_value < not_before_value:
        reasons.append("REVIEW_GRANT_NOT_YET_VALID")
    elif now_value > not_after_value:
        reasons.append("REVIEW_GRANT_EXPIRED")

    decision = REVIEW_SELECTION_REFUSED if reasons else REVIEW_SELECTION_ADMITTED
    return {
        "schema_version": SCHEMA_VERSION,
        "work_unit_id": work_unit_id,
        "governing_issue": governing_issue,
        "requirement_id": requirement_id,
        "comment_url": comment_url,
        "decision": decision,
        "decision_reason_codes": sorted(set(reasons)),
    }


#: Every reason code :func:`evaluate_review_selection` can emit from a hand-named ``if``/
#: ``elif`` branch (every one of them except the receipt-mismatch family, which is generated
#: from :data:`RECEIPT_KEYS` -- see :data:`EMITTED_RECEIPT_MISMATCH_REASON_CODES` for that
#: half, kept separate so adding a receipt-bound field here can never silently fall out of
#: step with what this set below claims).
EMITTED_REASON_CODES: frozenset[str] = frozenset(
    {
        "WORK_UNIT_ID_MALFORMED",
        "DIFFERENCE_ID_MALFORMED",
        "GOVERNING_REFERENCE_MALFORMED",
        "ADOPTION_ID_MALFORMED",
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "AUTHORIZED_PULL_REQUEST_MALFORMED",
        "REQUIREMENT_ID_MALFORMED",
        "IMPLEMENTATION_SESSION_REF_MALFORMED",
        "INSPECTOR_SESSION_REF_MALFORMED",
        "INPUT_DIGEST_MALFORMED",
        "PERMITTED_PATHS_MALFORMED",
        "PERMITTED_CHECKS_OUTSIDE_RATIFIED_CATEGORIES",
        "UNKNOWN_IMPLEMENTATION_PROVIDER",
        "INSPECTOR_PROVIDER_NOT_THE_RATIFIED_REVIEWER",
        "ENVIRONMENT_FINGERPRINT_UNSUPPORTED",
        "DECISION_AUTHORITY_NOT_HUMAN",
        "DECISION_STATUS_NOT_RATIFIED",
        "AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY",
        "REPOSITORY_SCOPE_MISMATCH",
        "PULL_REQUEST_SCOPE_MISMATCH",
        "AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA",
        "AUTHORIZED_HEAD_SHA_NOT_A_COMMIT_SHA",
        "CURRENT_BASE_SHA_NOT_A_COMMIT_SHA",
        "CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA",
        "BASE_SHA_SCOPE_MISMATCH",
        "HEAD_SHA_STALE",
        "CROSS_WORK_UNIT_REPLAY",
        "REVIEW_GRANT_REVOKED",
        "REVIEW_GRANT_WINDOW_INVERTED",
        "REVIEW_GRANT_NOT_YET_VALID",
        "REVIEW_GRANT_EXPIRED",
        # REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174): every hand-named reason
        # code this module's *second* evaluator, :func:`evaluate_native_review_relevance`, can
        # emit -- declared in this identical module-wide set (`test_active_document_terminal_
        # state.py`'s own generic, package-wide bidirectional proof binds the name
        # ``EMITTED_REASON_CODES`` to one whole module's own emittable surface, not to any one
        # evaluator inside it), proven reachable by its own separate matrix in
        # ``test_bounded_technical_review_enforcement.py``.
        "NATIVE_REPOSITORY_MISMATCH",
        "NATIVE_PULL_REQUEST_MISMATCH",
        "NATIVE_REVIEWED_BASE_UNKNOWN",
        "NATIVE_REVIEWED_BASE_STALE",
        "NATIVE_COVERAGE_INSUFFICIENT_FOR_GRANT_SCOPE",
        # NRC1-F2 correction (Issue #109 post-merge native-reuse adoption, comment 6054935084):
        # the reverse-direction coverage check -- inspected_paths carrying a path outside
        # permitted_paths -- was never reachable at all before this correction.
        "NATIVE_COVERAGE_EXCEEDS_GRANT_SCOPE",
        # SR2-F3 correction (PR #112 comment 6021757577): *reviewed_commit_sha* (the PR head a
        # native review ran against) and *inspected_base_sha* (what it actually diffed that
        # head against) are genuinely separate facts -- the former being right never implied
        # the latter was ever checked at all before this correction.
        "NATIVE_INSPECTED_BASE_UNKNOWN",
        "NATIVE_INSPECTED_BASE_STALE",
    }
)

#: The receipt-mismatch half of the reachable reason-code surface, generated from the
#: identical :data:`RECEIPT_KEYS` set :func:`evaluate_review_selection` itself loops over --
#: computed, not hand-duplicated, so the two can never drift apart.
EMITTED_RECEIPT_MISMATCH_REASON_CODES: frozenset[str] = frozenset(
    f"API_READ_BACK_RECEIPT_{field.upper()}_MISMATCH" for field in RECEIPT_KEYS
)


# --------------------------------------------------------------------------- #
# F1 correction (PR #112 comment 6019024445): authenticated admission, distinct from the
# pure shape/consistency check above.
# --------------------------------------------------------------------------- #

#: The one reference kind ``verifier_selection_grant_refs`` may ever name -- matching
#: ``independent_verification.route``'s own identical constant by value, never by import (that
#: route never imports this one, and this one never imports it -- see this module's own
#: docstring note on why a second owner duplicates a handful of literal strings rather than
#: ever becoming a second place either question is answered).
_VERIFIER_SELECTION_GRANT_REF_KIND = "verifier_selection_grant"

#: The one reference kind ``human_grant_declaration_refs`` may ever name -- the identical
#: convention for the identical reason.
_HUMAN_GRANT_DECLARATION_REF_KIND = "human_grant_declaration"


def _require_reference(value: Any, *, context: str, allowed_kind: str) -> dict[str, Any]:
    """Return *value* once it carries a non-empty ``kind``/``id`` pair naming *allowed_kind*
    exactly -- the identical shape check ``independent_verification.route`` already performs
    for its own grant/declaration references, duplicated here rather than imported across
    verticals."""

    if not isinstance(value, Mapping):
        raise ReviewSelectionError(f"{context} must be an explicit reference object: {value!r}")
    kind = value.get("kind")
    identity = value.get("id")
    if not isinstance(kind, str) or not kind:
        raise ReviewSelectionError(f"{context} carries no readable kind: {value!r}")
    if not isinstance(identity, str) or not identity:
        raise ReviewSelectionError(f"{context} carries no readable id: {value!r}")
    if kind != allowed_kind:
        raise ReviewSelectionError(f"{context} names {kind!r}, not {allowed_kind!r}: {value!r}")
    return dict(value)


def _resolve_or_refuse(
    store: Any, project_id: str, *, kind: str, record_id: str, context: str
) -> dict[str, Any]:
    """Return the Store's own committed record for *(kind, record_id)*, or fail closed --
    the identical single read-only surface (``FileStateStore.resolve_record``)
    ``independent_verification.route`` already uses for the identical purpose. A reference
    naming a record the Store does not durably resolve is never silently treated as absent; it
    refuses before :func:`authenticate_bounded_review_grant` ever reaches Authority."""

    resolved: dict[str, Any] | None = store.resolve_record(project_id, kind, record_id)
    if resolved is None:
        raise ReviewSelectionError(
            f"{context} does not resolve for project {project_id!r}: {kind}/{record_id}"
        )
    return resolved


#: SR3-F1 correction (PR #112 comment 6030487245): every grant field
#: :func:`compute_launch_envelope_digest` folds into one canonical digest -- the complete
#: launch envelope, never only ``permitted_paths``/``permitted_checks``.
LAUNCH_ENVELOPE_DIGEST_FIELDS: tuple[str, ...] = (
    "authorized_repository",
    "authorized_pull_request",
    "authorized_base_sha",
    "authorized_head_sha",
    "requirement_id",
    "input_digest",
    "not_before",
    "not_after",
    "implementation_provider",
    "implementation_session_ref",
    "inspector_provider",
    "inspector_session_ref",
)


def canonical_list_digest(values: Sequence[str]) -> str:
    """Return the one deterministic digest over *values*, order-independent -- the one
    building block :func:`compose_bounded_technical_review_dispatch`'s own ``permitted_boundary``
    uses (SR3-F2 correction, PR #112 comment 6030487245) so that boundary is built entirely
    from scalar digests, never a raw list.

    A raw ``list`` value inside ``permitted_boundary`` survives unmodified only through a
    caller that never passes that boundary through a :class:`~manosube_agent_civilization.
    independent_verification.types.VerifierSelection`'s own deep-freeze -- which turns every
    list into a ``tuple``, and a ``tuple`` is not itself a JSON array
    (:mod:`~manosube_agent_civilization.state.canonicalize`'s own contract, which accepts only
    ``list``). A ``permitted_boundary`` containing a raw list can therefore never be reused,
    unmodified, as a ``VerifierSelection``'s own ``permitted_boundary`` for the identical
    scope's Evidence handoff -- exactly the SR2-era workaround (a *different*, list-free-
    boundary grant for the handoff) that let a caller hand off a classification under a
    scope genuinely authorized for something else entirely (SR3-F2's own reproduced gap). A
    digest-only boundary has no such landmine, and is the identical object the composed
    route's own evidence-handoff correlation check can require a caller's ``VerifierSelection``
    to equal exactly.
    """

    return hashlib.sha256(json.dumps(sorted(values)).encode("utf-8")).hexdigest()


def compute_launch_envelope_digest(grant: Mapping[str, Any]) -> str:
    """Return the one canonical digest binding a Bounded Review Grant's *complete* launch
    envelope -- repository, pull request, base/head SHA, requirement, input digest, validity
    window, and implementation/inspector provenance, plus the environment fingerprint --
    never only the ``permitted_paths``/``permitted_checks`` pair alone.

    SR3-F1 correction (PR #112 comment 6030487245): before this correction,
    :func:`authenticate_bounded_review_grant`'s own *permitted_boundary* argument carried only
    the inspection scope -- a caller could satisfy that check while silently pointing the
    *same* permitted scope at a different repository, PR, base/head, requirement, input
    bundle, validity window, or provenance, since none of those fields was ever part of what
    Authority's own exact-equality check (``authority/verifier_selection.py``'s own
    ``grant["permitted_boundary"] != permitted_boundary``) actually compared. Folding this
    digest into *permitted_boundary* itself means that exact-equality check -- already
    verified against a real, Human-Authority-signed ``verifier_selection_grant`` record, via
    the existing Boot/Authority/Store owners, never re-derived here -- now also authenticates
    the complete envelope, through the identical existing mechanism, with no new Kernel record
    type and no second admission route. A grant signed for a different envelope now produces a
    different digest and is refused outright (``GRANT_BOUNDARY_MISMATCH``), never silently
    accepted because the two sides happened to agree on everything *else*.

    This is deliberately *not* a comparison against a caller-suppliable "live" snapshot taken
    at call time (the shape :func:`compose_bounded_technical_review_dispatch`'s own prior
    ``grant_provider`` re-check used) -- a caller who controls both the original and the
    "fresh" snapshot can make any two fabricated envelopes agree with each other. Binding the
    digest into the Authority-checked boundary instead means every one of these fields is
    checked against a real Human-signed record this function cannot be fooled into resolving
    a match for merely because a caller's own two readings of its own data agree.
    """

    payload = "|".join(str(grant[field]) for field in LAUNCH_ENVELOPE_DIGEST_FIELDS)
    payload += "|" + json.dumps(dict(grant["environment_fingerprint"]), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def authenticate_bounded_review_grant(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    requirement_id: str,
    selection_id: str,
    verifier_identity: Mapping[str, Any],
    permitted_boundary: Mapping[str, Any],
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return one authenticated-admission Decision for *this exact* CODEX review scope.

    This is the separate layer this module's own F1 correction adds (see the module
    docstring's own addendum): :func:`evaluate_review_selection` proves a record is only
    *internally consistent*; this function proves a real Human Authority actually granted
    *this exact* (*project_id*, *requirement_id*, *selection_id*, *verifier_identity*,
    *permitted_boundary*) scope, by calling the existing Boot and Authority owners exactly
    once each, over grant/declaration references this function itself resolves through the
    Store -- never grant or declaration *content* accepted directly from a caller.

    *verifier_identity* is CODEX's own declared reviewer identity for this scope (e.g.
    ``{"kind": "bounded_codex_technical_reviewer", "id": ...}``); *permitted_boundary* is the
    exact inspection scope this grant authorizes (e.g. ``{"permitted_paths": [...],
    "permitted_checks": [...], "launch_envelope_digest": compute_launch_envelope_digest(...)}``)
    -- both are plain data this function passes straight through to
    :func:`~manosube_agent_civilization.authority.evaluate_verifier_selection`, never
    interpreted here, so CODEX's review scope -- the complete launch envelope, since SR3-F1,
    not merely the inspection scope -- is encoded entirely through that existing contract's own
    two fields rather than through any new Kernel record type.

    Every Boot failure (:class:`~manosube_agent_civilization.boot.errors.BootNotFoundError`,
    :class:`~manosube_agent_civilization.boot.errors.BootConsistencyError`) and every
    :class:`~manosube_agent_civilization.authority.errors.AuthorityError` this function's own
    calls raise propagates completely unchanged -- there is no admission question to answer
    for a Project that does not genuinely boot, or a request Authority itself cannot read.
    An unresolvable grant/declaration reference raises :class:`~.errors.ReviewSelectionError`
    for the identical reason. Only the resulting Authority Decision's own ``SELECTED``/
    ``REFUSED`` outcome is ever returned as data: a readable request that Authority refuses is
    :data:`REVIEW_SELECTION_REFUSED`, with Authority's own ``decision_reason_codes`` carried
    through unchanged, never an exception.

    ``boot``/``authority`` are imported here, at call time, never at this module's own import
    time: :mod:`.development_binding` (this module's own package) is installed and imported
    far more widely than the two heavy Kernel owners this one function reuses, including by
    the installed-wheel guard (``tests/integration/binding/test_installed_wheel_guard.py``)
    with no declared dependency beyond the standard library itself. Importing ``boot``/
    ``authority`` eagerly at module scope would make every consumer of this package -- even one
    that only ever reads :mod:`.policy` -- transitively require ``jsonschema`` merely to import
    this module at all; deferring the import to here means that surface is only ever paid by a
    caller that actually calls this one function.
    """

    from manosube_agent_civilization.authority import (
        SELECTED as _AUTHORITY_SELECTED,
        evaluate_verifier_selection,
    )
    from manosube_agent_civilization.boot import boot_project

    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    real_human_authority_ref = dict(boot_context.human_authority_ref)
    real_human_authority_signing_key = dict(
        boot_context.project_binding["human_authority_signing_key"]
    )

    resolved_grants: list[dict[str, Any]] = []
    for index, grant_ref in enumerate(verifier_selection_grant_refs):
        checked = _require_reference(
            grant_ref,
            context=f"verifier_selection_grant_refs[{index}]",
            allowed_kind=_VERIFIER_SELECTION_GRANT_REF_KIND,
        )
        resolved_grants.append(
            _resolve_or_refuse(
                store,
                project_id,
                kind=checked["kind"],
                record_id=checked["id"],
                context=f"verifier_selection_grant_refs[{index}]",
            )
        )

    resolved_declarations: list[dict[str, Any]] = []
    for index, declaration_ref in enumerate(human_grant_declaration_refs):
        checked = _require_reference(
            declaration_ref,
            context=f"human_grant_declaration_refs[{index}]",
            allowed_kind=_HUMAN_GRANT_DECLARATION_REF_KIND,
        )
        resolved_declarations.append(
            _resolve_or_refuse(
                store,
                project_id,
                kind=checked["kind"],
                record_id=checked["id"],
                context=f"human_grant_declaration_refs[{index}]",
            )
        )

    selection_decision = evaluate_verifier_selection(
        {
            "schema_version": "0.1",
            "project_id": project_id,
            "requirement_id": requirement_id,
            "selection_id": selection_id,
            "verifier_identity": dict(verifier_identity),
            "permitted_boundary": dict(permitted_boundary),
            "selection_status": "ACTIVE",
            "human_authority_ref": real_human_authority_ref,
            "human_authority_signing_key": real_human_authority_signing_key,
            "grants": resolved_grants,
            "grant_declarations": resolved_declarations,
        }
    )

    if selection_decision["decision"] != _AUTHORITY_SELECTED:
        return {
            "decision": REVIEW_SELECTION_REFUSED,
            "decision_reason_codes": selection_decision["decision_reason_codes"],
            "grant_ref": None,
            "declaration_ref": None,
        }
    return {
        "decision": REVIEW_SELECTION_ADMITTED,
        "decision_reason_codes": [],
        "grant_ref": selection_decision["grant_ref"],
        "declaration_ref": selection_decision["declaration_ref"],
    }


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622):
# is one already-fetched, shape-valid native review (`.review_adapter.
# validate_native_review_evidence`) actually relevant to *this* Bounded Review Grant -- pure,
# offline, zero network calls, zero new model requests, identical discipline to
# :func:`evaluate_review_selection` above.
# --------------------------------------------------------------------------- #

NATIVE_REVIEW_RELEVANT = "NATIVE_REVIEW_RELEVANT"
NATIVE_REVIEW_NOT_RELEVANT = "NATIVE_REVIEW_NOT_RELEVANT"
NATIVE_REVIEW_RELEVANCE_DECISIONS: frozenset[str] = frozenset(
    {NATIVE_REVIEW_RELEVANT, NATIVE_REVIEW_NOT_RELEVANT}
)


def evaluate_native_review_relevance(
    native_evidence: Mapping[str, Any], *, grant: Mapping[str, Any]
) -> dict[str, Any]:
    """Return one relevance Decision for *native_evidence* against *this exact* Bounded Review
    Grant -- never whether the native review is itself trustworthy evidence of anything (that
    is :func:`.review_adapter.validate_native_review_evidence`'s own shape question, already
    answered before this function is ever reached) and never a VERIFIED/FAILED/INSUFFICIENT/
    UNAVAILABLE classification (that is the composed caller's own job, over *relevant*
    evidence only -- see ``scripts/bounded_technical_review.py``'s own native-reuse route).

    ``BASE_UNKNOWN`` (the evidence's own ``reviewed_commit_sha`` is ``None``) is always its own
    distinct reason, never folded into ``BASE_STALE`` -- the design supplement's own explicit
    "inspected-base-unknown は現在PRベースと区別し、絶対に推定しない" requirement: a native
    review that never named the commit it inspected is neither assumed current nor assumed
    stale, only refused as not relevant, honestly, for the reason it actually is.

    NRC1-F2 correction (Issue #109 post-merge native-reuse adoption, comment 6054935084): the
    coverage check below used to require only that *grant*'s own ``permitted_paths`` be a
    subset of the native review's own ``inspected_paths`` (``permitted_paths <= inspected_
    paths``) -- a native review that inspected strictly *more* than the grant ever permitted
    was still reported relevant, silently widening this grant-bound classification/import to
    a scope the grant itself never authorized. Reproduced: ``permitted_paths=["allowed.py"]``,
    ``inspected_paths=["allowed.py", "outside.py"]`` returned ``NATIVE_REVIEW_RELEVANT`` with
    no reason at all. Fixed: the two sets must now be exactly equal -- a native review that
    inspected anything outside *grant*'s own ``permitted_paths``, not only one that inspected
    too little, is refused (``NATIVE_COVERAGE_EXCEEDS_GRANT_SCOPE``). The native review's own,
    wider observation is never discarded by this check -- a caller that retains it may still
    treat it as external/historical information -- but this function never itself reports a
    grant-authorized ``NATIVE_REVIEW_RELEVANT`` import for more than the grant's own scope.
    """

    reasons: list[str] = []
    if native_evidence.get("repository") != grant["authorized_repository"]:
        reasons.append("NATIVE_REPOSITORY_MISMATCH")
    if native_evidence.get("pull_request") != grant["authorized_pull_request"]:
        reasons.append("NATIVE_PULL_REQUEST_MISMATCH")

    reviewed_commit_sha = native_evidence.get("reviewed_commit_sha")
    if reviewed_commit_sha is None:
        reasons.append("NATIVE_REVIEWED_BASE_UNKNOWN")
    elif reviewed_commit_sha != grant["authorized_head_sha"]:
        reasons.append("NATIVE_REVIEWED_BASE_STALE")

    # SR2-F3 correction (PR #112 comment 6021757577): *inspected_base_sha* is the merge-base/
    # target the native review actually diffed *reviewed_commit_sha* against -- a genuinely
    # separate fact from the head check above, checked here for the first time. Before this
    # correction a native review of the exact right head, diffed against a stale or wrong
    # base, was reported relevant purely because nothing here ever looked at this field at all.
    inspected_base_sha = native_evidence.get("inspected_base_sha")
    if inspected_base_sha is None:
        reasons.append("NATIVE_INSPECTED_BASE_UNKNOWN")
    elif inspected_base_sha != grant["authorized_base_sha"]:
        reasons.append("NATIVE_INSPECTED_BASE_STALE")

    permitted_paths = set(grant["permitted_paths"])
    inspected_paths = set(native_evidence.get("inspected_paths") or [])
    if not permitted_paths <= inspected_paths:
        reasons.append("NATIVE_COVERAGE_INSUFFICIENT_FOR_GRANT_SCOPE")
    # NRC1-F2 correction (Issue #109 post-merge native-reuse adoption, comment 6054935084): the
    # reverse direction -- inspected_paths carrying paths outside permitted_paths -- was never
    # checked at all; exact set equality is this grant-bound route's own minimal requirement.
    if not inspected_paths <= permitted_paths:
        reasons.append("NATIVE_COVERAGE_EXCEEDS_GRANT_SCOPE")

    decision = NATIVE_REVIEW_NOT_RELEVANT if reasons else NATIVE_REVIEW_RELEVANT
    return {
        "decision": decision,
        "decision_reason_codes": sorted(set(reasons)),
    }
