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
    {"schema_version", "repository", "claims", "jst_day_counts", "active_lock"}
)
_CLAIM_KEYS: frozenset[str] = frozenset(
    {"work_unit_id", "status", "claimed_at", "jst_date", "dispatch_attempts", "result_digest"}
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
    if not isinstance(data["claims"], dict) or not isinstance(data["jst_day_counts"], dict):
        raise ReviewControlError("review control ledger claims/jst_day_counts must be objects")
    for identity_key, claim in data["claims"].items():
        if not isinstance(claim, dict) or set(claim) != _CLAIM_KEYS:
            raise ReviewControlError(f"claim {identity_key!r} is not the closed shape declared")
        if claim["status"] not in _VALID_CLAIM_STATUSES:
            raise ReviewControlError(
                f"claim {identity_key!r} carries an unknown status: {claim['status']!r}"
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
        }
        ledger["jst_day_counts"][jst_date] = day_count + 1
        ledger["active_lock"] = identity_key
        _write_ledger(ledger_path, ledger)
        return {"decision": REVIEW_CLAIM_ADMITTED, "reason_codes": [], "identity_key": identity_key}


def record_dispatch_attempt(
    ledger_path: Path, identity_key: str, *, repository: str, acknowledged: bool
) -> None:
    """Record that one dispatch attempt was made for an already-claimed *identity_key*.

    *acknowledged* is the one bit this module ever accepts about whether the external effect
    (:mod:`.review_adapter`'s own one launch call) returned a trustworthy acknowledgement.
    ``False`` records ``ACK_UNKNOWN`` -- never retried, by :func:`claim_review_launch`'s own
    ``DUPLICATE_LAUNCH_FOR_IDENTITY`` check, exactly as a confirmed dispatch never is.
    """

    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        claim["dispatch_attempts"] = claim["dispatch_attempts"] + 1
        claim["status"] = STATUS_DISPATCHED if acknowledged else STATUS_ACK_UNKNOWN
        _write_ledger(ledger_path, ledger)


def record_review_outcome(
    ledger_path: Path,
    identity_key: str,
    *,
    repository: str,
    status: str,
    result_digest: str | None = None,
) -> None:
    """Record the final outcome of a dispatched review and release the concurrency slot.

    The slot (``active_lock``) is released so a *different* identity may now claim it -- this
    exact identity never launches again regardless, since its claim (whatever its final
    status) persists in ``claims`` forever.
    """

    if status not in _OUTCOME_STATUSES:
        raise ReviewControlError(f"unrecognized review outcome status: {status!r}")
    with _locked(ledger_path):
        ledger = _read_ledger(ledger_path, repository=repository)
        claim = ledger["claims"].get(identity_key)
        if claim is None:
            raise ReviewControlError(f"no claim exists for identity_key {identity_key!r}")
        claim["status"] = status
        claim["result_digest"] = result_digest
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
