"""Fixtures shared by state engine tests."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def initial_state() -> dict[str, Any]:
    """The genesis ``project_state`` fixture. Its own ``state_metadata.
    source_snapshot_refs`` names the real Kernel source snapshot :func:`real_kernel_
    source_snapshot` builds (R9-F2: ``GENESIS_KERNEL_PROVENANCE_REQUIRED=true`` -- even
    the very first State must carry real, resolvable Kernel provenance, not an empty
    placeholder). Computed fresh here rather than baked into the on-disk JSON case, so a
    real change to ``KERNEL_INVARIANTS.md``'s own bytes can never silently leave a stale
    id behind. This addition never touches ``semantic_fingerprint``:
    ``state.canonicalize.canonical_semantic_state_bytes`` (what ``fingerprint_project_
    state`` actually hashes) explicitly excludes ``state_metadata`` from that
    computation, so every already-recorded fingerprint in this suite stays valid.
    """

    cases = json.loads(
        (ROOT / "tests/contract/fixtures/schema/valid/cases.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(case for case in cases if case["name"] == "initial_state_revision_zero")
    state = deepcopy(case["instance"])
    snapshot_id = real_kernel_source_snapshot()["source_snapshot_id"]
    state["state_metadata"]["source_snapshot_refs"] = [
        {"kind": "source_snapshot", "id": snapshot_id}
    ]
    return state


def real_kernel_git_objects() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return ``(kernel_source_ref, kernel_source_witness)`` -- a real, self-consistent Git
    object witness proving ``00_KERNEL/KERNEL_INVARIANTS.md`` is reachable via a genuine
    commit/tree/blob chain (R4-F3). Built from ``KERNEL_INVARIANTS.md``'s own real on-disk
    bytes (so its blob sha genuinely equals the pinned ``KERNEL_INVARIANTS_BLOB_SHA``)
    wrapped in a synthetic but internally self-consistent tree/commit -- the same real
    object-hashing functions :func:`~manosube_agent_civilization.reflow.git_witness.
    verify_kernel_source_witness` itself uses. Fully deterministic (no timestamps), so
    every caller of this function -- ``tests/reflow_helpers.py``'s own
    ``real_kernel_source_witness`` included -- gets byte-identical objects.
    """

    from manosube_agent_civilization.reflow.git_witness import blob_sha1, commit_sha1, tree_sha1
    from manosube_agent_civilization.reflow.invariant_registry import (
        KERNEL_INVARIANTS_BLOB_SHA,
        KERNEL_INVARIANTS_PATH,
    )

    blob_content = (ROOT / KERNEL_INVARIANTS_PATH).read_bytes()
    blob_sha = blob_sha1(blob_content)
    assert blob_sha == KERNEL_INVARIANTS_BLOB_SHA, (
        "fixture drift: the on-disk KERNEL_INVARIANTS.md no longer matches the pinned blob sha"
    )

    leaf_entry = b"100644 KERNEL_INVARIANTS.md\0" + bytes.fromhex(blob_sha)
    leaf_tree_sha = tree_sha1(leaf_entry)
    root_entry = b"40000 00_KERNEL\0" + bytes.fromhex(leaf_tree_sha)
    root_tree_sha = tree_sha1(root_entry)
    commit_object = (
        f"tree {root_tree_sha}\n"
        "author Fixture <fixture@example.com> 0 +0000\n"
        "committer Fixture <fixture@example.com> 0 +0000\n"
        "\n"
        "fixture commit\n"
    ).encode()
    commit_sha = commit_sha1(commit_object)

    kernel_source_ref = {
        "kind": "git_tree",
        "repository": "manosube/manosube-agent-civilization-os",
        "commit_sha": commit_sha,
        "tree_sha": root_tree_sha,
    }
    kernel_source_witness = {
        "commit_object": commit_object.hex(),
        "tree_objects": {
            root_tree_sha: root_entry.hex(),
            leaf_tree_sha: leaf_entry.hex(),
        },
        "blob_object": blob_content.hex(),
    }
    return kernel_source_ref, kernel_source_witness


def real_kernel_source_snapshot() -> dict[str, Any]:
    """The real, content-addressed Source Snapshot naming this vertical's own Kernel
    source (``00_KERNEL/KERNEL_INVARIANTS.md``) -- R9-F2. Its own ``git_provenance`` is
    bound to the identical ``commit_sha``/``tree_sha``/``blob_sha`` :func:`real_kernel_
    git_objects` independently re-verifies, so a Candidate evaluated against that same
    witness and this snapshot's own claim always name the identical Kernel source. This
    is the record every ``project_state.state_metadata.source_snapshot_refs`` entry in
    these fixtures resolves to -- the canonical State's own base Kernel provenance,
    never a caller's bare restatement of ``base_kernel_source_ref``.
    """

    from manosube_agent_civilization.observation.source_snapshot import build_source_snapshot
    from manosube_agent_civilization.reflow.git_witness import blob_sha1
    from manosube_agent_civilization.reflow.invariant_registry import KERNEL_INVARIANTS_PATH

    kernel_source_ref, _ = real_kernel_git_objects()
    blob_content = (ROOT / KERNEL_INVARIANTS_PATH).read_bytes()
    return build_source_snapshot(
        source_locator=KERNEL_INVARIANTS_PATH,
        content_digest="sha256:" + hashlib.sha256(blob_content).hexdigest(),
        captured_at="2026-08-29T09:00:00Z",
        git_provenance={
            "repository": kernel_source_ref["repository"],
            "commit_sha": kernel_source_ref["commit_sha"],
            "tree_sha": kernel_source_ref["tree_sha"],
            "path": KERNEL_INVARIANTS_PATH,
            "blob_sha": blob_sha1(blob_content),
        },
    )
