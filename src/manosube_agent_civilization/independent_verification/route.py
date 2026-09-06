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
``.load_current``, ``.read_current_consistent``, or ``.reconstruct``, never calls
``bind_project`` or ``boot_project``, and never calls into ``evidence``, ``difference``, or
``reflow`` at all -- carrying an admissible verification result into existing Evidence-
sufficiency semantics remains entirely that existing owner's own, separate concern (frozen
semantic decision 6), a concern this route does not implement any bypass of.

Every requirement/selection/boundary/target admission failure raises
:class:`~manosube_agent_civilization.independent_verification.errors.
VerificationRequirementError` before this route ever calls the supplied verifier, and calling
the verifier is this route's own single side effect: no Store write, no second read beyond the
one ``resolve_record`` provenance check per Store-owned target, and no exception this route
catches or reclassifies once raised, in either direction.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
    verification_requirement: VerificationRequirement,
    verifier_selection: VerifierSelection,
    verifier: IndependentVerifier,
) -> VerificationResult:
    """Run one explicit Independent Verification and return its one immutable result.

    See ``08_VERIFICATION/VERIFICATION_CONTRACT.md`` §5 for the full canonical route this
    function implements, step by step.
    """

    _require_canonical_identity("project_id", project_id)

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
    _canonical_reference_equal(
        verifier_selection.selection_authority_ref,
        verification_requirement.selection_authority_ref,
        context=(
            "verifier_selection.selection_authority_ref vs "
            "verification_requirement.selection_authority_ref"
        ),
    )
    _canonical_reference_equal(
        verifier_selection.permitted_boundary,
        verification_requirement.verification_boundary,
        context="verifier_selection.permitted_boundary vs verification_requirement.verification_boundary",
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
            resolved = store.resolve_record(project_id, checked["kind"], checked["id"])
            if resolved is None:
                raise VerificationRequirementError(
                    f"target_refs[{index}] does not resolve for project {project_id!r}: "
                    f"{checked['kind']}/{checked['id']}"
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

    # Frozen semantic decision 5: indistinguishable implementation and verification
    # provenance does not satisfy independent verification. A verifier that examined nothing
    # beyond the exact target references it was asked to verify has produced no independent
    # input at all -- it has merely echoed the implementation lineage back. UNAVAILABLE is
    # the one exempt status: it asserts the verifier could not evaluate at all, so it is
    # never expected to have examined anything (disclosed interpretation, not a silent
    # narrowing -- see the completion report for this round).
    if status != "UNAVAILABLE":
        target_keys = {(ref["kind"], ref["id"]) for ref in verification_requirement.target_refs}
        input_keys = {(ref["kind"], ref["id"]) for ref in input_refs}
        if not input_keys:
            raise VerifierOutputError(
                "verifier returned no input_refs at all -- a non-UNAVAILABLE result must cite "
                "what it actually examined"
            )
        if input_keys <= target_keys:
            raise VerifierOutputError(
                "verifier cited no input beyond the target references it was asked to verify "
                "-- implementation-indistinguishable provenance does not satisfy an "
                "independent verification requirement"
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
