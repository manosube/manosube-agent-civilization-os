"""The one shared monotonic, signed transition-chain mechanism this package owns (Phase 15
Structural Review Round 4, Issue #64, P15-R4-F1 and P15-R4-F2).

**Why this module exists at all.** Round 4 required the identical lifecycle correction in two
places at once: a ``runtime_deployment_declaration``'s own chain (P15-R4-F2) and a
``runtime_root_admission``'s own chain (P15-R4-F1, item 5 -- "an old content-addressed ACTIVE
admission must not remain usable after composition-level rotation or revocation", which is
literally the same defect, one level up). Writing the genesis/successor/rotation/revocation/
terminality/Compare-And-Swap logic twice, independently, would give this delivery two chances to
drift apart -- and the review's own framing is that the *same semantic class* has recurred across
four rounds, so a second independent copy of the rule is exactly the wrong shape. Both chains
therefore parameterize **this** mechanism through :class:`MonotonicChainSpec`; neither restates a
rule of its own.

```text
GENESIS      generation == 0, predecessor_ref is null, and the chain has no current record.
SUCCESSOR    generation == current.generation + 1, and predecessor_ref names the EXACT id the
             chain pointer currently holds.
ROTATION     an ACTIVE successor replacing an ACTIVE current -- the successor rule, nothing more.
REVOCATION   a REVOKED successor naming the exact current record. TERMINAL for that chain.
TERMINAL     after a REVOKED record is current, NO successor and NO ancestor replay is ever
             admitted again for that chain key. Reactivation would require a separately adopted
             new target epoch, which this round deliberately does not build (§13.5, item 8).
REPLAY       proposing the record the pointer already names is an idempotent no-op success: it
             moves nothing, commits nothing, and is not a transition.
```

**What "monotonic" is anchored to, and why that matters.** ``generation`` and
``predecessor_ref`` are not committer bookkeeping: both participate in each record kind's own
adopted semantic-field tuple, so both are covered by the record's own content address, its own
semantic fingerprint, **and** the signature over it (a Human Authority's, for a declaration; the
deployment trust anchor's, for a root admission). A proposed successor is therefore a *signed
statement about which record it replaces*. That single fact is what makes the concurrency rule
below honest rather than convenient.

**The concurrency rule, stated exactly.** Round 3's committer retried the identical write on any
:class:`~manosube_agent_civilization.store.errors.StaleStateError`, tolerating whatever caused
the bump. That tolerance is still correct for genuinely unrelated contention -- another project's
commit, another target's declaration, any State mutation that leaves *this* chain's own pointer
where it was -- and is deliberately preserved (the P15-R1-F5 precedent's own required control
still passes unchanged). What Round 4 adds is the distinction Round 3 could not draw:

```text
UNRELATED CONTENTION      this chain's own pointer still names exactly the record the proposed
                          record's own predecessor_ref names   ->  reload and retry
THIS CHAIN'S OWN POINTER  the pointer already names something else                ->  FAIL CLOSED
MOVED                     (no retry -- retrying could never help)
```

The second case is not pessimism about retries; it is the only sound answer. The losing
proposal's own ``predecessor_ref`` and ``generation`` were signed against a *specific* prior
head. Re-aiming it at the new head would mean committing a body whose own signed content no
longer describes its true predecessor -- and producing an honestly re-aimed one requires a **new
signature over a new payload**, which only the Human Authority (or the deployment trust anchor)
can create, never this committer. So "the loser re-evaluates against the new head and fails
closed" is literally what happens, and the entire transition -- genesis rule, successor rule,
terminality, status legality -- is re-evaluated from freshly loaded State on **every** iteration,
never assumed to still hold from the previous one.

**This module is not a second State owner.** It builds one transition plan and hands it to the
Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition` -- the identical
primitive Reflow, Binding, Projection, and this package's own ``route.py`` already share). It
evaluates no Closure, mints no Authority, derives no Difference/Change/Evidence content, and
holds no key: it persists one already-issued, already-signed statement and the pointer that says
which one is current. It is also the *only* ``commit_state_transition`` call site either chain
has, which is why adding a second chain in this round added no second commit site to this package
(``tests/contract/runtime/test_runtime_static_conformance.py`` still admits exactly two, by
name).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .errors import RuntimeEnvelopeIntegrityError, RuntimeRequirementError

#: The field names a chained record carries. Both shipped chains use the identical names and the
#: identical closed status vocabulary -- stated once, here, and reachable through
#: :class:`MonotonicChainSpec` so a future third chain kind that genuinely names them differently
#: can say so at its own spec rather than by editing this mechanism.
GENERATION_FIELD = "generation"
PREDECESSOR_FIELD = "predecessor_ref"
STATUS_FIELD = "status"
ACTIVE_STATUS = "ACTIVE"
REVOKED_STATUS = "REVOKED"

#: Where every chain pointer lives inside Project State. ``semantic_state`` -> this domain ->
#: ``claims`` -> ``{chain_key: record_id}``. Established by Round 3 (P15-R3-F2) for declarations
#: and reused unchanged by Round 4 for root admissions -- still **no State schema change of any
#: kind**, because ``01_SCHEMA/state/semantic_state.schema.json``'s own ``$defs/domain.claims`` is
#: already an open ``{string: scalar}`` map. The two chains' key spaces are provably disjoint;
#: see :data:`~manosube_agent_civilization.runtime.identity.ROOT_ADMISSION_TARGET_KEY_PREFIX`.
CHAIN_POINTER_SEMANTIC_DOMAIN = "runtime"
CHAIN_POINTER_CLAIMS_FIELD = "claims"

#: The identical bounded Compare-And-Swap retry ``route.py``'s own ``_commit_envelope`` uses --
#: not a timeout, not a backoff, bounded protection against genuine, ordinary contention from an
#: unrelated commit landing on this project between an attempt's own ``load_current`` and its own
#: commit. A retry never re-submits a stale judgment: every iteration re-derives the whole
#: transition from freshly loaded State.
MAX_COMMIT_RETRIES = 8

#: The three outcomes :func:`commit_chain_transition` can return. ``IDEMPOTENT_REPLAY`` is
#: deliberately not called a transition: nothing moved.
TRANSITION_GENESIS = "GENESIS"
TRANSITION_SUCCESSOR = "SUCCESSOR"
TRANSITION_IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"


@dataclass(frozen=True, slots=True)
class MonotonicChainSpec:
    """Everything that differs between one chained record kind and another -- and nothing that
    does not.

    Deliberately narrow. A spec names *which* record kind, *how* to prove one self-consistent,
    *which* chain a record belongs to, and *what its own chain fields are called*. It carries no
    rule: genesis, succession, terminality, status legality, pointer movement, and the
    Compare-And-Swap discipline all live in this module and are identical for every chain, which
    is the entire point of there being one mechanism rather than two.

    Signature verification is deliberately **not** a spec field either. It is passed per call as
    the ``verify`` callback of :func:`commit_chain_transition`, because the two shipped chains ask
    genuinely different questions of genuinely different keys -- a declaration's signature is
    verified against the Human Authority key that call's own fresh Boot restored from the current
    Project Binding, while a root admission's is verified against a deployment-configured trust
    anchor that is, by design, not resolvable from inside the Store at all. Collapsing those into
    one spec field would have to pretend they are the same question.
    """

    record_kind: str
    id_field: str
    semantic_fingerprint_field: str
    require_valid: Callable[[Any], dict[str, Any]]
    recompute_id: Callable[[dict[str, Any]], str]
    recompute_semantic_fingerprint: Callable[[dict[str, Any]], str]
    chain_key_of: Callable[[dict[str, Any]], str]
    generation_field: str = field(default=GENERATION_FIELD)
    predecessor_field: str = field(default=PREDECESSOR_FIELD)
    status_field: str = field(default=STATUS_FIELD)
    active_status: str = field(default=ACTIVE_STATUS)
    revoked_status: str = field(default=REVOKED_STATUS)


def current_chain_record_id(current_state: Mapping[str, Any], chain_key: str) -> str | None:
    """Return the record id *current_state*'s own canonical pointer names for *chain_key*, or
    ``None`` when nothing has ever been made current for that chain.

    A pure read: no Store I/O, no resolution, no verification. ``None`` is returned for every
    shape that cannot carry a pointer at all -- an absent or non-mapping ``semantic_state``,
    domain, or ``claims`` map, or a non-string value -- rather than raising: a missing pointer is
    a perfectly ordinary state of the world, and deciding what it *means* belongs to the caller.
    Every caller in this package treats it as a refusal.
    """

    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        return None
    domain = semantic_state.get(CHAIN_POINTER_SEMANTIC_DOMAIN)
    if not isinstance(domain, Mapping):
        return None
    claims = domain.get(CHAIN_POINTER_CLAIMS_FIELD)
    if not isinstance(claims, Mapping):
        return None
    value = claims.get(chain_key)
    return value if isinstance(value, str) else None


def _next_semantic_state(
    current_state: Mapping[str, Any], chain_key: str, record_id: str
) -> dict[str, Any]:
    """Return a deep copy of *current_state*'s own ``semantic_state`` with exactly one claim
    added or replaced -- never a rebuilt domain, never a replaced ``semantic_state``.

    The scope is deliberately as narrow as ``reflow/bookkeeping.py``'s own single sanctioned
    ``semantic_state`` mutation: every other field of the ``runtime`` domain (its ``status``, its
    ``identity_refs``/``evidence_refs``, its ``blind_spots``), every other chain's own pointer,
    and every other domain are carried through byte-identical.
    """

    semantic_state = current_state.get("semantic_state")
    if not isinstance(semantic_state, Mapping):
        raise RuntimeRequirementError(
            "the current Project State carries no readable semantic_state -- refusing to move a "
            "runtime transition-chain pointer inside a State this module cannot read"
        )
    next_semantic_state = deepcopy(dict(semantic_state))
    domain = next_semantic_state.get(CHAIN_POINTER_SEMANTIC_DOMAIN)
    if not isinstance(domain, dict):
        raise RuntimeRequirementError(
            "the current Project State carries no readable "
            f"semantic_state.{CHAIN_POINTER_SEMANTIC_DOMAIN} domain"
        )
    claims = domain.get(CHAIN_POINTER_CLAIMS_FIELD)
    if not isinstance(claims, dict):
        raise RuntimeRequirementError(
            "the current Project State carries no readable "
            f"semantic_state.{CHAIN_POINTER_SEMANTIC_DOMAIN}.{CHAIN_POINTER_CLAIMS_FIELD} map"
        )
    claims[chain_key] = record_id
    return next_semantic_state


def require_self_consistent_record(spec: MonotonicChainSpec, record: Any) -> dict[str, Any]:
    """Prove *record* schema-valid for its own kind, then prove its own declared content address
    and semantic fingerprint equal what this repository independently recomputes from its own
    body -- the identical tamper check every ``_resolve_*`` in ``bootstrap.py`` and ``route.py``
    already applies to a Store-resolved record, applied here to a *proposed* one before it can
    move anything.

    Also proves the two chain fields readable and well-shaped: ``generation`` a non-negative
    integer (never a ``bool``, which Python would otherwise let through as an ``int``), and
    ``predecessor_ref`` either ``None`` or a reference of this record's own kind.
    """

    checked = spec.require_valid(record)
    declared_id = checked.get(spec.id_field)
    if spec.recompute_id(checked) != declared_id:
        raise RuntimeRequirementError(
            f"{spec.record_kind} own recomputed identity does not equal its own declared value "
            "-- refusing to commit it or to make it current"
        )
    if spec.recompute_semantic_fingerprint(checked) != checked.get(spec.semantic_fingerprint_field):
        raise RuntimeRequirementError(
            f"{spec.record_kind} own recomputed semantic fingerprint does not equal its own "
            "declared value -- refusing to commit it or to make it current"
        )
    if not isinstance(declared_id, str) or not declared_id:
        raise RuntimeRequirementError(f"{spec.record_kind} carries no readable {spec.id_field}")
    generation = checked.get(spec.generation_field)
    if isinstance(generation, bool) or not isinstance(generation, int) or generation < 0:
        raise RuntimeRequirementError(
            f"{spec.record_kind}.{spec.generation_field} must be a non-negative integer: "
            f"{generation!r}"
        )
    predecessor = checked.get(spec.predecessor_field)
    if predecessor is not None:
        if not isinstance(predecessor, Mapping) or predecessor.get("kind") != spec.record_kind:
            raise RuntimeRequirementError(
                f"{spec.record_kind}.{spec.predecessor_field} must be null or a reference of "
                f"kind {spec.record_kind!r}: {predecessor!r}"
            )
        if not isinstance(predecessor.get("id"), str) or not predecessor["id"]:
            raise RuntimeRequirementError(
                f"{spec.record_kind}.{spec.predecessor_field} carries no readable id: "
                f"{predecessor!r}"
            )
    status = checked.get(spec.status_field)
    if status not in (spec.active_status, spec.revoked_status):
        raise RuntimeRequirementError(
            f"{spec.record_kind}.{spec.status_field} is not a recognized status: {status!r}"
        )
    return checked


def require_legal_transition(
    spec: MonotonicChainSpec,
    *,
    proposed: Mapping[str, Any],
    current_record: Mapping[str, Any] | None,
    current_id: str | None,
) -> str:
    """Prove the whole transition from *current_record* to *proposed* legal, and return which
    kind of transition it is (:data:`TRANSITION_GENESIS` or :data:`TRANSITION_SUCCESSOR`).

    Re-derived in full, from freshly loaded State, on every commit attempt -- never cached from a
    previous iteration. Refusals are :class:`~manosube_agent_civilization.runtime.errors.
    RuntimeRequirementError` and are **never** retried: every one of them describes a fact about
    the chain that a retry cannot change, because changing it would require a new signature over
    a new payload.

    The rules, in evaluation order:

    0. **Same chain.** Whatever the pointer names must derive the identical chain key the proposed
       record does. This can only fail if a pointer was moved by something other than this
       mechanism, and refusing on it is cheaper than reasoning about what such a State means.
    1. **Terminality first.** If the current record's own status is ``REVOKED``, nothing may
       follow it, ever -- not a successor, not an ancestor replay, not a re-activation. Any later
       re-activation requires a separately adopted new target epoch/chain, which is deliberately
       out of this round's scope (``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.5, item 8); it is never
       silent pointer movement. Terminality is checked before the successor rule so that a
       perfectly well-formed successor to a revoked head is refused *as terminal*, which is the
       true reason, rather than as some accidental generation mismatch.
    2. **Genesis**, when the chain has no current record: ``generation`` must be ``0``,
       ``predecessor_ref`` must be null, and the record's own status must be ``ACTIVE`` -- a
       genesis ``REVOKED`` record would revoke nothing and would open a terminal chain that never
       admitted anything (§13.5, item 6).
    3. **Genesis is refused when a chain already exists.** A ``generation=0``/null-predecessor
       record proposed against a live chain is exactly the ancestor-replay attempt the
       decisive controls exercise, and it fails here.
    4. **Successor**, when a current record exists: ``predecessor_ref`` must name the **exact**
       id the pointer currently holds, and ``generation`` must be exactly one past the current
       record's own. Wrong predecessor, skipped generation, and duplicate generation with a
       different body all fail one of these two, with distinct messages.
    """

    proposed_id = str(proposed[spec.id_field])
    generation = int(proposed[spec.generation_field])
    predecessor = proposed.get(spec.predecessor_field)
    predecessor_id = (
        str(predecessor["id"])
        if isinstance(predecessor, Mapping) and isinstance(predecessor.get("id"), str)
        else None
    )

    if current_record is not None and spec.chain_key_of(dict(current_record)) != spec.chain_key_of(
        dict(proposed)
    ):
        raise RuntimeRequirementError(
            f"this chain's own pointer names a {spec.record_kind} ({current_id!r}) belonging to a "
            f"different chain than {proposed_id!r} -- refusing: a record may only ever supersede "
            "one that is genuinely about the same target"
        )

    if current_record is not None and current_record.get(spec.status_field) == spec.revoked_status:
        raise RuntimeRequirementError(
            f"the current {spec.record_kind} for this chain ({current_id!r}) is REVOKED, which is "
            f"terminal -- refusing {proposed_id!r}: after a revocation no same-chain successor "
            "and no ancestor replay is ever admitted again, and any later reactivation requires "
            "a separately adopted new target epoch, never silent pointer movement"
        )

    if current_record is None:
        if generation != 0 or predecessor_id is not None:
            raise RuntimeRequirementError(
                f"no {spec.record_kind} is current for this chain, so only a genesis record "
                f"({spec.generation_field}=0, {spec.predecessor_field}=null) may be committed -- "
                f"refusing {proposed_id!r} ({spec.generation_field}={generation}, "
                f"{spec.predecessor_field}={predecessor!r})"
            )
        if proposed.get(spec.status_field) != spec.active_status:
            raise RuntimeRequirementError(
                f"a genesis {spec.record_kind} must be ACTIVE -- refusing {proposed_id!r} "
                f"({proposed.get(spec.status_field)!r}): a chain cannot open with a revocation of "
                "something that was never admitted"
            )
        return TRANSITION_GENESIS

    if predecessor_id is None:
        raise RuntimeRequirementError(
            f"a {spec.record_kind} is already current for this chain ({current_id!r}), so a "
            f"genesis record is refused -- {proposed_id!r} declares no {spec.predecessor_field} "
            "at all, which is exactly the ancestor-replay a monotonic chain exists to prevent"
        )
    if predecessor_id != current_id:
        raise RuntimeRequirementError(
            f"{proposed_id!r} declares {spec.predecessor_field}={predecessor_id!r}, which is not "
            f"the {spec.record_kind} this chain's own pointer currently names ({current_id!r}) -- "
            "refusing: a successor may only ever replace the exact head it was signed against, "
            "and re-aiming an already-signed body at a different predecessor would require a new "
            "signature this committer cannot produce"
        )
    current_generation = current_record.get(spec.generation_field)
    if isinstance(current_generation, bool) or not isinstance(current_generation, int):
        raise RuntimeRequirementError(
            f"the current {spec.record_kind} ({current_id!r}) carries no readable "
            f"{spec.generation_field} -- refusing to compute a successor generation from it"
        )
    if generation != current_generation + 1:
        raise RuntimeRequirementError(
            f"{proposed_id!r} declares {spec.generation_field}={generation}, which is not exactly "
            f"one past the current {spec.record_kind}'s own ({current_generation}) -- refusing: a "
            "skipped, repeated, or rewound generation is never a legal transition"
        )
    return TRANSITION_SUCCESSOR


def commit_chain_transition(
    store: Any,
    project_id: str,
    record: Mapping[str, Any],
    *,
    spec: MonotonicChainSpec,
    committed_at: str,
    verify: Callable[[dict[str, Any], Mapping[str, Any]], None],
) -> dict[str, Any]:
    """Commit *record* **and** move its own chain pointer to it, in one atomic
    :func:`~manosube_agent_civilization.store.commit.commit_state_transition` call -- or refuse
    with no State change at all.

    The two halves are inseparable by construction: there is no call shape through which a caller
    could commit the record without moving the pointer, or move the pointer without committing the
    record.

    ```text
    records=[(<record_kind>, <id>, <the record itself>)]        immutable, as always
    semantic_state.runtime.claims[<chain_key>] = <id>           the current pointer
    ```

    The loop, exactly as ``10_RUNTIME/RUNTIME_CONTRACT.md`` §13.3 states it:

    ```text
    load State fresh
      -> read this chain's own pointer
      -> if the pointer already names this exact record: idempotent no-op success, no transition
      -> resolve the current record from the bound Store
      -> verify(proposed, current_state)          fresh Boot + signature, every iteration
      -> require_legal_transition(...)            fails CLOSED, never retried
      -> commit_state_transition(...)
           StaleStateError -> reload and re-evaluate the ENTIRE transition (this is where a
                              contention loser discovers the head moved, and refuses)
    ```

    *verify* is called with the proposed record and the State this attempt actually loaded, and
    must raise to refuse. It is deliberately re-run on every iteration rather than once before the
    loop: it is where each chain's own fresh Boot and signature verification happen, and a commit
    must never land under an authority that changed while this call was contending -- the
    identical per-attempt discipline P15-R1-F5 established for ``route.py``.

    *committed_at* is required and caller-supplied: this module reads no clock, the identical
    discipline every other route and committer in this repository already keeps.

    Returns ``{"record_ref", "chain_key", "generation", "transition", "committed_state"}``.
    ``committed_state`` is ``None`` for an idempotent replay, because no State was committed.
    """

    checked = require_self_consistent_record(spec, record)
    record_id = str(checked[spec.id_field])
    if checked.get("project_id") != project_id:
        raise RuntimeRequirementError(
            f"{spec.record_kind} names a different project than the one being committed into: "
            f"{checked.get('project_id')!r} != {project_id!r}"
        )
    chain_key = spec.chain_key_of(checked)

    for _ in range(MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        current_id = current_chain_record_id(current_state, chain_key)
        if current_id == record_id:
            # Item 6 of the canonical commit semantics: replaying the exact record the pointer
            # already names is idempotent. It is answered here, before any verification or
            # transition evaluation, precisely because it is *not* a transition -- treating it as
            # one would have to invent a "successor of itself" rule, and would move a pointer that
            # is already where the caller is asking it to be.
            return {
                "record_ref": {"kind": spec.record_kind, "id": record_id},
                "chain_key": chain_key,
                "generation": int(checked[spec.generation_field]),
                "transition": TRANSITION_IDEMPOTENT_REPLAY,
                "committed_state": None,
            }
        current_record = (
            store.resolve_record(project_id, spec.record_kind, current_id)
            if current_id is not None
            else None
        )
        if current_id is not None and current_record is None:
            raise RuntimeRequirementError(
                f"this chain's own pointer names {spec.record_kind}/{current_id!r}, which does "
                "not resolve in the bound Store -- refusing rather than move a pointer whose own "
                "current value cannot be read"
            )
        verify(checked, current_state)
        transition = require_legal_transition(
            spec,
            proposed=checked,
            current_record=dict(current_record) if current_record is not None else None,
            current_id=current_id,
        )

        transaction_id = f"TX-{record_id}-{current_state['state_revision']}"
        next_state = dict(current_state)
        next_state["semantic_state"] = _next_semantic_state(current_state, chain_key, record_id)
        next_state["state_revision"] = current_state["state_revision"] + 1
        next_state["previous_state_fingerprint"] = current_state["semantic_fingerprint"]
        next_state["lineage_head_ref"] = {"kind": "state_transition", "id": transaction_id}
        next_state["semantic_fingerprint"] = fingerprint_project_state(next_state).as_dict()
        plan = {
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
                plan,
                records=[(spec.record_kind, record_id, dict(checked))],
            )
        except RecordConflictError as error:
            raise RuntimeEnvelopeIntegrityError(
                f"a different record already occupies {spec.record_kind}/{record_id} with "
                "different content -- refusing rather than trust either"
            ) from error
        except StaleStateError:
            # Genuine contention. The next iteration re-derives EVERYTHING from freshly loaded
            # State: if the bump was unrelated, the identical transition is still legal and the
            # retry succeeds; if it was another commit on this very chain, the pointer no longer
            # names this record's own signed predecessor and require_legal_transition refuses
            # above -- the loser fails closed rather than silently re-aiming a signed body.
            continue
        return {
            "record_ref": {"kind": spec.record_kind, "id": record_id},
            "chain_key": chain_key,
            "generation": int(checked[spec.generation_field]),
            "transition": transition,
            "committed_state": next_state,
        }
    raise RuntimeRequirementError(
        f"could not durably commit {spec.record_kind}/{record_id} after {MAX_COMMIT_RETRIES} "
        "Compare-And-Swap retries -- sustained unrelated contention on this project's own State"
    )


__all__ = [
    "ACTIVE_STATUS",
    "CHAIN_POINTER_CLAIMS_FIELD",
    "CHAIN_POINTER_SEMANTIC_DOMAIN",
    "GENERATION_FIELD",
    "MAX_COMMIT_RETRIES",
    "PREDECESSOR_FIELD",
    "REVOKED_STATUS",
    "STATUS_FIELD",
    "TRANSITION_GENESIS",
    "TRANSITION_IDEMPOTENT_REPLAY",
    "TRANSITION_SUCCESSOR",
    "MonotonicChainSpec",
    "commit_chain_transition",
    "current_chain_record_id",
    "require_legal_transition",
    "require_self_consistent_record",
]
