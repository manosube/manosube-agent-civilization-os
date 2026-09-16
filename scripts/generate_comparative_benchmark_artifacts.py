"""Generate the checked-in Comparative Benchmark example artifact bundle (Issue #89, Structural
Review Round 1, P90-R1-F2: ``MATERIALIZE_VERSIONED_PUBLIC_PROTOCOL_RESULT_AND_REPRODUCTION_
ARTIFACTS``).

Runs the real, end-to-end ``tests.comparative_benchmark.orchestrator.run_comparative_benchmark``
against a real, disposable temporary directory -- a real protocol freeze, a real result bundle
(including its real, non-``COMPLETED_VERIFIED`` raw events, per ``FAILURES_PRESENT_IN_
PUBLISHED_RAW_DATA=true``), and a real independent reproduction receipt produced by a genuinely
separate OS process (P90-R1-F3) -- and writes the three resulting record bodies to
``examples/comparative_benchmark/{protocol_freeze,result_bundle,reproduction_receipt}.json``,
pretty-printed (``json.dumps(..., indent=2, sort_keys=True)``) for a readable diff. This is a
*display* serialization of the checked-in files only -- the records' own internal content
addressing (``canonical_json_bytes`` in ``state/canonicalize.py``) is entirely unaffected by how
this script formats the bytes it writes to disk.

Deliberately under ``examples/``, not a top-level ``artifacts/`` directory: this repository's own
``.gitignore`` boundary contract ignores ``/artifacts/`` outright ("Generated observations,
evidence, receipts, and external projections. Canonical examples and deterministic fixtures
belong under tests/ or examples/") -- a checked-in file under ``/artifacts/`` would silently
never be tracked by git.

``tests/contract/comparative_benchmark/test_comparative_benchmark_published_artifacts.py`` is
the required, durable proof that the three checked-in files this script produces are self-
consistent and rederivable byte-for-byte from their own published bytes alone -- this script
itself makes no such proof; run that test after regenerating."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "examples" / "comparative_benchmark"


def _write_json(path: Path, record: dict[str, Any]) -> None:
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate(*, output_dir: Path) -> dict[str, Path]:
    sys.path.insert(0, str(ROOT))
    from tests.comparative_benchmark.orchestrator import run_comparative_benchmark

    with tempfile.TemporaryDirectory(prefix="cb21-artifact-generation-") as tmp:
        result = run_comparative_benchmark(Path(tmp))

    output_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for name, record in (
        ("protocol_freeze", result["protocol_freeze"]),
        ("result_bundle", result["result_bundle"]),
        ("reproduction_receipt", result["reproduction_receipt"]),
    ):
        path = output_dir / f"{name}.json"
        _write_json(path, record)
        written[name] = path
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default=str(ARTIFACT_DIR),
        help=f"directory to write the three record files to (default: {ARTIFACT_DIR})",
    )
    args = parser.parse_args(argv)

    written = generate(output_dir=Path(args.output_dir))
    for name, path in written.items():
        print(f"{name.upper()}_WRITTEN={path}")  # noqa: T201 -- this script's own CLI report
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
