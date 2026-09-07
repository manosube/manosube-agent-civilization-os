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

## 1. The canonical two-stage sequence

```text
PR opened against main
  ↓
pre-merge source-impact gate classifies every changed path
  (kernel_surface / source_document / generated / governance_binding / other)
  ↓
OS_CHANGE_DETECTED AND REQUIRED_SOURCE_UPDATE_MISSING  ->  MERGE_BLOCKED
  ↓ (otherwise)
SHUKOU manually merges (this mechanism never merges)
  ↓
push-to-main workflow observes the exact resulting main SHA
  ↓
post-merge reflow regenerates only declared machine-owned surfaces
  ↓
one bounded, generated-only reflow commit (or none, if already converged)
  ↓
source freshness and drift detection rerun against the new main state
```

The reflow commit is a *successor* to the manually accepted merge. It never rewrites,
amends, or force-pushes over the merge commit it follows.

## 2. Ownership classification (the pre-merge gate's own table)

Every changed path in a pull request against `main` falls into exactly one class,
determined by prefix match against this closed table -- `source_impact_gate.py`'s
`classify_path` implements it verbatim, and `test_source_impact_gate.py` proves every row.

```text
class               path prefix (or exact path)                     requires a paired
                                                                      source_document
                                                                      update in the same PR
kernel_surface      src/, 00_KERNEL/, 01_SCHEMA/, 02_ENGINE/,          yes
                    04_BOOT/, 05_CLI/, 07_AGENT_RUNTIME/,
                    pyproject.toml (exact)
source_document     docs/project_sources/*.md (excluding generated/)  n/a (this *is* the
                                                                       required update)
generated           docs/project_sources/generated/, HANDOFF.md       no
                    (exact), SHA256SUMS (exact), README.md (exact)
governance_binding  03_BINDING/                                       no
other               everything else (tests/, scripts/,                no
                    docs/decisions/, examples/, ...)
```

`scripts/` and `tests/` are deliberately **not** `kernel_surface`: a governance-automation
or test-only change does not by itself force a `docs/project_sources/` update, only an
actual `src/`/Kernel/Schema/Boot/CLI/Agent-runtime change does. This Issue's own PR touches
none of the `kernel_surface` prefixes, so the gate -- run against this PR -- passes without
requiring a paired update; that self-consistency is checked directly by
`test_source_impact_gate.py`.

```text
OS_CHANGE_DETECTED = any changed path classifies kernel_surface
REQUIRED_SOURCE_UPDATE_MISSING = OS_CHANGE_DETECTED and no changed path classifies
                                  source_document
MERGE_BLOCKED = OS_CHANGE_DETECTED and REQUIRED_SOURCE_UPDATE_MISSING
```

`README.md` classifies `generated` even though most of its bytes are Human prose: path-based
classification cannot see which byte range changed, and the file's own bounded-block
technique (§4) is what actually protects the Human portion. A `README.md`-only change
therefore never counts as the required paired `source_document` update -- only an actual
`docs/project_sources/*.md` change does.

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

`reflow()` reads only Human-owned sources (`docs/project_sources/*.md` excluding
`generated/`, the Human bytes outside `HANDOFF.md`/`README.md`'s own markers) and the
caller-supplied `main_sha` -- never its own prior generated output. Running it twice in
immediate succession, with nothing else changed, is therefore a fixed point: the second run
computes byte-identical output to the first and writes nothing
(`test_reflow_is_idempotent_on_its_own_output`). Because the post-merge workflow's own
reflow commit changes no Human-owned source, a reflow commit can never itself trigger a
second, non-empty reflow -- the recursion this Issue's `REQUIRED_PROOF` names is prevented
by construction, not by detecting and skipping the automation's own commits.

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

## 10. Pre-merge gate boundary

```text
NETWORK_CALL_MADE_BY_source_impact_gate=false
MERGE_DECISION_MADE_BY_source_impact_gate=false
```

`source_impact_gate.py` only classifies and reports; it never merges, approves, or comments
on a Pull Request itself. The GitHub Actions check it powers is what actually blocks a
merge, through GitHub's own required-status-check mechanism -- the identical boundary
`evaluate_adoption_record` and `evaluate` (Issue #53) already hold between "this module
answers a question" and "GitHub enforces the answer."

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
```

The post-merge workflow's own `git add` step names the exact allowlisted paths `reflow()`
reports as written -- never `git add -A`, never a glob wider than §3's closed list. It
commits and pushes exactly one commit when `files_written` is non-empty, and pushes nothing
when the working tree already converges. This is a narrow, declared exception to "no direct
push to `main`," not general direct-push authority, and it is the only path capable of
pushing anything runs no other job or trigger.

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
SEMANTIC_AUTHORITY_TRANSFERRED=false
PR_52_MODIFIED=false
PHASE_13_SEMANTICS_MODIFIED=false
PHASE_14_STARTED=false
NEW_KERNEL_ELEMENT=false
NEW_AUTHORITY_OWNER=false
GITHUB_ADAPTER_IMPLEMENTED=false
LIVE_WORKFLOW_EXECUTION_VERIFIED=false
```
