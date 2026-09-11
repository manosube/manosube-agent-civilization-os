"""The one public Change Executor route (Phase 18, Issue #73).

``CHANGE_EXECUTOR_OWNER_COUNT=1``, ``PUBLIC_CHANGE_EXECUTOR_ENTRY_POINT_COUNT=2``
(:func:`compose_change_executor` ``+1`` :func:`~manosube_agent_civilization.change_executor.
evidence_handoff.route_change_execution_to_evidence`).

The closure :func:`compose_change_executor` returns executes one already-AUTHORIZED, canonical
Change record -- resolved and re-verified by reproduction, never trusted from a caller -- only
inside an explicit, closed, low-risk Execution Boundary, and only when a human kill switch is
resolved fresh and ``ACTIVE`` at two separate checkpoints. It produces exactly one immutable
``change_execution_receipt`` and then stops: it creates no Authority, updates no canonical
State's semantic content beyond its own three new record kinds, proves no causality, establishes
no sufficient Evidence, closes no Difference, and declares no completion -- it hands off to the
existing Evidence/Observation/Reflow owners (:mod:`~manosube_agent_civilization.change_executor.
evidence_handoff`) rather than becoming a new owner of any of them.

Structurally rhymes throughout with :mod:`manosube_agent_civilization.url_boot.route`'s own
``compose_url_source_observer`` -- data canonicalized once at composition, a fresh
:func:`~manosube_agent_civilization.boot.boot_project` Boot on every request, route-owned
outcome classification never asserted by the replaceable adapter, and route-owned commits with
bounded Compare-And-Swap retry through the Store's own single sanctioned committer
(:func:`~manosube_agent_civilization.store.commit.commit_state_transition`).

Canonical route, in the exact order every request-facing call performs it (Structural Review
Round 1, ADOPT_P18_R1_STRUCTURAL_CORRECTIONS, corrected this ordering and several steps below --
see the disclosed judgment calls, items 9-14):

```text
canonicalize + freeze execution_boundary / adapter_identity                (composition, once)
  -- worktree_root is now a required field *inside* the closed Boundary itself, never a
  separate composition-time parameter (disclosed judgment call 6, superseded by item 11 below);
  validated there to also be a genuine git checkout of the Boundary's own repository/branch
  (disclosed judgment call 15, Structural Review Round 2, P18-R2-F2)
→ idempotency-slot resolution: an existing receipt (replay/reuse/mismatch), an existing attempt
  with no receipt under this exact caller's own claim_token (resolves to a grounded terminal
  UNKNOWN receipt, zero adapter calls -- disclosed judgment calls 16-17, Structural Review Round
  2, P18-R2-F3) or under a different one (reconciliation required, unchanged), an existing intent
  under this exact caller's own claim_token with neither (resuming a crash-interrupted attempt --
  see this module's own disclosed judgment call 7 below), or none of the three (proceed) --
  deliberately *before* time-window/kill-switch #1/Boot/staleness; see this module's own
  disclosed judgment calls 5 and 12 below for why
→ execution_instant falls within the bound Boundary's own validity_window  (zero-call refusal;
  reached only for a genuinely new or resumed slot -- a terminal outcome above already returned)
→ kill switch check #1 -- fresh resolve, ACTIVE required, signature re-verified
→ fresh Boot                                                  (only reached for a genuinely new
                                                                 mapping slot, or a resumed one)
→ resolve the Change, recompute-and-compare its own identity/fingerprint
→ resolve the Authority Decision the Change names, recompute-and-compare, require AUTONOMOUS
→ require action_kind in the bound Boundary's own permitted_action_kinds, and not Human-only
→ require scope.repository/branch/paths are entirely admitted by the bound Boundary
→ staleness: when *not* resuming, before_state_fingerprint / expected_state_revision must equal
  the fresh Boot's own, exactly; when *resuming* its own crash-interrupted intent, an *exact*
  successor check instead -- state_revision must be exactly expected_state_revision + 1, and the
  fresh Boot's own previous_state_fingerprint must exactly equal before_state_fingerprint,
  proving nothing else committed between the authorized State and now (disclosed judgment call
  9, superseding the prior round's blanket skip)
→ commit execution_intent                                    (RecordConflictError -> concurrent
                                                                claim)
→ commit execution_attempt                                   (RecordConflictError -> concurrent
                                                                claim)
→ kill switch check #2 -- fresh resolve again, immediately before the one adapter call; a
  refusal here still produces a terminal receipt (KILL_SWITCH_STOPPED), never a bare exception,
  because an execution_attempt is already committed and idempotency requires a terminal outcome
→ build + validate the closed operation against the bound Boundary's own file-count/byte/path
  limits; a violation here likewise produces a terminal receipt (BOUNDARY_VIOLATION), never a
  bare exception, for the identical reason
→ final pre-effect State barrier -- re-fetch the current State and require its own
  state_revision to be exactly what this call's own intent+attempt commits just produced; an
  unrelated transition that landed in between raises (disclosed judgment call 10)
→ call adapter.execute(...) exactly once for the primary requested operation (a distinct,
  policy-gated best-effort rollback call may follow, only when the primary call partially
  mutated and rollback_policy == BEST_EFFORT_DELETE_WRITTEN_FILES -- see this module's own
  disclosed judgment call below) -- a raised exception, or a structurally invalid returned
  report, now each commit a terminal UNKNOWN-outcome receipt (with the embedded
  reobservation_request), never a bare exception (disclosed judgment call 11)
→ independent after-state re-observation -- a genuine, read-only re-read of the actual on-disk
  result, entirely separate from the adapter's own self-reported facts (disclosed judgment call
  13, :mod:`~manosube_agent_civilization.change_executor.reobservation`)
→ classify the adapter's raw reported facts into one EXECUTION_OUTCOMES member -- never trusted
  from the adapter as an assertion; a would-be SUCCEEDED the independent re-observation
  disagrees with is reclassified as REOBSERVATION_MISMATCH instead (disclosed judgment call 13)
→ build + commit the terminal change_execution_receipt (with the embedded reobservation_request
  and the embedded independent_after_state_observation)
→ return {"receipt": ..., "replay": bool, "semantic_reuse": bool}
```

A terminal replay/semantic-reuse return, and a refusal detected at idempotency-slot resolution
itself, both leave here with zero Boot, zero Store commit, and zero adapter calls -- regardless
of the current Boundary validity window or kill-switch state, since a replay/reuse return is
read-only (disclosed judgment call 12). Every exception path from idempotency-slot resolution
through staleness likewise raises before any Store commit and before the adapter is ever
constructed a call to. Every path reachable *after* execution_attempt is durably committed --
kill-switch #2, Boundary-limit violation, the final pre-effect State barrier, an adapter raise,
and an invalid adapter report alike -- now commits exactly one terminal receipt, or (the final
pre-effect State barrier alone) raises a typed exception that leaves the slot correctly
resolvable as reconciliation-required, never a bare, unresolvable exception (disclosed judgment
calls 3, 10, and 11).

**Disclosed judgment calls**, each also restated at the point in this module where it matters:

1. **The return shape is a small envelope, not the bare receipt.** The seeding task description
   asks for an idempotent replay to "return the existing receipt unchanged" and a disclosed
   semantic reuse to return it "with a distinguishable field/flag" -- but
   ``execution_receipt.schema.json`` is closed (``additionalProperties: false``), so no such flag
   can be added to the immutable receipt record itself without becoming a second, undeclared
   schema. :func:`compose_change_executor`'s returned closure therefore always returns
   ``{"receipt": <the exact, unmodified change_execution_receipt>, "replay": bool,
   "semantic_reuse": bool}`` -- a uniform envelope across every code path (a genuinely first
   execution returns both flags ``False``), so "unchanged" is satisfied for the nested receipt
   itself in every case, and the distinguishing flag lives one level out instead of inside the
   closed record.
2. **``execution_started_at``/``execution_ended_at`` both come from the one caller-supplied
   ``execution_instant``.** The request-facing closure's own call shape -- ``(change_id,
   claim_token, execution_instant, permit_semantic_reuse)`` (``worktree_root`` bound at
   composition, inside the closed Boundary itself -- see judgment call 6 below, superseded by
   judgment call 11) -- carries exactly one instant, and this package reads no clock anywhere.
   Both receipt timestamp fields are therefore set to that one instant; a deployment that
   genuinely needs the two to differ would need to extend the request shape itself, which this
   delivery does not do without being asked.
3. **A kill-switch refusal at checkpoint #2, and a Boundary-limit violation discovered while
   building the operation, both produce a terminal receipt rather than a raised exception.** By
   that point an ``execution_attempt`` is already durably committed; this package's own
   idempotency contract requires *some* terminal receipt to exist for a committed attempt (a bare
   exception here would leave the slot permanently stuck in "attempt exists, no receipt" --
   ``ExecutionReconciliationRequiredError`` forever, with no path to resolution). ``KILL_SWITCH_
   STOPPED`` and ``BOUNDARY_VIOLATION`` are both named, closed members of ``EXECUTION_OUTCOMES``
   for exactly this reason.
4. **The best-effort rollback call is a second, distinct, explicitly policy-gated adapter call,
   not a violation of "call adapter.execute(...) exactly once."** That requirement governs
   dispatch of the one *primary*, requested operation; ``rollback_policy ==
   "BEST_EFFORT_DELETE_WRITTEN_FILES"`` is a Boundary-declared, closed, distinct recovery action,
   only ever reached after a partial or failed primary call, and only ever deletes exactly the
   paths the primary call's own raw facts say it wrote -- never a second attempt at the original
   operation.
5. **Idempotency-slot resolution runs before Boot/Change/Authority/staleness, not after.** This
   package's own test suite demonstrated a genuine ordering defect in an earlier draft of this
   function: every commit this route performs (``execution_intent``, ``execution_attempt``,
   ``change_execution_receipt``) unconditionally advances the project's own ``state_revision`` by
   one, regardless of outcome. A staleness check performed *before* replay detection therefore
   made the very first successful ``execute()`` call for a Change make every subsequent call for
   it -- including an ordinary same-``claim_token`` replay -- spuriously refuse as stale, never
   reaching replay/reuse resolution at all: the exact opposite of what P18-C5's own idempotency
   contract requires. The mapping-slot key is a pure function of *change_id* (a caller-supplied
   parameter) and the two fingerprints already bound at composition time, so resolving it needs
   neither Boot nor the resolved Change record; moving it first means a terminal outcome -- which
   already reflects a fully-vetted prior execution -- is returned unchanged with zero Boot, zero
   Change/Authority resolution, and zero staleness re-check, and the live current State is Booted
   and stale-checked only for a genuinely new mapping slot, for which it is the correct State to
   check against.
6. **``worktree_root`` is bound once at composition, never carried on the per-request
   ``execute(...)`` call** (SUPERSEDED by judgment call 11 below, Structural Review Round 1: the
   fix disclosed here -- a separate composition-time parameter -- was itself further corrected
   to fold ``worktree_root`` *inside* the closed Boundary itself, closing a residual gap this
   entry's own fix did not: nothing yet tied a composed executor's own worktree root to its own
   Boundary's *identity/fingerprint*, only to its own lifetime). Retained here, unedited, as the
   disclosed history of the original fix. An automated review of this package correctly
   identified that a
   request-facing ``worktree_root`` was a genuine Boundary-binding gap: every other trust-
   sensitive parameter this module ever uses -- the Store, the Execution Boundary, the adapter
   identity, the adapter itself, the kill-switch trust anchor -- is bound once at composition and
   carries no per-request override, but ``worktree_root`` alone was left request-facing, so
   nothing tied it to the bound Boundary's own fixed ``repository``/``branch``. Since the
   adapter's own confinement is real defense *within* whatever ``worktree_root`` it is handed
   (never following a symlink out, never traversing above it) but is no defense at all against
   being handed the *wrong* root entirely, a caller of one composed executor could point every
   write at an arbitrary existing directory unrelated to the Change it was authorized against.
   Every Change executed through one composed executor already must share that one composed
   executor's own bound Boundary's fixed ``repository``/``branch`` (the existing scope check),
   so binding ``worktree_root`` once at composition -- validated there to be a non-empty string
   that resolves to a real, existing directory, exactly like every other composition-time input
   -- is not merely the security fix but the semantically correct model this module's own design
   already implies elsewhere: one composed executor, one fixed Boundary, one fixed worktree.
7. **A caller resuming its own crash-interrupted intent skips the staleness check for that one
   call.** Every commit this route performs unconditionally advances ``state_revision`` by one
   (judgment call 5 above already establishes this), including the ``execution_intent`` commit
   alone -- so a process that crashes after that commit succeeds but before the following
   ``execution_attempt`` commit ever runs leaves a slot with a durably committed intent, no
   attempt, and no receipt. A bare retry with the identical ``claim_token``/``execution_instant``
   would previously reach idempotency-slot resolution, find neither an attempt nor a receipt, and
   proceed through Boot and staleness exactly as a first call would -- except the intent's own
   prior commit already advanced ``state_revision`` past what the Change's own
   ``expected_state_revision`` names, so the retry raised ``StaleExecutionInputError``
   permanently, with no adapter side effect ever having occurred and no path to reconciliation
   (an automated review identified this real crash-recovery gap). The fix: idempotency-slot
   resolution additionally resolves any existing ``execution_intent`` for the slot; when one
   exists and its own declared ``claim_token`` equals this call's own, this call is that exact
   caller resuming its own interrupted attempt -- not a collision -- and the staleness raise
   alone is skipped for it. Every other step still runs unchanged: Boot, Change/Authority/scope
   resolution (Change is immutable, so re-resolving it is harmless and the checks remain
   meaningful), the intent commit itself (now a no-op replay of the byte-identical existing
   intent, since nothing about its own content differs), the attempt commit, both kill-switch
   checkpoints, and the one adapter call. A *different* ``claim_token`` against an existing
   intent is not a resume at all -- it is not treated specially here, and correctly falls through
   to collide at the intent-commit step below (``RecordConflictError`` ->
   ``ExecutionConcurrentClaimError``), exactly as before this fix.
8. **``execution_attempt`` now carries a fresh, per-call ``attempt_nonce``, closing a genuine
   duplicate-adapter-call race.** Two callers invoking ``execute()`` truly concurrently with the
   identical ``change_id``/``claim_token``/``execution_instant`` (through the same composed
   executor, so necessarily also the identical Boundary/adapter identity) could both pass
   idempotency-slot resolution before either had committed anything -- both would then build
   byte-identical ``execution_intent`` and ``execution_attempt`` records, deterministic from
   their identical inputs, and the Store's own commit correctly treats a second, byte-identical
   attempt as an idempotent replay of the first rather than a conflict (the exact behavior
   legitimate sequential crash-retry depends on) -- so the second caller's attempt-commit would
   also "succeed," and it too would proceed to call ``adapter.execute(...)``, genuinely
   duplicating the primary mutation this module's own docstring states happens exactly once (an
   automated review identified this real race). The fix generates a fresh
   ``secrets.token_hex(16)`` immediately before building a genuinely new
   ``execution_attempt`` -- never caller-supplied, never derived from any other input -- and
   embeds it as an ordinary new field on the attempt record's own body (never near the
   deterministic ``slot_key``/record id, which stays exactly as before: two racing callers must
   still collide at the identical ``(kind, id)``). This makes two independently-built attempts
   for the same slot genuinely different byte-for-byte, so the Store's own *existing*
   conflict-detection (a same-``(kind, id)``-different-body record under a fresh transaction is a
   real ``RecordConflictError``) now correctly refuses the second one -- ``route.py`` already
   converts that into ``ExecutionConcurrentClaimError`` at the attempt-commit call site, so no
   new Store-layer machinery is needed, only a genuinely non-reproducible attempt body. This
   deliberately does not touch ``execution_intent``'s own body: two racing callers' intent-commits
   both succeeding is harmless by itself (neither one calls the adapter), so the exclusivity
   boundary only needs to live at the attempt, the one record whose commit gates the adapter
   call.

**Structural Review Round 1 (ADOPT_P18_R1_STRUCTURAL_CORRECTIONS)** -- six further corrections,
adopted against this package's exact prior head, each disclosed here as its own new judgment
call (never overwriting the history above):

9. **Resuming a crash-interrupted intent now requires an *exact* immediate-successor check, not
   a blanket staleness skip (P18-R1-F2).** Judgment call 7 above skipped the staleness check
   entirely for a caller resuming its own crash-interrupted intent -- correct for the *ordinary*
   crash-recovery case, but it also silently admitted an unrelated transition that happened to
   land between the intent commit and the resumed retry, since nothing re-checked that the
   current State was genuinely the intent-commit's own direct successor and nothing else. The
   fix: when resuming, this route now requires ``boot_context.current_state["state_revision"] ==
   change["expected_state_revision"] + 1`` *and*
   ``boot_context.current_state["previous_state_fingerprint"] == change["before_state_
   fingerprint"]`` -- the second check is the genuinely decisive one: ``previous_state_
   fingerprint`` is the fingerprint of the State immediately *before* the current one
   (``_commit_records`` always sets it from the prior State's own ``semantic_fingerprint``), so
   requiring it to equal the Change's own ``before_state_fingerprint`` proves the intent commit
   really was the *only* thing that happened since this Change was authorized, not merely that
   *some* commit happened to land the revision counter on the expected number by coincidence. A
   different, unrelated transition landing in between now correctly raises
   ``StaleExecutionInputError`` even when resuming, with zero adapter calls.
10. **A final pre-effect State barrier, immediately before the one adapter call (P18-R1-F2).**
    Even with item 9's exact successor check in place at staleness time, a narrow window remains
    open *after* the intent+attempt commits and kill-switch check #2/Boundary-validation, right
    up until the adapter is actually called -- during which an unrelated transition could still
    land. This route now re-fetches the current State one more time, immediately before
    ``adapter.execute(...)``, and requires its own ``state_revision`` to equal exactly
    ``post_attempt_state_revision`` -- the empirical value this call's own attempt-commit itself
    just returned (never a recomputed guess). A mismatch raises ``StaleExecutionInputError``
    before the adapter is ever called, zero further mutation -- deliberately a raised exception
    here, not a fourth terminal-receipt-producing path alongside item 3's two: the slot is left in
    exactly the same "attempt committed, no receipt yet" state a genuine crash would leave it in,
    which any future caller for this identical slot already correctly resolves as
    ``ExecutionReconciliationRequiredError``.
11. **``worktree_root`` is now a required field *inside* the closed Execution Boundary itself,
    not merely a separate composition-time parameter alongside it (P18-R1-F3, superseding
    judgment call 6).** Since :func:`~manosube_agent_civilization.change_executor.boundary.
    execution_boundary_fingerprint` already hashes the *entire* canonical Boundary mapping, and
    the mapping-slot key (:func:`~manosube_agent_civilization.change_executor.identity.
    execution_mapping_slot_key`) already depends on that fingerprint, folding ``worktree_root``
    into the Boundary makes it participate in both structurally, automatically, with no change
    needed to the slot-key function itself: two composed executors bound to genuinely different
    worktree roots now necessarily get different Boundary fingerprints and therefore different
    mapping slots -- a cross-root/cross-worktree slot or receipt substitution is now structurally
    impossible within this package's own identity scheme, not merely discouraged by convention.
    This does **not** prove the directory at ``worktree_root`` is a real checkout of the
    Boundary's own ``repository``/``branch`` -- this package still performs no subprocess/network
    calls, so it cannot invoke ``git`` to verify that association (see this module's own
    non-claims, restated in ``CHANGE_EXECUTOR_CONTRACT.md``); only that a *given* worktree_root is
    now bound, structurally, to exactly one Boundary/fingerprint/slot.
12. **Idempotency-slot resolution now runs before time-window/kill-switch checkpoint #1 too, not
    merely before Boot/staleness (P18-R1-F5, extending judgment call 5).** None of the three
    slot-resolution outcomes (terminal replay, semantic reuse, terminal-claim-mismatch,
    reconciliation-required) ever proceeds to Boot, a Store commit, or an adapter call -- so none
    of them need an admission check first. Gating a *read-only* return behind checks that exist
    only to authorize a *new* side effect was itself the defect this correction closes: a
    terminal receipt committed while the bound Boundary's own ``validity_window`` was still
    current must still replay cleanly after that window has since expired, and a terminal receipt
    committed while the kill switch was still ``ACTIVE`` must still replay cleanly after the kill
    switch has since been ``REVOKED`` -- a replay performs zero Boot/Store-commit/adapter-calls
    regardless of either check's own current state.
13. **Every post-attempt path now commits exactly one terminal receipt, including an adapter
    raise and a structurally invalid adapter report (P18-R1-F4, extending judgment call 3 to the
    two paths that previously did not follow it).** Before this correction, ``adapter.execute``
    raising, or returning a report that failed ``_validate_adapter_report``, were each converted
    into a bare, raised ``ExecutionAdapterError`` -- unlike the kill-switch-#2 and
    Boundary-violation paths, which already committed a terminal receipt for the identical
    structural reason (an ``execution_attempt`` is already durably committed by that point). Both
    now instead commit a terminal receipt with ``outcome = "UNKNOWN"`` (already a defined
    ``EXECUTION_OUTCOMES`` member, mapped to Evidence's own ``UNAVAILABLE`` status) -- the safe,
    honest "we do not know what happened" default, carrying the identical embedded
    ``reobservation_request`` every other terminal path already carries, so an independent
    re-observation is still requested even though this package cannot itself confirm what
    happened. The raw exception's own text is deliberately never persisted on the receipt --
    ``performed_result_summary`` is schema-closed to ``files_written``/``bytes_written``/
    ``files_deleted`` (the identical bounded discipline already established for
    ``BOUNDARY_VIOLATION`` above), so free text has no admissible field to live in; only the
    closed ``UNKNOWN`` outcome is.
14. **Independent after-state re-observation now gates whether a receipt's own ``outcome`` may
    ever be ``SUCCEEDED`` (P18-R1-F1).** Before this correction, ``evidence_handoff.py`` mapped a
    receipt's own self-reported ``outcome == "SUCCEEDED"`` directly to Evidence's own
    ``VERIFIED`` status, using the adapter's own self-reported facts (never independently
    re-confirmed) as the sole basis. This route now performs a genuine, independent, read-only
    re-read of the actual resulting filesystem state
    (:func:`~manosube_agent_civilization.change_executor.reobservation.independently_reobserve`)
    immediately after a validated adapter report is obtained -- never trusting
    ``adapter_report["bytes_written"]``/``files_written`` as proof of content, only a fresh
    ``Path.read_bytes()`` compared, by SHA-256 digest, against the *requested*
    ``content_utf8`` -- and embeds the result inside the committed receipt itself (a new,
    schema-required field, ``independent_after_state_observation``, also covered by
    ``change_execution_receipt_semantic_fingerprint``). A would-be ``SUCCEEDED`` classification
    this independent re-read disagrees with is reclassified as the new, closed
    ``REOBSERVATION_MISMATCH`` outcome instead -- never silently reused as ``SUCCEEDED``. This is
    deliberately **not** a wiring-in of the full ``independent_verification`` package (that
    package requires a SHUKOU-authorized ``VerifierSelection`` plus a Store-resolved grant/
    declaration chain -- the human-selected-verifier claim-verification concern, a different one
    from this package's own bounded, autonomous execution; requiring a fresh human grant per
    autonomous execution would defeat Phase 18's whole bounded-autonomy design). Independent
    re-observation is deliberately skipped (embedding a fixed ``NOT_PERFORMED`` result instead)
    for every path that never reaches a validated adapter report at all -- ``KILL_SWITCH_
    STOPPED``, ``BOUNDARY_VIOLATION``, and the two ``UNKNOWN`` paths item 13 above introduces --
    since there is nothing meaningful to independently re-observe when the primary operation was
    never admitted to run, or its own outcome could not be trusted enough to re-observe against.

**Structural Review Round 2 (ADOPT_P18_R2_STRUCTURAL_CORRECTIONS)** -- four further corrections,
adopted against this package's exact prior head (PR #74, comment
``https://github.com/manosube/manosube-agent-civilization-os/pull/74#issuecomment-5628140572``),
each disclosed here as its own new judgment call (never overwriting the history above):

15. **Composition-time ``worktree_root`` identity verification against the Boundary's own
    ``repository``/``branch`` (P18-R2-F2).** Item 11 above closed the *structural* substitution
    gap (a given ``worktree_root`` binds to exactly one Boundary fingerprint/slot) but explicitly
    disclaimed proving the directory is genuinely a checkout of that Boundary's own declared
    ``repository``/``branch`` at all. :mod:`~manosube_agent_civilization.change_executor.boundary`
    now closes that gap too, entirely through pure, local ``.git`` metadata file reads (no
    ``subprocess``/network call of any kind, preserving this package's own static-conformance
    guarantee): it resolves the real git directory (following a linked worktree's own ``.git``
    file and ``commondir``), reads ``HEAD`` to require a genuine local branch ref (a detached
    HEAD fails closed -- it cannot prove a branch identity), and reads the main repository's own
    ``config`` for ``[remote "origin"] url`` normalized to the identical ``owner/repo`` slug form
    ``execution_boundary["repository"]`` already uses. A mismatch, or any unparseable/missing
    ``.git`` metadata, raises :class:`~manosube_agent_civilization.change_executor.errors.
    ExecutionBoundaryError` at composition time, before any request-facing operation can even be
    obtained. See ``boundary.py``'s own module docstring for the full mechanism, and
    ``CHANGE_EXECUTOR_CONTRACT.md``'s corrected non-claim (the prior round's own non-claim is
    superseded, not silently dropped).
16. **``execution_attempt`` now carries its own ``reobservation_request`` durably, embedded at
    commit time -- not merely recomputed later at each terminal-receipt call site (P18-R2-F3,
    part 1).** Before this correction, ``reobservation_request`` was built as a local variable
    *after* ``execution_attempt`` was already committed, and recomputed independently (from the
    identical inputs, so byte-identical in practice, but never read back from the durably
    committed record itself) at every one of the five ``_commit_terminal_receipt`` call sites.
    This route now builds it once, *before* the intent/attempt commits (everything it depends on
    -- the frozen Boundary, ``change_ref``, the resolved Change's own canonical scope, and
    ``execution_instant`` -- is already known by then), passes it into
    :func:`~manosube_agent_civilization.change_executor.engine.build_execution_attempt` as a new,
    schema-required, semantic-fingerprint-covered field, and every later terminal-receipt commit
    site reads it back off the durably committed ``attempt`` record itself
    (``attempt["reobservation_request"]``) rather than recomputing it a second time. The point is
    not the byte content (identical either way in the ordinary path) -- it is that from the
    instant ``execution_attempt`` becomes durable, the durable record chain already preserves a
    typed re-observation obligation a *future*, *resuming* caller can read back and resolve
    against, which item 17 below depends on.
17. **A caller resuming its OWN orphaned ``execution_attempt`` (identical ``claim_token``) now
    resolves to a grounded terminal ``UNKNOWN`` receipt, never a perpetual
    ``ExecutionReconciliationRequiredError`` (P18-R2-F3, part 2).** Before this correction, step 2
    (idempotency-slot resolution) raised ``ExecutionReconciliationRequiredError`` unconditionally
    the instant it found *any* orphaned ``execution_attempt`` (committed, no receipt yet) --
    regardless of whose ``claim_token`` it carried, mirroring the exact problem the pre-existing
    intent-only-crash fix (item 7) already solved for the intent-without-attempt case, but left
    unsolved one step later. The fix extends the identical claim_token-based distinction: when the
    orphaned attempt's own declared ``claim_token`` equals this call's own, this call is that
    exact caller resuming its own crash-interrupted (or final-pre-effect-barrier-refused, or
    otherwise unresolved) attempt -- not a collision -- so instead of raising, this route commits
    one terminal receipt with ``outcome = "UNKNOWN"`` directly from the orphaned attempt's own
    durably-embedded ``reobservation_request`` (item 16), with
    ``independent_after_state_observation = NOT_PERFORMED_REOBSERVATION``: the true outcome of
    whatever happened between the attempt commit and the crash -- including whether the adapter
    ever actually ran -- is genuinely unknowable, so ``UNKNOWN`` is the honest, safe answer, and
    the adapter is never re-called on this resume path (it may already have run; re-calling it
    would risk a real duplicate mutation). Neither Boot, either kill-switch checkpoint, nor the
    time-window check runs on this path -- none of them gate a *new* admission decision here (none
    is being made: no new ``execution_intent``/``execution_attempt`` is committed, only an
    already-admitted one is honestly concluded), the identical "a terminal outcome does not need
    an admission check first" reasoning items 5/12 already establish for idempotency-slot
    resolution as a whole. A *different* ``claim_token`` against an orphaned attempt remains
    exactly as before this fix: ``ExecutionReconciliationRequiredError``, unchanged -- an
    unrelated caller must not be able to auto-resolve someone else's stuck attempt. See
    :func:`_commit_orphaned_attempt_unknown_receipt`'s own docstring for the full mechanism.
18. **``evidence_handoff.route_change_execution_to_evidence`` no longer promotes a receipt's own
    self-reported ``SUCCEEDED`` to ``VERIFIED`` Evidence on the strength of this route's own
    embedded ``independent_after_state_observation`` alone (P18-R2-F1).** Item 14 above remains
    exactly as it was -- a legitimate, useful receipt-level cross-check (the adapter's own raw
    self-report vs. a fresh read, gating the receipt's own ``outcome`` field) -- but using that
    *same* embedded field, alone, to promote Evidence to ``VERIFIED`` let the executor manufacture
    the fact that promotes its own receipt. ``evidence_handoff.py`` now performs a *second*,
    genuinely independent, handoff-time-only re-read (entirely separate from, and never trusting,
    this route's own execution-time reobservation embedded on the receipt), mints a real
    Observation from it through the existing Observation owner
    (:func:`~manosube_agent_civilization.observation.engine.observe`, via ``evidence.
    derive_evidence``'s own internal call -- never a caller-supplied Observation record trusted
    directly), and requires the two independent re-reads to agree before ``VERIFIED`` may ever be
    derived. See ``evidence_handoff.py``'s own module docstring for the full mechanism -- this
    route's own code is unchanged by this item; only its own downstream consumer's promotion
    discipline is.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import hashlib
import secrets
from typing import Any

from manosube_agent_civilization.authority import AUTONOMOUS
from manosube_agent_civilization.authority.identity import (
    decision_id as _decision_id,
    decision_semantic_fingerprint as _decision_semantic_fingerprint,
)
from manosube_agent_civilization.authority.levels import HUMAN_ONLY_ACTION_KINDS
from manosube_agent_civilization.authority.scope import canonical_scope
from manosube_agent_civilization.binding.signature import verify_ed25519_signature
from manosube_agent_civilization.boot import boot_project
from manosube_agent_civilization.change.identity import (
    change_id as _change_id_of,
    change_semantic_fingerprint as _change_semantic_fingerprint_of,
)
from manosube_agent_civilization.state.canonicalize import canonical_json_bytes
from manosube_agent_civilization.state.fingerprint import fingerprint_project_state
from manosube_agent_civilization.store.commit import commit_state_transition
from manosube_agent_civilization.store.errors import RecordConflictError, StaleStateError

from .boundary import (
    canonicalize_inert_data,
    deep_freeze,
    execution_boundary_fingerprint,
    path_is_admitted,
    require_within_time_window,
    validate_execution_boundary,
)
from .engine import build_change_execution_receipt, build_execution_attempt, build_execution_intent
from .errors import (
    ChangeExecutorError,
    ExecutionAdapterError,
    ExecutionAuthorityProvenanceError,
    ExecutionConcurrentClaimError,
    ExecutionKillSwitchError,
    ExecutionReceiptIntegrityError,
    ExecutionReconciliationRequiredError,
    ExecutionTerminalClaimMismatchError,
    StaleExecutionInputError,
)
from .identity import (
    change_execution_receipt_id as _change_execution_receipt_id_of,
    change_execution_receipt_semantic_fingerprint,
    execution_attempt_id as _execution_attempt_id_of,
    execution_attempt_semantic_fingerprint,
    execution_intent_id as _execution_intent_id_of,
    execution_intent_semantic_fingerprint,
    execution_mapping_slot_key,
)
from .kill_switch import kill_switch_signing_payload, resolve_current_kill_switch
from .reobservation import NOT_PERFORMED_REOBSERVATION, independently_reobserve

_CHANGE_RECORD_KIND = "change"
_AUTHORITY_DECISION_RECORD_KIND = "authority_decision"
_INTENT_RECORD_KIND = "execution_intent"
_ATTEMPT_RECORD_KIND = "execution_attempt"
_RECEIPT_RECORD_KIND = "execution_receipt"

#: The identical bounded Compare-And-Swap retry ``url_boot/route.py``'s own ``_commit_envelope``
#: uses -- bounded protection against genuine, unrelated contention only.
_MAX_COMMIT_RETRIES = 8


def _require_canonical_identity(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ChangeExecutorError(f"{name} must be a non-empty string identity: {value!r}")
    if "/" in value or "\\" in value or value.startswith("..") or "://" in value:
        raise ChangeExecutorError(
            f"{name} must be a canonical identity, never a path/URL/locator: {value!r}"
        )
    return value


def _require_non_empty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ChangeExecutorError(f"{name} must be a non-empty string: {value!r}")
    return value


def _commit_records(
    store: Any,
    project_id: str,
    records: list[tuple[str, str, dict[str, Any]]],
    committed_at: str,
    *,
    transaction_prefix: str,
) -> dict[str, Any]:
    """The one Store-commit template every commit in this module shares -- copied, in shape,
    from ``url_boot/route.py``'s own ``_commit_envelope``: bounded Compare-And-Swap retry
    against genuine, unrelated contention only. ``RecordConflictError`` -- a real identity/
    content conflict -- is never swallowed into a retry; it is raised bare, and every call site
    in this module translates it into its own typed error."""

    for _ in range(_MAX_COMMIT_RETRIES):
        current_state = store.load_current(project_id)
        transaction_id = f"{transaction_prefix}-{current_state['state_revision']}"
        next_state = dict(current_state)
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
            return commit_state_transition(
                store,
                project_id,
                current_state["state_revision"],
                current_state["semantic_fingerprint"],
                next_state,
                transition,
                records=records,
            )
        except RecordConflictError:
            raise
        except StaleStateError:
            continue
    raise ChangeExecutorError(
        f"could not durably commit under transaction prefix {transaction_prefix!r} after "
        f"{_MAX_COMMIT_RETRIES} Compare-And-Swap retries -- sustained unrelated contention on "
        "this project's own State"
    )


def _require_active_kill_switch_verified(
    store: Any, project_id: str, trust_anchor_public_key_hex: str, *, stage: str
) -> None:
    """Resolve the current kill switch fresh, require it to exist and be ``ACTIVE``
    (:mod:`~manosube_agent_civilization.change_executor.kill_switch`'s own tamper-checked
    resolve), **and** independently re-verify its own signature against
    *trust_anchor_public_key_hex* -- defense in depth beyond what commit-time verification
    alone already establishes, appropriate to a control whose entire purpose is to be trusted
    at the exact moment it is checked, not merely once, historically, when it was minted."""

    current = resolve_current_kill_switch(store, project_id)
    if current is None:
        raise ExecutionKillSwitchError(
            f"no change_executor_kill_switch is currently admitted for project {project_id!r} "
            f"-- refusing to execute ({stage})"
        )
    if current.get("status") != "ACTIVE":
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for project {project_id!r} is not ACTIVE "
            f"({current.get('status')!r}) -- refusing to execute ({stage})"
        )
    signature = current.get("signature")
    signature_hex = signature.get("value") if isinstance(signature, dict) else None
    if not isinstance(signature_hex, str) or not verify_ed25519_signature(
        public_key_hex=trust_anchor_public_key_hex,
        message=kill_switch_signing_payload(current),
        signature_hex=signature_hex,
    ):
        raise ExecutionKillSwitchError(
            f"the current change_executor_kill_switch for project {project_id!r} carries no "
            f"genuine signature by the bound trust anchor -- refusing to execute ({stage})"
        )


def _resolve_change(store: Any, project_id: str, change_id: str) -> dict[str, Any]:
    resolved = store.resolve_record(project_id, _CHANGE_RECORD_KIND, change_id)
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionAuthorityProvenanceError(
            f"change_id does not resolve to a committed change for project {project_id!r}: "
            f"{change_id!r}"
        )
    change = dict(resolved)
    if change.get("project_id") != project_id:
        raise ExecutionAuthorityProvenanceError(
            f"resolved change names a different project than the one being executed against: "
            f"{change.get('project_id')!r} != {project_id!r}"
        )
    declared_id = change.get("change_id")
    recomputed_id = _change_id_of(change)
    if change_id != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved change's own identity does not agree across the Store lookup key, its own "
            f"declared value, and its own recomputed value -- lookup={change_id!r}, "
            f"declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if _change_semantic_fingerprint_of(change) != change.get("change_semantic_fingerprint"):
        raise ExecutionReceiptIntegrityError(
            f"resolved change {change_id!r} own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to trust any of its fields"
        )
    if change.get("status") != "AUTHORIZED":
        raise ExecutionAuthorityProvenanceError(
            f"resolved change {change_id!r} own status is not AUTHORIZED: {change.get('status')!r}"
        )
    return change


def _resolve_authority_decision(
    store: Any, project_id: str, decision_id_value: str
) -> dict[str, Any]:
    resolved = store.resolve_record(project_id, _AUTHORITY_DECISION_RECORD_KIND, decision_id_value)
    if resolved is None or not isinstance(resolved, dict):
        raise ExecutionAuthorityProvenanceError(
            "the change's own authority_ref does not resolve to a committed authority_decision "
            f"for project {project_id!r}: {decision_id_value!r}"
        )
    decision = dict(resolved)
    if decision.get("project_id") != project_id:
        raise ExecutionAuthorityProvenanceError(
            "resolved authority_decision names a different project than the one being executed "
            f"against: {decision.get('project_id')!r} != {project_id!r}"
        )
    declared_id = decision.get("authority_decision_id")
    recomputed_id = _decision_id(decision)
    if decision_id_value != declared_id or recomputed_id != declared_id:
        raise ExecutionReceiptIntegrityError(
            "resolved authority_decision's own identity does not agree across the Store lookup "
            f"key, its own declared value, and its own recomputed value -- "
            f"lookup={decision_id_value!r}, declared={declared_id!r}, recomputed={recomputed_id!r}"
        )
    if _decision_semantic_fingerprint(decision) != decision.get("decision_semantic_fingerprint"):
        raise ExecutionReceiptIntegrityError(
            f"resolved authority_decision {decision_id_value!r} own recomputed semantic "
            "fingerprint does not equal its own declared value -- refusing to trust any of its "
            "fields"
        )
    return decision


def _resolve_slot_record(
    store: Any, project_id: str, kind: str, slot_key: str
) -> dict[str, Any] | None:
    resolved = store.resolve_record(project_id, kind, slot_key)
    if resolved is None:
        return None
    return dict(resolved)


def _verify_slot_record(
    record: Mapping[str, Any],
    *,
    kind: str,
    declared_id_field: str,
    recompute_id: Callable[[Mapping[str, Any]], str],
    recompute_fingerprint: Callable[[Mapping[str, Any]], str],
    fingerprint_field: str,
    slot_key: str,
) -> dict[str, Any]:
    checked = dict(record)
    declared_id = checked.get(declared_id_field)
    if slot_key != declared_id or recompute_id(checked) != declared_id:
        raise ExecutionReceiptIntegrityError(
            f"resolved {kind}'s own identity does not agree across the Store lookup key, its "
            f"own declared value, and its own recomputed value -- lookup={slot_key!r}, "
            f"declared={declared_id!r}"
        )
    if recompute_fingerprint(checked) != checked.get(fingerprint_field):
        raise ExecutionReceiptIntegrityError(
            f"resolved {kind} {slot_key!r} own recomputed semantic fingerprint does not equal "
            "its own declared value -- refusing to trust any of its fields"
        )
    return checked


def _operation_violation_reason(
    action_kind: str, operation: Any, boundary: Mapping[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate *operation* -- the Change's own opaque ``action.operation`` payload -- against
    the closed :class:`~manosube_agent_civilization.change_executor.types.ExecutionOperation`
    shape and the bound Boundary's own file-count/byte/path limits. Returns ``(checked_operation,
    None)`` when admissible, or ``(None, reason)`` otherwise -- never raises: a well-typed
    operation that would exceed a limit, and a malformed operation payload alike, are both a
    normal, expected, typed terminal outcome (``BOUNDARY_VIOLATION``) this route's own caller
    needs a receipt for, not a bare exception."""

    if not isinstance(operation, Mapping):
        return None, "action.operation is not a mapping"
    if operation.get("operation_kind") != action_kind:
        return None, "action.operation.operation_kind does not equal the Change's own action_kind"
    writes = operation.get("file_writes")
    deletes = operation.get("file_deletes")
    if not isinstance(writes, list) or not isinstance(deletes, list):
        return None, "action.operation.file_writes/file_deletes must both be lists"

    checked_writes: list[dict[str, str]] = []
    checked_deletes: list[dict[str, str]] = []
    touched_paths: set[str] = set()
    total_bytes = 0
    max_file_bytes = boundary["max_file_bytes"]

    for entry in writes:
        if not isinstance(entry, Mapping):
            return None, "a file_writes entry is not a mapping"
        path = entry.get("path")
        content = entry.get("content_utf8")
        if type(path) is not str or not path or type(content) is not str:
            return None, "a file_writes entry has an unreadable path or content_utf8"
        if not path_is_admitted(path, boundary["admitted_paths"]):
            return None, f"path is not admitted by the bound Boundary: {path!r}"
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > max_file_bytes:
            return (
                None,
                f"file exceeds max_file_bytes: {path!r} ({content_bytes} > {max_file_bytes})",
            )
        total_bytes += content_bytes
        touched_paths.add(path)
        checked_writes.append({"path": path, "content_utf8": content})

    for entry in deletes:
        if not isinstance(entry, Mapping):
            return None, "a file_deletes entry is not a mapping"
        path = entry.get("path")
        if type(path) is not str or not path:
            return None, "a file_deletes entry has an unreadable path"
        if not path_is_admitted(path, boundary["admitted_paths"]):
            return None, f"path is not admitted by the bound Boundary: {path!r}"
        touched_paths.add(path)
        checked_deletes.append({"path": path})

    if not touched_paths:
        return None, "action.operation names no file_writes and no file_deletes"
    if len(touched_paths) != len(checked_writes) + len(checked_deletes):
        return (
            None,
            "action.operation names the identical path in both file_writes and file_deletes",
        )
    if len(touched_paths) > boundary["max_files_changed"]:
        return None, (
            f"operation touches {len(touched_paths)} files, exceeding max_files_changed "
            f"({boundary['max_files_changed']})"
        )
    if total_bytes > boundary["max_bytes_changed"]:
        return None, (
            f"operation writes {total_bytes} bytes, exceeding max_bytes_changed "
            f"({boundary['max_bytes_changed']})"
        )

    return {
        "operation_kind": action_kind,
        "file_writes": checked_writes,
        "file_deletes": checked_deletes,
    }, None


def _validate_adapter_report(raw: Any, operation: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ExecutionAdapterError(f"adapter.execute returned {raw!r}, not a mapping")
    files_written = raw.get("files_written")
    bytes_written = raw.get("bytes_written")
    files_deleted = raw.get("files_deleted")
    error = raw.get("error")
    if type(files_written) is not list or not all(type(p) is str for p in files_written):
        raise ExecutionAdapterError(
            f"adapter reported an unreadable files_written: {files_written!r}"
        )
    if type(bytes_written) is not int or isinstance(bytes_written, bool) or bytes_written < 0:
        raise ExecutionAdapterError(
            f"adapter reported an unreadable bytes_written: {bytes_written!r}"
        )
    if type(files_deleted) is not list or not all(type(p) is str for p in files_deleted):
        raise ExecutionAdapterError(
            f"adapter reported an unreadable files_deleted: {files_deleted!r}"
        )
    if error is not None and type(error) is not str:
        raise ExecutionAdapterError(f"adapter reported an unreadable error: {error!r}")

    requested_writes = {entry["path"] for entry in operation["file_writes"]}
    requested_deletes = {entry["path"] for entry in operation["file_deletes"]}
    unexpected_written = set(files_written) - requested_writes
    unexpected_deleted = set(files_deleted) - requested_deletes
    if unexpected_written or unexpected_deleted:
        raise ExecutionAdapterError(
            "adapter reported touching paths outside the admitted operation -- refusing to trust "
            f"a report naming written={sorted(unexpected_written)} deleted={sorted(unexpected_deleted)}"
        )
    return {
        "files_written": list(files_written),
        "bytes_written": bytes_written,
        "files_deleted": list(files_deleted),
        "error": error,
    }


def _classify_outcome(raw: dict[str, Any], operation: Mapping[str, Any]) -> str:
    requested_writes = {entry["path"] for entry in operation["file_writes"]}
    requested_deletes = {entry["path"] for entry in operation["file_deletes"]}
    complete = (
        set(raw["files_written"]) == requested_writes
        and set(raw["files_deleted"]) == requested_deletes
    )
    touched_anything = bool(raw["files_written"]) or bool(raw["files_deleted"])
    if raw["error"] is None and complete:
        return "SUCCEEDED"
    if touched_anything:
        return "PARTIAL_MUTATION"
    return "ADAPTER_FAILURE"


def _attempt_rollback(adapter: Any, worktree_root: str, files_written: list[str]) -> str:
    """Attempt to delete exactly the files the primary call reported writing -- a distinct,
    explicitly policy-gated second call to the adapter (see this module's own docstring,
    disclosed judgment call 4). Never raises: any adapter defect here is itself reported as a
    failed rollback, never escalated into an exception this route's own caller has to handle on
    top of the primary outcome it already has."""

    if not files_written:
        return "NOT_ATTEMPTED"
    rollback_operation = {
        "operation_kind": "DELETE_ISOLATED_SOURCE_FILE",
        "file_writes": [],
        "file_deletes": [{"path": path} for path in files_written],
    }
    try:
        raw = adapter.execute(rollback_operation, worktree_root=worktree_root)
        if not isinstance(raw, Mapping):
            return "ROLLBACK_FAILED"
        deleted = raw.get("files_deleted")
        if not isinstance(deleted, list) or set(deleted) != set(files_written) or raw.get("error"):
            return "ROLLBACK_FAILED"
    except Exception:  # a rollback failure is itself a reported outcome, never raised
        return "ROLLBACK_FAILED"
    return "ROLLBACK_SUCCEEDED"


def _commit_orphaned_attempt_unknown_receipt(
    *,
    store: Any,
    project_id: str,
    project_binding_id: str,
    slot_key: str,
    change_id: str,
    change: Mapping[str, Any],
    frozen_boundary: Mapping[str, Any],
    frozen_worktree_root: str,
    boundary_fp: str,
    claim_token: str,
    execution_instant: str,
    reobservation_request: Mapping[str, Any],
) -> dict[str, Any]:
    """(P18-R2-F3) Resolve a caller's own orphaned ``execution_attempt`` (attempt durably
    committed, no terminal receipt yet, this exact caller's own ``claim_token``) into one
    grounded, honest terminal ``UNKNOWN`` receipt -- directly from *reobservation_request*, the
    identical obligation already durably embedded on the attempt itself at commit time (P18-R2-F3
    part 1, ``engine.build_execution_attempt``) -- with zero adapter calls: the adapter may
    already have run (a genuine crash, or a final-pre-effect-barrier refusal, both leave the slot
    in this identical state), and re-calling it here would risk a real duplicate mutation.

    Deliberately does not re-run Boot, either kill-switch checkpoint, or the time-window check:
    none of those gate a *new* admission decision here (none is being made -- this call commits
    no new ``execution_intent``/``execution_attempt``, only concludes an already-admitted one
    honestly), exactly the same "a terminal outcome is read-only with respect to admission"
    reasoning that already lets idempotency-slot resolution as a whole run ahead of every
    admission check (disclosed judgment calls 5/12). ``boot_state_fingerprint`` is *change*'s own
    ``before_state_fingerprint`` -- the State this Change was authorized against, and therefore
    also what a fresh, non-resumed Boot would have equaled at this exact attempt's own original
    intent-commit time in the ordinary (non-drifted) case; imprecision here beyond that is
    inherent to an honestly-unknown outcome, not a defect this function could close.

    **The receipt's own ``operation`` field resolves and retains the exact admitted canonical
    operation, never a vacant echo (P18-R3-F3B, Structural Review Round 3).** Before this
    correction, this function unconditionally built ``operation`` as an empty echo
    (``operation_kind`` alone, no ``file_writes``/``file_deletes``) -- discarding what was
    actually admitted/requested even though the crash that orphaned this attempt may have
    happened *after* the adapter already performed the real mutation. This function now
    re-resolves *change*'s own admitted canonical operation the identical way the normal
    (non-orphan) path already does, via :func:`_operation_violation_reason` -- a pure
    validation/canonicalization call, never an adapter call, never a mutation, so safe to re-run
    here with zero risk of a duplicate real effect -- and uses that resolved operation as the
    grounded ``UNKNOWN`` receipt's own ``operation`` field. When the operation itself would be a
    boundary violation (``_operation_violation_reason`` returns ``None``), there was never
    anything real for the adapter to have touched, so the empty echo remains correct for that one
    case, matching the normal path's own ``BOUNDARY_VIOLATION`` receipt."""

    action_kind = change["action"]["action_kind"]
    # (P18-R3-F3B) Resolve and retain the exact admitted canonical operation -- the crash that
    # left this attempt orphaned may have happened after the adapter already performed it, so
    # the grounded UNKNOWN receipt must record what was genuinely requested, never a vacant
    # echo. _operation_violation_reason is a pure validation/canonicalization call (never an
    # adapter call, never a mutation) -- safe to re-run here. When the operation itself would
    # be a boundary violation, there was never anything real for the adapter to have touched,
    # so the empty echo remains correct for that one case, matching the normal
    # BOUNDARY_VIOLATION path's own receipt.
    checked_operation, _violation_reason = _operation_violation_reason(
        action_kind, change["action"]["operation"], frozen_boundary
    )
    empty_operation_echo = checked_operation or {
        "operation_kind": action_kind,
        "file_writes": [],
        "file_deletes": [],
    }
    empty_summary = {"files_written": [], "bytes_written": 0, "files_deleted": []}
    empty_result_fingerprint = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(empty_summary)).hexdigest()
    )
    receipt = build_change_execution_receipt(
        execution_request_id=slot_key,
        change_ref={"kind": "change", "id": change_id},
        idempotency_key=change["idempotency_key"],
        authority_ref=dict(change["authority_ref"]),
        project_id=project_id,
        project_binding_ref={"kind": "project_binding", "id": project_binding_id},
        boot_state_fingerprint=dict(change["before_state_fingerprint"]),
        execution_boundary_fingerprint=boundary_fp,
        executor_identity=frozen_boundary["executor_identity"],
        executor_version=frozen_boundary["executor_version"],
        target={
            "repository": frozen_boundary["repository"],
            "branch": frozen_boundary["branch"],
            "worktree_root": frozen_worktree_root,
        },
        operation=empty_operation_echo,
        execution_started_at=execution_instant,
        execution_ended_at=execution_instant,
        outcome="UNKNOWN",
        performed_result_fingerprint=empty_result_fingerprint,
        performed_result_summary=empty_summary,
        rollback_outcome=None,
        claim_token=claim_token,
        reobservation_request=dict(reobservation_request),
        independent_after_state_observation=NOT_PERFORMED_REOBSERVATION,
    )
    try:
        _commit_records(
            store,
            project_id,
            [(_RECEIPT_RECORD_KIND, slot_key, receipt)],
            execution_instant,
            transaction_prefix=f"TX-EXEC-RECEIPT-{slot_key}",
        )
    except RecordConflictError as error:
        raise ExecutionReceiptIntegrityError(
            f"a different change_execution_receipt already occupies mapping slot {slot_key!r} "
            "-- refusing rather than trust either"
        ) from error
    return receipt


def compose_change_executor(
    store: Any,
    *,
    project_id: str,
    project_binding_id: str,
    execution_boundary: Any,
    adapter_identity: Any,
    adapter: Any,
    kill_switch_trust_anchor_public_key_hex: str,
) -> Callable[..., dict[str, Any]]:
    """The one public, trusted composition step for Controlled Autonomous Change execution.

    Binds *store*, *project_id*, *project_binding_id*, a canonicalized-and-frozen Execution
    Boundary, a canonicalized-and-frozen adapter identity, the replaceable *adapter* itself, and
    the kill-switch trust anchor -- once, before any request exists -- and returns the
    request-facing operation itself, already closed over every one of them.
    ``worktree_root`` is no longer a separate parameter of this function at all (P18-R1-F3,
    Structural Review Round 1): it is now a required, schema-validated field *inside* the closed
    Execution Boundary itself (``execution_boundary["worktree_root"]``), validated by
    :func:`~manosube_agent_civilization.change_executor.boundary.validate_execution_boundary` the
    identical way every other Boundary field is (a non-empty string that resolves to a real,
    existing directory). Since :func:`~manosube_agent_civilization.change_executor.boundary.
    execution_boundary_fingerprint` already hashes the *entire* canonical boundary mapping, this
    makes ``worktree_root`` participate in the Boundary fingerprint -- and therefore in every
    mapping-slot key derived from it -- structurally, not merely by convention: two composed
    executors bound to genuinely different worktree roots now necessarily get different Boundary
    fingerprints and therefore different mapping slots (this module's own docstring, disclosed
    judgment call 6, superseded by this further correction). The returned closure's own call
    signature carries only request-facing data: ``execute(change_id, *, claim_token,
    execution_instant, permit_semantic_reuse=False)``. There is no keyword, positional slot, or
    attribute on the returned callable through which a caller could substitute a different Store,
    Boundary, adapter identity, adapter, worktree root, or trust anchor after the fact.
    """

    _require_canonical_identity("project_id", project_id)
    _require_canonical_identity("project_binding_id", project_binding_id)
    _require_non_empty_string(
        "kill_switch_trust_anchor_public_key_hex", kill_switch_trust_anchor_public_key_hex
    )
    if not callable(getattr(adapter, "execute", None)):
        raise ChangeExecutorError("adapter must declare a callable execute(...) method")

    canonical_boundary = validate_execution_boundary(execution_boundary)
    frozen_boundary = deep_freeze(canonical_boundary)
    boundary_fp = execution_boundary_fingerprint(canonical_boundary)
    # worktree_root is already validated (non-empty string resolving to a real, existing
    # directory) by validate_execution_boundary above -- its source is now the canonical Boundary
    # itself, never a separate parameter (P18-R1-F3).
    frozen_worktree_root = canonical_boundary["worktree_root"]

    # adapter_identity is canonicalized once, here, and reduced immediately to its own content
    # fingerprint -- the one value this closure actually needs to retain across every future
    # request (embedded in every execution_intent/execution_attempt this closure ever builds).
    # The canonicalized structure itself is not retained beyond this line, so no separate
    # deep_freeze step is needed for it the way frozen_boundary needs one.
    canonical_adapter_identity = canonicalize_inert_data(adapter_identity)
    adapter_fp = (
        "sha256:" + hashlib.sha256(canonical_json_bytes(canonical_adapter_identity)).hexdigest()
    )

    def execute(
        change_id: str,
        *,
        claim_token: str,
        execution_instant: str,
        permit_semantic_reuse: bool = False,
    ) -> dict[str, Any]:
        _require_canonical_identity("change_id", change_id)
        _require_non_empty_string("claim_token", claim_token)

        # (2) idempotency-slot resolution -- deliberately *before* time-window/kill-switch #1/
        # Boot/Change/Authority/staleness (P18-R1-F5, Structural Review Round 1, extending this
        # module's own disclosed judgment call 5: slot resolution already ran before Boot/
        # staleness for the identical reason -- a terminal outcome already reflects a fully-vetted
        # prior execution -- but a genuine correction moved it ahead of the *admission* checks
        # too. None of the three slot-resolution outcomes below (terminal replay, semantic reuse,
        # terminal-claim-mismatch, reconciliation-required) ever proceeds to Boot or any mutation,
        # so none of them need an admission check first -- gating a read-only return behind checks
        # that exist only to authorize a *new* side effect was itself the defect: a terminal
        # receipt committed while the bound Boundary's own validity_window was still current, or
        # while the kill switch was still ACTIVE, must still replay cleanly even after the window
        # has since expired or the kill switch has since been revoked -- replaying it performs no
        # Boot, no Store commit, and no adapter call regardless). Only the path that falls through
        # to "genuinely proceed" needs time-window/kill-switch #1 before Boot (below). The
        # mapping-slot key is a pure function of *change_id* (a caller-supplied parameter) and the
        # two fingerprints already bound at composition time, so resolving it needs neither Boot
        # nor the resolved Change record. This same step also resolves any existing
        # execution_intent for the slot (below, after the attempt check) -- a crash between the
        # intent commit and the following attempt commit leaves exactly an intent with no attempt
        # and no receipt, and this exact caller resuming it (identical claim_token) must not be
        # spuriously refused as stale either (disclosed judgment call 7).
        slot_key = execution_mapping_slot_key(change_id, boundary_fp, adapter_fp)
        change_ref = {"kind": "change", "id": change_id}

        resolved_receipt_raw = _resolve_slot_record(
            store, project_id, _RECEIPT_RECORD_KIND, slot_key
        )
        if resolved_receipt_raw is not None:
            receipt = _verify_slot_record(
                resolved_receipt_raw,
                kind=_RECEIPT_RECORD_KIND,
                declared_id_field="change_execution_receipt_id",
                recompute_id=_change_execution_receipt_id_of,
                recompute_fingerprint=change_execution_receipt_semantic_fingerprint,
                fingerprint_field="change_execution_receipt_semantic_fingerprint",
                slot_key=slot_key,
            )
            if receipt["claim_token"] == claim_token:
                return {"receipt": receipt, "replay": True, "semantic_reuse": False}
            if permit_semantic_reuse:
                return {"receipt": receipt, "replay": False, "semantic_reuse": True}
            raise ExecutionTerminalClaimMismatchError(
                f"a terminal change_execution_receipt already exists for this mapping slot "
                f"({slot_key!r}) under a different claim_token -- pass permit_semantic_reuse=True "
                "to explicitly reuse it"
            )

        resolved_attempt_raw = _resolve_slot_record(
            store, project_id, _ATTEMPT_RECORD_KIND, slot_key
        )
        if resolved_attempt_raw is not None:
            verified_attempt = _verify_slot_record(
                resolved_attempt_raw,
                kind=_ATTEMPT_RECORD_KIND,
                declared_id_field="execution_attempt_id",
                recompute_id=_execution_attempt_id_of,
                recompute_fingerprint=execution_attempt_semantic_fingerprint,
                fingerprint_field="execution_attempt_semantic_fingerprint",
                slot_key=slot_key,
            )
            if verified_attempt["claim_token"] != claim_token:
                # A different, genuinely concurrent/unrelated caller already holds this slot's
                # own orphaned attempt -- not this caller's own to resolve. Unchanged from before
                # P18-R2-F3.
                raise ExecutionReconciliationRequiredError(
                    f"an execution_attempt already exists for mapping slot {slot_key!r} with no "
                    "terminal change_execution_receipt yet, under a different claim_token than "
                    "this caller's own -- the true outcome of a prior attempt (which may already "
                    "have called the adapter) is genuinely unknown; refusing rather than risk a "
                    "duplicate real mutation"
                )
            # (P18-R2-F3) This exact caller (identical claim_token) resuming its OWN orphaned
            # attempt -- not a collision. From the instant execution_attempt became durable, it
            # already carried a typed re-observation obligation (its own embedded
            # reobservation_request -- disclosed judgment call 16 below) and this resolves to a
            # grounded, honest terminal UNKNOWN receipt built directly from that durably
            # committed record -- zero adapter calls, since the adapter may already have run
            # (a genuine crash, or the final pre-effect barrier's own refusal, both leave the
            # slot in this identical state) and re-calling it here would risk a real duplicate
            # mutation. This closes the prior permanent ExecutionReconciliationRequiredError trap
            # for this exact caller; a different caller (above) is still refused unchanged.
            # (see this module's own module docstring, disclosed judgment calls 16-17, for the
            # full P18-R2-F3 discipline)
            change_for_resume = _resolve_change(store, project_id, change_id)
            receipt = _commit_orphaned_attempt_unknown_receipt(
                store=store,
                project_id=project_id,
                project_binding_id=project_binding_id,
                slot_key=slot_key,
                change_id=change_id,
                change=change_for_resume,
                frozen_boundary=frozen_boundary,
                frozen_worktree_root=frozen_worktree_root,
                boundary_fp=boundary_fp,
                claim_token=claim_token,
                execution_instant=execution_instant,
                reobservation_request=verified_attempt["reobservation_request"],
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (2, continued) resolve any existing execution_intent for the slot -- reached only when
        # neither a receipt nor an attempt exists yet. When one exists and its own declared
        # claim_token equals this call's own, this call is that exact caller resuming its own
        # crash-interrupted attempt (intent committed, attempt never reached) -- not a collision
        # -- so the staleness check below is skipped for this call alone (disclosed judgment call
        # 7). A *different* claim_token is not a resume: it is left unflagged here and correctly
        # falls through to collide at the intent-commit step (RecordConflictError ->
        # ExecutionConcurrentClaimError), unchanged from before this fix.
        resuming_from_existing_intent = False
        resolved_intent_raw = _resolve_slot_record(store, project_id, _INTENT_RECORD_KIND, slot_key)
        if resolved_intent_raw is not None:
            verified_intent = _verify_slot_record(
                resolved_intent_raw,
                kind=_INTENT_RECORD_KIND,
                declared_id_field="execution_intent_id",
                recompute_id=_execution_intent_id_of,
                recompute_fingerprint=execution_intent_semantic_fingerprint,
                fingerprint_field="execution_intent_semantic_fingerprint",
                slot_key=slot_key,
            )
            resuming_from_existing_intent = verified_intent["claim_token"] == claim_token

        # (3) time-window check -- zero-call, before Boot or any adapter. Reached only for a
        # genuinely new or resumed mapping slot (P18-R1-F5): a terminal outcome above already
        # returned or raised without ever reaching this line.
        require_within_time_window(frozen_boundary, execution_instant)

        # (4) kill switch check #1.
        _require_active_kill_switch_verified(
            store, project_id, kill_switch_trust_anchor_public_key_hex, stage="before Boot"
        )

        # (5) fresh Boot. Reached for a genuinely new mapping slot, or one being resumed after a
        # crash between the intent and attempt commits -- the live current State is the correct
        # one to Boot and (ordinarily) stale-check against below.
        boot_context = boot_project(
            store, project_id=project_id, project_binding_id=project_binding_id
        )

        # (6) resolve the Change.
        change = _resolve_change(store, project_id, change_id)

        # (7) resolve the Authority Decision the Change names, require AUTONOMOUS.
        decision = _resolve_authority_decision(store, project_id, change["authority_ref"]["id"])
        if decision["decision"] != AUTONOMOUS:
            raise ExecutionAuthorityProvenanceError(
                f"the Authority Decision behind change {change_id!r} is not AUTONOMOUS: "
                f"{decision['decision']!r}"
            )

        # (8) action_kind in the bound Boundary's own permitted set, and not Human-only.
        action_kind = change["action"]["action_kind"]
        if action_kind not in frozen_boundary["permitted_action_kinds"]:
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own action_kind is not permitted by the bound Execution "
                f"Boundary: {action_kind!r}"
            )
        if action_kind in HUMAN_ONLY_ACTION_KINDS:
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own action_kind is a Human-only action kind: {action_kind!r}"
            )

        # (9) scope entirely admitted by the bound Boundary.
        scope = change["scope"]
        if (
            scope["repository"] != frozen_boundary["repository"]
            or scope["branch"] != frozen_boundary["branch"]
        ):
            raise ExecutionAuthorityProvenanceError(
                f"change {change_id!r} own scope names a different repository/branch than the "
                "bound Execution Boundary"
            )
        for path in scope["paths"]:
            if not path_is_admitted(path, frozen_boundary["admitted_paths"]):
                raise ExecutionAuthorityProvenanceError(
                    f"change {change_id!r} own scope names a path the bound Execution Boundary "
                    f"does not admit: {path!r}"
                )

        # (10) staleness (P18-R1-F2, Structural Review Round 1, replacing the prior round's
        # blanket resuming_from_existing_intent skip). When *not* resuming, the freshly Booted
        # current State must equal exactly what this Change was authorized against, unchanged.
        # When *resuming* a crash-interrupted intent (resuming_from_existing_intent, set at step
        # 2 above), a blanket skip is no longer trusted: instead this requires an *exact* check
        # that the freshly Booted current State is precisely the intent-commit's own direct
        # successor and nothing else landed in between -- state_revision is exactly one past what
        # this Change was authorized against (accounting for the one intent commit that already
        # happened before this call), and the chain-link fingerprint
        # (``previous_state_fingerprint``, which ``_commit_records`` always sets from the prior
        # State's own ``semantic_fingerprint``) genuinely equals this Change's own
        # ``before_state_fingerprint`` -- proving the intent commit really was the *only* thing
        # that happened since this Change was authorized, not merely that *some* commit happened
        # to land on the expected revision number by coincidence. A caller resuming its own
        # crash-interrupted intent is not staleness (disclosed judgment call 7); an unrelated
        # transition racing in between the authorized State and now still is.
        current_fingerprint = dict(boot_context.current_state["semantic_fingerprint"])
        if resuming_from_existing_intent:
            if boot_context.current_state["state_revision"] != change[
                "expected_state_revision"
            ] + 1 or dict(boot_context.current_state["previous_state_fingerprint"]) != dict(
                change["before_state_fingerprint"]
            ):
                raise StaleExecutionInputError(
                    f"change {change_id!r} own before_state_fingerprint/expected_state_revision "
                    "-- resuming a crash-interrupted intent, but the current State is not the "
                    "exact immediate successor of the State this Change was authorized against "
                    "-- an unrelated transition landed in between; refusing rather than trust a "
                    "blanket resume"
                )
        elif (
            dict(change["before_state_fingerprint"]) != current_fingerprint
            or change["expected_state_revision"] != boot_context.current_state["state_revision"]
        ):
            raise StaleExecutionInputError(
                f"change {change_id!r} own before_state_fingerprint/expected_state_revision no "
                "longer matches the freshly Booted current State -- blocked as stale, never "
                "executed against a State it did not observe"
            )

        # (10a) build reobservation_request -- moved here, *before* the intent/attempt commits
        # (P18-R2-F3 part 1, Structural Review Round 2), so it can be embedded durably inside
        # execution_attempt itself at commit time (below), not merely recomputed fresh after the
        # fact at each terminal-receipt call site. Everything it depends on (frozen_boundary,
        # change_ref, the resolved Change's own scope, execution_instant) is already known by
        # this point. The one canonical scope-normalization owner (`authority.scope.
        # canonical_scope`) is used here rather than a local sort -- re-sorting
        # `scope["paths"]` in this module would be a second, competing answer to what the
        # canonical member order is (`tests/contract/authority/
        # test_scope_normalization_owner.py`'s own static sweep).
        canonical_change_scope = canonical_scope(scope)
        reobservation_request = {
            "kind": "change_execution_reobservation_request",
            "target": {
                "repository": frozen_boundary["repository"],
                "branch": frozen_boundary["branch"],
                "paths": canonical_change_scope["paths"],
            },
            "reason_codes": ["AUTONOMOUS_CHANGE_EXECUTION_ATTEMPTED"],
            "requested_at": execution_instant,
        }

        # (11) commit execution_intent.
        intent = build_execution_intent(
            project_id=project_id,
            change_ref=change_ref,
            execution_boundary_fingerprint=boundary_fp,
            adapter_identity_fingerprint=adapter_fp,
            claim_token=claim_token,
            requested_at=execution_instant,
        )
        try:
            _commit_records(
                store,
                project_id,
                [(_INTENT_RECORD_KIND, slot_key, intent)],
                execution_instant,
                transaction_prefix=f"TX-EXEC-INTENT-{slot_key}",
            )
        except RecordConflictError as error:
            raise ExecutionConcurrentClaimError(
                f"a different execution_intent already occupies mapping slot {slot_key!r} -- a "
                "genuinely concurrent claim under a different claim_token, refused rather than "
                "silently retried into an attempt"
            ) from error

        # (12) commit execution_attempt. attempt_nonce is a fresh, cryptographically random
        # per-call token (never caller-supplied, never derived from any other input), generated
        # only on this path -- the one that actually builds a genuinely new attempt -- so two
        # independent callers racing to build a fresh attempt for the identical slot produce two
        # different, non-reproducible attempt bodies: the Store's own existing conflict-detection
        # (a same-(kind, id)-different-body record is a real RecordConflictError) then correctly
        # refuses the second one instead of treating it as an idempotent replay of the first
        # (disclosed judgment call 8).
        attempt = build_execution_attempt(
            project_id=project_id,
            change_ref=change_ref,
            execution_boundary_fingerprint=boundary_fp,
            adapter_identity_fingerprint=adapter_fp,
            claim_token=claim_token,
            requested_at=execution_instant,
            execution_intent_ref={"kind": _INTENT_RECORD_KIND, "id": slot_key},
            attempt_nonce=secrets.token_hex(16),
            reobservation_request=reobservation_request,
        )
        try:
            attempt_commit_result = _commit_records(
                store,
                project_id,
                [(_ATTEMPT_RECORD_KIND, slot_key, attempt)],
                execution_instant,
                transaction_prefix=f"TX-EXEC-ATTEMPT-{slot_key}",
            )
        except RecordConflictError as error:
            raise ExecutionConcurrentClaimError(
                f"a different execution_attempt already occupies mapping slot {slot_key!r} -- a "
                "genuinely concurrent claim, refused rather than silently retried into an "
                "adapter call"
            ) from error
        # The exact state_revision this route's own two commits (intent, then attempt) actually
        # produced -- the empirical value the final pre-effect State barrier (P18-R1-F2, below)
        # compares a fresh re-fetch against, immediately before the one real side effect.
        post_attempt_state_revision = attempt_commit_result["state_revision"]

        # (P18-R2-F3 part 1) Every terminal-receipt call site below reads its own
        # reobservation_request back off the durably committed attempt record itself, rather
        # than recomputing it independently -- the identical content either way (this route
        # itself just built and committed it), but reading it back is what actually proves the
        # receipt's own embedded obligation is the *same* one the attempt durably preserved from
        # the instant it became committed (the exact fact the resumed-orphaned-attempt path
        # above depends on, and every other path here now shares).
        reobservation_request = attempt["reobservation_request"]

        authority_ref = {"kind": "authority_decision", "id": decision["authority_decision_id"]}
        project_binding_ref = {"kind": "project_binding", "id": project_binding_id}
        target = {
            "repository": frozen_boundary["repository"],
            "branch": frozen_boundary["branch"],
            "worktree_root": frozen_worktree_root,
        }

        def _commit_terminal_receipt(
            *,
            outcome: str,
            performed_result_summary: dict[str, Any],
            performed_result_fingerprint: str,
            rollback_outcome: str | None,
            operation_echo: dict[str, Any],
            independent_after_state_observation: dict[str, Any],
        ) -> dict[str, Any]:
            receipt = build_change_execution_receipt(
                execution_request_id=slot_key,
                change_ref=change_ref,
                idempotency_key=change["idempotency_key"],
                authority_ref=authority_ref,
                project_id=project_id,
                project_binding_ref=project_binding_ref,
                boot_state_fingerprint=current_fingerprint,
                execution_boundary_fingerprint=boundary_fp,
                executor_identity=frozen_boundary["executor_identity"],
                executor_version=frozen_boundary["executor_version"],
                target=target,
                operation=operation_echo,
                execution_started_at=execution_instant,
                execution_ended_at=execution_instant,
                outcome=outcome,
                performed_result_fingerprint=performed_result_fingerprint,
                performed_result_summary=performed_result_summary,
                rollback_outcome=rollback_outcome,
                claim_token=claim_token,
                reobservation_request=reobservation_request,
                independent_after_state_observation=independent_after_state_observation,
            )
            try:
                _commit_records(
                    store,
                    project_id,
                    [(_RECEIPT_RECORD_KIND, slot_key, receipt)],
                    execution_instant,
                    transaction_prefix=f"TX-EXEC-RECEIPT-{slot_key}",
                )
            except RecordConflictError as error:
                raise ExecutionReceiptIntegrityError(
                    f"a different change_execution_receipt already occupies mapping slot "
                    f"{slot_key!r} -- refusing rather than trust either"
                ) from error
            return receipt

        _empty_operation_echo = {
            "operation_kind": action_kind,
            "file_writes": [],
            "file_deletes": [],
        }
        _empty_summary = {"files_written": [], "bytes_written": 0, "files_deleted": []}
        _empty_result_fingerprint = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(_empty_summary)).hexdigest()
        )

        # (13) kill switch check #2 -- immediately before the one adapter call. A refusal here
        # still produces a terminal receipt (see this module's own disclosed judgment call 3).
        try:
            _require_active_kill_switch_verified(
                store,
                project_id,
                kill_switch_trust_anchor_public_key_hex,
                stage="immediately before the adapter call",
            )
        except ExecutionKillSwitchError:
            receipt = _commit_terminal_receipt(
                outcome="KILL_SWITCH_STOPPED",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=_empty_operation_echo,
                independent_after_state_observation=NOT_PERFORMED_REOBSERVATION,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (14) build + validate the closed operation against the bound Boundary's own limits.
        # The violation reason itself is deliberately not persisted on the receipt --
        # performed_result_summary is schema-closed to files_written/bytes_written/files_deleted
        # (the identical bounded discipline the Boundary itself enforces), so a free-text reason
        # has no admissible field to live in; only the closed BOUNDARY_VIOLATION outcome is.
        checked_operation, _violation_reason = _operation_violation_reason(
            action_kind, change["action"]["operation"], frozen_boundary
        )
        if checked_operation is None:
            receipt = _commit_terminal_receipt(
                outcome="BOUNDARY_VIOLATION",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=_empty_operation_echo,
                independent_after_state_observation=NOT_PERFORMED_REOBSERVATION,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (14a) final pre-effect State barrier (P18-R1-F2, Structural Review Round 1) --
        # immediately before the one real side effect, after both the intent and attempt commits,
        # after kill-switch check #2, and after operation build/validation: re-fetch the current
        # State and require its own state_revision to be *exactly* post_attempt_state_revision,
        # the empirical value this route's own two commits (intent, then attempt) actually just
        # produced. If it has advanced *further* than that, an unrelated transition landed in the
        # narrow window between this route's own attempt commit finishing and this exact point --
        # refuse before the adapter is ever called, zero further mutation. Deliberately a raised
        # exception here, not a third terminal-receipt-producing path alongside kill-switch #2/
        # Boundary-violation (disclosed judgment call 3): unlike those two, this barrier detects a
        # condition under which *nothing* about this call's own eligibility to execute is actually
        # known to have changed except that something else, entirely unrelated, raced in --
        # StaleExecutionInputError is the honest, typed answer, and it leaves the slot in exactly
        # the same "attempt committed, no receipt yet" state a genuine crash would, which any
        # future caller for this identical slot already correctly resolves as
        # ExecutionReconciliationRequiredError (this package's own existing, typed, fail-closed
        # answer for "the true outcome is not yet known") -- never silently proceeding to mutate
        # against a State this call did not itself produce.
        fresh_state = store.load_current(project_id)
        if fresh_state["state_revision"] != post_attempt_state_revision:
            raise StaleExecutionInputError(
                f"change {change_id!r}: an unrelated State transition landed between this call's "
                "own execution_attempt commit and the one adapter call -- refusing rather than "
                f"mutate against a State this call did not itself produce (observed revision "
                f"{fresh_state['state_revision']!r}, expected exactly "
                f"{post_attempt_state_revision!r})"
            )

        # (15) call adapter.execute(...) exactly once for the primary requested operation. Every
        # path reachable from here on -- a raised exception, a structurally invalid report, or a
        # validated report -- now commits exactly one terminal receipt, never a bare exception
        # (P18-R1-F4, Structural Review Round 1, extending this module's own disclosed judgment
        # call 3 to the two paths that previously did not follow it): an execution_attempt is
        # already durably committed by this point, so a bare exception here would strand the slot
        # behind ExecutionReconciliationRequiredError forever, with no terminal receipt for any
        # future caller -- or any embedded reobservation_request -- to resolve against.
        try:
            raw_report = adapter.execute(checked_operation, worktree_root=frozen_worktree_root)
        except Exception:
            # The adapter itself raised, rather than returning a raw-facts report: nothing about
            # its own partial effects, if any, is trustworthy enough to report -- the safe,
            # honest default is "we do not know what happened" (the identical closed-record
            # discipline already established for BOUNDARY_VIOLATION above: performed_result_
            # summary is schema-closed to files_written/bytes_written/files_deleted, so the
            # exception's own text has no admissible field to live in; only the closed UNKNOWN
            # outcome is). Independent re-observation is deliberately skipped for this path (it
            # would itself be untrustworthy evidence about an adapter call whose own effects are
            # unknown), but the identical reobservation_request this route always builds is still
            # embedded, so an independent re-observation is still requested even though this
            # package cannot itself confirm what happened.
            receipt = _commit_terminal_receipt(
                outcome="UNKNOWN",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=checked_operation,
                independent_after_state_observation=NOT_PERFORMED_REOBSERVATION,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        try:
            checked_report = _validate_adapter_report(raw_report, checked_operation)
        except ExecutionAdapterError:
            # The adapter returned, but its own report cannot be trusted as a result --
            # structurally unreadable, or naming a file outside the exact operation this route
            # admitted. Identical treatment to a raised exception immediately above: a terminal
            # UNKNOWN-outcome receipt, embedded reobservation_request, never a bare exception.
            receipt = _commit_terminal_receipt(
                outcome="UNKNOWN",
                performed_result_summary=_empty_summary,
                performed_result_fingerprint=_empty_result_fingerprint,
                rollback_outcome=None,
                operation_echo=checked_operation,
                independent_after_state_observation=NOT_PERFORMED_REOBSERVATION,
            )
            return {"receipt": receipt, "replay": False, "semantic_reuse": False}

        # (15a) independent after-state re-observation (P18-R1-F1, Structural Review Round 1) --
        # a genuine, read-only re-read of the actual resulting filesystem state, performed by
        # this package itself, entirely separate from -- and never trusting -- the adapter's own
        # self-reported raw facts (`checked_report`) as proof of content. See
        # `reobservation.independently_reobserve`'s own docstring for the full discipline.
        reobservation_result = independently_reobserve(
            checked_operation, frozen_worktree_root, checked_report
        )

        # (16) classify the adapter's raw reported facts.
        outcome = _classify_outcome(checked_report, checked_operation)

        # (16a) gate: only when both the adapter's own raw facts AND this independent re-read
        # agree the operation fully succeeded may the receipt's own outcome be SUCCEEDED
        # (P18-R1-F1). A would-be SUCCEEDED that this independent re-read disagrees with is a
        # different, typed outcome -- REOBSERVATION_MISMATCH -- never silently reused as
        # SUCCEEDED. This does not change PARTIAL_MUTATION/ADAPTER_FAILURE classification: those
        # are already bounded failures the adapter's own raw facts admit to, not a claim of full
        # success this independent re-read needs to confirm or refute.
        if outcome == "SUCCEEDED" and reobservation_result["outcome"] != "MATCHED":
            outcome = "REOBSERVATION_MISMATCH"

        rollback_outcome: str | None = None
        if outcome in ("PARTIAL_MUTATION", "ADAPTER_FAILURE") and checked_report["files_written"]:
            if frozen_boundary["rollback_policy"] == "BEST_EFFORT_DELETE_WRITTEN_FILES":
                rollback_outcome = _attempt_rollback(
                    adapter, frozen_worktree_root, checked_report["files_written"]
                )
                if rollback_outcome == "ROLLBACK_SUCCEEDED":
                    outcome = "ROLLBACK_SUCCEEDED"
                elif rollback_outcome == "ROLLBACK_FAILED":
                    outcome = "ROLLBACK_FAILED"
            else:
                rollback_outcome = "NOT_ATTEMPTED"

        performed_result_summary = {
            "files_written": checked_report["files_written"],
            "bytes_written": checked_report["bytes_written"],
            "files_deleted": checked_report["files_deleted"],
        }
        performed_result_fingerprint = (
            "sha256:" + hashlib.sha256(canonical_json_bytes(checked_report)).hexdigest()
        )

        # (17) build + commit the terminal receipt.
        receipt = _commit_terminal_receipt(
            outcome=outcome,
            performed_result_summary=performed_result_summary,
            performed_result_fingerprint=performed_result_fingerprint,
            rollback_outcome=rollback_outcome,
            operation_echo=checked_operation,
            independent_after_state_observation=reobservation_result,
        )

        # (18) return.
        return {"receipt": receipt, "replay": False, "semantic_reuse": False}

    return execute


__all__ = ["compose_change_executor"]
