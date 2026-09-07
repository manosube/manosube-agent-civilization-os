"""Read-only observed-facts collector (Issue #54, source-freshness drift detection).

Emits exactly one JSON object of observable facts -- nothing this script writes is an
interpretation. It never reads or writes ``docs/project_sources/``, never opens a network
connection itself (the caller supplies ``--main-sha``; a CI workflow step reads it from
``git``/``github.sha``, not this script), and never decides Phase completion, SHUKOU
acceptance, Difference closure, Roadmap change, constitutional change, deferred-work
disposition, or merge permission -- see Issue #54 section B, "Human-governed meaning",
and ``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` section 12, "Untrusted
instruction boundary".

Unlike this repository's Kernel evaluators (``authority.evaluate_authority`` and
similar), this script does read the wall clock -- ``observed_at_utc`` is exactly the
"observation timestamp" Issue #54 section A requires a read-only collector to produce.
That is a deliberate difference in kind: this is a governance-automation tool operating
outside the Kernel's deterministic-evaluator boundary, not a second Kernel owner.
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


def build_snapshot(main_sha: str) -> dict[str, Any]:
    """Return the one observed-facts snapshot this collector produces.

    Raises ``SystemExit`` for a ``main_sha`` that is not shaped like a git commit SHA --
    an unreadable observation must stop the collector, not silently emit a fabricated one.
    """

    if not _looks_like_git_sha(main_sha):
        raise SystemExit(f"main_sha does not look like a git commit SHA: {main_sha!r}")
    return {
        "schema_version": SCHEMA_VERSION,
        "main_sha": main_sha,
        "observed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--main-sha",
        required=True,
        help="the default branch commit SHA to record, e.g. from `git rev-parse HEAD` "
        "or the CI workflow's own `github.sha`",
    )
    parser.add_argument(
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="where to write the JSON snapshot (default: stdout)",
    )
    args = parser.parse_args(argv)
    snapshot = build_snapshot(args.main_sha)
    _write_json(args.output, snapshot)
    if args.output is not sys.stdout:
        args.output.close()
    return 0


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
