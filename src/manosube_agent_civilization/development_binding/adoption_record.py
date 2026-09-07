"""The Governance Adoption Record: mechanical enforcement of an already-adopted rule.

`CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` sections 3 and 3.1 already state the rule this
module enforces: an external finding, and by the same reasoning an implementation
instruction, becomes authority only through an explicit SHUKOU adoption record, bound to its
exact observation. What was missing was a way to answer, mechanically, whether a *specific*
instruction actually carries one -- the same gap `development_binding.policy` closed for the
ratified role/state policy itself (`SHAPE VALIDATED != CONTENT PINNED`), applied here to the
instruction that authorizes a work unit in the first place rather than to the policy that
governs how the work unit moves once authorized.

Issue #53 (`ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT`) adopted the mechanical rule this
module evaluates: only a SHUKOU semantic decision that the Structural Advisor has *recorded
on GitHub*, that has been *read back through the API*, and that carries the resulting
*immutable comment URL*, may become implementation authority for Claude Code. A chat draft,
an unposted paragraph, or a URL nobody has actually read back through the API is not that --
however complete it otherwise looks.

**What this module is not.** It performs no network call, holds no GitHub token or
credential, and calls no GitHub API itself -- see `03_BINDING/
GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT.md` and the adoption's own explicit boundary. The
``api_read_back_receipt`` field this module requires is the caller's own structured claim of
what the read-back already showed (out of band, exactly as every adoption cited in this
repository's own commit and PR history was independently confirmed before use) -- this
module can prove that claim is *present, well-shaped, and internally consistent with the
record it accompanies*, never that the remote comment currently exists or currently reads as
claimed. A local, offline test can accordingly prove admission or refusal of a *recorded*
instruction; it cannot prove, and never claims to prove, current remote GitHub state
(`RUNTIME_ENFORCEMENT_IMPLEMENTED=false`, the same non-claim
`CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` section 9 already makes for the ratified policy
this module extends).

Following this repository's own admission-grammar convention (`authority.conformance`,
`authority.verifier_selection`): an **unreadable** record -- the wrong Python shape, a
missing required key, an unknown key -- raises :class:`~.errors.AdoptionRecordError`, since
there is no admission question to answer. A **readable-but-insufficient** record -- a
present-but-empty URL, a read-back receipt that does not match what the record itself
declares, a reviewed SHA that does not match the work unit it claims to authorize -- is never
an exception; it is the decision ``ADOPTION_RECORD_REFUSED``, with the specific reason codes
this module can name.

Structural Review Round 1 (GAR-R1-F1, Issue #53 comment 5565302174) adopted, and Round 2
(GAR-R2-F1, Issue #53 comment 5565703135) *superseded*, a binding between ``governing_issue``
and the Issue/Pull Request number embedded in ``comment_url``'s own path. Round 1's rule --
that the two numbers must be identical -- was itself wrong: a governing Issue may legitimately
be recorded through a comment on a *different* Issue or Pull Request (this very correction
was recorded as a comment on Issue #53 while governing PR #56's own implementation; an
adoption governing Issue #53 could equally be recorded as a comment on PR #56). ``governing_
issue`` (which unit this adoption semantically governs) and ``comment_url`` (where it happens
to have been recorded) are separate contexts, and this module no longer conflates them.

What Round 2 introduces instead is a structured **read-back receipt**
(``api_read_back_receipt``): the caller's own claim of what ``adoption_id``, ``governing_
issue``, ``reviewed_sha``, and ``comment_url`` the independent API read-back actually showed,
checked field-by-field for exact agreement with the record's own top-level declared values of
the same names. A receipt that disagrees with even one declared field -- including an absent
or empty receipt, which disagrees with every non-empty field it was compared against --
proves the record and its own supporting evidence are not describing the same thing, and is
refused for exactly the field(s) that disagree. This is the one binding this module can prove
offline: not that the comment *hosting* the record and the Issue it *governs* share a number,
but that what the record says and what its own cited read-back showed are the same claim.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any

from .errors import AdoptionRecordError

SCHEMA_VERSION = "0.1"

#: Named ``ADOPTION_RECORD_*`` rather than the bare ``ADMITTED``/``REFUSED`` this module's
#: own docstring otherwise uses, because this package already exports a bare ``REFUSED``
#: from :mod:`.evaluation` -- a second module-level ``REFUSED`` would silently shadow it in
#: ``development_binding/__init__.py``. Distinguishing the two vocabularies by name is a
#: smaller coupling than importing one from the other.
ADOPTION_RECORD_ADMITTED = "ADOPTION_RECORD_ADMITTED"
ADOPTION_RECORD_REFUSED = "ADOPTION_RECORD_REFUSED"
DECISIONS: frozenset[str] = frozenset({ADOPTION_RECORD_ADMITTED, ADOPTION_RECORD_REFUSED})

#: The sole authority this module ever admits an instruction on behalf of. Matches
#: ``development_binding.policy.HUMAN_AUTHORITY`` by value rather than by import, so this
#: module stays a self-contained extension of the same owner rather than a second one that
#: happens to agree today.
HUMAN_AUTHORITY = "SHUKOU"

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "adoption_id",
    "governing_issue",
    "comment_url",
    "decision_authority",
    "decision_status",
    "api_read_back_receipt",
    "reviewed_sha",
    "authorized_target_sha",
)

#: The read-back receipt's own closed shape (GAR-R2-F1) -- the same four field names as the
#: record's own top-level declarations they are checked against, so the binding below is a
#: plain, named field-by-field comparison rather than a derived or parsed relationship.
RECEIPT_KEYS: frozenset[str] = frozenset(
    {"adoption_id", "governing_issue", "reviewed_sha", "comment_url"}
)

#: A GitHub Issue or Pull Request comment URL, anchored to its own ``#issuecomment-<id>``
#: fragment -- the one part of a GitHub URL that names an individual, immutable comment
#: rather than a whole, editable, ever-changing Issue or PR body. A URL without this
#: fragment might be real, but it names a moving target, not a recorded decision.
_COMMENT_URL_PATTERN = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/(?:issues|pull)/[0-9]+#issuecomment-[0-9]+$"
)

#: A Governance Adoption identifier: non-empty, and shaped like every adoption this
#: repository has actually recorded (``ADOPT_...``). This module cannot verify offline that
#: the string names the *correct* adoption -- that is exactly what the read-back receipt
#: below is for -- but an empty or non-``ADOPT_``-shaped identifier is never that, whatever
#: else about the record is correct.
_ADOPTION_ID_PATTERN = re.compile(r"^ADOPT_[A-Z0-9_]+$")

#: A governing Issue or Pull Request reference, e.g. ``#53``.
_GOVERNING_REFERENCE_PATTERN = re.compile(r"^#[0-9]+$")


def _looks_like_git_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) in (40, 64)
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


def _require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AdoptionRecordError(f"{context} is not an object: {type(value).__name__}")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AdoptionRecordError(f"{context} is not a string: {type(value).__name__}")
    return value


def _require_request_shape(record: Any) -> dict[str, Any]:
    shaped = _require_object(record, "adoption record")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise AdoptionRecordError(f"adoption record carries unknown keys: {sorted(unknown)}")
    missing = set(REQUIRED_REQUEST_KEYS) - set(shaped)
    if missing:
        raise AdoptionRecordError(f"adoption record omits required keys: {sorted(missing)}")
    version = _require_string(shaped["schema_version"], "adoption record schema_version")
    if version != SCHEMA_VERSION:
        raise AdoptionRecordError(f"unsupported adoption record schema_version: {version!r}")
    return shaped


def _require_receipt_shape(value: Any, context: str) -> dict[str, Any]:
    shaped = _require_object(value, context)
    unknown = set(shaped) - RECEIPT_KEYS
    if unknown:
        raise AdoptionRecordError(f"{context} carries unknown keys: {sorted(unknown)}")
    missing = RECEIPT_KEYS - set(shaped)
    if missing:
        raise AdoptionRecordError(f"{context} omits required keys: {sorted(missing)}")
    return shaped


def evaluate_adoption_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Adoption Record Decision for one exact record.

    *record* is never mutated. The same record always produces the same decision and the
    same ``reason_codes`` -- this module reads a clock and a network exactly as much as
    :mod:`manosube_agent_civilization.authority` does, which is to say never.
    """

    shaped = _require_request_shape(deepcopy(record))

    adoption_id = _require_string(shaped["adoption_id"], "adoption record adoption_id")
    governing_issue = _require_string(shaped["governing_issue"], "adoption record governing_issue")
    comment_url = _require_string(shaped["comment_url"], "adoption record comment_url")
    decision_authority = _require_string(
        shaped["decision_authority"], "adoption record decision_authority"
    )
    decision_status = _require_string(shaped["decision_status"], "adoption record decision_status")
    receipt = _require_receipt_shape(
        shaped["api_read_back_receipt"], "adoption record api_read_back_receipt"
    )
    receipt_adoption_id = _require_string(
        receipt["adoption_id"], "adoption record api_read_back_receipt adoption_id"
    )
    receipt_governing_issue = _require_string(
        receipt["governing_issue"], "adoption record api_read_back_receipt governing_issue"
    )
    receipt_reviewed_sha = _require_string(
        receipt["reviewed_sha"], "adoption record api_read_back_receipt reviewed_sha"
    )
    receipt_comment_url = _require_string(
        receipt["comment_url"], "adoption record api_read_back_receipt comment_url"
    )
    reviewed_sha = _require_string(shaped["reviewed_sha"], "adoption record reviewed_sha")
    authorized_target_sha = _require_string(
        shaped["authorized_target_sha"], "adoption record authorized_target_sha"
    )

    reasons: list[str] = []

    # Distinguishes a chat draft or an unposted paragraph (no real comment exists at all)
    # from a real, individually addressable GitHub comment.
    if not _COMMENT_URL_PATTERN.match(comment_url):
        reasons.append("COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT")

    if not _ADOPTION_ID_PATTERN.match(adoption_id):
        reasons.append("ADOPTION_ID_MALFORMED")

    if not _GOVERNING_REFERENCE_PATTERN.match(governing_issue):
        reasons.append("GOVERNING_REFERENCE_MALFORMED")

    # GAR-R2-F1: the read-back receipt is the caller's own structured claim of what the
    # independent API read-back actually showed. Bound field-by-field against the record's
    # own declared fields of the same name -- never against comment_url's own hosting
    # Issue/PR number (GAR-R1's superseded approach; a governing Issue may legitimately be
    # recorded through a comment on a different Issue or Pull Request). An absent or empty
    # receipt disagrees with every non-empty declared field, so "not actually confirmed"
    # needs no separate boolean or reason code -- it surfaces as these same mismatches.
    if receipt_adoption_id != adoption_id:
        reasons.append("API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH")
    if receipt_governing_issue != governing_issue:
        reasons.append("API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH")
    if receipt_reviewed_sha != reviewed_sha:
        reasons.append("API_READ_BACK_RECEIPT_REVIEWED_SHA_MISMATCH")
    if receipt_comment_url != comment_url:
        reasons.append("API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH")

    if decision_authority != HUMAN_AUTHORITY:
        reasons.append("DECISION_AUTHORITY_NOT_HUMAN")

    if decision_status != "RATIFIED":
        reasons.append("DECISION_STATUS_NOT_RATIFIED")

    if not _looks_like_git_sha(reviewed_sha):
        reasons.append("REVIEWED_SHA_NOT_A_COMMIT_SHA")
    if not _looks_like_git_sha(authorized_target_sha):
        reasons.append("AUTHORIZED_TARGET_SHA_NOT_A_COMMIT_SHA")
    if (
        "REVIEWED_SHA_NOT_A_COMMIT_SHA" not in reasons
        and "AUTHORIZED_TARGET_SHA_NOT_A_COMMIT_SHA" not in reasons
        and reviewed_sha != authorized_target_sha
    ):
        reasons.append("REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET")

    decision = ADOPTION_RECORD_REFUSED if reasons else ADOPTION_RECORD_ADMITTED
    return {
        "schema_version": SCHEMA_VERSION,
        "adoption_id": adoption_id,
        "governing_issue": governing_issue,
        "comment_url": comment_url,
        "decision": decision,
        "decision_reason_codes": sorted(set(reasons)),
    }


#: Every reason code :func:`evaluate_adoption_record` can actually emit, declared explicitly
#: rather than inferred from source shape (GAR-R2-F2, Issue #53 comment 5565703135). The sole
#: source of truth the route-drift guard in ``test_active_document_terminal_state.py`` and
#: this module's own reachability tests read from -- ``test_adoption_record_enforcement.py``
#: statically proves this set is neither wider nor narrower than what this module's own
#: source can actually emit.
EMITTED_REASON_CODES: frozenset[str] = frozenset(
    {
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "ADOPTION_ID_MALFORMED",
        "GOVERNING_REFERENCE_MALFORMED",
        "API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH",
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        "API_READ_BACK_RECEIPT_REVIEWED_SHA_MISMATCH",
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        "DECISION_AUTHORITY_NOT_HUMAN",
        "DECISION_STATUS_NOT_RATIFIED",
        "REVIEWED_SHA_NOT_A_COMMIT_SHA",
        "AUTHORIZED_TARGET_SHA_NOT_A_COMMIT_SHA",
        "REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET",
    }
)
