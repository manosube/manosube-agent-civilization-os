"""WU2: evidence recording per
``docs/validation/dots_production_acceptance/PROTOCOL.md`` Sec.8.

Raw receipts live outside the source tree in a caller-supplied evidence root; only a
hash-manifest entry is written into a repo-controlled manifest file. Evidence records
are derived through the ONE existing canonical call (``derive_evidence``).

**Scope boundary, corrected in this revision:** this module's job stops at recording
and submitting the evidence candidate -- it never commits a meaningful State update of
its own. A prior revision also exposed ``commit_evidence_record``, which let a caller
hand-build a ``next_state``/``transition`` and pass it straight to ``store.commit(...)``
-- a real Store write, but one that bypasses Evidence/closure evaluation entirely, i.e.
a second, parallel Reflow invented by this module rather than the one that already
exists. That function has been removed.

The real connection point for a meaningful State update is the existing
``manosube_agent_civilization.reflow.route.reflow`` function, specifically its own
``provenance_only_evidence_requests`` parameter: it accepts the same evidence-request
shape ``derive_evidence`` (and this module's ``record_evidence_via_canonical_route``)
already takes, calls the real ``derive_evidence`` on each one itself, and persists the
result through its own real, atomic ``commit_reflow`` transaction -- never through a
second commit path this module would have to build and keep correct. A caller that
wants the evidence candidate this module derived to actually land in Store passes the
same request into *that* parameter of a real ``reflow()`` call; this module does not
wrap or shortcut that call itself, to keep the one real connection point visibly single.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from manosube_agent_civilization.evidence import derive_evidence
from manosube_agent_civilization.work_time_transparency.clock import default_clock


class RecorderError(Exception):
    """Raised when this module is asked to do something PROTOCOL.md Sec.8 forbids --
    e.g. write a raw receipt inside the source tree it was given, or use an unsafe
    ``run_id`` as a path component."""


# A run_id must be a single, safe path segment -- no separators, no "..", not absolute.
# This alone already rejects both reported escapes (an absolute path, and "../repo"),
# since both require a "/" character this pattern forbids; the first character is
# additionally restricted to alphanumeric so a bare "." or ".." (themselves containing
# no "/") can never match either.
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class ReceiptRecord:
    receipt_id: str  # content-addressed: "RCT-" + sha256 of the canonical payload bytes
    sha256: str
    raw_path: Path
    run_id: str
    recorded_at: str


def write_raw_receipt(
    evidence_root: Path,
    *,
    run_id: str,
    payload: Mapping[str, Any],
    source_tree_root: Path,
    clock: Callable[[], str] = default_clock,
) -> ReceiptRecord:
    """PROTOCOL.md Sec.8: raw receipts live outside the source tree. Refuses
    (``RecorderError``) if *evidence_root* resolves inside, or equal to,
    *source_tree_root* -- the one rule this function enforces programmatically rather
    than by convention alone, since a second State inside the tracked tree is exactly
    what this document forbids.

    *run_id* becomes a path component (``evidence_root/run_id/...``) and is therefore
    restricted to a single safe identifier (see ``_RUN_ID_PATTERN``) -- an unvalidated
    *run_id* previously let an absolute path (which, joined onto another path with
    ``pathlib``'s own ``/`` operator, silently discards everything to its left) or a
    ``"../..."`` segment land the receipt anywhere, including inside the source tree
    this function exists to keep raw receipts out of. After joining, the actual
    resolved destination is also verified to still be inside *evidence_root* and
    outside *source_tree_root* -- defense in depth, independent of the *run_id* check
    above, in case *evidence_root* itself turns out to traverse a symlink."""

    evidence_root_resolved = evidence_root.resolve()
    source_tree_resolved = source_tree_root.resolve()
    if evidence_root_resolved == source_tree_resolved or source_tree_resolved in evidence_root_resolved.parents:
        raise RecorderError(
            f"evidence_root {evidence_root_resolved} must be outside source_tree_root "
            f"{source_tree_resolved}, per PROTOCOL.md Sec.8"
        )

    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise RecorderError(
            f"run_id {run_id!r} must be a single safe identifier matching "
            f"{_RUN_ID_PATTERN.pattern!r} (no path separators, no '..', not an absolute "
            "path) -- refusing to use it as a path component"
        )

    raw_bytes = _canonical_json_bytes(payload)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    receipt_id = f"RCT-{digest}"

    run_dir = evidence_root_resolved / run_id
    raw_path = run_dir / f"{receipt_id}.json"

    # Defense in depth, independent of the run_id check above: verify the actual
    # resolved destination is inside evidence_root_resolved and outside
    # source_tree_resolved, in case evidence_root_resolved itself traverses a symlink.
    # (resolve() does not require the path to exist.)
    raw_path_resolved = raw_path.resolve()
    if evidence_root_resolved != raw_path_resolved and evidence_root_resolved not in raw_path_resolved.parents:
        raise RecorderError(
            f"resolved receipt path {raw_path_resolved} would escape evidence_root "
            f"{evidence_root_resolved} -- refusing to write"
        )
    if source_tree_resolved == raw_path_resolved or source_tree_resolved in raw_path_resolved.parents:
        raise RecorderError(
            f"resolved receipt path {raw_path_resolved} would land inside source_tree_root "
            f"{source_tree_resolved} -- refusing to write"
        )

    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw_bytes)

    return ReceiptRecord(
        receipt_id=receipt_id, sha256=digest, raw_path=raw_path, run_id=run_id, recorded_at=clock()
    )


@dataclass(frozen=True)
class ManifestEntry:
    receipt_id: str
    sha256: str
    run_id: str
    recorded_at: str
    evidence_id: str | None = None


def append_manifest_entry(manifest_path: Path, entry: ManifestEntry) -> None:
    """Append-only: never rewrites or removes a prior line, per PROTOCOL.md Sec.8's own
    "改竄receipt/欠落case/重複runのnegative controls" requirement -- an append-only
    manifest is what makes a later integrity recompute able to detect a missing or
    altered line in the first place."""

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(
        {
            "receipt_id": entry.receipt_id,
            "sha256": entry.sha256,
            "run_id": entry.run_id,
            "recorded_at": entry.recorded_at,
            "evidence_id": entry.evidence_id,
        },
        sort_keys=True,
    )
    with manifest_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def read_manifest_entries(manifest_path: Path) -> list[dict[str, Any]]:
    if not manifest_path.exists():
        return []
    entries = []
    with manifest_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


def record_evidence_via_canonical_route(evidence_request: Mapping[str, Any]) -> dict[str, Any]:
    """The ONE call to the canonical Evidence owner this module makes -- a thin,
    explicit pass-through so WU2 code has a single, auditable import point for Evidence
    derivation, mirroring every real caller's own pattern (e.g.
    ``independent_verification/evidence_handoff.py``,
    ``change_executor/evidence_handoff.py``): construct the request, call
    ``derive_evidence(request)`` once, return the result. Adds no second derivation
    logic of its own."""

    return derive_evidence(dict(evidence_request))
