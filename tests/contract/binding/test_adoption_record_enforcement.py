"""Issue #53 (`ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT`): only a SHUKOU semantic
decision that the Structural Advisor has recorded on GitHub, read back through the API, and
identified by its immutable comment URL, may become implementation authority for Claude
Code. This proves the mechanical check for that rule -- the four required negative cases
(a chat draft, unposted text, a reviewed-SHA mismatch, an unverified read-back receipt), the
required positive case, and that the module never performs the network call it is not
allowed to perform.

See `03_BINDING/GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT.md` for the operating guide this
suite proves.
"""

from __future__ import annotations

import ast
from copy import deepcopy
import inspect
from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    ADOPTION_RECORD_ADMITTED,
    ADOPTION_RECORD_REFUSED,
    AdoptionRecordError,
    adoption_record as adoption_record_module,
    evaluate_adoption_record,
)

pytestmark = pytest.mark.contract

_REAL_COMMENT_URL = (
    "https://github.com/manosube/manosube-agent-civilization-os/issues/53#issuecomment-5565102236"
)
_SHA_A = "2a81f782bfaccd72f1e27bbe3378bd5cd3f2e9c5"
_SHA_B = "070c1fa88f7eebce77b38d3ed026f23e500a6e4f"


def _receipt(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "adoption_id": "ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT",
        "governing_issue": "#53",
        "reviewed_sha": _SHA_A,
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
    }
    base.update(overrides)
    return base


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT",
        "governing_issue": "#53",
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_receipt": _receipt(),
        "reviewed_sha": _SHA_A,
        "authorized_target_sha": _SHA_A,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# the required positive case
# --------------------------------------------------------------------------- #


def test_a_complete_verified_adoption_url_with_matching_reviewed_sha_is_admitted() -> None:
    decision = evaluate_adoption_record(_record())
    assert decision["decision"] == ADOPTION_RECORD_ADMITTED
    assert decision["decision_reason_codes"] == []
    assert decision["comment_url"] == _REAL_COMMENT_URL


def test_the_decision_is_deterministic_and_the_input_is_never_mutated() -> None:
    record = _record()
    before = deepcopy(record)
    first = evaluate_adoption_record(record)
    second = evaluate_adoption_record(deepcopy(record))
    assert record == before
    assert first == second


# --------------------------------------------------------------------------- #
# the four required negative cases
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "chat_draft_url",
    [
        "SHUKOU said in chat: implement the governance enforcement",
        "the adoption is whatever we discussed just now",
        "(no URL -- SHUKOU approved this verbally)",
    ],
)
def test_a_chat_draft_is_refused(chat_draft_url: str) -> None:
    decision = evaluate_adoption_record(_record(comment_url=chat_draft_url))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "unposted_url",
    [
        "",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/53",
        "https://github.com/manosube/manosube-agent-civilization-os/issues/53#discussion",
    ],
)
def test_unposted_text_is_refused(unposted_url: str) -> None:
    """An Issue/PR URL with no `#issuecomment-<id>` fragment names a whole, editable,
    ever-changing body -- never one individually addressable, immutable comment."""

    decision = evaluate_adoption_record(_record(comment_url=unposted_url))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


def test_a_reviewed_sha_mismatch_is_refused() -> None:
    decision = evaluate_adoption_record(_record(authorized_target_sha=_SHA_B))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET"]


def test_an_unverified_read_back_receipt_is_refused_even_when_otherwise_complete() -> None:
    """A syntactically real, individually addressable comment URL is not enough on its own --
    the caller must also supply a read-back receipt that actually agrees with the record."""

    empty_receipt = {
        "adoption_id": "",
        "governing_issue": "",
        "reviewed_sha": "",
        "comment_url": "",
        "decision_authority": "",
        "decision_status": "",
    }
    decision = evaluate_adoption_record(_record(api_read_back_receipt=empty_receipt))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert set(decision["decision_reason_codes"]) == {
        "API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH",
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        "API_READ_BACK_RECEIPT_REVIEWED_SHA_MISMATCH",
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH",
    }


# --------------------------------------------------------------------------- #
# every other individual admission condition, proven directly
# --------------------------------------------------------------------------- #


def test_a_non_shukou_decision_authority_is_refused() -> None:
    decision = evaluate_adoption_record(_record(decision_authority="CHATGPT"))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "DECISION_AUTHORITY_NOT_HUMAN" in decision["decision_reason_codes"]


@pytest.mark.parametrize("status", ["DRAFT", "PROPOSED", "SUPERSEDED", ""])
def test_a_non_ratified_decision_status_is_refused(status: str) -> None:
    decision = evaluate_adoption_record(_record(decision_status=status))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "DECISION_STATUS_NOT_RATIFIED" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "bad_sha", ["", "not-a-sha", "abc123", "g" * 40, _SHA_A + "x", _SHA_A[:-1]]
)
def test_a_malformed_reviewed_sha_is_refused(bad_sha: str) -> None:
    decision = evaluate_adoption_record(_record(reviewed_sha=bad_sha))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "REVIEWED_SHA_NOT_A_COMMIT_SHA" in decision["decision_reason_codes"]


@pytest.mark.parametrize(
    "bad_adoption_id",
    ["", "not shaped like an adoption id", "adopt_lowercase_is_wrong", "ADOPTION_MISSING_PREFIX"],
)
def test_a_malformed_adoption_id_is_refused(bad_adoption_id: str) -> None:
    decision = evaluate_adoption_record(_record(adoption_id=bad_adoption_id))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "ADOPTION_ID_MALFORMED" in decision["decision_reason_codes"]


@pytest.mark.parametrize("bad_reference", ["", "53", "Issue 53", "#", "# 53", "issue-53"])
def test_a_malformed_governing_reference_is_refused(bad_reference: str) -> None:
    decision = evaluate_adoption_record(_record(governing_issue=bad_reference))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "GOVERNING_REFERENCE_MALFORMED" in decision["decision_reason_codes"]


# --------------------------------------------------------------------------- #
# GAR-R2-F1 (Issue #53 comment 5565703135): governing_issue (semantic jurisdiction)
# and comment_url (recording location) are separate contexts. The read-back
# receipt binds the record to what its own cited API read-back actually showed --
# never to the Issue/PR number that happens to host the comment.
# --------------------------------------------------------------------------- #


def test_a_governing_issue_recorded_through_a_pull_request_comment_is_admitted() -> None:
    """The required GAR-R2-F1 positive case: an adoption governing Issue #53, recorded
    through a comment on a *different* Issue or Pull Request (here, PR #56), is admitted in
    full -- not merely un-refused -- once the read-back receipt itself agrees with the
    record. GAR-R1's superseded rule would have refused this outright."""

    pr_comment_url = (
        "https://github.com/manosube/manosube-agent-civilization-os/pull/56#issuecomment-1"
    )
    record = _record(
        comment_url=pr_comment_url,
        governing_issue="#53",
        api_read_back_receipt=_receipt(comment_url=pr_comment_url, governing_issue="#53"),
    )
    decision = evaluate_adoption_record(record)
    assert decision["decision"] == ADOPTION_RECORD_ADMITTED
    assert decision["decision_reason_codes"] == []


@pytest.mark.parametrize(
    "field,mismatched_value,reason_code",
    [
        (
            "adoption_id",
            "ADOPT_SOMETHING_ELSE_ENTIRELY",
            "API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH",
        ),
        ("governing_issue", "#99", "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH"),
        ("reviewed_sha", _SHA_B, "API_READ_BACK_RECEIPT_REVIEWED_SHA_MISMATCH"),
        (
            "comment_url",
            "https://github.com/manosube/manosube-agent-civilization-os/issues/999#issuecomment-1",
            "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        ),
        ("decision_authority", "CHATGPT", "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH"),
        ("decision_status", "DRAFT", "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH"),
    ],
)
def test_a_receipt_field_disagreeing_with_the_declared_record_is_refused(
    field: str, mismatched_value: str, reason_code: str
) -> None:
    """A record cannot relabel a real, verified receipt as authority for a different
    adoption, governing unit, reviewed SHA, comment, decision authority, or decision status --
    each field is bound independently, so a single disagreeing field is refused for exactly
    that field."""

    decision = evaluate_adoption_record(
        _record(api_read_back_receipt=_receipt(**{field: mismatched_value}))
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == [reason_code]


# --------------------------------------------------------------------------- #
# GAR-R3-F1 (Issue #53 comment 5566075546): comment_url is scoped to this
# repository. A receipt for a comment hosted in a different repository must
# never authorize work here, even when the receipt itself agrees with a
# record that also names that foreign repository.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "foreign_url",
    [
        "https://github.com/manosube/some-other-repository/issues/53#issuecomment-1",
        "https://github.com/someone-else/manosube-agent-civilization-os/issues/53#issuecomment-1",
        "https://github.com/someone-else/some-other-repository/issues/53#issuecomment-1",
    ],
)
def test_a_foreign_repository_comment_url_is_refused_even_when_the_receipt_agrees(
    foreign_url: str,
) -> None:
    """A verified-looking receipt for another repository must never authorize work here --
    the record is refused for exactly the same reason a chat draft is: it does not name a
    verifiable comment in *this* repository, whatever a matching receipt might claim."""

    decision = evaluate_adoption_record(
        _record(comment_url=foreign_url, api_read_back_receipt=_receipt(comment_url=foreign_url))
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT"]


# --------------------------------------------------------------------------- #
# GAR-R2: every declared reason code is actually reachable
# --------------------------------------------------------------------------- #
#
# One crafted record per reason code, isolated so it is the *only* failure -- proving the
# allowlist a route-drift guard elsewhere in this suite trusts is neither wider nor narrower
# than what this evaluator can actually emit.

_REACHABILITY_CASES: tuple[tuple[str, dict[str, Any]], ...] = (
    (
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        {"comment_url": "", "api_read_back_receipt": _receipt(comment_url="")},
    ),
    (
        "ADOPTION_ID_MALFORMED",
        {"adoption_id": "", "api_read_back_receipt": _receipt(adoption_id="")},
    ),
    (
        "GOVERNING_REFERENCE_MALFORMED",
        {"governing_issue": "", "api_read_back_receipt": _receipt(governing_issue="")},
    ),
    (
        "API_READ_BACK_RECEIPT_ADOPTION_ID_MISMATCH",
        {"api_read_back_receipt": _receipt(adoption_id="ADOPT_SOMETHING_ELSE")},
    ),
    (
        "API_READ_BACK_RECEIPT_GOVERNING_ISSUE_MISMATCH",
        {"api_read_back_receipt": _receipt(governing_issue="#99")},
    ),
    (
        "API_READ_BACK_RECEIPT_REVIEWED_SHA_MISMATCH",
        {"api_read_back_receipt": _receipt(reviewed_sha=_SHA_B)},
    ),
    (
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        {
            "api_read_back_receipt": _receipt(
                comment_url="https://github.com/manosube/manosube-agent-civilization-os/issues/999#issuecomment-1"
            )
        },
    ),
    (
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        {"api_read_back_receipt": _receipt(decision_authority="CHATGPT")},
    ),
    (
        "API_READ_BACK_RECEIPT_DECISION_STATUS_MISMATCH",
        {"api_read_back_receipt": _receipt(decision_status="DRAFT")},
    ),
    (
        "DECISION_AUTHORITY_NOT_HUMAN",
        {
            "decision_authority": "CHATGPT",
            "api_read_back_receipt": _receipt(decision_authority="CHATGPT"),
        },
    ),
    (
        "DECISION_STATUS_NOT_RATIFIED",
        {"decision_status": "DRAFT", "api_read_back_receipt": _receipt(decision_status="DRAFT")},
    ),
    (
        "REVIEWED_SHA_NOT_A_COMMIT_SHA",
        {"reviewed_sha": "not-a-sha", "api_read_back_receipt": _receipt(reviewed_sha="not-a-sha")},
    ),
    ("AUTHORIZED_TARGET_SHA_NOT_A_COMMIT_SHA", {"authorized_target_sha": "not-a-sha"}),
    ("REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET", {"authorized_target_sha": _SHA_B}),
)


@pytest.mark.parametrize(
    "reason_code,overrides", _REACHABILITY_CASES, ids=[case[0] for case in _REACHABILITY_CASES]
)
def test_every_declared_reason_code_is_reachable(
    reason_code: str, overrides: dict[str, Any]
) -> None:
    decision = evaluate_adoption_record(_record(**overrides))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == [reason_code]


def test_the_reachability_matrix_covers_every_declared_reason_code() -> None:
    """Direction one of GAR-R2-F2's bidirectional proof: every code this module declares is
    reachable -- proven dynamically above, checked here against the declared surface itself
    rather than only against whatever the crafted cases happen to cover."""

    covered = {reason_code for reason_code, _overrides in _REACHABILITY_CASES}
    assert covered == adoption_record_module.EMITTED_REASON_CODES


def test_every_emittable_reason_code_is_declared() -> None:
    """Direction two: nothing this module's own source can actually emit escapes the
    declared surface. Self-contained AST extraction (a string literal ``.append()``-ed onto
    ``reasons`` -- the only shape this module's own reason codes reach their caller through,
    it has no ``_verdict`` helper or ``return``-based indirection) rather than importing
    another test module's private implementation."""

    tree = ast.parse(inspect.getsource(adoption_record_module))
    emittable: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr != "append":
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                emittable.add(arg.value)
    assert emittable == adoption_record_module.EMITTED_REASON_CODES


def test_multiple_failures_are_reported_together() -> None:
    decision = evaluate_adoption_record(_record(comment_url="", decision_authority="CHATGPT"))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert set(decision["decision_reason_codes"]) == {
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "API_READ_BACK_RECEIPT_COMMENT_URL_MISMATCH",
        "API_READ_BACK_RECEIPT_DECISION_AUTHORITY_MISMATCH",
        "DECISION_AUTHORITY_NOT_HUMAN",
    }


# --------------------------------------------------------------------------- #
# unreadable records raise, they are never silently refused or admitted
# --------------------------------------------------------------------------- #


def test_an_unknown_key_raises() -> None:
    with pytest.raises(AdoptionRecordError, match="unknown keys"):
        evaluate_adoption_record(_record(extra_field="not part of the schema"))


@pytest.mark.parametrize("missing_key", list(_record().keys()))
def test_a_missing_required_key_raises(missing_key: str) -> None:
    record = _record()
    del record[missing_key]
    with pytest.raises(AdoptionRecordError, match="omits required keys"):
        evaluate_adoption_record(record)


def test_a_non_object_record_raises() -> None:
    with pytest.raises(AdoptionRecordError):
        evaluate_adoption_record("this is not even a mapping")  # type: ignore[arg-type]


def test_an_unsupported_schema_version_raises() -> None:
    with pytest.raises(AdoptionRecordError, match="schema_version"):
        evaluate_adoption_record(_record(schema_version="99.9"))


def test_a_non_object_receipt_raises() -> None:
    """``"true"`` is not a receipt -- a string that merely claims confirmation must not be
    accepted as the structured receipt itself."""

    with pytest.raises(AdoptionRecordError, match="api_read_back_receipt"):
        evaluate_adoption_record(_record(api_read_back_receipt="true"))


def test_a_receipt_carrying_an_unknown_key_raises() -> None:
    with pytest.raises(AdoptionRecordError, match="unknown keys"):
        evaluate_adoption_record(_record(api_read_back_receipt=_receipt(extra="not part of it")))


@pytest.mark.parametrize("missing_key", list(_receipt().keys()))
def test_a_receipt_missing_a_required_key_raises(missing_key: str) -> None:
    receipt = _receipt()
    del receipt[missing_key]
    with pytest.raises(AdoptionRecordError, match="omits required keys"):
        evaluate_adoption_record(_record(api_read_back_receipt=receipt))


@pytest.mark.parametrize("field", list(_receipt().keys()))
def test_a_non_string_receipt_field_raises(field: str) -> None:
    with pytest.raises(AdoptionRecordError):
        evaluate_adoption_record(_record(api_read_back_receipt=_receipt(**{field: 12345})))


@pytest.mark.parametrize("field", ["comment_url", "adoption_id", "reviewed_sha"])
def test_a_non_string_field_raises(field: str) -> None:
    with pytest.raises(AdoptionRecordError):
        evaluate_adoption_record(_record(**{field: 12345}))


# --------------------------------------------------------------------------- #
# the boundary: no network call, no token, no secret, ever
# --------------------------------------------------------------------------- #


def test_the_module_source_contains_no_network_or_credential_surface() -> None:
    source = inspect.getsource(adoption_record_module)
    forbidden = (
        "requests",
        "urllib",
        "httpx",
        "socket",
        "http.client",
        "GITHUB_TOKEN",
        "token=",
        "Authorization",
        "os.environ",
        "getenv",
    )
    for term in forbidden:
        assert term not in source, term


def test_the_module_imports_nothing_beyond_the_standard_library_and_its_own_errors() -> None:
    tree = ast.parse(inspect.getsource(adoption_record_module))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert modules <= {"__future__", "copy", "re", "typing", "errors"}


def test_evaluate_adoption_record_never_writes_a_file() -> None:
    tree = ast.parse(inspect.getsource(adoption_record_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            assert name not in ("open", "write_text", "write_bytes")
