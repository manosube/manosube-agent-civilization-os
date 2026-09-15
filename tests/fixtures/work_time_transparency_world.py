"""Issue #22 shared Work Coordination test world.

Deliberately self-contained -- the identical "each vertical's own fixture module builds its own
``bound()`` from ``tests.fixtures.product_binding`` directly" discipline every other ``tests/
fixtures/*_world.py`` module already keeps (see ``tests/fixtures/change_executor_world.py``'s
own module docstring), never importing another vertical's own fixture world.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore


def bound(tmp_path: Path, *, subdir: str = "backend") -> tuple[FileStateStore, dict[str, Any]]:
    """One real ``FileStateStore`` with one real, genuinely bound project."""

    store = FileStateStore(tmp_path / subdir, schema_root=SCHEMA_ROOT)
    kwargs = bind_project_kwargs()
    result = bind_project(
        store, **kwargs, additional_genesis_records=genesis_records(), schema_root=SCHEMA_ROOT
    )
    return store, {
        "project_id": kwargs["project_id"],
        "project_binding_id": result["project_binding_id"],
        "genesis_state": result["committed_state"],
    }
