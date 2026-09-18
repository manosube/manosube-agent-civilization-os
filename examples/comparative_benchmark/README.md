# Comparative Benchmark published artifacts

Structural Review Round 1 (Issue #89, P90-R1-F2: `MATERIALIZE_VERSIONED_PUBLIC_PROTOCOL_
RESULT_AND_REPRODUCTION_ARTIFACTS`). `independent_reproducer_trust_anchor.json` was added in
Structural Review Round 4 (PR #90, `ADOPT_P90_R4_REAL_AGENT_CORPUS_AND_PRETRUSTED_INDEPENDENT_
REPRODUCER`).

This directory holds the real, checked-in record bodies from one genuine, end-to-end Comparative
Benchmark run, plus the real trust anchor admitted for its independent reproducer. It lives under
`examples/`, not a top-level `artifacts/` directory, because this repository's own `.gitignore`
boundary contract ignores `/artifacts/` outright ("Canonical examples and deterministic fixtures
belong under tests/ or examples/") — a file checked in under `/artifacts/` would never actually
be tracked by git.

- `protocol_freeze.json` — the immutable, content-addressed pre-result protocol declaration
  (corpus, comparison groups, metrics, thresholds, exclusion policy, claim vocabulary).
- `result_bundle.json` — the raw-event/metric/claim bundle, including real, non-successful
  outcomes (`REFUSED`/`FAILED`/`RETAINED_INCOMPLETE`), never a success-only subset.
- `reproduction_receipt.json` — an independent reproduction, produced by a genuinely separate
  OS process (P90-R1-F3), with its own real `MATCH`/`DIVERGENT`/`INCOMPARABLE` verdict.
- `independent_reproducer_trust_anchor.json` — SHUKOU's own real, pre-registered Ed25519
  *public* key for the Phase 21 independent reproducer (`reproducer_actor_or_authority_id=
  SHUKOU_PHASE21_REPRODUCER`), admitted through `comparative_benchmark.route.
  admit_independent_reproducer_trust_anchor` and authorized against this directory's own
  `protocol_freeze.json`. Carries only a public key — this repository never generates, requests,
  receives, or stores the matching private key (standing constraint, unchanged since Issue #89).

Each file is pretty-printed (`json.dumps(..., indent=2, sort_keys=True)`) for a readable diff.
This is a *display* serialization only — the records' own internal content addressing
(`manosube_agent_civilization.state.canonicalize.canonical_json_bytes`) is unaffected by how
this checked-in copy is formatted.

## How these were generated

```
python scripts/generate_comparative_benchmark_artifacts.py
python scripts/admit_comparative_benchmark_independent_reproducer_trust_anchor.py
```

The first script runs `tests.comparative_benchmark.orchestrator.run_comparative_benchmark`
against a real, disposable temporary directory and overwrites `protocol_freeze.json`,
`result_bundle.json`, and `reproduction_receipt.json` in this directory with the genuine output.
Re-run it and diff the result whenever the `comparative_benchmark` package, schemas, or fixture
corpus change.

The second script reads this directory's own already-published `protocol_freeze.json`, calls the
production route `admit_independent_reproducer_trust_anchor` against a fresh, disposable Store
with SHUKOU's own already-disclosed public key/key id (PR #90 comment 5709021178), and overwrites
`independent_reproducer_trust_anchor.json` with the genuine committed record. It never touches,
requests, or logs any private key. Re-run it only if the published `protocol_freeze.json` itself
changes (the trust anchor's own identity is bound to that exact protocol freeze) or SHUKOU
registers a revocation/rotation.

## How to verify these are genuine and reloadable

`tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py` loads
these four files directly off disk — no Store, no fixture module, no orchestrator call — and
proves they validate against their own schemas, that each record's own id/semantic-fingerprint
fields recompute to the stored values, that `result_bundle.json`'s own `metrics`/`claims`/
`threshold_evaluations` rederive byte-for-byte from its own `raw_events` and the published
protocol freeze alone, that `reproduction_receipt.json`'s own `agreement` verdict rederives from
its own `reproduced_metrics` compared against the published result bundle, and that
`independent_reproducer_trust_anchor.json` is admitted by `HUMAN_AUTHORITY`, is `ACTIVE`,
authorizes exactly the published protocol freeze, and carries only a well-formed public key.
