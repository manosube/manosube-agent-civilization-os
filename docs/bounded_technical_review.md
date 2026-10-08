# Bounded Codex technical review (Decision 0004, Issue #109)

```text
DOC_TYPE=OPERATOR_GUIDE
GOVERNING_ISSUE=#109
GOVERNING_DECISION=HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0004
ADOPTION_ID=ADOPT_I109_BOUNDED_WSL_CODEX_TECHNICAL_REVIEW_20261006
ACTIVATION_DEFAULT=false
REAL_CODEX_MODEL_REQUEST_ALLOWED=false
```

## 1. What this is, and what it is not

Codex is a bounded, non-default-active **technical reviewer**. It is never an implementer,
never a structural reviewer, never a final-acceptance or merge authority, and the native
GitHub automatic-review route this repository already prohibits
(`automated_review_trigger_allowed=false`) remains prohibited exactly as it was before this
decision. This decision opens exactly one additional, narrowly admitted route: a specific,
mechanically bounded review request, gated by a Human-ratified grant this repository's own
code independently checks before any external effect.

See `docs/decisions/ADR-0032-BOUNDED_TECHNICAL_REVIEW_IS_NOT_ACCEPTANCE.md` for why this does
not reopen the failure `docs/decisions/ADR-0028-CAPABILITY_NEUTRALITY_WITHOUT_SELECTION_IS_
UNBOUND.md` records.

## 2. The three owners

```text
review_selection   pure, offline admission -- is this exact Bounded Review Grant internally
                   consistent, unexpired, unrevoked, scoped to the exact repository/PR/base/
                   head/requirement/environment it claims
review_control     the durable, file-locked claim/budget ledger -- one launch per identity
                   forever, one concurrent review per repository, a JST-day launch ceiling,
                   restart-safe unknown-acknowledgement handling, and the activation/
                   spending gate
review_adapter     the one external-effect owner -- bounded process launch, credential-
                   isolated environment construction, a read-only inspection workspace,
                   process-group-aware cancellation
```

`scripts/bounded_technical_review.py` is the one script this decision authorizes to invoke
them; it introduces no second admission route.

## 3. The Bounded Review Grant

A grant (`development_binding.review_selection.evaluate_review_selection`) binds, together:
repository, pull request, base/head SHA, Difference, work unit, requirement, the
implementation provider and its session reference, the inspector (`CODEX`) and its session
reference, the permitted inspection paths and check categories, the exact environment
fingerprint (CLI version, model, auth method, provider, reasoning effort), the input digest,
and a validity window -- plus a read-back receipt binding every one of those fields again, and
a live `current_*` scope compared against the `authorized_*` scope so a stale head or a scope
substitution is refused rather than silently accepted.

A grant's own `decision_status=RATIFIED`, `authority=SHUKOU`, or mere presence never
authenticates it by itself -- every field above is independently checked, and the environment
fingerprint must match `review_selection.SUPPORTED_ENVIRONMENT_FINGERPRINT` exactly:

```text
cli_version      = 0.160.1
model            = GPT-6.1-Sol
auth_method      = CHATGPT_LOGIN
provider         = OPENAI
reasoning_effort = low
```

A grant naming a different CLI version, model, or configuration is refused
(`ENVIRONMENT_FINGERPRINT_UNSUPPORTED`) rather than silently routed to a different provider or
model. This is this delivery's own best-effort pin against the one configuration SHUKOU's own
terminal evidence observed (Issue #109 handoff, comment 6017544351); it has not been
independently re-validated against a live CLI invocation in this delivery.

## 4. The numeric ceiling (ratified, never caller-widenable)

```text
max_concurrent_reviews_per_repository = 1
max_launches_per_jst_day              = 4
max_process_seconds                   = 1800   (30 minutes)
max_poll_window_seconds               = 28800  (8 hours)
poll_interval_seconds                 = 60
max_input_bytes                       = 1048576  (1 MiB)
max_result_bytes                      = 1048576  (1 MiB)
automatic_retries_allowed             = 0
additional_spending_ceiling           = 0
```

Held as code (`development_binding.policy.BOUNDED_REVIEW_NUMERIC_LIMITS`), pinned against the
JSON artifact the identical way every other ratified value in this policy is. `review_control`
refuses outright (`ReviewControlError`) if ever handed a numeric-limits mapping that is not
exactly this one -- a caller cannot narrow or widen the ceiling by passing a different value
in.

A failed or unacknowledged launch counts exactly as a completed one against the one-per-
identity rule: `review_control`'s ledger never removes a claim once recorded, so a retry at
the identical identity is refused forever, including after a controller restart (the claim is
file-backed, not held only in a process's own memory).

## 5. The activation / spending gate

Runtime starts disabled (`bounded_review_activation_default=false`, pinned). Before any real
external launch could ever be attempted, `review_control.evaluate_activation_gate` requires
every one of:

```text
auth_confirmed                       = true
cli_version                          = the pinned, supported value
model                                = the pinned, supported value
allowance_confirmed_adequate         = true
auto_recharge_verified_disabled      = true
native_github_dedup_disposition      = DISABLED | NOT_APPLICABLE
live_bounded_review_grant_admitted   = true
activation_enabled                   = true
```

Any missing, unknown, or unsatisfied field refuses the whole gate -- there is no partial
activation and no default-to-pass for an unobserved field. **In this delivery,
`scripts/bounded_technical_review.py` hardcodes `activation_enabled=False` on every evidence
mapping it builds.** No flag, environment variable, or file this script reads can set it to
`True`. A live launch requires a separately authorized change this delivery does not contain.

## 6. What remains genuinely unverified

```text
SHUKOU_ACCOUNT_AUTO_RECHARGE_DISPOSITION_VERIFIED=false
NATIVE_GITHUB_AUTOMATIC_REVIEW_SETTING_VERIFIED=false
CODEX_CLI_FLAG_SET_INDEPENDENTLY_VALIDATED_AGAINST_REAL_CLI=false
```

SHUKOU's own terminal evidence (Issue #109 handoff, comment 6017544351) established the CLI
version, auth method, and that a usage allowance was displayed at a point in time. It did not
establish that automatic credit reload is disabled going forward, or that native GitHub's own
automatic-review setting is off. A balance display is not evidence that reload is disabled.
This delivery's own activation gate exists precisely so that absence of that confirmation
yields zero launch rather than an assumed pass.

## 7. Local-background-server cancellation, honestly

The observed Codex CLI (0.160.1) runs a local background server. Killing only the foreground
process `review_adapter.launch_review_process` started is not proof the review stopped --
`review_adapter.cancel_review_task` accordingly reports two separate facts, never one:

```text
local_process_group_terminated   -- whether THIS call's own owned process group is confirmed
                                     gone (reaping it if it is this process's own child; a
                                     kill-probe fallback otherwise)
provider_server_state             -- always "UNAVAILABLE" in this delivery; this module never
                                      calls a provider cancellation API and never claims a
                                      stronger confirmation than it actually has
```

A detached background child that outlives the foreground process this module started is
never claimed to be stopped. `tests/integration/binding/test_bounded_technical_review_route.py`
proves this exact scenario against a controlled local fake executable.

## 8. Credential and inspection boundaries

`review_adapter.build_subprocess_environment` is an allowlist, never a denylist: a reviewing
subprocess receives only the environment variable names a caller explicitly names, and a name
that is itself credential-shaped (`TOKEN`/`SECRET`/`KEY`/`PASSWORD`/`CREDENTIAL`/`AUTH`
appearing in it) is refused even if a caller tries to allow it. No repository write token or
production credential is ever named in this delivery's own allowlists.

`review_adapter.prepare_inspection_workspace` copies only a grant's own `permitted_paths` --
never the whole checkout -- into a fresh temporary directory, and marks every copied file
read-only (`chmod 0o444`) before returning it. This protection assumes the reviewing process
runs as a regular, non-root user, exactly as the intended deployment (a normal account in
SHUKOU's own WSL Ubuntu environment) does; a root-owned reviewing process can bypass a file
mode entirely, and this delivery's own test suite discloses that limitation rather than
hiding it (`test_the_inspection_workspace_is_genuinely_read_only` skips the write-bypass
assertion specifically when running as root, while still asserting the mode bit itself is
set).

## 9. Evidence handoff

A completed Codex review's own structured result is carried, unmodified, through the
existing, provider-neutral `run_independent_verification` and `route_verification_result_to_
evidence` routes (`manosube_agent_civilization.independent_verification`) -- neither route is
edited by this decision, and neither a new Kernel record type nor a second Evidence owner is
introduced. A canonical `VerificationResult` is distinct from a merely derived, file-persisted
Evidence record, which is itself distinct from an actual Store commit, which is itself
distinct from Human adoption and Closure -- this decision preserves every one of those
distinctions rather than collapsing any of them. Genuine Boot/Project Binding/Human Grant
Declaration admission remains required for the heavy route;
`tests/integration/binding/test_bounded_technical_review_route.py` proves it end to end over a
real, Store-bound fixture Project, never a shortcut.

## 10. What a live trial still requires

```text
REPOSITORY_IMPLEMENTATION_START_AUTHORIZED=true   (this delivery)
LIVE_REVIEW_CONTROLLER_START_ALLOWED=false
REAL_CODEX_MODEL_REQUEST_ALLOWED=false
```

This delivery implements and tests the control plane with activation off. A later, separately
authorized work unit -- after independent structural review of this integration, and after the
still-unverified account/native-setting preconditions in §6 are genuinely confirmed -- is
required before any real Codex launch may occur.

## 11. Structural Review Round 1 correction (PR #112 comment 6019024445)

Five P1 findings and one P2 finding, adopted in full
(`ADOPT_I109_PR112_SR1_F1_F5_E1_20261007`):

```text
F1  review_adapter.launch_review_process carried no admission guard of its own -- fixed by
    review_selection.authenticate_bounded_review_grant, a new, separate, authenticated layer
    reusing the existing Boot/Authority/Store owners (boot_project, authority.
    evaluate_verifier_selection, Store-resolved verifier_selection_grant/human_grant_
    declaration) -- the identical pattern `independent_verification.route` already uses. No
    new Kernel record type: CODEX's review scope is encoded entirely through the existing
    verifier_identity/permitted_boundary fields. review_selection.evaluate_review_selection
    itself is unchanged -- it stays the pure, offline, internal-consistency check it always
    was.
F2  No single composed dispatch route existed -- fixed by `scripts/bounded_technical_review.
    py`'s own compose_bounded_technical_review_dispatch: authenticate -> claim -> input-stage/
    digest-verify -> the one real dispatch -> a real structured-signal result classifier
    (never a bare `review_status` string match) -> the ledger outcome. Not reachable from
    this script's own CLI surface -- REAL_CODEX_MODEL_REQUEST_ALLOWED=false still holds for
    every way this script is actually invoked; this delivery's own tests call it directly.
F3  review_adapter.launch_review_process's deadline was only enforced while a stdout/stderr
    pipe stayed open, and its output cap was two independent per-stream budgets rather than
    one combined one; cancel_review_task took a bare PID with no ownership proof. Fixed: a
    post-loop deadline-bounded wait closes the pipe-closed-but-alive-child gap, one shared
    output-byte budget replaces the two, and cancel_review_task now requires a process-
    identity token captured at launch (`/proc/<pid>/stat` starttime) and refuses to signal
    anything on a mismatch.
F4  An environment allowlist and a chmod 0o444 workspace are both reversible by the identical
    same-UID subprocess they restrain -- neither is genuine isolation. Fixed: a real Linux
    mount+user namespace (`unshare`) masks the configured paths with empty, mode-000 tmpfs
    mounts, with a mandatory empirical negative-control probe before every launch
    (`check_isolation_capability`) -- a safe refusal, never a silent fallback to the weaker
    boundary, when the mechanism cannot be confirmed working.
F5  The ledger allowed a second dispatch against an already-dispatched claim, accepted an
    arbitrary caller-asserted outcome status with no declared evidence kind, and the composed
    flow reserved a claim before checking activation eligibility. Fixed: `record_dispatch_
    attempt` is now a strict one-way CLAIMED -> {DISPATCHED|ACK_UNKNOWN} transition;
    `record_review_outcome` requires a closed-set `resolution_kind` (`COLLECTED_RESULT` /
    `CONFIRMED_CANCELLATION`); `release_unsent_claim` frees the concurrency slot for a claim
    whose one permitted send was reserved but never attempted; and the CLI's own `dispatch`
    subcommand now checks the activation gate *before* ever claiming, so a disabled delivery
    (every CLI invocation, in this delivery) makes zero ledger writes.
E1  Three test files outside the original 22-path inventory were touched without a prior
    explicit scope supplement -- retroactively authorized by this same adoption (25-path
    maximum), recorded here honestly rather than as pre-authorized.
```

## 12. REUSE_NATIVE_ONLY (Issue #109 comment 6019865174, PR #112 comment 6019870622)

A second composed mode, distinct from the local-launch route above and never active by
default: import one already-fetched native GitHub review's own evidence (immutable
`review_id`, `reviewed_commit_sha`, `review_state`, `inspected_paths`, `findings`) as this
delivery's Evidence-layer classification, with **zero new model requests and zero local
launch reservation**.

```text
review_adapter.validate_native_review_evidence        trusted, read-only evidence shape check
review_selection.evaluate_native_review_relevance      admission/relevance (pure, offline)
review_control.{native_review_content_address,
                 record_native_review_import,
                 read_native_review_import}            dedup/correlation, over the existing
                                                        ledger file's own `native_imports`
scripts.bounded_technical_review.
    compose_bounded_technical_review_native_reuse_dispatch   composes all three
```

An inspected base this native evidence never named (`reviewed_commit_sha=null`) is refused as
`NATIVE_REVIEWED_BASE_UNKNOWN` -- distinct from, and never conflated with, a confirmed-stale
base (`NATIVE_REVIEWED_BASE_STALE`); neither is ever fabricated as "probably current." A
native completion signal, or an empty `findings` list, is never by itself `VERIFIED` -- only
`review_state == "APPROVED"` maps there; `"COMMENTED"` maps to `INSUFFICIENT`, honestly
reporting that the native review itself never reached an affirmative disposition. A running
native review (`"PENDING"`) maps to `UNAVAILABLE` and never triggers a local launch on this
account. This route never calls `claim_review_launch`, `launch_review_process`,
`record_dispatch_attempt`, or `record_review_outcome` -- it reserves no local concurrency slot
and spends no local daily launch budget, ever; the existing local activation gate's own
`native_github_dedup_disposition` field (§5) remains the separate, existing hook for a caller
to declare that native coverage was checked before any local launch is even attempted. An
identical native review (by content address) re-imported a second time is deduplicated, never
reprocessed or relaunched.

## 13. Structural Review Round 2 correction (PR #112 comment 6021757577)

Six P1 findings and one P2 finding, adopted in full
(`ADOPT_I109_PR112_SR2_F1_F6_E1_20261007`):

```text
F1  No live re-check of trusted clock/kill-switch/activation immediately before the one
    external-effect send and before its result was ever accepted; raw launch_review_process
    took no admission guard of its own. Fixed: compose_bounded_technical_review_dispatch now
    calls a new _recheck_live_authorization helper at two further checkpoints -- immediately
    before the send (while the claim is still releasably CLAIMED) and immediately before the
    collected result is accepted -- re-running evaluate_review_selection/evaluate_activation_
    gate/authenticate_bounded_review_grant fresh against caller-suppliable now_provider/
    activation_evidence_provider/grant_provider callables, rather than against a static string
    read once at the top of the call. permitted_boundary itself is never widened to carry the
    full repository/PR/base/head/digest envelope: that field is compared for exact equality
    against a Human-Authority-signed verifier_selection_grant this delivery never mints, and
    widening it would refuse every real grant SHUKOU has already signed, not strengthen the
    check; grant_provider's own envelope re-check (authorized_repository/pull_request/base_
    sha/head_sha/requirement_id/input_digest) covers that ground instead.
F2  classify_review_result ignored stdout_truncated/stderr_truncated and finding severity, no
    enforced input-staging cap existed, and the composed route never performed a real Evidence
    handoff itself. Fixed: classify_review_result now reports INSUFFICIENT on any truncated
    capture or over-scope inspected_paths, and FAILED on a COMPLETED result whose own findings
    carry a P1/BLOCKING/CRITICAL severity; measure_inspection_input_bytes enforces a new
    MAX_INSPECTION_INPUT_BYTES (1 MiB) ceiling on the staged input before any process starts;
    and compose_bounded_technical_review_dispatch's own new evidence_handoff parameter, when
    given, performs the real run_independent_verification/route_verification_result_to_
    evidence chain itself (never fabricating target_refs/selection_authority_ref/evidence_
    request, which must already be genuine caller-supplied, Store-backed context).
F3  validate_native_review_evidence was a pure shape check with no inspected-base concept
    distinct from the reviewed head, and native_review_content_address hashed only provider/
    repository/review_id/reviewed_commit_sha -- a review_state transition (e.g. APPROVED ->
    CHANGES_REQUESTED, with new findings) on the identical review_id returned the stale cached
    classification. Fixed: a new, separate required inspected_base_sha field (checked against
    the grant's own authorized_base_sha, with the identical UNKNOWN/STALE distinction already
    used for the head) and a revision-aware content address folding in review_state and a
    digest of findings, so a real transition always content-addresses as a genuinely new
    record. This module's own "zero network calls, ever" design boundary is unchanged --
    cryptographic source authentication is out of scope for a route that by design never
    fetches anything itself.
F4  record_dispatch_attempt(acknowledged=True) was called only after launch_review_process
    fully returned -- a crash during the up-to-30-minute collection wait left a CLAIMED record
    indistinguishable from "never sent", releasable via release_unsent_claim even though a real
    process might still be running; record_review_outcome accepted COLLECTED_RESULT with
    result_digest=None. Fixed: review_adapter.launch_review_process is now a thin composition
    of validate_review_launch_preconditions (pre-Popen refusal checks) / spawn_review_process
    (the one Popen call, returns immediately) / collect_review_process_result (the long wait on
    an already-started process); the composed route calls record_dispatch_attempt(acknowledged
    =False) immediately after every pre-launch refusal has already passed and before
    spawn_review_process is ever called, then confirm_dispatch_sent with the real pid the
    instant spawn_review_process returns -- before the collection wait begins. record_review_
    outcome now requires a real 64-character lowercase hex result_digest whenever resolution_
    kind is COLLECTED_RESULT, and requires it absent whenever CONFIRMED_CANCELLATION.
F5  cancel_review_task treated a bare caller-supplied pid + process_identity match as
    sufficient ownership -- reproduced by starting an unrelated harmless subprocess entirely
    outside this delivery's own ledger/adapter, reading its own real process_identity_token
    directly, and cancelling it this way with ownership_confirmed=True. Fixed: a new
    compose_bounded_technical_review_cancellation is the one canonical cancellation route --
    it first requires identity_key to name a real ledger claim, DISPATCHED or ACK_UNKNOWN,
    whose own recorded pid/process_identity (set only by confirm_dispatch_sent/record_
    dispatch_attempt for a process this delivery's own composed dispatch route actually
    started) exactly matches the caller-supplied ones, before cancel_review_task is ever
    reached. The generic cancel_review_task/launch_review_process primitives remain callable
    directly for this delivery's own tests -- never themselves the canonical route, identical
    in spirit to how the CLI's own `dispatch` subcommand never reaches compose_bounded_
    technical_review_dispatch.
F6  The isolation capability probe tested only one sentinel path, never the launched namespace's
    own ability to undo its own protections: a namespace-"root" child retains CAP_SYS_ADMIN
    within its own namespace (can unmount/remount its own masks), a chmod-0444 file remains
    unlink-and-replace-able by its owning UID, there was no network isolation, and mask_paths
    silently defaulted to an empty tuple. Fixed: build_isolated_argv now self-bind-mounts and
    remounts the workspace read-only, execs through `setpriv --bounding-set=-all --inh-caps=
    -all --no-new-privs` (capability-dropping, since uid-dropping fails inside a `--map-root-
    user` single-entry uid map), and adds a full network namespace (`unshare --net`);
    check_isolation_capability's own probe now tests all four properties together and reports
    unavailable on any failure; validate_review_launch_preconditions refuses outright when
    require_isolation is true but mask_paths is empty -- an empty mask was never evidence of
    isolation, only of nothing being masked.
E1  The verification suite cited in the prior round's own PR body omitted tests/contract/
    independent_verification and tests/integration/independent_verification; this round's own
    verification explicitly includes both (see this document's own revision history / the PR
    body). No append-only correction/verification history had been added to the two
    project_sources documents before this round; both now carry one.
```

## 14. Structural Review Round 3 correction (PR #112 comment 6030487245)

Five P1 findings and one E1, adopted in full (`ADOPT_I109_PR112_SR3_F1_F5_E1_20261007`, same
PR/branch, 25-path maximum inventory; adoption/handoff independently re-verified via GitHub
API — author `manosube`/OWNER, `AUTHORIZED_START_HEAD=EXPECTED_HEAD_SHA=
bab627cb2a4827f22f9b64e70c188fe4fbc7da32`, matching the pushed HEAD exactly):

```text
F1  _recheck_live_authorization's optional grant_provider compared two caller-controlled
    snapshots that could both agree on an envelope never actually authorized, now_provider/
    activation_evidence_provider defaulted to echoing the original static literals rather than
    reading anything live, and permitted_boundary never authenticated the complete envelope --
    only the inspection scope -- through the existing signed-grant Authority mechanism. The
    public spawn_review_process also performed no admission check of its own. Fixed:
    permitted_boundary is now built entirely from scalar SHA-256 digests (review_selection.
    canonical_list_digest, compute_launch_envelope_digest) over the complete launch envelope
    (repository/PR/base/head/digest/window/provenance/environment fingerprint), checked by
    Authority's own existing exact-equality grant comparison -- never a new Kernel record type;
    compose_bounded_technical_review_dispatch's own now_provider now defaults to a genuine wall-
    clock reader (_default_live_now); and spawn_review_process now requires a one-shot admission
    token only validate_review_launch_preconditions can mint, closing the public-surface bypass.
F2  classify_review_result's severity allowlist omitted P0, a FAILED finding with no severity
    at all still reported VERIFIED, and a COMPLETED result with zero findings for any permitted
    check was accepted as "nothing failed" rather than refused as "nothing observed";
    max_input_bytes was enforced post-hoc against the whole staged bundle, as a caller-
    widenable parameter; the Evidence handoff's own _constant_verifier performed no correlation
    check that the handoff's own requirement/scope actually named the identical launch this
    route just inspected. Fixed: every finding must now declare a real PASS/FAIL status and
    every permitted_checks entry must have at least one finding reporting on it, by name, or
    the result is INSUFFICIENT; prepare_inspection_workspace now enforces the ratified
    max_input_bytes ceiling per-file, before staging, with no caller-widenable parameter at
    all; _hand_off_to_evidence now requires the handoff's own VerificationRequirement/
    VerifierSelection to name the identical (requirement_id, permitted_boundary) this exact
    launch inspected, raising outright on any mismatch.
F3  validate_native_review_evidence accepted an invented, non-numeric review_id and an invalid
    submitted_at; classify_native_review_result mapped APPROVED directly to VERIFIED with no
    check of findings/conditions at all; native_review_content_address omitted request/
    requirement identity entirely, so a different requirement_id reusing identical native
    evidence returned a stale cached classification. Fixed: review_id must match GitHub's own
    numeric id shape and submitted_at must parse as a real timestamp; a new fetched_via
    disclosure field is required; a new NativeReviewTransport protocol plus
    fetch_trusted_native_review_evidence gives a caller with a genuine GitHub client one real,
    cross-checked acquisition seam (never implemented by this module, never a network call this
    module itself makes); classify_native_review_result now fails on any FAIL-status or
    blocking-severity finding even when APPROVED; native_review_content_address now folds in
    the requesting grant's own identity_key, so a genuinely different request never reuses
    another request's cached classification.
F4  record_review_outcome required digest *shape* but never digest *correlation* -- any well-
    formed 64-character hex string satisfied COLLECTED_RESULT, including one with zero actual
    collected bytes behind it; compose_bounded_technical_review_cancellation checked only
    ownership_confirmed, never local_process_group_terminated; the raw cancel_review_task
    confirmation loop probed only the process-group leader's own pid, never the group as a
    whole; the CLI's own cmd_cancel subcommand called the raw cancel_review_task primitive
    directly, bypassing the claim-bound composed cancellation route entirely. Fixed:
    record_review_outcome no longer accepts a caller-supplied digest at all -- it accepts the
    real result_bytes and computes the one digest it ever records from them directly;
    compose_bounded_technical_review_cancellation now requires local_process_group_terminated
    in addition to ownership_confirmed; cancel_review_task's confirmation loop now probes
    os.killpg(pgid, 0) -- the whole group's own existence -- rather than a single pid; cmd_cancel
    now routes through compose_bounded_technical_review_cancellation, the one canonical route.
F5  The read-only-remounted copied workspace plus capability drop established no out-of-scope
    filesystem boundary at all -- the orchestrator's own source checkout, other same-UID files,
    and ancestor instruction/hook paths remained fully readable/writable from inside a launched
    process, and validate_review_launch_preconditions required only that mask_paths be non-
    empty, never that it actually covered any sensitive root. Fixed: validate_review_launch_
    preconditions now takes required_mask_roots and refuses outright unless every declared root
    is actually covered by mask_paths -- an allowlist-of-covered-roots boundary over the
    identical real, kernel-enforced tmpfs-mask mechanism, never a filesystem-wide root-remount;
    compose_bounded_technical_review_dispatch now declares source_root and HOME as its own
    required_mask_roots. The residual risk that anything outside the declared roots remains
    reachable is disclosed, not papered over, exactly as F4 (SR1)'s own disclosure already is.
E1  The PR body and this document's own §13 E1 entry mis-described Round 1's own verification:
    they claimed the omitted suite was tests/contract/independent_verification and tests/
    integration/independent_verification -- false; the PR body's own SR1_FULL_SUITE line
    already listed both as run, with a 3407-passed result, in Round 1 itself. The actually-
    omitted suite the SR2 handoff named was a unit-level independent_verification suite; no
    such directory (`tests/unit/independent_verification`) exists anywhere in this repository
    -- disclosed here rather than fabricated or silently skipped. The real, existing suite that
    *was* run in Round 1's own SR1_FULL_SUITE but silently dropped from Round 2's own
    SR2_TARGETED_SUITE, and never re-confirmed since, is tests/contract/governance; it is run
    fresh as part of this round's own verification (§99.5 carries the result).
```

Eighteen new permanent regression tests were added to `tests/integration/binding/
test_bounded_technical_review_route.py` (SR3-F1×2, SR3-F2×5, SR3-F3×6, SR3-F4×3, SR3-F5×2)
and two to `tests/unit/binding/test_bounded_technical_review_control.py` (SR3-F4×2, the
digest-correlation fix), each reproducing the exact finding's own counterexample and proving
it now refused/fixed.

## 15. Structural Review Round 4 correction (PR #112 comment 6032479337)

Five P1 findings, adopted (`ADOPT_I109_PR112_SR4_F1_F5_20261007`, same PR/branch, identical
25-path maximum inventory; the prior round's own E1 (a withdrawn, erroneous "nonexistent
`tests/unit/independent_verification`" demand) explicitly excluded from this round's adopted
findings; adoption/handoff independently re-verified via GitHub API — author `manosube`/OWNER,
`AUTHORIZED_START_HEAD=EXPECTED_HEAD_SHA=5a33e4b58aa3dd008a48ccf4e476d6bffddba8f9`, matching
the pushed HEAD exactly):

```text
F1  _recheck_live_authorization still evaluated the grant's own static current_* fields --
    never genuinely refreshed from anywhere live -- and the SR3-F1 admission token was a bare
    set-membership marker, not bound to the exact validated argv/cwd/mask_paths/
    require_isolation configuration: a token minted for require_isolation=False was consumed
    by spawn_review_process under an independently-supplied, different configuration. Fixed: a
    new LiveReviewStateTransport protocol plus fetch_trusted_live_review_state gives
    _recheck_live_authorization a genuine live reader (cross-checked repository/pull_request,
    outright refusal on kill_switch_engaged), building a freshly-merged grant snapshot before
    evaluate_review_selection ever runs; the admission token now maps to a SHA-256
    _operation_fingerprint of the exact argv/cwd/mask_paths/require_isolation validated, and
    spawn_review_process recomputes and compares that same fingerprint before consuming it.
F2  classify_review_result's observed_status_by_check[check] = status let a later PASS
    overwrite an earlier FAIL for the identical check; a FAIL finding with no recognized check
    name was silently dropped; a positive COMPLETED+PASS shape returned VERIFIED with zero
    correlation to the actual launch's own input digest; prepare_inspection_workspace checked
    stat().st_size then called unbounded shutil.copyfile -- a TOCTOU race where the real bytes
    copied could exceed the ceiling the pre-copy stat() had approved. Fixed: a FAIL recorded
    for a check is never superseded by a later PASS for that same check, and an unattributed
    FAIL now fails the whole result unconditionally; classify_review_result requires a new
    expected_input_digest parameter and refuses unless the result's own observed_input_digest
    matches it; prepare_inspection_workspace no longer calls stat() or shutil.copyfile at all --
    it reads in bounded 65536-byte chunks, refusing the instant the running total of
    genuinely-read bytes exceeds the ceiling, closing the race entirely.
F3  compose_bounded_technical_review_native_reuse_dispatch never called the existing
    NativeReviewTransport/fetch_trusted_native_review_evidence trusted-acquisition seam -- it
    still accepted a bare caller-supplied native_evidence mapping directly through the shape-
    only validator, so a hand-typed numeric review_id with fetched_via="I_TYPED_THIS" and
    APPROVED/findings=[] was still fully VERIFIED with zero transport call; classify_native_
    review_result had no required-check/condition parameter at all. Fixed: native_evidence is
    no longer an accepted parameter -- the function now requires transport/review_id and calls
    fetch_trusted_native_review_evidence itself, catching any ReviewAdapterError as a reported
    native-acquisition-stage refusal; classify_native_review_result now requires
    required_checks, with the identical monotonic/unattributed-failure coverage logic F2 added.
F4  record_review_outcome's own SHA-256-of-result_bytes (the SR3-F4 fix) closed caller-digest
    substitution but never terminal-operation correlation -- the CLI's own cmd_record_outcome
    subcommand called that generic ledger primitive directly, so an ACK_UNKNOWN claim (no real
    pid ever confirmed) could be resolved FAILED/COLLECTED_RESULT with an arbitrary, invented
    result_bytes, releasing the concurrency slot for a different identity with zero
    correlation to anything actually collected; compose_bounded_technical_review_cancellation's
    own local_process_group_terminated requirement still let a controlled fixture with
    provider_server_state=UNAVAILABLE (local termination confirmed) reach the unqualified
    decision "CANCELLATION_CONFIRMED", overclaiming across two facts the adapter itself never
    conflates. Fixed: a new compose_bounded_technical_review_outcome_recording route requires
    caller-supplied pid/owned_process_identity to exactly match the claim's own recorded launch
    identity before record_review_outcome is ever reached -- mirroring cancel's identical
    check -- and cmd_record_outcome now routes through it exclusively; a claim with no
    confirmed pid can never be resolved this way at all. The cancellation success decision is
    now "CANCELLATION_CONFIRMED_LOCAL_ONLY", never the unqualified string, honestly scoped to
    what this route can ever actually confirm.
F5  The now-required source_root/HOME mask coverage (SR3-F5 fix) was a real improvement, but
    validate_review_launch_preconditions still permitted an empty required_mask_roots on its
    public surface -- require_isolation=True with a non-empty but entirely unrelated mask_
    paths (or required_mask_roots simply omitted) was fully admitted, with no check that
    anything sensitive was ever declared. Fixed: require_isolation=True with an empty
    required_mask_roots is now refused outright, independent of mask_paths -- every genuinely
    isolated launch must explicitly declare at least one root it relies on mask_paths to
    cover, structurally, never merely by a caller's own convention. This remains an allowlist-
    of-declared-roots boundary, never a filesystem-wide remount; the residual risk already
    disclosed for F5 (SR3) is unchanged, only the one declaration it depends on can no longer
    be silently absent.
```

Twenty-two new permanent regression tests were added to `tests/integration/binding/
test_bounded_technical_review_route.py` (SR4-F1×4, SR4-F2×5, SR4-F3×7, SR4-F4×4, SR4-F5×2),
each reproducing the exact finding's own counterexample and proving it now refused/fixed.
Three pre-existing tests whose own assumptions no longer held given F3's acquisition-before-
relevance ordering and F4's cancellation-decision rename were updated to match the corrected
behavior they already exercised (`test_native_reuse_an_irrelevant_review_is_refused_before_
any_classification`'s repository/pull-request-mismatch cases split into their own test now
asserting the `native-acquisition` stage; `test_native_reuse_unreadable_evidence_raises_
rather_than_silently_proceeding` now asserts the reported refusal dict rather than an
uncaught exception; the two `CANCELLATION_CONFIRMED` assertions now read
`CANCELLATION_CONFIRMED_LOCAL_ONLY`).

## 16. Structural Review Round 5 correction (PR #112 comment 6034603745)

Five P1 findings, adopted (`ADOPT_I109_PR112_SR5_F1_F5_20261007`, same PR/branch, identical
25-path maximum inventory; framed by the reviewer as an SR4 completion check -- unfinished
portions of the already-adopted SR4 scope, never new architecture; adoption/handoff
independently re-verified via GitHub API -- author `manosube`/OWNER, `AUTHORIZED_START_HEAD=
EXPECTED_HEAD_SHA=a265892a6e82dbdeafb7fe88566c54e2f549cb58`, matching the pushed HEAD exactly):

```text
F1  fetch_trusted_live_review_state required only repository/pull_request/base/head/kill-
    switch -- no PR-readiness state or observation-freshness field at all, and _recheck_live_
    authorization never inspected either. Matching SHAs with the live PR already pr_draft=True
    or pr_state="closed", or an observed_at from 1900, all reached evaluate_review_selection
    unrefused. Fixed: the transport must now also report pr_state/pr_draft/observed_at (shape-
    checked by fetch_trusted_live_review_state itself); _recheck_live_authorization refuses
    outright on a live PR that is no longer open or still a draft (LIVE_PR_NOT_READY), and on
    an observation older -- or, symmetrically, impossibly newer -- than a new ratified
    max_live_state_observation_age_seconds=300 ceiling (LIVE_STATE_OBSERVATION_STALE), checked
    fresh against now_provider's own real clock at this exact instant.
F2  classify_review_result correlated observed_input_digest, but a COMPLETED/exit-0 result
    with only inspected_paths+digest+a bare PASS still returned VERIFIED with no attempt/
    requirement identity, inspector/implementation provenance, observation time, or actual-
    procedure evidence at all -- correlation to the launch's own identity was never the same
    thing as correlation to what the launch's own caller already knows. Fixed: the function
    now requires identity_key/requirement_id/inspector_identity/launch_started_at/launch_
    ended_at, attaching them as a new correlated_launch field on every return path (VERIFIED,
    FAILED, and INSUFFICIENT alike); each finding must also report a non-empty procedure
    string, or the result is INSUFFICIENT. Fixed in the same pass: compose_bounded_technical_
    review_dispatch's own clock parameter defaulted to time.monotonic -- a float -- despite
    ReviewLaunchResult.started_at/ended_at being documented and typed as wall-clock str; every
    test omitted clock=, so this was always latent, surfacing only once correlated_launch's own
    observed_window began flowing those values into Evidence's schema, which prohibits floats.
    The default is now _default_live_now, matching the contract these fields always had.
F3  fetch_trusted_native_review_evidence's required schema carried no author/app/source-URL/
    read-back-revision/current-observation contract at all -- only repository/pull_request/
    review_id were cross-checked after shape validation. A fake transport with matching ids/
    base/head, submitted_at=1900-01-01, and fetched_via="I_TYPED_THIS" still reached complete/
    VERIFIED. Separately, the composed native route ended at record_native_review_import plus
    bare classification -- it never called the existing canonical run_independent_verification/
    Evidence handoff the local dispatch route already performs. Fixed: native review evidence
    now also requires source_url/author/fetched_at (shape-checked, source_url further cross-
    checked by fetch_trusted_native_review_evidence against the requested repository/pull_
    request); compose_bounded_technical_review_native_reuse_dispatch checks fetched_at's own
    freshness against now using the identical ratified max_live_state_observation_age_seconds
    ceiling F1 introduced -- deliberately never checking submitted_at's own age, since a native
    review submitted long ago is never itself refused merely for being old, only a stale re-
    fetch of it is -- and now accepts the identical optional evidence_handoff/store/project_id/
    project_binding_id/verifier_selection_grant_refs/human_grant_declaration_refs/
    permitted_boundary parameters the local dispatch route already does, calling the existing,
    unmodified _hand_off_to_evidence with the native evidence itself as codex_result.
F4  compose_bounded_technical_review_cancellation, with ownership_confirmed=True, local_
    process_group_terminated=True, provider_server_state=UNAVAILABLE, still called record_
    review_outcome -- resolving the claim and releasing the repository's one concurrency slot
    for a different identity, even though UNAVAILABLE is this delivery's own permanent, never-
    anything-else report of the provider/server-side task's own state. SR4-F4's own rename to
    "CANCELLATION_CONFIRMED_LOCAL_ONLY" was an honest label on an outcome that still silently
    released the slot -- never itself the adopted fix, as the independent review named
    directly: the adopted requirement was retention of the slot while provider/task state is
    unknown, not merely an honestly-renamed label. Separately, compose_bounded_technical_
    review_outcome_recording accepted any caller-asserted result_bytes once pid/
    owned_process_identity merely matched the claim's own recorded launch identity -- that
    equality proves this caller once legitimately observed the launch, never that the process
    has actually terminated or that the bytes were genuinely collected from it. Fixed: a
    confirmed local cancellation now calls a new record_local_cancellation_confirmed instead --
    the claim's own status/resolution_kind and active_lock are left completely untouched (the
    returned decision string is unchanged; the result also now carries
    concurrency_slot_retained=True) -- and compose_bounded_technical_review_outcome_recording
    now additionally re-reads process_identity_token for pid, fresh, at this exact instant,
    refusing (PROCESS_STILL_RUNNING) whenever it still exactly matches owned_process_identity.
    A retained claim is never permanently stuck: once the owned process is genuinely, freshly
    confirmed gone, outcome-recording still resolves it and releases the slot -- the one out-
    of-band path this module's own design already establishes for an otherwise-stuck claim.
F5  build_isolated_argv only ever mounted tmpfs over caller-selected mask_paths and remounted
    the staging workspace read-only -- the rest of the inherited host filesystem, including the
    independent review's own named example ("same-UID files elsewhere in /tmp or /var/tmp"),
    remained fully readable/writable from inside a launched process regardless of what mask_
    paths happened to contain; SR4-F5's non-empty-required_mask_roots fix closed the empty-list
    bypass, never this separate, broader incomplete-allowlist gap. Fixed: a new default_
    sensitive_mask_roots() enumerates same-UID roots this module itself always treats as in
    scope -- independent of any caller's own declaration -- and build_isolated_argv now always
    gives each of them a fresh, empty, writable tmpfs (distinct from mask_paths's own mode-000
    fully-inaccessible mount), ordered after workspace_path's own bind-mount so a workspace
    nested under one of these roots remains its own, already-established, visible mount. This
    set deliberately covers /var/tmp and XDG_RUNTIME_DIR, both unconditionally and in full --
    nothing in this delivery's own code or tests ever places anything needed by a launch under
    either of them, so neither carries the collateral-damage risk the platform temp directory
    itself does (this delivery's own staged inspection workspace, and its own test fixtures'
    controlled fake executables, are created there); closing that half of the reproduction
    correctly requires the launch's own legitimately-needed paths to first be consolidated
    under one caller-declared, explicitly preserved root, tracked as further, not-yet-delivered
    work, never silently assumed solved here. check_isolation_capability's own real-child probe
    now also plants a sentinel under /var/tmp and confirms it is genuinely invisible, refusing
    the launch outright (the identical existing capability.available check) in any environment
    where this cannot be confirmed -- never silently falling back to a weaker, merely-disclosed
    boundary.
```

Eighteen new permanent regression tests were added to `tests/integration/binding/
test_bounded_technical_review_route.py` (SR5-F1×4, SR5-F2×3, SR5-F3×6, SR5-F4×3, SR5-F5×2),
each reproducing the exact finding's own counterexample and proving it now refused/fixed.
Pre-existing tests whose own assumptions no longer held given F1's new live-state fields, F2's
new `classify_review_result` parameters, F3's new native-evidence fields, and F4's cancellation-
retention behavior were mechanically updated to match the corrected behavior they already
exercised (`_FakeLiveReviewStateTransport`/the inline mismatched-pull-request transport now
report `pr_state`/`pr_draft`/`observed_at`; all seven direct `classify_review_result` call
sites now pass the five new correlation kwargs, with a `procedure` field added to every finding
whose own test does not already fail at an earlier check; `_native_evidence`'s default fixture
now reports `source_url`/`author`/`fetched_at`; the two cancellation tests that previously
asserted a resolved `STATUS_FAILED`/`RESOLUTION_KIND_CONFIRMED_CANCELLATION` claim now assert
the claim remains `STATUS_DISPATCHED`/unresolved with `local_cancellation_confirmed_at` set).

## 17. Structural Review Round 6 correction (PR #112 comment 6036263982)

Four P1 findings, adopted (`ADOPT_I109_PR112_SR6_F1_F4_20261007`, same PR/branch, identical
25-path maximum inventory; framed by the reviewer as an SR5 completion check -- remaining
portions of the already-adopted SR5 scope, never new owners or a wider mechanism;
adoption/handoff independently re-verified via GitHub API -- author `manosube`/OWNER,
`REVIEWED_COMMIT_SHA`/`AUTHORIZED_START_HEAD`/`EXPECTED_HEAD_SHA` all exactly matching the
pushed HEAD `6d4aca7457b1aaca202d7fe39efb6c5949aafa5a`):

```text
F1  validate_review_launch_preconditions/spawn_review_process, called with the identical
    argv/cwd/mask_paths/require_isolation=False configuration at both validation and spawn --
    not substitution, a real matching configuration -- launched a genuine harmless local
    subprocess (HARMLESS_NO_AUTHORITY, exit 0) with zero selection/Authority/activation/claim
    check at all. SR5-F1's own docstring had characterized this as "by design, not a gap this
    function could close" -- the review named this exact claim as itself the gap. Fixed: both
    functions now require two new real Decision dicts, authentication_decision/claim_decision,
    checked for genuine REVIEW_SELECTION_ADMITTED/REVIEW_CLAIM_ADMITTED -- duplicated by value
    (never by import of review_selection/review_control), mirroring the existing
    NATIVE_REVIEW_PROVIDER precedent. This is structural, not cryptographic, protection,
    identical in kind to _operation_fingerprint's own existing admission-token mechanism; the
    one real composed route already has both decision objects in scope at its own call site,
    so no new plumbing was needed there.
F2  fetch_trusted_native_review_evidence's source_url cross-check was a bare substring test
    (expected_source_fragment in source_url) -- a different origin entirely
    (https://example.invalid/...) and a pull request number that merely begins with the
    requested one (109999 vs 109, since "/pull/109" is a substring of "/pull/109999") both
    passed. Separately, author was required only to be non-empty -- any value, including a
    genuinely unrelated account, satisfied it. Fixed: a real urlparse-based check now requires
    scheme="https", netloc="github.com", and an exact (never prefix) [owner, repo, "pull",
    number] path-segment match; a new required expected_author parameter is cross-checked by
    exact equality, sourced from the grant's own already-declared inspector_session_ref --
    never an invented bot/app identity constant.
F3  compose_bounded_technical_review_outcome_recording refused only when
    process_identity_token(pid) == owned_process_identity (still running) -- once absent or
    mismatched, whether the process exited naturally or was itself the subject of SR5-F4's own
    confirmed local-only cancellation retention, any caller-supplied result_bytes was accepted
    through to record_review_outcome, bypassing retention entirely. Reproduced: after a local-
    only cancellation (slot retained, provider_server_state=UNAVAILABLE), the matching ledger
    pid/token now absent let through an invented, never-collected result_bytes, releasing the
    slot for a new identity with the provider/task's own state still genuinely unknown. Local
    process absence is not correlated collected-result evidence and not provider terminal
    confirmation. Fixed: a claim this ledger ever recorded a confirmed local-only cancellation
    for (claim["local_cancellation_confirmed_at"] is not None) can now never be resolved
    through this route at all, regardless of pid/owned_process_identity or the SR5-F4 fresh-
    liveness recheck -- permanent through this path, the identical "deliberately stuck...
    resolvable only by a kill switch or a Human revocation acting through some other, out-of-
    band means" disposition this function's own SR4-F4 correction already applies to a claim
    with no confirmed pid at all. This supersedes this delivery's own prior SR5-F4 test premise
    that a retained claim could still eventually be resolved through this route once the
    process was confirmed dead.
F4  default_sensitive_mask_roots (SR5-F5) deliberately excluded the platform temp directory,
    named in its own docstring as "further, not-yet-delivered work" -- no longer acceptable as
    "correction complete." A successful /var/tmp sentinel proof was never itself proof of a
    *complete* filesystem boundary: unrelated same-UID content elsewhere under the platform
    temp directory remained fully reachable from inside a real local launch. Consolidating
    workspace/prompt/executable under one explicitly preserved root (the reviewer's first
    option) was not delivered this round; instead, compose_bounded_technical_review_dispatch --
    the one real composed route that could ever reach a genuine local launch referencing all
    three -- now refuses that launch outright, before send ("local-dispatch-boundary"/
    "INCOMPLETE_FILESYSTEM_BOUNDARY"), whenever build_argv is omitted (the only way this route
    ever reaches a real launch at all; every existing/production caller already omits it, so
    no caller's observed behavior changes). This is the reviewer's second, explicitly
    sanctioned option: treat the incomplete local boundary as unavailable and refuse local
    dispatch, rather than silently launching under a weaker boundary. An operator who needs a
    review performed today uses the already-delivered REUSE_NATIVE_ONLY path instead, on their
    own initiative -- this route never auto-launches a native review as a substitute.
```

Four new permanent regression tests were added to `tests/integration/binding/
test_bounded_technical_review_route.py` (SR6-F1×2, SR6-F2×5, SR6-F3×2, SR6-F4×1), each
reproducing the exact finding's own counterexample and proving it now refused/fixed.
Pre-existing tests whose own call sites reached the newly-required parameters were
mechanically updated (`authentication_decision`/`claim_decision` added to every
`validate_review_launch_preconditions`/`launch_review_process` call; `expected_author` added to
every direct `fetch_trusted_native_review_evidence` call, with `_native_evidence`'s default
fixture author now matching `_native_reuse_grant`'s `inspector_session_ref`); the one pre-
existing SR5-F4 test asserting a retained claim could still be resolved out-of-band once the
owned process was confirmed dead now asserts the identical scenario is refused
(`CLAIM_RETAINED_UNKNOWN_STATE`) instead, matching F3's corrected, permanent-retention
behavior.

## 18. Structural Review Round 7 correction (PR #112 comment 6037312445)

Three P1 findings, adopted (`ADOPT_I109_PR112_SR7_F1_F3_20261008`, same PR/branch, identical
25-path maximum inventory; framed by the reviewer as an SR6 completion check — remaining
portions of the already-adopted SR6 scope, never new owners or a wider mechanism; formal
adoption recorded directly by SHUKOU in a ChatGPT session (not an independent AI adoption) —
adoption/handoff independently re-verified via GitHub API, author `manosube`/OWNER,
`REVIEWED_COMMIT_SHA`/`AUTHORIZED_START_HEAD`/`EXPECTED_HEAD_SHA` all exactly matching the
pushed HEAD `3243a268fd7f53562b2a9bea3b332f3a19ba7a66`):

```text
F1  SR6-F1's own authentication_decision/claim_decision parameters raised the bar from "zero
    context required" to "two caller-constructed dicts required" -- the independent review
    reproduced that bar being no bar at all: authentication_decision={"decision":
    "REVIEW_SELECTION_ADMITTED"}, claim_decision={"decision": "REVIEW_CLAIM_ADMITTED"}, with
    no Authority/Store/ledger operation ever performed, still minted a token and launched a
    genuine harmless subprocess. "An internally owned admitted operation must depend on the
    existing real checks/claim, or the production effect must refuse... requiring dict
    parameters does not establish that distinction." Fixed: a new review_adapter.
    require_authenticated_review_launch_admission is the one function that can ever mint a
    local-launch admission token -- it calls authenticate_bounded_review_grant itself, fresh,
    with the caller's own real store/project_id/project_binding_id/requirement_id/
    selection_id/verifier_identity/permitted_boundary/verifier_selection_grant_refs/
    human_grant_declaration_refs, and independently re-reads the real, durable ledger at
    ledger_path for identity_key to confirm a claim genuinely exists and has not yet been
    terminally resolved, rather than trusting a caller-supplied assertion that either is true.
    validate_review_launch_preconditions/spawn_review_process/launch_review_process remain
    unchanged -- the generic, directly-testable primitives this module's own test suite
    already exercises for mechanics unrelated to authority at all; the one real composed
    route now calls the new gate instead of constructing decisions itself. Still never a new
    Authority owner (no new Kernel record, no check beyond calling the two existing real
    owners) and never a cryptographic scheme (no signature, no non-forgeable token) --
    dependency on the existing real checks themselves, exactly as required.
F2  SR6-F3's own fix closed the retained-unknown-state bypass only for a claim already marked
    local_cancellation_confirmed_at -- an ACK_UNKNOWN/DISPATCHED claim that never went through
    the cancellation route at all (a crash, a lost acknowledgement, or a process that simply
    exited on its own) still reached the pid/process_identity match plus fresh-liveness checks,
    and once those passed (a genuinely owned, genuinely no-longer-running process), any
    caller-supplied result_bytes was still accepted for RESOLUTION_KIND_COLLECTED_RESULT as a
    real OUTCOME_RECORDED. Local pid/token ownership has never been, and can never be made,
    evidence that result_bytes was genuinely collected -- this adapter performs no provider
    API call and keeps no durable record of what was actually captured, so this external/CLI
    route has no way to ever correlate caller-supplied bytes to anything real. Fixed:
    compose_bounded_technical_review_outcome_recording now refuses outright
    (COLLECTED_RESULT_UNSUPPORTED_EXTERNALLY) whenever resolution_kind is
    RESOLUTION_KIND_COLLECTED_RESULT, unconditionally, before pid/token/liveness is ever
    checked and regardless of any cancellation marker. A genuinely collected result can only
    ever be recorded through compose_bounded_technical_review_dispatch itself, which calls
    record_review_outcome directly with the real bytes collect_review_process_result just
    read. RESOLUTION_KIND_CONFIRMED_CANCELLATION remains reachable here (result_bytes still
    required to be None) -- an operator-asserted status label over a pid/token this route
    still independently confirms is genuinely bound and genuinely not running, never a
    caller-asserted payload this route cannot verify at all.
F3  SR6-F4's own INCOMPLETE_FILESYSTEM_BOUNDARY refusal ran only when build_argv was None --
    the independent review reproduced that a caller supplying any callable, including one
    constructing the identical real local Codex argv the omitted default would have built,
    bypassed it entirely and reached the same incomplete boundary. Fixed: the refusal is now
    unconditional on build_argv, lifted only by a new, explicit, test-only
    acknowledge_incomplete_filesystem_boundary_for_test_only parameter -- never by a
    callback's mere presence or its own choice of argv. No production/CLI caller in this
    delivery ever sets it True; this delivery's own tests set it explicitly, alongside a
    controlled build_argv fake, to exercise the rest of the route end to end, never to claim
    the boundary itself is complete.
```

Ten new permanent regression tests were added to `tests/integration/binding/
test_bounded_technical_review_route.py` (SR7-F1×4, SR7-F2×3, SR7-F3×1, plus two existing-
behavior preservation tests folded into the F2 count above), each reproducing the exact
finding's own counterexample and proving it now refused/fixed. Mechanical updates: the SR6-F1
`validate_review_launch_preconditions`/`spawn_review_process`/`launch_review_process` call
sites and their own tests needed no change at all (F1's new gate is a separate function in
front of them); the eleven `build_argv`-based composed-route tests each gained
`acknowledge_incomplete_filesystem_boundary_for_test_only=True`; three pre-existing F2-adjacent
tests (`test_sr4_f4_record_outcome_cli_succeeds_for_the_genuinely_bound_pid_and_identity`,
`test_sr4_f4_a_claim_with_no_confirmed_pid_can_never_be_resolved_through_this_route`,
`test_sr5_f4_outcome_recording_refuses_a_terminal_outcome_for_a_still_running_process`) and one
SR6-F3 test (`test_sr6_f3_an_invented_collected_result_after_local_cancellation_is_refused`)
were updated to match the corrected, broader COLLECTED_RESULT refusal -- the first renamed and
rewritten entirely since its own "COLLECTED_RESULT succeeds for a genuinely bound pid" premise
no longer holds; the other three switched their own exercised `resolution_kind` to
`RESOLUTION_KIND_CONFIRMED_CANCELLATION` (the one kind still reachable through this route) to
keep proving the identical pid/liveness/retention logic they always exercised, or updated
their expected reason string.
