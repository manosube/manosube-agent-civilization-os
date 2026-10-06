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
    launch_review_process,
    parse_structured_review_output,
    prepare_inspection_workspace,
    validate_native_review_evidence,
)
from manosube_agent_civilization.development_binding.review_control import (
    RESOLUTION_KIND_COLLECTED_RESULT,
    REVIEW_CLAIM_ADMITTED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    claim_review_launch,
    compute_identity_key,
    evaluate_activation_gate,
    native_review_content_address,
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

    review_status = codex_result.get("review_status")
    inspected_paths = codex_result.get("inspected_paths")
    findings = codex_result.get("findings")
    if review_status == "UNAVAILABLE":
        return VERIFICATION_UNAVAILABLE, codex_result
    if not isinstance(inspected_paths, list) or not isinstance(findings, list):
        return VERIFICATION_INSUFFICIENT, codex_result
    if not set(permitted_paths) <= set(inspected_paths):
        return VERIFICATION_INSUFFICIENT, codex_result
    if review_status == "COMPLETED":
        return VERIFICATION_VERIFIED, codex_result
    if review_status == "FAILED":
        return VERIFICATION_FAILED, codex_result
    return VERIFICATION_INSUFFICIENT, codex_result


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
) -> dict[str, Any]:
    """The one composed Bounded Technical Review dispatch route (PR #112 comment 6019024445,
    F2), in the exact order F5's own correction requires:

    ```text
    validate-grant (pure)   -> evaluate_review_selection
    activation-gate (pure)  -> evaluate_activation_gate              -- before any claim, F5
    authenticate (Boot/Authority/Store) -> authenticate_bounded_review_grant               -- F1
    claim (durable ledger)  -> claim_review_launch
    input-stage+digest-verify -> prepare_inspection_workspace + digest_inspection_input
    dispatch (external effect) -> launch_review_process, exactly once
    classify (real signals) -> classify_review_result
    record-outcome (durable ledger) -> record_review_outcome
    ```

    Every stage before ``claim`` performs zero ledger writes -- an ineligible or unauthenticated
    request never reserves the repository's one concurrency slot or a day's own launch budget
    (the exact ordering bug F5 corrects). A digest mismatch discovered *after* claiming releases
    the slot via :func:`~manosube_agent_civilization.development_binding.review_control.
    release_unsent_claim` rather than recording a false outcome; a launch that raises before any
    process is ever started (every :class:`~manosube_agent_civilization.development_binding.
    errors.ReviewAdapterError` :func:`~manosube_agent_civilization.development_binding.
    review_adapter.launch_review_process` itself raises is a *pre*-launch refusal, per that
    function's own contract) releases it identically, for the identical reason: nothing was
    ever sent. Only a launch that genuinely started a process ever reaches
    :func:`~manosube_agent_civilization.development_binding.review_control.
    record_dispatch_attempt`, and only once, ever, for this identity.

    This function performs the one real :mod:`.review_adapter` launch this delivery's own
    composed route can ever make; it never itself constructs a Kernel ``VerificationResult`` or
    calls ``run_independent_verification``/``route_verification_result_to_evidence`` -- that
    handoff belongs to the caller, exactly as the existing integration test (``tests/
    integration/binding/test_bounded_technical_review_route.py``) already demonstrates by hand,
    so this module never becomes a second owner of Evidence construction.

    *build_argv*, when given, replaces :func:`~manosube_agent_civilization.development_binding.
    review_adapter.build_codex_review_argv`'s own fixed real-CLI argv with an explicit
    ``Callable[[Path], Sequence[str]]`` over the prepared workspace -- the one seam this
    delivery's own tests use to exercise this entire composed route end to end against a
    controlled local fake executable, never the real Codex CLI
    (``REAL_CODEX_MODEL_REQUEST_ALLOWED=false``, identical to every other :mod:`.
    review_adapter` test in this delivery). Production/CLI callers never pass it.
    """

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

        if build_argv is None:
            argv = build_codex_review_argv(
                codex_executable=codex_executable, workspace=workspace, prompt_path=prompt_path
            )
        else:
            argv = list(build_argv(workspace))
        env = build_subprocess_environment(orchestrator_env)

        try:
            launch_result = launch_review_process(
                argv,
                cwd=workspace,
                env=env,
                max_seconds=BOUNDED_REVIEW_NUMERIC_LIMITS["max_process_seconds"],
                max_output_bytes=BOUNDED_REVIEW_NUMERIC_LIMITS["max_result_bytes"],
                clock=clock,
                mask_paths=mask_paths,
            )
        except ReviewAdapterError as error:
            # Every ReviewAdapterError launch_review_process itself raises is a *pre*-launch
            # refusal (its own contract) -- no process was ever started, so this identity's one
            # permitted send was reserved, never attempted. Release it rather than recording a
            # dispatch this module cannot honestly claim happened.
            release_unsent_claim(
                ledger_path, identity_key, repository=grant["authorized_repository"]
            )
            return {"stage": "dispatch", "identity_key": identity_key, "error": str(error)}

        record_dispatch_attempt(
            ledger_path,
            identity_key,
            repository=grant["authorized_repository"],
            acknowledged=True,
            pid=launch_result.pid,
            process_identity=launch_result.process_identity,
        )

        classification, codex_result = classify_review_result(
            launch_result, permitted_paths=grant["permitted_paths"]
        )
        ledger_status = (
            STATUS_COMPLETED if classification == VERIFICATION_VERIFIED else STATUS_FAILED
        )
        record_review_outcome(
            ledger_path,
            identity_key,
            repository=grant["authorized_repository"],
            status=ledger_status,
            resolution_kind=RESOLUTION_KIND_COLLECTED_RESULT,
            result_digest=hashlib.sha256(launch_result.stdout).hexdigest(),
        )
        return {
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
    finally:
        cleanup_inspection_workspace(workspace)


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
