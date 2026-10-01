"""The Executor Selection Record: which eligible provider is this work unit's one executor.

Decision 0003 (Issue #102) admits ``GITHUB_COPILOT`` as a second name the implementation
executor capability may be filled by, alongside ``CLAUDE_CODE`` (`development_binding.policy`).
That admission is eligibility, not authority: a role existing in the ratified role map answers
"is this name one this Binding recognises at all", never "is it the active executor for this
one work unit, right now, at this exact scope". This module answers the second, narrower
question, mechanically, the same way `development_binding.adoption_record` answers it for a
Human-adopted finding -- a structured record, checked offline, with no network call and no
default-admit path.

```text
ELIGIBLE  = named in policy.EXECUTOR_PROVIDERS
SELECTED  = ELIGIBLE, and bound by an ADMITTED record to this exact work unit and scope
```

Claude Code needs no selection record to keep operating: :data:`policy.DEFAULT_EXECUTOR_PROVIDER`
is ``CLAUDE_CODE``, so every historical and future Claude Code work unit continues exactly as
it did under Decision 0002. A selection record is the gate for the *other* eligible name:
before any output from Copilot is treated as this repository's authorized implementation for
a given work unit, a record naming Copilot must be evaluated here and answer
``EXECUTOR_SELECTION_ADMITTED``.

Following this repository's `adoption_record` grammar: an **unreadable** record -- wrong
Python shape, an unknown key, a missing required key, a non-string field -- raises
:class:`~.errors.ExecutorSelectionError`, since there is no selection question to answer. A
**readable-but-insufficient** record is never an exception; it is the decision
``EXECUTOR_SELECTION_REFUSED``, with the specific reason codes this module can name. This
module performs no network call, holds no token, and cannot prove current remote GitHub or
repository state -- only that the record it was given is internally consistent, exactly as
`adoption_record` states for itself (`RUNTIME_ENFORCEMENT_IMPLEMENTED=false`).

Six bindings this module checks, each answering one of the required counterexamples:

- ``selected_executor_provider`` must be a name :data:`policy.EXECUTOR_PROVIDERS` recognises
  (an unknown provider, e.g. a plain actor string nobody ratified, is refused).
- ``comment_url`` must be a verifiable, immutable comment in *this* repository, and the
  six-field ``api_read_back_receipt`` must agree with the record's own declared fields of the
  same name (a forged or unposted selection is refused the same way a forged adoption is).
- ``authorized_repository``/``authorized_branch``/``authorized_base_sha`` must match
  ``current_repository``/``current_branch``/``current_base_sha`` (a scope mismatch, including
  a changed base, is refused).
- ``expected_head_sha`` must match ``current_head_sha`` (new commits landed since the grant --
  a stale selection -- is refused).
- ``work_unit_id`` must match ``invoked_work_unit_id`` (a grant issued for one work unit is
  refused when replayed to authorize a different one).
- ``concurrently_active_provider_for_work_unit`` must be empty or equal to this record's own
  ``selected_executor_provider`` (two providers simultaneously active for one work unit is
  refused as a duplicate selection).
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .errors import ExecutorSelectionError
from .policy import EXECUTOR_PROVIDERS

SCHEMA_VERSION = "0.1"

EXECUTOR_SELECTION_ADMITTED = "EXECUTOR_SELECTION_ADMITTED"
EXECUTOR_SELECTION_REFUSED = "EXECUTOR_SELECTION_REFUSED"
DECISIONS: frozenset[str] = frozenset({EXECUTOR_SELECTION_ADMITTED, EXECUTOR_SELECTION_REFUSED})

#: The sole authority that may select, for one work unit, which eligible provider is active.
#: Matches ``development_binding.policy.EXECUTOR_PROVIDER_SELECTION_AUTHORITY`` by value, for
#: the same reason `adoption_record.HUMAN_AUTHORITY` matches `policy.HUMAN_AUTHORITY` by value
#: rather than by import: a self-contained extension, not a second owner that happens to agree.
HUMAN_AUTHORITY = "SHUKOU"

#: This repository, and no other -- a selection record scoped to a different repository must
#: never authorize work here, whatever else about it reads as complete.
THIS_REPOSITORY = "manosube/manosube-agent-civilization-os"

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "work_unit_id",
    "invoked_work_unit_id",
    "governing_issue",
    "selected_executor_provider",
    "comment_url",
    "decision_authority",
    "decision_status",
    "api_read_back_receipt",
    "authorized_repository",
    "authorized_branch",
    "authorized_base_sha",
    "expected_head_sha",
    "current_repository",
    "current_branch",
    "current_base_sha",
    "current_head_sha",
    "concurrently_active_provider_for_work_unit",
)

#: The read-back receipt's closed shape: the same six field names as the record's own
#: top-level declarations of those names, so the binding below is a plain field-by-field
#: comparison rather than a derived relationship.
RECEIPT_KEYS: frozenset[str] = frozenset(
    {
        "work_unit_id",
        "governing_issue",
        "selected_executor_provider",
        "comment_url",
        "decision_authority",
        "decision_status",
    }
)

_COMMENT_URL_PATTERN = re.compile(
    r"^https://github\.com/manosube/manosube-agent-civilization-os"
    r"/(?:issues|pull)/[0-9]+#issuecomment-[0-9]+$"
)
_WORK_UNIT_ID_PATTERN = re.compile(r"^WORK-UNIT-[A-Z0-9][A-Z0-9-]*$")
_GOVERNING_REFERENCE_PATTERN = re.compile(r"^#[0-9]+$")


def _looks_like_git_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in (40, 64)
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExecutorSelectionError(f"{context} is not an object: {type(value).__name__}")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise ExecutorSelectionError(f"{context} is not a string: {type(value).__name__}")
    return value


def _require_request_shape(record: Any) -> dict[str, Any]:
    shaped = _require_object(record, "executor selection record")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise ExecutorSelectionError(
            f"executor selection record carries unknown keys: {sorted(unknown)}"
        )
    missing = set(REQUIRED_REQUEST_KEYS) - set(shaped)
    if missing:
        raise ExecutorSelectionError(
            f"executor selection record omits required keys: {sorted(missing)}"
        )
    version = _require_string(shaped["schema_version"], "executor selection schema_version")
    if version != SCHEMA_VERSION:
        raise ExecutorSelectionError(f"unsupported executor selection schema_version: {version!r}")
    return shaped


def _require_receipt_shape(value: Any, context: str) -> dict[str, Any]:
    shaped = _require_object(value, context)
    unknown = set(shaped) - RECEIPT_KEYS
    if unknown:
        raise ExecutorSelectionError(f"{context} carries unknown keys: {sorted(unknown)}")
    missing = RECEIPT_KEYS - set(shaped)
    if missing:
        raise ExecutorSelectionError(f"{context} omits required keys: {sorted(missing)}")
    return shaped


def evaluate_executor_selection(record: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Executor Selection Decision for one exact record.

    *record* is never mutated. The same record always produces the same decision and the same
    ``decision_reason_codes`` -- this module reads a clock and a network exactly as much as
    :mod:`.adoption_record` does, which is to say never.
    """

    shaped = _require_request_shape(deepcopy(record))

    work_unit_id = _require_string(shaped["work_unit_id"], "executor selection work_unit_id")
    invoked_work_unit_id = _require_string(
        shaped["invoked_work_unit_id"], "executor selection invoked_work_unit_id"
    )
    governing_issue = _require_string(
        shaped["governing_issue"], "executor selection governing_issue"
    )
    selected_executor_provider = _require_string(
        shaped["selected_executor_provider"], "executor selection selected_executor_provider"
    )
    comment_url = _require_string(shaped["comment_url"], "executor selection comment_url")
    decision_authority = _require_string(
        shaped["decision_authority"], "executor selection decision_authority"
    )
    decision_status = _require_string(
        shaped["decision_status"], "executor selection decision_status"
    )
    receipt = _require_receipt_shape(
        shaped["api_read_back_receipt"], "executor selection api_read_back_receipt"
    )
    receipt_work_unit_id = _require_string(
        receipt["work_unit_id"], "executor selection api_read_back_receipt work_unit_id"
    )
    receipt_governing_issue = _require_string(
        receipt["governing_issue"], "executor selection api_read_back_receipt governing_issue"
    )
    receipt_selected_executor_provider = _require_string(
        receipt["selected_executor_provider"],
        "executor selection api_read_back_receipt selected_executor_provider",
    )
    receipt_comment_url = _require_string(
        receipt["comment_url"], "executor selection api_read_back_receipt comment_url"
    )
    receipt_decision_authority = _require_string(
        receipt["decision_authority"],
        "executor selection api_read_back_receipt decision_authority",
    )
    receipt_decision_status = _require_string(
        receipt["decision_status"], "executor selection api_read_back_receipt decision_status"
    )
    authorized_repository = _require_string(
        shaped["authorized_repository"], "executor selection authorized_repository"
    )
    authorized_branch = _require_string(
        shaped["authorized_branch"], "executor selection authorized_branch"
    )
    authorized_base_sha = _require_string(
        shaped["authorized_base_sha"], "executor selection authorized_base_sha"
    )
    expected_head_sha = _require_string(
        shaped["expected_head_sha"], "executor selection expected_head_sha"
    )
    current_repository = _require_string(
        shaped["current_repository"], "executor selection current_repository"
    )
    current_branch = _require_string(
        shaped["current_branch"], "executor selection current_branch"
    )
    current_base_sha = _require_string(
        shaped["current_base_sha"], "executor selection current_base_sha"
    )
    current_head_sha = _require_string(
        shaped["current_head_sha"], "executor selection current_head_sha"
    )
    concurrently_active_provider_for_work_unit = _require_string(
        shaped["concurrently_active_provider_for_work_unit"],
        "executor selection concurrently_active_provider_for_work_unit",
    )

    reasons: list[str] = []

    if selected_executor_provider not in EXECUTOR_PROVIDERS:
        reasons.append("UNKNOWN_EXECUTOR_PROVIDER")

    if not _WORK_UNIT_ID_PATTERN.match(work_unit_id):
        reasons.append("WORK_UNIT_ID_MALFORMED")

    if not _GOVERNING_REFERENCE_PATTERN.match(governing_issue):
        reasons.append("GOVERNING_REFERENCE_MALFORMED")

    # Distinguishes a forged or unposted grant from a real, individually addressable comment,
    # exactly as `adoption_record` distinguishes a chat draft from a recorded adoption.
    if not _COMMENT_URL_PATTERN.match(comment_url):
        reasons.append("COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT")

    if receipt_work_unit_id != work_unit_id:
        reasons.append("API_READ_BACK_RECEIPT_WORK_UNIT_ID_MISMATCH")
    if receipt_governing_issue != governing_issue:
        reasons.append("API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH")
    if receipt_selected_executor_provider != selected_executor_provider:
        reasons.append("API_READ_BACK_RECEIPT_SELECTED_EXECUTOR_PROVIDER_MISMATCH")
    if receipt_comment_url != comment_url:
        reasons.append("API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH")
    if receipt_decision_authority != decision_authority:
        reasons.append("API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH")
    if receipt_decision_status != decision_status:
        reasons.append("API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH")

    if decision_authority != HUMAN_AUTHORITY:
        reasons.append("DECISION_AUTHORITY_NOT_HUMAN")
    if decision_status != "RATIFIED":
        reasons.append("DECISION_STATUS_NOT_RATIFIED")

    if authorized_repository != THIS_REPOSITORY:
        reasons.append("AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY")
    if current_repository != authorized_repository:
        reasons.append("REPOSITORY_SCOPE_MISMATCH")
    if current_branch != authorized_branch:
        reasons.append("BRANCH_SCOPE_MISMATCH")

    base_sha_ok = _looks_like_git_sha(authorized_base_sha)
    if not base_sha_ok:
        reasons.append("AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA")
    head_sha_ok = _looks_like_git_sha(expected_head_sha)
    if not head_sha_ok:
        reasons.append("EXPECTED_HEAD_SHA_NOT_A_COMMIT_SHA")
    current_base_sha_ok = _looks_like_git_sha(current_base_sha)
    if not current_base_sha_ok:
        reasons.append("CURRENT_BASE_SHA_NOT_A_COMMIT_SHA")
    current_head_sha_ok = _looks_like_git_sha(current_head_sha)
    if not current_head_sha_ok:
        reasons.append("CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA")

    if base_sha_ok and current_base_sha_ok and authorized_base_sha != current_base_sha:
        reasons.append("BASE_SHA_SCOPE_MISMATCH")
    if head_sha_ok and current_head_sha_ok and expected_head_sha != current_head_sha:
        # New commits landed on the authorized branch since the grant was issued: the grant
        # has gone stale and must be refused rather than silently re-used for a changed world.
        reasons.append("HEAD_SHA_STALE")

    if work_unit_id != invoked_work_unit_id:
        reasons.append("CROSS_WORK_UNIT_REPLAY")

    if concurrently_active_provider_for_work_unit not in ("", selected_executor_provider):
        reasons.append("DUPLICATE_ACTIVE_EXECUTOR_FOR_WORK_UNIT")

    decision = EXECUTOR_SELECTION_REFUSED if reasons else EXECUTOR_SELECTION_ADMITTED
    return {
        "schema_version": SCHEMA_VERSION,
        "work_unit_id": work_unit_id,
        "governing_issue": governing_issue,
        "selected_executor_provider": selected_executor_provider,
        "comment_url": comment_url,
        "decision": decision,
        "decision_reason_codes": sorted(set(reasons)),
    }


#: Every reason code :func:`evaluate_executor_selection` can actually emit, declared
#: explicitly rather than inferred from source shape -- the same discipline GAR-R2-F2 applied
#: to `adoption_record`, and proven the same way by this module's own reachability tests.
EMITTED_REASON_CODES: frozenset[str] = frozenset(
    {
        "UNKNOWN_EXECUTOR_PROVIDER",
        "WORK_UNIT_ID_MALFORMED",
        "GOVERNING_REFERENCE_MALFORMED",
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "API_READ_BACK_RECEIPT_WORK_UNIT_ID_MISMATCH",
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        "API_READ_BACK_RECEIPT_SELECTED_EXECUTOR_PROVIDER_MISMATCH",
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH",
        "DECISION_AUTHORITY_NOT_HUMAN",
        "DECISION_STATUS_NOT_RATIFIED",
        "AUTHORIZED_REPOSITORY_NOT_THIS_REPOSITORY",
        "REPOSITORY_SCOPE_MISMATCH",
        "BRANCH_SCOPE_MISMATCH",
        "AUTHORIZED_BASE_SHA_NOT_A_COMMIT_SHA",
        "EXPECTED_HEAD_SHA_NOT_A_COMMIT_SHA",
        "CURRENT_BASE_SHA_NOT_A_COMMIT_SHA",
        "CURRENT_HEAD_SHA_NOT_A_COMMIT_SHA",
        "BASE_SHA_SCOPE_MISMATCH",
        "HEAD_SHA_STALE",
        "CROSS_WORK_UNIT_REPLAY",
        "DUPLICATE_ACTIVE_EXECUTOR_FOR_WORK_UNIT",
    }
)
