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

Structural Review Round 5 (P13-R5, Authority Provenance Bypass follow-on, P13-R3-F2's own
remaining gap): a grant's own shape/binding/provenance being self-consistent -- even once
Structural Review Round 4 (P13-R4) required it to be a genuinely Store-resolved record rather
than caller-supplied content -- still never proved a Human, rather than any caller who could
commit a Store record, actually *declared* that grant. A binding grant now additionally
requires at least one matching, real, canonical
:data:`~.conformance.RECORD_TYPES` ``"human_grant_declaration"`` record -- the Binding
owner's own canonical, read-only-reverifiable Human declaration anchor
(:func:`~manosube_agent_civilization.binding.route.declare_human_grant`) -- whose
``grant_ref`` names exactly this grant, whose ``project_id`` matches, whose ``declared_by``
canonical-reference-equals the real, Boot-verified ``human_authority_ref``, and whose own
``status`` is ``ACTIVE``. A grant with no matching declaration, a declaration naming a
different (or self-fabricated) Human Authority, or a declaration that is not itself
``ACTIVE``, withholds the selection exactly as a non-``ACTIVE`` grant already does -- never an
exception, always a total convergence to ``VERIFIER_SELECTION_REFUSED``.

Structural Review Round 5-R1 (P13-R5-R1, Issue #51,
``ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER``): a declaration's own
Store persistence and self-consistent shape -- even durably committed through Binding's own
route -- still never proved a *Human* authored it, only that some Store-write-capable caller
committed a record shaped like one. This module now additionally requires the caller-supplied
*human_authority_signing_key* (the real Project Binding's own public verification key, which
the caller independently resolved through Boot/the Store -- never a caller-supplied copy of
its own) to verify the candidate declaration's own ``signature`` field, over the declaration's
own restated ``requirement_id``/``selection_id``/``verifier_identity``/``permitted_boundary``
-- read independently against *this* candidate grant's own matching fields, not merely
asserted by the declaration itself -- via
:func:`~manosube_agent_civilization.binding.signature.verify_declaration_signature`. A
declaration whose restated fields do not match this grant's own fields, or whose signature
does not verify, does not bind, exactly as a non-``ACTIVE`` declaration already does not.
Authority never trusts Binding's own prior verification at commit time as a substitute for its
own -- a Store write proves nothing about who authored the payload it carries.

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
    "human_authority_signing_key",
    "grants",
    "grant_declarations",
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


def _anchors_grant(declaration: dict[str, Any], *, project_id: str, grant_id: str) -> bool:
    """Whether *declaration* names exactly this project and this grant -- distinctness
    before activeness, the identical convention :func:`_core_mismatches` already uses.
    A declaration that does not even anchor this grant is not a weaker version of one that
    does; it is simply not a candidate for it at all, exactly as a grant naming a different
    selection is not a weaker grant for this one (Structural Review Round 5, P13-R5)."""

    return bool(
        declaration["project_id"] == project_id
        and declaration["grant_ref"] == {"kind": "verifier_selection_grant", "id": grant_id}
    )


def _declaration_restates_grant(declaration: dict[str, Any], grant: dict[str, Any]) -> bool:
    """Whether *declaration*'s own restated ``requirement_id``/``selection_id``/
    ``verifier_identity``/``permitted_boundary`` equal *grant*'s own matching fields
    (Structural Review Round 5-R1, Issue #51, P13-R5-R1) -- independently re-checked here,
    never merely trusted because ``grant_ref`` already names this grant's id: R5-R1's own
    adopted design has the declaration restate these fields directly (rather than bind them
    only by ``grant_ref``'s content address) precisely so the Human's signature covers a
    complete, self-describing payload, and this evaluator re-verifies that restatement
    independently rather than trusting Binding's own prior assembly of it."""

    return bool(
        declaration["requirement_id"] == grant["requirement_id"]
        and declaration["selection_id"] == grant["selection_id"]
        and declaration["verifier_identity"] == grant["verifier_identity"]
        and declaration["permitted_boundary"] == grant["permitted_boundary"]
    )


def _verify_declaration_signature(
    declaration: dict[str, Any], *, signing_key: dict[str, Any]
) -> bool:
    """Lazily import and delegate to Binding's own
    :func:`~manosube_agent_civilization.binding.signature.verify_declaration_signature`
    (Structural Review Round 5-R1, Issue #51, P13-R5-R1) -- deferred to call time, never
    module import time, for the identical circular-import reason
    :mod:`~manosube_agent_civilization.authority.conformance`'s own
    ``_human_grant_declaration_id`` already documents: importing ``binding`` reaches
    ``binding.admission`` -> ``reflow`` -> ``evidence`` -> ``change`` -> back to this very
    package. By the time any declaration is actually verified, every module in the repository
    has already finished importing; only import-time module construction can observe the
    cycle."""

    from manosube_agent_civilization.binding.signature import (
        verify_declaration_signature as _real_verify_declaration_signature,
    )

    return _real_verify_declaration_signature(declaration, signing_key=signing_key)


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
    # Structural Review Round 5-R1 (Issue #51, P13-R5-R1): the real Project Binding's own
    # public verification key, independently resolved by the caller (never a caller-supplied
    # copy asserted without Store backing) -- this evaluator never trusts Binding's own prior
    # signature check at commit time as a substitute for its own independent re-verification.
    human_authority_signing_key = require_object(
        shaped["human_authority_signing_key"],
        "verifier selection request human_authority_signing_key",
    )

    # Every supplied grant crosses the identical admission gate every other Authority-owned
    # record does: schema, supported version, no unknown property, recomputed content
    # address, and Human Authority provenance (`.conformance.admit`). A grant failing any of
    # those does not bind, is not consulted, and does not quietly become an absence. Every
    # supplied declaration (Structural Review Round 5, P13-R5) crosses the identical gate too,
    # over Binding's own `human_grant_declaration.schema.json` and identity function.
    grants = admit_all(shaped["grants"], "verifier_selection_grant", "grants")
    declarations = admit_all(
        shaped["grant_declarations"], "human_grant_declaration", "grant_declarations"
    )

    binding: list[tuple[dict[str, Any], dict[str, Any]]] = []
    excluding: list[tuple[dict[str, Any], str]] = []
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
            continue
        if candidate["status"] != "ACTIVE":
            excluding.append((candidate, f"GRANT_{candidate['status']}"))
            continue

        # P13-R5: a core-clean, ACTIVE grant still withholds the selection unless a real,
        # matching, ACTIVE Human Grant Declaration anchors it -- the grant's own content or
        # its mere Store persistence (both already required by P13-R3/P13-R4) is never
        # itself proof a Human declared it. Staged, not a flat mismatch list, because each
        # stage answers a different question: does any declaration even name this grant at
        # all; among those, does one agree with the real Human Authority; among those, is one
        # still ACTIVE.
        grant_id = candidate["verifier_selection_grant_id"]
        anchored = [
            declaration
            for declaration in declarations
            if _anchors_grant(declaration, project_id=project_id, grant_id=grant_id)
        ]
        if not anchored:
            excluding.append((candidate, "DECLARATION_MISSING"))
            continue
        authority_matching = [
            declaration
            for declaration in anchored
            if declaration["declared_by"] == human_authority_ref
        ]
        if not authority_matching:
            excluding.append((candidate, "DECLARATION_AUTHORITY_MISMATCH"))
            continue
        active_declarations = [
            declaration for declaration in authority_matching if declaration["status"] == "ACTIVE"
        ]
        if not active_declarations:
            excluding.append((candidate, "DECLARATION_NOT_ACTIVE"))
            continue

        # Structural Review Round 5-R1 (P13-R5-R1): a declaration that anchors this grant by
        # `grant_ref` and is otherwise ACTIVE still does not bind unless its own restated
        # requirement/selection/verifier/boundary independently agree with *this* candidate
        # grant's own matching fields -- never merely trusted because `grant_ref` already
        # names this grant's id (see `_declaration_restates_grant`'s own docstring).
        restating_declarations = [
            declaration
            for declaration in active_declarations
            if _declaration_restates_grant(declaration, candidate)
        ]
        if not restating_declarations:
            excluding.append((candidate, "DECLARATION_CONTENT_MISMATCH"))
            continue

        # And finally, the declaration's own claimed `signature` must independently verify
        # against the real Project Binding's own `human_authority_signing_key` -- durable
        # Store commission of a self-consistent, correctly-anchored declaration is still never
        # itself proof a Human authored it (see the module docstring's own R5-R1 addendum).
        signature_valid_declarations = [
            declaration
            for declaration in restating_declarations
            if _verify_declaration_signature(declaration, signing_key=human_authority_signing_key)
        ]
        if signature_valid_declarations:
            # Chosen by identity, not by input position -- the same determinism already
            # guaranteed for grant selection below.
            chosen_declaration = sorted(
                signature_valid_declarations,
                key=lambda declaration: str(declaration["human_grant_declaration_id"]),
            )[0]
            binding.append((candidate, chosen_declaration))
        else:
            excluding.append((candidate, "DECLARATION_SIGNATURE_INVALID"))

    reason_codes: list[str] = []
    used_grant: dict[str, Any] | None = None
    used_declaration: dict[str, Any] | None = None
    if not grants:
        reason_codes.append("GRANT_MISSING")
    elif binding:
        # Chosen by identity, not by input position -- the same determinism
        # `evaluate_authority` already guarantees for its own approval selection.
        used_grant, used_declaration = sorted(
            binding, key=lambda pair: str(pair[0]["verifier_selection_grant_id"])
        )[0]
        reason_codes.append("GRANT_EXACT")
    elif excluding:
        # A grant that binds every other field but is not ACTIVE, or that lacks a genuine,
        # matching, ACTIVE Human Grant Declaration, withholds the selection -- it does not
        # fall through to "no grant named this selection at all".
        _first_grant, first_reason = sorted(
            excluding, key=lambda pair: str(pair[0]["verifier_selection_grant_id"])
        )[0]
        reason_codes.append(first_reason)
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
        used_declaration=used_declaration,
        excluding_grants=[grant for grant, _reason in excluding],
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
    used_declaration: dict[str, Any] | None,
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
        "declaration_ref": (
            None
            if used_declaration is None
            else {
                "kind": "human_grant_declaration",
                "id": used_declaration["human_grant_declaration_id"],
            }
        ),
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
