"""WU2: evidence recording per
``docs/validation/dots_production_acceptance/PROTOCOL.md`` Sec.8.

Raw receipts live outside the source tree in a caller-supplied evidence root; only a
hash-manifest entry is written into a repo-controlled manifest file. Evidence records
are derived through the ONE existing canonical call (``derive_evidence``) and, when a
caller supplies a Store + project context, committed through the same ``store.commit``
transaction every other owner uses -- never a parallel Evidence-specific commit path,
never a second State.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from manosube_agent_civilization.evidence import EVIDENCE_REFERENCE_KIND, derive_evidence
from manosube_agent_civilization.work_time_transparency.clock import default_clock


class RecorderError(Exception):
    """Raised when this module is asked to do something PROTOCOL.md Sec.8 forbids --
    e.g. write a raw receipt inside the source tree it was given."""


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
    what this document forbids."""

    evidence_root_resolved = evidence_root.resolve()
    source_tree_resolved = source_tree_root.resolve()
    if evidence_root_resolved == source_tree_resolved or source_tree_resolved in evidence_root_resolved.parents:
        raise RecorderError(
            f"evidence_root {evidence_root_resolved} must be outside source_tree_root "
            f"{source_tree_resolved}, per PROTOCOL.md Sec.8"
        )

    raw_bytes = _canonical_json_bytes(payload)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    receipt_id = f"RCT-{digest}"

    run_dir = evidence_root_resolved / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / f"{receipt_id}.json"
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


def commit_evidence_record(
    store: Any,
    *,
    project_id: str,
    expected_revision: int,
    expected_fingerprint: Mapping[str, str],
    next_state: Mapping[str, Any],
    transition: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Commits an already-derived Evidence record through the same, single
    ``store.commit(...)`` transaction every other Kernel owner uses -- never a separate
    Evidence-specific committer. Callers build *next_state*/*transition* themselves
    (this module does not guess at State shape); this function only adds the one
    ``(EVIDENCE_REFERENCE_KIND, evidence_id, evidence)`` record to that same commit,
    using the real Evidence owner's own reference-kind constant (``"observation_evidence"``)
    rather than a guessed literal -- the same kind real callers such as
    ``multi_agent/evidence_handoff.py`` use when committing a derived Evidence record."""

    return store.commit(
        project_id,
        expected_revision,
        expected_fingerprint,
        next_state,
        transition,
        records=[(EVIDENCE_REFERENCE_KIND, evidence["evidence_id"], dict(evidence))],
    )
