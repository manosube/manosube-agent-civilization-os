"""The pre-merge source-impact gate (Issue #57, `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md`
section 2).

Classifies every path a pull request changes into exactly one of five closed classes, and
answers one question: does this set of changed paths carry an actual OS-implementation
change (``kernel_surface``) without any accompanying Human-owned
``docs/project_sources/*.md`` update (``source_document``)? If so, the merge is blocked --
never inferred from a green or mergeable PR, only from the declared paths themselves.

This module makes no network call, holds no GitHub token, and never merges, approves, or
comments on anything. It answers a classification question; the GitHub Actions required
status check built on top of its exit code is what actually blocks a merge -- the same
answer/enforcement split ``development_binding.evaluation`` and ``.adoption_record`` already
draw between "this module decides" and "GitHub enforces."
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

SCHEMA_VERSION = "0.1"

#: Prefix-matched paths whose change is an actual OS-implementation change. Deliberately
#: excludes `scripts/` and `tests/`: a governance-automation or test-only change does not by
#: itself force a `docs/project_sources/` update, only a real product/Kernel change does --
#: see the contract document section 2 for why, including why this Issue's own PR (which
#: touches only `scripts/`, `tests/`, `03_BINDING/`, and `.github/workflows/`) passes this
#: gate without needing a paired source_document update.
KERNEL_SURFACE_PREFIXES: tuple[str, ...] = (
    "src/",
    "00_KERNEL/",
    "01_SCHEMA/",
    "02_ENGINE/",
    "04_BOOT/",
    "05_CLI/",
    "07_AGENT_RUNTIME/",
)
KERNEL_SURFACE_EXACT: tuple[str, ...] = ("pyproject.toml",)

#: Human-owned narrative documents. A change here is the *paired update* the gate looks for
#: -- never the `generated/` subdirectory, which is machine-owned.
SOURCE_DOCUMENT_PREFIX = "docs/project_sources/"
GENERATED_SUBDIR_PREFIX = "docs/project_sources/generated/"

GOVERNANCE_BINDING_PREFIX = "03_BINDING/"

#: Exact machine-owned paths outside `docs/project_sources/generated/`. `README.md`
#: classifies here even though most of its bytes are Human prose -- path-based
#: classification cannot see which byte range changed, so a `README.md`-only change never
#: counts as the required paired `source_document` update (contract section 2).
GENERATED_EXACT_PATHS: tuple[str, ...] = ("HANDOFF.md", "SHA256SUMS", "README.md")

CLASSES: frozenset[str] = frozenset(
    {"kernel_surface", "source_document", "generated", "governance_binding", "other"}
)


def classify_path(path: str) -> str:
    """Return exactly one of :data:`CLASSES` for *path* -- a repository-relative path
    using forward slashes, as ``git diff --name-only`` already emits."""

    if path in GENERATED_EXACT_PATHS:
        return "generated"
    if path.startswith(GENERATED_SUBDIR_PREFIX):
        return "generated"
    if path.startswith(SOURCE_DOCUMENT_PREFIX):
        return "source_document"
    if path in KERNEL_SURFACE_EXACT:
        return "kernel_surface"
    if any(path.startswith(prefix) for prefix in KERNEL_SURFACE_PREFIXES):
        return "kernel_surface"
    if path.startswith(GOVERNANCE_BINDING_PREFIX):
        return "governance_binding"
    return "other"


def build_manifest(changed_paths: list[str]) -> dict[str, Any]:
    """Return the one source-impact manifest this gate produces for *changed_paths*.

    Never mutates *changed_paths*. Deterministic: the same input always produces the same
    manifest, sorted, with no wall-clock or network dependency.
    """

    classified: dict[str, list[str]] = {name: [] for name in sorted(CLASSES)}
    for path in changed_paths:
        classified[classify_path(path)].append(path)
    for paths in classified.values():
        paths.sort()

    os_change_detected = bool(classified["kernel_surface"])
    required_source_update_missing = os_change_detected and not classified["source_document"]
    merge_blocked = os_change_detected and required_source_update_missing

    return {
        "schema_version": SCHEMA_VERSION,
        "changed_paths": sorted(changed_paths),
        "classified_paths": classified,
        "os_change_detected": os_change_detected,
        "required_source_update_missing": required_source_update_missing,
        "merge_blocked": merge_blocked,
        "decision": "BLOCKED" if merge_blocked else "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--changed-path",
        dest="changed_paths",
        action="append",
        default=[],
        help="a single changed path (repository-relative, forward-slashed); repeat once "
        "per path, or supply --changed-paths-file instead",
    )
    parser.add_argument(
        "--changed-paths-file",
        default=None,
        help="path to a file listing one changed path per line (e.g. the output of "
        "`git diff --name-only`); blank lines are ignored",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="path to write the JSON manifest to (default: stdout)",
    )
    args = parser.parse_args(argv)

    changed_paths = list(args.changed_paths)
    if args.changed_paths_file is not None:
        with open(args.changed_paths_file, encoding="utf-8") as stream:
            changed_paths.extend(line.strip() for line in stream if line.strip())

    manifest = build_manifest(changed_paths)

    if args.output is None:
        _write_json(sys.stdout, manifest)
    else:
        with open(args.output, "w", encoding="utf-8") as stream:
            _write_json(stream, manifest)

    return 1 if manifest["merge_blocked"] else 0


def _write_json(stream: TextIO, payload: dict[str, Any]) -> None:
    json.dump(payload, stream, indent=2, sort_keys=True)
    stream.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
