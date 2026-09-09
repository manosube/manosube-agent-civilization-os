"""The pre-merge source-impact gate (Issue #57, `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md`
section 2), hardened by Structural Review Round 1
(`ADOPT_MSR_R1_EVENT_BOUND_REVALIDATED_AND_PATH_HARDENED_REFLOW`, Issue #57 comment
5567433361).

Classifies every path a pull request changes into exactly one of six closed classes, and
enforces two independent fail-closed rules -- never inferred from a green or mergeable PR,
only from the declared paths themselves:

1. A `kernel_surface` change (an actual OS-implementation change) must be paired with a
   `source_document` update from the *specific* closed set :data:`KERNEL_SURFACE_IMPACT_MAP`
   declares for that area -- an arbitrary, unrelated `docs/project_sources/*.md` edit no
   longer satisfies the obligation (MSR-R1-F4).
2. A change to a `protected_governance_surface` path (this gate's own executor script,
   the reflow's own executor script, or either reflow workflow file) must be paired with a
   `governance_binding` update -- these are the surfaces that *implement* Merge Source
   Reflow's own enforcement, so a change to them is itself a governance-sensitive event
   (MSR-R1-F3).

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
    # Phase 16 (Issue #66): the Model Runtime contract directory. Registered here so a
    # doc-only change inside it is gated exactly the way a doc-only change inside
    # `07_AGENT_RUNTIME/` already is. `09_PROJECTION/` and `10_RUNTIME/` remain unregistered,
    # a pre-existing gap deliberately left alone by this Phase rather than silently widened.
    "11_MODEL_RUNTIME/",
)
KERNEL_SURFACE_EXACT: tuple[str, ...] = ("pyproject.toml",)

#: Human-owned narrative documents. A change here is a *candidate* paired update the gate
#: looks for -- never the `generated/` subdirectory, which is machine-owned, and only
#: admitted when it is also a member of the specific area's own
#: :data:`KERNEL_SURFACE_IMPACT_MAP` entry (MSR-R1-F4).
SOURCE_DOCUMENT_PREFIX = "docs/project_sources/"
GENERATED_SUBDIR_PREFIX = "docs/project_sources/generated/"

GOVERNANCE_BINDING_PREFIX = "03_BINDING/"

#: Exact machine-owned paths outside `docs/project_sources/generated/`. `README.md`
#: classifies here even though most of its bytes are Human prose -- path-based
#: classification cannot see which byte range changed, so a `README.md`-only change never
#: counts as the required paired `source_document` update (contract section 2).
GENERATED_EXACT_PATHS: tuple[str, ...] = ("HANDOFF.md", "SHA256SUMS", "README.md")

#: The executor scripts and workflow files that *implement* Merge Source Reflow's own
#: enforcement -- protected governance surfaces the pre-merge gate itself requires a
#: paired `governance_binding` update to change (MSR-R1-F3), never merely `other`.
PROTECTED_GOVERNANCE_SURFACE_EXACT: tuple[str, ...] = (
    "scripts/merge_source_reflow.py",
    "scripts/source_impact_gate.py",
    ".github/workflows/merge_source_pre_merge_gate.yml",
    ".github/workflows/merge_source_post_merge_reflow.yml",
)

CLASSES: frozenset[str] = frozenset(
    {
        "kernel_surface",
        "source_document",
        "generated",
        "governance_binding",
        "protected_governance_surface",
        "other",
    }
)

#: The closed, declared impact mapping (MSR-R1-F4): the specific `source_document` path(s)
#: that are the legitimate required pairing for a `kernel_surface` change in a given area --
#: never "any `docs/project_sources/*.md` update satisfies any kernel_surface change."
#: Every area maps to the identical two-document set today, since both documents
#: legitimately describe any OS-implementation change (current state, and as-built
#: architecture, respectively); the mapping is declared per-area rather than globally so it
#: can be refined to per-subsystem granularity later without changing the gate's own
#: admission logic (contract section 2.1).
_KERNEL_SURFACE_REQUIRED_DOCS: tuple[str, ...] = (
    "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md",
    "docs/project_sources/04_REPOSITORY_ARCHITECTURE.md",
)
KERNEL_SURFACE_IMPACT_MAP: dict[str, tuple[str, ...]] = {
    **dict.fromkeys(KERNEL_SURFACE_PREFIXES, _KERNEL_SURFACE_REQUIRED_DOCS),
    **dict.fromkeys(KERNEL_SURFACE_EXACT, _KERNEL_SURFACE_REQUIRED_DOCS),
}


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
    if path in PROTECTED_GOVERNANCE_SURFACE_EXACT:
        return "protected_governance_surface"
    return "other"


def _kernel_surface_area(path: str) -> str | None:
    """The specific :data:`KERNEL_SURFACE_EXACT`/:data:`KERNEL_SURFACE_PREFIXES` key
    *path* matched -- the same key :data:`KERNEL_SURFACE_IMPACT_MAP` is declared over --
    or ``None`` if *path* does not classify as ``kernel_surface``."""

    if path in KERNEL_SURFACE_EXACT:
        return path
    for prefix in KERNEL_SURFACE_PREFIXES:
        if path.startswith(prefix):
            return prefix
    return None


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

    touched_source_documents = set(classified["source_document"])
    unmet_kernel_surface_areas = sorted(
        {
            area
            for path in classified["kernel_surface"]
            if (area := _kernel_surface_area(path)) is not None
            and touched_source_documents.isdisjoint(KERNEL_SURFACE_IMPACT_MAP[area])
        }
    )
    required_source_update_missing = bool(unmet_kernel_surface_areas)

    protected_surface_changed = bool(classified["protected_governance_surface"])
    required_governance_update_missing = (
        protected_surface_changed and not classified["governance_binding"]
    )

    merge_blocked = required_source_update_missing or required_governance_update_missing

    return {
        "schema_version": SCHEMA_VERSION,
        "changed_paths": sorted(changed_paths),
        "classified_paths": classified,
        "os_change_detected": os_change_detected,
        "required_source_update_missing": required_source_update_missing,
        "unmet_kernel_surface_areas": unmet_kernel_surface_areas,
        "protected_surface_changed": protected_surface_changed,
        "required_governance_update_missing": required_governance_update_missing,
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
