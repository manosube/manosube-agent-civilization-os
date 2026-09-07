"""The one public Independent Verification route (Phase 13, Issue #51).

``INDEPENDENT_VERIFICATION_OWNER_COUNT=1``, ``PUBLIC_VERIFICATION_ENTRY_POINT_COUNT=1``.

``run_independent_verification`` validates an explicit :class:`~manosube_agent_civilization.
independent_verification.types.VerificationRequirement` and the
:class:`~manosube_agent_civilization.independent_verification.types.VerifierSelection` SHUKOU
authorized against it, resolves the one Store-owned kind a target reference may actually name
(``observation_evidence``) through the existing Store's own read-only
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.resolve_record` -- the
identical, already-established reference-resolution surface Boot itself calls, never a second
one -- and calls its explicit
:class:`~manosube_agent_civilization.independent_verification.types.IndependentVerifier`
exactly once. It creates no second State, Evidence, Difference, Authority, Change, Store, or
Closure owner: it never calls ``FileStateStore.initialize``, ``.commit``, ``.recover``,
``.load_current``, ``.read_current_consistent``, ``.reconstruct``, or ``bind_project``, and
never calls into ``evidence``, ``difference``, ``reflow``, or ``binding`` at all -- carrying
an admissible verification result into existing Evidence-sufficiency semantics remains
entirely that existing owner's own, separate concern (frozen semantic decision 6), a concern
this route does not implement any bypass of. It calls into ``authority`` exactly once per
invocation, read-only: the existing Authority owner's own dedicated
:func:`~manosube_agent_civilization.authority.evaluate_verifier_selection` (Structural Review
Round 3, P13-R3-F1) -- never a second Authority owner, registry, token, or cache. Together
with the existing Boot owner's own ``boot_project`` (Structural Review Round 1, P13-R1-F2,
called once, from ``boot`` rather than ``authority``), these are the only two owners this
route reuses by call.

Structural Review Round 1 correction (P13-R1-F2): a caller-supplied
``verifier_selection.selection_authority_ref`` that merely equals
``verification_requirement.selection_authority_ref`` -- both values the same caller
constructed -- proves nothing about SHUKOU's own explicit authorization; two self-consistent
fabricated references satisfy that equality just as well as two genuine ones. This route now
calls the existing, already-established Boot owner
(:func:`~manosube_agent_civilization.boot.boot_project`) exactly once, over an explicit
*project_binding_id* the caller supplies, and requires both references to canonical-
reference-equal the real, independently re-verified ``BootContext.human_authority_ref`` that
call returns -- never a second Authority owner, registry, token, or cache; every
Boot/Binding/Store failure `boot_project` itself already proves fail-closed propagates
unchanged, exactly as `boot/route.py`'s own callers already rely on.

Structural Review Round 1 correction (P13-R1-F1): the callable actually invoked as *verifier*
must declare, on itself, the identical identity SHUKOU selected
(``verifier.verifier_identity``) -- checked by exact equality against
``verifier_selection.verifier_identity`` *before* this route ever calls it, so a mismatched,
absent, or unreadable declared identity never reaches invocation and no arbitrary callable's
output can be attributed to a different, selected verifier.

Structural Review Round 3 correction (P13-R3-F1): the real, Boot-verified
``human_authority_ref`` alone is a necessary precondition, not itself proof that SHUKOU
selected *this* ``verifier_selection`` for *this* ``verification_requirement`` -- two
self-consistent, caller-fabricated references satisfy a mere mapping-equality check just as
well as two genuine ones, the identical gap Round 1 already closed for the Human Authority
reference itself. This route calls the existing Authority owner's own dedicated
:func:`~manosube_agent_civilization.authority.evaluate_verifier_selection` exactly once,
requiring it to answer ``SELECTED`` -- a real, canonical, Human-Authority-declared grant
binding project, requirement, verifier identity, permitted boundary, selection status, and the
real selection authority identity together -- before the verifier is ever called; a
caller-created selection duplicating known-real values without such a grant is refused with
the verifier called zero times, and every ``AuthorityError`` this call itself raises for an
unreadable request propagates unchanged.

Structural Review Round 4 correction (P13-R4, Authority Provenance Bypass, P13-R3-F2): Round
3's own ``evaluate_verifier_selection`` re-verifies a grant's *shape* -- schema-valid,
content-address self-consistent, ``granted_by.kind == "human_authority"`` -- and that its
``granted_by`` equals the real, Boot-verified ``human_authority_ref``. None of that proves the
grant was actually authored by that Human Authority: a ``human_authority_ref`` is not a
secret, so a caller who can supply arbitrary in-memory ``verifier_selection_grant`` *content*
can self-hash a grant whose every field, ``granted_by`` included, merely repeats known-real
values -- the identical class of gap Round 1 already closed for the Human Authority reference
itself, now recurring one layer deeper. This route no longer accepts grant *content* as a
caller-supplied argument at all: it takes an explicit *verifier_selection_grant_refs*
collection of ``{"kind": "verifier_selection_grant", "id": ...}`` references and resolves each
one through the existing Store's own read-only :meth:`~manosube_agent_civilization.store.
file_store.FileStateStore.resolve_record` -- the identical surface, and (Round 4) the
identical single call site, this route already uses to resolve ``observation_evidence``
targets -- before any of the resulting bodies ever reach ``evaluate_verifier_selection``. A
ref naming a record the Store does not durably resolve refuses before the verifier is ever
called, exactly as an unresolvable ``observation_evidence`` target already does; only a grant
that actually reached the same durable, COMMITTED-boundary persistence every other canonical
record in this system relies on can ever bind a selection. This closes
``CALLER_ASSERTED_GRANT_AS_PROVENANCE`` without adding a second Authority owner, registry,
token, or cache: ``evaluate_verifier_selection`` itself is untouched, and still performs the
identical shape/binding checks over whatever content it is given -- only what content this
route is willing to give it has changed.

Structural Review Round 5-R1 correction (P13-R5-R1, Issue #51,
``ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER``): a Human Grant
Declaration's own durable Store commission (P13-R5) still never proved a Human, rather than
any Store-write-capable caller, actually authored it. This route now also reads the real
Project Binding's own ``human_authority_signing_key`` directly off the already deep-frozen,
Boot-verified ``boot_context.project_binding`` mapping -- never a caller-supplied copy -- and
passes it into ``evaluate_verifier_selection`` alongside the resolved grants/declarations, so
Authority independently re-verifies each declaration's own Ed25519 ``signature`` against that
real key before ever answering ``SELECTED``, rather than trusting Binding's own prior
verification at commit time.

Every requirement/selection/boundary/target/authority admission failure raises
:class:`~manosube_agent_civilization.independent_verification.errors.
VerificationRequirementError` before this route ever calls the supplied verifier, and calling
the verifier is this route's own single side effect: no Store write, no second read beyond the
one ``resolve_record`` provenance check per Store-owned target plus the one ``boot_project``
authority re-verification and the one ``evaluate_verifier_selection`` Authority-owned
selection-decision re-verification, and no exception this route catches or reclassifies once
raised, in either direction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from manosube_agent_civilization.authority import SELECTED, evaluate_verifier_selection
from manosube_agent_civilization.boot import boot_project

from .errors import VerificationRequirementError, VerifierOutputError
from .types import (
    SELECTION_STATUSES,
    TARGET_REF_KINDS,
    VERIFICATION_STATUSES,
    IndependentVerifier,
    VerificationRequirement,
    VerificationResult,
    VerifierSelection,
)

#: The one target-reference kind this route ever resolves against the Store -- Difference
#: and Change are never Store-owned record kinds in this vertical
#: (``reflow/reference_registry.py``'s own documented classification), so a ``difference``/
#: ``change`` target is validated for shape alone, never resolved here.
_STORE_RESOLVABLE_TARGET_KIND = "observation_evidence"

#: The one reference kind ``verifier_selection_grant_refs`` may ever name (Structural Review
#: Round 4, P13-R4). A grant is never accepted as caller-supplied content -- only a reference
#: this route itself resolves through the Store.
_VERIFIER_SELECTION_GRANT_REF_KIND = "verifier_selection_grant"

#: The one reference kind ``human_grant_declaration_refs`` may ever name (Structural Review
#: Round 5, P13-R5). A Human Grant Declaration -- the Binding owner's own canonical, read-
#: only-reverifiable anchor proving a Human, not merely a caller, declared a specific grant --
#: is never accepted as caller-supplied content either, for the identical reason grant content
#: itself no longer is (P13-R4).
_HUMAN_GRANT_DECLARATION_REF_KIND = "human_grant_declaration"


def _require_canonical_identity(name: str, value: Any) -> str:
    """Fail closed unless *value* is a plain, non-empty canonical identity string -- never a
    filesystem path, URL, or directory name (frozen semantic decision 9: no Project
    discovery, the caller must supply an explicit canonical identity, never a locator)."""

    if not isinstance(value, str) or not value:
        raise VerificationRequirementError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise VerificationRequirementError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_reference(
    value: Any,
    *,
    context: str,
    allowed_kinds: frozenset[str] | None = None,
    error_cls: type[Exception] = VerificationRequirementError,
) -> dict[str, Any]:
    """Return *value* once it carries a non-empty ``kind``/``id`` pair -- and, if
    *allowed_kinds* is given, once ``kind`` is one of them. Fails closed on any other shape,
    before this route (or its caller) ever treats *value* as a resolvable reference.

    *error_cls* lets one caller (the verifier's own ``input_refs``, validated *after* this
    route's own admission gate has already passed) report a malformed reference as
    :class:`~manosube_agent_civilization.independent_verification.errors.VerifierOutputError`
    rather than :class:`VerificationRequirementError` -- the two error classes are this
    layer's own two distinct boundaries (admission of the caller's own inputs, versus the
    shape of what the supplied verifier returned), and a malformed reference must be
    reported under whichever boundary actually produced it."""

    if not isinstance(value, Mapping):
        raise error_cls(f"{context} must be an explicit reference object: {value!r}")
    kind = value.get("kind")
    identity = value.get("id")
    if not isinstance(kind, str) or not kind:
        raise error_cls(f"{context} carries no readable kind: {value!r}")
    if not isinstance(identity, str) or not identity:
        raise error_cls(f"{context} carries no readable id: {value!r}")
    if allowed_kinds is not None and kind not in allowed_kinds:
        raise error_cls(
            f"{context} names a kind outside its permitted set: {kind!r} not in {sorted(allowed_kinds)}"
        )
    return dict(value)


def _resolve_or_refuse(
    store: Any, project_id: str, *, kind: str, record_id: str, context: str
) -> dict[str, Any]:
    """Return the Store's own committed record for *(kind, record_id)*, or fail closed.

    The one place this route ever calls :meth:`~manosube_agent_civilization.store.
    file_store.FileStateStore.resolve_record` -- shared by ``observation_evidence`` target
    resolution and, since Structural Review Round 4 (P13-R4), ``verifier_selection_grant``
    resolution, so this route's own single-Store-read-surface discipline
    (``VERIFICATION_CONTRACT.md`` §4) is a fact about the source rather than a count that
    happens to hold today."""

    resolved: dict[str, Any] | None = store.resolve_record(project_id, kind, record_id)
    if resolved is None:
        raise VerificationRequirementError(
            f"{context} does not resolve for project {project_id!r}: {kind}/{record_id}"
        )
    return resolved


def _canonical_reference_equal(left: Any, right: Any, *, context: str) -> None:
    """Fail closed unless *left* and *right* are the identical canonical reference/boundary
    -- the same exact-equality convention ``boot/route.py`` already uses for its own
    four-way Human Authority check."""

    if dict(left) != dict(right):
        raise VerificationRequirementError(f"{context}: {dict(left)!r} != {dict(right)!r}")


def run_independent_verification(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    verification_requirement: VerificationRequirement,
    verifier_selection: VerifierSelection,
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
    verifier: IndependentVerifier,
) -> VerificationResult:
    """Run one explicit Independent Verification and return its one immutable result.

    *project_binding_id* (Structural Review Round 1, P13-R1-F2) names the already-bound
    Project whose real Human Authority reference this route re-verifies through the
    existing Boot owner before either selection authority reference is trusted.

    *verifier_selection_grant_refs* (Structural Review Round 3, P13-R3-F1; resolved from the
    Store since Structural Review Round 4, P13-R4) is the caller's own explicit collection of
    ``{"kind": "verifier_selection_grant", "id": ...}`` references -- never grant *content*.
    *human_grant_declaration_refs* (Structural Review Round 5, P13-R5) is the identical shape
    of collection over ``{"kind": "human_grant_declaration", "id": ...}`` references -- the
    Binding owner's own canonical, read-only-reverifiable Human declaration anchors, never
    accepted as content either, for the identical reason. Each ref in both collections is
    resolved through the existing Store's own read-only ``resolve_record`` (the same single
    call site ``observation_evidence`` targets already resolve through); an unresolvable ref
    in either collection refuses before the verifier is ever called. Only the resulting,
    genuinely Store-committed bodies are passed to the existing Authority owner's own
    :func:`~manosube_agent_civilization.authority.evaluate_verifier_selection`, called exactly
    once: the real, Boot-verified Human Authority reference alone is a necessary precondition
    for that decision, never itself the decision that SHUKOU selected *this*
    ``VerifierSelection`` for *this* ``VerificationRequirement``; neither is a grant whose only
    provenance is that a caller supplied it in-process (P13-R4); and neither is a grant whose
    only provenance is that it was, by itself, durably Store-committed, absent a real, matching
    Human Grant Declaration anchoring it (P13-R5).

    See ``08_VERIFICATION/VERIFICATION_CONTRACT.md`` §5 for the full canonical route this
    function implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)

    if not isinstance(verification_requirement, VerificationRequirement):
        raise VerificationRequirementError(
            "verification_requirement must be a VerificationRequirement instance, not "
            f"{type(verification_requirement)!r}"
        )
    if not isinstance(verifier_selection, VerifierSelection):
        raise VerificationRequirementError(
            f"verifier_selection must be a VerifierSelection instance, not {type(verifier_selection)!r}"
        )

    if verification_requirement.project_id != project_id:
        raise VerificationRequirementError(
            "verification_requirement.project_id does not match the requested project_id: "
            f"{verification_requirement.project_id!r} != {project_id!r}"
        )
    if verifier_selection.project_id != project_id:
        raise VerificationRequirementError(
            "verifier_selection.project_id does not match the requested project_id: "
            f"{verifier_selection.project_id!r} != {project_id!r}"
        )
    if verifier_selection.requirement_id != verification_requirement.requirement_id:
        raise VerificationRequirementError(
            "verifier_selection does not apply to the supplied requirement: "
            f"{verifier_selection.requirement_id!r} != {verification_requirement.requirement_id!r}"
        )
    if verifier_selection.status not in SELECTION_STATUSES:
        raise VerificationRequirementError(
            f"verifier_selection.status is not a recognized selection status: "
            f"{verifier_selection.status!r}"
        )
    if verifier_selection.status != "ACTIVE":
        raise VerificationRequirementError(
            f"verifier_selection is not ACTIVE -- {verifier_selection.status!r} may never "
            "authorize a verifier invocation"
        )

    # P13-R1-F2: neither selection_authority_ref is trusted merely because the two
    # caller-supplied values agree with each other -- both are required to canonical-
    # reference-equal the real, independently re-verified Human Authority reference the
    # existing Boot owner returns for this exact project/binding. boot_project's own
    # BootNotFoundError/BootConsistencyError (missing binding, tampered record, wrong
    # project) propagate completely unchanged; this route neither catches nor reclassifies
    # them, and produces no VerificationResult and calls the verifier zero times on any such
    # rejection.
    boot_context = boot_project(store, project_id=project_id, project_binding_id=project_binding_id)
    real_human_authority_ref = boot_context.human_authority_ref
    _canonical_reference_equal(
        verification_requirement.selection_authority_ref,
        real_human_authority_ref,
        context=(
            "verification_requirement.selection_authority_ref vs the real, Boot-verified "
            "Human Authority reference"
        ),
    )
    _canonical_reference_equal(
        verifier_selection.selection_authority_ref,
        real_human_authority_ref,
        context=(
            "verifier_selection.selection_authority_ref vs the real, Boot-verified Human "
            "Authority reference"
        ),
    )
    _canonical_reference_equal(
        verifier_selection.permitted_boundary,
        verification_requirement.verification_boundary,
        context="verifier_selection.permitted_boundary vs verification_requirement.verification_boundary",
    )

    # P13-R4 (Structural Review Round 4, Authority Provenance Bypass, P13-R3-F2): a grant is
    # never accepted as caller-supplied content -- only a {"kind": "verifier_selection_grant",
    # "id": ...} reference this route itself resolves through the Store, exactly as an
    # observation_evidence target already is (via the identical _resolve_or_refuse call
    # site). A ref naming a record the Store does not durably resolve refuses here, before
    # the Authority owner or the verifier is ever reached; only genuinely Store-committed
    # bodies are ever passed to evaluate_verifier_selection below.
    resolved_grants: list[dict[str, Any]] = []
    for index, grant_ref in enumerate(verifier_selection_grant_refs):
        checked_grant_ref = _require_reference(
            grant_ref,
            context=f"verifier_selection_grant_refs[{index}]",
            allowed_kinds=frozenset({_VERIFIER_SELECTION_GRANT_REF_KIND}),
        )
        resolved_grants.append(
            _resolve_or_refuse(
                store,
                project_id,
                kind=checked_grant_ref["kind"],
                record_id=checked_grant_ref["id"],
                context=f"verifier_selection_grant_refs[{index}]",
            )
        )

    # P13-R5 (Structural Review Round 5, canonical Human declaration anchor): a Human Grant
    # Declaration is never accepted as caller-supplied content either -- only a {"kind":
    # "human_grant_declaration", "id": ...} reference this route resolves through the
    # identical Store call site above. An unresolvable ref refuses here, before the Authority
    # owner or the verifier is ever reached, exactly as an unresolvable grant ref already does.
    resolved_declarations: list[dict[str, Any]] = []
    for index, declaration_ref in enumerate(human_grant_declaration_refs):
        checked_declaration_ref = _require_reference(
            declaration_ref,
            context=f"human_grant_declaration_refs[{index}]",
            allowed_kinds=frozenset({_HUMAN_GRANT_DECLARATION_REF_KIND}),
        )
        resolved_declarations.append(
            _resolve_or_refuse(
                store,
                project_id,
                kind=checked_declaration_ref["kind"],
                record_id=checked_declaration_ref["id"],
                context=f"human_grant_declaration_refs[{index}]",
            )
        )

    # P13-R3-F1: the real, Boot-verified Human Authority reference above is a necessary
    # precondition, not itself the decision that SHUKOU selected *this* VerifierSelection for
    # *this* VerificationRequirement -- that decision belongs to the existing Authority
    # owner's own dedicated, read-only surface, re-verified exactly once, before the verifier
    # is ever called. A caller-created selection that merely repeats real_human_authority_ref
    # (or any other field) is never itself an Authority Decision; only a genuine, canonical,
    # Human-Authority-declared verifier_selection_grant binding every one of project_id,
    # requirement_id, verifier_identity, permitted_boundary, selection status, and the real
    # selection authority identity together produces one -- and (P13-R4) only a grant this
    # route itself resolved from the Store above is ever offered as a candidate.
    # P13-R5-R1 (Structural Review Round 5-R1, Issue #51): the real Project Binding's own
    # public verification key, read directly off the already deep-frozen, Boot-verified
    # `boot_context.project_binding` mapping -- never a caller-supplied copy -- so Authority
    # can independently re-verify each declaration's own signature rather than trusting
    # Binding's prior verification at commit time.
    real_human_authority_signing_key = dict(
        boot_context.project_binding["human_authority_signing_key"]
    )

    selection_decision = evaluate_verifier_selection(
        {
            "schema_version": "0.1",
            "project_id": project_id,
            "requirement_id": verification_requirement.requirement_id,
            "selection_id": verifier_selection.selection_id,
            "verifier_identity": dict(verifier_selection.verifier_identity),
            "permitted_boundary": dict(verifier_selection.permitted_boundary),
            "selection_status": verifier_selection.status,
            "human_authority_ref": dict(real_human_authority_ref),
            "human_authority_signing_key": real_human_authority_signing_key,
            "grants": [dict(grant) for grant in resolved_grants],
            "grant_declarations": [dict(declaration) for declaration in resolved_declarations],
        }
    )
    if selection_decision["decision"] != SELECTED:
        raise VerificationRequirementError(
            "verifier_selection is not an Authority-owned SELECTED decision: "
            f"{selection_decision['decision_reason_codes']}"
        )

    if not verification_requirement.target_refs:
        raise VerificationRequirementError(
            "verification_requirement.target_refs must name at least one explicit target"
        )
    for index, target_ref in enumerate(verification_requirement.target_refs):
        checked = _require_reference(
            target_ref,
            context=f"verification_requirement.target_refs[{index}]",
            allowed_kinds=TARGET_REF_KINDS,
        )
        if checked["kind"] == _STORE_RESOLVABLE_TARGET_KIND:
            _resolve_or_refuse(
                store,
                project_id,
                kind=checked["kind"],
                record_id=checked["id"],
                context=f"target_refs[{index}]",
            )

    # P13-R1-F1: the callable actually invoked must declare, on itself, the identical
    # identity SHUKOU selected -- checked before this route ever calls it, so a mismatched,
    # absent, or unreadable declared identity never reaches invocation and no arbitrary
    # callable's output can be attributed to a different, selected verifier.
    declared_identity = getattr(verifier, "verifier_identity", None)
    if not isinstance(declared_identity, Mapping):
        raise VerificationRequirementError(
            "verifier does not declare a readable verifier_identity attribute -- an "
            "unstated or unverifiable identity may never be attributed to the selected "
            "verifier"
        )
    _canonical_reference_equal(
        dict(declared_identity),
        verifier_selection.verifier_identity,
        context="verifier's own declared verifier_identity vs verifier_selection.verifier_identity",
    )

    result_payload = verifier(requirement=verification_requirement, selection=verifier_selection)
    if not isinstance(result_payload, Mapping):
        raise VerifierOutputError(f"verifier returned {result_payload!r}, not a mapping")

    status = result_payload.get("status")
    if status not in VERIFICATION_STATUSES:
        raise VerifierOutputError(f"verifier returned an unrecognized status: {status!r}")

    input_refs_raw = result_payload.get("input_refs")
    if not isinstance(input_refs_raw, list):
        raise VerifierOutputError("verifier's own input_refs must be a list")
    input_refs = [
        _require_reference(
            ref, context=f"verifier input_refs[{index}]", error_cls=VerifierOutputError
        )
        for index, ref in enumerate(input_refs_raw)
    ]

    observations = result_payload.get("observations")
    if not isinstance(observations, Mapping):
        raise VerifierOutputError("verifier's own observations must be an explicit mapping")

    # Frozen semantic decision 5, sharpened by Structural Review Round 2 (P13-R2-F3):
    # indistinguishable implementation and verification provenance does not satisfy
    # independent verification, for every status alike -- UNAVAILABLE is fail-closed, not
    # an exemption from the provenance obligation. A verifier that examined nothing beyond
    # the exact target references it was asked to verify has produced no independent input
    # at all -- it has merely echoed the implementation lineage back; and a verifier that
    # asserts UNAVAILABLE must still cite the explicit boundary/capability/observation/
    # Evidence input that actually grounds why it could not evaluate. Round 0/1's own
    # UNAVAILABLE exemption is superseded here, not merely narrowed.
    target_keys = {(ref["kind"], ref["id"]) for ref in verification_requirement.target_refs}
    input_keys = {(ref["kind"], ref["id"]) for ref in input_refs}
    if not input_keys:
        raise VerifierOutputError(
            "verifier returned no input_refs at all -- every result, including UNAVAILABLE, "
            "must cite what it actually examined"
        )
    if input_keys <= target_keys:
        raise VerifierOutputError(
            "verifier cited no input beyond the target references it was asked to verify "
            "-- implementation-indistinguishable provenance does not satisfy an "
            "independent verification requirement, for any status including UNAVAILABLE"
        )

    return VerificationResult(
        status=status,
        requirement_id=verification_requirement.requirement_id,
        selection_id=verifier_selection.selection_id,
        project_id=project_id,
        target_refs=verification_requirement.target_refs,
        verifier_identity=verifier_selection.verifier_identity,
        selection_authority_ref=verifier_selection.selection_authority_ref,
        verification_boundary=verification_requirement.verification_boundary,
        input_refs=tuple(input_refs),
        observations=dict(observations),
    )
