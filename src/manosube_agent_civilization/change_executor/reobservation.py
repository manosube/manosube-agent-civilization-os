"""Independent after-state re-observation (P18-R1-F1, Structural Review Round 1).

Before this correction, ``evidence_handoff.py``'s own ``_construct_provenance`` mapped a
receipt's own self-reported ``outcome == "SUCCEEDED"`` directly to Evidence's own
``verification_result_provenance.status = "VERIFIED"`` -- using the receipt's own
``executor_identity``/``executor_version`` as ``verifier_identity``. That let the executor
self-promote its own success report into Evidence, with no independent check that the files
actually written match what was actually requested: the adapter's own ``AdapterReport`` (
``files_written``/``bytes_written``/``files_deleted``) is a self-reported fact about what the
adapter itself believes it did, never independently re-confirmed against the real, resulting
filesystem state.

This module is deliberately **not** a wiring-in of the full ``independent_verification``
package. ``run_independent_verification`` requires a SHUKOU-authorized ``VerifierSelection`` plus
a Store-resolved grant/declaration chain -- the human-selected-verifier claim-verification
concern, a different one from this package's own bounded, autonomous, low-risk execution.
Requiring a fresh human grant per autonomous execution would defeat Phase 18's whole bounded-
autonomy design (an executor that must stop and wait for a human to authorize its own
after-the-fact re-observation is not autonomous at all). Instead, this module performs a
genuine, independent, read-only re-read of the actual resulting filesystem state, by this
package itself, deliberately separate from -- and never trusting -- the adapter's own
self-reported facts: for every ``file_writes`` entry, it reads the actual current bytes at
``worktree_root/<path>`` directly via :meth:`pathlib.Path.read_bytes`, computes its own SHA-256
digest, and compares it against the SHA-256 digest of the *requested* ``content_utf8`` from the
operation itself (never against ``adapter_report["bytes_written"]``/``files_written``, which are
never treated as proof of content); for every ``file_deletes`` entry, it independently confirms
the path no longer exists.

The result of this independent re-read (see :func:`independently_reobserve`) is what
``route.py`` requires to agree with the adapter's own raw facts before a receipt's own
``outcome`` may ever be ``"SUCCEEDED"`` -- and it is embedded, verbatim, inside the committed
``change_execution_receipt`` itself (a new, schema-required field,
``independent_after_state_observation``), so the independent confirmation becomes a durable,
immutable, tamper-checked fact of the receipt, never a transient value discarded once
``execute()`` returns.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
from typing import Any

#: The one, fixed value :func:`independently_reobserve` returns when no independent
#: re-observation was ever attempted for a given receipt -- the adapter was never reached at all
#: (``KILL_SWITCH_STOPPED``/``BOUNDARY_VIOLATION``), or its own outcome could not be trusted
#: enough to re-observe against (``UNKNOWN``, from a raised adapter exception or a structurally
#: invalid adapter report -- P18-R1-F4). A fixed, shared constant so every such call site embeds
#: the byte-identical shape.
NOT_PERFORMED_REOBSERVATION: dict[str, Any] = {"outcome": "NOT_PERFORMED", "checked_files": []}


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def independently_reobserve(
    operation: Mapping[str, Any], worktree_root: str, adapter_report: Mapping[str, Any]
) -> dict[str, Any]:
    """Independently re-read the actual, current, on-disk filesystem state named by
    *operation*, strictly beneath *worktree_root* -- never trusting *adapter_report*'s own
    self-reported facts as proof of content. *adapter_report* is accepted (the closed,
    already-validated :class:`~manosube_agent_civilization.change_executor.types.AdapterReport`
    ``route.py`` itself already validated before calling this function) purely so a future,
    stricter cross-check against the adapter's own claimed file list has a place to live without
    changing this function's own call shape; this delivery's own comparison is against
    *operation*'s own requested content alone, deliberately never against anything
    *adapter_report* claims.

    Returns a structured, deterministic, JSON-serializable result naming exactly which files
    matched/mismatched -- never a bare boolean:

    ``{"outcome": "MATCHED" | "MISMATCH" | "MISSING", "checked_files": [
        {"path": ..., "kind": "write" | "delete", "status": "MATCHED" | "MISMATCH" | "MISSING"},
        ...
    ]}``

    Per-file status, independently determined for each entry:

    - a ``file_writes`` entry: ``"MATCHED"`` when the file exists and its own freshly-read
      SHA-256 digest equals the SHA-256 digest of the requested ``content_utf8``; ``"MISMATCH"``
      when the file exists but the digest differs; ``"MISSING"`` when the file does not exist (or
      cannot be read) at all.
    - a ``file_deletes`` entry: ``"MATCHED"`` when the path genuinely no longer exists;
      ``"MISMATCH"`` when it still does (there is no ``"MISSING"`` state for a delete).

    Top-level ``outcome``: ``"MISMATCH"`` if any per-file entry is ``"MISMATCH"``; otherwise
    ``"MISSING"`` if any per-file entry is ``"MISSING"``; otherwise ``"MATCHED"``.
    """

    root = Path(worktree_root)
    checked_files: list[dict[str, str]] = []
    any_mismatch = False
    any_missing = False

    for entry in operation["file_writes"]:
        path = entry["path"]
        expected_digest = _sha256_hex(entry["content_utf8"].encode("utf-8"))
        target = root / path
        status: str
        if not target.is_file():
            status = "MISSING"
        else:
            try:
                actual_digest = _sha256_hex(target.read_bytes())
            except OSError:
                status = "MISSING"
            else:
                status = "MATCHED" if actual_digest == expected_digest else "MISMATCH"
        checked_files.append({"path": path, "kind": "write", "status": status})
        if status == "MISMATCH":
            any_mismatch = True
        elif status == "MISSING":
            any_missing = True

    for entry in operation["file_deletes"]:
        path = entry["path"]
        target = root / path
        still_exists = target.exists() or target.is_symlink()
        status = "MISMATCH" if still_exists else "MATCHED"
        checked_files.append({"path": path, "kind": "delete", "status": status})
        if still_exists:
            any_mismatch = True

    if any_mismatch:
        outcome = "MISMATCH"
    elif any_missing:
        outcome = "MISSING"
    else:
        outcome = "MATCHED"

    return {"outcome": outcome, "checked_files": checked_files}


__all__ = ["NOT_PERFORMED_REOBSERVATION", "independently_reobserve"]
