"""The one public Change Execution receipt-to-Evidence hand-off (Phase 18, Issue #73).

Reuses the identical, already-ratified Change-Free Verification Evidence position
(``evidence/engine.py``'s ``CHANGE_FREE_VERIFICATION_EVIDENCE``)
:mod:`~manosube_agent_civilization.url_boot.evidence_handoff` and
:mod:`~manosube_agent_civilization.runtime.evidence_handoff` both already occupy for their own
bounded, Change-free confirmations -- a completed, bounded, low-risk filesystem execution's own
terminal receipt is structurally the identical kind of independent, Change-free confirmation
input, so this module calls the identical existing owner
(:func:`~manosube_agent_civilization.evidence.derive_evidence`, called exactly once) rather than
adding a second Evidence, Observation, or Reflow owner. This package never itself declares an
Evidence record sufficient, never closes a Difference, and never itself decides completion --
that is exactly the boundary this hand-off exists to respect.

**No re-execution at hand-off.** Corroboration here means resolving the real, committed
``execution_receipt`` this hand-off is given and requiring every one of its own caller-passed
fields to exactly equal what that real, resolved record actually recorded -- never a second
adapter call, and never trusting the caller-passed *receipt* dict directly (the identical
"resolve the real record, never the caller's claim about it" discipline both sibling hand-off
modules already establish).

**``VERIFIED`` requires independent re-observation agreement, not merely a self-reported
``SUCCEEDED`` (P18-R1-F1, Structural Review Round 1).** Before this correction, this module
mapped ``receipt["outcome"] == "SUCCEEDED"`` directly to ``status = "VERIFIED"``, using the
receipt's own ``executor_identity``/``executor_version`` as ``verifier_identity`` -- the executor
self-promoting its own success report into Evidence, with no independent check that the written
files' actual on-disk content matched what was requested. :func:`_construct_provenance` now
additionally requires the resolved receipt's own embedded ``independent_after_state_observation``
(:mod:`~manosube_agent_civilization.change_executor.reobservation`, committed as part of the
receipt itself by ``route.py``) to carry ``outcome == "MATCHED"`` before deriving ``VERIFIED`` --
and, since ``route.py`` itself already refuses to ever commit a ``SUCCEEDED``-outcome receipt
whose own independent re-observation disagrees, a receipt reaching this module with
``outcome == "SUCCEEDED"`` but a disagreeing ``independent_after_state_observation`` should be
structurally unreachable; this module asserts that defensively (raises
:class:`~manosube_agent_civilization.change_executor.errors.ChangeExecutorError`) rather than
silently deriving ``VERIFIED`` for it regardless.

**``VERIFIED`` now additionally requires a SECOND, genuinely independent, handoff-time-only
re-read -- never the executor's own embedded field alone (P18-R2-F1, Structural Review Round
2).** SHUKOU's own adoption of Structural Review Round 2 named the gap the correction directly
above did not close: "an executor-local filesystem re-read embedded in the executor's own receipt
is not, by itself, the independently produced and resolved after-state Observation/Independent
Verification result adopted in Round 1... The executor must not manufacture the fact that
promotes its own receipt." The defensive check the paragraph above describes still only reads
``receipt["independent_after_state_observation"]`` -- a field ``route.py`` itself computed, at
execution time, and simply carried along; trusting it alone to gate ``VERIFIED`` is trusting the
executor's own self-check a second time, under a different name.

:func:`route_change_execution_to_evidence` now itself performs a SECOND, genuinely independent
re-read of the real, current on-disk filesystem state -- entirely separate from, and at a
strictly later instant than, ``route.py``'s own execution-time re-read (:func:`
_second_independent_after_state_reread`) -- and mints a real Observation from it through the one
existing Observation owner (:func:`~manosube_agent_civilization.observation.engine.observe`, via
``evidence.derive_evidence``'s own internal call -- never a caller-supplied Observation record
trusted directly). It builds one real, content-addressed :func:`~manosube_agent_civilization.
observation.source_snapshot.build_source_snapshot` record per file the receipt's own operation
named, from bytes it reads itself, at handoff time; the caller-supplied base ``observation_
request`` (``evidence_request["observation_request"]``, already establishing this exact target's
own ``project_id``/``target_identity``/``target_kind``/``method_ref``/``scope`` shape) is copied
verbatim for those fields, with only ``source_snapshot_refs`` replaced by the freshly-built ones
(or left as the base request's own, unchanged, when there is nothing to independently
re-observe -- an empty operation, e.g. ``KILL_SWITCH_STOPPED``/``BOUNDARY_VIOLATION``/
``UNKNOWN``) and a fresh ``state_revision_observed``/``state_fingerprint_observed`` from a fresh
:meth:`~manosube_agent_civilization.store.FileStateStore.load_current` read. This module therefore
now itself CONSTRUCTS ``verification_observation_request`` (exactly the way it already constructs
and injects ``verification_result_provenance``) rather than trusting whatever a caller supplied --
so *evidence_request* must now carry ``verification_observation_request: None`` (the position
this hand-off itself produces), the mirror image of the pre-existing requirement that
*evidence_request* carry no caller-supplied ``verification_result_provenance``.

A receipt claiming ``outcome == "SUCCEEDED"`` whose own real, current on-disk content (read fresh,
right here, never from the receipt's own embedded field) disagrees with what the receipt's own
``operation`` requested is refused (raises :class:`~manosube_agent_civilization.change_executor.
errors.ChangeExecutorError`) before ``derive_evidence`` is ever called -- a genuine, independent
disagreement this module itself discovers, not a re-check of the same embedded dict. The pre-
existing defensive check against the receipt's own embedded field (paragraph above) remains, as
belt-and-suspenders on the receipt's own internal consistency, but it is no longer what gates
``VERIFIED`` -- this second, independent, handoff-time re-read is.

**The minted verification Observation must itself be resolved back and bound to the receipt's own
target/scope/operation -- never trusted merely because ``derive_evidence`` returned without
raising (P18-R3-F1, Structural Review Round 3).** Structural Review Round 3 named the gap the two
corrections above did not close: this module builds ``verification_observation_request`` and
hands it to ``derive_evidence``, which mints the real verification Observation internally (via
``evidence.engine._change_free_verification_evidence`` -> ``_minted_observation`` ->
``observation.engine.observe()``) -- but, before this correction, the only checks performed on
``derive_evidence``'s return value were ``evidence["verification_result_provenance"] == provenance``
(self-referential: comparing the returned value to the value this module itself constructed) and
``evidence["target"]["project_id"] == project_id``. Neither check ever resolved the freshly-minted
Observation back and independently confirmed it actually grounds the exact
``verification_observation_request`` this module built for this exact receipt. :func:`route_
change_execution_to_evidence` now additionally computes, via the new
:func:`_expected_verification_observation_id`, the exact content-addressed ``observation_id`` that
``observation.engine.observe()`` would mint for the ``verification_observation_request`` this
module itself constructed -- entirely independently recomputed from that request, never trusted
from whatever ``derive_evidence`` happens to report it minted -- and requires the returned
Evidence record's own embedded ``observed_result.observation_ref.id`` to equal it exactly. This is
the identical "resolve and verify a record's own identity by independently recomputing it, without
a Store lookup" pattern :mod:`~manosube_agent_civilization.observation.source_snapshot`'s own
``resolve_source_snapshot`` already establishes in this codebase. A receipt's self-reported
``SUCCEEDED`` outcome can therefore never, by itself, manufacture a ``VERIFIED`` Evidence record --
only a minted verification Observation this module can itself resolve and confirm grounds the
exact request it built may.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.observation import observe
from manosube_agent_civilization.observation.identity import observation_identity
from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot

from .errors import ChangeExecutorError, ExecutionReceiptIntegrityError
from .identity import change_execution_receipt_id, change_execution_receipt_semantic_fingerprint

_RECEIPT_RECORD_KIND = "execution_receipt"

#: The digest :func:`_second_independent_after_state_reread` embeds for a requested delete's own
#: source_snapshot -- there is no real content to digest once a file is gone, so this fixed
#: sentinel (the digest of zero bytes) stands for "genuinely absent," schema-valid either way.
_ABSENT_CONTENT_DIGEST = "sha256:" + hashlib.sha256(b"").hexdigest()

#: The identical ten fields ``evidence.schema.json``'s own ``verification_result_provenance``
#: requires -- see ``url_boot/evidence_handoff.py``'s own identical constant.
REQUIRED_PROVENANCE_FIELDS: tuple[str, ...] = (
    "status",
    "requirement_id",
    "selection_id",
    "project_id",
    "target_refs",
    "verifier_identity",
    "selection_authority_ref",
    "verification_boundary",
    "input_refs",
    "observations",
)

#: (P18-R4-F1) The only :mod:`~manosube_agent_civilization.observation.engine` ``status``
#: values that represent a genuinely resolved, decisive collection outcome -- the minted
#: verification Observation's own status must be one of these before this module will let a
#: ``VERIFIED`` provenance status survive and be returned. ``EMPTY`` is the value a real,
#: fully-successful second re-read of this module's own re-observation produces (it checks
#: on-disk content digests, never asserting domain Facts, so ``has_facts`` is always false);
#: ``COMPLETE`` is included for forward compatibility should a future caller ever attach real
#: Facts. Every other member of the Observation status vocabulary (``INCOMPLETE``, ``UNKNOWN``,
#: ``UNOBSERVED``, ``BLOCKED``, ``FAILED``, ``INVALID``, ``CONFLICTED``) means the Observation
#: owner itself could not decisively resolve this collection -- never an acceptable basis for
#: promoting a receipt's self-reported ``SUCCEEDED`` into ``VERIFIED`` Evidence.
_ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES = frozenset({"COMPLETE", "EMPTY"})

#: Every :data:`~manosube_agent_civilization.change_executor.types.EXECUTION_OUTCOMES` member
#: maps to exactly one of Evidence's own ``verification_result_provenance.status`` vocabulary
#: members (``VERIFIED``/``FAILED``/``INSUFFICIENT``/``UNAVAILABLE``) -- the one shared
#: classification this module reads.
_OUTCOME_TO_PROVENANCE_STATUS: dict[str, str] = {
    "SUCCEEDED": "VERIFIED",
    "REFUSED": "FAILED",
    "BOUNDARY_VIOLATION": "FAILED",
    "STALE_AUTHORITY": "FAILED",
    "TARGET_DRIFT": "FAILED",
    "KILL_SWITCH_STOPPED": "FAILED",
    "TIMEOUT": "UNAVAILABLE",
    "ADAPTER_FAILURE": "FAILED",
    "PARTIAL_MUTATION": "INSUFFICIENT",
    "ROLLBACK_SUCCEEDED": "INSUFFICIENT",
    "ROLLBACK_FAILED": "FAILED",
    "UNKNOWN": "UNAVAILABLE",
    "REOBSERVATION_MISMATCH": "FAILED",
}


def resolve_and_verify_committed_receipt(
    store: Any, project_id: str, change_execution_receipt_id_value: str
) -> dict[str, Any]:
    """Resolve the real, committed ``execution_receipt`` named by
    *change_execution_receipt_id_value* under *project_id*, and require: same project, and its
    own identity and semantic fingerprint, independently recomputed from its own content, equal
    to its own declared values -- **and** equal to the Store lookup key itself (the three-way
    check every sibling hand-off module already applies)."""

    resolved = store.resolve_record(
        project_id, _RECEIPT_RECORD_KIND, change_execution_receipt_id_value
    )
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionReceiptIntegrityError(
            "change_execution_receipt_id does not resolve to a committed execution_receipt for "
            f"project {project_id!r}: {change_execution_receipt_id_value!r}"
        )
    receipt = dict(resolved)
    if receipt.get("project_id") != project_id:
        raise ExecutionReceiptIntegrityError(
            "resolved execution_receipt names a different project than the one being handed "
            f"off: {receipt.get('project_id')!r} != {project_id!r}"
        )
    declared_id = receipt.get("change_execution_receipt_id")
    recomputed_id = change_execution_receipt_id(receipt)
    if change_execution_receipt_id_value != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved execution_receipt's own identity does not agree across the Store lookup "
            f"key, its own declared value, and its own recomputed value -- "
            f"lookup={change_execution_receipt_id_value!r}, declared={declared_id!r}, "
            f"recomputed={recomputed_id!r}"
        )
    if change_execution_receipt_semantic_fingerprint(receipt) != receipt.get(
        "change_execution_receipt_semantic_fingerprint"
    ):
        raise ExecutionReceiptIntegrityError(
            f"resolved execution_receipt {change_execution_receipt_id_value!r} own recomputed "
            "semantic fingerprint does not equal its own declared value -- refusing to trust "
            "any of its fields"
        )
    return receipt


def _reference_set(refs: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    members = [dict(ref) for ref in refs]
    members.sort(key=lambda ref: (ref.get("kind", ""), ref.get("id", "")))
    return {"collection_kind": "UNORDERED_SET", "members": members}


def _construct_provenance(
    receipt: Mapping[str, Any],
    project_id: str,
    *,
    resolved_verification_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the one, deterministic ``verification_result_provenance`` projection this hand-off
    derives -- entirely from the real, resolved, integrity-checked receipt and the real, resolved
    canonical verification Observation, never from any field a caller-constructed receipt dict
    merely claims.

    A receipt claiming ``outcome == "SUCCEEDED"`` whose own embedded
    ``independent_after_state_observation`` does not itself carry ``outcome == "MATCHED"`` is
    refused outright rather than derived as ``VERIFIED`` -- this should be structurally
    unreachable (``route.py`` itself never commits such a combination), so reaching it here means
    something upstream is broken, and this module fails closed rather than silently trust a
    self-reported ``SUCCEEDED`` it cannot itself independently confirm (P18-R1-F1, Structural
    Review Round 1).

    **``status`` for a ``SUCCEEDED`` receipt is DERIVED FROM *resolved_verification_observation*
    itself, never precomputed from the receipt's own outcome (P18-R5-F1, Structural Review Round
    5).** Earlier corrections (P18-R3-F1, P18-R4-F1) still computed ``status = VERIFIED`` from
    ``receipt["outcome"]`` alone, before any canonical Observation existed, and only *vetoed* that
    precomputed status afterward once the Observation was resolved -- SHUKOU's own adopted meaning
    is stronger: ``RECEIPT_OUTCOME_MAY_BE_INPUT_BUT_CANNOT_PRECOMPUTE_PROMOTION``. *
    resolved_verification_observation* is the real record :func:`route_change_execution_to_
    evidence` already resolved, through the one existing canonical Observation owner
    (:func:`~manosube_agent_civilization.observation.engine.observe`), *before* calling this
    function -- so ``VERIFIED`` is only ever derived here from that Observation's own ``status``
    actually being decisive (:data:`_ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES`), never from the
    receipt alone. Its identity and status are also bound directly into this provenance's own
    ``observations`` payload (``canonical_verification_observation``), so the returned record
    itself carries the fact that determined the promotion, not merely receipt-derived material.

    ``verifier_identity`` still names ``executor_identity``/``executor_version`` -- the identical,
    honest framing this package already used before this correction: this package's own re-read
    code (:mod:`~manosube_agent_civilization.change_executor.reobservation`), not the adapter, is
    what actually performed the confirming independent observation, and that re-read is itself
    executed, and its own result committed, under this same executor identity/version -- the field
    names what performed and confirmed the work, not merely what the adapter self-reported."""

    if (
        receipt["outcome"] == "SUCCEEDED"
        and receipt["independent_after_state_observation"].get("outcome") != "MATCHED"
    ):
        raise ChangeExecutorError(
            "resolved execution_receipt claims outcome=SUCCEEDED but its own embedded "
            "independent_after_state_observation does not agree (outcome="
            f"{receipt['independent_after_state_observation'].get('outcome')!r}) -- refusing to "
            "derive VERIFIED for a self-reported success this package cannot itself independently "
            "confirm; route.py should never commit this combination, so reaching this check means "
            "something upstream is broken"
        )

    if receipt["outcome"] == "SUCCEEDED":
        # (P18-R5-F1) VERIFIED is derived from the resolved canonical Observation's own status --
        # the receipt's SUCCEEDED outcome is an input to whether this module even attempts the
        # derivation, never what determines the resulting status by itself.
        if (
            resolved_verification_observation["status"]
            not in _ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES
        ):
            raise ChangeExecutorError(
                "the receipt's own outcome is SUCCEEDED, but the canonical verification "
                "Observation this hand-off resolved through its own owner (observe()) before "
                "constructing provenance did not itself reach a decisive status -- refusing to "
                "derive VERIFIED from anything but that resolved Observation (P18-R5-F1): "
                f"observation_status={resolved_verification_observation['status']!r} not in "
                f"{sorted(_ADMISSIBLE_VERIFIED_OBSERVATION_STATUSES)}"
            )
        status = "VERIFIED"
    else:
        status = _OUTCOME_TO_PROVENANCE_STATUS[receipt["outcome"]]

    receipt_ref = {"kind": _RECEIPT_RECORD_KIND, "id": receipt["change_execution_receipt_id"]}
    refs = (dict(receipt["change_ref"]), receipt_ref)
    slot_key = receipt["execution_request_id"]
    observations = {
        "outcome": receipt["outcome"],
        "performed_result_summary": dict(receipt["performed_result_summary"]),
        "performed_result_fingerprint": receipt["performed_result_fingerprint"],
        "rollback_outcome": receipt["rollback_outcome"],
        "execution_started_at": receipt["execution_started_at"],
        "execution_ended_at": receipt["execution_ended_at"],
        "independent_after_state_observation": dict(receipt["independent_after_state_observation"]),
        # (P18-R5-F1) The canonical verification Observation's own identity and status, bound
        # directly into the returned provenance -- never merely a fact this hand-off checked and
        # discarded.
        "canonical_verification_observation": {
            "observation_ref": {
                "kind": "observation",
                "id": resolved_verification_observation["observation_id"],
            },
            "observation_status": resolved_verification_observation["status"],
        },
    }
    provenance = {
        "status": status,
        "requirement_id": slot_key,
        "selection_id": slot_key,
        "project_id": project_id,
        "target_refs": _reference_set(refs),
        "verifier_identity": {
            "executor_identity": receipt["executor_identity"],
            "executor_version": receipt["executor_version"],
        },
        "selection_authority_ref": dict(receipt["authority_ref"]),
        "verification_boundary": {
            "execution_boundary_fingerprint": receipt["execution_boundary_fingerprint"],
            "target": dict(receipt["target"]),
            "operation": dict(receipt["operation"]),
        },
        "input_refs": _reference_set(refs),
        "observations": observations,
    }
    if set(provenance) != set(REQUIRED_PROVENANCE_FIELDS):
        raise ChangeExecutorError(
            "constructed verification_result_provenance does not carry exactly the required "
            f"field set: {sorted(provenance)} != {sorted(REQUIRED_PROVENANCE_FIELDS)}"
        )
    return provenance


def _second_independent_after_state_reread(
    operation: Mapping[str, Any], worktree_root: str, *, captured_at: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """(P18-R2-F1) Perform a SECOND, genuinely independent, handoff-time-only read-only re-read
    of the actual, current, on-disk filesystem state named by *operation* -- entirely separate
    from, and never trusting, ``route.py``'s own execution-time reobservation embedded on the
    receipt itself. Builds one real, content-addressed
    :func:`~manosube_agent_civilization.observation.source_snapshot.build_source_snapshot` record
    per touched path, from bytes actually read right here -- never from the receipt's own claims.

    Returns ``(source_snapshot records, matching source_occurrences, whether every touched
    path's own real current content matches what the receipt's own operation requested)`` -- the
    third element is this module's own independent gate (never derived from the Observation's own
    facts, which carry none: see this module's own docstring for why)."""

    root = Path(worktree_root)
    snapshots: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    matches = True

    for entry in operation.get("file_writes", []):
        path = entry["path"]
        target = root / path
        try:
            actual_bytes = target.read_bytes() if target.is_file() else b""
        except OSError:
            actual_bytes = b""
        actual_digest = "sha256:" + hashlib.sha256(actual_bytes).hexdigest()
        expected_digest = (
            "sha256:" + hashlib.sha256(entry["content_utf8"].encode("utf-8")).hexdigest()
        )
        if not target.is_file() or actual_digest != expected_digest:
            matches = False
        snapshot = build_source_snapshot(
            source_locator=path, content_digest=actual_digest, captured_at=captured_at
        )
        snapshots.append(snapshot)
        occurrences.append(
            {
                "source_ref": {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]},
                "source_locator": path,
                "outcome": "COMPLETE",
                "facts": [],
            }
        )

    for entry in operation.get("file_deletes", []):
        path = entry["path"]
        target = root / path
        if target.exists() or target.is_symlink():
            matches = False
        snapshot = build_source_snapshot(
            source_locator=path, content_digest=_ABSENT_CONTENT_DIGEST, captured_at=captured_at
        )
        snapshots.append(snapshot)
        occurrences.append(
            {
                "source_ref": {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]},
                "source_locator": path,
                "outcome": "COMPLETE",
                "facts": [],
            }
        )

    return snapshots, occurrences, matches


def _build_verification_observation_request(
    base_request: Mapping[str, Any],
    *,
    project_id: str,
    fresh_state_revision: int,
    fresh_state_fingerprint: Mapping[str, Any],
    snapshots: list[dict[str, Any]],
    occurrences: list[dict[str, Any]],
    captured_at: str,
) -> dict[str, Any]:
    """Build one genuine, ``observe()``-shaped ``verification_observation_request`` -- the
    identical ``project_id``/``target_identity``/``target_kind``/``method_ref``/scope shape
    *base_request* already establishes for this exact target (copied verbatim), bound to a
    *fresh*, handoff-time State revision/fingerprint and a fresh time_boundary, and carrying
    either the real, freshly-captured ``source_snapshot_refs`` this hand-off itself just read
    (when *snapshots* is non-empty), or the base request's own unchanged ``source_snapshot_refs``
    (when there is nothing to independently re-observe -- an empty operation). This request is
    never itself trusted as an Observation: it is handed to ``derive_evidence``, which mints the
    real record through the one existing Observation owner (``observation.engine.observe()``),
    never accepting a caller-supplied Observation record directly.

    (P18-R4-F1) The Scope's own ``observation_window``/``cutoff`` are rebuilt around *captured_at*
    itself, rather than left at *base_request*'s own (necessarily earlier, pre-execution)
    values -- ``observation.boundary.time_boundary_within_scope`` requires this fresh
    Observation's own ``observation_started_at``/``observation_ended_at`` (both *captured_at*)
    to fall inside the Scope's ``observation_window``, and its ``source_snapshot_time`` (also
    *captured_at*) to fall at or before the Scope's own ``cutoff``; copying the base Scope's
    stale window verbatim made every genuine handoff-time re-read fail that check and degrade to
    ``INCOMPLETE`` regardless of what was actually found on disk -- the exact defect Structural
    Review Round 4 (P18-R4-F1) named. A real ``attempts`` entry is built too (one, representing
    this module's own single collection attempt over every touched path), required for
    ``observe()`` to ever report a resolved ``EMPTY``/``COMPLETE`` status instead of falling
    through to ``UNKNOWN`` for want of any attempt record at all."""

    base_scope = base_request["scope"]
    scope = dict(base_scope)
    scope["observation_window"] = {"start": captured_at, "end": captured_at}
    scope["cutoff"] = captured_at
    if snapshots:
        new_refs = [
            {"kind": "source_snapshot", "id": snapshot["source_snapshot_id"]}
            for snapshot in snapshots
        ]
        scope["source_snapshot_refs"] = new_refs
        top_level_refs = new_refs
    else:
        top_level_refs = list(base_scope["source_snapshot_refs"])

    effective_window = base_scope["target_effective_window"]
    time_boundary = {
        "observation_started_at": captured_at,
        "observation_ended_at": captured_at,
        "target_effective_start": effective_window["start"],
        "target_effective_end": effective_window["end"],
        "source_snapshot_time": captured_at,
    }
    method_ref = dict(base_request["method_ref"])

    # (P18-R4-F1) One real attempt, representing this module's own single collection attempt
    # over every touched path -- required for observe() to ever resolve a decisive EMPTY/
    # COMPLETE status (see observation.engine._observation_status: with zero attempts it always
    # falls through to UNKNOWN, regardless of how many source_occurrences are present). "EMPTY"
    # is the honest result: this module's own occurrences never carry Facts (it verifies on-disk
    # content digests, never asserts domain Facts), so has_facts is always false here. When there
    # is nothing to observe (an empty operation), no attempt is built -- that path is only ever
    # reached for a non-SUCCEEDED outcome, which never derives VERIFIED regardless.
    attempts = (
        [
            {
                "attempt_id": "VERIFICATION-REREAD-ATTEMPT-0001",
                "method_ref": dict(method_ref),
                "started_at": captured_at,
                "ended_at": captured_at,
                "result": "EMPTY",
                "failure_class": None,
            }
        ]
        if occurrences
        else []
    )

    return {
        "project_id": project_id,
        "state_revision_observed": fresh_state_revision,
        "state_fingerprint_observed": dict(fresh_state_fingerprint),
        "target_identity": base_request["target_identity"],
        "target_kind": base_request["target_kind"],
        "scope": scope,
        "method_ref": method_ref,
        "time_boundary": time_boundary,
        "source_snapshot_refs": top_level_refs,
        "normalization_profile": base_request["normalization_profile"],
        "source_occurrences": occurrences,
        "attempts": attempts,
        "blind_spots": [],
        "observation_evidence_refs": [],
        "negative_evidence_refs": [],
        "negative_claims": [],
        "collection_complete": True,
    }


def _expected_verification_observation_id(
    verification_observation_request: Mapping[str, Any],
) -> str:
    """(P18-R3-F1) Independently recompute the exact ``observation_id``
    :func:`~manosube_agent_civilization.observation.engine.observe` would mint for
    *verification_observation_request* -- the identical ``observation_identity_payload``
    projection ``observe()`` itself builds internally from a request (see
    ``observation/engine.py``'s own ``observe`` for the canonical construction this mirrors),
    computed here entirely from the request THIS module built, never trusted from whatever
    ``derive_evidence`` happens to return. Used to resolve the minted verification Observation
    back and bind it to the receipt's own target/scope/operation, closing the gap Structural
    Review Round 3 named: a receipt's self-reported ``SUCCEEDED`` outcome must never be what
    determines ``VERIFIED`` -- only a genuinely resolved-and-checked Observation may."""

    canonical_source_refs = sorted(
        (dict(ref) for ref in verification_observation_request["source_snapshot_refs"]),
        key=lambda reference: (reference["kind"], reference["id"]),
    )
    payload = {
        "project_id": verification_observation_request["project_id"],
        "state_revision_observed": verification_observation_request["state_revision_observed"],
        "state_fingerprint_observed": dict(
            verification_observation_request["state_fingerprint_observed"]
        ),
        "target": {
            "target_identity": verification_observation_request["target_identity"],
            "kind": verification_observation_request["target_kind"],
        },
        "scope_ref": {
            "kind": "observation_scope",
            "id": verification_observation_request["scope"]["scope_id"],
        },
        "method_ref": dict(verification_observation_request["method_ref"]),
        "time_boundary": dict(verification_observation_request["time_boundary"]),
        "source_snapshot_refs": canonical_source_refs,
        "normalization_profile": verification_observation_request["normalization_profile"],
    }
    return observation_identity(payload)


def route_change_execution_to_evidence(
    store: Any, receipt: Mapping[str, Any], project_id: str, evidence_request: Mapping[str, Any]
) -> dict[str, Any]:
    """Hand *receipt* off to the existing Evidence owner and return the one canonical Evidence
    record it derives from *evidence_request*.

    *receipt* is never trusted directly: this function resolves the real, committed
    ``execution_receipt`` its own ``change_execution_receipt_id`` names, and requires every field
    of the passed-in *receipt* to exactly equal the corresponding field of that resolved record
    before deriving anything.

    *evidence_request* must already be a real, Change-free Evidence request carrying a genuine
    ``observation_request`` (see :mod:`manosube_agent_civilization.evidence.engine` for its own
    real, complete request shape, which this function follows exactly) -- but, since P18-R2-F1
    (Structural Review Round 2), must carry ``verification_observation_request: None``: this
    function now constructs that field itself, from a second, independent, handoff-time-only
    re-read of the real resulting filesystem state (never from whatever a caller supplied), the
    identical way it already constructs and injects ``verification_result_provenance``, and
    re-verifies the derived record actually carries exactly what it constructed before returning
    it.

    Every :class:`~manosube_agent_civilization.evidence.errors.EvidenceError` the existing owner
    itself raises propagates unchanged.
    """

    if not isinstance(receipt, Mapping):
        raise ChangeExecutorError(f"receipt must be a mapping, not {type(receipt)!r}")
    receipt_id = receipt.get("change_execution_receipt_id")
    if not isinstance(receipt_id, str) or not receipt_id:
        raise ChangeExecutorError("receipt carries no readable change_execution_receipt_id")
    if receipt.get("project_id") != project_id:
        raise ChangeExecutorError(
            "receipt's own originating project_id does not match the requested project_id -- a "
            f"receipt cannot be relabelled across projects: {receipt.get('project_id')!r} != "
            f"{project_id!r}"
        )

    resolved = resolve_and_verify_committed_receipt(store, project_id, receipt_id)

    # Complete receipt attestation required, the identical discipline both sibling hand-off
    # modules already establish: every one of *receipt*'s own Evidence-relevant fields must
    # exactly equal the real, resolved receipt's own content before any Evidence is derived. A
    # receipt forged in any single field, even with every other field genuine, refuses here.
    for field in (
        "execution_request_id",
        "change_ref",
        "idempotency_key",
        "authority_ref",
        "project_binding_ref",
        "boot_state_fingerprint",
        "execution_boundary_fingerprint",
        "executor_identity",
        "executor_version",
        "target",
        "operation",
        "execution_started_at",
        "execution_ended_at",
        "outcome",
        "performed_result_fingerprint",
        "performed_result_summary",
        "rollback_outcome",
        "claim_token",
        "reobservation_request",
        "independent_after_state_observation",
    ):
        if dict(receipt).get(field) != resolved.get(field):
            raise ChangeExecutorError(
                f"receipt's own {field} does not match the real, committed execution_receipt's "
                f"own {field}"
            )

    if not isinstance(evidence_request, Mapping):
        raise ChangeExecutorError(
            f"evidence_request must be an explicit mapping, not {type(evidence_request)!r}"
        )
    if evidence_request.get("change_request") is not None:
        raise ChangeExecutorError(
            "evidence_request must be Change-free -- a Change Execution receipt never executes "
            "or grounds a new Change"
        )
    if evidence_request.get("post_change_observation_request") is not None:
        raise ChangeExecutorError(
            "evidence_request must carry no post_change_observation_request -- a Change "
            "Execution receipt never grounds a Change result"
        )
    if evidence_request.get("verification_observation_request") is not None:
        raise ChangeExecutorError(
            "evidence_request must not already carry a verification_observation_request -- this "
            "hand-off constructs it itself, from a second, independent, handoff-time-only "
            "re-read of the real resulting filesystem state (P18-R2-F1), never from whatever a "
            "caller already supplied"
        )
    if evidence_request.get("observation_request") is None:
        raise ChangeExecutorError(
            "evidence_request must carry a real observation_request establishing this exact "
            "target's own project_id/target_identity/target_kind/method_ref/scope shape -- this "
            "hand-off copies that shape verbatim when building its own verification_observation_"
            "request (P18-R2-F1)"
        )
    if evidence_request.get("verification_result_provenance") is not None:
        raise ChangeExecutorError(
            "evidence_request must not already carry a verification_result_provenance -- this "
            "hand-off constructs it from the real, resolved execution_receipt itself"
        )

    # (P18-R2-F1, Structural Review Round 2) A SECOND, genuinely independent, handoff-time-only
    # re-read of the real, current on-disk filesystem state -- entirely separate from, and never
    # trusting, route.py's own execution-time reobservation already embedded on *resolved*
    # itself. captured_at reuses evidence_request's own caller-supplied recorded_at (this
    # package reads no ambient clock anywhere, the identical discipline route.py itself keeps)
    # as the bounded instant this second re-read is captured at.
    captured_at = evidence_request.get("recorded_at")
    if not isinstance(captured_at, str) or not captured_at:
        raise ChangeExecutorError(
            "evidence_request.recorded_at must be a real, non-empty instant -- reused as the "
            "bounded instant this hand-off's own second, independent, handoff-time re-read is "
            "captured at (P18-R2-F1)"
        )
    snapshots, occurrences, reread_matches_requested = _second_independent_after_state_reread(
        resolved["operation"], resolved["target"]["worktree_root"], captured_at=captured_at
    )
    if resolved["outcome"] == "SUCCEEDED" and not reread_matches_requested:
        raise ChangeExecutorError(
            "a second, independent, handoff-time-only re-read of the real resulting filesystem "
            "state disagrees with what the receipt's own operation requested -- refusing to "
            "derive VERIFIED for a self-reported SUCCEEDED this hand-off cannot itself "
            "independently confirm (P18-R2-F1): an executor-local re-read embedded in the "
            "receipt itself is never, by itself, sufficient to promote the executor's own receipt"
        )
    fresh_state = store.load_current(project_id)
    verification_observation_request = _build_verification_observation_request(
        evidence_request["observation_request"],
        project_id=project_id,
        fresh_state_revision=fresh_state["state_revision"],
        fresh_state_fingerprint=fresh_state["semantic_fingerprint"],
        snapshots=snapshots,
        occurrences=occurrences,
        captured_at=captured_at,
    )

    # (P18-R5-F1, Structural Review Round 5) Resolve the real canonical verification Observation
    # THROUGH THE ONE EXISTING OBSERVATION OWNER (observe()) itself, BEFORE constructing
    # provenance -- so VERIFIED is derived from that resolved Observation's own status, never
    # precomputed from the receipt's outcome and only vetoed afterward. Calling observe() here
    # and letting derive_evidence's own internal call mint the identical record for the identical
    # request (observe() is pure/deterministic -- see observation/engine.py's own docstring) is
    # calling the existing single owner twice and cross-verifying agreement; it does not create a
    # second canonical owner.
    resolved_verification_bundle = observe(verification_observation_request)
    resolved_verification_observation = resolved_verification_bundle["observations"][-1]

    provenance = _construct_provenance(
        resolved, project_id, resolved_verification_observation=resolved_verification_observation
    )
    request = dict(evidence_request)
    request["verification_observation_request"] = verification_observation_request
    request["verification_result_provenance"] = provenance

    evidence = derive_evidence(request)

    # (P18-R3-F1) Resolve the minted verification Observation back and bind it to the receipt's
    # own target/scope/operation: the returned Evidence's own embedded Observation reference
    # must equal the identity this module independently recomputes from the exact
    # verification_observation_request it built (never derive_evidence's own internal claim
    # about what it minted). A SUCCEEDED receipt's own self-report never determines VERIFIED by
    # itself -- only this genuinely resolved-and-checked Observation binding does.
    expected_verification_observation_id = _expected_verification_observation_id(
        verification_observation_request
    )
    if (
        evidence["observed_result"]["observation_ref"]["id"] != expected_verification_observation_id
        or expected_verification_observation_id
        != resolved_verification_observation["observation_id"]
    ):
        raise ChangeExecutorError(
            "the derived Evidence record's own grounding Observation does not match the "
            "identity this hand-off independently recomputed from the exact "
            "verification_observation_request it built, and/or does not match the identity of "
            "the canonical Observation this hand-off itself resolved through the existing "
            "Observation owner before constructing provenance -- refusing to trust a VERIFIED "
            "promotion this hand-off cannot itself resolve and confirm (P18-R3-F1, P18-R5-F1): "
            f"evidence={evidence['observed_result']['observation_ref']['id']!r}, "
            f"recomputed={expected_verification_observation_id!r}, "
            f"resolved={resolved_verification_observation['observation_id']!r}"
        )
    # (P18-R5-F1) The returned Evidence's own observation_status must EXACTLY equal the resolved
    # canonical Observation's own status -- never merely fall within an admissible set checked
    # only when the receipt's outcome happened to precompute VERIFIED (P18-R4-F1's weaker,
    # post-call-veto framing, which this stricter exact-equality check now subsumes). This is the
    # stronger meaning SHUKOU's own Round 5 adoption named:
    # RECEIPT_OUTCOME_MAY_BE_INPUT_BUT_CANNOT_PRECOMPUTE_PROMOTION -- the resolved Observation's
    # own status is what the returned Evidence must actually carry, in every case, not only when
    # convenient to check.
    if (
        evidence["observed_result"]["observation_status"]
        != resolved_verification_observation["status"]
    ):
        raise ChangeExecutorError(
            "the derived Evidence record's own observed_result.observation_status does not "
            "exactly equal the resolved canonical verification Observation's own status this "
            "hand-off itself obtained through the existing Observation owner before "
            "constructing provenance -- refusing to trust a status derive_evidence reports that "
            "disagrees with the Observation this hand-off can itself resolve and confirm "
            f"(P18-R4-F1, P18-R5-F1): evidence="
            f"{evidence['observed_result']['observation_status']!r} != "
            f"resolved={resolved_verification_observation['status']!r}"
        )
    if evidence["verification_result_provenance"] != provenance:
        raise ChangeExecutorError(
            "the derived Evidence record's own verification_result_provenance does not exactly "
            "equal the one this hand-off constructed from the real execution_receipt -- refusing "
            "to return a record whose provenance this hand-off cannot confirm"
        )
    if evidence["target"]["project_id"] != project_id:
        raise ChangeExecutorError(
            "the derived Evidence record names a different project than requested: "
            f"{evidence['target']['project_id']!r} != {project_id!r}"
        )

    return evidence


__all__ = [
    "REQUIRED_PROVENANCE_FIELDS",
    "resolve_and_verify_committed_receipt",
    "route_change_execution_to_evidence",
]
