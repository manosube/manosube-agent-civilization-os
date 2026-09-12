"""The human kill switch for autonomous Change execution: a monotonic ACTIVE/REVOKED rotation
(Phase 18, Issue #73).

Mirrors -- deliberately without importing -- :mod:`manosube_agent_civilization.runtime.
admission_registry`'s own shape: signed, content-addressed, monotonically chained records, and
one sanctioned committer that verifies a genuine Ed25519 signature against a caller-supplied
*trust_anchor_public_key_hex* (never read from the Store, never baked into shipped source)
before it will move anything. This module holds no private key and mints no signature; it only
ever verifies (see :func:`~manosube_agent_civilization.binding.signature.
verify_ed25519_signature`), the identical separation ``runtime/admission_registry.py`` and
``runtime/root_admission.py`` already keep between minting and verifying.

**Disclosed judgment call: where the current-kill-switch pointer lives.** The task description
that seeded this package suggested ``semantic_state.change_executor.kill_switch_current_id`` --
a new top-level ``change_executor`` domain under ``semantic_state``. That is not available:
``01_SCHEMA/state/semantic_state.schema.json`` is an existing-owner schema this package may not
touch, it declares ``additionalProperties: false``, and its top-level ``required``/``properties``
set is fixed to exactly nine domains (``project``, ``objective``, ``repository``,
``requirements``, ``code``, ``tests``, ``runtime``, ``infrastructure``, ``deployment``) plus a
handful of non-domain fields -- there is no ``change_executor`` domain to write into without
editing that schema file, which this delivery is not permitted to do. Every one of those nine
domains already carries an open ``claims: {string: scalar}`` map for exactly this kind of
package-owned pointer (the identical extension point :mod:`~manosube_agent_civilization.runtime.
transition_chain` already uses for its own two chains, both inside the ``"runtime"`` domain).
This module therefore stores its own pointer inside the existing **``"deployment"``** domain's
``claims`` map instead -- a domain no other shipped package currently writes to (confirmed by
repository-wide search at the time this module was written), and deliberately *not*
``"runtime"``, which is Runtime's own domain and which the task description explicitly said not
to reuse. The claim key itself (:data:`_POINTER_CLAIM_KEY`) is a single, fixed, distinctively
named string -- there is exactly one kill switch per project, never one per target, so no
per-binding key map is needed the way the two Runtime chains need one.

**Disclosed judgment call: which Store read surface backs which call site.** Reading the
*current* record (:func:`resolve_current_kill_switch`) uses
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.read_current_consistent` --
the one read-only, quiescence-checked surface that never risks materializing ``current.json``
via a write, appropriate for a check this package's own route performs *twice* per execution
attempt, including once before any Store commit has happened at all. *Committing* a new kill
switch record (:func:`commit_change_executor_kill_switch`) instead calls
:meth:`~manosube_agent_civilization.store.file_store.FileStateStore.load_current` inside its own
Compare-And-Swap retry loop -- the identical convention every other committer in this repository
(``url_boot/route.py``'s own ``_commit_envelope``, ``runtime/transition_chain.py``'s own
``commit_chain_transition``) already uses, since that call site is already about to commit a real
State transition regardless.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from typing import Any

from manosube_agent_civilization.binding.signature import (
    SUPPORTED_SIGNATURE_ALGORITHM,
    verify_ed25519_signature,
)
from manosube_agent_civilization.difference.errors import DifferenceValidationError
from manosube_agent_civilization.difference.validation import validate_record as _validate_record
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .boundary import CHANGE_EXECUTOR_SCHEMA_BASE
from .errors import ChangeExecutorError, ExecutionKillSwitchError, ExecutionReceiptIntegrityError

#: The canonical Store record kind this module commits and resolves.
KILL_SWITCH_RECORD_KIND = "change_executor_kill_switch"

#: What a kill switch record *is*: which project, its own current status, its own position in
#: its own chain, and which record it supersedes. Deliberately excludes its own declared id, its
#: own declared semantic fingerprint (an identity cannot be computed over itself), and its own
#: ``signature`` (a signature cannot cover its own value) -- the identical exclusion
#: :data:`~manosube_agent_civilization.runtime.identity.ROOT_ADMISSION_SEMANTIC_FIELDS` states
#: for its own sibling record kind.
KILL_SWITCH_SEMANTIC_FIELDS: tuple[str, ...] = (
    "project_id",
    "status",
    "generation",
    "predecessor_ref",
)

KILL_SWITCH_ACTIVE = "ACTIVE"
KILL_SWITCH_REVOKED = "REVOKED"
KILL_SWITCH_STATUSES: frozenset[str] = frozenset({KILL_SWITCH_ACTIVE, KILL_SWITCH_REVOKED})

#: Where this module's own current-kill-switch pointer lives inside Project State -- see this
#: module's own docstring, "Disclosed judgment call: where the current-kill-switch pointer
#: lives", for why this is the ``"deployment"`` domain rather than a new top-level one.
_POINTER_DOMAIN = "deployment"
_POINTER_CLAIM_KEY = "CHANGE_EXECUTOR_KILL_SWITCH_CURRENT_ID"

_MAX_COMMIT_RETRIES = 8


def _semantic_projection(record: Mapping[str, Any]) -> dict[str, Any]:
    missing = [field for field in KILL_SWITCH_SEMANTIC_FIELDS if field not in record]
    if missing:
        raise ChangeExecutorError(
            f"change_executor_kill_switch carries no readable {', '.join(missing)} -- its own "
            "identity cannot be recomputed"
        )
    return {field: record[field] for field in KILL_SWITCH_SEMANTIC_FIELDS}


def kill_switch_signing_payload(record: Mapping[str, Any]) -> bytes:
    """The exact canonical bytes a genuine trust-anchor signature over *record* must cover --
    the identical payload :func:`kill_switch_id` and :func:`kill_switch_semantic_fingerprint`
    themselves hash, over :data:`KILL_SWITCH_SEMANTIC_FIELDS`."""

    return canonical_json_bytes(_semantic_projection(record))


def kill_switch_id(record: Mapping[str, Any]) -> str:
    """The content address of a kill switch record, over
    :func:`kill_switch_signing_payload`'s own bytes."""

    return (
        "EXEC-KILLSWITCH-" + hashlib.sha256(kill_switch_signing_payload(record)).hexdigest().upper()
    )


def kill_switch_semantic_fingerprint(record: Mapping[str, Any]) -> str:
    """The digest of a kill switch record's own meaning, under the ``sha256:`` encoding every
    other record kind in this repository uses for its own semantic fingerprint."""

    return "sha256:" + hashlib.sha256(kill_switch_signing_payload(record)).hexdigest()


def _current_kill_switch_id(current_state: Mapping[str, Any]) -> str | None:
    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        return None
    domain = semantic_state.get(_POINTER_DOMAIN)
    if not isinstance(domain, Mapping):
        return None
    claims = domain.get("claims")
    if not isinstance(claims, Mapping):
        return None
    value = claims.get(_POINTER_CLAIM_KEY)
    return value if isinstance(value, str) else None


def _next_semantic_state(current_state: Mapping[str, Any], record_id: str) -> dict[str, Any]:
    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        raise ChangeExecutorError(
            "the current Project State carries no readable semantic_state -- refusing to move "
            "the kill switch pointer inside a State this module cannot read"
        )
    next_semantic_state: dict[str, Any] = dict(semantic_state)
    domain = next_semantic_state.get(_POINTER_DOMAIN)
    if not isinstance(domain, Mapping):
        raise ChangeExecutorError(
            f"the current Project State carries no readable semantic_state.{_POINTER_DOMAIN} domain"
        )
    next_domain: dict[str, Any] = dict(domain)
    claims = next_domain.get("claims")
    if not isinstance(claims, Mapping):
        raise ChangeExecutorError(
            "the current Project State carries no readable "
            f"semantic_state.{_POINTER_DOMAIN}.claims map"
        )
    next_claims = dict(claims)
    next_claims[_POINTER_CLAIM_KEY] = record_id
    next_domain["claims"] = next_claims
    next_semantic_state[_POINTER_DOMAIN] = next_domain
    return next_semantic_state


def _require_self_consistent(record: Mapping[str, Any]) -> dict[str, Any]:
    """Schema-validate *record*, then require its own declared identity and semantic
    fingerprint to equal what this module independently recomputes from its own body."""

    checked = dict(record)
    try:
        _validate_record(
            checked, "change_executor_kill_switch.schema.json", base=CHANGE_EXECUTOR_SCHEMA_BASE
        )
    except DifferenceValidationError as error:
        raise ExecutionReceiptIntegrityError(
            f"change_executor_kill_switch is schema-invalid: {error}"
        ) from error
    if kill_switch_id(checked) != checked.get("change_executor_kill_switch_id"):
        raise ExecutionReceiptIntegrityError(
            "change_executor_kill_switch own recomputed identity does not equal its own "
            "declared value -- refusing to trust it"
        )
    if kill_switch_semantic_fingerprint(checked) != checked.get(
        "change_executor_kill_switch_semantic_fingerprint"
    ):
        raise ExecutionReceiptIntegrityError(
            "change_executor_kill_switch own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to trust it"
        )
    return checked


def resolve_current_kill_switch(store: Any, project_id: str) -> dict[str, Any] | None:
    """Return the current, resolved, integrity-checked kill switch record for *project_id*, or
    ``None`` when no kill switch has ever been made current for this project (this module never
    Store-initializes one implicitly). Raises
    :class:`~manosube_agent_civilization.change_executor.errors.ExecutionReceiptIntegrityError`
    if the resolved record's own recomputed identity or semantic fingerprint disagrees with its
    own declared value."""

    current_state = store.read_current_consistent(project_id)
    current_id = _current_kill_switch_id(current_state)
    if current_id is None:
        return None
    resolved = store.resolve_record(project_id, KILL_SWITCH_RECORD_KIND, current_id)
    if resolved is None:
        raise ExecutionReceiptIntegrityError(
            f"the current kill switch pointer names {current_id!r}, which does not resolve in "
            "the bound Store -- refusing to trust a pointer whose own current value cannot be read"
        )
    return _require_self_consistent(resolved)


def require_active_kill_switch(store: Any, project_id: str, *, stage: str) -> dict[str, Any]:
    """Resolve the current kill switch and require it to exist and be ``ACTIVE`` -- refusing
    closed, with zero adapter calls, otherwise."""

    current = resolve_current_kill_switch(store, project_id)
    if current is None:
        raise ExecutionKillSwitchError(
            f"no change_executor_kill_switch is currently admitted for project {project_id!r} "
            f"-- refusing to execute ({stage}): a project with no kill switch ever committed "
            "for it may never autonomously execute a Change"
        )
    if current.get("status") != KILL_SWITCH_ACTIVE:
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for project {project_id!r} is not ACTIVE "
            f"({current.get('status')!r}) -- refusing to execute ({stage})"
        )
    return current


def commit_change_executor_kill_switch(
    store: Any,
    project_id: str,
    kill_switch: Mapping[str, Any],
    *,
    trust_anchor_public_key_hex: str,
    committed_at: str,
) -> dict[str, Any]:
    """Commit *kill_switch* **and** make it this project's own current kill switch, in one
    atomic :func:`~manosube_agent_civilization.store.commit.commit_state_transition` call -- if,
    and only if, it is a legal monotonic transition from whatever is current right now, and
    genuinely signed by the holder of *trust_anchor_public_key_hex*.

    Holds no private key and mints no signature of its own -- it only ever verifies. Nothing in
    ``route.py``, ``engine.py``, or any adapter may construct a valid signed kill switch record
    or flip its own status; only this function, called with an externally supplied private key's
    matching public counterpart, can ever make a proposed record current.

    *committed_at* is required and caller-supplied: this module reads no clock.
    """

    if not isinstance(trust_anchor_public_key_hex, str) or not trust_anchor_public_key_hex:
        raise ExecutionKillSwitchError(
            "trust_anchor_public_key_hex must be a non-empty hex-encoded Ed25519 public key, "
            "supplied by the deployment/composition boundary itself -- never read from the "
            "Store being admitted, and never derived from anything on the request path"
        )
    if not isinstance(committed_at, str) or not committed_at:
        raise ChangeExecutorError("committed_at must be a non-empty caller-supplied instant")

    checked = _require_self_consistent(dict(kill_switch))
    if checked.get("project_id") != project_id:
        raise ChangeExecutorError(
            "change_executor_kill_switch names a different project than the one being "
            f"committed into: {checked.get('project_id')!r} != {project_id!r}"
        )
    record_id = checked["change_executor_kill_switch_id"]

    signature = checked.get("signature")
    if (
        not isinstance(signature, dict)
        or signature.get("algorithm") != SUPPORTED_SIGNATURE_ALGORITHM
    ):
        raise ExecutionKillSwitchError(
            "change_executor_kill_switch carries no genuine ed25519 signature block"
        )
    signature_hex = signature.get("value")
    if not isinstance(signature_hex, str) or not verify_ed25519_signature(
        public_key_hex=trust_anchor_public_key_hex,
        message=kill_switch_signing_payload(checked),
        signature_hex=signature_hex,
    ):
        raise ExecutionKillSwitchError(
            "change_executor_kill_switch carries no genuine signature over its own adopted "
            "semantic fields by the externally supplied trust anchor -- an unsigned, "
            "self-authored, or foreign-world-signed kill switch may never open, rotate, or "
            "revoke this project's own kill switch chain"
        )

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        current_id = _current_kill_switch_id(current_state)
        if current_id == record_id:
            return {
                "change_executor_kill_switch_ref": {
                    "kind": KILL_SWITCH_RECORD_KIND,
                    "id": record_id,
                },
                "generation": int(checked["generation"]),
                "committed_state": None,
            }
        current_record = (
            store.resolve_record(project_id, KILL_SWITCH_RECORD_KIND, current_id)
            if current_id is not None
            else None
        )
        if current_id is not None and current_record is None:
            raise ExecutionReceiptIntegrityError(
                f"the kill switch pointer names {current_id!r}, which does not resolve in the "
                "bound Store -- refusing to move a pointer whose own current value cannot be read"
            )
        _require_legal_transition(checked, current_record, current_id)

        transaction_id = f"TX-{record_id}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["semantic_state"] = _next_semantic_state(current_state, record_id)
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
            commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=[(KILL_SWITCH_RECORD_KIND, record_id, checked)],
            )
        except RecordConflictError as error:
            raise ExecutionReceiptIntegrityError(
                f"a different record already occupies {KILL_SWITCH_RECORD_KIND}/{record_id} "
                "with different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            continue
        return {
            "change_executor_kill_switch_ref": {"kind": KILL_SWITCH_RECORD_KIND, "id": record_id},
            "generation": int(checked["generation"]),
            "committed_state": next_state,
        }
    raise ChangeExecutorError(
        f"could not durably commit {KILL_SWITCH_RECORD_KIND}/{record_id} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


def _require_legal_transition(
    proposed: Mapping[str, Any], current_record: Mapping[str, Any] | None, current_id: str | None
) -> None:
    """The identical genesis/successor/terminality rules
    :mod:`~manosube_agent_civilization.runtime.transition_chain` establishes for its own two
    chains, restated here self-contained and simplified for a single, project-scoped pointer
    (no per-target chain-key map is needed: there is exactly one kill switch per project)."""

    generation = proposed["generation"]
    predecessor = proposed.get("predecessor_ref")
    predecessor_id = (
        predecessor["id"]
        if isinstance(predecessor, Mapping) and isinstance(predecessor.get("id"), str)
        else None
    )

    if current_record is not None and current_record.get("status") == KILL_SWITCH_REVOKED:
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for this project ({current_id!r}) is "
            "REVOKED, which is terminal -- refusing: after a revocation no successor and no "
            "ancestor replay is ever admitted again for this project's own kill switch chain"
        )

    if current_record is None:
        if generation != 0 or predecessor_id is not None:
            raise ExecutionKillSwitchError(
                "no change_executor_kill_switch is current for this project, so only a genesis "
                "record (generation=0, predecessor_ref=null) may be committed"
            )
        if proposed.get("status") != KILL_SWITCH_ACTIVE:
            raise ExecutionKillSwitchError(
                "a genesis change_executor_kill_switch must be ACTIVE -- a chain cannot open "
                "with a revocation of something that was never admitted"
            )
        return

    if predecessor_id is None:
        raise ExecutionKillSwitchError(
            f"a change_executor_kill_switch is already current for this project ({current_id!r}), "
            "so a genesis record is refused"
        )
    if predecessor_id != current_id:
        raise ExecutionKillSwitchError(
            f"the proposed record declares predecessor_ref={predecessor_id!r}, which is not the "
            f"change_executor_kill_switch this project's own pointer currently names "
            f"({current_id!r})"
        )
    current_generation = current_record.get("generation")
    if not isinstance(current_generation, int) or isinstance(current_generation, bool):
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch ({current_id!r}) carries no readable "
            "generation -- refusing to compute a successor generation from it"
        )
    if generation != current_generation + 1:
        raise ExecutionKillSwitchError(
            f"the proposed record declares generation={generation}, which is not exactly one "
            f"past the current record's own ({current_generation})"
        )


__all__ = [
    "KILL_SWITCH_ACTIVE",
    "KILL_SWITCH_RECORD_KIND",
    "KILL_SWITCH_REVOKED",
    "KILL_SWITCH_SEMANTIC_FIELDS",
    "KILL_SWITCH_STATUSES",
    "commit_change_executor_kill_switch",
    "kill_switch_id",
    "kill_switch_semantic_fingerprint",
    "kill_switch_signing_payload",
    "require_active_kill_switch",
    "resolve_current_kill_switch",
]
