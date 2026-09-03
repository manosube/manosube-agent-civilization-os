"""Evidence Sufficiency: is what was recorded strong enough, fresh enough, and present?

```text
DIFFERENCE OWNS   the Closure Policy schema
                  the Evidence Sufficiency Result schema
                  Difference Closure itself

EVIDENCE OWNS     the production of a Sufficiency Result
```

That split is not a design choice made here; it is what the frozen tree already says.
``01_SCHEMA/difference/closure_policy.schema.json`` and
``evidence_sufficiency_result.schema.json`` exist and are Difference's.
``difference/engine.py`` *carries* sufficiency results forward and never mints one, and
``ADR-0009`` records the section as ``NOT CLAIMED — LATER PHASE``. There was no producer.
This module is that producer, and it creates no second policy owner, no second result
schema, and no second answer to whether a Difference closes.

**What this module decides.** Three things, and it says so: are there Evidence records at
all, is the weakest of them at or above the policy's floor, and is every one of them inside
the policy's age bound as measured from an instant the caller admitted. Nothing else.

**What it does not decide,** and names rather than silently skips: required claims, required
invariants, allowed terminal states, reopen conditions, the contradiction policy, and
observation scope completeness. Those are Difference's closure gates. A ``SUFFICIENT``
result here is not a closure, and :data:`NOT_EVALUATED_HERE` is in the return value so no
caller has to take that on trust.
"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from manosube_agent_civilization.difference.admissibility import require_object
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.identity import (
    closure_policy_id,
    policy_semantic_fingerprint,
)
from manosube_agent_civilization.difference.policy import closure_policy_semantic_errors
from manosube_agent_civilization.difference.validation import (
    DIFFERENCE_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.observation.boundary import instant
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes

from .engine import derive_evidence
from .errors import EvidenceError, EvidenceValidationError
from .levels import EVIDENCE_LEVEL_SCALE, level_index, weakest

SCHEMA_VERSION = "0.1"

#: Every key a sufficiency request may carry.
#:
#: ``evidence_requests`` rather than ``evidence_records``, for the reason ``engine.py`` gives
#: at length: a supplied record can be re-hashed into agreement with itself, so the only way
#: to know an Evidence record is one this Kernel produced is to produce it.
REQUIRED_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "difference_ref",
        "closure_policy",
        "completion_semantics_ref",
        "evidence_requests",
        "evaluation_instant",
    }
)

#: The Closure Policy fields this module does not evaluate, with the owner that does. Public
#: and asserted by a test, so "sufficiency passed" can never be read as "closure passed".
NOT_EVALUATED_HERE: tuple[str, ...] = (
    "required_claims",
    "required_invariants",
    "required_observation_scope",
    "allowed_terminal_states",
    "contradiction_policy",
    "reopen_conditions",
)

#: One code per distinguishable condition. The canonical result carries four values, which
#: is Difference's schema and not ours to widen; without these, EMPTY, BLOCKED, FAILED,
#: UNKNOWN, UNOBSERVED, INCOMPLETE, CONFLICTED, absence and staleness would all arrive at a
#: reader as the same word. ``NO_RESULT != PROVEN_ABSENCE`` is only true if something
#: preserves the difference, and this is that something.
REASON_CODES: tuple[str, ...] = (
    "SUFFICIENT",
    "EVIDENCE_ABSENT",
    "EVIDENCE_LEVEL_BELOW_MINIMUM",
    "EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6",
    "EVIDENCE_AGE_EXCEEDED",
    "EVIDENCE_FUTURE_DATED",
    "EVIDENCE_STATUS_EMPTY",
    "EVIDENCE_STATUS_INCOMPLETE",
    "EVIDENCE_STATUS_UNKNOWN",
    "EVIDENCE_STATUS_UNOBSERVED",
    "EVIDENCE_STATUS_BLOCKED",
    "EVIDENCE_STATUS_FAILED",
    "EVIDENCE_STATUS_INVALID",
    "EVIDENCE_STATUS_CONFLICTED",
)

#: An Evidence status that settles the question against sufficiency. The observation ran and
#: did not stand up.
_DETERMINATE_INSUFFICIENT_STATUSES: dict[str, str] = {
    "BLOCKED": "EVIDENCE_STATUS_BLOCKED",
    "FAILED": "EVIDENCE_STATUS_FAILED",
    "INVALID": "EVIDENCE_STATUS_INVALID",
    "CONFLICTED": "EVIDENCE_STATUS_CONFLICTED",
}

#: An Evidence status that leaves the question open. The observation did not settle it
#: either way, and reporting INSUFFICIENT would assert a negative that was never observed.
_INDETERMINATE_STATUSES: dict[str, str] = {
    "INCOMPLETE": "EVIDENCE_STATUS_INCOMPLETE",
    "UNKNOWN": "EVIDENCE_STATUS_UNKNOWN",
    "UNOBSERVED": "EVIDENCE_STATUS_UNOBSERVED",
}


def evidence_level_scale_digest() -> str:
    """Return the digest of the ordered scale this module applies.

    ``CLOSURE_POLICY.md`` §5 requires G12 to resolve the scale from the exact canonical
    source by content-addressed blob reference. A pure function cannot open a file, so the
    obligation is split: the scale is pinned in :mod:`.levels`, this digest addresses the
    pin, a caller must present the blob reference whose recorded digest equals it, and
    ``tests/contract/evidence/test_evidence_level_scale_source.py`` proves the pin equals
    what ``00_KERNEL/COMPLETION_SEMANTICS.md`` chapter 3 actually says.

    Each half is checkable. Neither half alone would be: a pin nobody compares to the
    document can drift, and a document nobody addresses can be swapped underneath a policy.
    """

    return hashlib.sha256(
        canonical_json_bytes({"evidence_level_scale": list(EVIDENCE_LEVEL_SCALE)})
    ).hexdigest()


def _require_request_shape(request: Any) -> dict[str, Any]:
    shaped = require_object(request, "evidence sufficiency request")
    unknown = set(shaped) - REQUIRED_REQUEST_KEYS
    if unknown:
        raise EvidenceError(f"evidence sufficiency request carries unknown keys: {sorted(unknown)}")
    missing = REQUIRED_REQUEST_KEYS - set(shaped)
    if missing:
        raise EvidenceError(f"evidence sufficiency request omits required keys: {sorted(missing)}")
    if shaped["schema_version"] != SCHEMA_VERSION:
        raise EvidenceError(
            "evidence sufficiency request declares an unsupported schema_version: "
            f"{shaped['schema_version']!r}"
        )
    return shaped


def _require_scale_source(value: Any) -> dict[str, Any]:
    """Return the completion-semantics blob reference once it addresses *this* scale."""

    reference = require_object(value, "completion_semantics_ref")
    required = {
        "kind",
        "repository",
        "commit_sha",
        "path",
        "blob_sha",
        "evidence_level_scale_sha256",
    }
    unknown = set(reference) - required
    if unknown:
        raise EvidenceError(f"completion_semantics_ref carries unknown keys: {sorted(unknown)}")
    missing = required - set(reference)
    if missing:
        raise EvidenceError(f"completion_semantics_ref omits required keys: {sorted(missing)}")
    if reference["kind"] != "git_blob":
        raise EvidenceError(
            f"completion_semantics_ref must be a git_blob reference: {reference['kind']!r}"
        )
    if reference["path"] != "00_KERNEL/COMPLETION_SEMANTICS.md":
        raise EvidenceError(
            "completion_semantics_ref must address the canonical Evidence Level source: "
            f"{reference['path']!r}"
        )
    expected = evidence_level_scale_digest()
    if reference["evidence_level_scale_sha256"] != expected:
        raise EvidenceError(
            "completion_semantics_ref addresses a different Evidence Level scale than the "
            f"one being applied: {reference['evidence_level_scale_sha256']!r} != {expected!r}"
        )
    return deepcopy(reference)


def _require_policy(value: Any, difference_ref: dict[str, Any]) -> dict[str, Any]:
    """Return the Closure Policy once Difference's own schema has admitted it.

    The schema is Difference's and is applied unchanged. That is where
    ``independent_verification_required`` is pinned to ``false``, so this module neither
    restates nor re-decides it: a policy demanding independent verification is rejected by
    the owner that pinned it, and ``verification_independence_ref`` stays null because
    Phase 6 produces no independence record at all.
    """

    policy = require_object(value, "closure_policy")
    try:
        _validate_canonical_record(
            policy, "closure_policy.schema.json", base=DIFFERENCE_SCHEMA_BASE
        )
    except ValueError as error:
        raise EvidenceValidationError(f"closure_policy: {error}") from error

    errors = closure_policy_semantic_errors(policy, "closure_policy")
    if errors:
        raise EvidenceError(sorted(errors)[0])

    subject = policy["subject_difference_ref"]
    if subject.get("kind") != difference_ref.get("kind") or subject.get("id") != difference_ref.get(
        "id"
    ):
        raise EvidenceError(
            "closure_policy governs a different Difference than the one being evaluated: "
            f"{subject.get('id')!r} != {difference_ref.get('id')!r}"
        )

    # The address, recomputed from the Policy's *content* through Difference's own identity
    # functions. This closes the gap ``difference/conformance.py`` names: a caller could
    # otherwise lower ``minimum_evidence_level``, keep the stored identity, and have this
    # module evaluate a floor nobody ratified.
    #
    # Only the identity is checked here, and the omission is deliberate rather than an
    # oversight. ``closure_policy_semantic_errors`` above already recomputes
    # ``policy_semantic_fingerprint`` and refuses a Policy whose stored digest disagrees with
    # its own requirements, so a second comparison of that digest could never fail. A check
    # that cannot fail reads as protection and provides none, which is worse than no check
    # at all; the division of labour is asserted in
    # ``tests/contract/evidence/test_sufficiency_ownership.py`` so it stays visible.
    identity = closure_policy_id(policy_semantic_fingerprint(policy), str(subject.get("id")))
    if policy["closure_policy_id"] != identity:
        raise EvidenceError(
            "closure_policy identity does not match the policy it names: "
            f"{policy['closure_policy_id']!r} != {identity!r}"
        )
    return deepcopy(policy)


def _require_difference_ref(value: Any) -> dict[str, Any]:
    reference = require_object(value, "difference_ref")
    unknown = set(reference) - {"kind", "id", "digest"}
    if unknown:
        raise EvidenceError(f"difference_ref carries unknown keys: {sorted(unknown)}")
    if reference.get("kind") != "difference":
        raise EvidenceError(f"difference_ref must be a difference reference: {reference!r}")
    if not isinstance(reference.get("id"), str) or not reference["id"]:
        raise EvidenceError("difference_ref carries no readable identity")
    return deepcopy(reference)


def _age_seconds(recorded_at: str, evaluated_at: str) -> int:
    """Return whole seconds between an Evidence timestamp and the evaluation instant.

    Negative means the Evidence is dated after the evaluation, which is not an age.
    """

    delta = instant(evaluated_at) - instant(recorded_at)
    return int(delta.total_seconds())


def evaluate_sufficiency(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Evidence Sufficiency Result, plus what it does not say.

    The canonical record is exactly Difference's ``evidence_sufficiency_result.schema.json``
    and carries its four values. Everything the four values cannot express -- which
    condition produced them, which Evidence contributed, what was deliberately not
    evaluated -- is returned beside it rather than folded into it.
    """

    try:
        return _evaluate(request)
    except EvidenceError:
        raise
    except (DifferenceError, ValueError) as error:
        raise EvidenceError(str(error)) from error


def _evaluate(request: dict[str, Any]) -> dict[str, Any]:
    shaped = _require_request_shape(deepcopy(request))
    difference_ref = _require_difference_ref(shaped["difference_ref"])
    policy = _require_policy(shaped["closure_policy"], difference_ref)
    _require_scale_source(shaped["completion_semantics_ref"])

    evaluated_at = shaped["evaluation_instant"]
    if not isinstance(evaluated_at, str) or not evaluated_at:
        raise EvidenceError("evaluation_instant must be an explicit canonical UTC timestamp")
    # Reading a clock here would make this evaluation unreproducible, and an unreproducible
    # freshness verdict is one no reviewer can check. The instant is admitted, not observed.
    instant(evaluated_at)

    requests = shaped["evidence_requests"]
    if not isinstance(requests, list):
        raise EvidenceError("evidence_requests must be a list")
    records = [derive_evidence(require_object(item, "evidence request")) for item in requests]

    maximum_age = policy["maximum_evidence_age"]
    minimum_level = policy["minimum_evidence_level"]

    reason_codes: set[str] = set()
    stale = False
    determinate_insufficient = False
    indeterminate = False
    evaluations: list[dict[str, Any]] = []

    for record in records:
        age = _age_seconds(record["timestamp"], evaluated_at)
        if age < 0:
            reason_codes.add("EVIDENCE_FUTURE_DATED")
            stale = True
        elif maximum_age is not None and age > maximum_age:
            reason_codes.add("EVIDENCE_AGE_EXCEEDED")
            stale = True
        status = record["status"]
        if status in _DETERMINATE_INSUFFICIENT_STATUSES:
            reason_codes.add(_DETERMINATE_INSUFFICIENT_STATUSES[status])
            determinate_insufficient = True
        elif status in _INDETERMINATE_STATUSES:
            reason_codes.add(_INDETERMINATE_STATUSES[status])
            indeterminate = True
        elif status == "EMPTY":
            # A proven-empty observation is a real observation, and downgrading it here would
            # be this module answering Target Satisfaction, which is Difference's question.
            # The code is recorded so the distinction survives into the caller's hands.
            reason_codes.add("EVIDENCE_STATUS_EMPTY")
        evaluations.append(
            {
                "evidence_ref": {"kind": "evidence", "id": record["evidence_id"]},
                "evidence_level": record["evidence_level"],
                "status": status,
                "recorded_at": record["timestamp"],
                "age_seconds": age,
            }
        )

    if not records:
        reason_codes.add("EVIDENCE_ABSENT")
        determinate_insufficient = True
        effective_level = EVIDENCE_LEVEL_SCALE[0]
    else:
        # 件数で補ってはならない: a claim is only as strong as the weakest thing it rests on,
        # so more weak Evidence never raises the effective level.
        effective_level = weakest([record["evidence_level"] for record in records])

    if minimum_level not in {"E0", "E1", "E2", "E3"}:
        # Q2-A. The policy is held, not weakened: a floor Phase 6 cannot reach stays
        # unreached, and the Difference stays open.
        reason_codes.add("EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6")
        determinate_insufficient = True
    elif records and level_index(effective_level) < level_index(minimum_level):
        reason_codes.add("EVIDENCE_LEVEL_BELOW_MINIMUM")
        determinate_insufficient = True

    if stale:
        result = "STALE"
    elif determinate_insufficient:
        result = "INSUFFICIENT"
    elif indeterminate:
        result = "UNKNOWN"
    else:
        result = "SUFFICIENT"
        reason_codes.add("SUFFICIENT")

    sufficiency = {
        "schema_version": SCHEMA_VERSION,
        "evidence_sufficiency_id": "",
        "difference_ref": difference_ref,
        "policy_ref": {
            "kind": "closure_policy",
            "id": policy["closure_policy_id"],
            "version": policy["policy_version"],
            "semantic_fingerprint": policy["policy_semantic_fingerprint"],
        },
        "evidence_level": effective_level,
        "evidence_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(
                ({"kind": "evidence", "id": record["evidence_id"]} for record in records),
                key=lambda reference: reference["id"],
            ),
        },
        "result": result,
        "evaluated_at": evaluated_at,
    }
    sufficiency["evidence_sufficiency_id"] = (
        "EVID-SUFF-"
        + hashlib.sha256(
            canonical_json_bytes(
                {
                    key: value
                    for key, value in sufficiency.items()
                    if key != "evidence_sufficiency_id"
                }
            )
        )
        .hexdigest()
        .upper()
    )
    try:
        _validate_canonical_record(
            sufficiency, "evidence_sufficiency_result.schema.json", base=DIFFERENCE_SCHEMA_BASE
        )
    except ValueError as error:
        raise EvidenceValidationError(f"generated evidence sufficiency result: {error}") from error

    return {
        "evidence_sufficiency_result": sufficiency,
        "reason_codes": sorted(reason_codes),
        "evidence_level_evaluations": sorted(
            evaluations, key=lambda item: str(item["evidence_ref"]["id"])
        ),
        "not_evaluated_here": list(NOT_EVALUATED_HERE),
    }
