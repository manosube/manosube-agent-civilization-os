"""Append-only-lineage authoritative filesystem State Store."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from manosube_agent_civilization.state.canonicalize import (
    _validate,
    canonical_json_bytes,
    canonical_semantic_state_bytes,
)
from manosube_agent_civilization.state.errors import SchemaValidationError
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state

from .atomic_write import atomic_write, fsync_directory
from .errors import (
    AlreadyInitializedError,
    BoundaryError,
    CorruptStoreError,
    RecordConflictError,
    RevisionError,
    StaleStateError,
    StateNotFoundError,
    TransactionConflictError,
)
from .interface import FaultInjector

STAGES=("AFTER_JOURNAL_CREATED","AFTER_STAGED_STATE_WRITTEN","AFTER_STAGED_RECORDS_WRITTEN","AFTER_COMMIT_INTENT","AFTER_LINEAGE_APPEND","AFTER_RECORDS_PROMOTED","BEFORE_CURRENT_REPLACE","AFTER_CURRENT_REPLACE","BEFORE_COMMITTED_MARKER")
TRANSITION_SCHEMA_ID="https://schemas.manosube.org/agent-civilization-os/v0.1/state/state_transition.schema.json"
GENESIS_RECEIPT_SCHEMA_ID="https://schemas.manosube.org/agent-civilization-os/v0.1/state/genesis_receipt.schema.json"
#: MANOSUBE-GENESIS-MANIFEST-DIGEST-SHA256-0.1 -- the same sha256+domain-separator+profile
#: convention `state.fingerprint`'s own `MANOSUBE-STATE-SHA256-0.1` already uses, applied to
#: a genesis transaction's own exact (kind, id) manifest membership (never body content --
#: NEVER_CONFUSED_WITH_BODY_SEMANTIC_IDENTITY=true). A distinct domain separator from
#: State's own semantic fingerprint keeps the two digest spaces from ever colliding.
_GENESIS_MANIFEST_DIGEST_DOMAIN=b"MANOSUBE_AGENT_CIVILIZATION_OS\x00GENESIS_MANIFEST\x000.1\x00"

class FileStateStore:
    def __init__(self, root: Path, *, schema_root: Path) -> None:
        self.root=root.resolve(); self.schema_root=schema_root.resolve()
        if self.root == Path.cwd().resolve() or self.root.is_relative_to(Path.cwd().resolve()):
            raise BoundaryError("backend root must be outside the repository working tree")
        self.root.mkdir(parents=True,exist_ok=True)
        if self.root.is_symlink(): raise BoundaryError("symlink backend root is prohibited")

    def _project(self, project_id: str) -> Path:
        if not project_id or "/" in project_id or ".." in project_id: raise BoundaryError("invalid project identity")
        path=(self.root/"projects"/project_id).resolve()
        if not path.is_relative_to(self.root): raise BoundaryError("project path escapes backend")
        return path

    @contextmanager
    def _lock(self, project_id: str) -> Iterator[None]:
        path=self._project(project_id)/"locks"/"store.lock"; path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("a+b") as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            try: yield
            finally: fcntl.flock(stream.fileno(),fcntl.LOCK_UN)

    def _validate_state(self, project_id: str, state: Mapping[str,Any]) -> dict[str,Any]:
        canonical_semantic_state_bytes(state,schema_root=self.schema_root)
        value=deepcopy(dict(state)); actual=fingerprint_project_state(value,schema_root=self.schema_root).as_dict()
        if value["project_id"] != project_id or value["semantic_fingerprint"] != actual: raise CorruptStoreError("state identity or fingerprint mismatch")
        return value

    def _lineage(self, project_id: str) -> Path: return self._project(project_id)/"events"/"transitions.jsonl"
    def _current(self, project_id: str) -> Path: return self._project(project_id)/"state"/"current.json"

    def _record_kind_dir(self, project_id: str, kind: str) -> Path:
        if not kind or "/" in kind or ".." in kind: raise BoundaryError("invalid record kind")
        return self._project(project_id)/"records"/kind

    def _record_path(self, project_id: str, kind: str, record_id: str) -> Path:
        if not record_id or "/" in record_id or ".." in record_id: raise BoundaryError("invalid record identity")
        return self._record_kind_dir(project_id,kind)/f"{record_id}.json"

    def resolve_record(self, project_id: str, kind: str, record_id: str) -> dict[str,Any]|None:
        """Return the immutable committed record of *kind* addressed by *record_id*, or ``None``.

        Only a record whose promoting transaction is durably ``COMMITTED`` is ever returned
        -- R8-F4. ``commit``'s own sequence promotes a transaction's staged records
        (``AFTER_RECORDS_PROMOTED``) *before* it replaces ``current.json`` and writes that
        transaction's recovery journal's own ``COMMITTED`` marker (``BEFORE_COMMITTED_MARKER``
        onward): a crash in that window once left a record's permanent file already on disk,
        and therefore already resolvable here, while the State transition it belongs to had
        not yet published anywhere else -- the same partial-transaction visibility gap
        R7-F5 already closed for :meth:`resolve_transaction`, now closed for this method too,
        through the identical durability check (:meth:`_record_committed_by_any_transaction`,
        built on the same ``_transaction_committed`` this class already uses) so the two
        methods' visibility can never again diverge.
        """

        path=self._record_path(project_id,kind,record_id)
        if not path.exists():
            return None
        if not self._record_committed_by_any_transaction(project_id,kind,record_id):
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:
            raise CorruptStoreError(f"malformed record: {kind}/{record_id}") from exc

    def _record_committed_by_any_transaction(self, project_id: str, kind: str, record_id: str) -> bool:
        """Return whether *(kind, record_id)*'s permanent file was promoted by a transaction
        that is now durably ``COMMITTED`` -- R8-F4, sharpened by R10-F3, sharpened again by
        R12-F1.

        A record's own file carries no transaction-id metadata, so this asks every
        transaction that ever recorded this same ``manifest.json`` reproduction.

        R10-F3 (SHUKOU Round 10): a record file existing on disk is never, by itself,
        evidence that any transaction actually promoted it -- ``FILE_EXISTS_NE_CANONICAL_
        RECORD=true``. Two prior readings of "no evidence found" as "must be committed" are
        both refused now: an absent ``recovery`` directory (no transaction has ever run
        :meth:`commit` for this project at all) no longer implies every record file predates
        tracking and is therefore trusted; and a key no manifest anywhere claims
        (``claimed_by_any=false``) no longer implies a legitimate pre-tracking record either
        (``NO_MANIFEST_CLAIM_NE_COMMITTED=true``) -- this vertical carries no actual
        pre-manifest-tracking data to reconcile, and SHUKOU's own adoption refuses that
        inference as a permanent, unverifiable "maybe legacy" excuse. A caller that genuinely
        needs to adopt real historical data would need an explicit, checkable migration
        receipt (a ``STORE_FORMAT_VERSION``/``MIGRATION_RECEIPT``/``LEGACY_ADOPTION_MANIFEST``
        fact) -- no such mechanism exists or is invented here, so an unclaimed record is
        simply refused, not silently trusted. Genesis's own records (R10-F1) are staged and
        promoted through this identical manifest mechanism under the ``TX-GENESIS`` journal,
        so they are found and committed here exactly like any other transaction's -- no
        special-casing needed in this method for genesis at all.

        R12-F1 (SHUKOU Phase 7 Final Closure): the prior version of this method returned on
        the *first* journal (in sorted directory-name order) whose manifest claimed this key
        -- ``FIRST_CLAIMANT_NE_CANONICAL_VERDICT=true``/``JOURNAL_DIRECTORY_ORDER_NE_
        AUTHORITY=true``. Two real bugs followed from that: an uncommitted claimant sorting
        before a real, COMMITTED claimant made a genuinely canonical record wrongly
        invisible; and no claimant's own staged body was ever compared against any other's,
        so a same-identity/different-body divergence across two claimants (or between a
        claimant and the permanent file) silently passed, or silently failed, purely by
        chance of sort order -- never actually detected either way. This method now collects
        *every* manifest claimant unconditionally (``ALL_CLAIMANTS_MUST_BE_EXAMINED=true``,
        ``CLAIMANT_ORDER_PERMUTATION_INVARIANT=true`` -- the result cannot depend on
        directory iteration order, since every claimant is always visited): the record is
        visible only once at least one committed claimant exists
        (``ANY_COMMITTED_CLAIMANT_MAKES_IDENTICAL_RECORD_VISIBLE=true``), and only if every
        body actually available to compare -- the permanent file's, and every claimant's own
        staged copy where one still exists in its journal -- is byte-identical
        (``SAME_ID_DIFFERENT_BODY_MUST_FAIL_CLOSED=true``, via the existing
        :class:`CorruptStoreError`, never a second, parallel Conflict authority). A claimant
        whose manifest claims the key but carries no staged file of its own contributes no
        body evidence either way -- :meth:`_stage_records` deliberately drops (never writes)
        a staged copy identical to what was already the current permanent record at that
        claimant's own staging time, so a missing staged file only ever means "nothing new to
        compare here", never "this claimant's body differs"
        (``MISSING_BEFORE_RECORD_STAGE`` is not ``DIFFERENT_BODY_AFTER_RECORD_STAGE``, and
        must never be conflated with it).
        """

        recovery=self._project(project_id)/"state"/"recovery"
        if not recovery.exists():
            return False
        bodies:set[bytes]=set()
        permanent_path=self._record_path(project_id,kind,record_id)
        if permanent_path.exists():
            bodies.add(permanent_path.read_bytes())
        any_committed=False
        for journal in sorted(recovery.iterdir()):
            if not journal.is_dir():
                continue
            manifest_path=journal/"manifest.json"
            if not manifest_path.exists():
                continue
            entries=self._read_manifest_entries(manifest_path, journal.name)
            if (kind,record_id) not in entries:
                continue
            if (journal/"COMMITTED").exists():
                any_committed=True
            staged_path=journal/"records"/f"{kind}__{record_id}.json"
            if staged_path.exists():
                bodies.add(staged_path.read_bytes())
        if not any_committed:
            return False
        if len(bodies)>1:
            raise CorruptStoreError(
                f"same-identity record diverges across manifest claimants: {kind}/{record_id}"
            )
        return True

    def resolve_transaction(self, project_id: str, transaction_id: str) -> dict[str,Any]|None:
        """Return the committed ``state_transition`` event named by *transaction_id*, or
        ``None`` -- R6-F1/R6-F4: a public read path over the existing append-only lineage
        log itself, not a second persistence location. A ``state_transition`` reference
        (``{"kind": "state_transition", "id": tx}``, minted by ``reflow/identity.py``'s
        ``transaction_id`` and published on the Completion Record, the lifecycle event, and
        every committed State's own ``lineage_head_ref``) resolves through here, the same
        way any other record kind resolves through :meth:`resolve_record` -- except the body
        already lives in the lineage log every commit already appends to, so this only reads
        it back, never writes a duplicate copy anywhere.

        Only an event whose own transaction actually reached the lineage log is ever
        returned -- the same durability guarantee :meth:`reconstruct` relies on: a
        transaction that crashed before ``AFTER_LINEAGE_APPEND`` never appears here, exactly
        as it never contributes a State revision.

        R7-F5: ``commit``'s own sequence appends the event to the lineage log
        (``AFTER_LINEAGE_APPEND``) *before* it promotes that transaction's staged records and
        writes its recovery journal's own ``COMMITTED`` marker -- so a crash between those
        two points once left this method returning an event whose own transaction's records
        were still unresolvable, a real partial-transaction visibility gap. This method now
        publishes an event only once its own transaction is durably ``COMMITTED``
        (:meth:`_transaction_committed`), never a transaction recovery has not yet finished
        promoting -- the same recovery journal :meth:`recover` itself completes from, read
        here rather than written to, so there is no second persistence location for this
        state and no divergence from what :meth:`recover` will eventually make visible.
        """

        if not self._transaction_committed(project_id, transaction_id):
            return None
        for event in self._events(project_id):
            if event.get("transaction_id")==transaction_id:
                return deepcopy(event)
        return None

    def resolve_transaction_manifest(self, project_id: str, transaction_id: str) -> list[tuple[str,str]]|None:
        """Return the exact ``(kind, id)`` membership list a *committed* transaction's own
        recovery-journal manifest claims, or ``None`` if *transaction_id* is unresolvable --
        does not exist, or exists but is not yet durably committed (Phase 9 Structural
        Review Round 2, P9-R2-F4).

        A generic, transaction-agnostic public read surface -- no domain-specific comparison
        semantics of any kind live here; a caller decides what "identical", "conflicting",
        "duplicate" mean for its own manifest members. Gated on the identical committed-
        boundary check :meth:`resolve_transaction` already uses
        (:meth:`_transaction_committed`), so the two can never diverge on what counts as
        "this transaction happened". Mirrors :meth:`_transaction_manifest_keys` (``commit``'s
        own internal replay-comparison helper), now exposed publicly rather than restated by
        a caller reading the Store's own on-disk recovery-journal layout directly.

        An empty list means the transaction is committed but adopted no records at all (a
        bare genesis, or an ordinary commit with no ``records`` argument) -- genuinely
        different from ``None``, which means the transaction itself is unresolvable.
        """

        if not self._transaction_committed(project_id, transaction_id):
            return None
        path=self._project(project_id)/"state"/"recovery"/transaction_id/"manifest.json"
        if not path.exists():
            return []
        return self._read_manifest_entries(path, transaction_id)

    def _read_manifest_entries(self, manifest_path: Path, label: str) -> list[tuple[str,str]]:
        """Parse and validate one transaction manifest.json's own member list --
        ``MANIFEST_MEMBER_CONTRACT`` (Phase 9 Completion Repair 4, P9-C4-F1): JSON decode
        success alone never implies manifest validity. A public Store method may not treat a
        persisted file as a trusted Python object merely because ``json.loads`` succeeded --
        a malformed top-level shape, malformed member, or non-string/empty ``kind``/``id``
        must fail closed as :class:`CorruptStoreError`, never leak a raw ``ValueError`` or
        ``TypeError`` from tuple-unpacking a shape nobody validated, and never be silently
        accepted (a ``null`` or numeric ``kind``/``id`` is not a valid canonical identity).

        The one shared reader every call site in this class uses for this identical on-disk
        shape (:meth:`resolve_transaction_manifest`, :meth:`_transaction_manifest_keys`,
        :meth:`_record_committed_by_any_transaction`, and :meth:`_genesis_transaction_
        committed`) -- never a second, competing manifest parser, validated in one reader
        and trusted raw in another.

        *label* names the transaction/journal this manifest belongs to, for diagnostics
        only -- never echoed as a value, only as an identifying label.
        """

        try:
            entries=json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:
            raise CorruptStoreError(f"malformed transaction manifest: {label}") from exc
        if not isinstance(entries,list):
            raise CorruptStoreError(f"transaction manifest is not a JSON array: {label}")
        # Phase 9 Structural Review Round 3, P9-R3-F1 (boundary 3 of 3: the committed
        # manifest read itself): a tampered manifest.json naming the same (kind, id) twice
        # is corruption, not a legitimate duplicate -- fail closed here, before a caller can
        # silently collapse it into a set and lose the very multiplicity that would have
        # revealed the tamper.
        seen: set[tuple[str,str]] = set()
        result: list[tuple[str,str]] = []
        for member in entries:
            if not isinstance(member,list) or len(member)!=2:
                raise CorruptStoreError(
                    f"transaction manifest member is not a two-element array: {label}"
                )
            kind,record_id=member
            if not isinstance(kind,str) or not kind or not isinstance(record_id,str) or not record_id:
                raise CorruptStoreError(
                    f"transaction manifest member has a non-string or empty kind/id: {label}"
                )
            key=(kind,record_id)
            if key in seen:
                raise CorruptStoreError(
                    f"transaction manifest names {kind}/{record_id} more than once: {label}"
                )
            seen.add(key)
            result.append(key)
        return result

    #: R10-F3 (SHUKOU Round 10): the one, explicitly-named genesis transaction identity --
    #: GENESIS_EXCEPTION_IS_EXPLICIT=true, GENESIS_EXCEPTION_IS_NOT_WILDCARD=true. Every
    #: other transaction_id with no recovery journal is refused, never silently trusted.
    GENESIS_TRANSACTION_ID = "TX-GENESIS"

    def _manifest_digest(self, members: list[tuple[str,str]]) -> str:
        """Return the ``MANOSUBE-GENESIS-MANIFEST-DIGEST-SHA256-0.1`` digest of *members*
        (Phase 9 Completion Repair 5, P9-C5-F1): a canonical, order-independent commitment
        to the exact ``(kind, id)`` set a genesis manifest claims.

        *members* must already be known duplicate-free (:meth:`_read_manifest_entries`
        itself refuses a manifest naming the same key twice, before this is ever called) --
        ``GENESIS_MANIFEST_MULTIPLICITY_VALIDATED_BEFORE_DIGEST=true``, this never silently
        folds a duplicate away and digests the collapsed result. Sorting canonically before
        digesting makes an order-only difference between two replays of the identical
        membership produce the identical digest (``ORDER_ONLY_DIFFERENCE_SEMANTICS=
        CANONICAL_ORDER_EQUIVALENT``), while genuinely different membership -- a missing,
        extra, or wrong-kind member -- always produces a different digest.
        """

        canonical=sorted(members)
        payload=canonical_json_bytes([[kind,record_id] for kind,record_id in canonical])
        return "sha256:"+hashlib.sha256(_GENESIS_MANIFEST_DIGEST_DOMAIN+payload).hexdigest()

    def _genesis_receipt_path(self, project_id: str) -> Path:
        return self._project(project_id)/"state"/"genesis_receipt.json"

    def _read_genesis_receipt(self, project_id: str) -> dict[str,Any]|None:
        """Read and schema-validate *project_id*'s own genesis institution receipt (P9-C5-F1),
        or ``None`` if none has ever been written for it. Never trusts a decoded receipt
        object without validating its own shape first -- the identical discipline
        :meth:`_read_manifest_entries` already applies to manifest.json."""

        path=self._genesis_receipt_path(project_id)
        if not path.exists():
            return None
        try:
            receipt: dict[str,Any]=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc:
            raise CorruptStoreError(f"malformed genesis receipt: {project_id}") from exc
        try:
            _validate(receipt,GENESIS_RECEIPT_SCHEMA_ID,self.schema_root)
        except SchemaValidationError as exc:
            raise CorruptStoreError(f"genesis receipt fails its own schema: {project_id}") from exc
        if receipt["project_id"]!=project_id:
            raise CorruptStoreError(
                f"genesis receipt project_id does not match its own project: {project_id}"
            )
        return receipt

    def _transaction_committed(self, project_id: str, transaction_id: str) -> bool:
        """Return whether *transaction_id* is durably ``COMMITTED`` -- R7-F5, sharpened by
        R10-F3, R11-F1, P9-R3-F2, and P9-C4-F2 in turn, replaced again by Phase 9 Completion
        Repair 5 (P9-C5-F1).

        Every prior version of this method's own genesis-institution check inferred
        ``BARE`` vs ``WITH_RECORDS`` from *circumstantial* evidence -- the transaction_id
        string, the lineage event, which journals happen to still exist, which manifests
        happen to still claim a given record -- and SHUKOU's own Completion Repair 5
        adoption formally rejects every one of those as authority
        (``GLOBAL_RECORD_CLAIM_INFERENCE_IS_AUTHORITY=false``, ``LINEAGE_TRANSACTION_ID_
        ALONE_IS_AUTHORITY=false``, ``ORPHANED_PROMOTED_RECORD_HEURISTIC_IS_AUTHORITY=
        false``): P9-C4-F2's own orphaned-record heuristic was itself defeated by a later,
        wholly legitimate transaction reclaiming the identical ``(kind, id, body)`` in its
        own still-intact manifest, making the genuinely-tampered genesis look un-orphaned
        again.

        A genesis transaction's own institution is now settled by an explicit, durable
        receipt (:meth:`_read_genesis_receipt`) written atomically at genesis time,
        declaring ``genesis_mode`` (``BARE``/``WITH_RECORDS``) and -- for ``WITH_RECORDS``
        -- the exact manifest membership's own digest and count. See
        :meth:`_genesis_transaction_committed` for the full decision table.
        """

        if transaction_id != self.GENESIS_TRANSACTION_ID:
            path = self._project(project_id)/"state"/"recovery"/transaction_id
            if not path.exists():
                return False
            return (path/"COMMITTED").exists()
        return self._genesis_transaction_committed(project_id)

    def _genesis_transaction_committed(self, project_id: str) -> bool:
        """The one authority for whether ``TX-GENESIS`` is durably committed, and for which
        of the two genesis institutions it was (P9-C5-F1).

        While a genesis-with-records journal directory still exists, its own ``COMMITTED``
        marker alone still gates crash-stage visibility exactly as before this fix -- a
        journal created but not yet committed (any of the pre-``COMMITTED`` crash stages
        :meth:`initialize` exercises) is legitimately "not yet committed" (``False``, no
        raise), never a contradiction to report, since nothing has durably claimed a
        genesis institution yet. Only once that journal's own ``COMMITTED`` marker exists
        does this method additionally demand the receipt agree with it -- by then, both are
        supposed to already be durably consistent by construction.

        Once the journal is gone (never existed -- bare genesis or never-initialized -- or
        has since been lost/tampered with), the receipt becomes the sole remaining
        authority. SHUKOU: ``LEGACY_GENESIS_AUTO_CLASSIFICATION_ALLOWED=false`` -- a lineage
        event with no receipt to explain it is never silently assumed ``BARE`` or
        ``WITH_RECORDS``; it fails closed as :class:`CorruptStoreError` (a legacy
        pre-receipt genesis or an unexplained migration gap). A receipt that explicitly
        declares ``WITH_RECORDS`` while no journal exists is exactly the P9-C5-F1 fix
        itself: ``MISSING_WITH_RECORDS_JOURNAL_FAILS_CLOSED=true`` -- this can never again
        be silently reinterpreted as bare merely because the journal (and with it, the only
        place a record-reclaim heuristic could ever have looked) is gone.
        """

        journal=self._project(project_id)/"state"/"recovery"/self.GENESIS_TRANSACTION_ID
        if journal.exists():
            if not (journal/"COMMITTED").exists():
                return False
            receipt=self._read_genesis_receipt(project_id)
            if receipt is None:
                raise CorruptStoreError(
                    f"genesis transaction is COMMITTED but carries no genesis receipt: {project_id}"
                )
            if receipt["genesis_mode"]!="WITH_RECORDS":
                raise CorruptStoreError(
                    f"genesis receipt does not declare WITH_RECORDS for a genesis whose "
                    f"own recovery journal exists: {project_id}"
                )
            manifest_path=journal/"manifest.json"
            if not manifest_path.exists():
                raise CorruptStoreError(
                    f"genesis receipt declares WITH_RECORDS but its own manifest is "
                    f"missing: {project_id}"
                )
            entries=self._read_manifest_entries(manifest_path,self.GENESIS_TRANSACTION_ID)
            if len(entries)!=receipt["manifest_member_count"] or self._manifest_digest(entries)!=receipt["manifest_digest"]:
                raise CorruptStoreError(
                    f"genesis receipt's manifest digest does not match its own journal's "
                    f"manifest: {project_id}"
                )
            return True

        receipt=self._read_genesis_receipt(project_id)
        lineage_has_event=any(
            event.get("transaction_id")==self.GENESIS_TRANSACTION_ID
            for event in self._events(project_id)
        )
        if receipt is None:
            if not lineage_has_event:
                return False
            raise CorruptStoreError(
                f"genesis transaction's own lineage event exists but no genesis receipt "
                f"explains it -- migration required or corrupt: {project_id}"
            )
        mode=receipt["genesis_mode"]
        if mode=="WITH_RECORDS":
            raise CorruptStoreError(
                f"genesis receipt declares WITH_RECORDS but its recovery journal is "
                f"missing: {project_id}"
            )
        if mode=="BARE":
            if receipt["manifest_member_count"]!=0 or receipt["manifest_digest"]!=self._manifest_digest([]):
                raise CorruptStoreError(
                    f"BARE genesis receipt's own manifest fields are not the canonical "
                    f"empty manifest: {project_id}"
                )
            return lineage_has_event
        raise CorruptStoreError(f"unknown genesis_mode in genesis receipt: {mode!r}: {project_id}")

    def _events(self, project_id: str) -> list[dict[str,Any]]:
        path=self._lineage(project_id)
        if not path.exists(): return []
        try: return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError("malformed lineage") from exc

    def _verify_event(self, project_id: str, event: Mapping[str,Any], prior: Mapping[str,Any]|None) -> dict[str,Any]:
        _validate(event,TRANSITION_SCHEMA_ID,self.schema_root)
        state=self._validate_state(project_id,event["after_state"]); fp=state["semantic_fingerprint"]
        if event["project_id"]!=project_id or event["after_fingerprint"]!=fp or event["to_revision"]!=state["state_revision"]: raise CorruptStoreError("event/state mismatch")
        if prior is None:
            if event["event_type"]!="GENESIS" or event["from_revision"] is not None or event["before_fingerprint"] is not None or event["to_revision"]!=0: raise RevisionError("invalid genesis")
        else:
            if event["event_type"]!="TRANSITION" or event["from_revision"]!=prior["state_revision"] or event["to_revision"]!=prior["state_revision"]+1 or event["before_fingerprint"]!=prior["semantic_fingerprint"] or state["previous_state_fingerprint"]!=prior["semantic_fingerprint"]: raise RevisionError("non-contiguous transition")
        return state

    def initialize(self, project_id: str, initial_state: Mapping[str,Any], *, records: list[tuple[str,str,Mapping[str,Any]]]|None=None, fault: FaultInjector|None=None) -> dict[str,Any]:
        """Initialize *project_id*'s genesis State -- R10-F1: *records*, when supplied, are
        immutable bodies (the same ``(kind, id, body)`` shape :meth:`commit` already takes)
        this genesis State itself references and must therefore close to a real, canonical,
        Store-adopted predecessor from the moment genesis exists -- ``CANONICAL_REFERENCE_
        CLOSURE_REQUIRED=true``/``GENESIS_DANGLING_CANONICAL_REFERENCE_ALLOWED=false``. They
        are staged and promoted through the identical manifest/journal mechanism
        :meth:`commit` already uses for every later transaction, under the same explicit
        :data:`GENESIS_TRANSACTION_ID` -- no second persistence owner, no second Source
        Snapshot producer, no second ``initialize`` path: this is still the one
        ``FileStateStore`` this vertical has, staging into the one canonical record store it
        already writes to. A caller with no records to close (the common case for every
        genesis this vertical minted before R10-F1) gets the identical bare genesis this
        method always produced -- no journal, no manifest, nothing new to recover.

        *fault* is the identical :data:`FaultInjector` hook :meth:`commit` already accepts,
        raised at the identical named :data:`STAGES` boundaries -- no second fault-injection
        surface, so a genesis-with-records crash is exercised, and recovered from, through
        exactly the same mechanism and the same generic :meth:`recover` as every other
        transaction.

        Phase 9 Completion Repair 5 (P9-C5-F1): every genesis -- bare or with-records --
        also writes an explicit, durable genesis institution receipt
        (:meth:`_genesis_receipt_path`, deliberately outside ``state/recovery/`` so it
        survives even a wholesale-deleted recovery journal directory), declaring
        ``genesis_mode`` and, for ``WITH_RECORDS``, the exact manifest membership's own
        digest and count -- see :meth:`_genesis_transaction_committed` for how this receipt
        becomes the one authority a genesis institution is ever settled by.
        """

        def hit(stage: str) -> None:
            if fault:
                fault(stage)

        with self._lock(project_id):
            if self._lineage(project_id).exists(): raise AlreadyInitializedError(project_id)
            state=self._validate_state(project_id,initial_state)
            if state["state_revision"]!=0 or state["previous_state_fingerprint"] is not None: raise RevisionError("initial revision must be zero")
            event={"schema_version":"0.1","transaction_id":self.GENESIS_TRANSACTION_ID,"event_type":"GENESIS","project_id":project_id,"from_revision":None,"to_revision":0,"before_fingerprint":None,"after_fingerprint":state["semantic_fingerprint"],"after_state":state,"evidence_refs":[],"committed_at":state["state_metadata"]["recorded_at"]}
            self._verify_event(project_id,event,None)
            receipt_path=self._genesis_receipt_path(project_id)
            if records:
                # Mirrors commit()'s own stage order exactly (event/state staged, records
                # staged, COMMIT_INTENT, lineage append, records promoted, current
                # published, COMMITTED marker last) so the existing, generic recover() --
                # unaware and uncaring whether an event is GENESIS- or TRANSITION-shaped --
                # can complete an interrupted genesis exactly like any other transaction. No
                # second recovery mechanism, no second fault-injection surface.
                journal=self._project(project_id)/"state"/"recovery"/self.GENESIS_TRANSACTION_ID
                journal.mkdir(parents=True,exist_ok=True)
                atomic_write(journal/"event.json",canonical_json_bytes(event))
                hit(STAGES[0])
                atomic_write(journal/"state.json",canonical_json_bytes(state))
                hit(STAGES[1])
                self._stage_records(project_id,journal,list(records))
                # The receipt is written once the manifest itself is durable, re-reading it
                # (rather than re-deriving from the caller's own *records* argument) so the
                # receipt's own digest/count are guaranteed byte-for-byte consistent with
                # what this transaction's own manifest.json actually, durably claims.
                manifest_entries=self._read_manifest_entries(journal/"manifest.json",self.GENESIS_TRANSACTION_ID)
                atomic_write(receipt_path,canonical_json_bytes({
                    "schema_version":"0.1","project_id":project_id,
                    "transaction_id":self.GENESIS_TRANSACTION_ID,"genesis_mode":"WITH_RECORDS",
                    "manifest_member_count":len(manifest_entries),
                    "manifest_digest":self._manifest_digest(manifest_entries),
                }))
                hit(STAGES[2])
                atomic_write(journal/"COMMIT_INTENT",b"1")
                hit(STAGES[3])
                self._append(project_id,event)
                hit(STAGES[4])
                self._promote_staged_records(project_id,journal)
                hit(STAGES[5])
                hit(STAGES[6])
                atomic_write(self._current(project_id),canonical_json_bytes(state))
                hit(STAGES[7])
                hit(STAGES[8])
                atomic_write(journal/"COMMITTED",b"1")
            else:
                # Written before the lineage/current pair below: a crash between this
                # write and those (this branch carries no fault-injection/recovery support,
                # identically to before this fix) leaves only the receipt durable, which
                # _genesis_transaction_committed already correctly reads as "not yet
                # committed" (no raise) rather than a contradiction -- never the reverse
                # ordering, which would instead leave a lineage event with no receipt to
                # explain it, indistinguishable from unmigrated legacy evidence.
                atomic_write(receipt_path,canonical_json_bytes({
                    "schema_version":"0.1","project_id":project_id,
                    "transaction_id":self.GENESIS_TRANSACTION_ID,"genesis_mode":"BARE",
                    "manifest_member_count":0,"manifest_digest":self._manifest_digest([]),
                }))
                atomic_write(self._lineage(project_id),canonical_json_bytes(event)+b"\n")
                atomic_write(self._current(project_id),canonical_json_bytes(state))
            return deepcopy(state)

    def _committed_events(self, project_id: str) -> list[dict[str,Any]]:
        """The append-only lineage log, filtered to events whose own transaction is
        durably ``COMMITTED`` -- R9-F4. ``commit``'s own sequence appends an event to the
        lineage (``AFTER_LINEAGE_APPEND``) *before* it promotes that transaction's staged
        records, replaces ``current.json`` or writes that transaction's own ``COMMITTED``
        marker -- a crash in that window once left every public read surface built on top
        of the raw log (``reconstruct``, and therefore ``load_current``) reporting a
        revision no different call ever agreed was real. Only the trailing entry can ever
        be uncommitted this way (this Store enforces one in-flight transaction at a time
        via its own project lock, and every earlier entry was necessarily committed before
        the next commit began), so this stops at -- and excludes -- the first event whose
        transaction is not yet durably ``COMMITTED``, the same check :meth:`resolve_
        transaction`/:meth:`resolve_record` already apply per-transaction (R7-F5/R8-F4),
        now the single boundary every public read shares. Recovery's own bookkeeping (
        :meth:`recover`) reads the unfiltered log directly (:meth:`_events`) -- it is the
        one caller allowed to see a dangling entry, since completing or discarding it is
        exactly its job.
        """

        committed: list[dict[str,Any]] = []
        for event in self._events(project_id):
            if not self._transaction_committed(project_id, event["transaction_id"]):
                break
            committed.append(event)
        return committed

    def reconstruct(self, project_id: str) -> dict[str,Any]:
        prior=None
        for event in self._committed_events(project_id): prior=self._verify_event(project_id,event,prior)
        if prior is None: raise CorruptStoreError("lineage has no genesis")
        return deepcopy(prior)

    def load_current(self, project_id: str) -> dict[str,Any]:
        reconstructed=self.reconstruct(project_id); path=self._current(project_id)
        if not path.exists():
            atomic_write(path,canonical_json_bytes(reconstructed)); return deepcopy(reconstructed)
        try: current=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: raise CorruptStoreError("invalid current view") from exc
        self._validate_state(project_id,current)
        if canonical_json_bytes(current)==canonical_json_bytes(reconstructed): return current
        # R9-F4: current.json can legitimately be one revision ahead of the committed
        # lineage view -- a crash between AFTER_CURRENT_REPLACE and the transaction's own
        # COMMITTED marker leaves exactly this gap, and recover() has not yet run. The
        # committed (reconstructed) view stays authoritative until it does; this is a
        # recoverable, expected state, never corruption. Anything else -- current.json
        # behind the committed view, or more than one revision ahead -- has no such
        # explanation and still raises.
        if current.get("state_revision")==reconstructed["state_revision"]+1: return deepcopy(reconstructed)
        raise CorruptStoreError("current view differs from lineage")

    def _append(self, project_id: str, event: Mapping[str,Any]) -> None:
        path=self._lineage(project_id); path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("ab") as stream: stream.write(canonical_json_bytes(event)+b"\n"); stream.flush(); os.fsync(stream.fileno())
        fsync_directory(path.parent)

    def _stage_records(self, project_id: str, journal: Path, records: list[tuple[str,str,Mapping[str,Any]]]) -> list[tuple[str,str,bytes]]:
        """Return ``(kind, id, canonical_bytes)`` for every record this transaction must
        promote, after a same-ID/different-body conflict pre-check against every record
        already durably committed under a prior transaction.

        A record identical, byte-for-byte, to one already committed is dropped here: it is
        already canonical, and re-staging it would double-write the same immutable file for
        no reason. A duplicate identity *within this one manifest* is rejected the same as a
        conflict with a prior commit -- a transaction cannot stage two different bodies, or
        even two identical stagings, under one (kind, id).

        Every supplied ``(kind, id)`` -- staged fresh or already canonical -- is recorded in
        ``manifest.json``, unconditionally: R2-F3B needs this transaction's full declared
        membership to survive even for keys that needed no fresh file, so a replay can later
        prove the *set* of records this transaction claims, not only the bodies of the ones
        it happened to write.
        """

        staged: list[tuple[str,str,bytes]] = []
        seen: set[tuple[str,str]] = set()
        for kind, record_id, body in records:
            key=(kind,record_id)
            if key in seen: raise RecordConflictError(f"{kind}/{record_id}")
            seen.add(key)
            canonical=canonical_json_bytes(body)
            existing=self._record_path(project_id,kind,record_id)
            if existing.exists():
                if existing.read_bytes()!=canonical: raise RecordConflictError(f"{kind}/{record_id}")
                continue
            staged.append((kind,record_id,canonical))
        journal_records=journal/"records"
        for kind, record_id, canonical in staged:
            atomic_write(journal_records/f"{kind}__{record_id}.json",canonical)
        atomic_write(journal/"manifest.json",canonical_json_bytes([[kind,record_id] for kind,record_id in sorted(seen)]))
        return staged

    def _transaction_manifest_keys(self, project_id: str, tx: str) -> set[tuple[str,str]]:
        """Return the exact ``(kind, id)`` set a *committed* transaction's manifest claims.

        Read from the transaction's own recovery journal, which is never deleted -- the
        same durable record :meth:`recover` already relies on to finish or discard an
        interrupted commit. Absent for a transaction committed before this manifest tracking
        existed (or one that admitted no records at all), in which case the set is empty.
        """

        path=self._project(project_id)/"state"/"recovery"/tx/"manifest.json"
        if not path.exists(): return set()
        return set(self._read_manifest_entries(path, tx))

    def _promote_staged_records(self, project_id: str, journal: Path) -> None:
        records_dir=journal/"records"
        if not records_dir.exists(): return
        for path in sorted(records_dir.iterdir()):
            kind, _, record_id = path.stem.partition("__")
            canonical=path.read_bytes()
            target=self._record_path(project_id,kind,record_id)
            if target.exists():
                if target.read_bytes()!=canonical: raise CorruptStoreError(f"staged record diverges from committed: {kind}/{record_id}")
                continue
            atomic_write(target,canonical)

    def commit(self, project_id: str, expected_revision: int, expected_fingerprint: Mapping[str,str], next_state: Mapping[str,Any], transition: Mapping[str,Any], *, records: list[tuple[str,str,Mapping[str,Any]]]|None=None, fault: FaultInjector|None=None) -> dict[str,Any]:
        hit=lambda stage: fault(stage) if fault else None
        with self._lock(project_id):
            current=self.reconstruct(project_id); events=self._events(project_id); event=deepcopy(dict(transition)); tx=event["transaction_id"]
            prior=[item for item in events if item["transaction_id"]==tx]
            if prior:
                if canonical_json_bytes(prior[0])!=canonical_json_bytes(event): raise TransactionConflictError(tx)
                # R2-F3B: identical replay must also carry the identical record manifest --
                # exact (kind, id) membership, and exact canonical bytes for every member,
                # matched against what this transaction actually committed. A changed,
                # missing, additional or substituted record under the same transaction_id
                # is the same conflict a divergent event already raises on.
                supplied_keys: set[tuple[str,str]] = set()
                for kind, record_id, body in (records or []):
                    key=(kind,record_id)
                    if key in supplied_keys: raise RecordConflictError(f"{kind}/{record_id}")
                    supplied_keys.add(key)
                    committed=self.resolve_record(project_id,kind,record_id)
                    if committed is None or canonical_json_bytes(committed)!=canonical_json_bytes(body):
                        raise TransactionConflictError(tx)
                if supplied_keys!=self._transaction_manifest_keys(project_id,tx): raise TransactionConflictError(tx)
                atomic_write(self._current(project_id),canonical_json_bytes(prior[0]["after_state"])); return deepcopy(prior[0]["after_state"])
            if current["state_revision"]!=expected_revision or current["semantic_fingerprint"]!=dict(expected_fingerprint): raise StaleStateError("CAS mismatch")
            state=self._validate_state(project_id,next_state); self._verify_event(project_id,event,current)
            journal=self._project(project_id)/"state"/"recovery"/tx; journal.mkdir(parents=True,exist_ok=False)
            atomic_write(journal/"event.json",canonical_json_bytes(event)); hit(STAGES[0])
            atomic_write(journal/"state.json",canonical_json_bytes(state)); hit(STAGES[1])
            self._stage_records(project_id,journal,list(records or [])); hit(STAGES[2])
            atomic_write(journal/"COMMIT_INTENT",b"1"); hit(STAGES[3])
            self._append(project_id,event); hit(STAGES[4])
            self._promote_staged_records(project_id,journal); hit(STAGES[5])
            hit(STAGES[6])
            atomic_write(self._current(project_id),canonical_json_bytes(state)); hit(STAGES[7])
            hit(STAGES[8])
            atomic_write(journal/"COMMITTED",b"1")
            return deepcopy(state)

    def recover(self, project_id: str) -> dict[str,Any]:
        """Complete every interrupted transaction whose ``COMMIT_INTENT`` was durably
        written but whose ``COMMITTED`` marker was not.

        R10-F1: genesis itself can now carry a recovery journal (a genesis with ``records``
        interrupted before ``initialize`` finished). A crash before genesis's own
        ``COMMIT_INTENT`` was ever durably written leaves *no* completed transaction at all
        -- not corruption, simply a project that never finished initializing, and therefore
        safe to retry via :meth:`initialize` from scratch (its own ``AlreadyInitializedError``
        guard checks the lineage log, which such a crash never touched). :meth:`reconstruct`
        itself has no way to distinguish "nothing has ever committed" from real corruption,
        so this method checks that case first and raises the more precise
        :class:`~manosube_agent_civilization.store.errors.StateNotFoundError` instead of
        letting reconstruct's own generic error leak through.
        """

        with self._lock(project_id):
            recovery=self._project(project_id)/"state"/"recovery"; events=self._events(project_id); txids={e["transaction_id"] for e in events}
            if recovery.exists():
                for journal in sorted(recovery.iterdir()):
                    if not journal.is_dir() or not (journal/"COMMIT_INTENT").exists(): continue
                    event=json.loads((journal/"event.json").read_text(encoding="utf-8"))
                    if event["transaction_id"] not in txids: self._append(project_id,event); txids.add(event["transaction_id"])
                    self._promote_staged_records(project_id,journal)
                    atomic_write(journal/"COMMITTED",b"1")
            if not self._committed_events(project_id):
                raise StateNotFoundError(project_id)
            state=self.reconstruct(project_id); atomic_write(self._current(project_id),canonical_json_bytes(state)); return state
