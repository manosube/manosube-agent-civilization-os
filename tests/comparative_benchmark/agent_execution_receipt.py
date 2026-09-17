"""PR #90 Round 6 correction (Structural Advisor interim finding P90-R6-IF1, comment
5715107317): a real, machine-verifiable execution receipt binding a genuine tool-using
Agent action to its Agent identity, condition, task input, tool surface, resource budget,
and output content -- so the ``MANOSUBE_PRESENT``/``MANOSUBE_ABSENT`` lifecycle resolves and
verifies a receipt of a real action that already happened, rather than invoking a Python
callback and self-labeling that callback's own execution as "the real Agent action".

P90-R6-IF1, verbatim: "ordinary in-process Python computes SHA-256 and calls
``Path.write_text(...)``... Calling the callback 'the real Agent action' in docstrings/
RAW_EVENTS.md does not change its executable identity." This module is the fix: it never
performs a task itself (there is no ``perform_real_change``-shaped callable anywhere in this
module), it only builds a receipt *from* an already-completed real action's own real,
independently-observable artifacts (its output file's real bytes on disk), and verifies a
receipt against an expected identity/condition/task/tool-surface/resource-budget/output-digest
tuple, refusing fail-closed on any mismatch -- exactly the discipline
``manosube_agent_civilization.evidence``/``.observation`` already apply to every other
Evidence-bearing record in this repository, applied here to an external Agent action's own
receipt.

A receipt is not a claim this module trusts blindly: :func:`verify_agent_execution_receipt`
re-derives the receipt's own content-addressed id from its body (catching a hand-edited
receipt), and re-reads and re-hashes the real output file fresh off disk at verification time
(catching a receipt whose claimed digest no longer matches what is actually on disk, or a
receipt built for one file being pointed at another) -- never relying on the receipt's own
self-reported digest alone.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

SCHEMA_VERSION = "0.1"

CONDITIONS: frozenset[str] = frozenset({"MANOSUBE_PRESENT", "MANOSUBE_ABSENT"})


class AgentExecutionReceiptError(Exception):
    """Base class for every refusal :func:`verify_agent_execution_receipt` raises."""


class ReceiptIntegrityError(AgentExecutionReceiptError):
    """The receipt's own declared ``receipt_id`` does not match its recomputed content
    address -- the receipt body was hand-edited or corrupted after being built."""


class AgentIdentityMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``RECEIPT_AGENT_IDENTITY_MISMATCH``."""


class ConditionMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative controls: ``RECEIPT_CONDITION_MISMATCH`` and
    ``RECEIPT_REPLAY_OR_CROSS_CONDITION_REUSE`` (reusing one condition's real receipt where
    the other condition is expected is exactly a condition mismatch)."""


class TaskInputMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``RECEIPT_TASK_INPUT_MISMATCH``."""


class ToolSurfaceMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``RECEIPT_TOOL_SURFACE_MISMATCH``."""


class ResourceBudgetMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``RECEIPT_RESOURCE_BUDGET_MISMATCH``."""


class OutputDigestMismatchError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``RECEIPT_OUTPUT_DIGEST_MISMATCH`` -- also the mechanism
    that refuses ``PREEXISTING_OUTPUT_WITHOUT_EXECUTION_RECEIPT`` once combined with
    :func:`resolve_and_verify_receipt`'s own required-receipt-file check."""


class ReceiptNotFoundError(AgentExecutionReceiptError):
    """P90-R6-IF1 negative control: ``PREEXISTING_OUTPUT_WITHOUT_EXECUTION_RECEIPT`` -- an
    output file exists but no receipt file names it."""


def _canonical_body(receipt: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if key != "receipt_id"}


def agent_execution_receipt_id(receipt: dict[str, Any]) -> str:
    """The receipt's own content-addressed identity -- sha256 over the canonical JSON of
    every field except ``receipt_id`` itself, so a receipt can never declare its own id;
    verification always recomputes it fresh."""

    body = _canonical_body(receipt)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return "AGENT-RECEIPT-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest().upper()


def build_agent_execution_receipt(
    *,
    agent_identity: dict[str, str],
    condition: str,
    task_key: str,
    task_input: str,
    tool_surface: list[str],
    resource_budget: dict[str, Any],
    output_path: str,
    tool_call_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build one real execution receipt from an already-completed real action's own real,
    on-disk output -- never performs the action itself. *output_path* is repository-relative;
    its real, current bytes (read fresh, not cached) are what this receipt's own
    ``output_sha256`` commits to.

    *tool_call_events* is the real, raw record of the tool call(s) that performed the action
    (tool name, start/end instants, and the command or write actually issued) -- published
    verbatim into the receipt so the receipt itself carries the same raw provenance
    ``RAW_EVENTS.md`` already publishes, rather than a bare assertion.
    """

    if condition not in CONDITIONS:
        raise AgentExecutionReceiptError(f"unrecognized condition: {condition!r}")
    real_bytes = (ROOT / output_path).read_bytes()
    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "agent_identity": dict(agent_identity),
        "condition": condition,
        "task_key": task_key,
        "task_input": task_input,
        "tool_surface": sorted(tool_surface),
        "resource_budget": dict(resource_budget),
        "output_path": output_path,
        "output_sha256": hashlib.sha256(real_bytes).hexdigest(),
        "tool_call_events": list(tool_call_events),
    }
    receipt["receipt_id"] = agent_execution_receipt_id(receipt)
    return receipt


def verify_agent_execution_receipt(
    receipt: dict[str, Any],
    *,
    expected_agent_identity: dict[str, str],
    expected_condition: str,
    expected_task_key: str,
    expected_task_input: str,
    expected_tool_surface: list[str],
    expected_resource_budget: dict[str, Any],
    expected_output_path: str,
) -> None:
    """Verify *receipt* against every expected field, and independently re-derive both the
    receipt's own content-addressed id and its claimed output digest from the real,
    current bytes on disk. Raises the specific typed error for the first mismatch found;
    raises nothing if every check passes.

    Never trusts the receipt's own self-reported ``output_sha256`` alone: this function
    re-reads *expected_output_path* fresh off disk at verification time and independently
    recomputes the digest, so a receipt that no longer matches what is actually on disk (or
    that was built for a different file) is refused even if its own ``output_sha256`` field
    is internally self-consistent.
    """

    recomputed_id = agent_execution_receipt_id(receipt)
    if recomputed_id != receipt.get("receipt_id"):
        raise ReceiptIntegrityError(
            f"receipt_id {receipt.get('receipt_id')!r} does not match the body's own "
            f"recomputed content address {recomputed_id!r} -- receipt was tampered with"
        )
    if receipt.get("agent_identity") != expected_agent_identity:
        raise AgentIdentityMismatchError(
            f"receipt agent_identity {receipt.get('agent_identity')!r} != expected "
            f"{expected_agent_identity!r}"
        )
    if receipt.get("condition") != expected_condition:
        raise ConditionMismatchError(
            f"receipt condition {receipt.get('condition')!r} != expected "
            f"{expected_condition!r} -- a receipt from one condition cannot stand in for "
            "the other"
        )
    if (
        receipt.get("task_key") != expected_task_key
        or receipt.get("task_input") != expected_task_input
    ):
        raise TaskInputMismatchError(
            f"receipt task_key/task_input {receipt.get('task_key')!r}/"
            f"{receipt.get('task_input')!r} != expected {expected_task_key!r}/"
            f"{expected_task_input!r}"
        )
    if sorted(receipt.get("tool_surface") or []) != sorted(expected_tool_surface):
        raise ToolSurfaceMismatchError(
            f"receipt tool_surface {receipt.get('tool_surface')!r} != expected "
            f"{sorted(expected_tool_surface)!r}"
        )
    if receipt.get("resource_budget") != expected_resource_budget:
        raise ResourceBudgetMismatchError(
            f"receipt resource_budget {receipt.get('resource_budget')!r} != expected "
            f"{expected_resource_budget!r}"
        )
    if receipt.get("output_path") != expected_output_path:
        raise TaskInputMismatchError(
            f"receipt output_path {receipt.get('output_path')!r} != expected "
            f"{expected_output_path!r}"
        )
    real_bytes = (ROOT / expected_output_path).read_bytes()
    real_digest = hashlib.sha256(real_bytes).hexdigest()
    if receipt.get("output_sha256") != real_digest:
        raise OutputDigestMismatchError(
            f"receipt output_sha256 {receipt.get('output_sha256')!r} != the real, current "
            f"digest of {expected_output_path!r} ({real_digest!r}) -- the file was modified "
            "after the receipt was built, or the receipt was built for different content"
        )


def load_receipt(receipt_path: str) -> dict[str, Any]:
    """Load a real, published receipt JSON file from a repository-relative path. Raises
    :class:`ReceiptNotFoundError` if it does not exist -- the mechanism that refuses
    ``PREEXISTING_OUTPUT_WITHOUT_EXECUTION_RECEIPT``: an output file with no receipt file
    naming it never resolves here."""

    path = ROOT / receipt_path
    if not path.exists():
        raise ReceiptNotFoundError(f"no receipt file at {receipt_path!r}")
    return dict(json.loads(path.read_text(encoding="utf-8")))
