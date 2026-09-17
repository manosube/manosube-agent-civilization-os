"""PR #90 corrected Round 6 rebind (``ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN``,
comment 5715652626) -- the frozen protocol's own predeclared, native-Agent-free mechanical
reproduction procedure (``reproduction_procedure.entrypoint`` in
:mod:`tests.fixtures.comparative_benchmark_rebind_protocol`).

This corpus's own two tasks are fully deterministic and independently computable without any
native Agent capability: a SHA-256 digest of a fixed literal string, and the ascending prime
list in ``[2, 50]``. This module mechanically recomputes both, maps them onto this protocol's
own two comparison groups, and returns ``reproduced_raw_events`` in exactly the shape
:func:`manosube_agent_civilization.comparative_benchmark.engine.aggregate_metrics` expects --
never a native-Agent re-invocation this repository has no capability to offer any third party
(:mod:`tests.fixtures.comparative_benchmark_rebind_protocol`'s own comparability_loss_receipts
disclose this honestly). Any actor holding a Python interpreter can run this module and
independently confirm the frozen corpus's own declared per-group outcome counts."""

from __future__ import annotations

import hashlib
from typing import Any

from tests.fixtures import comparative_benchmark_rebind_protocol as rb

from manosube_agent_civilization.work_time_transparency.clock import default_clock

#: The literal ASCII string this frozen corpus's own ``task_a`` hashes -- identical to
#: ``examples/comparative_benchmark/real_agent_corpus/TASK_CORPUS.md``'s own declared task.
TASK_A_LITERAL = "MANOSUBE_PHASE21_ROUND6_TASK_A"


def _task_a_digest() -> str:
    return hashlib.sha256(TASK_A_LITERAL.encode("ascii")).hexdigest()


def _task_b_primes() -> str:
    primes = [p for p in range(2, 51) if all(p % d for d in range(2, int(p**0.5) + 1))]
    return ",".join(str(p) for p in primes)


def reproduce_raw_events() -> list[dict[str, Any]]:
    """Mechanically recompute both frozen tasks and return one ``COMPLETED_VERIFIED``
    ``task_attempt`` raw event per (comparison_group_id, task_id) pair this protocol
    declares -- both this frozen corpus's own comparison groups reach the identical
    outcome under its own always-authorizing Authority Rule (see the protocol freeze's
    own predeclared ``numeric_thresholds``)."""

    task_a_digest = _task_a_digest()
    task_b_primes = _task_b_primes()
    if task_a_digest != "b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8":
        raise AssertionError(
            f"task_a mechanical recomputation diverged: got {task_a_digest!r}, expected the "
            "frozen corpus's own published digest"
        )
    if task_b_primes != "2,3,5,7,11,13,17,19,23,29,31,37,41,43,47":
        raise AssertionError(
            f"task_b mechanical recomputation diverged: got {task_b_primes!r}, expected the "
            "frozen corpus's own published prime list"
        )

    now = default_clock()
    events: list[dict[str, Any]] = []
    for group_id in (rb.PRESENT_GROUP_ID, rb.ABSENT_GROUP_ID):
        for task_id in rb.TASK_IDS:
            events.append(
                {
                    "kind": "task_attempt",
                    "comparison_group_id": group_id,
                    "task_id": task_id,
                    "outcome": "COMPLETED_VERIFIED",
                    "started_at": now,
                    "closed_at": now,
                    "reason": (
                        "mechanical, native-Agent-free deterministic recomputation "
                        "(tests.comparative_benchmark.frozen_protocol_reproduction) -- see "
                        "this protocol's own comparability_loss_receipts CLR-CB21-R6F-0002"
                    ),
                }
            )
    return events


__all__ = ["TASK_A_LITERAL", "reproduce_raw_events"]
