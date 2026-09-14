"""Human Wait-Time Transparency (Issue #22): canonical timing/terminal-status schemas, one
deterministic coordination evaluator/state machine, and composition wrappers proving conformance
across every execution-capable adapter this repository's own kernel exposes.

Public entrypoints (:mod:`~manosube_agent_civilization.work_time_transparency.route`):

- :func:`~manosube_agent_civilization.work_time_transparency.route.open_work_time_coordination`
- :func:`~manosube_agent_civilization.work_time_transparency.route.record_work_time_progress_update`
- :func:`~manosube_agent_civilization.work_time_transparency.route.record_work_time_terminal_notice`

See ``16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md`` for the full operating
contract, and this module's own ``route.py`` docstring for the non-Authority/non-Evidence
structural boundary.
"""

from __future__ import annotations

from .adapters import with_work_time_coordination
from .route import (
    open_work_time_coordination,
    record_work_time_progress_update,
    record_work_time_terminal_notice,
)
from .types import ADAPTER_KINDS, POSITION_KINDS, TERMINAL_OUTCOMES

__all__ = [
    "ADAPTER_KINDS",
    "POSITION_KINDS",
    "TERMINAL_OUTCOMES",
    "open_work_time_coordination",
    "record_work_time_progress_update",
    "record_work_time_terminal_notice",
    "with_work_time_coordination",
]
