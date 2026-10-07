"""The one script Decision 0004 (Issue #109) authorizes to invoke the bounded-technical-review
owners -- :mod:`manosube_agent_civilization.development_binding.review_selection`,
``.review_control``, and ``.review_adapter`` -- and the only place this delivery composes them
into a sequence. It introduces no second admission route: every decision below is answered by
calling one of those three owners, never by re-deriving their logic here.

```text
validate-grant    -> review_selection.evaluate_review_selection            (pure, offline)
claim             -> review_control.claim_review_launch                   (durable ledger)
record-dispatch   -> review_control.record_dispatch_attempt               (durable ledger)
record-outcome    -> compose_bounded_technical_review_outcome_recording   (claim-bound, SR4-F4)
activation-gate   -> review_control.evaluate_activation_gate              (pure, offline)
cancel            -> compose_bounded_technical_review_cancellation        (claim-bound)
dispatch          -> validate-grant, then the activation gate -- and stops there, zero claims
```

**``dispatch`` never launches a real review in this delivery.** Runtime starts disabled
(``ACTIVATION_DEFAULT=false``, `.policy.BOUNDED_REVIEW_ACTIVATION_DEFAULT`), and this script
hardcodes ``activation_enabled=False`` on every activation-gate evidence it assembles -- there
is no flag, environment variable, or configuration file this script reads that can set it to
``True``. A caller that wants a real launch must build one outside this script entirely, after
an authenticated activation grant this delivery does not create. This is intentional, not a
missing feature: ``REAL_CODEX_MODEL_REQUEST_ALLOWED=false`` for this whole delivery, and this
script's own ``dispatch`` subcommand is where that boundary is enforced, not merely stated.

This script performs no automated-review request on its own initiative -- every subcommand
reads an explicit, caller-supplied grant/ledger/evidence file or argument and reports a
decision; none of them discover a PR, a repository, or a provider account on their own.

**F5 correction (PR #112 comment 6019024445).** ``dispatch`` above no longer claims at all:
the activation gate is evaluated *before* any claim would be attempted, not after, so an
ineligible or disabled request (every CLI invocation, in this delivery) never reserves the
repository's one concurrency slot or a day's own launch budget purely to then discover it was
always going to be refused. The full claim/dispatch sequence moved out of this subcommand
entirely, into :func:`compose_bounded_technical_review_dispatch`.

**F1/F2 correction (PR #112 comment 6019024445).** :func:`compose_bounded_technical_review_dispatch`
is the one composed route this delivery's own handoff requires but this CLI's own ``dispatch``
subcommand never reaches: validate-grant, the activation gate, a real authenticated-admission
check (:func:`~manosube_agent_civilization.development_binding.review_selection.
authenticate_bounded_review_grant`, reusing the existing Boot/Authority/Store owners), the
claim, input staging with a genuine digest verification, the one real :mod:`.review_adapter`
launch, a real structured-signal result classifier (:func:`classify_review_result` -- never a
bare ``review_status`` string match), and the ledger outcome. It is a plain library function,
not a CLI subcommand: nothing in this script's own command-line surface can reach it, so the
``REAL_CODEX_MODEL_REQUEST_ALLOWED=false`` boundary above still holds for every way this script
is actually invoked; this delivery's own tests call it directly.

**REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622).**
:func:`compose_bounded_technical_review_native_reuse_dispatch` is a second composed route,
distinct from :func:`compose_bounded_technical_review_dispatch` above: it imports one
already-fetched native GitHub review's own evidence as this delivery's Evidence-layer
classification, reusing the identical three owners (``review_adapter`` for the trusted,
read-only evidence shape check; ``review_selection`` for grant admission and native-relevance;
``review_control`` for the dedup/correlation ledger) rather than a parallel admission route --
and never claims a local concurrency slot, spends a local daily launch budget, or calls
:mod:`.review_adapter`'s own ``launch_review_process`` at all. Like the local dispatch route,
it is a plain library function this script's own command-line surface never reaches.

**PR #112 Structural Review Round 2 corrections (comment 6021757577), adopted
``ADOPT_I109_PR112_SR2_F1_F6_E1_20261007``.**

- *SR2-F1* (exact-envelope authority + live re-check): :func:`_recheck_live_authorization`
  re-runs validate-grant/activation-gate/authenticate fresh, at two further checkpoints inside
  :func:`compose_bounded_technical_review_dispatch` -- immediately before the one external
  effect is ever sent (while the claim is still releasably ``CLAIMED``), and again immediately
  before its real, already-collected result is ever accepted into the ledger. A caller may wire
  in a genuinely live trusted clock/kill-switch/grant reader via *now_provider*/
  *activation_evidence_provider*/*grant_provider*; see that function's own docstring for why
  *permitted_boundary* itself is never widened to carry the full envelope (doing so would refuse
  every real, already-signed grant, not strengthen this check).
- *SR2-F2* (condition/cap-based classification + real Evidence handoff): :func:`
  classify_review_result` now also refuses a truncated capture, an over-scope inspected path,
  and a ``COMPLETED`` result whose own findings carry a blocking severity;
  :func:`measure_inspection_input_bytes` enforces :data:`MAX_INSPECTION_INPUT_BYTES` on the
  staged input before any process is ever started; the composed route's own
  *evidence_handoff* parameter, when given, performs the real
  :mod:`~manosube_agent_civilization.independent_verification` handoff itself (see
  :func:`_hand_off_to_evidence`) rather than leaving every caller to hand-assemble it.
- *SR2-F3* (trusted native-reuse transport, inspected-base separation, revision-aware dedup):
  :data:`~manosube_agent_civilization.development_binding.review_adapter.
  NATIVE_REVIEW_EVIDENCE_SCHEMA_KEYS` now also requires ``inspected_base_sha``, a genuinely
  separate fact from ``reviewed_commit_sha`` that :func:`~manosube_agent_civilization.
  development_binding.review_selection.evaluate_native_review_relevance` now also checks
  against the grant's own ``authorized_base_sha``; :func:`~manosube_agent_civilization.
  development_binding.review_control.native_review_content_address` now folds in
  ``review_state`` and a digest of ``findings``, so a review that transitions state (e.g.
  ``APPROVED`` -> ``CHANGES_REQUESTED``) on the identical ``review_id`` content-addresses as a
  genuinely new record rather than returning a stale cached classification. This module's own
  "no network call, ever" design boundary (this file's own module docstring, and `.
  review_adapter`'s) is unchanged -- *authenticated source* in the cryptographic sense is out
  of scope for a route that by design never fetches anything itself; what changed is that two
  real, previously-unchecked facts (the inspected base, and a state/finding revision) are now
  checked and correlated instead of silently assumed.
- *SR2-F4* (atomic pre-send attempt durability + evidence-correlated terminal release): see
  :mod:`~manosube_agent_civilization.development_binding.review_adapter`'s own
  ``validate_review_launch_preconditions``/``spawn_review_process``/
  ``collect_review_process_result`` split and :mod:`~manosube_agent_civilization.
  development_binding.review_control`'s own ``confirm_dispatch_sent``/``record_review_outcome``
  digest requirement; :func:`compose_bounded_technical_review_dispatch` now calls
  ``record_dispatch_attempt(acknowledged=False)`` immediately after every pre-launch refusal
  condition has already passed, and before ``spawn_review_process`` is ever called.
- *SR2-F5* (claim-bound cancellation): :func:`compose_bounded_technical_review_cancellation`
  is the one canonical cancellation route -- it is the generic ``cancel_review_task`` adapter
  primitive, bound to a real ledger claim's own recorded pid/process identity, that this CLI's
  own ``cancel`` subcommand (a deliberately generic, directly-testable fake-process primitive;
  never itself the canonical route, identical in spirit to how ``dispatch`` never reaches
  :func:`compose_bounded_technical_review_dispatch`) does not call.
- *SR2-F6* (enforce real isolation or refuse): see :mod:`~manosube_agent_civilization.
  development_binding.review_adapter`'s own ``check_isolation_capability``/
  ``build_isolated_argv`` corrections (self-bind-mount read-only remount, capability-bounding-
  set drop, network namespace isolation) and ``validate_review_launch_preconditions``'s own
  refusal when ``require_isolation`` is true but ``mask_paths`` is empty.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any, TextIO

from manosube_agent_civilization.development_binding.errors import ReviewAdapterError
from manosube_agent_civilization.development_binding.policy import BOUNDED_REVIEW_NUMERIC_LIMITS
from manosube_agent_civilization.development_binding.review_adapter import (
    CancellationOutcome,
    LiveReviewStateTransport,
    NativeReviewTransport,
    build_codex_review_argv,
    build_subprocess_environment,
    cancel_review_task,
    cleanup_inspection_workspace,
    collect_review_process_result,
    fetch_trusted_live_review_state,
    fetch_trusted_native_review_evidence,
    parse_structured_review_output,
    prepare_inspection_workspace,
    process_identity_token,
    spawn_review_process,
    validate_review_launch_preconditions,
)
from manosube_agent_civilization.development_binding.review_control import (
    RESOLUTION_KIND_COLLECTED_RESULT,
    RESOLUTION_KIND_CONFIRMED_CANCELLATION,
    REVIEW_CLAIM_ADMITTED,
    STATUS_ACK_UNKNOWN,
    STATUS_COMPLETED,
    STATUS_DISPATCHED,
    STATUS_FAILED,
    claim_review_launch,
    compute_identity_key,
    confirm_dispatch_sent,
    evaluate_activation_gate,
    native_review_content_address,
    read_claim,
    read_native_review_import,
    record_dispatch_attempt,
    record_native_review_import,
    record_review_outcome,
    release_unsent_claim,
)
from manosube_agent_civilization.development_binding.review_selection import (
    NATIVE_REVIEW_RELEVANT,
    REVIEW_SELECTION_ADMITTED,
    authenticate_bounded_review_grant,
    canonical_list_digest,
    compute_launch_envelope_digest,
    evaluate_native_review_relevance,
    evaluate_review_selection,
)

#: SR2-F2 correction: the closed set of per-finding severities that keep a ``COMPLETED``
#: native or local review result from ever being reported :data:`VERIFICATION_VERIFIED` --
#: reproduced gap: a result carrying a P1/blocking finding, with ``review_status ==
#: "COMPLETED"``, was previously reported VERIFIED purely because the classifier never read
#: ``findings`` at all once ``review_status`` itself looked clean. SR3-F2 correction (PR #112
#: comment 6030487245): ``P0`` added -- the prior set's own gap (``P1``/``BLOCKING``/
#: ``CRITICAL`` only) let a reproduced ``P0`` finding through as ``VERIFIED``. Severity is now
#: only a secondary signal regardless -- :func:`classify_review_result`'s own primary check is
#: each permitted check's own declared ``status``, never a severity scan over whatever
#: findings happen to be present.
BLOCKING_FINDING_SEVERITIES = frozenset({"P0", "P1", "BLOCKING", "CRITICAL"})

SCHEMA_VERSION = "0.1"

#: The one Evidence-layer classification vocabulary :func:`classify_review_result` returns --
#: deliberately the identical four names :mod:`manosube_agent_civilization.
#: independent_verification.types`'s own ``VERIFICATION_STATUSES`` uses, duplicated by value
#: rather than imported (the identical cross-vertical-import-avoidance convention :mod:`.
#: development_binding.review_selection`'s own module docstring already states): a Bounded
#: Review's result is reported in the same vocabulary the Evidence layer it eventually hands
#: off to already expects, without this module importing that vertical merely to name four
#: strings.
VERIFICATION_VERIFIED = "VERIFIED"
VERIFICATION_FAILED = "FAILED"
VERIFICATION_INSUFFICIENT = "INSUFFICIENT"
VERIFICATION_UNAVAILABLE = "UNAVAILABLE"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _emit(stream: TextIO, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, indent=2, sort_keys=True))
    stream.write("\n")


def digest_inspection_input(workspace: Path) -> str:
    """Return the Bounded Review Grant's own canonical ``input_digest`` for the exact files
    *workspace* holds -- a SHA-256 over every file's own repository-relative path and bytes,
    sorted by path so the result never depends on filesystem iteration order.

    This is the one definition :func:`compose_bounded_technical_review_dispatch` uses to prove
    the staged inspection input is genuinely the bundle a grant's own *input_digest* names --
    never merely that *a* workspace was prepared, but that *this exact* one was. Whoever issues
    a grant must compute *input_digest* with this identical function before declaring it.
    """

    hasher = hashlib.sha256()
    relative_paths = sorted(
        str(path.relative_to(workspace)) for path in workspace.rglob("*") if path.is_file()
    )
    for relative_path in relative_paths:
        hasher.update(relative_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update((workspace / relative_path).read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _default_live_now() -> str:
    """The real current wall-clock time, in the identical ``YYYY-MM-DDTHH:MM:SSZ`` form every
    grant's own ``not_before``/``not_after`` window already uses -- :func:
    `compose_bounded_technical_review_dispatch`'s own default *now_provider*, read fresh every
    time it is called (SR3-F1, PR #112 comment 6030487245), never an echo of the one literal
    ``now`` string a caller supplied once at the top of the call.
    """

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_review_result(
    launch_result: Any,
    *,
    permitted_paths: Sequence[str],
    permitted_checks: Sequence[str],
    expected_input_digest: str,
) -> tuple[str, dict[str, Any]]:
    """Return the Evidence-layer classification for one real launch's own bounded outcome --
    never a bare ``review_status == "COMPLETED"`` string match (PR #112 comment 6019024445,
    F2), but several independent, genuine structured signals checked together: the process
    group's own exit status and whether it was killed at the deadline (never trusted from the
    reviewed subprocess's own self-report), whether its parsed structured output names a real
    completion at all, whether what it claims to have inspected actually covers *every* path
    the grant permitted (partial or over-scope coverage is :data:`VERIFICATION_INSUFFICIENT`,
    never a silent pass), and -- SR3-F2 correction (PR #112 comment 6030487245) -- whether
    *every one* of *permitted_checks* actually has a genuine, well-shaped ``PASS``/``FAIL``
    disposition reported for it.

    SR3-F2 correction: before this correction, the only signal this function read from
    ``findings`` was an allowlisted severity string -- reproduced gaps: a ``COMPLETED`` result
    carrying a ``P0`` finding (outside the then-``{P1, BLOCKING, CRITICAL}`` allowlist), and a
    finding declaring ``condition=CORRECTNESS``/``status=FAILED`` with no severity at all,
    were both still reported :data:`VERIFICATION_VERIFIED`; an empty ``findings`` list -- no
    evidence any permitted check was ever actually performed -- was accepted as "nothing
    failed" rather than refused as "nothing observed". Fixed: every finding must now declare a
    real ``status`` (``"PASS"`` or ``"FAIL"``) -- anything else (missing, malformed, a bare
    severity with no status) makes the whole result :data:`VERIFICATION_INSUFFICIENT`, never
    silently ignored; every one of *permitted_checks* must have at least one finding reporting
    on it, by name, or the result is :data:`VERIFICATION_INSUFFICIENT` ("no evidence this
    check was ever performed"); any check reporting ``"FAIL"`` is :data:`VERIFICATION_FAILED`;
    *severity* remains a secondary, independent signal -- a ``"PASS"`` finding that also
    declares a blocking severity is self-contradictory and refused outright, and any blocking
    severity present anywhere still fails the result even if every declared *status* is
    ``"PASS"``.

    SR4-F2 correction (PR #112 comment 6032479337): before this correction, a later finding's
    ``"PASS"`` for the identical ``check`` silently overwrote an earlier ``"FAIL"`` for that
    same check (reproduced: ``CORRECTNESS FAIL`` followed by ``CORRECTNESS PASS`` -> VERIFIED);
    a ``"FAIL"`` finding naming no recognized ``check`` at all was silently dropped rather than
    refused (reproduced: a bare ``status=FAIL``/no ``check`` finding, alongside a *separate*
    ``check=CORRECTNESS``/``PASS`` finding -> VERIFIED). Fixed: once a check is recorded
    ``"FAIL"``, no later finding for the identical check can ever revert it to ``"PASS"``; a
    ``"FAIL"`` finding that names no recognized check still fails the whole result, never
    silently ignored merely because it cannot be attributed to a permitted check by name.

    *expected_input_digest* (SR4-F2 correction): the result's own self-reported
    ``observed_input_digest`` -- computed by the reviewing process itself, over whatever files
    it could actually see in its own working directory, the identical way :func:`
    digest_inspection_input` computes it -- must equal this value, or the result is
    :data:`VERIFICATION_INSUFFICIENT`. Before this correction, a result naming genuine paths/
    checks but carrying zero correlation to *which* staged input it actually ran against was
    still accepted as fully sufficient evidence; a result's own claim to have reviewed
    something is now required to independently reproduce the identical digest of what it was
    actually given, never merely assert PASS over a path list with nothing underneath it.

    *launch_result* is a :class:`~manosube_agent_civilization.development_binding.
    review_adapter.ReviewLaunchResult`; accepted here as ``Any`` only to avoid this script
    importing that dataclass merely to annotate a parameter it never constructs itself.
    """

    codex_result = parse_structured_review_output(launch_result.stdout)
    if launch_result.timed_out:
        return VERIFICATION_INSUFFICIENT, codex_result
    if launch_result.exit_code != 0:
        return VERIFICATION_FAILED, codex_result
    # SR2-F2 correction (PR #112 comment 6021757577): truncated captured output can never be
    # fully trusted as a complete structured signal -- a truncated ``findings``/
    # ``inspected_paths`` list could be silently missing exactly the entry that would have
    # changed this classification. Reported INSUFFICIENT, never VERIFIED/FAILED on a partial
    # read.
    if launch_result.stdout_truncated or launch_result.stderr_truncated:
        return VERIFICATION_INSUFFICIENT, codex_result

    review_status = codex_result.get("review_status")
    inspected_paths = codex_result.get("inspected_paths")
    findings = codex_result.get("findings")
    if review_status == "UNAVAILABLE":
        return VERIFICATION_UNAVAILABLE, codex_result
    if not isinstance(inspected_paths, list) or not isinstance(findings, list):
        return VERIFICATION_INSUFFICIENT, codex_result
    if not set(permitted_paths) <= set(inspected_paths):
        return VERIFICATION_INSUFFICIENT, codex_result
    # SR2-F2 correction: coverage was previously checked in one direction only
    # (``permitted_paths`` ⊆ ``inspected_paths``) -- a result naming an inspected path *outside*
    # the grant's own permitted scope is over-scope, never silently accepted merely because the
    # permitted set was also covered.
    if not set(inspected_paths) <= set(permitted_paths):
        return VERIFICATION_INSUFFICIENT, codex_result
    if review_status == "FAILED":
        return VERIFICATION_FAILED, codex_result
    if review_status != "COMPLETED":
        return VERIFICATION_INSUFFICIENT, codex_result

    # SR4-F2 correction (PR #112 comment 6032479337): a result's own claim to have reviewed
    # something is never itself correlated to *which* staged input it actually ran against --
    # checked here, against the real review process's own self-computed digest, before any
    # finding is even read.
    if codex_result.get("observed_input_digest") != expected_input_digest:
        return VERIFICATION_INSUFFICIENT, codex_result

    observed_status_by_check: dict[str, str] = {}
    any_blocking_severity = False
    any_unattributed_failure = False
    for finding in findings:
        if not isinstance(finding, dict):
            return VERIFICATION_INSUFFICIENT, codex_result
        status = finding.get("status")
        if status not in ("PASS", "FAIL"):
            return VERIFICATION_INSUFFICIENT, codex_result
        severity = finding.get("severity")
        if severity in BLOCKING_FINDING_SEVERITIES:
            if status == "PASS":
                # Self-contradictory: a PASS can never also declare a blocking severity.
                return VERIFICATION_INSUFFICIENT, codex_result
            any_blocking_severity = True
        check = finding.get("check")
        if isinstance(check, str) and check:
            # SR4-F2 correction: monotonic -- once a check is recorded FAIL, no later finding
            # for the identical check (reproduced: a duplicate PASS) can ever revert it.
            if observed_status_by_check.get(check) != "FAIL":
                observed_status_by_check[check] = status
        elif status == "FAIL":
            # SR4-F2 correction: a FAIL that cannot be attributed to any recognized check is
            # never silently dropped merely because it has nothing to be coverage-matched
            # against (reproduced: a bare status=FAIL/no-check finding alongside an unrelated,
            # separately-named check=X/PASS finding).
            any_unattributed_failure = True

    if set(permitted_checks) - set(observed_status_by_check):
        # At least one permitted check has no finding reporting on it at all -- never treated
        # as a silent pass merely because nothing explicitly failed.
        return VERIFICATION_INSUFFICIENT, codex_result
    if any(status == "FAIL" for status in observed_status_by_check.values()):
        return VERIFICATION_FAILED, codex_result
    if any_unattributed_failure:
        return VERIFICATION_FAILED, codex_result
    if any_blocking_severity:
        return VERIFICATION_FAILED, codex_result
    return VERIFICATION_VERIFIED, codex_result


def _recheck_live_authorization(
    *,
    grant: Mapping[str, Any],
    now_provider: Callable[[], str],
    activation_evidence_provider: Callable[[], Mapping[str, Any]],
    live_state_transport: LiveReviewStateTransport,
    store: Any,
    project_id: str,
    project_binding_id: str,
    verifier_identity: Mapping[str, Any],
    permitted_boundary: Mapping[str, Any],
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
    grant_provider: Callable[[], Mapping[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return a refusal dict, or ``None`` if every live admission check still holds at this
    exact instant -- SR2-F1 correction (PR #112 comment 6021757577).

    Before this correction, :func:`compose_bounded_technical_review_dispatch` evaluated
    ``evaluate_review_selection``/``evaluate_activation_gate``/``authenticate_bounded_review_
    grant`` exactly once, at admission, over whatever static ``now``/``activation_evidence``
    strings the caller happened to supply at the top of the call -- "``current_*``" values a
    caller wrote once were never actually re-read, so nothing distinguished a genuinely fresh
    trusted-clock/kill-switch/activation check from a caller merely repeating the same literal
    string it already had. This function re-runs the identical three checks against whatever
    *now_provider*/*activation_evidence_provider* return when *called*, at the instant each
    checkpoint below actually needs them -- a caller that supplies a real live clock/kill-switch
    reader gets a genuinely fresh re-check; a caller that supplies none (every pre-existing
    caller, via this module's own ``lambda: now``/``lambda: activation_evidence`` defaults)
    still gets the identical static re-check repeated, never silently skipped.

    SR3-F1 correction (PR #112 comment 6030487245): *permitted_boundary* now carries
    ``launch_envelope_digest`` (:func:`~manosube_agent_civilization.development_binding.
    review_selection.compute_launch_envelope_digest`) -- the complete launch envelope, not
    merely the inspection scope -- so every call this function makes to
    :func:`~manosube_agent_civilization.development_binding.review_selection.
    authenticate_bounded_review_grant` below re-authenticates the *whole* envelope against a
    real, Human-Authority-signed ``verifier_selection_grant`` record, fresh from the Store,
    every time. This is the real fix; *grant_provider*, when given, is a cheap, optional
    pre-check that can catch an obviously-changed envelope *before* paying for that heavier
    Store/Authority round trip -- it is no longer the primary authentication, and its absence
    no longer leaves the envelope unauthenticated the way it did before this correction.

    SR4-F1 correction (PR #112 comment 6032479337): before this correction,
    ``evaluate_review_selection`` was called against *grant* itself -- its own
    ``current_repository``/``current_pull_request``/``current_base_sha``/``current_head_sha``
    fields, written once by whichever caller built the grant dict and never refreshed from
    anywhere live. A "fresh" re-check against values nothing had ever actually re-observed
    could never distinguish a genuinely still-current PR from one that had moved on.
    *live_state_transport* is now a required parameter (never optional, never defaulted to a
    stale echo): :func:`~manosube_agent_civilization.development_binding.review_adapter.
    fetch_trusted_live_review_state` calls it fresh, at this exact instant, and this function
    builds the record ``evaluate_review_selection`` actually sees by overwriting ``current_
    base_sha``/``current_head_sha`` with what that live call just returned -- never the grant's
    own static fields. An engaged kill switch refuses outright before the live sha comparison
    is even reached.
    """

    if grant_provider is not None:
        fresh_grant = grant_provider()
        for field in (
            "authorized_repository",
            "authorized_pull_request",
            "authorized_base_sha",
            "authorized_head_sha",
            "requirement_id",
            "input_digest",
        ):
            if fresh_grant.get(field) != grant.get(field):
                return {
                    "reason": "GRANT_ENVELOPE_CHANGED",
                    "field": field,
                    "original": grant.get(field),
                    "fresh": fresh_grant.get(field),
                }

    live_state = fetch_trusted_live_review_state(
        live_state_transport,
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
    )
    if live_state["kill_switch_engaged"]:
        return {"reason": "KILL_SWITCH_ENGAGED", "live_state": live_state}

    live_checked_grant = dict(grant)
    live_checked_grant["current_repository"] = grant["authorized_repository"]
    live_checked_grant["current_pull_request"] = grant["authorized_pull_request"]
    live_checked_grant["current_base_sha"] = live_state["current_base_sha"]
    live_checked_grant["current_head_sha"] = live_state["current_head_sha"]

    fresh_now = now_provider()
    selection_decision = evaluate_review_selection(live_checked_grant, now=fresh_now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {"reason": "SELECTION_NO_LONGER_ADMITTED", "decision": selection_decision}

    gate_decision = evaluate_activation_gate(activation_evidence_provider())
    if gate_decision["decision"] != "ACTIVATION_GATE_ACTIVATED":
        return {"reason": "ACTIVATION_NO_LONGER_ACTIVE", "decision": gate_decision}

    authentication_decision = authenticate_bounded_review_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        requirement_id=grant["requirement_id"],
        selection_id=grant["work_unit_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=verifier_selection_grant_refs,
        human_grant_declaration_refs=human_grant_declaration_refs,
    )
    if authentication_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {
            "reason": "AUTHENTICATION_NO_LONGER_ADMITTED",
            "decision": authentication_decision,
        }

    return None


def compose_bounded_technical_review_dispatch(
    *,
    grant: dict[str, Any],
    now: str,
    ledger_path: Path,
    activation_evidence: Mapping[str, Any],
    store: Any,
    project_id: str,
    project_binding_id: str,
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
    live_state_transport: LiveReviewStateTransport,
    source_root: Path,
    codex_executable: str,
    prompt_path: Path,
    orchestrator_env: Mapping[str, str],
    mask_paths: Sequence[Path] = (),
    clock: Callable[[], float] = time.monotonic,
    build_argv: Callable[[Path], Sequence[str]] | None = None,
    now_provider: Callable[[], str] | None = None,
    activation_evidence_provider: Callable[[], Mapping[str, Any]] | None = None,
    grant_provider: Callable[[], Mapping[str, Any]] | None = None,
    evidence_handoff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """The one composed Bounded Technical Review dispatch route (PR #112 comment 6019024445,
    F2), in the exact order the F5/SR2-F4/SR2-F1 corrections require:

    ```text
    validate-grant (pure)      -> evaluate_review_selection
    activation-gate (pure)     -> evaluate_activation_gate            -- before any claim, F5
    authenticate (Boot/Authority/Store) -> authenticate_bounded_review_grant             -- F1
    claim (durable ledger)     -> claim_review_launch
    input-stage+digest-verify  -> prepare_inspection_workspace + digest_inspection_input
    input-size-cap             -> measure_inspection_input_bytes                    -- SR2-F2
    preconditions (pre-launch) -> validate_review_launch_preconditions              -- SR2-F4
    live-recheck (pre-send)    -> _recheck_live_authorization, while still CLAIMED  -- SR2-F1
    ack-unknown (durable ledger) -> record_dispatch_attempt(acknowledged=False)      -- SR2-F4
    spawn (external effect)    -> spawn_review_process, exactly once                -- SR2-F4
    confirm-sent (durable ledger) -> confirm_dispatch_sent, with the real pid        -- SR2-F4
    collect (bounded wait)     -> collect_review_process_result                     -- SR2-F4
    classify (real signals)    -> classify_review_result                            -- SR2-F2
    live-recheck (pre-accept)  -> _recheck_live_authorization, over the real result  -- SR2-F1
    record-outcome (durable ledger) -> record_review_outcome
    evidence-handoff (opt-in)  -> run_independent_verification + evidence_handoff    -- SR2-F2
    ```

    Every stage before ``claim`` performs zero ledger writes -- an ineligible or unauthenticated
    request never reserves the repository's one concurrency slot or a day's own launch budget
    (the exact ordering bug F5 corrects). A digest mismatch, an over-size staged input, a
    precondition refusal, or a pre-send live-recheck refusal -- every one of them discovered
    while the claim is still ``CLAIMED``, before :func:`~manosube_agent_civilization.
    development_binding.review_adapter.spawn_review_process` is ever called -- releases the
    slot via :func:`~manosube_agent_civilization.development_binding.review_control.
    release_unsent_claim` rather than recording a false outcome: nothing was ever sent.

    SR2-F4 correction (PR #112 comment 6021757577): once :func:`~manosube_agent_civilization.
    development_binding.review_control.record_dispatch_attempt` records ``ACK_UNKNOWN`` -- the
    one durable marker that an attempt is *about* to be made -- this route never again releases
    the claim as unsent; the one remaining irreducible window (the real ``spawn_review_process``
    call itself) is covered by an already-``ACK_UNKNOWN`` claim a restarted controller could
    still recover real ownership proof from, never one indistinguishable from "never sent". The
    real pid/process identity is attached the instant :func:`~manosube_agent_civilization.
    development_binding.review_adapter.spawn_review_process` returns (:func:`~manosube_agent_
    civilization.development_binding.review_control.confirm_dispatch_sent`) -- before the
    collection wait, which may run up to the ratified ceiling, ever begins.

    SR2-F1 correction: *now_provider*/*activation_evidence_provider*/*grant_provider*, when
    given, let a caller wire in a genuinely live trusted clock, kill-switch/activation reader,
    and grant re-fetch -- re-checked by :func:`_recheck_live_authorization` immediately before
    the one external effect is ever sent, and again immediately before its result is ever
    accepted into the ledger. Every pre-existing caller that supplies none of them still gets
    the identical two checkpoints, just repeating the one static admission already proven at the
    top of this call -- never silently skipped, even when it adds nothing new to check.

    SR2-F2/SR3-F2 correction: the staged inspection input itself is bounded (distinct from the
    launched process's own captured-output ceiling, already enforced by :mod:`.review_adapter`)
    by :func:`~manosube_agent_civilization.development_binding.review_adapter.
    prepare_inspection_workspace` itself, against the ratified ``max_input_bytes`` ceiling --
    checked per file, before it is ever opened, never only against the whole bundle after it
    was already fully staged, and never a parameter this route (or any caller) can widen.
    :func:`classify_review_result` itself now also refuses a truncated capture, an over-scope
    inspected path, and -- SR3-F2's own correction -- any permitted check the result does not
    report a genuine ``PASS``/``FAIL`` disposition for, never merely a severity scan over
    whatever findings happen to be present. *evidence_handoff*, when given, is a mapping with
    exactly ``verification_requirement``/``verifier_selection``/``evidence_request`` keys --
    this route then performs the one real :mod:`~manosube_agent_civilization.
    independent_verification` handoff itself (wrapping this call's own already-collected
    classification/``codex_result`` as the one real verifier outcome), rather than leaving
    every caller to hand-assemble the identical sequence (as this delivery's own integration
    test previously had to). SR3-F2 correction: this route now also refuses outright
    (:class:`~manosube_agent_civilization.development_binding.errors.ReviewAdapterError`) if
    *evidence_handoff*'s own ``verification_requirement``/``verifier_selection`` do not name
    *this exact* (``requirement_id``, ``permitted_boundary``) scope -- a genuinely authorized
    handoff for a *different* requirement/scope is never interchangeable with this one's own
    result, however real its own authority is. This route still never *fabricates*
    ``target_refs``, ``selection_authority_ref``, or an ``evidence_request`` -- those must
    already be genuine, Store-backed context only the caller can supply; when *evidence_handoff*
    is omitted, this route stops at the ledger outcome exactly as before, and the caller is free
    to perform that handoff itself.

    This function performs the one real :mod:`.review_adapter` launch this delivery's own
    composed route can ever make.

    *build_argv*, when given, replaces :func:`~manosube_agent_civilization.development_binding.
    review_adapter.build_codex_review_argv`'s own fixed real-CLI argv with an explicit
    ``Callable[[Path], Sequence[str]]`` over the prepared workspace -- the one seam this
    delivery's own tests use to exercise this entire composed route end to end against a
    controlled local fake executable, never the real Codex CLI
    (``REAL_CODEX_MODEL_REQUEST_ALLOWED=false``, identical to every other :mod:`.
    review_adapter` test in this delivery). Production/CLI callers never pass it.
    """

    # SR3-F1 correction (PR #112 comment 6030487245): a caller that supplies no now_provider
    # still gets a genuinely live read of the real wall clock at each recheck checkpoint --
    # never an echo of the one literal `now` string the top-of-call admission already used.
    now_provider = now_provider or _default_live_now
    activation_evidence_provider = activation_evidence_provider or (lambda: activation_evidence)

    selection_decision = evaluate_review_selection(grant, now=now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {"stage": "validate-grant", "decision": selection_decision}

    gate_decision = evaluate_activation_gate(activation_evidence)
    if gate_decision["decision"] != "ACTIVATION_GATE_ACTIVATED":
        return {"stage": "activation-gate", "decision": gate_decision}

    verifier_identity = {
        "kind": "bounded_codex_technical_reviewer",
        "id": grant["inspector_session_ref"],
    }
    # SR3-F1/F2 correction (PR #112 comment 6030487245): permitted_boundary carries
    # content-address digests of the inspection scope plus launch_envelope_digest -- the
    # complete launch envelope (repository/PR/base/head/requirement/input digest/window/
    # provenance/environment) -- never the raw permitted_paths/permitted_checks lists
    # themselves. Digests, not lists, for a second reason beyond SR3-F1's own envelope
    # authentication: a list value survives this exact dict unchanged only through callers
    # that never pass it through a VerifierSelection's own deep-freeze (SR2-F2's evidence_
    # handoff does); a tuple a list becomes there is not itself a JSON array
    # (`state.canonicalize`'s own contract), so a permitted_boundary containing a raw list can
    # never be reused, unmodified, as a VerifierSelection's own permitted_boundary for the
    # identical scope's Evidence handoff. A boundary built entirely from scalar digests has no
    # such landmine, and is the identical object this route's own evidence_handoff correlation
    # check (below) can require a caller's VerifierSelection to equal exactly.
    permitted_boundary = {
        "permitted_paths_digest": canonical_list_digest(grant["permitted_paths"]),
        "permitted_checks_digest": canonical_list_digest(grant["permitted_checks"]),
        "launch_envelope_digest": compute_launch_envelope_digest(grant),
    }
    authentication_decision = authenticate_bounded_review_grant(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        requirement_id=grant["requirement_id"],
        selection_id=grant["work_unit_id"],
        verifier_identity=verifier_identity,
        permitted_boundary=permitted_boundary,
        verifier_selection_grant_refs=verifier_selection_grant_refs,
        human_grant_declaration_refs=human_grant_declaration_refs,
    )
    if authentication_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {"stage": "authenticate", "decision": authentication_decision}

    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    claim_decision = claim_review_launch(
        ledger_path,
        identity_key=identity_key,
        work_unit_id=grant["work_unit_id"],
        repository=grant["authorized_repository"],
        now=now,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    if claim_decision["decision"] != REVIEW_CLAIM_ADMITTED:
        return {"stage": "claim", "decision": claim_decision}

    def _recheck() -> dict[str, Any] | None:
        return _recheck_live_authorization(
            grant=grant,
            now_provider=now_provider,
            activation_evidence_provider=activation_evidence_provider,
            live_state_transport=live_state_transport,
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            verifier_identity=verifier_identity,
            permitted_boundary=permitted_boundary,
            verifier_selection_grant_refs=verifier_selection_grant_refs,
            human_grant_declaration_refs=human_grant_declaration_refs,
            grant_provider=grant_provider,
        )

    # SR3-F2 correction (PR #112 comment 6030487245): prepare_inspection_workspace itself now
    # enforces the ratified max_input_bytes ceiling, per file, before any byte is staged --
    # never only against the whole bundle after it was already fully copied, and never a
    # parameter this route (or any caller) can widen. The claim is still CLAIMED here, so a
    # refusal still releases it as genuinely unsent.
    try:
        workspace = prepare_inspection_workspace(
            source_root, permitted_paths=grant["permitted_paths"]
        )
    except ReviewAdapterError as error:
        release_unsent_claim(ledger_path, identity_key, repository=grant["authorized_repository"])
        return {"stage": "input-staging", "identity_key": identity_key, "error": str(error)}

    try:
        actual_input_digest = digest_inspection_input(workspace)
        if actual_input_digest != grant["input_digest"]:
            release_unsent_claim(
                ledger_path, identity_key, repository=grant["authorized_repository"]
            )
            return {
                "stage": "input-digest-verify",
                "identity_key": identity_key,
                "expected_input_digest": grant["input_digest"],
                "actual_input_digest": actual_input_digest,
            }

        if build_argv is None:
            argv = build_codex_review_argv(
                codex_executable=codex_executable, workspace=workspace, prompt_path=prompt_path
            )
        else:
            argv = list(build_argv(workspace))
        env = build_subprocess_environment(orchestrator_env)

        try:
            # SR3-F5 correction (PR #112 comment 6030487245): a non-empty mask_paths was never
            # itself evidence that the orchestrator's own sensitive roots were actually among
            # them -- the exact reproduced gap: the source checkout and ancestor instruction/
            # hook paths under HOME remained fully readable/writable from inside a launched
            # process regardless of what mask_paths happened to contain. required_mask_roots
            # is this route's own declared list of roots that must actually be covered.
            # SR4-F1 correction (PR #112 comment 6032479337): argv/cwd are now validated here,
            # before the token is minted, so the token this route carries forward is bound to
            # the exact configuration spawn_review_process below will actually be given --
            # never a bare marker a differently-configured spawn call could also consume.
            admission_token = validate_review_launch_preconditions(
                argv=argv,
                cwd=workspace,
                max_seconds=BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"],
                max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
                mask_paths=mask_paths,
                require_isolation=True,
                required_mask_roots=[source_root, Path.home()],
            )
        except ReviewAdapterError as error:
            release_unsent_claim(
                ledger_path, identity_key, repository=grant["authorized_repository"]
            )
            return {"stage": "preconditions", "identity_key": identity_key, "error": str(error)}

        pre_send_refusal = _recheck()
        if pre_send_refusal is not None:
            # SR2-F1: still CLAIMED here -- record_dispatch_attempt has not yet run, so nothing
            # was ever sent, and the slot may still be honestly released as unsent.
            release_unsent_claim(
                ledger_path, identity_key, repository=grant["authorized_repository"]
            )
            return {
                "stage": "live-recheck-pre-send",
                "identity_key": identity_key,
                "refusal": pre_send_refusal,
            }

        # SR2-F4: durably mark "an attempt is about to be made" *before* the one irreducible
        # external-effect call -- a crash between this line and the next can never again be
        # mistaken, on restart, for "this identity was never sent".
        record_dispatch_attempt(
            ledger_path,
            identity_key,
            repository=grant["authorized_repository"],
            acknowledged=False,
        )
        started_at = clock()
        process = spawn_review_process(
            argv,
            cwd=workspace,
            env=env,
            admission_token=admission_token,
            mask_paths=mask_paths,
            require_isolation=True,
        )
        confirm_dispatch_sent(
            ledger_path,
            identity_key,
            repository=grant["authorized_repository"],
            pid=process.pid,
            process_identity=process_identity_token(process.pid) or "",
        )
        launch_result = collect_review_process_result(
            process,
            max_seconds=BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"],
            max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
            clock=clock,
            started_at=started_at,
        )

        classification, codex_result = classify_review_result(
            launch_result,
            permitted_paths=grant["permitted_paths"],
            permitted_checks=grant["permitted_checks"],
            expected_input_digest=grant["input_digest"],
        )

        # SR2-F1: pre-accept -- a real process genuinely ran and genuinely returned bytes
        # (recorded below regardless), but whether this route still *trusts* that result as a
        # live-authorized outcome is re-checked fresh, one more time, before it is accepted.
        pre_accept_refusal = _recheck()
        if pre_accept_refusal is not None:
            record_review_outcome(
                ledger_path,
                identity_key,
                repository=grant["authorized_repository"],
                status=STATUS_FAILED,
                resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
                result_bytes=launch_result.stdout,
            )
            return {
                "stage": "live-recheck-pre-accept",
                "identity_key": identity_key,
                "refusal": pre_accept_refusal,
                "codex_result": codex_result,
            }

        ledger_status = (
            STATUS_COMPLETED if classification == VERIFICATION_VERIFIED else STATUS_FAILED
        )
        record_review_outcome(
            ledger_path,
            identity_key,
            repository=grant["authorized_repository"],
            status=ledger_status,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_bytes=launch_result.stdout,
        )
        response: dict[str, Any] = {
            "stage": "complete",
            "identity_key": identity_key,
            "classification": classification,
            "codex_result": codex_result,
            "launch_result": {
                "exit_code": launch_result.exit_code,
                "timed_out": launch_result.timed_out,
                "pid": launch_result.pid,
            },
        }

        if evidence_handoff is not None:
            response["evidence"] = _hand_off_to_evidence(
                evidence_handoff=evidence_handoff,
                store=store,
                project_id=project_id,
                project_binding_id=project_binding_id,
                verifier_selection_grant_refs=verifier_selection_grant_refs,
                human_grant_declaration_refs=human_grant_declaration_refs,
                grant=grant,
                permitted_boundary=permitted_boundary,
                identity_key=identity_key,
                classification=classification,
                codex_result=codex_result,
            )
        return response
    finally:
        cleanup_inspection_workspace(workspace)


def _hand_off_to_evidence(
    *,
    evidence_handoff: Mapping[str, Any],
    store: Any,
    project_id: str,
    project_binding_id: str,
    verifier_selection_grant_refs: Sequence[Mapping[str, Any]],
    human_grant_declaration_refs: Sequence[Mapping[str, Any]],
    grant: Mapping[str, Any],
    permitted_boundary: Mapping[str, Any],
    identity_key: str,
    classification: str,
    codex_result: Mapping[str, Any],
) -> dict[str, Any]:
    """The one real Evidence-layer handoff for an already-collected Bounded Review result
    (SR2-F2 correction, PR #112 comment 6021757577): wraps this call's own already-computed
    *classification*/*codex_result* as the one real :class:`~manosube_agent_civilization.
    independent_verification.types.IndependentVerifier` outcome, runs it through the existing
    :func:`~manosube_agent_civilization.independent_verification.route.
    run_independent_verification`, and hands the resulting :class:`~manosube_agent_civilization.
    independent_verification.types.VerificationResult` to :func:`~manosube_agent_civilization.
    independent_verification.evidence_handoff.route_verification_result_to_evidence`.

    *evidence_handoff* must carry real, already Store-backed ``verification_requirement``
    (:class:`~manosube_agent_civilization.independent_verification.types.
    VerificationRequirement`) and ``verifier_selection`` (:class:`~manosube_agent_civilization.
    independent_verification.types.VerifierSelection`) instances, plus a real
    ``evidence_request`` mapping -- this function fabricates none of the three; a caller that
    has no genuine ``target_refs``/``selection_authority_ref``/Evidence request to supply should
    omit *evidence_handoff* entirely and perform no handoff, never pass placeholder content
    here. ``independent_verification`` is imported here, at call time, for the identical
    reason :func:`~manosube_agent_civilization.development_binding.review_selection.
    authenticate_bounded_review_grant` imports ``boot``/``authority`` lazily: this module's own
    import-time surface stays minimal for every caller that never requests this handoff.

    SR3-F2 correction (PR #112 comment 6030487245): before this correction, this function
    passed *evidence_handoff*'s own ``verification_requirement``/``verifier_selection``
    straight through with no check that either actually named *this* launch's own
    (*requirement_id*, *permitted_boundary*) scope -- reproduced gap: the integration test
    this correction fixes had, until now, handed off through a genuinely-authorized
    ``VerifierSelection`` for a *different* requirement/scope than the one this launch itself
    inspected. Genuine authority for two separate scopes never makes their outcomes
    interchangeable, so this function now requires *verification_requirement*'s own
    ``requirement_id``/``verification_boundary`` and *verifier_selection*'s own
    ``requirement_id``/``permitted_boundary`` to exactly equal *grant*'s own ``requirement_id``
    and this launch's own authenticated *permitted_boundary* -- raising
    :class:`~manosube_agent_civilization.development_binding.errors.ReviewAdapterError`
    outright on any mismatch, before ``run_independent_verification`` is ever called. Since
    *permitted_boundary* is built entirely from scalar digests (:func:`canonical_list_digest`,
    SR3-F2), it is also now the identical object a caller's own ``VerifierSelection`` can equal
    exactly -- the SR2-era workaround of authorizing the handoff through a *different*,
    list-free-boundary grant no longer applies, and this function accepts only the identical
    *verifier_selection_grant_refs*/*human_grant_declaration_refs* this launch's own admission
    already used.
    """

    from manosube_agent_civilization.independent_verification.evidence_handoff import (
        route_verification_result_to_evidence,
    )
    from manosube_agent_civilization.independent_verification.route import (
        run_independent_verification,
    )
    from manosube_agent_civilization.independent_verification.types import (
        VerificationRequirement,
        VerifierSelection,
    )

    verification_requirement = evidence_handoff["verification_requirement"]
    verifier_selection = evidence_handoff["verifier_selection"]
    if not isinstance(verification_requirement, VerificationRequirement):
        raise TypeError(
            "evidence_handoff['verification_requirement'] must be a VerificationRequirement "
            f"instance, not {type(verification_requirement)!r}"
        )
    if not isinstance(verifier_selection, VerifierSelection):
        raise TypeError(
            f"evidence_handoff['verifier_selection'] must be a VerifierSelection instance, "
            f"not {type(verifier_selection)!r}"
        )

    if verification_requirement.requirement_id != grant["requirement_id"]:
        raise ReviewAdapterError(
            "evidence_handoff's own verification_requirement.requirement_id "
            f"({verification_requirement.requirement_id!r}) does not match this launch's own "
            f"grant requirement_id ({grant['requirement_id']!r}) -- a genuinely authorized "
            "handoff for a different requirement is never interchangeable with this one's own "
            "result"
        )
    if verifier_selection.requirement_id != grant["requirement_id"]:
        raise ReviewAdapterError(
            "evidence_handoff's own verifier_selection.requirement_id "
            f"({verifier_selection.requirement_id!r}) does not match this launch's own grant "
            f"requirement_id ({grant['requirement_id']!r})"
        )
    if dict(verification_requirement.verification_boundary) != dict(permitted_boundary):
        raise ReviewAdapterError(
            "evidence_handoff's own verification_requirement.verification_boundary does not "
            "equal this launch's own authenticated permitted_boundary"
        )
    if dict(verifier_selection.permitted_boundary) != dict(permitted_boundary):
        raise ReviewAdapterError(
            "evidence_handoff's own verifier_selection.permitted_boundary does not equal this "
            "launch's own authenticated permitted_boundary"
        )

    declared_identity = dict(verifier_selection.verifier_identity)

    # The canonical identity schema (``01_SCHEMA/common/identity.schema.json``) requires an
    # uppercase ``^[A-Z][A-Z0-9]*(-[A-Z0-9]+)+`` shape -- *identity_key* itself is a lowercase
    # hex digest, so it is re-cast into a compliant reference id here rather than used as one
    # directly.
    input_ref_id = "BOUNDED-REVIEW-LAUNCH-" + identity_key.upper()

    def _constant_verifier(*, requirement: Any, selection: Any) -> dict[str, Any]:
        return {
            "status": classification,
            "input_refs": [{"kind": "bounded_review_launch", "id": input_ref_id}],
            "observations": {"codex_review": dict(codex_result)},
        }

    _constant_verifier.verifier_identity = declared_identity  # type: ignore[attr-defined]

    verification_result = run_independent_verification(
        store,
        project_id=project_id,
        project_binding_id=project_binding_id,
        verification_requirement=verification_requirement,
        verifier_selection=verifier_selection,
        verifier_selection_grant_refs=verifier_selection_grant_refs,
        human_grant_declaration_refs=human_grant_declaration_refs,
        verifier=_constant_verifier,
    )
    return route_verification_result_to_evidence(
        verification_result, evidence_handoff["evidence_request"]
    )


def compose_bounded_technical_review_cancellation(
    *,
    ledger_path: Path,
    identity_key: str,
    repository: str,
    pid: int,
    owned_process_identity: str,
) -> dict[str, Any]:
    """The one canonical Bounded Technical Review cancellation route (SR2-F5 correction, PR
    #112 comment 6021757577) -- never bare *pid*/*owned_process_identity* ownership alone.

    The exact reproduced gap this closes: :func:`~manosube_agent_civilization.
    development_binding.review_adapter.cancel_review_task` treats a bare caller-supplied
    *pid* and *owned_process_identity* that merely happen to match each other
    (:func:`~manosube_agent_civilization.development_binding.review_adapter.
    process_identity_token`'s own shape) as sufficient proof of ownership -- the finding
    reproduced this by starting an unrelated, harmless subprocess entirely *outside* this
    delivery's own ledger/adapter, reading its own token directly, and successfully cancelling
    it this way, with ``ownership_confirmed=True``. This function is the one route that first
    requires *identity_key* to name a real ledger claim, for *repository*, currently
    ``DISPATCHED`` or ``ACK_UNKNOWN``, whose own recorded ``pid``/``process_identity`` -- set
    only by :func:`~manosube_agent_civilization.development_binding.review_control.
    confirm_dispatch_sent`/:func:`~manosube_agent_civilization.development_binding.
    review_control.record_dispatch_attempt` for the one real process this delivery's own
    composed dispatch route actually started -- exactly matches the caller-supplied *pid*/
    *owned_process_identity*, before :func:`~manosube_agent_civilization.development_binding.
    review_adapter.cancel_review_task` is ever reached. An unrelated process's own pid/token,
    supplied here, never matches any live claim's own recorded ones, and is refused outright.

    A confirmed cancellation is recorded as the claim's own terminal outcome
    (:data:`~manosube_agent_civilization.development_binding.review_control.
    RESOLUTION_KIND_CONFIRMED_CANCELLATION`, ``result_bytes=None`` -- a cancellation never
    collects a result to digest), releasing the concurrency slot for a different identity,
    exactly as a genuine review outcome would.

    SR3-F4 correction (PR #112 comment 6030487245): a confirmed cancellation now also requires
    ``outcome.local_process_group_terminated`` -- before this correction, ``ownership_confirmed``
    alone reached ``CANCELLATION_CONFIRMED``, so a controlled fixture reporting ownership
    confirmed but the process group *not* actually terminated (``local_process_group_
    terminated=False``, ``provider_server_state=UNAVAILABLE``) still recorded a terminal
    outcome for a process this route never actually confirmed was gone.

    SR4-F4 correction (PR #112 comment 6032479337): before this correction, a local process
    group confirmed terminated reached the unqualified decision ``"CANCELLATION_CONFIRMED"`` --
    reproduced gap: a controlled fixture with ``local_process_group_terminated=True`` but
    ``provider_server_state=UNAVAILABLE`` (this adapter's own permanent, never-anything-else
    report of the provider/server-side task's own state -- see :mod:`~manosube_agent_
    civilization.development_binding.review_adapter`'s own module docstring) still reached
    that same unqualified "CONFIRMED" decision, overclaiming across the two facts the adapter
    itself deliberately never conflates: this call's own confirmed local termination, and the
    provider/task's own genuinely unknown state. Fixed: the success decision is now
    ``"CANCELLATION_CONFIRMED_LOCAL_ONLY"`` -- honestly scoped to what this route can ever
    actually confirm -- never the unqualified ``"CANCELLATION_CONFIRMED"``, which this route no
    longer returns at all; a caller reading ``decision`` alone, without separately checking
    ``provider_server_state``, is never misled into believing the provider/server-side task
    itself was ever confirmed stopped.
    """

    claim = read_claim(ledger_path, identity_key, repository=repository)
    if claim is None:
        return {
            "stage": "cancel",
            "decision": "CANCELLATION_REFUSED",
            "reason": "NO_SUCH_CLAIM",
        }
    if claim["status"] not in (STATUS_DISPATCHED, STATUS_ACK_UNKNOWN):
        return {
            "stage": "cancel",
            "decision": "CANCELLATION_REFUSED",
            "reason": "CLAIM_NOT_CANCELLABLE",
            "status": claim["status"],
        }
    if claim.get("pid") != pid or claim.get("process_identity") != owned_process_identity:
        return {
            "stage": "cancel",
            "decision": "CANCELLATION_REFUSED",
            "reason": "PID_OR_IDENTITY_NOT_BOUND_TO_THIS_CLAIM",
        }

    outcome: CancellationOutcome = cancel_review_task(
        pid=pid, owned_process_identity=owned_process_identity
    )
    if not outcome.ownership_confirmed:
        return {
            "stage": "cancel",
            "decision": "CANCELLATION_REFUSED",
            "reason": "OWNERSHIP_NOT_CONFIRMED",
            "local_process_group_terminated": outcome.local_process_group_terminated,
            "provider_server_state": outcome.provider_server_state,
        }
    # SR3-F4 correction (PR #112 comment 6030487245): before this correction, this route
    # confirmed a cancellation on `ownership_confirmed` alone -- reproduced gap: a controlled
    # fixture returning `ownership_confirmed=True, local_process_group_terminated=False,
    # provider_server_state=UNAVAILABLE` still reached `CANCELLATION_CONFIRMED`, recording a
    # terminal outcome for a process this route never actually confirmed was gone. Both facts
    # are now required: owning the process is never itself proof it was terminated.
    if not outcome.local_process_group_terminated:
        return {
            "stage": "cancel",
            "decision": "CANCELLATION_REFUSED",
            "reason": "PROCESS_GROUP_NOT_CONFIRMED_TERMINATED",
            "local_process_group_terminated": outcome.local_process_group_terminated,
            "provider_server_state": outcome.provider_server_state,
        }

    record_review_outcome(
        ledger_path,
        identity_key,
        repository=repository,
        status=STATUS_FAILED,
        resolution_kind=RESOLUTION_KIND_CONFIRMED_CANCELLATION,
        result_bytes=None,
    )
    return {
        "stage": "complete",
        "decision": "CANCELLATION_CONFIRMED_LOCAL_ONLY",
        "identity_key": identity_key,
        "local_process_group_terminated": outcome.local_process_group_terminated,
        "provider_server_state": outcome.provider_server_state,
    }


def compose_bounded_technical_review_outcome_recording(
    *,
    ledger_path: Path,
    identity_key: str,
    repository: str,
    status: str,
    resolution_kind: str,
    pid: int,
    owned_process_identity: str,
    result_bytes: bytes | None,
) -> dict[str, Any]:
    """The one canonical, ownership-checked route for recording a dispatched review's terminal
    outcome from outside the composed dispatch route itself (SR4-F4 correction, PR #112 comment
    6032479337).

    SR4-F4 correction: before this correction, this CLI's own ``record-outcome`` subcommand
    called the generic, directly-testable :func:`~manosube_agent_civilization.
    development_binding.review_control.record_review_outcome` primitive directly -- exactly the
    gap :func:`compose_bounded_technical_review_cancellation` already closed for ``cancel``
    (SR2-F5, PR #112 comment 6019024445), left open here. Reproduced gap: a claim left
    ``ACK_UNKNOWN`` (dispatch attempted, acknowledgement never confirmed, no real pid ever
    recorded) was resolved ``FAILED``/``COLLECTED_RESULT`` with an arbitrary, invented
    ``result_bytes=b"not a collected result"`` -- :func:`record_review_outcome`'s own SHA-256
    digest (the SR3-F4 fix) closes *caller-digest substitution* (a caller can no longer assert
    an arbitrary digest with nothing behind it), but never checked that the bytes it was given
    bytes at all correlate to any real, owned, dispatched operation this ledger ever actually
    launched -- releasing the concurrency slot (``active_lock``) for a different identity with
    zero such correlation. :func:`compose_bounded_technical_review_dispatch` itself was never
    vulnerable to this -- its own two calls to :func:`record_review_outcome` always pass
    ``result_bytes=launch_result.stdout``, the real bytes :func:`~manosube_agent_civilization.
    development_binding.review_adapter.collect_review_process_result` just read from the exact
    process that same call started moments earlier; there is no path through that composed
    route for a caller to substitute different bytes. The gap was entirely in the one other
    production caller that could reach :func:`record_review_outcome` without that structural
    guarantee: this CLI's own ``record-outcome`` subcommand.

    Fixed: this function is now that subcommand's one route, requiring *pid*/
    *owned_process_identity* to exactly match the claim's own recorded ``pid``/
    ``process_identity`` -- set only by :func:`~manosube_agent_civilization.development_binding.
    review_control.record_dispatch_attempt`/:func:`~manosube_agent_civilization.
    development_binding.review_control.confirm_dispatch_sent` for the one real process this
    delivery's own composed dispatch route actually started -- before
    :func:`record_review_outcome` is ever reached, mirroring
    :func:`compose_bounded_technical_review_cancellation`'s own identical check. A claim whose
    dispatch was never confirmed with a real pid (``claim["pid"] is None``) can never be
    resolved through this route at all -- there is nothing real to correlate to, and this
    route never invents one; such a claim's concurrency slot remains deliberately stuck (the
    module docstring's own "this module never auto-releases it" design), resolvable only by a
    kill switch or a Human revocation acting through some other, out-of-band means, never by an
    unauthenticated caller merely asserting bytes.
    """

    claim = read_claim(ledger_path, identity_key, repository=repository)
    if claim is None:
        return {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "NO_SUCH_CLAIM",
        }
    if claim["status"] not in (STATUS_DISPATCHED, STATUS_ACK_UNKNOWN):
        return {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "CLAIM_NOT_RESOLVABLE",
            "status": claim["status"],
        }
    if claim.get("pid") != pid or claim.get("process_identity") != owned_process_identity:
        return {
            "stage": "record-outcome",
            "decision": "OUTCOME_REFUSED",
            "reason": "PID_OR_IDENTITY_NOT_BOUND_TO_THIS_CLAIM",
        }

    record_review_outcome(
        ledger_path,
        identity_key,
        repository=repository,
        status=status,
        resolution_kind=resolution_kind,
        result_bytes=result_bytes,
    )
    return {
        "stage": "complete",
        "decision": "OUTCOME_RECORDED",
        "identity_key": identity_key,
    }


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622).
# --------------------------------------------------------------------------- #


def classify_native_review_result(
    native_evidence: Mapping[str, Any], *, required_checks: Sequence[str]
) -> str:
    """Return the Evidence-layer classification for one already-relevant native review (its
    relevance to *this* grant was already confirmed by :func:`~manosube_agent_civilization.
    development_binding.review_selection.evaluate_native_review_relevance` before this
    function is ever reached -- it never re-checks scope or base here).

    A native completion signal, or an empty ``findings`` list, is never by itself
    :data:`VERIFICATION_VERIFIED` -- the design supplement's own explicit requirement. Only
    ``review_state == "APPROVED"`` maps there; ``"COMMENTED"`` (a native review that finished
    with neither an approval nor a change request, findings or not) maps to
    :data:`VERIFICATION_INSUFFICIENT`, honestly reporting that the native review itself never
    reached an affirmative disposition, rather than inferring one from the mere absence of
    findings. ``"PENDING"`` (the real GitHub review state for one not yet submitted, and this
    delivery's own stand-in for "genuinely still running") maps to
    :data:`VERIFICATION_UNAVAILABLE` -- this function, and the composed route that calls it,
    never wait, poll, or queue a local launch on this account; see this module's own
    ``compose_bounded_technical_review_native_reuse_dispatch`` docstring.

    SR3-F3 correction (PR #112 comment 6030487245): before this correction,
    ``review_state == "APPROVED"`` mapped straight to :data:`VERIFICATION_VERIFIED` with no
    check of the evidence's own ``findings`` at all -- reproduced gap: an ``APPROVED`` review
    that still carried a genuine ``P1``/``FAIL`` finding (a reviewer who approved with an
    unresolved blocking comment attached) was still reported :data:`VERIFICATION_VERIFIED`.
    Fixed: an ``APPROVED`` disposition is now the necessary, never the sufficient, condition --
    any well-shaped finding reporting ``status == "FAIL"``, or declaring a severity in
    :data:`BLOCKING_FINDING_SEVERITIES`, still fails the result; a malformed finding (not a
    mapping, or a ``status`` present but not ``"PASS"``/``"FAIL"``) is reported
    :data:`VERIFICATION_INSUFFICIENT`, never silently ignored.

    SR4-F3 correction (PR #112 comment 6032479337): before this correction, this function took
    no ``required_checks`` at all -- an ``APPROVED`` review with ``findings=[]`` (no condition
    evidence whatsoever) was still fully :data:`VERIFICATION_VERIFIED` (reproduced). Fixed: the
    identical coverage requirement :func:`classify_review_result` already enforces for a local
    launch now applies here too -- every one of *required_checks* must have at least one
    finding reporting on it, by name, or the result is :data:`VERIFICATION_INSUFFICIENT`; a
    ``"FAIL"`` finding that cannot be attributed to any recognized check still fails the whole
    result (the identical monotonic, never-silently-ignored handling SR4-F2 added for a local
    launch's own findings).
    """

    review_state = native_evidence["review_state"]
    if review_state in ("PENDING", "DISMISSED"):
        return VERIFICATION_UNAVAILABLE
    if review_state == "CHANGES_REQUESTED":
        return VERIFICATION_FAILED
    if review_state != "APPROVED":
        return VERIFICATION_INSUFFICIENT

    observed_status_by_check: dict[str, str] = {}
    any_blocking_severity = False
    any_unattributed_failure = False
    for finding in native_evidence["findings"]:
        if not isinstance(finding, dict):
            return VERIFICATION_INSUFFICIENT
        status = finding.get("status")
        if status is not None and status not in ("PASS", "FAIL"):
            return VERIFICATION_INSUFFICIENT
        if finding.get("severity") in BLOCKING_FINDING_SEVERITIES:
            any_blocking_severity = True
        check = finding.get("check")
        if isinstance(check, str) and check:
            if observed_status_by_check.get(check) != "FAIL" and status is not None:
                observed_status_by_check[check] = status
        elif status == "FAIL":
            any_unattributed_failure = True

    if any_unattributed_failure:
        return VERIFICATION_FAILED
    if any(status == "FAIL" for status in observed_status_by_check.values()):
        return VERIFICATION_FAILED
    if any_blocking_severity:
        return VERIFICATION_FAILED
    if set(required_checks) - set(observed_status_by_check):
        return VERIFICATION_INSUFFICIENT
    return VERIFICATION_VERIFIED


def compose_bounded_technical_review_native_reuse_dispatch(
    *,
    grant: dict[str, Any],
    now: str,
    ledger_path: Path,
    transport: NativeReviewTransport,
    review_id: str,
) -> dict[str, Any]:
    """The one composed REUSE_NATIVE_ONLY route (Issue #109 comment 6019865174, PR #112
    comment 6019870622): import one already-fetched native GitHub review's own evidence as
    this delivery's Evidence-layer classification, with zero new model requests and zero local
    launch reservation.

    ```text
    validate-grant (pure)       -> evaluate_review_selection
    acquire+validate (trusted)  -> review_adapter.fetch_trusted_native_review_evidence
    relevance (pure)            -> review_selection.evaluate_native_review_relevance
    dedup/correlate (ledger)    -> review_control.read_native_review_import / record_...
    classify (real signals)     -> classify_native_review_result
    ```

    This function never calls :func:`claim_review_launch`, :func:`~manosube_agent_civilization.
    development_binding.review_adapter.launch_review_process`, :func:`record_dispatch_attempt`,
    or :func:`record_review_outcome` -- native reuse reserves no local concurrency slot and
    spends no local daily launch budget, ever (the design supplement's own "ネイティブ側の利用量
    と、Agent OSの起動上限を区別する" requirement; see :func:`~manosube_agent_civilization.
    development_binding.review_control.record_native_review_import`'s own docstring for how
    this relates to the existing local activation gate's own ``native_github_dedup_
    disposition`` field). This function itself makes no network call and requests no new model
    completion -- *transport* is the caller's own real GitHub API/MCP client (or, in this
    delivery's own tests, a controlled fake standing in for one).

    SR4-F3 correction (PR #112 comment 6032479337): before this correction, this function took
    a bare, caller-supplied ``native_evidence`` mapping directly through the shape-check-only
    :func:`~manosube_agent_civilization.development_binding.review_adapter.
    validate_native_review_evidence` -- the exact reproduced gap: a hand-typed, invented
    mapping (an obviously fabricated numeric ``review_id``, ``fetched_via="I_TYPED_THIS"``)
    satisfied every shape check and was fully imported and classified, with no acquisition
    this function could ever distinguish from a genuine one. Fixed: *transport* and
    *review_id* replace the raw evidence parameter entirely -- this function now requires
    :func:`~manosube_agent_civilization.development_binding.review_adapter.
    fetch_trusted_native_review_evidence` to actually call *transport* and cross-check its own
    returned (repository, pull_request, review_id) before anything is ever imported; a caller
    with no transport, only an already-typed mapping, can no longer reach this composed route
    at all -- that caller still has ``validate_native_review_evidence`` directly, a
    deliberately generic, directly-testable shape check, never itself this canonical route.

    A native review this delivery has already imported once (the identical content address,
    from :func:`~manosube_agent_civilization.development_binding.review_control.
    native_review_content_address`) is returned unchanged rather than re-processed --
    deduplication, never a second import of the identical evidence, and never a second local
    launch "to be sure" merely because the caller asked again (the design supplement's own
    "実行中・取得済みのレビューをWSLから重複起動しない" requirement).

    Every refusal stage below -- an inadmissible grant, an acquisition failure, or irrelevant
    native evidence (including the honestly-disclosed "inspected base unknown" case) -- is
    reported with its own reason codes, never silently advanced past, and this function never
    itself decides to fall back to a local launch, auto-adopt a result, or request a further
    review on its own initiative (the design supplement's own "不足は明記し、自動修正・自動採択・
    無断追加レビューへ進まない" requirement) -- that decision, if any, belongs entirely to this
    function's own caller.
    """

    selection_decision = evaluate_review_selection(grant, now=now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {"stage": "validate-grant", "decision": selection_decision}

    try:
        validated_evidence = fetch_trusted_native_review_evidence(
            transport,
            repository=grant["authorized_repository"],
            pull_request=grant["authorized_pull_request"],
            review_id=review_id,
        )
    except ReviewAdapterError as error:
        return {"stage": "native-acquisition", "error": str(error)}

    relevance_decision = evaluate_native_review_relevance(validated_evidence, grant=grant)
    if relevance_decision["decision"] != NATIVE_REVIEW_RELEVANT:
        return {"stage": "native-relevance", "decision": relevance_decision}

    # SR3-F3 correction (PR #112 comment 6030487245): identity_key is now computed *before*
    # the dedup lookup, and folded into the content address itself, so the lookup is
    # request-identity-aware -- a genuinely different requirement_id reusing byte-identical
    # native evidence never collides with, or returns, a different request's own cached
    # classification.
    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
    )
    content_address = native_review_content_address(validated_evidence, identity_key=identity_key)
    existing = read_native_review_import(
        ledger_path, content_address, repository=grant["authorized_repository"]
    )
    if existing is not None:
        return {
            "stage": "complete",
            "content_address": content_address,
            "classification": existing["classification"],
            "deduplicated": True,
            "native_evidence": validated_evidence,
        }

    classification = classify_native_review_result(
        validated_evidence, required_checks=grant["permitted_checks"]
    )
    record_native_review_import(
        ledger_path,
        content_address,
        repository=grant["authorized_repository"],
        identity_key=identity_key,
        classification=classification,
        now=now,
    )
    return {
        "stage": "complete",
        "content_address": content_address,
        "classification": classification,
        "deduplicated": False,
        "native_evidence": validated_evidence,
    }


def cmd_validate_grant(args: argparse.Namespace, stdout: TextIO) -> int:
    grant = _read_json(args.grant_file)
    decision = evaluate_review_selection(grant, now=args.now)
    _emit(stdout, decision)
    return 0 if decision["decision"] == REVIEW_SELECTION_ADMITTED else 1


def cmd_activation_gate(args: argparse.Namespace, stdout: TextIO) -> int:
    evidence = _read_json(args.evidence_file)
    decision = evaluate_activation_gate(evidence)
    _emit(stdout, decision)
    return 0 if decision["decision"] == "ACTIVATION_GATE_ACTIVATED" else 1


def cmd_claim(args: argparse.Namespace, stdout: TextIO) -> int:
    identity_key = compute_identity_key(
        repository=args.repository,
        pull_request=args.pull_request,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        requirement_id=args.requirement_id,
        input_digest=args.input_digest,
    )
    decision = claim_review_launch(
        args.ledger_file,
        identity_key=identity_key,
        work_unit_id=args.work_unit_id,
        repository=args.repository,
        now=args.now,
        numeric_limits=BOUNDED_REVIEW_NUMERIC_LIMITS,
    )
    _emit(stdout, decision)
    return 0 if decision["decision"] == REVIEW_CLAIM_ADMITTED else 1


def cmd_record_dispatch(args: argparse.Namespace, stdout: TextIO) -> int:
    record_dispatch_attempt(
        args.ledger_file,
        args.identity_key,
        repository=args.repository,
        acknowledged=args.acknowledged,
    )
    _emit(stdout, {"identity_key": args.identity_key, "acknowledged": args.acknowledged})
    return 0


def cmd_record_outcome(args: argparse.Namespace, stdout: TextIO) -> int:
    # SR4-F4 correction (PR #112 comment 6032479337): before this correction, this subcommand
    # called the generic, directly-testable :func:`~manosube_agent_civilization.
    # development_binding.review_control.record_review_outcome` primitive directly -- the one
    # real CLI effect this delivery's own outcome-recording surface could reach completely
    # bypassed any check that the result being recorded correlates to a real, owned, dispatched
    # operation. Fixed: this is now the claim-bound composed route's own one CLI caller,
    # mirroring the identical SR2-F5 fix already applied to ``cancel``.
    result_bytes = (
        args.result_bytes_file.read_bytes() if args.result_bytes_file is not None else None
    )
    decision = compose_bounded_technical_review_outcome_recording(
        ledger_path=args.ledger_file,
        identity_key=args.identity_key,
        repository=args.repository,
        status=args.status,
        resolution_kind=args.resolution_kind,
        pid=args.pid,
        owned_process_identity=args.owned_process_identity,
        result_bytes=result_bytes,
    )
    _emit(stdout, decision)
    return 0 if decision["decision"] == "OUTCOME_RECORDED" else 1


def cmd_cancel(args: argparse.Namespace, stdout: TextIO) -> int:
    # SR3-F4 correction (PR #112 comment 6030487245): before this correction, this subcommand
    # called the generic, directly-testable :func:`~manosube_agent_civilization.
    # development_binding.review_adapter.cancel_review_task` primitive directly -- the one
    # real CLI effect this delivery's own cancel surface could reach completely bypassed the
    # claim-bound composed route (:func:`compose_bounded_technical_review_cancellation`), so
    # "generic primitive available for tests only" mis-described what this subcommand
    # actually did. Fixed: this is now the composed route's own one CLI caller.
    decision = compose_bounded_technical_review_cancellation(
        ledger_path=args.ledger_file,
        identity_key=args.identity_key,
        repository=args.repository,
        pid=args.pid,
        owned_process_identity=args.owned_process_identity,
    )
    _emit(stdout, decision)
    return 0 if decision["decision"] == "CANCELLATION_CONFIRMED_LOCAL_ONLY" else 1


def cmd_dispatch(args: argparse.Namespace, stdout: TextIO) -> int:
    """Validate a grant, then evaluate the activation gate, and stop before ever claiming.

    F5 correction (PR #112 comment 6019024445): the activation gate is now checked *before*
    any claim is ever attempted -- the exact ordering bug the handoff names ("the composed
    dispatch flow reserving a claim/slot before checking activation eligibility"). This
    subcommand's own activation evidence always carries ``activation_enabled=False`` (see the
    module docstring), so the gate it reports is always ``ACTIVATION_GATE_NOT_ACTIVATED``, and
    this delivery's own CLI entry point therefore makes exactly zero ledger writes, ever,
    whatever the grant itself says -- never reserving a concurrency slot or a day's own launch
    budget for a request already guaranteed to go no further.

    F2 correction (PR #112 comment 6019024445): the full composed route past this point --
    authenticate, claim, input-stage/digest-verify, the one real dispatch, classification, and
    the ledger outcome -- now genuinely exists, as
    :func:`compose_bounded_technical_review_dispatch`. It is not reachable from this CLI
    subcommand, by design: ``REAL_CODEX_MODEL_REQUEST_ALLOWED=false`` for this whole delivery,
    and this script's own command-line surface is where that boundary is enforced, not merely
    stated. It is exercised directly, as a library call, by this delivery's own tests.
    """

    grant = _read_json(args.grant_file)
    selection_decision = evaluate_review_selection(grant, now=args.now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        _emit(stdout, {"stage": "validate-grant", "decision": selection_decision})
        return 1

    activation_evidence = {
        "auth_confirmed": bool(args.auth_confirmed),
        "cli_version": args.cli_version,
        "model": args.model,
        "allowance_confirmed_adequate": bool(args.allowance_confirmed_adequate),
        "auto_recharge_verified_disabled": bool(args.auto_recharge_verified_disabled),
        "native_github_dedup_disposition": args.native_github_dedup_disposition,
        "live_bounded_review_grant_admitted": selection_decision["decision"]
        == REVIEW_SELECTION_ADMITTED,
        # Never read from a flag -- see the module docstring. This is the one field this
        # script itself never lets a caller set True.
        "activation_enabled": False,
    }
    gate_decision = evaluate_activation_gate(activation_evidence)
    _emit(
        stdout,
        {
            "stage": "activation-gate",
            "decision": gate_decision,
            "real_launch_performed": False,
            "claim_attempted": False,
        },
    )
    return 0 if gate_decision["decision"] == "ACTIVATION_GATE_ACTIVATED" else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bounded_technical_review",
        description=(
            "Decision 0004 (Issue #109): invoke review_selection/review_control/"
            "review_adapter. Never performs a real Codex launch in this delivery."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_grant = subparsers.add_parser("validate-grant", help="Evaluate a Bounded Review Grant")
    validate_grant.add_argument("grant_file", type=Path)
    validate_grant.add_argument("--now", required=True)
    validate_grant.set_defaults(handler=cmd_validate_grant)

    activation_gate = subparsers.add_parser(
        "activation-gate", help="Evaluate the activation/spending gate"
    )
    activation_gate.add_argument("evidence_file", type=Path)
    activation_gate.set_defaults(handler=cmd_activation_gate)

    claim = subparsers.add_parser("claim", help="Atomically claim one review launch identity")
    claim.add_argument("ledger_file", type=Path)
    claim.add_argument("--repository", required=True)
    claim.add_argument("--pull-request", required=True, dest="pull_request")
    claim.add_argument("--base-sha", required=True, dest="base_sha")
    claim.add_argument("--head-sha", required=True, dest="head_sha")
    claim.add_argument("--requirement-id", required=True, dest="requirement_id")
    claim.add_argument("--input-digest", required=True, dest="input_digest")
    claim.add_argument("--work-unit-id", required=True, dest="work_unit_id")
    claim.add_argument("--now", required=True)
    claim.set_defaults(handler=cmd_claim)

    record_dispatch = subparsers.add_parser(
        "record-dispatch", help="Record one dispatch attempt against an existing claim"
    )
    record_dispatch.add_argument("ledger_file", type=Path)
    record_dispatch.add_argument("identity_key")
    record_dispatch.add_argument("--repository", required=True)
    record_dispatch.add_argument("--acknowledged", action="store_true")
    record_dispatch.set_defaults(handler=cmd_record_dispatch)

    record_outcome = subparsers.add_parser(
        "record-outcome", help="Record the final outcome of a dispatched review"
    )
    record_outcome.add_argument("ledger_file", type=Path)
    record_outcome.add_argument("identity_key")
    record_outcome.add_argument("pid", type=int)
    record_outcome.add_argument("owned_process_identity")
    record_outcome.add_argument("--repository", required=True)
    record_outcome.add_argument("--status", required=True, choices=["COMPLETED", "FAILED"])
    record_outcome.add_argument(
        "--resolution-kind",
        dest="resolution_kind",
        required=True,
        choices=[RESOLUTION_KIND_COLLECTED_RESULT, RESOLUTION_KIND_CONFIRMED_CANCELLATION],
    )
    # SR3-F4 correction (PR #112 comment 6030487245): a caller-asserted digest string is never
    # accepted here -- see `record_review_outcome`'s own docstring. This CLI surface instead
    # takes the path to the real collected-result file whose bytes the ledger itself digests.
    record_outcome.add_argument(
        "--result-bytes-file", dest="result_bytes_file", type=Path, default=None
    )
    record_outcome.set_defaults(handler=cmd_record_outcome)

    cancel = subparsers.add_parser("cancel", help="Cancel the owned review process group")
    cancel.add_argument("ledger_file", type=Path)
    cancel.add_argument("identity_key")
    cancel.add_argument("pid", type=int)
    cancel.add_argument("owned_process_identity")
    cancel.add_argument("--repository", required=True)
    cancel.set_defaults(handler=cmd_cancel)

    dispatch = subparsers.add_parser(
        "dispatch",
        help="Validate a grant, claim, and evaluate activation -- never launches a review",
    )
    dispatch.add_argument("grant_file", type=Path)
    dispatch.add_argument("ledger_file", type=Path)
    dispatch.add_argument("--now", required=True)
    dispatch.add_argument("--auth-confirmed", action="store_true", dest="auth_confirmed")
    dispatch.add_argument("--cli-version", default="", dest="cli_version")
    dispatch.add_argument("--model", default="", dest="model")
    dispatch.add_argument(
        "--allowance-confirmed-adequate", action="store_true", dest="allowance_confirmed_adequate"
    )
    dispatch.add_argument(
        "--auto-recharge-verified-disabled",
        action="store_true",
        dest="auto_recharge_verified_disabled",
    )
    dispatch.add_argument(
        "--native-github-dedup-disposition",
        default="UNRESOLVED",
        dest="native_github_dedup_disposition",
    )
    dispatch.set_defaults(handler=cmd_dispatch)

    return parser


def main(argv: list[str] | None = None, *, stdout: TextIO = sys.stdout) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return handler(args, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
