"""Closed Change Executor vocabularies and the Change Executor Adapter Protocol (Phase 18,
Issue #73).

Mirrors :mod:`manosube_agent_civilization.url_boot.types`'s own discipline: a closed
``frozenset`` outcome vocabulary, and a minimal ``Protocol`` a replaceable adapter must satisfy
-- exactly one executable method, receiving only a prevalidated closed operation and an
admitted worktree root, never raw prose, a URL, model output, or an arbitrary command string.
The adapter itself asserts no :data:`EXECUTION_OUTCOMES` member; it reports only raw,
structurally bounded facts, and :mod:`~manosube_agent_civilization.change_executor.route` alone
classifies those facts into one outcome -- the identical "no ambient classification power in
the adapter" lesson ``url_boot``'s own Structural Review Rounds 4-5 already established.
"""

from __future__ import annotations

from typing import Any, Protocol, TypedDict

#: The complete, closed terminal-outcome vocabulary a ``change_execution_receipt`` may ever
#: record (P18-C9). ``REFUSED`` covers a generic, well-formed-but-inadmissible request refused
#: before any Store commit (this package's own route never itself commits a receipt carrying
#: this outcome -- a refusal at that stage is a raised, typed exception with zero Store I/O of
#: any kind, per this package's own preflight discipline -- but the outcome remains part of the
#: closed contract vocabulary a future caller or adapter path may need). ``BOUNDARY_VIOLATION``
#: is deliberately distinct and narrower: a well-typed operation that would exceed the bound
#: Boundary's own limits, discovered *after* an ``execution_attempt`` is already committed, and
#: therefore recorded as a genuine terminal receipt rather than a bare exception (this
#: package's own route does produce this one). Not every member is necessarily reachable by
#: this package's own :class:`~manosube_agent_civilization.change_executor.adapter.
#: ControlledFilesystemAdapter` and its purely synchronous, local, non-networked execution path
#: (``TIMEOUT`` in particular: this package reads no ambient clock, so no call site can ever
#: genuinely measure or report one) -- the vocabulary is closed and complete for the *contract*,
#: not a claim that one route implementation exercises every member.
EXECUTION_OUTCOMES: frozenset[str] = frozenset(
    {
        "SUCCEEDED",
        "REFUSED",
        "BOUNDARY_VIOLATION",
        "STALE_AUTHORITY",
        "TARGET_DRIFT",
        "KILL_SWITCH_STOPPED",
        "TIMEOUT",
        "ADAPTER_FAILURE",
        "PARTIAL_MUTATION",
        "ROLLBACK_SUCCEEDED",
        "ROLLBACK_FAILED",
        "UNKNOWN",
    }
)

#: The ``rollback_outcome`` a receipt may carry -- ``None`` for an outcome no rollback question
#: ever applies to (e.g. ``SUCCEEDED``, or a refusal before any file was ever touched).
ROLLBACK_OUTCOMES: frozenset[str] = frozenset(
    {"NOT_ATTEMPTED", "ROLLBACK_SUCCEEDED", "ROLLBACK_FAILED"}
)


class FileWrite(TypedDict):
    """One admitted file write -- a relative path and its complete UTF-8 text content."""

    path: str
    content_utf8: str


class FileDelete(TypedDict):
    """One admitted file deletion -- a relative path."""

    path: str


class ExecutionOperation(TypedDict):
    """The closed, prevalidated operation shape :class:`ChangeExecutorAdapter.execute` ever
    receives. Every path named in ``file_writes``/``file_deletes`` has already been checked, by
    the route alone, against the bound Boundary's own ``admitted_paths``/``max_files_changed``/
    ``max_bytes_changed``/``max_file_bytes`` limits before the adapter is ever reached -- the
    adapter itself performs no admission decision of any kind, only mechanical filesystem work
    strictly beneath the ``worktree_root`` it is handed."""

    operation_kind: str
    file_writes: list[FileWrite]
    file_deletes: list[FileDelete]


class AdapterReport(TypedDict):
    """The closed, raw-facts shape :class:`ChangeExecutorAdapter.execute` must return -- honest,
    structurally bounded facts about what mechanically happened, never a classification. The
    route alone turns this into one :data:`EXECUTION_OUTCOMES` member."""

    files_written: list[str]
    bytes_written: int
    files_deleted: list[str]
    error: str | None


class ChangeExecutorAdapter(Protocol):
    """The one replaceable execution capability this package ever calls -- exactly one
    executable method, receiving only a prevalidated closed :class:`ExecutionOperation` and the
    admitted ``worktree_root`` path, never raw prose, a URL, model output, or an arbitrary
    command string. Returns an :class:`AdapterReport`: raw, structurally bounded facts, never an
    asserted :data:`EXECUTION_OUTCOMES` member -- the adapter has no ambient classification
    power, exactly as :mod:`~manosube_agent_civilization.url_boot.route`'s own Structural Review
    Rounds established for its own replaceable adapter surface.

    An adapter never owns canonical State, decides Authority, determines Evidence sufficiency,
    closes a Difference, mutates Store internals, decides whether an operation is in-scope, or
    performs network, subprocess, environment-mutation, or credential-access I/O of any kind --
    it is a bounded, mechanical filesystem primitive, full stop.
    """

    def execute(self, operation: Any, *, worktree_root: str) -> dict[str, Any]:
        """Perform exactly the writes/deletes named in *operation*, strictly beneath
        *worktree_root*, and return an :class:`AdapterReport` of what mechanically happened."""
        ...


__all__ = [
    "EXECUTION_OUTCOMES",
    "ROLLBACK_OUTCOMES",
    "AdapterReport",
    "ChangeExecutorAdapter",
    "ExecutionOperation",
    "FileDelete",
    "FileWrite",
]
