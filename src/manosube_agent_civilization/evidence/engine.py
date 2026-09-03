"""The one Evidence deriver: what does the record of this observation actually say?

```text
RAW EVIDENCE REQUEST
→ REQUEST ADMISSION
→ PREDECESSOR REPRODUCTION BY THE CANONICAL OWNERS
→ POSITION DERIVED FROM WHAT WAS REPRODUCED
→ LEVEL DERIVED FROM STRUCTURE
→ CANONICAL EVIDENCE
```

Evidence **records** what was observed. It does not observe, and it does not decide whether
what it records is enough -- that is :mod:`.sufficiency`, against a policy Difference owns.
This module reads no clock, no filesystem, no network, no environment and no agent state.
The recording instant is a required input, because a record whose timestamp came from the
machine that wrote it is a record no reviewer can reproduce.

Three ratified semantics shape everything below (ADR-0029).

**Q1-A + Q1-ii.** Every minimum field of 第28条 is present on every Evidence record. Fields
that do not apply to a position are ``null``, not absent, so "this Evidence carries no
Change" and "this Evidence forgot to say" are different records. State is bound as
``revision + semantic_fingerprint`` and never embedded: a copy of a canonical State inside
an Evidence record is a second State that can disagree with the first.

**Q2-A.** Levels are derived from structure. E4, E5 and E6 stay in the vocabulary and are
refused here, because the Kernel names them and defines no predicate that decides them.

**Q3-A.** Change Result Evidence exists only when there is a post-change Observation to
ground it. Nothing else is renamed into it.

What is deliberately absent from the request is any way to *supply* a predecessor record.
``observation_identity``, ``change_id`` and ``decision_id`` are public pure functions, so a
supplied record can always be re-hashed into perfect internal agreement -- the Phase 5 P1
defect exactly. The request carries the predecessors' **requests**, and this module runs
:func:`observe` and :func:`derive_change` to obtain the records themselves. A forged
predecessor is therefore not refused; it is inexpressible.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from manosube_agent_civilization.authority.errors import AuthorityError
from manosube_agent_civilization.change import derive_change
from manosube_agent_civilization.change.errors import ChangeError
from manosube_agent_civilization.difference.admissibility import require_object
from manosube_agent_civilization.difference.errors import DifferenceError
from manosube_agent_civilization.difference.validation import (
    SCHEMA_BASE as CANONICAL_SCHEMA_BASE,
    validate_record as _validate_canonical_record,
)
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.observation.boundary import instant
from manosube_agent_civilization.observation.errors import ObservationError
from manosube_agent_civilization.state.errors import CanonicalizationError

from .errors import (
    EvidenceError,
    EvidenceValidationError,
    UngroundedChangeResultEvidenceError,
)
from .identity import evidence_id, evidence_semantic_fingerprint
from .levels import completed_attempt_count, derive_level

EVIDENCE_SCHEMA_BASE = CANONICAL_SCHEMA_BASE + "evidence/"
SCHEMA_VERSION = "0.1"

#: The two positions of 第27条. They are derived, never declared: a request that carries a
#: Change request is Change Result Evidence and a request that does not is Observation
#: Evidence, so a caller cannot label a record one thing and populate it as the other.
OBSERVATION_EVIDENCE = "OBSERVATION_EVIDENCE"
CHANGE_RESULT_EVIDENCE = "CHANGE_RESULT_EVIDENCE"

#: Every key an Evidence request may carry. Closed, for the reason ``AUTHORITY_CONTRACT.md``
#: §4 gives: an ignored key is still a channel.
#:
#: Note what is *not* here. There is no ``evidence_level``, no ``status``, no
#: ``evidence_position``, no ``observation`` and no ``change``. Each of those is a conclusion,
#: and a conclusion supplied by the caller is a conclusion this engine did not reach.
REQUIRED_REQUEST_KEYS: frozenset[str] = frozenset(
    {
        "schema_version",
        "recorded_at",
        "observation_request",
        "observation_method_class",
        "change_request",
        "post_change_observation_request",
        "artifact_references",
        "predecessor_evidence_refs",
        "remaining_difference_refs",
    }
)


def _validate(record: dict[str, Any], schema_name: str, base: str, context: str) -> None:
    """Validate against the canonical schema, in Evidence's error vocabulary."""

    try:
        _validate_canonical_record(record, schema_name, base=base)
    except ValueError as error:
        raise EvidenceValidationError(f"{context}: {error}") from error


def _require_request_shape(request: Any) -> dict[str, Any]:
    """Return the request once its key set is exactly the declared one."""

    shaped = require_object(request, "evidence request")
    unknown = set(shaped) - REQUIRED_REQUEST_KEYS
    if unknown:
        raise EvidenceError(f"evidence request carries unknown keys: {sorted(unknown)}")
    missing = REQUIRED_REQUEST_KEYS - set(shaped)
    if missing:
        raise EvidenceError(f"evidence request omits required keys: {sorted(missing)}")
    if shaped["schema_version"] != SCHEMA_VERSION:
        raise EvidenceError(
            f"evidence request declares an unsupported schema_version: {shaped['schema_version']!r}"
        )
    return shaped


def _delegate(owner: Any, request: Any, context: str) -> Any:
    """Call a predecessor owner, and let no unreadable-input crash cross this boundary.

    ``observe`` reads its request keys directly: it has no declared envelope grammar, so an
    absent key surfaces as ``KeyError`` and an unhashable one as ``TypeError`` rather than
    as that owner's refusal. Those are real refusals wearing the wrong type, and a caller of
    *Evidence* must not have to catch them to learn its own request was malformed.

    The translation is deliberately at the call site and nowhere wider. Wrapping the whole
    derivation would swallow a genuine defect in this module's own code, which is the thing
    a broad ``except TypeError`` always eventually does.

    The predecessor-side gap is reported, not taken: declaring an admissibility grammar for
    the Observation request belongs to the phase that owns that request, exactly as
    ``difference/admissibility.py`` was written by the phase that owned its envelope.
    """

    try:
        return owner(require_object(request, context))
    except (KeyError, TypeError, IndexError) as error:
        raise EvidenceError(f"{context} could not be read: {error!r}") from error


def _observe_last(request: dict[str, Any]) -> dict[str, Any]:
    """Run the canonical Observation Engine and return the record it just minted.

    The extraction is inside the function ``_delegate`` guards on purpose. There is no input
    for which ``observe`` returns an empty bundle, so a branch raising "no Observation was
    produced" would be a branch nothing could reach -- protection in appearance only. If that
    postcondition ever changes, the ``IndexError`` becomes an ``EvidenceError`` here rather
    than escaping as a crash, which is the outcome the unreachable branch was reaching for.
    """

    minted: dict[str, Any] = observe(request)["observations"][-1]
    return minted


def _minted_observation(request: Any, context: str) -> dict[str, Any]:
    """Reproduce one Observation through its canonical owner and return the new record.

    ``observe`` appends the Observation it mints to any prior bundle it was given, so the
    record this Evidence is about is the last one. Taking it by position rather than by a
    caller-supplied identity is what keeps the reproduction meaningful: there is no
    parameter here through which a caller could point at a record ``observe`` did not make.
    """

    return deepcopy(_delegate(_observe_last, request, context))


def _typed_references(value: Any, kind: str, context: str) -> list[dict[str, Any]]:
    """Return a deterministic, de-duplicated set of references of exactly one kind."""

    if not isinstance(value, list):
        raise EvidenceError(f"{context} must be a list of references")
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for member in value:
        reference = require_object(member, f"{context} member")
        unknown = set(reference) - {"kind", "id", "digest"}
        if unknown:
            raise EvidenceError(f"{context} member carries unknown keys: {sorted(unknown)}")
        if reference.get("kind") != kind:
            raise EvidenceError(
                f"{context} member is not a {kind} reference: {reference.get('kind')!r}"
            )
        identity = reference.get("id")
        if not isinstance(identity, str) or not identity:
            raise EvidenceError(f"{context} member carries no readable identity")
        key = (kind, identity)
        existing = seen.get(key)
        if existing is not None and existing != reference:
            raise EvidenceError(f"{context} carries two different references for {identity}")
        seen[key] = deepcopy(reference)
    return [seen[key] for key in sorted(seen)]


def _artifact_references(value: Any) -> list[dict[str, Any]]:
    """Return the artifact set, bound by content digest and by nothing mutable.

    An artifact reference binds *integrity*: a content digest, a byte length and a media
    type. It carries no URL, no credential and no host. That is not a convenience -- a
    reference that resolved through a mutable external locator would make whatever is at
    that locator today the authority for what this Evidence says, which is the opposite of
    an immutable record (``E-003``). Where a location matters, an immutable
    ``source_snapshot`` reference the Observation layer already owns may be attached; the
    schema admits that key and no other.
    """

    if not isinstance(value, list):
        raise EvidenceError("artifact_references must be a list")
    seen: dict[str, dict[str, Any]] = {}
    for member in value:
        artifact = require_object(member, "artifact reference")
        identity = artifact.get("id")
        if not isinstance(identity, str) or not identity:
            raise EvidenceError("artifact reference carries no readable identity")
        existing = seen.get(identity)
        if existing is not None and existing != artifact:
            raise EvidenceError(
                f"artifact_references carries two different artifacts for {identity}"
            )
        seen[identity] = deepcopy(artifact)
    return [seen[key] for key in sorted(seen)]


def _state_binding(observation: dict[str, Any]) -> dict[str, Any]:
    """Return an Observation's State binding: revision and fingerprint, never a body."""

    return {
        "state_revision": observation["state_revision_observed"],
        "semantic_fingerprint": deepcopy(observation["state_fingerprint_observed"]),
    }


def _observed_result(observation: dict[str, Any]) -> dict[str, Any]:
    """Return what was observed, copied from the Observation record and judged nowhere.

    Every value here is the Observation owner's own. ``status`` in particular is carried
    through unchanged across all nine of its values, so EMPTY, UNKNOWN, UNOBSERVED, BLOCKED,
    FAILED, INCOMPLETE, INVALID and CONFLICTED each stay themselves. Collapsing any pair of
    them into "no result" is the substitution ``CLOSURE_POLICY.md`` §6 forbids, and the
    place it would happen is here.
    """

    return {
        "observation_ref": {"kind": "observation", "id": observation["observation_id"]},
        "observation_status": observation["status"],
        "blind_spot_status": observation["blind_spots"]["status"],
        "normalized_fact_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(
                deepcopy(observation["normalized_fact_refs"]),
                key=lambda reference: (reference["kind"], reference["id"]),
            ),
        },
        "attempt_outcomes": {
            "collection_kind": "ORDERED_LIST",
            "members": [attempt["result"] for attempt in observation["attempts"]],
        },
    }


def derive_evidence(request: dict[str, Any]) -> dict[str, Any]:
    """Return one canonical Evidence record for one grounded request.

    The returned record is schema-valid and content-addressed: the same grounded observation
    always produces the same ``evidence_id``. *request* is never mutated.

    Every refusal leaves here as an :class:`EvidenceError`. The owners one layer down speak
    their own vocabularies -- Observation, Change, Authority, Difference readability and
    canonical serialization -- and asking all of them is right. Letting any of them escape
    would make a caller of *Evidence* catch an *Observation* error to learn that its own
    request was malformed. The decisions are delegated. The boundary's vocabulary is not.
    """

    try:
        return _derive(request)
    except EvidenceError:
        raise
    except (
        ObservationError,
        ChangeError,
        AuthorityError,
        DifferenceError,
        CanonicalizationError,
    ) as error:
        raise EvidenceError(str(error)) from error


def _derive(request: dict[str, Any]) -> dict[str, Any]:
    request = deepcopy(request)
    shaped = _require_request_shape(request)

    # --- the grounding observation -------------------------------------------- #
    #
    # Reproduced, not supplied. This runs first and unconditionally: if a later admission
    # could refuse ahead of it, the shape of a caller-supplied value would decide whether
    # the canonical Observation ever ran, which is the same defect as trusting the caller,
    # wearing a different hat.
    observation = _minted_observation(shaped["observation_request"], "observation_request")

    change_request = shaped["change_request"]
    post_change_request = shaped["post_change_observation_request"]

    # --- position ------------------------------------------------------------- #
    #
    # 第27条 separates two positions, and this is where the separation is made. It is made
    # from what the request *contains*, so the two cannot be crossed: a record cannot be
    # Observation Evidence carrying a Change, and it cannot be Change Result Evidence
    # carrying no Change.
    if change_request is None:
        if post_change_request is not None:
            raise EvidenceError(
                "a post-change Observation was supplied without a Change: Observation "
                "Evidence records one observation, and a re-observation after a Change that "
                "is not named here is a Change Result Evidence request missing its Change"
            )
        return _observation_evidence(shaped, observation)

    # Q3-A. This is the refusal, and it comes before anything is built, because the record
    # being refused is one that would be false rather than one that is malformed.
    if post_change_request is None:
        raise UngroundedChangeResultEvidenceError(
            "Change Result Evidence requires a post-change Observation to record. v0.1 has "
            "no executor, change.schema.json pins execution_result to null, and an "
            "AUTHORIZED Change is not an EXECUTED one, so there is no result here to "
            "observe. Record the situation as Observation Evidence -- UNKNOWN, BLOCKED or "
            "INCOMPLETE is a truthful status and is not a weaker record than a false one"
        )
    return _change_result_evidence(shaped, observation, change_request, post_change_request)


def _finalize(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence["evidence_semantic_fingerprint"] = evidence_semantic_fingerprint(evidence)
    evidence["evidence_id"] = evidence_id(evidence)
    _validate(evidence, "evidence.schema.json", EVIDENCE_SCHEMA_BASE, "generated evidence")
    return evidence


def _require_recorded_after(recorded_at: Any, observation: dict[str, Any]) -> str:
    """Return the admitted recording instant once it is not before what it records.

    The instant is an input rather than a reading, and this is the one thing that can be
    checked about it without a clock: an Evidence record cannot have been written before the
    Observation it describes finished.

    The comparison goes through ``observation.boundary.instant``, the repository's canonical
    parser, rather than comparing the strings. Lexicographic order looks exact for a
    fixed-width UTC form and is not, because ``common/timestamp.schema.json`` admits optional
    fractional seconds: ``...00.5Z`` sorts *before* ``...00Z`` on ``'.' < 'Z'`` while being
    half a second later. A guard that is wrong on the values it was written to order is worse
    than no guard.
    """

    if not isinstance(recorded_at, str) or not recorded_at:
        raise EvidenceError("recorded_at must be an explicit canonical UTC timestamp")
    ended_at = observation["time_boundary"]["observation_ended_at"]
    try:
        recorded = instant(recorded_at)
        ended = instant(ended_at)
    except ValueError as error:
        raise EvidenceError(f"recorded_at is not a canonical UTC instant: {error}") from error
    if recorded < ended:
        raise EvidenceError(
            f"recorded_at {recorded_at!r} precedes the end of the Observation it records "
            f"({ended_at!r})"
        )
    return recorded_at


def _common(shaped: dict[str, Any], grounding: dict[str, Any]) -> dict[str, Any]:
    """Return the fields both positions share, derived from the grounding Observation."""

    artifacts = _artifact_references(shaped["artifact_references"])
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": "",
        "timestamp": _require_recorded_after(shaped["recorded_at"], grounding),
        "target": {
            "project_id": grounding["project_id"],
            "target_identity": grounding["target"]["target_identity"],
            "kind": grounding["target"]["kind"],
        },
        "observation_method": {
            "method_ref": deepcopy(grounding["method_ref"]),
            "method_class": shaped["observation_method_class"],
        },
        "observed_result": _observed_result(grounding),
        # Carried through from the Observation owner. Evidence does not re-derive a status:
        # a second status deriver is one that can disagree with the first.
        "status": grounding["status"],
        "artifact_references": {"collection_kind": "UNORDERED_SET", "members": artifacts},
        "remaining_differences": {
            "collection_kind": "UNORDERED_SET",
            "members": _typed_references(
                shaped["remaining_difference_refs"], "difference", "remaining_difference_refs"
            ),
        },
        "evidence_level": derive_level(
            shaped["observation_method_class"],
            artifact_reference_count=len(artifacts),
            completed_attempt_count=completed_attempt_count(grounding),
        ),
        "evidence_semantic_fingerprint": "",
    }


def _lineage(shaped: dict[str, Any], derived_from: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "derived_from": {
            "collection_kind": "UNORDERED_SET",
            "members": sorted(derived_from, key=lambda item: (item["kind"], item["id"])),
        },
        "predecessor_evidence_refs": {
            "collection_kind": "UNORDERED_SET",
            "members": _typed_references(
                shaped["predecessor_evidence_refs"], "evidence", "predecessor_evidence_refs"
            ),
        },
    }


def _observation_evidence(shaped: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    """Return Observation Evidence: 第27条's first position, before any Change exists.

    ``after_state``, ``change_identity``, ``authority_used`` and ``expected_result`` are
    ``null``. Q1-C -- reading ``after_state`` as equal to ``before_state`` because nothing
    changed -- is not taken: "nothing changed" is a claim about a second point in time, and
    a second point in time requires a second observation. This record has one.
    """

    evidence = _common(shaped, observation)
    evidence.update(
        {
            "evidence_position": OBSERVATION_EVIDENCE,
            "before_state": _state_binding(observation),
            "change_identity": None,
            "authority_used": None,
            "after_state": None,
            "expected_result": None,
            "lineage": _lineage(
                shaped,
                [{"kind": "observation", "id": observation["observation_id"]}],
            ),
        }
    )
    return _finalize(evidence)


def _change_result_evidence(
    shaped: dict[str, Any],
    before_observation: dict[str, Any],
    change_request: Any,
    post_change_request: Any,
) -> dict[str, Any]:
    """Return Change Result Evidence: 第27条's second position, grounded in re-observation.

    What this record proves is exactly one thing: an after-state was observed. It does not
    prove the Change ran, and it does not prove the Change caused what was seen.

    ```text
    POST_CHANGE_OBSERVATION
    != EXECUTION_RECEIPT
    != CAUSALITY_PROOF
    != E4_PROOF
    ```

    Both refusals to the contrary are structural rather than documentary.
    ``causality_claimed`` and ``execution_receipt_present`` are pinned ``false`` by the
    schema, so no record can carry the opposite; and the level still comes from the method
    class, so a re-observation cannot become 自然経路実行 by being a re-observation.
    """

    # Reproduced through the canonical Change deriver, which itself reproduces the Authority
    # decision through the canonical evaluator. Evidence therefore inherits Phase 5's
    # provenance rather than restating it, and there is no supplied Change to forge.
    change = _delegate(derive_change, change_request, "change_request")
    decision = require_object(
        require_object(change_request, "change_request")["authority_decision"],
        "change_request.authority_decision",
    )

    if before_observation["state_revision_observed"] != change["expected_state_revision"] or (
        before_observation["state_fingerprint_observed"] != change["before_state_fingerprint"]
    ):
        raise EvidenceError(
            "the Observation supplied as this Change's before-state is not the State the "
            f"Change was authorized against: observed revision "
            f"{before_observation['state_revision_observed']} against expected "
            f"{change['expected_state_revision']}"
        )

    after_observation = _minted_observation(post_change_request, "post_change_observation_request")

    # Independence, in the sense CLOSURE_POLICY.md §4 gives it: the Change must not supply
    # its own success flag. The before-picture is not a re-observation, so the same
    # Observation cannot stand on both sides -- that would be the Change certifying itself
    # with the very record that motivated it.
    if after_observation["observation_id"] == before_observation["observation_id"]:
        raise EvidenceError(
            "the post-change Observation is the same Observation as the before-state one: a "
            "re-observation must be a second observation"
        )
    if after_observation["state_revision_observed"] < change["expected_state_revision"]:
        raise EvidenceError(
            "the post-change Observation observed a State revision earlier than the one the "
            f"Change was authorized against: {after_observation['state_revision_observed']} "
            f"< {change['expected_state_revision']}"
        )

    # The level and the status come from the *re-observation*, because the re-observation is
    # what this record evidences. Reading them from the before-picture would let a complete
    # observation of the old state stand in for a missing observation of the new one.
    evidence = _common(shaped, after_observation)
    evidence.update(
        {
            "evidence_position": CHANGE_RESULT_EVIDENCE,
            "before_state": _state_binding(before_observation),
            "change_identity": {
                "kind": "change",
                "id": change["change_id"],
                "change_semantic_fingerprint": change["change_semantic_fingerprint"],
                "idempotency_key": change["idempotency_key"],
                "execution_result": change["execution_result"],
                "causality_claimed": False,
            },
            "authority_used": {
                "kind": "authority_decision",
                "id": decision["authority_decision_id"],
                "decision": decision["decision"],
                "decision_semantic_fingerprint": decision["decision_semantic_fingerprint"],
            },
            "after_state": _state_binding(after_observation),
            "expected_result": {
                "declared_action": deepcopy(change["action"]),
                "declared_scope": deepcopy(change["scope"]),
                "expected_state_revision": change["expected_state_revision"],
                "causality_claimed": False,
                "execution_receipt_present": False,
            },
            "lineage": _lineage(
                shaped,
                [
                    {"kind": "observation", "id": before_observation["observation_id"]},
                    {"kind": "observation", "id": after_observation["observation_id"]},
                    {"kind": "change", "id": change["change_id"]},
                    {"kind": "authority_decision", "id": decision["authority_decision_id"]},
                ],
            ),
        }
    )
    return _finalize(evidence)
