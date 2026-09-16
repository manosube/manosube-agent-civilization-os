# Comparative Benchmark published artifacts

Structural Review Round 1 (Issue #89, P90-R1-F2: `MATERIALIZE_VERSIONED_PUBLIC_PROTOCOL_
RESULT_AND_REPRODUCTION_ARTIFACTS`).

This directory holds the three real, checked-in record bodies from one genuine, end-to-end
Comparative Benchmark run. It lives under `examples/`, not a top-level `artifacts/` directory,
because this repository's own `.gitignore` boundary contract ignores `/artifacts/` outright
("Canonical examples and deterministic fixtures belong under tests/ or examples/") — a file
checked in under `/artifacts/` would never actually be tracked by git.

- `protocol_freeze.json` — the immutable, content-addressed pre-result protocol declaration
  (corpus, comparison groups, metrics, thresholds, exclusion policy, claim vocabulary).
- `result_bundle.json` — the raw-event/metric/claim bundle, including real, non-successful
  outcomes (`REFUSED`/`FAILED`/`RETAINED_INCOMPLETE`), never a success-only subset.
- `reproduction_receipt.json` — an independent reproduction, produced by a genuinely separate
  OS process (P90-R1-F3), with its own real `MATCH`/`DIVERGENT`/`INCOMPARABLE` verdict.

Each file is pretty-printed (`json.dumps(..., indent=2, sort_keys=True)`) for a readable diff.
This is a *display* serialization only — the records' own internal content addressing
(`manosube_agent_civilization.state.canonicalize.canonical_json_bytes`) is unaffected by how
this checked-in copy is formatted.

## How these were generated

```
python scripts/generate_comparative_benchmark_artifacts.py
```

The script runs `tests.comparative_benchmark.orchestrator.run_comparative_benchmark` against a
real, disposable temporary directory and overwrites the three files in this directory with the
genuine output. Re-run it and diff the result whenever the `comparative_benchmark` package,
schemas, or fixture corpus change.

## How to verify these are genuine and reloadable

`tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py` loads
these three files directly off disk — no Store, no fixture module, no orchestrator call — and
proves they validate against their own schemas, that each record's own id/semantic-fingerprint
fields recompute to the stored values, that `result_bundle.json`'s own `metrics`/`claims`/
`threshold_evaluations` rederive byte-for-byte from its own `raw_events` and the published
protocol freeze alone, and that `reproduction_receipt.json`'s own `agreement` verdict rederives
from its own `reproduced_metrics` compared against the published result bundle.
