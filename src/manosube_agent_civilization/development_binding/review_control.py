"""Operational claim/budget coordination for one Bounded Review (Decision 0004, Issue #109).

:mod:`.review_selection` answers one offline question -- is this exact Bounded Review Grant
internally consistent and still live. It never tracks state across calls, and never answers
whether a concurrency slot or a daily reservation is actually available *right now*. This
module is that second, stateful owner: a small, durable, file-based ledger -- never the
canonical Store, never a second Kernel State owner (the handoff's own §4: "It remains
execution-control metadata, not a second canonical State owner") -- recording, atomically,
every claim this repository has ever admitted for a bounded review launch.

```text
review_selection  = is this request, by itself, a valid grant                (pure, offline)
review_control    = is a launch for this request's identity actually available right now
                                                                              (stateful ledger)
review_adapter    = the one external-effect call this delivery may ever make with both above
                                                                              (subprocess, I/O)
```

**The numeric ceiling itself is never read from a caller.** Every function here takes it as
an explicit *numeric_limits* argument and refuses outright (:class:`~.errors.
ReviewControlError`) unless it is exactly :data:`.policy.BOUNDED_REVIEW_NUMERIC_LIMITS` -- the
ratified constant, not a value a caller could narrow or (more dangerously) widen. This is a
caller-programming-error guard, not an ordinary claim refusal; an ordinary refusal (duplicate
identity, concurrency, daily ceiling) is this module's own ``REVIEW_CLAIM_REFUSED`` decision,
with reason codes, exactly as an inadmissible grant is never an exception in
:mod:`.review_selection`.

**Atomicity.** Every mutation acquires an exclusive ``flock`` on a dedicated lock file next to
the ledger, reads the current ledger inside that lock, computes the new state, and writes it
back via a temp-file-plus-``os.replace`` -- so a reader never observes a partially written
ledger, and two concurrent callers (including two processes started by a restarted controller)
never race past each other's own claim/reservation. The lock is released, and the file closed,
whether the body succeeds or raises.

**Restart safety.** A claim, once recorded, is never removed by this module -- a restart finds
exactly the ledger it left behind. ``record_dispatch_attempt(..., acknowledged=False)`` records
``ACK_UNKNOWN``, which is a terminal-enough status for :func:`claim_review_launch` to refuse any
further attempt at the identical identity: "Unknown post-send acknowledgement retains the claim
and blocks redispatch, including after controller restart" (handoff §4) is this module's own
default behaviour, not a special case it has to detect -- the *same* ``DUPLICATE_LAUNCH_FOR_
IDENTITY`` check that blocks a second attempt at a completed identity blocks a second attempt
at an unacknowledged one, because both leave a claim behind and this module never distinguishes
"why not" from "not again" for the one-launch-per-identity rule. The repository-wide
concurrency slot (``active_lock``) is the one thing an abandoned, never-resolved claim *does*
leave stuck -- deliberately: this module never auto-releases it, because inferring that a
silent controller crashed rather than merely being slow is exactly the kind of guess a kill
switch or a Human revocation should make instead, not a timeout this module invents for itself.

**F5 correction (PR #112 comment 6019024445).** The one-way ``CLAIMED`` -> (``DISPATCHED`` |
``ACK_UNKNOWN``) transition above is now enforced, not merely described: :func:`
record_dispatch_attempt` raises :class:`~.errors.ReviewControlError` outright on any second call
for an identity already past ``CLAIMED``, rather than silently recording a second dispatch.
:func:`record_review_outcome` requires an explicit, closed-set *resolution_kind* (:data:
`RESOLUTION_KIND_COLLECTED_RESULT` / :data:`RESOLUTION_KIND_CONFIRMED_CANCELLATION`) alongside
every ``status`` -- an arbitrary caller-asserted ``FAILED``/``COMPLETED`` string with no declared
evidence kind behind it is refused; this ledger never itself re-verifies that evidence is
genuine, only that *some* ratified kind always accompanies a resolution. And a claim whose one
permitted send was reserved but never attempted (e.g. an activation-gate refusal that lands
*after* the claim, until :mod:`.review_selection`'s own composed caller reorders this -- see
:func:`release_unsent_claim`) can now release the concurrency slot without ever being recorded
as a review "outcome" it never had.

This module performs no network call and launches no process -- see :mod:`.review_adapter` for
the one owner of those two things.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager, suppress
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .errors import ReviewControlError
from .policy import BOUNDED_REVIEW_NUMERIC_LIMITS
from .review_selection import SUPPORTED_ENVIRONMENT_FINGERPRINT

SCHEMA_VERSION = "0.1"

REVIEW_CLAIM_ADMITTED = "REVIEW_CLAIM_ADMITTED"
REVIEW_CLAIM_REFUSED = "REVIEW_CLAIM_REFUSED"

#: Terminal-enough to block a retry at the same identity, but distinguishable from a result a
#: caller might mistake for a real outcome.
STATUS_CLAIMED = "CLAIMED"
STATUS_DISPATCHED = "DISPATCHED"
STATUS_ACK_UNKNOWN = "ACK_UNKNOWN"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
_VALID_CLAIM_STATUSES: frozenset[str] = frozenset(
    {STATUS_CLAIMED, STATUS_DISPATCHED, STATUS_ACK_UNKNOWN, STATUS_COMPLETED, STATUS_FAILED}
)
#: Outcome statuses a caller may ever record through :func:`record_review_outcome` -- never
#: the dispatch-only statuses, which only :func:`record_dispatch_attempt` ever writes.
_OUTCOME_STATUSES: frozenset[str] = frozenset({STATUS_COMPLETED, STATUS_FAILED})

_LEDGER_KEYS: frozenset[str] = frozenset(
    {"schema_version", "repository", "claims", "jst_day_counts", "active_lock", "native_imports"}
)
#: The closed shape of one native-review dedup/correlation record (REUSE_NATIVE_ONLY
#: supplement, Issue #109 comment 6019865174) -- see :func:`record_native_review_import`.
_NATIVE_IMPORT_KEYS: frozenset[str] = frozenset({"identity_key", "classification", "imported_at"})
_CLAIM_KEYS: frozenset[str] = frozenset(
    {
        "work_unit_id",
        "status",
        "claimed_at",
        "jst_date",
        "dispatch_attempts",
        "result_digest",
        "pid",
        "process_identity",
        "resolution_kind",
    }
)

#: The only two outcome-resolution kinds this module will ever accept (F5 correction, PR #112
#: comment 6019024445): either a genuinely collected, structured result
#: (``COLLECTED_RESULT`` -- the composed route actually ran and read the review, however that
#: result itself classifies), or a confirmed, ownership-checked cancellation
#: (``CONFIRMED_CANCELLATION`` -- :func:`.review_adapter.cancel_review_task` returned
#: ``ownership_confirmed=True`` and the owned process group was actually terminated). A bare
#: caller assertion of ``FAILED``/``COMPLETED`` with neither is refused: "unknown provider/task
#: state cannot become resolved through an arbitrary FAILED/COMPLETED string."
RESOLUTION_KIND_COLLECTED_RESULT = "COLLECTED_RESULT"
RESOLUTION_KIND_CONFIRMED_CANCELLATION = "CONFIRMED_CANCELLATION"
_RATIFIED_RESOLUTION_KINDS: frozenset[str] = frozenset(
    {RESOLUTION_KIND_COLLECTED_RESULT, RESOLUTION_KIND_CONFIRMED_CANCELLATION}
)


def _require_ratified_numeric_limits(numeric_limits: Mapping[str, int]) -> None:
    """Refuse any *numeric_limits* that is not exactly the ratified ceiling.

    A caller-programming-error guard: the whole point of this module reading the ceiling as
    an explicit argument rather than importing the constant for itself (`claim_review_launch`
    still needs it threaded through from whatever already loaded the policy) is that an
    *unverified* argument could silently widen the ceiling a test or a caller supplies. This
    closes exactly that gap, the same discipline `.policy.load_policy` already applies to the
    JSON artifact itself.
    """

    if dict(numeric_limits) != BOUNDED_REVIEW_NUMERIC_LIMITS:
        raise ReviewControlError(
            "numeric_limits is not the ratified ceiling "
            f"(BOUNDED_REVIEW_NUMERIC_LIMITS): {dict(numeric_limits)!r}"
        )


def compute_identity_key(
    *,
    repository: str,
    pull_request: str,
    base_sha: str,
    head_sha: str,
    requirement_id: str,
    input_digest: str,
) -> str:
    """Return the one deterministic identity a (repo, PR, base, head, requirement, input-hash)
    tuple maps to -- the "one launch per identity" rule's own key, content-addressed so the
    identical tuple always produces the identical key and an attacker cannot forge collisions
    cheaper than finding a SHA-256 preimage."""

    payload = "|".join([repository, pull_request, base_sha, head_sha, requirement_id, input_digest])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def jst_date_for(utc_timestamp: str) -> str:
    """Return the JST (UTC+9) calendar date *utc_timestamp* falls on, as ``YYYY-MM-DD``.

    This module reads no clock of its own -- *utc_timestamp* is always the caller's own
    trusted-clock reading, the identical discipline :mod:`.review_selection` already follows
    for its own *now* parameter.
    """

    try:
        moment = datetime.fromisoformat(utc_timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReviewControlError(f"not a real ISO-8601 timestamp: {utc_timestamp!r}") from error
    jst = moment.astimezone(timezone(timedelta(hours=9)))
    return jst.date().isoformat()


def _default_ledger(repository: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "claims": {},
        "jst_day_counts": {},
        "active_lock": None,
        "native_imports": {},
    }


def _read_ledger(ledger_path: Path, *, repository: str) -> dict[str, Any]:
    """Return the ledger at *ledger_path*, or a fresh empty one if it does not yet exist.

    Called only from inside :func:`_locked`'s own exclusive lock -- never on its own, so a
    caller can never read a ledger that a concurrent writer is still in the middle of
    replacing.
    """

    if not ledger_path.is_file():
        return _default_ledger(repository)
    try:
        text = ledger_path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as error:
        raise ReviewControlError(f"review control ledger is unreadable: {error}") from error
    if not isinstance(data, dict) or set(data) != _LEDGER_KEYS:
        raise ReviewControlError("review control ledger is not the closed shape declared")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ReviewControlError(
            f"unsupported review control ledger schema: {data['schema_version']!r}"
        )
    if data["repository"] != repository:
        raise ReviewControlError(
            f"ledger belongs to a different repository: {data['repository']!r} != {repository!r}"
        )
    if (
        not isinstance(data["claims"], dict)
        or not isinstance(data["jst_day_counts"], dict)
        or not isinstance(data["native_imports"], dict)
    ):
        raise ReviewControlError(
            "review control ledger claims/jst_day_counts/native_imports must be objects"
        )
    for identity_key, claim in data["claims"].items():
        if not isinstance(claim, dict) or set(claim) != _CLAIM_KEYS:
            raise ReviewControlError(f"claim {identity_key!r} is not the closed shape declared")
        if claim["status"] not in _VALID_CLAIM_STATUSES:
            raise ReviewControlError(
                f"claim {identity_key!r} carries an unknown status: {claim['status']!r}"
            )
    for content_address, native_import in data["native_imports"].items():
        if not isinstance(native_import, dict) or set(native_import) != _NATIVE_IMPORT_KEYS:
            raise ReviewControlError(
                f"native import {content_address!r} is not the closed shape declared"
            )
    return data


def _write_ledger(ledger_path: Path, data: dict[str, Any]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, tmp_name = tempfile.mkstemp(
        dir=str(ledger_path.parent), prefix=".review-control-ledger-", suffix=".tmp"
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, ledger_path)
    except BaseException:
        with suppress(OSError):
            tmp_path.unlink()
        raise


@contextmanager
def _locked(ledger_path: Path):
    """Hold an exclusive OS-level lock on a dedicated lock file beside *ledger_path* for the
    duration of the ``with`` block -- the one section of this module ever allowed to read-then
    -write the ledger, so two processes (including one started by a restarted controller)
    never race each other's own claim or reservation."""

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = ledger_path.parent / f"{ledger_path.name}.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def claim_review_launch(
    ledger_path: Path,
    *,
    identity_key: str,
    work_unit_id: str,
    repository: str,
    now: str,
    numeric_limits: Mapping[str, int],
) -> dict[str, Any]:
    """Atomically admit or refuse one launch claim for *identity_key*.

    Admitted exactly when: no claim of any outcome already exists for this identity (one
    launch per identity, forever -- a failed or unacknowledged launch counts exactly as a
    completed one); no *other* identity currently holds the repository's one concurrency slot;
    and today's (JST) launch count is still below the ratified daily ceiling. All three checks,
    and the write that follows when they pass, happen inside the identical lock -- there is no
    window between "checked" and "claimed" another process could land in.
    """

    _require_ratified_numeric_limits(numeric_limits)
    jst_date = jst_date_for(now)
    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        reasons: list[str] = []
        if identity_key in ledger["claims"]:
            reasons.append("DUPLICATE_LAUNCH_FOR_IDENTITY")
        active_lock = ledger["active_lock"]
        if active_lock is not None and active_lock != identity_key:
            reasons.append("CONCURRENT_REVIEW_ACTIVE")
        day_count = ledger["jst_day_counts"].get(jst_date, 0)
        if day_count >= numeric_limits["max_launches_per_jst_day"]:
            reasons.append("DAILY_LAUNCH_CEILING_REACHED")
        if reasons:
            return {
                "decision": REVIEW_CLAIM_REFUSED,
                "reason_codes": sorted(set(reasons)),
                "identity_key": identity_key,
            }

        ledger["claims"][identity_key] = {
            "work_unit_id": work_unit_id,
            "status": STATUS_CLAIMED,
            "claimed_at": now,
            "jst_date": jst_date,
            "dispatch_attempts": 0,
            "result_digest": None,
            "pid": None,
            "process_identity": None,
            "resolution_kind": None,
        }
        ledger["jst_day_counts"][jst_date] = day_count + 1
        ledger["active_lock"] = identity_key
        _write_ledger(ledger_path, ledger)
        return {"decision": REVIEW_CLAIM_ADMITTED, "reason_codes": [], "identity_key": identity_key}


def record_dispatch_attempt(
    ledger_path: Path,
    identity_key: str,
    *,
    repository: str,
    acknowledged: bool,
    pid: int | None = None,
    process_identity: str | None = None,
) -> None:
    """Record the *one* dispatch attempt ever permitted for an already-claimed *identity_key*.

    F5 correction (PR #112 comment 6019024445): this is a one-way ``CLAIMED`` ->
    (``DISPATCHED`` | ``ACK_UNKNOWN``) transition -- raises :class:`~.errors.
    ReviewControlError` outright if the claim is not currently ``CLAIMED``, so a second call
    for the identical identity (whatever its current status, ``ACK_UNKNOWN`` included) is
    refused rather than silently re-recording a "second dispatch" the adopted limits forbid.

    SR2-F4 correction (PR #112 comment 6021757577): the composed route now calls this function
    with *acknowledged=False* (and *pid*/*process_identity* both ``None``) *before* the
    external effect begins -- immediately after every precondition that can confirm "nothing
    will be sent" has already been checked (:func:`.review_adapter.
    validate_review_launch_preconditions`), and *before* :func:`.review_adapter.
    spawn_review_process` is ever called. This durably marks "an attempt is about to be made"
    before the one irreducible window (the real ``Popen`` call itself) a crash could land in,
    closing the exact gap the finding reproduced: a crash during the launch's own potentially
    long collection wait can no longer be mistaken, on restart, for "this was never sent" --
    the claim is already past ``CLAIMED`` the instant it could be confirmed a send was even
    attempted. See :func:`confirm_dispatch_sent` for the one further write that attaches the
    real pid/process identity once :func:`.review_adapter.spawn_review_process` returns, and
    :func:`release_unsent_claim` for the only path that may still release a claim that never
    reached this function at all.

    *acknowledged* is the one bit this module ever accepts about whether the external effect
    (:mod:`.review_adapter`'s own one launch call) returned a trustworthy acknowledgement.
    ``False`` records ``ACK_UNKNOWN`` -- never retried, by :func:`claim_review_launch`'s own
    ``DUPLICATE_LAUNCH_FOR_IDENTITY`` check, exactly as a confirmed dispatch never is.

    *pid*/*process_identity* (:func:`.review_adapter.process_identity_token`), when given,
    are persisted on the claim so a later call -- including one from a restarted controller
    process that never itself called :func:`.review_adapter.launch_review_process` -- can
    still recover genuine ownership proof before attempting
    :func:`.review_adapter.cancel_review_task`.
    """

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        if claim["status"] != STATUS_CLAIMED:
            raise ReviewControlError(
                f"identity_key {identity_key!r} has already been dispatched once "
                f"(current status {claim['status']!r}); a second dispatch of an existing "
                "claim is refused, including from an ACK_UNKNOWN state"
            )
        claim["dispatch_attempts"] = claim["dispatch_attempts"] + 1
        claim["status"] = STATUS_DISPATCHED if acknowledged else STATUS_ACK_UNKNOWN
        claim["pid"] = pid
        claim["process_identity"] = process_identity
        _write_ledger(ledger_path, ledger)


def confirm_dispatch_sent(
    ledger_path: Path, identity_key: str, *, repository: str, pid: int, process_identity: str
) -> None:
    """Attach the real pid/process identity to a claim already marked ``ACK_UNKNOWN`` by
    :func:`record_dispatch_attempt`, upgrading it to ``DISPATCHED``.

    SR2-F4 correction (PR #112 comment 6021757577): the composed route calls this the instant
    :func:`.review_adapter.spawn_review_process` returns -- a real, already-started process,
    with a real pid -- never only after the whole, potentially long, collection wait finishes.
    A controller that crashes after this call returns, but before collection ever completes,
    leaves a ledger a restarted controller can still recover genuine ownership proof from (for
    :func:`.review_adapter.cancel_review_task`) without ever risking a second send: this
    identity's claim is already ``DISPATCHED``, and :func:`claim_review_launch`'s own
    ``DUPLICATE_LAUNCH_FOR_IDENTITY`` check refuses any further attempt at it, forever.
    """

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        if claim["status"] != STATUS_ACK_UNKNOWN:
            raise ReviewControlError(
                f"identity_key {identity_key!r} is {claim['status']!r}, not ACK_UNKNOWN -- "
                "only a claim already marked as an attempted-but-unconfirmed send may be "
                "confirmed this way"
            )
        claim["status"] = STATUS_DISPATCHED
        claim["pid"] = pid
        claim["process_identity"] = process_identity
        _write_ledger(ledger_path, ledger)


def record_review_outcome(
    ledger_path: Path,
    identity_key: str,
    *,
    repository: str,
    status: str,
    resolution_kind: str,
    result_bytes: bytes | None = None,
) -> None:
    """Record the final outcome of a dispatched review and release the concurrency slot.

    F5 correction (PR #112 comment 6019024445): *resolution_kind* must be one of
    :data:`_RATIFIED_RESOLUTION_KINDS` -- an arbitrary caller-asserted ``FAILED``/``COMPLETED``
    string, with no declared evidence kind behind it, is refused outright. This ledger never
    itself re-verifies that the claimed evidence is genuine (that is the composed route's own
    responsibility: it may claim ``COLLECTED_RESULT`` only once it has actually collected a
    structured result, and ``CONFIRMED_CANCELLATION`` only once
    :func:`.review_adapter.cancel_review_task` returned ``ownership_confirmed=True``); this
    function's own contract is that *some* declared, closed-set evidence kind always
    accompanies a resolution -- "unknown provider/task state cannot become resolved through
    an arbitrary FAILED/COMPLETED string".

    SR2-F4 correction (PR #112 comment 6021757577): this ledger now additionally requires that
    a result digest be present whenever *resolution_kind* is :data:
    `RESOLUTION_KIND_COLLECTED_RESULT`, and absent whenever it is :data:
    `RESOLUTION_KIND_CONFIRMED_CANCELLATION`.

    SR3-F4 correction (PR #112 comment 6030487245): before this correction, the parameter here
    was a caller-asserted ``result_digest: str`` -- any well-formed 64-character lowercase hex
    string satisfied the shape check above, including one with zero actual collected bytes
    behind it at all (reproduced: ``result_digest="0" * 64`` for a status this ledger had never
    itself seen any bytes for). A digest *shape* check alone was never evidence of digest
    *correlation* to anything real. Fixed: this function no longer accepts a digest at all --
    it accepts *result_bytes*, the real collected result itself, and computes the one digest
    the ledger ever records from those bytes directly. A caller can no longer assert an
    arbitrary digest with nothing behind it: the recorded digest is always genuinely the
    SHA-256 of whatever bytes this call was actually given, even when that is zero bytes
    (``result_bytes=b""`` digests to a real, specific value, never ``"0" * 64``). This is still
    never a claim that *those* bytes are themselves the real launch's own uncorrupted output --
    that remains the composed route's own responsibility, exactly as before -- only that the
    digest this ledger stores is never disconnected from any bytes whatsoever.

    Only a claim currently ``DISPATCHED`` or ``ACK_UNKNOWN`` may be resolved this way -- a
    claim still ``CLAIMED`` (the one send was never even attempted, e.g. because the
    activation gate refused before any claim was reserved) has nothing here to resolve; see
    the module docstring's own ordering note.

    The slot (``active_lock``) is released so a *different* identity may now claim it -- this
    exact identity never launches again regardless, since its claim (whatever its final
    status) persists in ``claims`` forever.
    """

    if status not in _OUTCOME_STATUSES:
        raise ReviewControlError(f"unrecognized review outcome status: {status!r}")
    if resolution_kind not in _RATIFIED_RESOLUTION_KINDS:
        raise ReviewControlError(
            f"resolution_kind {resolution_kind!r} is not a ratified evidence kind "
            f"{sorted(_RATIFIED_RESOLUTION_KINDS)}; an outcome may never be recorded without "
            "declaring genuine correlated evidence"
        )
    if resolution_kind == RESOLUTION_KIND_COLLECTED_RESULT and not isinstance(result_bytes, bytes):
        raise ReviewControlError(
            "resolution_kind is COLLECTED_RESULT but result_bytes is not real bytes: "
            f"{type(result_bytes)!r} -- a collected result always has something to digest, "
            "and this ledger computes that digest itself rather than trusting a caller's own"
        )
    if resolution_kind == RESOLUTION_KIND_CONFIRMED_CANCELLATION and result_bytes is not None:
        raise ReviewControlError(
            "resolution_kind is CONFIRMED_CANCELLATION but result_bytes is not None -- a "
            "cancellation never collects a result to digest"
        )
    result_digest = hashlib.sha256(result_bytes).hexdigest() if result_bytes is not None else None
    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        if claim["status"] not in (STATUS_DISPATCHED, STATUS_ACK_UNKNOWN):
            raise ReviewControlError(
                f"identity_key {identity_key!r} is {claim['status']!r}, not DISPATCHED or "
                "ACK_UNKNOWN -- an outcome can only resolve a claim whose one dispatch "
                "attempt was actually made"
            )
        claim["status"] = status
        claim["result_digest"] = result_digest
        claim["resolution_kind"] = resolution_kind
        if ledger["active_lock"] == identity_key:
            ledger["active_lock"] = None
        _write_ledger(ledger_path, ledger)


#: The one terminal status a claim reaches when its one permitted send was reserved but never
#: actually attempted (e.g. the external-effect call itself raised before ever starting a
#: process). Distinct from every outcome status: it was never dispatched, so it is never a
#: review "outcome" -- see :func:`release_unsent_claim`.
STATUS_ABANDONED_UNSENT = "ABANDONED_UNSENT"
_VALID_CLAIM_STATUSES = _VALID_CLAIM_STATUSES | frozenset({STATUS_ABANDONED_UNSENT})


def release_unsent_claim(ledger_path: Path, identity_key: str, *, repository: str) -> None:
    """Release the concurrency slot for a claim whose one permitted send was reserved but
    never actually attempted, without ever recording it as a review outcome.

    Only a claim still ``CLAIMED`` may be released this way -- once
    :func:`record_dispatch_attempt` has run even once, the claim is no longer "unsent" and
    only :func:`record_review_outcome` may resolve it. The identity itself is still never
    reusable (the claim persists, now ``ABANDONED_UNSENT``, in ``claims`` forever) -- only the
    repository's one concurrency slot is freed, so one identity's own abandoned, never-sent
    reservation cannot indefinitely block every other identity's own claim.
    """

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        if claim["status"] != STATUS_CLAIMED:
            raise ReviewControlError(
                f"identity_key {identity_key!r} is {claim['status']!r}, not CLAIMED -- only "
                "a claim whose one send was never attempted may be released unsent"
            )
        claim["status"] = STATUS_ABANDONED_UNSENT
        if ledger["active_lock"] == identity_key:
            ledger["active_lock"] = None
        _write_ledger(ledger_path, ledger)


def read_claim(ledger_path: Path, identity_key: str, *, repository: str) -> dict[str, Any] | None:
    """Return a snapshot of the current claim for *identity_key*, or ``None`` if it was never
    claimed. Read-only, but still taken under the same lock as every writer, so a caller never
    observes a half-written claim."""

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        return dict(claim) if claim is not None else None


# --------------------------------------------------------------------------- #
# The activation / spending gate (handoff §6). Disabled by default
# (`.policy.BOUNDED_REVIEW_ACTIVATION_DEFAULT`); nothing in this delivery ever supplies a path
# that sets ``activation_enabled`` to ``True`` in real evidence -- this function itself never
# reads a file, a process, or an environment variable to decide that for itself. A caller
# assembles *evidence* from whatever it has genuinely confirmed; this function's only job is
# to refuse unless literally every one of the required fields says so explicitly.
# --------------------------------------------------------------------------- #

ACTIVATION_GATE_ACTIVATED = "ACTIVATION_GATE_ACTIVATED"
ACTIVATION_GATE_NOT_ACTIVATED = "ACTIVATION_GATE_NOT_ACTIVATED"

#: Every field :func:`evaluate_activation_gate` requires, and no other -- an evidence mapping
#: that is missing even one, or names a field this gate does not recognise, is refused before
#: any individual value is even inspected. There is no default for an absent field: absence is
#: itself ``ACTIVATION_EVIDENCE_OMITS_REQUIRED_KEYS``, never treated as "assume not yet, keep
#: going" for the other fields.
ACTIVATION_EVIDENCE_KEYS: frozenset[str] = frozenset(
    {
        "auth_confirmed",
        "cli_version",
        "model",
        "allowance_confirmed_adequate",
        "auto_recharge_verified_disabled",
        "native_github_dedup_disposition",
        "live_bounded_review_grant_admitted",
        "activation_enabled",
    }
)

#: The only two values ``native_github_dedup_disposition`` may ever hold to pass -- an
#: explicit confirmation that native GitHub's own automatic review setting is either disabled
#: or does not apply to this repository, never an absent/unknown value treated as either.
_ACCEPTABLE_NATIVE_DEDUP_DISPOSITIONS: frozenset[str] = frozenset({"DISABLED", "NOT_APPLICABLE"})


def evaluate_activation_gate(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return ``ACTIVATION_GATE_ACTIVATED`` only when *evidence* affirmatively confirms every
    required precondition; ``ACTIVATION_GATE_NOT_ACTIVATED`` otherwise, with the specific
    reason codes. Never raises: an unreadable *evidence* is itself a refusal.
    """

    if not isinstance(evidence, Mapping):
        unreadable_reasons: list[str] = []
        unreadable_reasons.append("ACTIVATION_EVIDENCE_UNREADABLE")
        return {"decision": ACTIVATION_GATE_NOT_ACTIVATED, "reason_codes": unreadable_reasons}
    unknown = set(evidence) - ACTIVATION_EVIDENCE_KEYS
    missing = ACTIVATION_EVIDENCE_KEYS - set(evidence)
    if unknown or missing:
        reasons = []
        if unknown:
            reasons.append("ACTIVATION_EVIDENCE_CARRIES_UNKNOWN_KEYS")
        if missing:
            reasons.append("ACTIVATION_EVIDENCE_OMITS_REQUIRED_KEYS")
        return {"decision": ACTIVATION_GATE_NOT_ACTIVATED, "reason_codes": reasons}

    reasons = []
    if evidence["auth_confirmed"] is not True:
        reasons.append("AUTH_NOT_CONFIRMED")
    if evidence["cli_version"] != SUPPORTED_ENVIRONMENT_FINGERPRINT["cli_version"]:
        reasons.append("CLI_VERSION_UNSUPPORTED")
    if evidence["model"] != SUPPORTED_ENVIRONMENT_FINGERPRINT["model"]:
        reasons.append("MODEL_UNSUPPORTED")
    if evidence["allowance_confirmed_adequate"] is not True:
        reasons.append("ALLOWANCE_NOT_CONFIRMED_ADEQUATE")
    if evidence["auto_recharge_verified_disabled"] is not True:
        reasons.append("AUTO_RECHARGE_NOT_VERIFIED_DISABLED")
    if evidence["native_github_dedup_disposition"] not in _ACCEPTABLE_NATIVE_DEDUP_DISPOSITIONS:
        reasons.append("NATIVE_GITHUB_DEDUP_DISPOSITION_UNRESOLVED")
    if evidence["live_bounded_review_grant_admitted"] is not True:
        reasons.append("LIVE_BOUNDED_REVIEW_GRANT_NOT_ADMITTED")
    if evidence["activation_enabled"] is not True:
        reasons.append("ACTIVATION_NOT_ENABLED")

    decision = ACTIVATION_GATE_NOT_ACTIVATED if reasons else ACTIVATION_GATE_ACTIVATED
    return {"decision": decision, "reason_codes": sorted(set(reasons))}


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622):
# dedup/correlation for an already-fetched native review, over this module's own existing
# ledger file -- never a parallel owner, never a concurrency-slot or daily-budget reservation.
# --------------------------------------------------------------------------- #


def native_review_content_address(native_evidence: Mapping[str, Any], *, identity_key: str) -> str:
    """Return the one deterministic content address a native review's own immutable identity,
    *for exactly this request*, maps to. Two reads of the identical native review -- fetched
    twice, by two different callers, at two different times, *for the identical request* --
    always content-address identically, so :func:`record_native_review_import` can deduplicate
    a re-fetch rather than importing it a second time.

    SR2-F3 correction (PR #112 comment 6021757577): the pre-correction address hashed only
    ``provider``/``repository``/``review_id``/``reviewed_commit_sha`` -- reproduced gap: a
    native review whose ``review_state`` changed on GitHub (e.g. ``APPROVED`` ->
    ``CHANGES_REQUESTED``, with new findings attached) on the *identical* ``review_id`` still
    content-addressed identically to its earlier, now-superseded fetch, so
    :func:`record_native_review_import`'s own dedup returned the stale cached classification
    instead of ever re-processing the changed evidence. ``review_state`` and a digest of
    ``findings`` are now included, so a real state/finding transition on the same review_id
    always content-addresses as a genuinely new record -- revision-aware, not identity-only,
    deduplication.

    SR3-F3 correction (PR #112 comment 6030487245): the address still omitted *which request*
    the native evidence was being imported for at all -- reproduced gap: a second grant naming
    a genuinely different ``requirement_id`` (its own distinct work unit, distinct
    ``input_digest``), reusing the identical already-fetched native evidence, still
    content-addressed identically to the first import and so returned the first import's own
    cached classification as if it were this different request's own -- a dedup collision
    across requests, never a real re-import for the new request's own identity. *identity_key*
    -- the caller's own :func:`compute_identity_key` over the *requesting* grant (never derived
    from *native_evidence* itself) -- is now folded into the address, so two genuinely distinct
    requests reusing byte-identical native evidence always content-address distinctly, and
    dedup only ever fires for a second import of the identical evidence *for the identical
    request*.
    """

    findings_digest = hashlib.sha256(
        json.dumps(native_evidence.get("findings") or [], sort_keys=True, default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    payload = "|".join(
        [
            str(native_evidence["provider"]),
            str(native_evidence["repository"]),
            str(native_evidence["review_id"]),
            str(native_evidence.get("reviewed_commit_sha") or ""),
            str(native_evidence.get("inspected_base_sha") or ""),
            str(native_evidence.get("review_state") or ""),
            findings_digest,
            str(identity_key),
        ]
    )
    return "NATIVE-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_native_review_import(
    ledger_path: Path, content_address: str, *, repository: str
) -> dict[str, Any] | None:
    """Return the already-recorded native-import record for *content_address*, or ``None`` if
    none exists yet -- read-only, no lock held beyond the one ledger read itself."""

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        record = ledger["native_imports"].get(content_address)
    return None if record is None else dict(record)


def record_native_review_import(
    ledger_path: Path,
    content_address: str,
    *,
    repository: str,
    identity_key: str,
    classification: str,
    now: str,
) -> dict[str, Any]:
    """Idempotently record that native review *content_address* has been imported as
    *classification* for *identity_key* -- or, if it was already recorded, return the existing
    record unchanged rather than importing it a second time (the supplement's own dedup
    requirement). This never touches ``claims``, ``jst_day_counts``, or ``active_lock`` --
    native reuse reserves no local concurrency slot and spends no local daily launch budget;
    :data:`.review_control.evaluate_activation_gate`'s own existing ``native_github_dedup_
    disposition`` field (already required, pinned to ``DISABLED``/``NOT_APPLICABLE``, for any
    *local* dispatch this delivery ever performs) is this module's existing, separate hook for
    a caller to declare that native coverage was checked before a local launch is even
    attempted -- this function answers "was this exact native review already imported", that
    local gate answers "has a caller checked native coverage at all"; neither re-derives the
    other.
    """

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        existing = ledger["native_imports"].get(content_address)
        if existing is not None:
            return dict(existing)
        record = {
            "identity_key": identity_key,
            "classification": classification,
            "imported_at": now,
        }
        ledger["native_imports"][content_address] = record
        _write_ledger(ledger_path, ledger)
        return dict(record)


#: Every reason code either function above can emit, declared explicitly (the identical
#: discipline every other evaluator module in this package follows).
EMITTED_REASON_CODES: frozenset[str] = frozenset(
    {
        "DUPLICATE_LAUNCH_FOR_IDENTITY",
        "CONCURRENT_REVIEW_ACTIVE",
        "DAILY_LAUNCH_CEILING_REACHED",
        "ACTIVATION_EVIDENCE_UNREADABLE",
        "ACTIVATION_EVIDENCE_CARRIES_UNKNOWN_KEYS",
        "ACTIVATION_EVIDENCE_OMITS_REQUIRED_KEYS",
        "AUTH_NOT_CONFIRMED",
        "CLI_VERSION_UNSUPPORTED",
        "MODEL_UNSUPPORTED",
        "ALLOWANCE_NOT_CONFIRMED_ADEQUATE",
        "AUTO_RECHARGE_NOT_VERIFIED_DISABLED",
        "NATIVE_GITHUB_DEDUP_DISPOSITION_UNRESOLVED",
        "LIVE_BOUNDED_REVIEW_GRANT_NOT_ADMITTED",
        "ACTIVATION_NOT_ENABLED",
    }
)
