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
