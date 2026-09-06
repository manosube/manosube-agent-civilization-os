"""Boot (Phase 10, Issue #45): ``KERNEL_ELEMENT=NONE_ADAPTER_ENTRY``.

Restores an already-bound Project -- its Project Binding, Objective Revision, Authority
Rule, and current State -- from an existing, already-initialized canonical Store into one
immutable, non-authoritative Boot Context, so a caller can begin a Phase 8 Reflow cycle.
This is not a ninth Kernel element (the same ``KERNEL_ELEMENT=none`` convention Development
Binding and Product Binding already use), and it is not initialization, discovery, or repair:
Boot never calls ``bind_project``, ``FileStateStore.initialize``, or ``FileStateStore.
recover``, never enumerates Store projects, and never mutates the Store.

See ``04_BOOT/BOOT_INDEX.md`` for the full contract set.
"""

from .context import BootContext
from .errors import BootConsistencyError, BootError, BootNotFoundError
from .route import boot_project

__all__ = [
    "BootConsistencyError",
    "BootContext",
    "BootError",
    "BootNotFoundError",
    "boot_project",
]
