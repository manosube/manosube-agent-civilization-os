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

A predicate's `verification_result` is `PASS` only if every one of its owner test
modules exits `0`, `FAIL` if the owning suite ran and reported a failure, and `UNKNOWN`
if the owning module does not exist under the given repository root (never silently
coerced to `FAIL`). `gate_22_all_pass` is `true` only if all twelve predicates read
`PASS` -- `UNKNOWN_EQUALS_FALSE=false` and `UNKNOWN_EQUALS_TRUE=false` (Issue #92
section 4) apply, so an `UNKNOWN` predicate blocks `gate_22_all_pass` exactly like a
`FAIL` one, without being reported as a false negative.

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

---

## 5. Required negative/tamper controls

`tests/contract/v1_0_acceptance/test_v1_0_acceptance_negative_controls.py` implements the
ten decisive controls Issue #92 section 7 requires, NC-1 through NC-10.

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
