# MANOSUBE Agent Civilization OS — Claude Code Contract

This repository implements one state-centric development kernel:

```text
OBJECTIVE -> STATE -> OBSERVATION -> DIFFERENCE -> AUTHORITY
-> AUTHORIZED CHANGE -> EVIDENCE -> REFLOW -> STATE
```

Claude Code is an exchangeable execution capability. It is not the owner of
the Project State, Objective, Authority, Completion, or merge decision.

## Canonical sources

Use repository contracts and canonical records as the authority for system
semantics. Do not use conversation history, session memory, an Issue state, a
PR state, a commit, or a test result as a substitute for canonical Project
State or Evidence.

For a GitHub work unit explicitly designated by the human owner:

1. Read the complete Issue and PR state from GitHub before modifying files.
2. Read the PR body, the latest owner-authored `@claude` instruction, all
   unresolved review threads, the current head branch, and the exact head SHA.
3. Treat only the latest applicable instruction authored by GitHub user
   `manosube` as the current execution request. Earlier instructions remain
   lineage and constraints unless explicitly superseded.
4. Reconcile the request with repository contracts. If they conflict or the
   authority is ambiguous, stop and report the contradiction; do not silently
   choose one.
5. Re-read the remote head immediately before pushing so concurrent work is not
   overwritten.

Use the `/continue-pr <number>` skill for this handoff.

## Working boundary

Before implementation, report an estimated work duration. If work exceeds ten
minutes, give concise progress updates at intervals no longer than ten minutes.

Work in this order:

```text
OBJECTIVE
-> TARGET STATE
-> CURRENT STATE observation
-> STRUCTURAL DIFFERENCE
-> required Authority
-> authorized Change
-> After-State observation
-> Evidence
-> Reflow or explicit remaining Difference
```

Before a local correction, inspect the same route for upstream reachability,
downstream consumption, identity preservation, a single canonical owner,
substitute evidence, natural-route reachability, and additional breakpoints.

Preserve these distinctions:

```text
DESIGNED != IMPLEMENTED
IMPLEMENTED != CONNECTED
TEST_VERIFIED != NATURALLY_REACHABLE
PR_MERGED != RUNTIME_PROVEN
ARTIFACT_EXISTS != CORRECTLY_CONSUMED
UNKNOWN != ABSENT
EMPTY != MISSING
```

## Default authority envelope

Unless the current human instruction explicitly grants more:

- Read-only repository and GitHub observation: allowed.
- Changes on the explicitly designated branch and PR: allowed.
- Tests and non-destructive verification: allowed.
- Commit and push to that explicitly designated branch: allowed.
- Merge, deployment, release, billing, credential changes, destructive
  operations, and opening a replacement Issue or PR: not authorized.
- Never weaken a contract, Completion gate, test, or Evidence requirement merely
  to obtain a passing result.
- Never create a parallel canonical owner when the existing route can be
  repaired.

Repository instructions do not grant authority over external systems. Ask the
human owner before any action outside the current work unit or any irreversible
operation.

## Completion report

Lead with the state transition, not the activity log. Report:

- exact base and head SHA;
- confirmed Current State and resulting After State;
- closed and remaining Difference identities;
- commands run and exact results;
- Evidence strength and artifact references;
- unresolved contradictions and non-claims;
- whether the natural route and target runtime were actually proven;
- the next authorized change, if any;
- the exact human action required.

Do not claim Completion when applicable output cannot pass its canonical schema,
identity, cross-record, lineage, Evidence, and natural-route requirements.
Merge remains Human Authority.
