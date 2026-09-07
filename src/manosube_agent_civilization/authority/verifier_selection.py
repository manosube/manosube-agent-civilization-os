"""The Verifier Selection Decision: does a real Human Authority grant *this* selection?

Structural Review Round 3 (Issue #51, P13-R3-F1): ``boot_project(...).human_authority_ref``
re-verifies the real Human Authority a Project is bound to -- it is a necessary precondition,
not itself a decision that SHUKOU selected *this* ``VerifierSelection``
(verifier_identity/permitted_boundary/status) for *this* ``VerificationRequirement``. This
module is the dedicated, read-only, deterministic public surface that decision requires,
added as an extension of the existing ``authority`` owner rather than as a second owner: it
introduces no Authority registry, token, cache, or persisted artifact, reuses the identical
admission grammar (:mod:`.conformance`) every other Authority-owned record already crosses,
and computes its own decision the same way :func:`~.engine.evaluate_authority` computes its
-- deterministically, over explicit inputs, content-addressed, never reading a clock.

``evaluate_verifier_selection`` binds ``project_id``, ``requirement_id``, ``selection_id``,
``verifier_identity``, ``permitted_boundary``, and ``selection_status`` to at least one
canonical, Human-Authority-declared :data:`~.conformance.RECORD_TYPES`
``"verifier_selection_grant"`` record that names exactly those same values -- never merely a
caller-supplied mapping repeating them, and never a synthetic Change/Difference/State
constructed solely to route this question through :func:`~.engine.evaluate_authority`
(P13-R3-F1's own prohibition). A grant that binds on every field but is not itself ``ACTIVE``
withholds the selection exactly as an excluding Approval withholds a Change (frozen semantic
decision analogous to ``AUTHORITY_CONTRACT.md`` §4's approval-exclusion stage); a request
naming no grant at all, or naming only grants that do not bind, is refused.

Following :mod:`.errors`' own distinction: an unreadable request raises
:class:`~.errors.AuthorityError` (there is no permission question to answer). A readable
request that does not bind is not an exception -- it is the decision ``REFUSED``, exactly as
an unreadable-but-well-formed Change request answers ``PROHIBITED``/``HUMAN_APPROVAL_REQUIRED``
rather than raising.

This module never imports ``manosube_agent_civilization.independent_verification`` --
Independent Verification calls this surface by its one public function, never the reverse, so
no cycle and no Adapter-owned Authority can exist (P13-R3-F1's own explicit prohibition).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.difference.admissibility import require_object, require_scalar_tag
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.state.errors import CanonicalizationError

from .conformance import AUTHORITY_SCHEMA_BASE, admit_all, validate
from .errors import AuthorityError
from .identity import (
    verifier_selection_decision_id,
    verifier_selection_decision_semantic_fingerprint,
)

SCHEMA_VERSION = "0.1"

SELECTED = "VERIFIER_SELECTION_SELECTED"
REFUSED = "VERIFIER_SELECTION_REFUSED"
DECISIONS: frozenset[str] = frozenset({SELECTED, REFUSED})

#: The identical status vocabulary ``authority.approval`` and
#: ``independent_verification.types`` each already use, duplicated deliberately -- this
#: module never imports ``independent_verification`` (see the module docstring), and copying
#: three literal strings is a smaller coupling than a shared import would be.
SELECTION_STATUSES: frozenset[str] = frozenset({"ACTIVE", "REVOKED", "EXPIRED"})

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "requirement_id",
    "selection_id",
    "verifier_identity",
    "permitted_boundary",
    "selection_status",
    "human_authority_ref",
    "grants",
)


def _validate(record: dict[str, Any], schema_name: str) -> None:
    validate(record, schema_name, "verifier selection decision", base=AUTHORITY_SCHEMA_BASE)


def _require_request_shape(request: Any) -> dict[str, Any]:
    shaped = require_object(request, "verifier selection request")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise AuthorityError(f"verifier selection request carries unknown keys: {sorted(unknown)}")
    for key in REQUIRED_REQUEST_KEYS:
        if key not in shaped:
            raise AuthorityError(f"verifier selection request omits a required key: {key}")
    version = require_scalar_tag(shaped["schema_version"], "verifier selection request version")
    if version != SCHEMA_VERSION:
        raise AuthorityError(
            f"unsupported schema_version {version!r} at verifier selection request"
        )
    return shaped


def _core_mismatches(
    grant: dict[str, Any],
    *,
    project_id: str,
    requirement_id: str,
    selection_id: str,
    verifier_identity: dict[str, Any],
    permitted_boundary: dict[str, Any],
    selection_status: str,
    human_authority_ref: dict[str, Any],
) -> list[str]:
    """Every way *grant* fails to bind this exact selection; empty means it binds.

    Distinctness before activeness -- a grant naming a different project, requirement,
    selection, verifier, or boundary is not *this* selection's grant at all, whatever its own
    status is. ``GRANT_SELECTION_STATUS_MISMATCH`` catches a caller who declared a different
    status than the grant it points to actually carries: the caller's own claim is not
    trusted merely because it repeats a real grant's other fields. ``GRANT_AUTHORITY_MISMATCH``
    is the binding P13-R3-F1 itself requires: *this* module never re-derives the real Human
    Authority a project is bound to (that is what ``boot_project`` is for) -- it requires the
    grant's own ``granted_by`` to canonical-reference-equal the caller-supplied
    *human_authority_ref*, which the caller re-verified through the existing Boot owner before
    ever reaching this evaluator. A grant declared by a different (or self-fabricated) Human
    Authority does not bind, however well every other field matches.
    """

    reasons: list[str] = []
    if grant["project_id"] != project_id:
        reasons.append("GRANT_PROJECT_MISMATCH")
    if grant["requirement_id"] != requirement_id:
        reasons.append("GRANT_REQUIREMENT_MISMATCH")
    if grant["selection_id"] != selection_id:
        reasons.append("GRANT_SELECTION_MISMATCH")
    if grant["verifier_identity"] != verifier_identity:
        reasons.append("GRANT_VERIFIER_IDENTITY_MISMATCH")
    if grant["permitted_boundary"] != permitted_boundary:
        reasons.append("GRANT_BOUNDARY_MISMATCH")
    if grant["status"] != selection_status:
        reasons.append("GRANT_SELECTION_STATUS_MISMATCH")
    if grant["granted_by"] != human_authority_ref:
        reasons.append("GRANT_AUTHORITY_MISMATCH")
    return sorted(reasons)


def evaluate_verifier_selection(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Verifier Selection Decision for one exact request.

    The returned record is schema-valid and content-addressed: the same question always
    produces the same ``verifier_selection_decision_id``. *request* is never mutated.

    Every unreadable input leaves here as an :class:`~.errors.AuthorityError`; a readable
    request that does not bind returns a ``REFUSED`` decision rather than raising, the
    identical distinction :func:`~.engine.evaluate_authority` already draws.
    """

    try:
        return _evaluate(request)
    except (DifferenceError, CanonicalizationError) as error:
        raise AuthorityError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "verifier selection request project")
    requirement_id = require_scalar_tag(
        shaped["requirement_id"], "verifier selection request requirement"
    )
    selection_id = require_scalar_tag(
        shaped["selection_id"], "verifier selection request selection"
    )
    verifier_identity = require_object(
        shaped["verifier_identity"], "verifier selection request verifier_identity"
    )
    permitted_boundary = require_object(
        shaped["permitted_boundary"], "verifier selection request permitted_boundary"
    )
    selection_status = require_scalar_tag(
        shaped["selection_status"], "verifier selection request selection_status"
    )
    if selection_status not in SELECTION_STATUSES:
        raise AuthorityError(
            f"verifier selection request selection_status is not recognized: {selection_status!r}"
        )
    human_authority_ref = require_object(
        shaped["human_authority_ref"], "verifier selection request human_authority_ref"
    )
    if human_authority_ref.get("kind") != "human_authority":
        raise AuthorityError(
            "verifier selection request human_authority_ref is not a Human Authority "
            f"reference: {human_authority_ref.get('kind')!r}"
        )

    # Every supplied grant crosses the identical admission gate every other Authority-owned
    # record does: schema, supported version, no unknown property, recomputed content
    # address, and Human Authority provenance (`.conformance.admit`). A grant failing any of
    # those does not bind, is not consulted, and does not quietly become an absence.
    grants = admit_all(shaped["grants"], "verifier_selection_grant", "grants")

    binding: list[dict[str, Any]] = []
    excluding: list[dict[str, Any]] = []
    failures: list[str] = []
    for candidate in grants:
        mismatches = _core_mismatches(
            candidate,
            project_id=project_id,
            requirement_id=requirement_id,
            selection_id=selection_id,
            verifier_identity=verifier_identity,
            permitted_boundary=permitted_boundary,
            selection_status=selection_status,
            human_authority_ref=human_authority_ref,
        )
        if mismatches:
            failures.extend(mismatches)
        elif candidate["status"] == "ACTIVE":
            binding.append(candidate)
        else:
            excluding.append(candidate)

    reason_codes: list[str] = []
    used_grant: dict[str, Any] | None = None
    if not grants:
        reason_codes.append("GRANT_MISSING")
    elif binding:
        # Chosen by identity, not by input position -- the same determinism
        # `evaluate_authority` already guarantees for its own approval selection.
        used_grant = sorted(binding, key=lambda grant: str(grant["verifier_selection_grant_id"]))[0]
        reason_codes.append("GRANT_EXACT")
    elif excluding:
        # A grant that binds every other field but is not ACTIVE withholds the selection --
        # it does not fall through to "no grant named this selection at all".
        first = sorted(excluding, key=lambda grant: str(grant["verifier_selection_grant_id"]))[0]
        reason_codes.append(f"GRANT_{first['status']}")
    else:
        reason_codes.extend(sorted(set(failures)))

    decision = SELECTED if used_grant is not None else REFUSED
    return _decision(
        project_id=project_id,
        requirement_id=requirement_id,
        selection_id=selection_id,
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        selection_status=selection_status,
        human_authority_ref=human_authority_ref,
        used_grant=used_grant,
        excluding_grants=excluding,
        decision=decision,
        reason_codes=reason_codes,
    )


def _decision(
    *,
    project_id: str,
    requirement_id: str,
    selection_id: str,
    verifier_identity: dict[str, Any],
    permitted_boundary: dict[str, Any],
    selection_status: str,
    human_authority_ref: dict[str, Any],
    used_grant: dict[str, Any] | None,
    excluding_grants: list[dict[str, Any]],
    decision: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    """Assemble, address and validate one Verifier Selection Decision record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "verifier_selection_decision_id": "",
        "project_id": project_id,
        "requirement_id": requirement_id,
        "selection_id": selection_id,
        "verifier_identity": deepcopy(verifier_identity),
        "permitted_boundary": deepcopy(permitted_boundary),
        "selection_status": selection_status,
        "selection_authority_ref": deepcopy(human_authority_ref),
        "grant_ref": (
            None
            if used_grant is None
            else {
                "kind": "verifier_selection_grant",
                "id": used_grant["verifier_selection_grant_id"],
            }
        ),
        "excluding_grant_refs": [
            {"kind": "verifier_selection_grant", "id": grant["verifier_selection_grant_id"]}
            for grant in excluding_grants
        ],
        "decision": decision,
        "decision_reason_codes": sorted(set(reason_codes)),
        "decision_semantic_fingerprint": "",
    }
    record["decision_semantic_fingerprint"] = verifier_selection_decision_semantic_fingerprint(
        record
    )
    record["verifier_selection_decision_id"] = verifier_selection_decision_id(record)
    _validate(record, "verifier_selection_decision.schema.json")
    return record
