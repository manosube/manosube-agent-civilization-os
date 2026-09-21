# v1.0 Acceptance Contract

## 0. Governing authority

```text
GOVERNING_ISSUE=#92
PHASE=22
PHASE_NAME=V1_0_ACCEPTANCE
ADOPTION_ID=ADOPT_PHASE_22_V1_0_ACCEPTANCE
ADOPTION_COMMENT_ID=5738937830
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
PREDECESSOR_ISSUE=#89
PREDECESSOR_ACCEPTED=true
AUTHORIZED_BASE_MAIN_SHA=b2a5d287113d3a98e77a2212f8b89359d8e09c5d
```

This contract documents the package `src/manosube_agent_civilization/v1_0_acceptance/`
against Issue #92's own adopted Objective (section 2), canonical twelve-predicate Gate 22
(section 4), required output (section 5), authority boundary (section 6), required
decisive negative controls (section 7), and verification policy (section 8).

---

## 1. Non-capability-building boundary

Phase 22 is acceptance/release proof, not a new capability-building Phase.
`src/manosube_agent_civilization/v1_0_acceptance/` implements no new Store-committed
record kind, no new canonical owner, and calls no write route from any other package
(proven by `tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py::test_nc10_...`).
It has exactly four public entry points
(`PUBLIC_V1_0_ACCEPTANCE_ENTRY_POINT_COUNT=4`):

```text
build_v1_0_acceptance_bundle
classify_v1_0_blocking_differences
compute_release_identity
rederive_all_pytest_owned_predicates
```

---

## 2. Gate 22 mechanical rederivation

Eleven of the twelve canonical predicates (Issue #92 section 4) are each bound, by a
pinned mapping in `gate22.py::PREDICATE_TEST_OWNERS`, to the exact already-accepted test
module(s) from their owning Phase that proved them. Rederiving a predicate means actually
re-running that owning suite as a real `pytest` subprocess and reading its exit code --
never regex-parsing prose, never trusting a caller-restated boolean
(`reflow/closure.py`'s own "provenance by reproduction, not by trust" principle, reused
here).

```text
OBJECTIVE_CONTINUITY_PROVEN         -> tests/unit/difference/test_objective_chain.py,
                                        tests/natural_cycle/test_vertical_proof.py
AGENT_REPLACEMENT_SAFE              -> tests/long_running_proof/test_long_running_proof_gate_20.py
SESSION_LOSS_SAFE                   -> tests/long_running_proof/test_long_running_proof_gate_20.py
GITHUB_INDEPENDENCE                 -> tests/unit/reflow/test_closure_evaluation.py,
                                        tests/natural_cycle/test_vertical_proof.py
RUNTIME_VERIFICATION                -> tests/long_running_proof/test_long_running_proof_gate_20.py
AUTHORITY_ENFORCEMENT               -> tests/integration/acceptance_policy/
                                        test_acceptance_policy_lineage_and_incident_fixture.py
EVIDENCE_ONLY_COMPLETION            -> tests/contract/evidence/test_sufficiency_ownership.py,
                                        tests/integration/evidence/test_sufficiency_semantics.py
STATE_LINEAGE_PRESERVATION          -> tests/unit/reflow/test_git_witness.py,
                                        tests/unit/difference/test_lineage_closure.py
LONG_RUNNING_PROOF_PASS             -> tests/long_running_proof/test_long_running_proof_gate_20.py
COMPARATIVE_BENCHMARK_PASS          -> tests/contract/comparative_benchmark/
                                        test_p90_r7_canonical_gate21_disposition.py
THIRD_PARTY_REPRODUCTION_CONFIRMED  -> tests/contract/comparative_benchmark/
                                        test_p90_r7_canonical_gate21_disposition.py
```

The twelfth predicate, `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED`, has no owning pytest
module -- it is read directly from `docs/project_sources/06_DEFERRED_DIFFERENCES.md`
(section 3).

A predicate's `verification_result` is derived strictly from the owning `pytest`
subprocess's own exit code, per pytest's own documented exit-code semantics (PR #93
Structural Review Round 1, `P93-R1-F3`): exit `0` (`EXIT_OK`) -> `PASS`; exit `1`
(`EXIT_TESTSFAILED`) -> `FAIL`; every other recognized pytest exit code -- `2`
(`EXIT_INTERRUPTED`), `3` (`EXIT_INTERNALERROR`), `4` (`EXIT_USAGEERROR`), `5`
(`EXIT_NOTESTSCOLLECTED`) -- and any negative (signal-terminated) or otherwise
unrecognized code all read `UNKNOWN`, each tagged with an explicit
`failure_category` (`INTERRUPTED`/`INTERNAL_ERROR`/`USAGE_ERROR`/
`NO_TESTS_COLLECTED`/`TERMINATED_BY_SIGNAL`/`UNRECOGNIZED_EXIT_CODE`), never coerced
to `FAIL`. The owning module not existing under the given repository root is likewise
`UNKNOWN` with `failure_category=MISSING_OWNER`. `gate_22_all_pass` is `true` only if
all twelve predicates read `PASS` -- `UNKNOWN_EQUALS_FALSE=false` and
`UNKNOWN_EQUALS_TRUE=false` (Issue #92 section 4) apply, so an `UNKNOWN` predicate
(collection failure, interrupted run, or any other pytest infrastructure outcome)
blocks `gate_22_all_pass` exactly like a `FAIL` one, without ever being misreported as
decisive negative predicate evidence.

---

## 3. v1.0-blocking Difference disposition

`blocking_differences.py` classifies every active record in
`06_DEFERRED_DIFFERENCES.md` against that register's own section 2 classification
table:

- `DEFERRED_DESIGN_CANDIDATE` / `CANCELLED_BY_HUMAN_DECISION` / `CLOSED_WITH_EVIDENCE` ->
  always `NON_BLOCKING` (the table's own unconditional "No").
- `DEFERRED_REMAINING_DIFFERENCE` / `FUTURE_OWNER_OBLIGATION` / `FOLLOW_ON_DIFFERENCE` ->
  `REQUIRES_HUMAN_AUTHORITY_DISPOSITION`, because none of their own already-recorded
  `CURRENT_PHASE_BLOCKING_EFFECT` values have ever been evaluated specifically against
  Phase 22/v1.0 -- this package never infers that an earlier "not blocking Phase N"
  statement means "not blocking v1.0" (`06_DEFERRED_DIFFERENCES.md` section 1: "must not
  be inferred by an Agent").
- The one exception is a record explicitly named as non-blocking by Issue #92 itself:
  `FD-0005` (`FD_0005_AUTOMATICALLY_BECOMES_V1_0_BLOCKER=false`, Issue #92 section 1).
  That exemption is on the record's *identity* alone, never on its *content*: every
  record's own recorded `CLASSIFICATION` is validated against the register's six
  recognized classifications *before* the `FD-0005` identity exemption is even
  consulted, so a corrupted or unrecognized classification on `FD-0005` itself still
  reads `REGISTER_CONTENT_CONTRADICTION`, never bypassed by record id alone (PR #93
  Structural Review Round 1, `P93-R1-F4`).
- An unrecognized classification (a register-content contradiction) is `FAIL`, never a
  silent pass.

At this delivery head, seven records are active (`DD-0001`, `DD-0002`, `DC-0001`,
`FD-0001`, `FD-0002`, `FD-0003`, `FD-0005`); only `DC-0001` and `FD-0005` are
`NON_BLOCKING`, so `ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED` mechanically rederives
`UNKNOWN`, not a false `PASS` -- five records genuinely require an explicit SHUKOU
disposition before this predicate can honestly read `PASS`.

---

## 4. Release identity/receipt surface

`release_identity.py::compute_release_identity` computes a commit-bound repository-shape
fingerprint (`git ls-tree -r -t`'s own blob/tree counts, the same convention
`04_REPOSITORY_ARCHITECTURE.md`'s `AS_BUILT_TREE_ENTRY_COUNT` already uses), never
creates a tag, and never publishes a release (`tag_created`/`release_published` are typed
`Literal[False]`, structurally impossible to set `True`). No `git tag` or GitHub release
API call exists anywhere in this package
(`GITHUB_RELEASE_PUBLICATION_ALLOWED=false`, `RELEASE_TAG_CREATION_ALLOWED=false`).

Every commit input this package accepts -- `delivery_head`, `authorized_base_main_sha`,
and the `commit_sha` passed to `compute_release_identity` -- is resolved through
`commit_binding.py::resolve_commit_sha` (`git rev-parse --verify <ref>^{commit}`) before
any use, so a raw tree/blob object or an unresolvable ref is rejected outright rather
than silently accepted merely because it matches the 40-hex schema pattern (PR #93
Structural Review Round 1, `P93-R1-F2`). `engine.py::build_v1_0_acceptance_bundle`
additionally binds its resolved `delivery_head` to the live repository worktree via
`commit_binding.py::verify_repo_root_bound_to_commit`: `repo_root`'s checked-out `HEAD`
must equal the resolved commit, and its tracked worktree/index must be clean, before any
pytest-owned predicate or Deferred Differences register rederivation reads that
filesystem (`P93-R1-F1`) -- this is the fail-closed alternative to checking out a
disposable temporary worktree. `authorized_base_main_sha` is further verified as a real
ancestor of the resolved `delivery_head` via `git merge-base --is-ancestor`
(`verify_authorized_base_ancestry`), never accepted merely because it is a well-formed
commit (`P93-R1-F5`'s closing ancestry-verification requirement). The bundle's own
`delivery_head`/`authorized_base_main_sha`/`release_identity.commit_sha` fields always
carry these resolved canonical lowercase 40-hex SHAs, never a raw caller-supplied ref
like `"HEAD"`; the schema enforces this shape with a `^[0-9a-f]{40}$` pattern on all
three fields.

Before any of the above, `build_v1_0_acceptance_bundle` calls
`commit_binding.py::verify_repository_project_binding`, which resolves `repo_root`'s
`origin` remote URL to a `owner/repo` GitHub project identity and fails closed unless
it equals the one authorized project (`commit_binding.AUTHORIZED_PROJECT`,
`"manosube/manosube-agent-civilization-os"`). Commit-object identity, a clean worktree,
and correct ancestry together prove nothing about *which* repository `repo_root` is --
a clone or fork carrying the exact same git objects would pass every commit-identity
check above while belonging to an unauthorized project (PR #93 Structural Review
Round 2, `P93-R2-F1`). The resolved identity is persisted as the bundle's own
`repository_project` field, required by the schema (fixed to the exact constant
`"manosube/manosube-agent-civilization-os"` via `const`, PR #93 Structural Review
Round 3, `P93-R3-F1`) and included in both the bundle id and semantic fingerprint --
a substituted project mints a genuinely different bundle identity, never a same-id
collision.

The remote URL is parsed structurally, never by unanchored substring search: an HTTPS
remote is accepted only when `urllib.parse.urlsplit(url).hostname` resolves to exactly
`github.com`, and an SSH remote is accepted only in the exact SCP-style
`git@github.com:owner/repo(.git)` form. A lookalike host such as `evilgithub.com`
contains the substring `github.com` but is not the hostname `github.com`, and is
rejected (`P93-R3-F1`).

---

## 5. Required negative/tamper controls

`tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py` implements the
ten decisive controls Issue #92 section 7 originally required (NC-1 through NC-10), plus
seven more (NC-11 through NC-17) added by PR #93 Structural Review Round 1
(`P93-R1-F5`) to decisively prove rejection of: a historical delivery SHA combined with
current-worktree evidence (NC-11); a dirty tracked worktree at the claimed delivery
commit (NC-12); a raw tree/blob object presented as a commit identity (NC-13); an
unresolvable commit SHA (NC-14); an unauthorized/non-ancestor `authorized_base_main_sha`
(NC-15); a broken/uncollectable owning test file read as `UNKNOWN` rather than `FAIL`
(NC-16); and a corrupted `FD-0005` classification not bypassing recognized-classification
validation (NC-17). NC-2 and NC-8 were also rewritten in that round: NC-2 now performs a
real content mutation between two rederivations and asserts the result actually changes
(the original only checked object identity across two calls, which is trivially true
regardless of mutation and proved nothing about re-execution); NC-8 now asserts
`delivery_head`/`release_identity.commit_sha` share one *resolved* canonical 40-hex SHA,
never the raw caller-supplied `"HEAD"` ref.

Four more (NC-18 through NC-21) were added by PR #93 Structural Review Round 2
(`P93-R2-F2`/`P93-R2-F1`) to decisively prove rejection of: a staged-only dirty index --
a change `git add`-ed into the index with no further unstaged diff on top of it (NC-18);
a real pytest internal error, `pytest` exit code `3` (NC-19); a real pytest usage error,
`pytest` exit code `4` (NC-20); and a repository carrying the exact same git objects
(a real clone) as the authorized project, but whose `origin` remote resolves to a
different GitHub project (NC-21).

One more (NC-22) was added by PR #93 Structural Review Round 3 (`P93-R3-F1`) to
decisively prove rejection of a lookalike-hostname bypass: a remote URL on a host that
merely *contains* the substring `github.com` (`https://evilgithub.com/manosube/
manosube-agent-civilization-os.git`, with the exact authorized `owner/repo` in its
path) is rejected, proving the hostname check is structural, not substring-based.
Twenty-two decisive controls total.

---

## 6. Non-claims

```text
PHASE_22_CREATES_NEW_CANONICAL_OWNER=false
PHASE_22_REWRITES_PRIOR_PHASE_ACCEPTANCE=false
PHASE_22_SILENTLY_CLOSES_DEFERRED_DIFFERENCES=false
GATE_22_ALL_PASS_AT_THIS_HEAD=false
V1_0_DECLARATION_EMITTED=false
GITHUB_RELEASE_PUBLICATION_PERFORMED=false
RELEASE_TAG_CREATED=false
```

`gate_22_all_pass=false` at this delivery head is the honest, mechanically rederived
result -- eleven predicates PASS and the twelfth (`ALL_V1_0_BLOCKING_DIFFERENCES_CLOSED`)
is `UNKNOWN` pending SHUKOU disposition of five Deferred Differences. No claim in this
delivery asserts v1.0 readiness beyond this recorded state.

---

## 7. PR #93 Structural Review Round 1 corrections (`ADOPT_P93_R1_F1_F2_F3_F4_F5`)

```text
GOVERNING_PR=#93
ADOPTION_ID=ADOPT_P93_R1_F1_F2_F3_F4_F5
ADOPTION_COMMENT_ID=5746034137
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
AUTHORIZED_TARGET_HEAD=cdace37d1bee777c08bfbfa86206e2bcc0c54dcd
AUTHORIZED_BASE_MAIN=b2a5d287113d3a98e77a2212f8b89359d8e09c5d
```

Five findings from Structural Review Round 1 of PR #93, corrected on the same
branch/PR:

- **`P93-R1-F1`** -- `build_v1_0_acceptance_bundle` rederived pytest-owned predicates and
  the Deferred Differences register against `repo_root`'s live filesystem without ever
  confirming that filesystem was actually checked out at, and clean at, the caller's
  claimed `delivery_head`. Fixed by `commit_binding.py::verify_repo_root_bound_to_commit`
  (worktree-binding check: `git rev-parse HEAD` must equal the resolved delivery commit,
  and `git status --porcelain --untracked-files=no` must be empty), invoked by
  `resolve_and_bind_delivery_head` at the top of `build_v1_0_acceptance_bundle`. See
  section 4.
- **`P93-R1-F2`** -- no commit input (`delivery_head`, `authorized_base_main_sha`,
  `release_identity`'s `commit_sha`) was ever verified to resolve to a real commit
  object; a raw tree/blob SHA or an unresolvable ref matching the 40-hex schema pattern
  would have been silently accepted. Fixed by `commit_binding.py::resolve_commit_sha`
  (`git rev-parse --verify <ref>^{commit}`), used by both `engine.py` (via
  `resolve_and_bind_delivery_head`/`resolve_and_verify_authorized_base`) and
  `release_identity.py::compute_release_identity`. See section 4.
- **`P93-R1-F3`** -- Gate 22 predicate rederivation treated every non-zero pytest exit
  code as `FAIL`, which misreports pytest infrastructure failures (interrupted runs,
  internal errors, usage errors, collection failures) as decisive negative predicate
  evidence. Fixed by `gate22.py`'s explicit pytest exit-code classification: only exit
  `0`/`1` are ever `PASS`/`FAIL`; every other code (and any negative, signal-terminated
  code) is `UNKNOWN` with an explicit `failure_category`. See section 2.
- **`P93-R1-F4`** -- `blocking_differences.py`'s `FD-0005` non-blocking exemption was
  applied by record id alone, before that record's own `CLASSIFICATION` value was
  validated as one of the register's six recognized classifications -- a corrupted
  `FD-0005` entry could have been silently waved through. Fixed by validating
  `record.classification` against `_RECOGNIZED_CLASSIFICATIONS` first, unconditionally,
  before the `FD-0005` identity exemption (or any other disposition rule) is applied.
  See section 3.
- **`P93-R1-F5`** -- the negative-control matrix did not decisively prove rejection of
  several of these same fail-closed conditions (worktree substitution, non-ancestor
  base, malformed commit identities, pytest infrastructure failures scored as `FAIL`,
  and NC-2's original re-execution claim), and NC-2/NC-8 in particular tested only
  incidental properties (object identity, string equality against `"HEAD"`) rather than
  the actual guarantee. Fixed by NC-11 through NC-17 plus the NC-2/NC-8 rewrites. See
  section 5.

All five corrections landed as real code changes plus decisive tests -- never a report,
restated boolean, or documentation-only claim -- consistent with this package's own
"provenance by reproduction, not by trust" principle.

---

## 8. PR #93 Structural Review Round 2 corrections (`ADOPT_P93_R2_F1_F2`)

```text
GOVERNING_PR=#93
ADOPTION_ID=ADOPT_P93_R2_F1_F2
ADOPTION_COMMENT_ID=5748918434
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
AUTHORIZED_TARGET_HEAD=e8d8f9f6d8b47aa60e7e8a72ecebb676f3923620
AUTHORIZED_BASE_MAIN=b2a5d287113d3a98e77a2212f8b89359d8e09c5d
```

Two findings from Structural Review Round 2 of PR #93, corrected on the same
branch/PR:

- **`P93-R2-F1`** -- the Round 1 commit-binding checks (commit-object identity, clean
  worktree, authorized-base ancestry) prove `repo_root` is at the right commit, cleanly,
  with the right history, but say nothing about *which* repository it is -- a clone or
  fork carrying the exact same git objects would pass every one of those checks while
  belonging to an unauthorized project. Fixed by
  `commit_binding.py::verify_repository_project_binding`, which resolves `repo_root`'s
  `origin` remote URL to a `owner/repo` GitHub project identity and fails closed with
  `RepositoryProjectBindingError` unless it equals the one authorized project
  (`commit_binding.AUTHORIZED_PROJECT`, `"manosube/manosube-agent-civilization-os"`).
  Called at the very start of `build_v1_0_acceptance_bundle`, before any commit binding
  or Gate 22 rederivation. The resolved identity is persisted as the bundle's own
  `repository_project` field, required by the schema and included in
  `ACCEPTANCE_BUNDLE_ID_FIELDS` (so a substituted project mints a genuinely new bundle
  id and semantic fingerprint; the schema field was later tightened from a shape
  pattern to the exact `const` value by Round 3's `P93-R3-F1`, section 9). See
  section 4.
- **`P93-R2-F2`** -- the adopted negative-control matrix had not yet exercised every
  scenario its own implementation paths were already capable of rejecting: a purely
  staged-only dirty index (as opposed to an unstaged working-tree change), and real
  pytest internal-error (exit `3`) / usage-error (exit `4`) outcomes specifically (as
  opposed to the collection-error case NC-16 already covered). Fixed by four new
  controls, NC-18 through NC-21 -- see section 5.

Both corrections landed as real code changes plus decisive tests -- never a report,
restated boolean, or documentation-only claim -- consistent with this package's own
"provenance by reproduction, not by trust" principle.

---

## 9. PR #93 Structural Review Round 3 corrections (`ADOPT_P93_R3_F1`)

```text
GOVERNING_PR=#93
ADOPTION_ID=ADOPT_P93_R3_F1
ADOPTION_COMMENT_ID=5752891096
ADOPTION_COMMENT_AUTHOR=manosube (OWNER)
AUTHORIZED_TARGET_HEAD=9f580c7e15185d00c2afddaa6722c64644dd8873
AUTHORIZED_BASE_MAIN=b2a5d287113d3a98e77a2212f8b89359d8e09c5d
```

One finding from Structural Review Round 3 of PR #93, corrected on the same
branch/PR:

- **`P93-R3-F1`** -- `commit_binding.py`'s Round 2 remote-URL parser
  (`_REMOTE_URL_PROJECT_PATTERN`) matched the substring `github\.com[:/]` anywhere in
  the URL, unanchored. A lookalike host such as
  `https://evilgithub.com/manosube/manosube-agent-civilization-os.git` contains that
  substring and the exact authorized `owner/repo` in its path, so it would have
  resolved to the authorized project despite being served by an entirely different,
  attacker-controlled host -- the real trust boundary Round 2's `P93-R2-F1` intended to
  close was therefore bypassable through mutable remote configuration. Fixed by parsing
  the remote URL structurally: an HTTPS remote is accepted only when
  `urllib.parse.urlsplit(url).hostname` equals exactly `github.com`, and an SSH remote
  is accepted only in the exact SCP-style `git@github.com:owner/repo(.git)` form --
  never a substring match. The bundle schema's `repository_project` field was also
  tightened from a shape pattern to the exact `const` value
  `"manosube/manosube-agent-civilization-os"`, since this schema belongs to this one
  authorized Phase 22 project rather than an arbitrary `owner/repo`. See section 4.
  New decisive control NC-22 exercises the hostile lookalike host directly against the
  real parser. See section 5.

This correction landed as a real code change plus a decisive test -- never a report,
restated boolean, or documentation-only claim -- consistent with this package's own
"provenance by reproduction, not by trust" principle. It is a narrow boundary
correction: it does not redesign the acceptance package, add another capability or
public entry point, or change Gate 22 predicate ownership.
