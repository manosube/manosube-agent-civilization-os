"""The one Change deriver: what authorized mutation does this decision permit?

```text
RAW CHANGE REQUEST
→ REQUEST ADMISSION
→ AUTHORITY EVALUATION BY THE CANONICAL OWNER
→ PROVENANCE BY REPRODUCTION
→ PERMISSION
→ CANONICAL CHANGE
```

Change **describes** an authorized mutation. It does not perform one. This module reads no
clock, no filesystem, no network, no environment, no GitHub and no conversation; it computes
a record from the records it was given, and the absence of any API through which it could do
more is the evidence for that, not a promise in this docstring.

The permission question is answered by :func:`evaluate_authority` and by nothing here.
Change's only judgement is whether the decision in front of it is **genuine** and permits
*this exact* Change. Re-deciding permission here would be a second Authority, and a second
Authority is one that can disagree with the first.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.authority import (
    AUTONOMOUS,
    evaluate_authority,
)
from manosube_agent_civilization.authority.errors import (
    AuthorityError,
    StaleAuthorityInputError,
)
from manosube_agent_civilization.authority.identity import (
    decision_id,
    decision_semantic_fingerprint,
)
from manosube_agent_civilization.difference.admissibility import require_object
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.state.errors import CanonicalizationError

from .errors import (
    AuthorityProvenanceError,
    ChangeError,
    ChangeValidationError,
    StaleChangeError,
    UnauthorizedChangeError,
)
from .identity import change_id, change_semantic_fingerprint, idempotency_key

AUTHORITY_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "authority/"
CHANGE_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "change/"
SCHEMA_VERSION = "0.1"

#: The one status this engine emits. ``KERNEL_CONSTITUTION.md`` 第25条 fixes seven, and the
#: invariants say a Change *becomes* AUTHORIZED once Authority has evaluated it. The other
#: six belong to execution and to a lifecycle owner v0.1 does not have: RUNNING, EXECUTED and
#: FAILED are things only an executor can report, and REJECTED and STALE are refusals, which
#: this engine raises rather than records. Emitting a record that says a Change was rejected
#: would be emitting a Change for a mutation that may not occur.
AUTHORIZED = "AUTHORIZED"

#: Every key a Change request may carry. Closed, for the reason ``AUTHORITY_CONTRACT.md`` §4
#: gives: an ignored key is still a channel.
#:
#: There are two, and the pairing is the point. ``authority_request`` carries the **real
#: inputs** the canonical evaluator needs -- the Difference, the action, the scope, the State,
#: the rules, the prohibitions, the approvals, the evaluation time -- so that Change can ask
#: Authority rather than believe a caller. ``authority_decision`` is the caller's **claim**
#: about what Authority answered, and it is checked against the answer, never trusted as one.
#:
#: What is deliberately *absent* is a way to supply the Difference, the action, the scope or
#: the project beside the decision. Every one of those is read from the decision Authority
#: actually returned, so a pair of them cannot disagree -- the disagreement is not refused,
#: it is inexpressible.
REQUIRED_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "authority_request",
        "authority_decision",
    }
)

#: Every key a bound Authority decision must carry, and no other. Public because the
#: totality generator builds its cases from this set rather than from a remembered list: a
#: key added to the decision record is then covered without anyone remembering to add it.
DECISION_REQUIRED_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "authority_decision_id",
        "project_id",
        "difference_ref",
        "requested_action",
        "requested_scope",
        "evaluated_state_revision",
        "evaluated_state_fingerprint",
        "resolved_rule_ref",
        "prohibition_refs",
        "approval_ref",
        "excluding_approval_refs",
        "decision",
        "decision_reason_codes",
        "decision_semantic_fingerprint",
    }
)


def _validate(record: dict[str, Any], schema_name: str, base: str, context: str) -> None:
    """Validate against the canonical schema, in Change's error vocabulary."""

    try:
        _validate_canonical_record(record, schema_name, base=base)
    except ValueError as error:
        raise ChangeValidationError(f"{context}: {error}") from error


def _require_request_shape(request: Any) -> dict[str, Any]:
    """Return the request once its key set is exactly the declared one."""

    shaped = require_object(request, "change request")
    unknown = set(shaped) - REQUIRED_REQUEST_KEYS
    if unknown:
        raise ChangeError(f"change request carries unknown keys: {sorted(unknown)}")
    missing = REQUIRED_REQUEST_KEYS - set(shaped)
    if missing:
        raise ChangeError(f"change request omits required keys: {sorted(missing)}")
    if shaped["schema_version"] != SCHEMA_VERSION:
        raise ChangeError(
            f"change request declares an unsupported schema_version: {shaped['schema_version']!r}"
        )
    return shaped


def _admit_claim(value: Any) -> dict[str, Any]:
    """Return the caller's claimed decision once it is at least a well-formed one.

    This is admission, not verification. It exists so that a malformed *claim* is refused
    with a diagnostic about its shape rather than surfacing as a bare inequality against the
    reproduced decision, which would tell a caller nothing about what is wrong with theirs.

    Recomputing the claim's own address is part of that shape check and **not** evidence of
    anything: ``decision_id`` is a public pure function, so a caller who never called the
    evaluator can satisfy it. That is precisely the defect this module now closes, and the
    reason this function stops where it does. Provenance is established in :func:`_derive`,
    by reproduction, and nowhere else.
    """

    decision = require_object(value, "claimed Authority decision")
    version = decision.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ChangeError(
            f"claimed Authority decision declares an unsupported schema_version: {version!r}"
        )
    unknown = set(decision) - DECISION_REQUIRED_KEYS
    if unknown:
        raise ChangeError(f"claimed Authority decision carries unknown keys: {sorted(unknown)}")
    _validate(
        decision, "authority.schema.json", AUTHORITY_SCHEMA_BASE, "claimed Authority decision"
    )
    declared = decision["authority_decision_id"]
    recomputed = decision_id(decision)
    if declared != recomputed:
        raise ChangeError(
            "claimed Authority decision identity does not match the decision it names: "
            f"{declared!r} != {recomputed!r}"
        )
    declared_fingerprint = decision["decision_semantic_fingerprint"]
    recomputed_fingerprint = decision_semantic_fingerprint(decision)
    if declared_fingerprint != recomputed_fingerprint:
        raise ChangeError(
            "claimed Authority decision fingerprint does not match its own meaning: "
            f"{declared_fingerprint!r} != {recomputed_fingerprint!r}"
        )
    return decision


def derive_change(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Change for one exactly-authorized request.

    The returned record is schema-valid and content-addressed: the same authorized change
    always produces the same ``change_id``. *request* is never mutated.

    Every refusal leaves here as a :class:`ChangeError`. Three owners one layer down speak
    their own vocabularies -- readability answers in ``DifferenceError`` (ADR-0025), canonical
    serialization in ``CanonicalizationError``, and the evaluator Change calls rather than
    reimplements answers in ``AuthorityError`` -- and asking all three is right. Letting any
    of them escape would make a caller of *Change* catch a *Difference*, a *State* or an
    *Authority* error to learn that its own request was malformed. The decisions are
    delegated. The boundary's error vocabulary is not.

    Staleness is the one Authority answer that keeps its own meaning on the way out.
    ``KERNEL_CONSTITUTION.md`` 第26条 requires a stale Change to be *blocked*, and a caller
    told only "refused" cannot tell a human to re-observe. Authority detects it; Change names
    it :class:`StaleChangeError`.
    """

    try:
        return _derive(request)
    except StaleAuthorityInputError as error:
        raise StaleChangeError(str(error)) from error
    except (AuthorityError, DifferenceError, CanonicalizationError) as error:
        raise ChangeError(str(error)) from error


def _derive(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    # --- authority ------------------------------------------------------------ #
    #
    # The single evaluator, on the caller's real inputs. Change does not decide permission
    # here and does not re-implement any part of deciding it; it asks the one owner. Every
    # question Authority answers on the way -- is the Difference admissible, is the scope
    # enumerated, is the State the one the Difference observed, does a rule or an exact
    # approval reach this action -- is answered once, by Authority, for both of us.
    #
    # This runs **before** the claim is admitted, and the order is deliberate. If admitting
    # the claim could refuse first, the shape of a caller-supplied value would decide whether
    # the canonical evaluation happens at all -- which is the same defect as trusting the
    # claim itself, wearing a different hat. Authority always runs. The claim is then
    # compared against what it said, and cannot pre-empt it.
    reproduced = evaluate_authority(shaped["authority_request"])
    claimed = _admit_claim(shaped["authority_decision"])

    # --- provenance ----------------------------------------------------------- #
    #
    # This is the check whose absence let a synthetic decision through. `decision_id` and
    # `decision_semantic_fingerprint` are public pure functions: a caller who never called
    # the evaluator can build an AUTONOMOUS decision citing a rule that exists nowhere and
    # re-hash it into perfect internal agreement. Internal agreement is what those functions
    # measure, and it is not provenance.
    #
    # Reproduction is. The decision is compared whole -- not by address alone, because an
    # address is a digest over a projection, and a projection is by construction not the
    # record. Two records agreeing on every field they are addressed by can still differ.
    if claimed["authority_decision_id"] != reproduced["authority_decision_id"]:
        raise AuthorityProvenanceError(
            "claimed Authority decision is not the decision the canonical evaluator produces "
            "from these inputs: "
            f"{claimed['authority_decision_id']!r} != {reproduced['authority_decision_id']!r}"
        )
    if claimed != reproduced:
        differing = sorted(
            key for key in DECISION_REQUIRED_KEYS if claimed.get(key) != reproduced.get(key)
        )
        raise AuthorityProvenanceError(
            "claimed Authority decision differs from the one the canonical evaluator produces "
            f"from these inputs, at: {differing}"
        )

    # --- permission ----------------------------------------------------------- #
    #
    # One value permits a Change, and it is the one Authority uses to say so. An exactly
    # approved decision *is* AUTONOMOUS -- the approval resolved the floor inside Authority
    # and is recorded in `approval_ref` -- so there is no second permitting branch here, and
    # no place for Change to decide that HUMAN_APPROVAL_REQUIRED was close enough.
    if reproduced["decision"] != AUTONOMOUS:
        raise UnauthorizedChangeError(
            "Authority decision does not permit this change: "
            f"{reproduced['decision']} (reason codes: {reproduced['decision_reason_codes']})"
        )

    # --- derivation ----------------------------------------------------------- #
    #
    # Every field comes from the reproduced decision. There is no second supplied value for
    # any of them, so "bound to the exact project / Difference / State / action / scope" is
    # not a set of checks that could be forgotten -- it is the only thing the record can say.
    change: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "change_id": "",
        "project_id": reproduced["project_id"],
        "difference_ref": deepcopy(reproduced["difference_ref"]),
        "authority_ref": {
            "kind": "authority_decision",
            "id": reproduced["authority_decision_id"],
        },
        "before_state_fingerprint": deepcopy(reproduced["evaluated_state_fingerprint"]),
        "expected_state_revision": reproduced["evaluated_state_revision"],
        "action": deepcopy(reproduced["requested_action"]),
        "scope": deepcopy(reproduced["requested_scope"]),
        "idempotency_key": "",
        # 第24条 requires the field; Change must not execute, so at derivation there is
        # nothing to report.
        "execution_result": None,
        "status": AUTHORIZED,
        "change_semantic_fingerprint": "",
    }
    change["idempotency_key"] = idempotency_key(change)
    change["change_semantic_fingerprint"] = change_semantic_fingerprint(change)
    change["change_id"] = change_id(change)
    _validate(change, "change.schema.json", CHANGE_SCHEMA_BASE, "generated change")
    return change
