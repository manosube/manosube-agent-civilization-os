"""Temporary Agent lifecycle (Phase 12, Issue #49): ``KERNEL_ELEMENT=EPHEMERAL_EXECUTION_ADAPTER``.

Adds exactly one provider-neutral, in-process lifecycle adapter over the existing, already-
verified Phase 10 Boot route:

.. code-block:: python

   agent = start_temporary_agent(store, project_id=..., project_binding_id=...)
   agent.boot_context  # read-only while active
   agent.release()  # idempotent, local, zero-write

This is not a ninth Kernel element (the same ``KERNEL_ELEMENT=none``-style convention Boot and
the CLI already use, here spelled ``EPHEMERAL_EXECUTION_ADAPTER``): it never validates,
restores, or reverifies a Project itself -- that remains Boot's own, one-owner concern
(:func:`~manosube_agent_civilization.boot.boot_project`) -- and it never mutates the Store,
grants Authority, executes a Change, or observes an external system. A ``TemporaryAgent``
exists only in process memory: it creates no canonical record, schema, directory, journal,
manifest, cache, resume token, durable agent id, or long-term memory, and is never model-,
tool-, command-, or network-capable. ``TemporaryAgent`` is constructible only through
``start_temporary_agent`` (Structural Review Round 1, P12-R1-F1) -- a direct
``TemporaryAgent(...)`` call, or one over a payload that is not already a real ``BootContext``,
raises ``AgentConstructionError`` rather than producing an Agent over unverified data.

See ``07_AGENT_RUNTIME/AGENT_RUNTIME_INDEX.md`` for the full contract set.
"""

from .agent import TemporaryAgent
from .errors import AgentConstructionError, AgentReleasedError, AgentRuntimeError
from .route import start_temporary_agent

__all__ = [
    "AgentConstructionError",
    "AgentReleasedError",
    "AgentRuntimeError",
    "TemporaryAgent",
    "start_temporary_agent",
]
