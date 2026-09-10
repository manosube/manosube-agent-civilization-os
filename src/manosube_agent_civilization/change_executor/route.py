"""The one public Change Executor route (Phase 18, Issue #73).

``CHANGE_EXECUTOR_OWNER_COUNT=1``, ``PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2``
(:func:`compose_change_executor` ``+1`` :func:`~manosube_agent_civilization.change_executor.
evidence_handoff.route_change_execution_to_evidence`).

The closure :func:`compose_change_executor` returns executes one already-AUTHORIZED, canonical
Change record -- resolved and re-verified by reproduction, never trusted from a caller -- only
inside an explicit, closed, low-risk Execution Boundary, and only when a human kill switch is
resolved fresh and ``ACTIVE`` at two separate checkpoints. It produces exactly one immutable
``change_execution_receipt`` and then stops: it creates no Authority, updates no canonical
State's semantic content beyond its own three new record kinds, proves no causality, establishes
no sufficient Evidence, closes no Difference, and declares no completion -- it hands off to the
existing Evidence/Observation/Reflow owners (:mod:`~manosube_agent_civilization.change_executor.
evidence_handoff`) rather than becoming a new owner of any of them.

Structurally rhymes throughout with :mod:`manosube_agent_civilization.url_boot.route`'s own
``compose_url_source_observer`` -- data canonicalized once at composition, a fresh
:func:`~manosube_agent_civilization.boot.boot_project` Boot on every request, route-owned
outcome classification never asserted by the replaceable adapter, and route-owned commits with
bounded Compare-And-Swap retry through the Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition`).

Canonical route, in the exact order every request-facing call performs it:

```text
canonicalize + freeze execution_boundary / adapter_identity                (composition, once)
→ execution_instant falls within the bound Boundary's own validity_window  (zero-call refusal)
→ kill switch check #1 -- fresh resolve, ACTIVE required, signature re-verified
→ idempotency-slot resolution: an existing receipt (replay/reuse/mismatch), an existing attempt
  with no receipt (reconciliation required), or neither (proceed) -- deliberately *before* Boot
  and staleness; see this module's own disclosed judgment call 5 below for why
→ fresh Boot                                                  (only reached for a genuinely new
                                                                 mapping slot)
→ resolve the Change, recompute-and-compare its own identity/fingerprint
→ resolve the Authority Decision the Change names, recompute-and-compare, require AUTONOMOUS
→ require action_kind in the bound Boundary's own permitted_action_kinds, and not Human-only
→ require scope.repository/branch/paths are entirely admitted by the bound Boundary
→ staleness: before_state_fingerprint / expected_state_revision must equal the fresh Boot's own
→ commit execution_intent                                    (RecordConflictError -> concurrent
                                                                claim)
→ commit execution_attempt                                   (RecordConflictError -> concurrent
                                                                claim)
→ kill switch check #2 -- fresh resolve again, immediately before the one adapter call; a
  refusal here still produces a terminal receipt (KILL_SWITCH_STOPPED), never a bare exception,
  because an execution_attempt is already committed and idempotency requires a terminal outcome
→ build + validate the closed operation against the bound Boundary's own file-count/byte/path
  limits; a violation here likewise produces a terminal receipt (BOUNDARY_VIOLATION), never a
  bare exception, for the identical reason
→ call adapter.execute(...) exactly once for the primary requested operation (a distinct,
  policy-gated best-effort rollback call may follow, only when the primary call partially
  mutated and rollback_policy == BEST_EFFORT_DELETE_WRITTEN_FILES -- see this module's own
  disclosed judgment call below)
→ classify the adapter's raw reported facts into one EXECUTION_OUTCOMES member -- never trusted
  from the adapter as an assertion
→ build + commit the terminal change_execution_receipt (with the embedded reobservation_request)
→ return {"receipt": ..., "replay": bool, "semantic_reuse": bool}
```

A terminal replay/semantic-reuse return, and a refusal detected at idempotency-slot resolution
itself, both leave here with zero Boot, zero Store commit, and zero adapter calls. Every
exception path from idempotency-slot resolution through staleness likewise raises before any
Store commit and before the adapter is ever constructed a call to.

**Disclosed judgment calls**, each also restated at the point in this module where it matters:

1. **The return shape is a small envelope, not the bare receipt.** The seeding task description
   asks for an idempotent replay to "return the existing receipt unchanged" and a disclosed
   semantic reuse to return it "with a distinguishable field/flag" -- but
   ``execution_receipt.schema.json`` is closed (``additionalProperties: false``), so no such flag
   can be added to the immutable receipt record itself without becoming a second, undeclared
   schema. :func:`compose_change_executor`'s returned closure therefore always returns
   ``{"receipt": <the exact, unmodified change_execution_receipt>, "replay": bool,
   "semantic_reuse": bool}`` -- a uniform envelope across every code path (a genuinely first
   execution returns both flags ``False``), so "unchanged" is satisfied for the nested receipt
   itself in every case, and the distinguishing flag lives one level out instead of inside the
   closed record.
2. **``execution_started_at``/``execution_ended_at`` both come from the one caller-supplied
   ``execution_instant``.** The request-facing closure's own call shape -- handed down verbatim
   from the task description as ``(change_id, claim_token, execution_instant, worktree_root,
   permit_semantic_reuse)`` -- carries exactly one instant, and this package reads no clock
   anywhere. Both receipt timestamp fields are therefore set to that one instant; a deployment
   that genuinely needs the two to differ would need to extend the request shape itself, which
   this delivery does not do without being asked.
3. **A kill-switch refusal at checkpoint #2, and a Boundary-limit violation discovered while
   building the operation, both produce a terminal receipt rather than a raised exception.** By
   that point an ``execution_attempt`` is already durably committed; this package's own
   idempotency contract requires *some* terminal receipt to exist for a committed attempt (a bare
   exception here would leave the slot permanently stuck in "attempt exists, no receipt" --
   ``ExecutionReconciliationRequiredError`` forever, with no path to resolution). ``KILL_SWITCH_
   STOPPED`` and ``BOUNDARY_VIOLATION`` are both named, closed members of ``EXECUTION_OUTCOMES``
   for exactly this reason.
4. **The best-effort rollback call is a second, distinct, explicitly policy-gated adapter call,
   not a violation of "call adapter.execute(...) exactly once."** That requirement governs
   dispatch of the one *primary*, requested operation; ``rollback_policy ==
   "BEST_EFFORT_DELETE_WRITTEN_FILES"`` is a Boundary-declared, closed, distinct recovery action,
   only ever reached after a partial or failed primary call, and only ever deletes exactly the
   paths the primary call's own raw facts say it wrote -- never a second attempt at the original
   operation.
5. **Idempotency-slot resolution runs before Boot/Change/Authority/staleness, not after.** This
   package's own test suite demonstrated a genuine ordering defect in an earlier draft of this
   function: every commit this route performs (``execution_intent``, ``execution_attempt``,
   ``change_execution_receipt``) unconditionally advances the project's own ``state_revision`` by
   one, regardless of outcome. A staleness check performed *before* replay detection therefore
   made the very first successful ``execute()`` call for a Change make every subsequent call for
   it -- including an ordinary same-``claim_token`` replay -- spuriously refuse as stale, never
   reaching replay/reuse resolution at all: the exact opposite of what P18-C5's own idempotency
   contract requires. The mapping-slot key is a pure function of *change_id* (a caller-supplied
   parameter) and the two fingerprints already bound at composition time, so resolving it needs
   neither Boot nor the resolved Change record; moving it first means a terminal outcome -- which
   already reflects a fully-vetted prior execution -- is returned unchanged with zero Boot, zero
   Change/Authority resolution, and zero staleness re-check, and the live current State is Booted
   and stale-checked only for a genuinely new mapping slot, for which it is the correct State to
   check against.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.authority import AUTONOMOUS
from manosube_agent_civilization.authority.identity import (
    decision_id as _decision_id,
    decision_semantic_fingerprint as _decision_semantic_fingerprint,
)
from manosube_agent_civilization.authority.levels import HUMAN_ONLY_ACTION_KINDS
from manosube_agent_civilization.authority.scope import canonical_scope
from manosube_agent_civilization.binding.signature import verify_ed25519_signature
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id_of,
    change_semantic_fingerprint as _change_semantic_fingerprint_of,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .boundary import (
    canonicalize_inert_data,
    deep_freeze,
    execution_boundary_fingerprint,
    path_is_admitted,
    require_within_time_window,
    validate_execution_boundary,
)
from .engine import build_change_execution_receipt, build_execution_attempt, build_execution_intent
from .errors import (
    ChangeExecutorError,
    ExecutionAdapterError,
    ExecutionAuthorityProvenanceError,
    ExecutionConcurrentClaimError,
    ExecutionKillSwitchError,
    ExecutionReceiptIntegrityError,
    ExecutionReconciliationRequiredError,
    ExecutionTerminalClaimMismatchError,
    StaleExecutionInputError,
)
from .identity import (
    change_execution_receipt_id as _change_execution_receipt_id_of,
    change_execution_receipt_semantic_fingerprint,
    execution_attempt_id as _execution_attempt_id_of,
    execution_attempt_semantic_fingerprint,
    execution_mapping_slot_key,
)
from .kill_switch import kill_switch_signing_payload, resolve_current_kill_switch

_CHANGE_RECORD_KIND = "change"
_AUTHORITY_DECISION_RECORD_KIND = "authority_decision"
_INTENT_RECORD_KIND = "execution_intent"
_ATTEMPT_RECORD_KIND = "execution_attempt"
_RECEIPT_RECORD_KIND = "execution_receipt"

#: The identical bounded Compare-And-Swap retry ``url_boot/route.py``'s own ``_commit_envelope``
#: uses -- bounded protection against genuine, unrelated contention only.
_MAX_COMMIT_RETRIES = 8


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ChangeExecutorError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise ChangeExecutorError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ChangeExecutorError(f"{name} must be a non-empty string: {value!r}")
    return value


def _commit_records(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    committed_at: str,
    *,
    transaction_prefix: str,
) -> dict[str, Any]:
    """The one Store-commit template every commit in this module shares -- copied, in shape,
    from ``url_boot/route.py``'s own ``_commit_envelope``: bounded Compare-And-Swap retry
    against genuine, unrelated contention only. ``RecordConflictError`` -- a real identity/
    content conflict -- is never swallowed into a retry; it is raised bare, and every call site
    in this module translates it into its own typed error."""

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        transition = {
            "schema_version": "0.1",
            "transaction_id": transaction_id,
            "event_type": "TRANSITION",
            "project_id": project_id,
            "from_revision": current_state["state_revision"],
            "to_revision": next_state["state_revision"],
            "before_fingerprint": current_state["semantic_fingerprint"],
            "after_fingerprint": next_state["semantic_fingerprint"],
            "after_state": next_state,
            "evidence_refs": [],
            "committed_at": committed_at,
        }
        try:
            return commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=records,
            )
        except RecordConflictError:
            raise
        except StaleStateError:
            continue
    raise ChangeExecutorError(
        f"could not durably commit under transaction prefix {transaction_prefix!r} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


def _require_active_kill_switch_verified(
    store: Any, project_id: str, trust_anchor_public_key_hex: str, *, stage: str
) -> None:
    """Resolve the current kill switch fresh, require it to exist and be ``ACTIVE``
    (:mod:`~manosube_agent_civilization.change_executor.kill_switch`'s own tamper-checked
    resolve), **and** independently re-verify its own signature against
    *trust_anchor_public_key_hex* -- defense in depth beyond what commit-time verification
    alone already establishes, appropriate to a control whose entire purpose is to be trusted
    at the exact moment it is checked, not merely once, historically, when it was minted."""

    current = resolve_current_kill_switch(store, project_id)
    if current is None:
        raise ExecutionKillSwitchError(
            f"no change_executor_kill_switch is currently admitted for project {project_id!r} "
            f"-- refusing to execute ({stage})"
        )
    if current.get("status") != "ACTIVE":
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for project {project_id!r} is not ACTIVE "
            f"({current.get('status')!r}) -- refusing to execute ({stage})"
        )
    signature = current.get("signature")
    signature_hex = signature.get("value") if isinstance(signature, dict) else None
    if not isinstance(signature_hex, str) or not verify_ed25519_signature(
        public_key_hex=trust_anchor_public_key_hex,
        message=kill_switch_signing_payload(current),
        signature_hex=signature_hex,
    ):
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for project {project_id!r} carries no "
            f"genuine signature by the bound trust anchor -- refusing to execute ({stage})"
        )


def _resolve_change(store: Any, project_id: str, change_id: str) -> dict[str, Any]:
    resolved = store.resolve_record(project_id, _CHANGE_RECORD_KIND, change_id)
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionAuthorityProvenanceError(
            f"change_id does not resolve to a committed change for project {project_id!r}: "
            f"{change_id!r}"
        )
    change = dict(resolved)
    if change.get("project_id") != project_id:
        raise ExecutionAuthorityProvenanceError(
            f"resolved change names a different project than the one being executed against: "
            f"{change.get('project_id')!r} != {project_id!r}"
        )
    declared_id = change.get("change_id")
    recomputed_id = _change_id_of(change)
    if change_id != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved change's own identity does not agree across the Store lookup key, its own "
            f"declared value, and its own recomputed value -- lookup={change_id!r}, "
            f"declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if _change_semantic_fingerprint_of(change) != change.get("change_semantic_fingerprint"):
        raise ExecutionReceiptIntegrityError(
            f"resolved change {change_id!r} own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to trust any of its fields"
        )
    if change.get("status") != "AUTHORIZED":
        raise ExecutionAuthorityProvenanceError(
            f"resolved change {change_id!r} own status is not AUTHORIZED: {change.get('status')!r}"
        )
    return change


def _resolve_authority_decision(
    store: Any, project_id: str, decision_id_value: str
) -> dict[str, Any]:
    resolved = store.resolve_record(project_id, _AUTHORITY_DECISION_RECORD_KIND, decision_id_value)
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionAuthorityProvenanceError(
            "the change's own authority_ref does not resolve to a committed authority_decision "
            f"for project {project_id!r}: {decision_id_value!r}"
        )
    decision = dict(resolved)
    if decision.get("project_id") != project_id:
        raise ExecutionAuthorityProvenanceError(
            "resolved authority_decision names a different project than the one being executed "
            f"against: {decision.get('project_id')!r} != {project_id!r}"
        )
    declared_id = decision.get("authority_decision_id")
    recomputed_id = _decision_id(decision)
    if decision_id_value != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved authority_decision's own identity does not agree across the Store lookup "
            f"key, its own declared value, and its own recomputed value -- "
            f"lookup={decision_id_value!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if _decision_semantic_fingerprint(decision) != decision.get("decision_semantic_fingerprint"):
        raise ExecutionReceiptIntegrityError(
            f"resolved authority_decision {decision_id_value!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return decision


def _resolve_slot_record(
    store: Any, project_id: str, kind: str, slot_key: str
) -> dict[str, Any] | None:
    resolved = store.resolve_record(project_id, kind, slot_key)
    if resolved is None:
        return None
    return dict(resolved)


def _verify_slot_record(
    record: Mapping[str, Any],
    *,
    kind: str,
    declared_id_field: str,
    recompute_id: Callable[[Mapping[str, Any]], str],
    recompute_fingerprint: Callable[[Mapping[str, Any]], str],
    fingerprint_field: str,
    slot_key: str,
) -> dict[str, Any]:
    checked = dict(record)
    declared_id = checked.get(declared_id_field)
    if slot_key != declared_id or recompute_id(checked) != declared_id:
        raise ExecutionReceiptIntegrityError(
            f"resolved {kind}'s own identity does not agree across the Store lookup key, its "
            f"own declared value, and its own recomputed value -- lookup={slot_key!r}, "
            f"declared={declared_id!r}"
        )
    if recompute_fingerprint(checked) != checked.get(fingerprint_field):
        raise ExecutionReceiptIntegrityError(
            f"resolved {kind} {slot_key!r} own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to trust any of its fields"
        )
    return checked


def _operation_violation_reason(
    action_kind: str, operation: Any, boundary: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate *operation* -- the Change's own opaque ``action.operation`` payload -- against
    the closed :class:`~manosube_agent_civilization.change_executor.types.ExecutionOperation`
    shape and the bound Boundary's own file-count/byte/path limits. Returns ``(checked_operation,
    None)`` when admissible, or ``(None, reason)`` otherwise -- never raises: a well-typed
    operation that would exceed a limit, and a malformed operation payload alike, are both a
    normal, expected, typed terminal outcome (``BOUNDARY_VIOLATION``) this route's own caller
    needs a receipt for, not a bare exception."""

    if not isinstance(operation, Mapping):
        return None, "action.operation is not a mapping"
    if operation.get("operation_kind") != action_kind:
        return None, "action.operation.operation_kind does not equal the Change's own action_kind"
    writes = operation.get("file_writes")
    deletes = operation.get("file_deletes")
    if not isinstance(writes, list) or not isinstance(deletes, list):
        return None, "action.operation.file_writes/file_deletes must both be lists"

    checked_writes: list[dict[str, str]] = []
    checked_deletes: list[dict[str, str]] = []
    touched_paths: set[str] = set()
    total_bytes = 0
    max_file_bytes = boundary["max_file_bytes"]

    for entry in writes:
        if not isinstance(entry, Mapping):
            return None, "a file_writes entry is not a mapping"
        path = entry.get("path")
        content = entry.get("content_utf8")
        if type(path) is not str or not path or type(content) is not str:
            return None, "a file_writes entry has an unreadable path or content_utf8"
        if not path_is_admitted(path, boundary["admitted_paths"]):
            return None, f"path is not admitted by the bound Boundary: {path!r}"
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > max_file_bytes:
            return (
                None,
                f"file exceeds max_file_bytes: {path!r} ({content_bytes} > {max_file_bytes})",
            )
        total_bytes += content_bytes
        touched_paths.add(path)
        checked_writes.append({"path": path, "content_utf8": content})

    for entry in deletes:
        if not isinstance(entry, Mapping):
            return None, "a file_deletes entry is not a mapping"
        path = entry.get("path")
        if type(path) is not str or not path:
            return None, "a file_deletes entry has an unreadable path"
        if not path_is_admitted(path, boundary["admitted_paths"]):
            return None, f"path is not admitted by the bound Boundary: {path!r}"
        touched_paths.add(path)
        checked_deletes.append({"path": path})

    if not touched_paths:
        return None, "action.operation names no file_writes and no file_deletes"
    if len(touched_paths) != len(checked_writes) + len(checked_deletes):
        return (
            None,
            "action.operation names the identical path in both file_writes and file_deletes",
        )
    if len(touched_paths) > boundary["max_files_changed"]:
        return None, (
            f"operation touches {len(touched_paths)} files, exceeding max_files_changed "
            f"({boundary['max_files_changed']})"
        )
    if total_bytes > boundary["max_bytes_changed"]:
        return None, (
            f"operation writes {total_bytes} bytes, exceeding max_bytes_changed "
            f"({boundary['max_bytes_changed']})"
        )

    return {
        "operation_kind": action_kind,
        "file_writes": checked_writes,
        "file_deletes": checked_deletes,
    }, None


def _validate_adapter_report(raw: Any, operation: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ExecutionAdapterError(f"adapter.execute returned {raw!r}, not a mapping")
    files_written = raw.get("files_written")
    bytes_written = raw.get("bytes_written")
    files_deleted = raw.get("files_deleted")
    error = raw.get("error")
    if type(files_written) is not list or not all(type(p) is str for p in files_written):
        raise ExecutionAdapterError(
            f"adapter reported an unreadable files_written: {files_written!r}"
        )
    if type(bytes_written) is not int or isinstance(bytes_written, bool) or bytes_written < 0:
        raise ExecutionAdapterError(
            f"adapter reported an unreadable bytes_written: {bytes_written!r}"
        )
    if type(files_deleted) is not list or not all(type(p) is str for p in files_deleted):
        raise ExecutionAdapterError(
            f"adapter reported an unreadable files_deleted: {files_deleted!r}"
        )
    if error is not None and type(error) is not str:
        raise ExecutionAdapterError(f"adapter reported an unreadable error: {error!r}")

    requested_writes = {entry["path"] for entry in operation["file_writes"]}
    requested_deletes = {entry["path"] for entry in operation["file_deletes"]}
    unexpected_written = set(files_written) - requested_writes
    unexpected_deleted = set(files_deleted) - requested_deletes
    if unexpected_written or unexpected_deleted:
        raise ExecutionAdapterError(
            "adapter reported touching paths outside the admitted operation -- refusing to trust "
            f"a report naming written={sorted(unexpected_written)} deleted={sorted(unexpected_deleted)}"
        )
    return {
        "files_written": list(files_written),
        "bytes_written": bytes_written,
        "files_deleted": list(files_deleted),
        "error": error,
    }


def _classify_outcome(raw: dict[str, Any], operation: Mapping[str, Any]) -> str:
    requested_writes = {entry["path"] for entry in operation["file_writes"]}
    requested_deletes = {entry["path"] for entry in operation["file_deletes"]}
    complete = (
        set(raw["files_written"]) == requested_writes
        and set(raw["files_deleted"]) == requested_deletes
    )
    touched_anything = bool(raw["files_written"]) or bool(raw["files_deleted"])
    if raw["error"] is None and complete:
        return "SUCCEEDED"
    if touched_anything:
        return "PARTIAL_MUTATION"
    return "ADAPTER_FAILURE"


def _attempt_rollback(adapter: Any, worktree_root: str, files_written: list[str]) -> str:
    """Attempt to delete exactly the files the primary call reported writing -- a distinct,
    explicitly policy-gated second call to the adapter (see this module's own docstring,
    disclosed judgment call 4). Never raises: any adapter defect here is itself reported as a
    failed rollback, never escalated into an exception this route's own caller has to handle on
    top of the primary outcome it already has."""

    if not files_written:
        return "NOT_ATTEMPTED"
    rollback_operation = {
        "operation_kind": "DELETE_ISOLATED_SOURCE_FILE",
        "file_writes": [],
        "file_deletes": [{"path": path} for path in files_written],
    }
    try:
        raw = adapter.execute(rollback_operation, worktree_root=worktree_root)
        if not isinstance(raw, Mapping):
            return "ROLLBACK_FAILED"
        deleted = raw.get("files_deleted")
        if not isinstance(deleted, list) or set(deleted) != set(files_written) or raw.get("error"):
            return "ROLLBACK_FAILED"
    except Exception:  # a rollback failure is itself a reported outcome, never raised
        return "ROLLBACK_FAILED"
    return "ROLLBACK_SUCCEEDED"


def compose_change_executor(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    execution_boundary: Any,
    adapter_identity: Any,
    adapter: Any,
    kill_switch_trust_anchor_public_key_hex: str,
) -> Callable[..., dict[str, Any]]:
    """The one public, trusted composition step for Controlled Autonomous Change execution.

    Binds *store*, *project_id*, *project_binding_id*, a canonicalized-and-frozen Execution
    Boundary, a canonicalized-and-frozen adapter identity, the replaceable *adapter* itself, and
    the kill-switch trust anchor -- once, before any request exists -- and returns the request-
    facing operation itself, already closed over every one of them. The returned closure's own
    call signature carries only request-facing data: ``execute(change_id, *, claim_token,
    execution_instant, worktree_root, permit_semantic_reuse=False)``. There is no keyword,
    positional slot, or attribute on the returned callable through which a caller could
    substitute a different Store, Boundary, adapter identity, adapter, or trust anchor after the
    fact.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    _require_non_empty_string(
        "kill_switch_trust_anchor_public_key_hex", kill_switch_trust_anchor_public_key_hex
    )
    if not callable(getattr(adapter, "execute", None)):
        raise ChangeExecutorError("adapter must declare a callable execute(...) method")

    canonical_boundary = validate_execution_boundary(execution_boundary)
    frozen_boundary = deep_freeze(canonical_boundary)
    boundary_fp = execution_boundary_fingerprint(canonical_boundary)

    # adapter_identity is canonicalized once, here, and reduced immediately to its own content
    # fingerprint -- the one value this closure actually needs to retain across every future
    # request (embedded in every execution_intent/execution_attempt this closure ever builds).
    # The canonicalized structure itself is not retained beyond this line, so no separate
    # deep_freeze step is needed for it the way frozen_boundary needs one.
    canonical_adapter_identity = canonicalize_inert_data(adapter_identity)
    adapter_fp = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(canonical_adapter_identity)).hexdigest()
    )

    def execute(
        change_id: str,
        *,
        claim_token: str,
        execution_instant: str,
        worktree_root: str,
        permit_semantic_reuse: bool = False,
    ) -> dict[str, Any]:
        _require_canonical_identity("change_id", change_id)
        _require_non_empty_string("claim_token", claim_token)
        _require_non_empty_string("worktree_root", worktree_root)

        # (2) time-window check -- zero-call, before Boot or any adapter.
        require_within_time_window(frozen_boundary, execution_instant)

        # (3) kill switch check #1.
        _require_active_kill_switch_verified(
            store, project_id, kill_switch_trust_anchor_public_key_hex, stage="before Boot"
        )

        # (4) idempotency-slot resolution -- deliberately *before* Boot/Change/Authority/
        # staleness (moved here after this package's own test suite demonstrated a genuine
        # ordering defect: every commit this route performs unconditionally advances
        # state_revision by one, so a staleness check performed *before* replay detection would
        # make the very first successful execute() call for a Change make every subsequent call
        # for it -- including an ordinary same-claim_token replay -- spuriously refuse as stale,
        # never reaching replay/reuse resolution at all). The mapping-slot key is a pure function
        # of *change_id* (a caller-supplied parameter) and the two fingerprints already bound at
        # composition time, so resolving it needs neither Boot nor the resolved Change record --
        # a terminal outcome already reflects a fully-vetted prior execution and is returned
        # unchanged without re-Booting or re-checking staleness against it.
        slot_key = execution_mapping_slot_key(change_id, boundary_fp, adapter_fp)
        change_ref = {"kind": "change", "id": change_id}

        resolved_receipt_raw = _resolve_slot_record(
            store, project_id, _RECEIPT_RECORD_KIND, slot_key
        )
        if resolved_receipt_raw is not None:
            receipt = _verify_slot_record(
                resolved_receipt_raw,
                kind=_RECEIPT_RECORD_KIND,
                declared_id_field="change_execution_receipt_id",
                recompute_id=_change_execution_receipt_id_of,
                recompute_fingerprint=change_execution_receipt_semantic_fingerprint,
                fingerprint_field="change_execution_receipt_semantic_fingerprint",
                slot_key=slot_key,
            )
            if receipt["claim_token"] == claim_token:
                return {"receipt": receipt, "replay": True, "semantic_reuse": False}
            if permit_semantic_reuse:
                return {"receipt": receipt, "replay": False, "semantic_reuse": True}
            raise ExecutionTerminalClaimMismatchError(
                f"a terminal change_execution_receipt already exists for this mapping slot "
                f"({slot_key!r}) under a different claim_token -- pass permit_semantic_reuse=True "
                "to explicitly reuse it"
            )

        resolved_attempt_raw = _resolve_slot_record(
            store, project_id, _ATTEMPT_RECORD_KIND, slot_key
        )
        if resolved_attempt_raw is not None:
            _verify_slot_record(
                resolved_attempt_raw,
                kind=_ATTEMPT_RECORD_KIND,
                declared_id_field="execution_attempt_id",
                recompute_id=_execution_attempt_id_of,
                recompute_fingerprint=execution_attempt_semantic_fingerprint,
                fingerprint_field="execution_attempt_semantic_fingerprint",
                slot_key=slot_key,
            )
            raise ExecutionReconciliationRequiredError(
                f"an execution_attempt already exists for mapping slot {slot_key!r} with no "
                "terminal change_execution_receipt yet -- the true outcome of a prior attempt "
                "(which may already have called the adapter) is genuinely unknown; refusing "
                "rather than risk a duplicate real mutation"
            )

        # (5) fresh Boot. Only reached for a genuinely new mapping slot -- no receipt, no
        # attempt -- so the live current State is the correct one to Boot and stale-check
        # against below.
        boot_context = boot_project(
            store, project_id=project_id, project_binding_id=project_binding_id
        )

        # (6) resolve the Change.
        change = _resolve_change(store, project_id, change_id)

        # (7) resolve the Authority Decision the Change names, require AUTONOMOUS.
        decision = _resolve_authority_decision(store, project_id, change["authority_ref"]["id"])
        if decision["decision"] != AUTONOMOUS:
            raise ExecutionAuthorityProvenanceError(
                f"the Authority Decision behind change {change_id!r} is not AUTONOMOUS: "
                f"{decision['decision']!r}"
            )

        # (8) action_kind in the bound Boundary's own permitted set, and not Human-only.
        action_kind = change["action"]["action_kind"]
        if action_kind not in frozen_boundary["permitted_action_kinds"]:
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own action_kind is not permitted by the bound Execution "
                f"Boundary: {action_kind!r}"
            )
        if action_kind in HUMAN_ONLY_ACTION_KINDS:
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own action_kind is a Human-only action kind: {action_kind!r}"
            )

        # (9) scope entirely admitted by the bound Boundary.
        scope = change["scope"]
        if (
            scope["repository"] != frozen_boundary["repository"]
            or scope["branch"] != frozen_boundary["branch"]
        ):
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own scope names a different repository/branch than the "
                "bound Execution Boundary"
            )
        for path in scope["paths"]:
            if not path_is_admitted(path, frozen_boundary["admitted_paths"]):
                raise ExecutionAuthorityProvenanceError(
                    f"change {change_id!r} own scope names a path the bound Execution Boundary "
                    f"does not admit: {path!r}"
                )

        # (10) staleness.
        current_fingerprint = dict(boot_context.current_state["semantic_fingerprint"])
        if (
            dict(change["before_state_fingerprint"]) != current_fingerprint
            or change["expected_state_revision"] != boot_context.current_state["state_revision"]
        ):
            raise StaleExecutionInputError(
                f"change {change_id!r} own before_state_fingerprint/expected_state_revision no "
                "longer matches the freshly Booted current State -- blocked as stale, never "
                "executed against a State it did not observe"
            )

        # (11) commit execution_intent.
        intent = build_execution_intent(
            project_id=project_id,
            change_ref=change_ref,
            execution_boundary_fingerprint=boundary_fp,
            adapter_identity_fingerprint=adapter_fp,
            claim_token=claim_token,
            requested_at=execution_instant,
        )
        try:
            _commit_records(
                store,
                project_id,
                [(_INTENT_RECORD_KIND, slot_key, intent)],
                execution_instant,
                transaction_prefix=f"TX-EXEC-INTENT-{slot_key}",
            )
        except RecordConflictError as error:
            raise ExecutionConcurrentClaimError(
                f"a different execution_intent already occupies mapping slot {slot_key!r} -- a "
                "genuinely concurrent claim under a different claim_token, refused rather than "
                "silently retried into an attempt"
            ) from error

        # (12) commit execution_attempt.
        attempt = build_execution_attempt(
            project_id=project_id,
            change_ref=change_ref,
            execution_boundary_fingerprint=boundary_fp,
            adapter_identity_fingerprint=adapter_fp,
            claim_token=claim_token,
            requested_at=execution_instant,
            execution_intent_ref={"kind": _INTENT_RECORD_KIND, "id": slot_key},
        )
        try:
            _commit_records(
                store,
                project_id,
                [(_ATTEMPT_RECORD_KIND, slot_key, attempt)],
                execution_instant,
                transaction_prefix=f"TX-EXEC-ATTEMPT-{slot_key}",
            )
        except RecordConflictError as error:
            raise ExecutionConcurrentClaimError(
                f"a different execution_attempt already occupies mapping slot {slot_key!r} -- a "
                "genuinely concurrent claim, refused rather than silently retried into an "
                "adapter call"
            ) from error

        authority_ref = {"kind": "authority_decision", "id": decision["authority_decision_id"]}
        project_binding_ref = {"kind": "project_binding", "id": project_binding_id}
        target = {
            "repository": frozen_boundary["repository"],
            "branch": frozen_boundary["branch"],
            "worktree_root": worktree_root,
        }
        # The one canonical scope-normalization owner (`authority.scope.canonical_scope`) is
        # used here rather than a local sort -- re-sorting `scope["paths"]` in this module
        # would be a second, competing answer to what the canonical member order is
        # (`tests/contract/authority/test_scope_normalization_owner.py`'s own static sweep).
        canonical_change_scope = canonical_scope(scope)
        reobservation_request = {
            "kind": "change_execution_reobservation_request",
            "target": {
                "repository": frozen_boundary["repository"],
                "branch": frozen_boundary["branch"],
                "paths": canonical_change_scope["paths"],
            },
            "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
            "requested_at": execution_instant,
        }

        def _commit_terminal_receipt(
            *,
            outcome: str,
            performed_result_summary: dict[str, Any],
            performed_result_fingerprint: str,
            rollback_outcome: str | None,
            operation_echo: dict[str, Any],
        ) -> dict[str, Any]:
            receipt = build_change_execution_receipt(
                execution_request_id=slot_key,
                change_ref=change_ref,
                idempotency_key=change["idempotency_key"],
                authority_ref=authority_ref,
                project_id=project_id,
                project_binding_ref=project_binding_ref,
                boot_state_fingerprint=current_fingerprint,
                execution_boundary_fingerprint=boundary_fp,
                executor_identity=frozen_boundary["executor_identity"],
                executor_version=frozen_boundary["executor_version"],
                target=target,
                operation=operation_echo,
                execution_started_at=execution_instant,
                execution_ended_at=execution_instant,
                outcome=outcome,
                performed_result_fingerprint=performed_result_fingerprint,
                performed_result_summary=performed_result_summary,
                rollback_outcome=rollback_outcome,
                claim_token=claim_token,
                reobservation_request=reobservation_request,
            )
            try:
                _commit_records(
                    store,
                    project_id,
                    [(_RECEIPT_RECORD_KIND, slot_key, receipt)],
                    execution_instant,
                    transaction_prefix=f"TX-EXEC-RECEIPT-{slot_key}",
                )
            except RecordConflictError as error:
                raise ExecutionReceiptIntegrityError(
                    f"a different change_execution_receipt already occupies mapping slot "
                    f"{slot_key!r} -- refusing rather than trust either"
                ) from error
            return receipt

        _empty_operation_echo = {
            "operation_kind": action_kind,
            "file_writes": [],
            "file_deletes": [],
        }
        _empty_summary = {"files_written": [], "bytes_written": 0, "files_deleted": []}
        _empty_result_fingerprint = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(_empty_summary)).hexdigest()
        )

        # (13) kill switch check #2 -- immediately before the one adapter call. A refusal here
        # still produces a terminal receipt (see this module's own disclosed judgment call 3).
        try:
            _require_active_kill_switch_verified(
                store,
                project_id,
                kill_switch_trust_anchor_public_key_hex,
                stage="immediately before the adapter call",
            )
        except ExecutionKillSwitchError:
            receipt = _commit_terminal_receipt(
                outcome="KILL_SWITCH_STOPPED",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=_empty_operation_echo,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (14) build + validate the closed operation against the bound Boundary's own limits.
        # The violation reason itself is deliberately not persisted on the receipt --
        # performed_result_summary is schema-closed to files_written/bytes_written/files_deleted
        # (the identical bounded discipline the Boundary itself enforces), so a free-text reason
        # has no admissible field to live in; only the closed BOUNDARY_VIOLATION outcome is.
        checked_operation, _violation_reason = _operation_violation_reason(
            action_kind, change["action"]["operation"], frozen_boundary
        )
        if checked_operation is None:
            receipt = _commit_terminal_receipt(
                outcome="BOUNDARY_VIOLATION",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=_empty_operation_echo,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (15) call adapter.execute(...) exactly once for the primary requested operation. A
        # raised exception here (rather than a returned error fact) is itself converted into a
        # typed error -- but an execution_attempt is already durably committed at this point, so
        # the *next* call for this same slot correctly reconciliation-requires (this package's
        # own idempotency contract), never a bare exception type leaking a trust distinction.
        try:
            raw_report = adapter.execute(checked_operation, worktree_root=worktree_root)
        except Exception as error:
            raise ExecutionAdapterError(
                f"adapter.execute raised {type(error).__name__}: {error} -- an "
                "execution_attempt is already committed for this mapping slot, so the next call "
                "for it will correctly refuse as reconciliation-required rather than retry blindly"
            ) from error
        checked_report = _validate_adapter_report(raw_report, checked_operation)

        # (16) classify the adapter's raw reported facts.
        outcome = _classify_outcome(checked_report, checked_operation)

        rollback_outcome: str | None = None
        if outcome in ("PARTIAL_MUTATION", "ADAPTER_FAILURE") and checked_report["files_written"]:
            if frozen_boundary["rollback_policy"] == "BEST_EFFORT_DELETE_WRITTEN_FILES":
                rollback_outcome = _attempt_rollback(
                    adapter, worktree_root, checked_report["files_written"]
                )
                if rollback_outcome == "ROLLBACK_SUCCEEDED":
                    outcome = "ROLLBACK_SUCCEEDED"
                elif rollback_outcome == "ROLLBACK_FAILED":
                    outcome = "ROLLBACK_FAILED"
            else:
                rollback_outcome = "NOT_ATTEMPTED"

        performed_result_summary = {
            "files_written": checked_report["files_written"],
            "bytes_written": checked_report["bytes_written"],
            "files_deleted": checked_report["files_deleted"],
        }
        performed_result_fingerprint = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(checked_report)).hexdigest()
        )

        # (17) build + commit the terminal receipt.
        receipt = _commit_terminal_receipt(
            outcome=outcome,
            performed_result_summary=performed_result_summary,
            performed_result_fingerprint=performed_result_fingerprint,
            rollback_outcome=rollback_outcome,
            operation_echo=checked_operation,
        )

        # (18) return.
        return {"receipt": receipt, "replay": False, "semantic_reuse": False}

    return execute


__all__ = ["compose_change_executor"]
