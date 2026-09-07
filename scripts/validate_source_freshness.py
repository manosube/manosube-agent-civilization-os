"""Deterministic, read-only source-freshness validator (Issue #54, P13-adjacent governance).

Compares an already-collected observed-facts snapshot (see
``collect_repository_snapshot.py`` -- a separate component, per Issue #54's own split
between "A. Machine-owned observation" and "C. Drift detection") against the
mutable-projection fields recorded inside ``docs/project_sources/03_CURRENT_DEVELOPMENT_
STATE.md`` and ``docs/project_sources/04_REPOSITORY_ARCHITECTURE.md``, and reports drift.

This module never writes to ``docs/project_sources/`` or anywhere else, never opens a
network connection, and never reads the wall clock -- every fact it reasons about is
supplied by its two callers (the on-disk source documents and the caller-supplied
snapshot). It answers exactly one question per checked field: does the observed value
still match what the mutable source document records? A mismatch is reported as
``SOURCE_DRIFT_DETECTED`` with the fields Issue #54 section C names
(``AFFECTED_FILES``/``OBSERVED_VALUES``/``RECORDED_VALUES``/``REQUIRED_OWNER``); it is
never silently repaired, and this module holds no authority to decide whether the drift
matters -- see ``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` sections 6 and 11.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, TextIO

SCHEMA_VERSION = "0.1"

#: Matches one ``KEY=VALUE`` line inside a fenced ```text block in the source documents'
#: own convention (see e.g. ``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` section
#: 14, "Minimum source metadata"). Deliberately conservative: an all-caps identifier key,
#: an ``=``, and the remainder of the line as the value verbatim.
_FIELD_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)=(.*)$")

#: (recorded file, recorded field, observed snapshot key, required owner) -- the exact
#: set of comparisons this first drift-detection round performs. Each recorded field
#: comes from the "Update ownership" table in
#: ``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` section 13: both
#: ``03_CURRENT_DEVELOPMENT_STATE.md`` and ``04_REPOSITORY_ARCHITECTURE.md`` are
#: "Structural Advisor prepares; SHUKOU accepts", so a mismatch is theirs to resolve, not
#: this validator's and not this repository's automation's.
CHECKS: tuple[tuple[str, str, str, str], ...] = (
    (
        "03_CURRENT_DEVELOPMENT_STATE.md",
        "MAIN_ACCEPTED_BASE_SHA",
        "main_sha",
        "CHATGPT_STRUCTURAL_ADVISOR",
    ),
    (
        "04_REPOSITORY_ARCHITECTURE.md",
        "AS_BUILT_REF",
        "main_sha",
        "CHATGPT_STRUCTURAL_ADVISOR",
    ),
)


def extract_fields(markdown_text: str) -> dict[str, str]:
    """Every ``KEY=VALUE`` line inside any fenced ```text block, last occurrence wins.

    A later section's summary (e.g. a document's own closing "receipt" section) is
    treated as the document's own canonical restatement of an earlier field, matching how
    these documents are written -- never as a right to prefer one arbitrary occurrence
    over another.
    """

    fields: dict[str, str] = {}
    in_text_block = False
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped == "```text":
            in_text_block = True
            continue
        if stripped == "```":
            in_text_block = False
            continue
        if not in_text_block:
            continue
        match = _FIELD_LINE.match(stripped)
        if match:
            fields[match.group(1)] = match.group(2)
    return fields


def load_recorded_facts(docs_dir: Path) -> dict[str, dict[str, str]]:
    """Read-only: every field this validator can check, keyed by source filename."""

    recorded: dict[str, dict[str, str]] = {}
    for filename, _field, _observed_key, _owner in CHECKS:
        recorded.setdefault(
            filename, extract_fields((docs_dir / filename).read_text(encoding="utf-8"))
        )
    return recorded


def validate(recorded: dict[str, dict[str, str]], observed: dict[str, Any]) -> dict[str, Any]:
    """Compare *recorded* (from :func:`load_recorded_facts`) against *observed*.

    Never mutates either argument. A recorded field the source document omits entirely is
    a source-document integrity problem, reported separately from ordinary drift -- it
    means the document no longer carries the metadata this validator (and, per the
    documents' own section 14, every reader) depends on, not that the value merely
    changed.
    """

    affected: list[dict[str, str]] = []
    observed_values: dict[str, str] = {}
    recorded_values: dict[str, str] = {}
    missing_recorded_fields: list[dict[str, str]] = []

    for filename, field, observed_key, owner in CHECKS:
        recorded_value = recorded.get(filename, {}).get(field)
        if recorded_value is None:
            missing_recorded_fields.append({"file": filename, "field": field})
            continue
        observed_value = observed[observed_key]
        location = f"{filename}#{field}"
        if recorded_value != observed_value:
            affected.append({"file": filename, "field": field, "required_owner": owner})
            observed_values[location] = observed_value
            recorded_values[location] = recorded_value

    required_owners = sorted({entry["required_owner"] for entry in affected})
    return {
        "schema_version": SCHEMA_VERSION,
        "source_drift_detected": bool(affected),
        "affected_files": affected,
        "observed_values": observed_values,
        "recorded_values": recorded_values,
        "required_owner": required_owners or None,
        "missing_recorded_fields": missing_recorded_fields,
        "checked_observed_at_utc": observed.get("observed_at_utc"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs/project_sources"),
        help="directory holding the nine reconstructed information-source documents",
    )
    parser.add_argument(
        "--observed-snapshot",
        type=Path,
        required=True,
        help="path to a JSON snapshot produced by collect_repository_snapshot.py",
    )
    parser.add_argument(
        "--output",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="where to write the JSON drift report (default: stdout)",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="exit non-zero when SOURCE_DRIFT_DETECTED is true (the report is still "
        "written either way)",
    )
    args = parser.parse_args(argv)

    observed = json.loads(args.observed_snapshot.read_text(encoding="utf-8"))
    recorded = load_recorded_facts(args.docs_dir)
    report = validate(recorded, observed)
    _write_json(args.output, report)
    if args.output is not sys.stdout:
        args.output.close()

    if report["missing_recorded_fields"]:
        return 2
    if args.fail_on_drift and report["source_drift_detected"]:
        return 1
    return 0


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
