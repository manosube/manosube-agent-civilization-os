"""The one script Decision 0004 (Issue #109) authorizes to invoke the bounded-technical-review
owners -- :mod:`manosube_agent_civilization.development_binding.review_selection`,
``.review_control``, and ``.review_adapter`` -- and the only place this delivery composes them
into a sequence. It introduces no second admission route: every decision below is answered by
calling one of those three owners, never by re-deriving their logic here.

```text
validate-grant    -> review_selection.evaluate_review_selection            (pure, offline)
claim             -> review_control.claim_review_launch                   (durable ledger)
record-dispatch   -> review_control.record_dispatch_attempt               (durable ledger)
record-outcome    -> review_control.record_review_outcome                 (durable ledger)
activation-gate   -> review_control.evaluate_activation_gate              (pure, offline)
cancel            -> review_adapter.cancel_review_task                   (external effect)
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
    build_codex_review_argv,
    build_subprocess_environment,
    cancel_review_task,
    cleanup_inspection_workspace,
    collect_review_process_result,
    parse_structured_review_output,
    prepare_inspection_workspace,
    process_identity_token,
    spawn_review_process,
    validate_native_review_evidence,
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
    evaluate_native_review_relevance,
    evaluate_review_selection,
)

#: SR2-F2 correction (PR #112 comment 6021757577): the ratified ceiling on how large the
#: staged inspection input a bounded review ever launches against may be -- checked after
#: :func:`~manosube_agent_civilization.development_binding.review_adapter.
#: prepare_inspection_workspace` stages it and before any process is ever started. Distinct
#: from ``max_result_bytes`` (the launched process's own captured output ceiling, already
#: enforced by :mod:`.review_adapter`): this is an input-side ceiling this script itself owns.
MAX_INSPECTION_INPUT_BYTES = 1024 * 1024

#: SR2-F2 correction: the closed set of per-finding severities that keep a ``COMPLETED``
#: native or local review result from ever being reported :data:`VERIFICATION_VERIFIED` --
#: reproduced gap: a result carrying a P1/blocking finding, with ``review_status ==
#: "COMPLETED"``, was previously reported VERIFIED purely because the classifier never read
#: ``findings`` at all once ``review_status`` itself looked clean.
BLOCKING_FINDING_SEVERITIES = frozenset({"P1", "BLOCKING", "CRITICAL"})

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


def measure_inspection_input_bytes(workspace: Path) -> int:
    """Return the total staged byte size of every file under *workspace* (SR2-F2, PR #112
    comment 6021757577) -- checked by :func:`compose_bounded_technical_review_dispatch`
    against :data:`MAX_INSPECTION_INPUT_BYTES` before any process is ever started. Before this
    correction nothing in this script's own composed route ever bounded how large the staged
    inspection input itself could grow; only the launched process's own *captured output* was
    ever capped.
    """

    return sum(path.stat().st_size for path in workspace.rglob("*") if path.is_file())


def classify_review_result(
    launch_result: Any, *, permitted_paths: Sequence[str]
) -> tuple[str, dict[str, Any]]:
    """Return the Evidence-layer classification for one real launch's own bounded outcome --
    never a bare ``review_status == "COMPLETED"`` string match (PR #112 comment 6019024445,
    F2), but several independent, genuine structured signals checked together: the process
    group's own exit status and whether it was killed at the deadline (never trusted from the
    reviewed subprocess's own self-report), whether its parsed structured output names a real
    completion at all, and whether what it claims to have inspected actually covers *every*
    path the grant permitted -- partial coverage is :data:`VERIFICATION_INSUFFICIENT`, never a
    silent pass.

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
    if review_status == "COMPLETED":
        # SR2-F2 correction: a bare ``review_status == "COMPLETED"`` was never, by itself,
        # proof that nothing blocking was found -- reproduced gap: a result carrying a P1
        # finding, with ``review_status`` still reporting ``COMPLETED``, was returned VERIFIED
        # because this classifier never read ``findings``' own severities at all.
        for finding in findings:
            severity = finding.get("severity") if isinstance(finding, dict) else None
            if severity in BLOCKING_FINDING_SEVERITIES:
                return VERIFICATION_FAILED, codex_result
        return VERIFICATION_VERIFIED, codex_result
    return VERIFICATION_INSUFFICIENT, codex_result


def _recheck_live_authorization(
    *,
    grant: Mapping[str, Any],
    now_provider: Callable[[], str],
    activation_evidence_provider: Callable[[], Mapping[str, Any]],
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

    This never widens :func:`~manosube_agent_civilization.development_binding.review_selection.
    authenticate_bounded_review_grant`'s own *permitted_boundary* argument to carry
    repository/PR/base/head/digest fields: that argument is compared for exact equality
    (``authority/verifier_selection.py``'s own ``grant["permitted_boundary"] != permitted_
    boundary`` check) against a Human-Authority-signed ``verifier_selection_grant`` record this
    delivery never mints and cannot widen the shape of -- doing so would refuse every real
    grant SHUKOU has already signed, not strengthen this check. The exact-envelope binding SR2-
    F1 asks for instead lives in *grant_provider*: when given, this function re-reads the grant
    fresh and refuses outright if its own ``authorized_repository``/``authorized_pull_request``/
    ``authorized_base_sha``/``authorized_head_sha``/``requirement_id``/``input_digest`` no
    longer match the snapshot this call started from -- the grant's full identity envelope,
    checked for having silently changed underneath an in-flight request, never merely assumed
    static because it was read once.
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

    fresh_now = now_provider()
    selection_decision = evaluate_review_selection(grant, now=fresh_now)
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
    max_input_bytes: int = MAX_INSPECTION_INPUT_BYTES,
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

    SR2-F2 correction: *max_input_bytes* bounds the staged inspection input itself (distinct
    from the launched process's own captured-output ceiling, already enforced by
    :mod:`.review_adapter`); :func:`classify_review_result` itself now also refuses a truncated
    capture and an over-scope inspected path, and checks finding severities rather than trusting
    a bare ``review_status`` string. *evidence_handoff*, when given, is a mapping with exactly
    ``verification_requirement``/``verifier_selection``/``evidence_request`` keys -- this route
    then performs the one real :mod:`~manosube_agent_civilization.independent_verification`
    handoff itself (wrapping this call's own already-collected classification/``codex_result``
    as the one real verifier outcome), rather than leaving every caller to hand-assemble the
    identical sequence (as this delivery's own integration test previously had to). This route
    still never *fabricates* ``target_refs``, ``selection_authority_ref``, or an
    ``evidence_request`` -- those must already be genuine, Store-backed context only the caller
    can supply; when *evidence_handoff* is omitted, this route stops at the ledger outcome
    exactly as before, and the caller is free to perform that handoff itself.

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

    now_provider = now_provider or (lambda: now)
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
    permitted_boundary = {
        "permitted_paths": list(grant["permitted_paths"]),
        "permitted_checks": list(grant["permitted_checks"]),
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
            store=store,
            project_id=project_id,
            project_binding_id=project_binding_id,
            verifier_identity=verifier_identity,
            permitted_boundary=permitted_boundary,
            verifier_selection_grant_refs=verifier_selection_grant_refs,
            human_grant_declaration_refs=human_grant_declaration_refs,
            grant_provider=grant_provider,
        )

    workspace = prepare_inspection_workspace(source_root, permitted_paths=grant["permitted_paths"])
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

        staged_bytes = measure_inspection_input_bytes(workspace)
        if staged_bytes > max_input_bytes:
            release_unsent_claim(
                ledger_path, identity_key, repository=grant["authorized_repository"]
            )
            return {
                "stage": "input-size-cap",
                "identity_key": identity_key,
                "staged_bytes": staged_bytes,
                "max_input_bytes": max_input_bytes,
            }

        try:
            validate_review_launch_preconditions(
                max_seconds=BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"],
                max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
                mask_paths=mask_paths,
                require_isolation=True,
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

        if build_argv is None:
            argv = build_codex_review_argv(
                codex_executable=codex_executable, workspace=workspace, prompt_path=prompt_path
            )
        else:
            argv = list(build_argv(workspace))
        env = build_subprocess_environment(orchestrator_env)

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
            argv, cwd=workspace, env=env, mask_paths=mask_paths, require_isolation=True
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
            launch_result, permitted_paths=grant["permitted_paths"]
        )
        result_digest = hashlib.sha256(launch_result.stdout).hexdigest()

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
                result_digest=result_digest,
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
            result_digest=result_digest,
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

    *verifier_selection_grant_refs*/*human_grant_declaration_refs* default to the identical
    refs the Bounded Review's own admission already used, but *evidence_handoff* may override
    either with its own ``verifier_selection_grant_refs``/``human_grant_declaration_refs`` keys
    -- a real Bounded Review Grant's own ``permitted_boundary`` (``{"permitted_paths": [...],
    "permitted_checks": [...]}``) is never JSON-canonicalizable once it round-trips through a
    :class:`~manosube_agent_civilization.independent_verification.types.VerifierSelection`'s
    own immutable tuple-freezing (:mod:`~manosube_agent_civilization.state.canonicalize`
    accepts only ``list``, never ``tuple``, for a JSON array) -- a caller whose
    ``verifier_selection`` carries that exact shape must authorize it through a *different*,
    list-free-boundary grant (e.g. the ``{"scope": ..., "boundary_id": ...}`` convention
    :mod:`~manosube_agent_civilization.independent_verification` itself already uses), never
    through the Bounded Review Grant's own refs.
    """

    from manosube_agent_civilization.independent_verification.evidence_handoff import (
        route_verification_result_to_evidence,
    )
    from manosube_agent_civilization.independent_verification.route import (
        run_independent_verification,
    )
    from manosube_agent_civilization.independent_verification.types import VerifierSelection

    verifier_selection_grant_refs = evidence_handoff.get(
        "verifier_selection_grant_refs", verifier_selection_grant_refs
    )
    human_grant_declaration_refs = evidence_handoff.get(
        "human_grant_declaration_refs", human_grant_declaration_refs
    )
    verifier_selection = evidence_handoff["verifier_selection"]
    if not isinstance(verifier_selection, VerifierSelection):
        raise TypeError(
            f"evidence_handoff['verifier_selection'] must be a VerifierSelection instance, "
            f"not {type(verifier_selection)!r}"
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
        verification_requirement=evidence_handoff["verification_requirement"],
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
    RESOLUTION_KIND_CONFIRMED_CANCELLATION`, ``result_digest=None`` -- a cancellation never
    collects a result to digest), releasing the concurrency slot for a different identity,
    exactly as a genuine review outcome would.
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

    record_review_outcome(
        ledger_path,
        identity_key,
        repository=repository,
        status=STATUS_FAILED,
        resolution_kind=RESOLUTION_KIND_CONFIRMED_CANCELLATION,
        result_digest=None,
    )
    return {
        "stage": "complete",
        "decision": "CANCELLATION_CONFIRMED",
        "identity_key": identity_key,
        "local_process_group_terminated": outcome.local_process_group_terminated,
        "provider_server_state": outcome.provider_server_state,
    }


# --------------------------------------------------------------------------- #
# REUSE_NATIVE_ONLY supplement (Issue #109 comment 6019865174, PR #112 comment 6019870622).
# --------------------------------------------------------------------------- #


def classify_native_review_result(native_evidence: Mapping[str, Any]) -> str:
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
    """

    review_state = native_evidence["review_state"]
    if review_state in ("PENDING", "DISMISSED"):
        return VERIFICATION_UNAVAILABLE
    if review_state == "CHANGES_REQUESTED":
        return VERIFICATION_FAILED
    if review_state == "APPROVED":
        return VERIFICATION_VERIFIED
    return VERIFICATION_INSUFFICIENT


def compose_bounded_technical_review_native_reuse_dispatch(
    *,
    grant: dict[str, Any],
    now: str,
    ledger_path: Path,
    native_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """The one composed REUSE_NATIVE_ONLY route (Issue #109 comment 6019865174, PR #112
    comment 6019870622): import one already-fetched native GitHub review's own evidence as
    this delivery's Evidence-layer classification, with zero new model requests and zero local
    launch reservation.

    ```text
    validate-grant (pure)       -> evaluate_review_selection
    validate-evidence (pure)    -> review_adapter.validate_native_review_evidence
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
    disposition`` field). *native_evidence* is never fetched by this function itself -- it is
    whatever the caller already independently retrieved; this function performs no network
    call and requests no new model completion.

    A native review this delivery has already imported once (the identical content address,
    from :func:`~manosube_agent_civilization.development_binding.review_control.
    native_review_content_address`) is returned unchanged rather than re-processed --
    deduplication, never a second import of the identical evidence, and never a second local
    launch "to be sure" merely because the caller asked again (the design supplement's own
    "実行中・取得済みのレビューをWSLから重複起動しない" requirement).

    Every refusal stage below -- an inadmissible grant, unreadable native evidence, or
    irrelevant native evidence (including the honestly-disclosed "inspected base unknown"
    case) -- is reported with its own reason codes, never silently advanced past, and this
    function never itself decides to fall back to a local launch, auto-adopt a result, or
    request a further review on its own initiative (the design supplement's own "不足は明記し、
    自動修正・自動採択・無断追加レビューへ進まない" requirement) -- that decision, if any,
    belongs entirely to this function's own caller.
    """

    selection_decision = evaluate_review_selection(grant, now=now)
    if selection_decision["decision"] != REVIEW_SELECTION_ADMITTED:
        return {"stage": "validate-grant", "decision": selection_decision}

    validated_evidence = validate_native_review_evidence(native_evidence)

    relevance_decision = evaluate_native_review_relevance(validated_evidence, grant=grant)
    if relevance_decision["decision"] != NATIVE_REVIEW_RELEVANT:
        return {"stage": "native-relevance", "decision": relevance_decision}

    content_address = native_review_content_address(validated_evidence)
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

    classification = classify_native_review_result(validated_evidence)
    identity_key = compute_identity_key(
        repository=grant["authorized_repository"],
        pull_request=grant["authorized_pull_request"],
        base_sha=grant["authorized_base_sha"],
        head_sha=grant["authorized_head_sha"],
        requirement_id=grant["requirement_id"],
        input_digest=grant["input_digest"],
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
    record_review_outcome(
        args.ledger_file,
        args.identity_key,
        repository=args.repository,
        status=args.status,
        result_digest=args.result_digest,
    )
    _emit(stdout, {"identity_key": args.identity_key, "status": args.status})
    return 0


def cmd_cancel(args: argparse.Namespace, stdout: TextIO) -> int:
    outcome: CancellationOutcome = cancel_review_task(
        pid=args.pid, owned_process_identity=args.owned_process_identity
    )
    _emit(
        stdout,
        {
            "ownership_confirmed": outcome.ownership_confirmed,
            "local_process_group_terminated": outcome.local_process_group_terminated,
            "provider_server_state": outcome.provider_server_state,
        },
    )
    return 0


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
    record_outcome.add_argument("--repository", required=True)
    record_outcome.add_argument("--status", required=True, choices=["COMPLETED", "FAILED"])
    record_outcome.add_argument("--result-digest", dest="result_digest", default=None)
    record_outcome.set_defaults(handler=cmd_record_outcome)

    cancel = subparsers.add_parser("cancel", help="Cancel the owned review process group")
    cancel.add_argument("pid", type=int)
    cancel.add_argument("owned_process_identity")
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
