"""The one Change deriver: what authorized mutation does this decision permit?

```text
RAW CHANGE REQUEST
→ REQUEST + DIFFERENCE + DECISION ADMISSION
→ EXACT BINDING
→ PERMISSION
→ CANONICAL CHANGE
```

Change **describes** an authorized mutation. It does not perform one. This module reads no
clock, no filesystem, no network, no environment, no GitHub and no conversation; it computes
a record from the records it was given, and the absence of any API through which it could do
more is the evidence for that, not a promise in this docstring.

The permission question is already answered before this module runs. Authority decides
whether an action *may* occur (``KERNEL_CONSTITUTION.md`` 第21条); Change's only judgement is
whether the decision in front of it permits *this exact* Change. Re-deciding permission here
would be a second Authority, and a second Authority is one that can disagree with the first.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.authority import AUTONOMOUS
from manosube_agent_civilization.authority.conformance import (
    AUTHORITY_SCHEMA_BASE,
    admit_difference,
    require_action_kind,
)
from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.authority.identity import (
    action_fingerprint,
    decision_id,
    decision_semantic_fingerprint,
)
from manosube_agent_civilization.authority.levels import REVERSIBILITIES
from manosube_agent_civilization.authority.scope import require_scope
from manosube_agent_civilization.difference.admissibility import (
    require_object,
    require_scalar_tag,
)
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.state.errors import CanonicalizationError

from .errors import (
    ChangeBoundaryViolationError,
    ChangeError,
    ChangeValidationError,
    StaleChangeError,
    UnauthorizedChangeError,
)
from .identity import change_id, change_semantic_fingerprint, idempotency_key

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
#: gives: an ignored key is still a channel. A caller that attaches prose to a Change request
#: is refused rather than quietly having it dropped.
REQUIRED_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "project_id",
        "difference",
        "authority_decision",
        "requested_action",
        "requested_scope",
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


def _require_action(value: Any) -> dict[str, Any]:
    """Return the requested action once it is canonical and names its own operation.

    The fingerprint is **recomputed**, never trusted: a caller-declared digest is a label,
    and a label that is believed rather than checked lets one approval cover two operations.
    """

    action = require_object(value, "requested action")
    expected = {"action_kind", "reversibility", "operation", "action_semantic_fingerprint"}
    unknown = set(action) - expected
    if unknown:
        raise ChangeError(f"requested action carries unknown keys: {sorted(unknown)}")
    missing = expected - set(action)
    if missing:
        raise ChangeError(f"requested action omits required keys: {sorted(missing)}")
    require_action_kind(action["action_kind"], "requested action kind")
    reversibility = require_scalar_tag(action["reversibility"], "requested action reversibility")
    if reversibility not in REVERSIBILITIES:
        raise ChangeError(f"requested action declares an unknown reversibility: {reversibility!r}")
    declared = action["action_semantic_fingerprint"]
    try:
        recomputed = action_fingerprint(action)
    except CanonicalizationError as error:
        raise ChangeError(f"requested action operation payload is not canonical: {error}") from error
    if declared != recomputed:
        raise ChangeError(
            "requested action fingerprint does not match the action it names: "
            f"{declared!r} != {recomputed!r}"
        )
    return action


def _admit_decision(value: Any) -> dict[str, Any]:
    """Return the bound Authority decision once it is canonical, including its own address.

    A decision is a *supplied* record here exactly as a rule or an approval is supplied to
    Authority, so it crosses the same four questions: readable, schema-valid at a supported
    version with no unknown property, **content address recomputed**, and -- the one Authority
    itself guarantees -- produced by the evaluator rather than asserted.

    The address is asked of Authority's own owner. A second implementation of a decision
    address would be a second answer to what that address is, and the first time the two
    disagree the disagreement is silent.
    """

    decision = require_object(value, "bound Authority decision")
    version = decision.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ChangeError(
            f"bound Authority decision declares an unsupported schema_version: {version!r}"
        )
    unknown = set(decision) - DECISION_REQUIRED_KEYS
    if unknown:
        raise ChangeError(f"bound Authority decision carries unknown keys: {sorted(unknown)}")
    _validate(
        decision, "authority.schema.json", AUTHORITY_SCHEMA_BASE, "bound Authority decision"
    )
    declared = decision["authority_decision_id"]
    recomputed = decision_id(decision)
    if declared != recomputed:
        raise ChangeError(
            "bound Authority decision identity does not match the decision it names: "
            f"{declared!r} != {recomputed!r}"
        )
    declared_fingerprint = decision["decision_semantic_fingerprint"]
    recomputed_fingerprint = decision_semantic_fingerprint(decision)
    if declared_fingerprint != recomputed_fingerprint:
        raise ChangeError(
            "bound Authority decision fingerprint does not match its own meaning: "
            f"{declared_fingerprint!r} != {recomputed_fingerprint!r}"
        )
    return decision


def derive_change(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Change for one exactly-authorized request.

    The returned record is schema-valid and content-addressed: the same authorized change
    always produces the same ``change_id``. *request* is never mutated.

    Every refusal leaves here as a :class:`ChangeError`. Three owners one layer down speak
    their own vocabularies -- readability answers in ``DifferenceError`` (ADR-0025), canonical
    serialization in ``CanonicalizationError``, and the shared admission path Change reuses
    rather than reimplements answers in ``AuthorityError`` -- and asking all three is right.
    Letting any of them escape would make a caller of *Change* catch a *Difference*, a *State*
    or an *Authority* error to learn that its own request was malformed. The decisions are
    delegated. The boundary's error vocabulary is not.

    ``AuthorityError`` is the one that is easiest to get wrong, because reusing Authority's
    conformance owner is deliberate: ``admit_difference`` and ``require_scope`` are Authority's,
    and a second implementation of either would be a second answer to what a Difference or a
    scope is. Reusing them is right; letting their vocabulary out of this boundary is not.
    """

    try:
        return _derive(request)
    except (AuthorityError, DifferenceError, CanonicalizationError) as error:
        raise ChangeError(str(error)) from error


def _derive(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "change request project")
    difference = admit_difference(shaped["difference"], "bound Difference")
    decision = _admit_decision(shaped["authority_decision"])
    action = _require_action(shaped["requested_action"])
    scope = require_scope(shaped["requested_scope"], "requested scope")

    # --- exact binding ------------------------------------------------------- #
    #
    # Every one of these is a pair of supplied values that must already agree. Checking them
    # is what makes "bound to the exact X" a property rather than a hope: a caller who
    # relabels any single input is refused here, before anything is derived from it.
    if difference["project_id"] != project_id:
        raise ChangeBoundaryViolationError(
            "bound Difference belongs to a different project: "
            f"{difference['project_id']!r} != {project_id!r}"
        )
    if decision["project_id"] != project_id:
        raise ChangeBoundaryViolationError(
            "bound Authority decision belongs to a different project: "
            f"{decision['project_id']!r} != {project_id!r}"
        )
    if decision["difference_ref"].get("id") != difference["difference_id"]:
        raise ChangeBoundaryViolationError(
            "bound Authority decision was not made about this Difference: "
            f"{decision['difference_ref'].get('id')!r} != {difference['difference_id']!r}"
        )
    if decision["requested_action"] != action:
        raise ChangeBoundaryViolationError(
            "requested action is not the action the Authority decision permitted"
        )
    if decision["requested_scope"] != scope:
        raise ChangeBoundaryViolationError(
            "requested scope is not the scope the Authority decision permitted"
        )

    # --- staleness ----------------------------------------------------------- #
    #
    # The State binding is taken from the decision rather than supplied beside it, so the two
    # cannot disagree (Issue #31 interpretation 5). What remains checkable is that the
    # Difference was observed against that same State: 第26条 blocks a stale Change, and a
    # Difference describing a State the decision did not evaluate is exactly that.
    expected_revision = decision["evaluated_state_revision"]
    before_fingerprint = decision["evaluated_state_fingerprint"]
    if (
        difference["observed_state_revision"] != expected_revision
        or difference["observed_state_fingerprint"] != before_fingerprint
    ):
        stale: list[str] = []
        if difference["observed_state_revision"] != expected_revision:
            stale.append(
                f"revision {difference['observed_state_revision']} vs authorized {expected_revision}"
            )
        if difference["observed_state_fingerprint"] != before_fingerprint:
            stale.append("fingerprint differs from the authorized State fingerprint")
        raise StaleChangeError(
            "bound Difference is not bound to the authorized State: " + "; ".join(stale)
        )

    # --- permission ---------------------------------------------------------- #
    #
    # One value permits a Change, and it is the one Authority uses to say so. An exactly
    # approved decision *is* AUTONOMOUS -- the approval resolved the floor inside Authority
    # and is recorded in `approval_ref` -- so there is no second permitting branch here, and
    # no place for Change to decide that HUMAN_APPROVAL_REQUIRED was close enough.
    if decision["decision"] != AUTONOMOUS:
        raise UnauthorizedChangeError(
            "bound Authority decision does not permit this change: "
            f"{decision['decision']} (reason codes: {decision['decision_reason_codes']})"
        )

    change: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "change_id": "",
        "project_id": project_id,
        "difference_ref": {"kind": "difference", "id": difference["difference_id"]},
        "authority_ref": {
            "kind": "authority_decision",
            "id": decision["authority_decision_id"],
        },
        "before_state_fingerprint": deepcopy(before_fingerprint),
        "expected_state_revision": expected_revision,
        "action": deepcopy(action),
        "scope": deepcopy(scope),
        "idempotency_key": "",
        # 第24条 requires the field; Change must not execute, so at derivation there is
        # nothing to report. It is null, and the schema holds it null for an AUTHORIZED
        # Change rather than leaving that to this line alone.
        "execution_result": None,
        "status": AUTHORIZED,
        "change_semantic_fingerprint": "",
    }
    change["idempotency_key"] = idempotency_key(change)
    change["change_semantic_fingerprint"] = change_semantic_fingerprint(change)
    change["change_id"] = change_id(change)
    _validate(change, "change.schema.json", CHANGE_SCHEMA_BASE, "generated change")
    return change
