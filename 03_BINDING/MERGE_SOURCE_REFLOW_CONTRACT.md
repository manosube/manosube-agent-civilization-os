# MANOSUBE Agent Civilization OS

## Merge Source Reflow Contract (Issue #57)

```text
DOC_TYPE=GOVERNANCE_OPERATING_GUIDE
SYSTEM=MANOSUBE_AGENT_CIVILIZATION_OS
DOCUMENT_ID=MERGE-SOURCE-REFLOW-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
KERNEL_ELEMENT=none
DECISION_AUTHORITY=SHUKOU
ADOPTION_ID=ADOPT_MERGE_SOURCE_REFLOW_MACHINE_OWNED_CONVERGENCE
CORRECTION_ROUND_1_ADOPTION_ID=ADOPT_MSR_R1_EVENT_BOUND_REVALIDATED_AND_PATH_HARDENED_REFLOW
GOVERNING_ISSUE=#57
RUNTIME_ENFORCEMENT_IMPLEMENTED=partial
```

---

## 0. What this document is

Issue #54 (merged PR #55) gave this repository read-only source-freshness *detection*.
Detection alone does not stop `HANDOFF.md`, `SHA256SUMS`, generated repository facts, the
README generated status block, and the variable portions of `docs/project_sources/` from
staying stale after a manually accepted merge. Issue #57 owns that separate difference --
`MERGE_SOURCE_REFLOW` -- and this document is its operating guide. It does not expand Issue
#53/PR #56's own scope, does not alter Issue #51/PR #52 (Phase 13), and does not accept a
Phase or start Phase 14.

```text
MERGE_SOURCE_REFLOW_IS_A_NEW_KERNEL_ELEMENT=false
MERGE_SOURCE_REFLOW_IS_A_NEW_AUTHORITY_OWNER=false
MERGE_SOURCE_REFLOW_MODIFIES_ISSUE_53_OR_PR_56=false
MERGE_SOURCE_REFLOW_MODIFIES_PHASE_13_SEMANTICS=false
```

`scripts/source_impact_gate.py` is the pre-merge stage's enforcement;
`scripts/merge_source_reflow.py` is the post-merge stage's enforcement;
`tests/contract/governance/test_source_impact_gate.py` and
`tests/contract/governance/test_merge_source_reflow.py` are their proof.

### 0.1 Structural Review Round 1 (MSR-R1)

SHUKOU adopted [`ADOPT_MSR_R1_EVENT_BOUND_REVALIDATED_AND_PATH_HARDENED_REFLOW`](https://github.com/manosube/manosube-agent-civilization-os/issues/57#issuecomment-5567433361)
(Issue #57 comment 5567433361; independently re-verified via the GitHub API, `REVIEWED_HEAD`
matched this PR's live head, `b129a919`, exactly before any action). Four corrections, all
implemented in place on the same PR:

- **MSR-R1-F1**: the post-merge workflow now triggers on `pull_request: types: [closed]`
  guarded by `github.event.pull_request.merged == true` -- once per manually merged Pull
  Request, never on every push to `main`. `main_sha` is that Pull Request's own
  `merge_commit_sha`; `observed_at_utc` is its own `merged_at`. Both are bound to the merge
  event itself, not to whenever the job happens to run (§9).
- **MSR-R1-F2**: candidate-output validation (source-freshness/drift detection against the
  already-reflowed, not-yet-committed working tree) now runs *before* any `git add`,
  `git commit`, or `git push` -- a validation failure leaves `main` untouched (§11).
- **MSR-R1-F3**: the post-merge workflow enforces its own literal, workflow-defined path
  allowlist against the actual working-tree diff before staging -- it never trusts
  `merge_source_reflow.py`'s own reported `files_written` list as sole authority (§11).
  `merge_source_reflow.py`, `source_impact_gate.py`, and both reflow workflow files are now
  themselves `protected_governance_surface` paths the pre-merge gate requires a paired
  `03_BINDING/` update to change (§2).
- **MSR-R1-F4**: the pre-merge gate's kernel_surface pairing requirement is now derived
  from a closed, declared `KERNEL_SURFACE_IMPACT_MAP` rather than "any
  `docs/project_sources/*.md` update" -- an unrelated document no longer satisfies an
  unrelated kernel_surface obligation (§2).

## 1. The canonical two-stage sequence

```text
PR opened against main
  ↓
pre-merge source-impact gate classifies every changed path (six classes, §2)
  ↓
REQUIRED_SOURCE_UPDATE_MISSING or REQUIRED_GOVERNANCE_UPDATE_MISSING  ->  MERGE_BLOCKED
  ↓ (otherwise)
SHUKOU manually merges (this mechanism never merges)
  ↓
that Pull Request's own "closed as merged" event fires the post-merge workflow, bound to
its merge_commit_sha and merged_at (MSR-R1-F1) -- never a generic push-to-main trigger
  ↓
post-merge reflow computes candidate output for only the declared machine-owned surfaces
  ↓
candidate validated against source-freshness/drift detection BEFORE any commit (MSR-R1-F2);
a failure here leaves main untouched
  ↓
the actual working-tree diff is checked against the workflow's own literal allowlist
before staging (MSR-R1-F3)
  ↓
one bounded, generated-only reflow commit (or none, if already converged)
  ↓
source freshness and drift detection rerun against the new main state
```

The reflow commit is a *successor* to the manually accepted merge. It never rewrites,
amends, or force-pushes over the merge commit it follows. Because the reflow commit is a
direct push rather than a Pull Request being closed as merged, this workflow's own trigger
(MSR-R1-F1) never fires on it at all -- recursion is prevented structurally, before the
idempotence argument in §7 is even needed.

## 2. Ownership classification (the pre-merge gate's own table)

Every changed path in a pull request against `main` falls into exactly one of six closed
classes, determined by prefix match against this table -- `source_impact_gate.py`'s
`classify_path` implements it verbatim, and `test_source_impact_gate.py` proves every row.

```text
class                          path prefix (or exact path)                requires a paired
                                                                            update
kernel_surface                 src/, 00_KERNEL/, 01_SCHEMA/, 02_ENGINE/,   yes -- a source_
                                04_BOOT/, 05_CLI/, 07_AGENT_RUNTIME/,      document from that
                                pyproject.toml (exact)                    area's own
                                                                           KERNEL_SURFACE_
                                                                           IMPACT_MAP entry
                                                                           (below)
source_document                docs/project_sources/*.md (excluding       n/a (this *is* a
                                generated/)                               candidate update)
generated                      docs/project_sources/generated/,           no
                                HANDOFF.md (exact), SHA256SUMS (exact),
                                README.md (exact)
governance_binding             03_BINDING/                                n/a (this *is* the
                                                                           required update)
protected_governance_surface   scripts/merge_source_reflow.py,            yes -- any
                                scripts/source_impact_gate.py,             governance_binding
                                .github/workflows/merge_source_            path
                                pre_merge_gate.yml,
                                .github/workflows/merge_source_
                                post_merge_reflow.yml (all exact)
other                          everything else (tests/, most of           no
                                scripts/, docs/decisions/, examples/, ...)
```

`scripts/` and `tests/` are deliberately **not** `kernel_surface`: a governance-automation
or test-only change does not by itself force a `docs/project_sources/` update, only an
actual `src/`/Kernel/Schema/Boot/CLI/Agent-runtime change does. But the four exact paths
that *implement* Merge Source Reflow's own enforcement are `protected_governance_surface`
(MSR-R1-F3), not merely `other`: a change to the executor scripts or either reflow workflow
file is itself a governance-sensitive event, and must be paired with a `03_BINDING/`
update. This Issue's own PR touches all four protected paths and pairs them with this same
document, so the gate -- run against this PR -- still passes; that self-consistency is
checked directly by `test_source_impact_gate.py`.

```text
OS_CHANGE_DETECTED = any changed path classifies kernel_surface
REQUIRED_SOURCE_UPDATE_MISSING = there exists a touched kernel_surface area whose own
                                  KERNEL_SURFACE_IMPACT_MAP required-document set has no
                                  member among the changed source_document paths
PROTECTED_SURFACE_CHANGED = any changed path classifies protected_governance_surface
REQUIRED_GOVERNANCE_UPDATE_MISSING = PROTECTED_SURFACE_CHANGED and no changed path
                                      classifies governance_binding
MERGE_BLOCKED = REQUIRED_SOURCE_UPDATE_MISSING or REQUIRED_GOVERNANCE_UPDATE_MISSING
```

`README.md` classifies `generated` even though most of its bytes are Human prose: path-based
classification cannot see which byte range changed, and the file's own bounded-block
technique (§4) is what actually protects the Human portion. A `README.md`-only change
therefore never counts as the required paired `source_document` update -- only an actual
`docs/project_sources/*.md` change does.

### 2.1 The closed impact mapping (MSR-R1-F4)

Before Round 1, *any* `docs/project_sources/*.md` change satisfied *any* kernel_surface
obligation -- pairing an unrelated `05_CLI/` change with an edit to, say,
`06_DEFERRED_DIFFERENCES.md` incorrectly passed the gate. `KERNEL_SURFACE_IMPACT_MAP` closes
that gap: a declared, per-area mapping from each `KERNEL_SURFACE_PREFIXES`/
`KERNEL_SURFACE_EXACT` key to the specific `source_document` path(s) legitimate for that
area.

```text
every kernel_surface area  ->  { docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md,
                                  docs/project_sources/04_REPOSITORY_ARCHITECTURE.md }
```

Every area maps to the identical two-document set today, since both documents legitimately
describe any OS-implementation change (current state, and as-built architecture,
respectively) -- but the mapping is declared *per area*, not globally, specifically so it
can be refined to per-subsystem granularity later without changing `build_manifest`'s own
admission logic. `test_an_unrelated_source_document_does_not_satisfy_a_kernel_surface_obligation`
and `test_kernel_surface_impact_map_is_closed_and_covers_every_declared_area` prove this
directly.

## 3. Post-merge reflow: what is regenerated

```text
docs/project_sources/generated/CURRENT_REPOSITORY_FACTS.json
    the observed main_sha, observed_at_utc, and a verbatim re-projection of whichever
    KEY=VALUE fields docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md's own fenced
    ```text block already records -- never a new judgment, the identical extraction
    validate_source_freshness.extract_fields already performs
docs/project_sources/generated/REPOSITORY_TREE.txt
    a deterministic, sorted listing of every tracked file path
docs/project_sources/generated/PHASE_EVIDENCE_INDEX.json
    a verbatim re-projection of docs/project_sources/05_PHASE_ACCEPTANCE_LEDGER.md's own
    fenced ```text block fields, labelled a candidate -- never Phase acceptance itself
docs/project_sources/generated/SOURCE_REFLOW_RECEIPT.json
    the convergence receipt (§6)
HANDOFF.md
    one bounded generated block (§4) -- generated inventory, SHA, transfer status
SHA256SUMS
    full deterministic regeneration (§5) -- never hashes itself
README.md
    its existing bounded generated block, via the unchanged Issue #54
    generate_readme_status_block.py
```

No other path is ever written by `merge_source_reflow.py`. In particular, it never writes
to any `docs/project_sources/*.md` file directly (only its own `generated/` subdirectory),
never to any `03_BINDING/`, `00_KERNEL/`, `01_SCHEMA/`, or `src/` path, and never to the
GitHub Actions workflow files that invoke it (`WORKFLOW_SELF_MODIFICATION=false`).

## 4. The generated-boundary contract

A file that mixes Human prose and machine-owned content (`README.md`, `HANDOFF.md`) marks
its machine-owned range with exactly one pair of HTML-comment markers:

```text
<!-- SOURCE_STATUS:GENERATED:BEGIN -->  ... <!-- SOURCE_STATUS:GENERATED:END -->   (README.md, Issue #54)
<!-- HANDOFF_STATUS:GENERATED:BEGIN -->  ... <!-- HANDOFF_STATUS:GENERATED:END -->  (HANDOFF.md, Issue #57)
```

`scripts/bounded_generated_block.py` holds the one replacement primitive both writers use:
it refuses (`SystemExit`), never silently appends or guesses, when a file does not carry
exactly one well-ordered marker pair. `merge_source_reflow.py` additionally hashes every
byte *outside* the marker pair before and after a regeneration and refuses to report
convergence if that hash changed -- the mechanical proof behind
`HUMAN_TEXT_HASH_BEFORE=HUMAN_TEXT_HASH_AFTER`.

```text
EDIT_OUTSIDE_GENERATED_BOUNDARY=PROHIBITED
PATH_ALLOWLIST_ENFORCED=true
```

`merge_source_reflow.ALLOWLISTED_GENERATED_PATHS` is the closed set of paths §3 names.
`reflow()` computes every output in memory first and only writes a path if it is a member
of that set; `test_merge_source_reflow.py` proves both that every real write stays inside
the allowlist and that no combination of malicious/malformed input can make it write
outside it.

## 5. `SHA256SUMS`

A deterministic manifest over exactly the files §3 names as machine-touched (the
`generated/` files, `HANDOFF.md`, `README.md`) plus every Human-authored
`docs/project_sources/*.md` document, sorted by repository-relative path, one
`<sha256>  <path>` line per file. `SHA256SUMS` itself is never a member of its own manifest
-- and neither is `docs/project_sources/generated/SOURCE_REFLOW_RECEIPT.json`, the one
`generated/` file this exclusion necessarily covers: the receipt's own `sha256sums_digest`
field (§6) is computed *from* `SHA256SUMS`'s already-written bytes, so `SHA256SUMS` cannot
also depend on the receipt without a circular dependency neither file could resolve.

## 6. The convergence receipt

`docs/project_sources/generated/SOURCE_REFLOW_RECEIPT.json` records, for one reflow run:

```text
schema_version
reflowed_main_sha              the exact main SHA this reflow was computed against
observed_at_utc
files_written                  paths actually changed by this run (may be empty --
                                a no-op run is not a failure, see §7)
files_unchanged                allowlisted paths this run computed but left byte-identical
human_text_converged           true only if every bounded-block file's outside-marker
                                bytes hashed identically before and after
sha256sums_digest              sha256 of the regenerated SHA256SUMS file itself, so a
                                caller can verify no further tampering after this receipt
                                was written
convergence_proven             true only when every one of the above holds
```

A caller that reads `convergence_proven=false` must treat the reflow as failed and take no
further action; `merge_source_reflow.py`'s own CLI exits non-zero in that case.

## 7. Idempotence and the recursion guard

Two independent layers now prevent the reflow commit from ever triggering another reflow.

The primary layer (MSR-R1-F1, §0.1): the post-merge workflow triggers on
`pull_request: types: [closed]` guarded by `merged == true`, never on `push`. The reflow's
own commit is a direct push to `main`, not a Pull Request being closed as merged, so this
workflow's own trigger structurally never fires on it -- recursion is prevented by the
event type itself, not by inspecting the commit.

The secondary layer, preserved from the original design: `reflow()` reads only Human-owned
sources (`docs/project_sources/*.md` excluding `generated/`, the Human bytes outside
`HANDOFF.md`/`README.md`'s own markers) and the caller-supplied `main_sha` -- never its own
prior generated output. Running it twice in immediate succession, with nothing else
changed, is therefore a fixed point: the second run computes byte-identical output to the
first and writes nothing, including the receipt itself
(`test_reflow_is_idempotent_on_its_own_output`). Even if some future change ever caused this
workflow to run twice against the same state, this second layer alone would still make the
second run a true no-op.

## 8. Precompute-then-write: no partial convergence

`reflow()` computes every output file's full bytes in memory before writing anything. A
failure at any point during computation (an unreadable source document, a malformed marker
pair, a SHA that does not look like a git commit SHA) raises before the first file is
written, leaving the working tree completely unchanged. Each individual write that does
happen goes through a temp-file-then-`os.replace` sequence, so even an interruption between
two file writes never leaves a half-written file on disk.
`test_a_computation_failure_writes_nothing_to_disk` proves this directly.

## 9. Stale SHA

`merge_source_reflow.py`'s CLI accepts `--main-sha` (the caller's claim) and, when invoked
with `--verify-git-head`, independently resolves the real `git rev-parse HEAD` of the
checked-out tree and refuses (`SystemExit`) if the two disagree -- the identical shape of
guard `collect_repository_snapshot.py`'s own SHA-shape check already uses, extended to an
equality check against the actual checkout. The post-merge workflow always passes
`--verify-git-head`.

As of MSR-R1-F1, the workflow's own `--main-sha` claim is the triggering Pull Request's own
`merge_commit_sha` -- never a freshly resolved `HEAD` -- so this guard now also catches a
race: if some other Pull Request's merge has already landed on `main` ahead of this one by
the time the job runs, the checked-out `HEAD` no longer equals this event's own
`merge_commit_sha`, and the run refuses rather than reflowing against a target it no longer
matches. That later Pull Request's own "closed as merged" event reflows the now-current
state on its own; nothing is lost by refusing here rather than racing to reconcile.

## 10. Pre-merge gate boundary

```text
NETWORK_CALL_MADE_BY_source_impact_gate=false
MERGE_DECISION_MADE_BY_source_impact_gate=false
```

`source_impact_gate.py` only classifies and reports; it never merges, approves, or comments
on a Pull Request itself, for either of its two independent blocking rules (§2). The GitHub
Actions check it powers is what actually blocks a merge, through GitHub's own
required-status-check mechanism -- the identical boundary `evaluate_adoption_record` and
`evaluate` (Issue #53) already hold between "this module answers a question" and "GitHub
enforces the answer."

## 11. Post-merge workflow boundary

```text
UNBOUNDED_DIRECT_PUSH_TO_MAIN=false
BOUNDED_GENERATED_REFLOW_COMMIT=true
AUTOMATIC_MERGE=false
AUTOMATIC_PHASE_ACCEPTANCE=false
AUTOMATIC_AUTHORITY_EXPANSION=false
KERNEL_SOURCE_AUTOWRITE=false
HUMAN_SEMANTIC_TEXT_AUTOWRITE=false
WORKFLOW_SELF_MODIFICATION=false
CANDIDATE_VALIDATED_BEFORE_COMMIT=true
FILES_WRITTEN_TRUSTED_FOR_STAGING=false
```

Corrected under MSR-R1-F2/F3: the post-merge workflow computes the candidate reflow
(writing to the runner's own working tree, committing nothing) and then runs
source-freshness/drift validation against that candidate *before* any `git add`, `git
commit`, or `git push` -- a validation failure ends the job there, leaving `main`
untouched. Only after that validation passes does the workflow enforce its own literal,
YAML-hardcoded path allowlist (the same closed set §3 names) against `git status`'s actual
report of the working-tree diff (covering both modified-tracked and newly-created
untracked paths); any changed path outside that literal allowlist refuses the run before
anything is staged. Staging then adds exactly the paths that check already validated --
never the paths `merge_source_reflow.py`'s own `reflow_result.json` happens to report as
`files_written`, which the workflow no longer even reads for this purpose. It commits and
pushes exactly one commit when that diff is non-empty, and pushes nothing when the working
tree already converges. This is a narrow, declared exception to "no direct push to `main`,"
not general direct-push authority, and it is the only workflow in this repository granted
`contents: write`.

## 12. What this delivery does not prove

Both new GitHub Actions workflows are written to the identical structural pattern the
already-merged Issue #54 workflow uses (explicit `ref: main` resolution, `git rev-parse
HEAD`-based SHA resolution regardless of trigger, least-privilege `permissions:`), but this
session cannot execute a live GitHub Actions run against a real pull request or a protected
`main` branch. Every property §§2-9 name is proven by direct, offline pytest against the
underlying Python functions the workflows call; the workflow YAML files themselves are
reviewed by inspection and by the identical static-shape assertions
`test_source_freshness_drift_detection.py` already applies to the Issue #54 workflow, never
by a live push.

```text
LOCAL_TEST_PROVES_CLASSIFICATION_AND_REGENERATION_LOGIC=true
LOCAL_TEST_PROVES_LIVE_GITHUB_ACTIONS_EXECUTION=false
RUNTIME_ENFORCEMENT_IMPLEMENTED=partial
```

## 13. Acceptance

```text
PRE_MERGE_GATE_IMPLEMENTED=true
POST_MERGE_REFLOW_IMPLEMENTED=true
OWNERSHIP_CLASSIFICATION_TABLE_WRITTEN=true
GENERATED_BOUNDARY_CONTRACT_IMPLEMENTED=true
CANONICAL_GENERATED_FACTS_IMPLEMENTED=true
CONVERGENCE_RECEIPT_IMPLEMENTED=true
NEGATIVE_AND_RECOVERY_TESTS_PRESENT=true
MSR_R1_F1_EVENT_BOUND_TRIGGER_IMPLEMENTED=true
MSR_R1_F2_CANDIDATE_VALIDATION_BEFORE_COMMIT_IMPLEMENTED=true
MSR_R1_F3_LITERAL_ALLOWLIST_AND_PROTECTED_SURFACES_IMPLEMENTED=true
MSR_R1_F4_CLOSED_IMPACT_MAPPING_IMPLEMENTED=true
SEMANTIC_AUTHORITY_TRANSFERRED=false
PR_52_MODIFIED=false
PHASE_13_SEMANTICS_MODIFIED=false
PHASE_14_STARTED=false
NEW_KERNEL_ELEMENT=false
NEW_AUTHORITY_OWNER=false
GITHUB_ADAPTER_IMPLEMENTED=false
LIVE_WORKFLOW_EXECUTION_VERIFIED=false
```
