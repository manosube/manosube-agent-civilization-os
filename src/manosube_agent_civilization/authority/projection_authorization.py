"""The GitHub Projection Decision: does a real Human Authority grant *this exact* projection?

Phase 14 Structural Review Round 1 (Issue #62, P14-R1-F1): Projection's own route re-verified
``github_authority_ref`` against ``boot_project(...).human_authority_ref`` -- a necessary
precondition (identity of an Authority holder), but never itself a decision that this exact
Human Authority actually authorized projecting *this* subject, at *this* subject fingerprint,
as *this* projection kind, to *this* target repository, with *this* payload. That gap is the
identical class Independent Verification's own Structural Review Round 3 (Issue #51,
P13-R3-F1) already closed for verifier selection: an owner identity is a prerequisite, not a
specific authorization decision. This module is that dedicated, read-only, deterministic
public surface for Projection, added as an extension of the existing ``authority`` owner
rather than as a second owner -- it introduces no Authority registry, token, cache, or
persisted artifact beyond the one canonical record kind (``github_projection_grant``) this
module admits through the identical :mod:`.conformance` gate every other Authority-owned
record already crosses.

``evaluate_projection_authorization`` binds ``project_id``, ``subject_ref``,
``subject_fingerprint``, ``projection_kind``, ``target_repository``, ``payload_fingerprint``,
and ``permitted_action`` to at least one canonical, Human-Authority-declared
:data:`~.conformance.RECORD_TYPES` ``"github_projection_grant"`` record that names exactly
those same values -- never merely a caller-supplied mapping repeating them. A grant that
binds on every field but is not itself ``ACTIVE`` withholds authorization exactly as an
excluding Approval withholds a Change; a request naming no grant at all, or naming only
grants that do not bind, is refused.

**Disclosed scope boundary.** Unlike Independent Verification's own ``verifier_selection_grant``
(Structural Review Rounds 4-5-R1), this module does not yet require the supplied grant to be
independently Store-resolved by the caller, nor anchored by a separate, signed Human Grant
Declaration -- Projection's own route resolves ``github_projection_grant`` records through the
identical Store surface every other Projection reference already resolves through
(``store.resolve_record``), which gives the identical Round-4-level protection (a grant must
be genuinely, durably committed, never merely asserted as this function's own caller
argument), but this correction round does not extend that to Round 5/5-R1's own deeper
Human-declaration-and-signature layer. That is a disclosed, bounded scope decision -- not a
silent narrowing -- left as a candidate future Difference, exactly as Independent
Verification's own Round 3 disclosed the identical next gap before Round 4 closed it.

Following :mod:`.errors`' own distinction: an unreadable request raises
:class:`~.errors.AuthorityError`. A readable request that does not bind is not an exception --
it is the decision ``PROJECTION_REFUSED``, exactly as an unreadable-but-well-formed Change
request answers ``PROHIBITED``/``HUMAN_APPROVAL_REQUIRED`` rather than raising.

This module never imports ``manosube_agent_civilization.projection`` -- Projection calls this
surface by its one public function, never the reverse, so no cycle and no Adapter-owned
Authority can exist (the identical prohibition P13-R3-F1 already states for Independent
Verification).
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
    github_projection_decision_id,
    github_projection_decision_semantic_fingerprint,
)

SCHEMA_VERSION = "0.1"

AUTHORIZED = "PROJECTION_AUTHORIZED"
REFUSED = "PROJECTION_REFUSED"
DECISIONS: frozenset[str] = frozenset({AUTHORIZED, REFUSED})

REQUIRED_REQUEST_KEYS: tuple[str, ...] = (
    "schema_version",
    "project_id",
    "subject_ref",
    "subject_fingerprint",
    "projection_kind",
    "target_repository",
    "payload_fingerprint",
    "permitted_action",
    "human_authority_ref",
    "grants",
)

_PERMITTED_ACTIONS: frozenset[str] = frozenset({"MATERIALIZE_PROJECTION"})
_PROJECTION_KINDS: frozenset[str] = frozenset(
    {"DIFFERENCE_ISSUE", "CHANGE_PULL_REQUEST", "EVIDENCE_ARTIFACT"}
)


def _validate(record: dict[str, Any], schema_name: str) -> None:
    validate(record, schema_name, "github projection decision", base=AUTHORITY_SCHEMA_BASE)


def _require_request_shape(request: Any) -> dict[str, Any]:
    shaped = require_object(request, "github projection request")
    unknown = set(shaped) - set(REQUIRED_REQUEST_KEYS)
    if unknown:
        raise AuthorityError(f"github projection request carries unknown keys: {sorted(unknown)}")
    for key in REQUIRED_REQUEST_KEYS:
        if key not in shaped:
            raise AuthorityError(f"github projection request omits a required key: {key}")
    version = require_scalar_tag(shaped["schema_version"], "github projection request version")
    if version != SCHEMA_VERSION:
        raise AuthorityError(
            f"unsupported schema_version {version!r} at github projection request"
        )
    return shaped


def _core_mismatches(
    grant: dict[str, Any],
    *,
    project_id: str,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    payload_fingerprint: str,
    permitted_action: str,
    human_authority_ref: dict[str, Any],
) -> list[str]:
    """Every way *grant* fails to bind this exact projection; empty means it binds.

    Distinctness before activeness -- a grant naming a different subject, target, or payload
    is not *this* projection's grant at all, whatever its own status is
    (the identical discipline :func:`~.verifier_selection._core_mismatches` already applies).
    """

    reasons: list[str] = []
    if grant["project_id"] != project_id:
        reasons.append("GRANT_PROJECT_MISMATCH")
    if grant["subject_ref"] != subject_ref:
        reasons.append("GRANT_SUBJECT_MISMATCH")
    if grant["subject_fingerprint"] != subject_fingerprint:
        reasons.append("GRANT_SUBJECT_FINGERPRINT_MISMATCH")
    if grant["projection_kind"] != projection_kind:
        reasons.append("GRANT_PROJECTION_KIND_MISMATCH")
    if grant["target_repository"] != target_repository:
        reasons.append("GRANT_TARGET_REPOSITORY_MISMATCH")
    if grant["payload_fingerprint"] != payload_fingerprint:
        reasons.append("GRANT_PAYLOAD_MISMATCH")
    if grant["permitted_action"] != permitted_action:
        reasons.append("GRANT_ACTION_MISMATCH")
    if grant["granted_by"] != human_authority_ref:
        reasons.append("GRANT_AUTHORITY_MISMATCH")
    return sorted(reasons)


def evaluate_projection_authorization(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical GitHub Projection Decision for one exact request.

    The returned record is schema-valid and content-addressed: the same question always
    produces the same ``github_projection_decision_id``. *request* is never mutated.

    Every unreadable input leaves here as an :class:`~.errors.AuthorityError`; a readable
    request that does not bind returns a ``PROJECTION_REFUSED`` decision rather than raising.
    """

    try:
        return _evaluate(request)
    except (DifferenceError, CanonicalizationError) as error:
        raise AuthorityError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    project_id = require_scalar_tag(shaped["project_id"], "github projection request project")
    subject_ref = require_object(shaped["subject_ref"], "github projection request subject_ref")
    subject_fingerprint = require_scalar_tag(
        shaped["subject_fingerprint"], "github projection request subject_fingerprint"
    )
    projection_kind = require_scalar_tag(
        shaped["projection_kind"], "github projection request projection_kind"
    )
    if projection_kind not in _PROJECTION_KINDS:
        raise AuthorityError(
            f"github projection request projection_kind is not recognized: {projection_kind!r}"
        )
    target_repository = require_object(
        shaped["target_repository"], "github projection request target_repository"
    )
    payload_fingerprint = require_scalar_tag(
        shaped["payload_fingerprint"], "github projection request payload_fingerprint"
    )
    permitted_action = require_scalar_tag(
        shaped["permitted_action"], "github projection request permitted_action"
    )
    if permitted_action not in _PERMITTED_ACTIONS:
        raise AuthorityError(
            f"github projection request permitted_action is not recognized: {permitted_action!r}"
        )
    human_authority_ref = require_object(
        shaped["human_authority_ref"], "github projection request human_authority_ref"
    )
    if human_authority_ref.get("kind") != "human_authority":
        raise AuthorityError(
            "github projection request human_authority_ref is not a Human Authority "
            f"reference: {human_authority_ref.get('kind')!r}"
        )

    # Every supplied grant crosses the identical admission gate every other Authority-owned
    # record does: schema, supported version, no unknown property, recomputed content
    # address, and Human Authority provenance (`.conformance.admit`).
    grants = admit_all(shaped["grants"], "github_projection_grant", "grants")

    binding: list[dict[str, Any]] = []
    excluding: list[tuple[dict[str, Any], str]] = []
    failures: list[str] = []
    for candidate in grants:
        mismatches = _core_mismatches(
            candidate,
            project_id=project_id,
            subject_ref=subject_ref,
            subject_fingerprint=subject_fingerprint,
            projection_kind=projection_kind,
            target_repository=target_repository,
            payload_fingerprint=payload_fingerprint,
            permitted_action=permitted_action,
            human_authority_ref=human_authority_ref,
        )
        if mismatches:
            failures.extend(mismatches)
            continue
        if candidate["status"] != "ACTIVE":
            excluding.append((candidate, f"GRANT_{candidate['status']}"))
            continue
        binding.append(candidate)

    reason_codes: list[str] = []
    used_grant: dict[str, Any] | None = None
    if not grants:
        reason_codes.append("GRANT_MISSING")
    elif binding:
        # Chosen by identity, not by input position -- the same determinism
        # `evaluate_verifier_selection` already guarantees for its own grant selection.
        used_grant = sorted(binding, key=lambda grant: str(grant["github_projection_grant_id"]))[
            0
        ]
        reason_codes.append("GRANT_EXACT")
    elif excluding:
        _first_grant, first_reason = sorted(
            excluding, key=lambda pair: str(pair[0]["github_projection_grant_id"])
        )[0]
        reason_codes.append(first_reason)
    else:
        reason_codes.extend(sorted(set(failures)))

    decision = AUTHORIZED if used_grant is not None else REFUSED
    return _decision(
        project_id=project_id,
        subject_ref=subject_ref,
        subject_fingerprint=subject_fingerprint,
        projection_kind=projection_kind,
        target_repository=target_repository,
        payload_fingerprint=payload_fingerprint,
        permitted_action=permitted_action,
        human_authority_ref=human_authority_ref,
        used_grant=used_grant,
        excluding_grants=[grant for grant, _reason in excluding],
        decision=decision,
        reason_codes=reason_codes,
    )


def _decision(
    *,
    project_id: str,
    subject_ref: dict[str, Any],
    subject_fingerprint: str,
    projection_kind: str,
    target_repository: dict[str, Any],
    payload_fingerprint: str,
    permitted_action: str,
    human_authority_ref: dict[str, Any],
    used_grant: dict[str, Any] | None,
    excluding_grants: list[dict[str, Any]],
    decision: str,
    reason_codes: list[str],
) -> dict[str, Any]:
    """Assemble, address and validate one GitHub Projection Decision record."""

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "github_projection_decision_id": "",
        "project_id": project_id,
        "subject_ref": deepcopy(subject_ref),
        "subject_fingerprint": subject_fingerprint,
        "projection_kind": projection_kind,
        "target_repository": deepcopy(target_repository),
        "payload_fingerprint": payload_fingerprint,
        "permitted_action": permitted_action,
        "selection_authority_ref": deepcopy(human_authority_ref),
        "grant_ref": (
            None
            if used_grant is None
            else {
                "kind": "github_projection_grant",
                "id": used_grant["github_projection_grant_id"],
            }
        ),
        "excluding_grant_refs": [
            {"kind": "github_projection_grant", "id": grant["github_projection_grant_id"]}
            for grant in excluding_grants
        ],
        "decision": decision,
        "decision_reason_codes": sorted(set(reason_codes)),
        "decision_semantic_fingerprint": "",
    }
    record["decision_semantic_fingerprint"] = github_projection_decision_semantic_fingerprint(
        record
    )
    record["github_projection_decision_id"] = github_projection_decision_id(record)
    _validate(record, "github_projection_decision.schema.json")
    return record
