"""Read-only observed-facts collector (Issue #54, source-freshness drift detection).

Emits exactly one JSON object of observable facts -- nothing this script writes is an
interpretation. It never reads or writes ``docs/project_sources/``, never opens a network
connection itself (the caller supplies ``--main-sha``/``--predecessor-main-sha``; a CI
workflow step resolves them from ``git``, always against the real ``main`` ref regardless
of what triggered the run -- see Issue #54 section A and Structural Review Round 1's
SFD-R1-F2), and never decides Phase completion, SHUKOU acceptance, Difference closure,
Roadmap change, constitutional change, deferred-work disposition, or merge permission --
see Issue #54 section B, "Human-governed meaning", and
``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` section 12, "Untrusted instruction
boundary".

Structural Review Round 1 (SFD-R1-F1, Issue #54 comment 5564639335) adopted a convergent
baseline rule: a source projection describes the immediately preceding accepted ``main``
state, not the commit that writes the projection. So this collector emits *both* the
actual pushed ``main_sha`` (retained purely as an observation) and the separate
``predecessor_main_sha`` the push event's own "before" state -- the validator compares
recorded fields against the latter, never the former; see ``validate_source_freshness.py``.

Unlike this repository's Kernel evaluators (``authority.evaluate_authority`` and
similar), this script does read the wall clock -- ``observed_at_utc`` is exactly the
"observation timestamp" Issue #54 section A requires a read-only collector to produce.
That is a deliberate difference in kind: this is a governance-automation tool operating
outside the Kernel's deterministic-evaluator boundary, not a second Kernel owner.

Structural Review Round 1 (SFD-R1-F3) also removed ``argparse.FileType`` from this
script's CLI: that type opens its file eagerly during argument parsing, so a parse-time
error path (or any exit before the write completes) can leave the handle open until
garbage collection -- a ``ResourceWarning`` this repository's Python 3.14 test policy
treats as an error. ``--output`` is now a plain path string, opened only once, right
before the one write, and always closed explicitly.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from typing import Any, TextIO

SCHEMA_VERSION = "0.1"


def _looks_like_git_sha(value: str) -> bool:
    return len(value) in (40, 64) and all(c in "0123456789abcdefABCDEF" for c in value)


def build_snapshot(main_sha: str, predecessor_main_sha: str) -> dict[str, Any]:
    """Return the one observed-facts snapshot this collector produces.

    Raises ``SystemExit`` for either SHA that is not shaped like a git commit SHA -- an
    unreadable observation must stop the collector, not silently emit a fabricated one.
    """

    if not _looks_like_git_sha(main_sha):
        raise SystemExit(f"main_sha does not look like a git commit SHA: {main_sha!r}")
    if not _looks_like_git_sha(predecessor_main_sha):
        raise SystemExit(
            f"predecessor_main_sha does not look like a git commit SHA: {predecessor_main_sha!r}"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "main_sha": main_sha,
        "predecessor_main_sha": predecessor_main_sha,
        "observed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--main-sha",
        required=True,
        help="the actual, currently pushed main commit SHA -- retained purely as an "
        "observation, never itself compared against a recorded source baseline",
    )
    parser.add_argument(
        "--predecessor-main-sha",
        required=True,
        help="the main commit SHA immediately before this push (a push event's own "
        "`before` field), or -- for a manual run with no push event -- the resolved "
        "main ref's own parent commit; this is the value source-freshness validation "
        "compares against",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="path to write the JSON snapshot to (default: stdout)",
    )
    args = parser.parse_args(argv)
    snapshot = build_snapshot(args.main_sha, args.predecessor_main_sha)

    if args.output is None:
        _write_json(sys.stdout, snapshot)
    else:
        with open(args.output, "w", encoding="utf-8") as stream:
            _write_json(stream, snapshot)
    return 0


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
