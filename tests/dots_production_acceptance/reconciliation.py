"""WU2: the Store/external-side-effect reconciliation gate per
``docs/validation/dots_production_acceptance/MEASUREMENT_CONTRACT.md`` Sec.A,
"Reconciliation completion" row.

Declares reconciliation complete only from BOTH (1) a real Store re-read
(``FileStateStore.read_current_consistent``) matching the expected post-condition, AND
(2) an independent re-read of the external side effect -- never from either alone.

The external-side read itself is the connection-method-dependent boundary: this module
ships with that boundary as an injected callable only. A real dots-specific reader
(GitHub API state, dots' own task/relay state, etc.) is ``dots_adapter.py``'s job, built
after SHUKOU's Reading A/B/C decision (``OPEN_ITEMS.md`` item 1) -- never guessed at or
stubbed with fabricated behavior here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from manosube_agent_civilization.work_time_transparency.clock import default_clock


class ReconciliationError(Exception):
    """Raised when this gate is asked to decide without both required inputs -- e.g. a
    missing external_reader -- rather than silently reconciling from one side alone."""


@dataclass(frozen=True)
class ReconciliationResult:
    store_matched: bool
    external_matched: bool
    reconciled: bool  # True only if BOTH of the above are True
    store_observed: Mapping[str, Any]
    external_observed: Mapping[str, Any]
    checked_at: str


def reconcile(
    store: Any,
    *,
    project_id: str,
    expected_state_predicate: Callable[[Mapping[str, Any]], bool],
    external_reader: Callable[[], Mapping[str, Any]],
    expected_external_predicate: Callable[[Mapping[str, Any]], bool],
    clock: Callable[[], str] = default_clock,
) -> ReconciliationResult:
    """MEASUREMENT_CONTRACT.md Sec.A's two-part reconciliation gate, implemented
    exactly: (1) re-reads the real current Project State via
    ``store.read_current_consistent(project_id)`` -- the same quiescence-checked,
    fail-closed surface Boot itself uses -- and tests it against
    *expected_state_predicate*; (2) calls the caller-supplied, connection-method-
    dependent *external_reader* and tests its result against
    *expected_external_predicate*. ``reconciled`` is True only when both checks pass.
    Never declares reconciliation complete from either check alone, and never resends
    or retries anything itself -- that decision belongs to the caller (the driver),
    per this contract's own invariant that no dispatch may be resent while the prior
    attempt's outcome is unknown."""

    store_observed = store.read_current_consistent(project_id)
    store_matched = bool(expected_state_predicate(store_observed))

    external_observed = external_reader()
    external_matched = bool(expected_external_predicate(external_observed))

    return ReconciliationResult(
        store_matched=store_matched,
        external_matched=external_matched,
        reconciled=store_matched and external_matched,
        store_observed=store_observed,
        external_observed=external_observed,
        checked_at=clock(),
    )
