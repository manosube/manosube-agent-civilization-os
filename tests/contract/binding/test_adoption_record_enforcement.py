"""Issue #53 (`ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT`): only a SHUKOU semantic
decision that the Structural Advisor has recorded on GitHub, read back through the API, and
identified by its immutable comment URL, may become implementation authority for Claude
Code. This proves the mechanical check for that rule -- the four required negative cases
(a chat draft, unposted text, a reviewed-SHA mismatch, an unverified URL), the required
positive case, and that the module never performs the network call it is not allowed to
perform.

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


def _record(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "adoption_id": "ADOPT_GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT",
        "governing_issue": "#53",
        "comment_url": _REAL_COMMENT_URL,
        "decision_authority": "SHUKOU",
        "decision_status": "RATIFIED",
        "api_read_back_confirmed": True,
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
    decision = evaluate_adoption_record(
        _record(comment_url=chat_draft_url, api_read_back_confirmed=False)
    )
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

    decision = evaluate_adoption_record(
        _record(comment_url=unposted_url, api_read_back_confirmed=False)
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT" in decision["decision_reason_codes"]


def test_a_reviewed_sha_mismatch_is_refused() -> None:
    decision = evaluate_adoption_record(_record(authorized_target_sha=_SHA_B))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["REVIEWED_SHA_DOES_NOT_MATCH_AUTHORIZED_TARGET"]


def test_an_unverified_url_is_refused_even_when_otherwise_complete() -> None:
    """A syntactically real, individually addressable comment URL is not enough on its
    own -- the caller must also claim the API read-back that confirms it actually
    happened."""

    decision = evaluate_adoption_record(_record(api_read_back_confirmed=False))
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert decision["decision_reason_codes"] == ["API_READ_BACK_NOT_CONFIRMED"]


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


def test_multiple_failures_are_reported_together() -> None:
    decision = evaluate_adoption_record(
        _record(comment_url="", api_read_back_confirmed=False, decision_authority="CHATGPT")
    )
    assert decision["decision"] == ADOPTION_RECORD_REFUSED
    assert set(decision["decision_reason_codes"]) == {
        "COMMENT_URL_NOT_A_VERIFIABLE_GITHUB_COMMENT",
        "API_READ_BACK_NOT_CONFIRMED",
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


def test_a_non_boolean_api_read_back_confirmed_raises() -> None:
    """``"true"`` is not ``True`` -- a string that merely looks like the claim must not be
    accepted as the claim itself."""

    with pytest.raises(AdoptionRecordError, match="api_read_back_confirmed"):
        evaluate_adoption_record(_record(api_read_back_confirmed="true"))


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
