"""Issue #116 / WU2 shared Project Binding test world.

Deliberately self-contained -- the identical "each vertical's own fixture module builds
its own ``bound()`` from ``tests.fixtures.product_binding`` directly" discipline every
other ``tests/fixtures/*_world.py`` module already keeps (see
``tests/fixtures/work_time_transparency_world.py``'s own module docstring), never
importing another vertical's own fixture world.

Tracks #116. This fixture world is WU2 test-only infrastructure: it exists so
``tests/dots_production_acceptance/``'s contract tests can exercise the real canonical
Binding/Store routes end-to-end, never a parallel State/Authority owner of their own.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.fixtures.product_binding import bind_project_kwargs, genesis_records
from tests.state_helpers import SCHEMA_ROOT

from manosube_agent_civilization.binding import bind_project
from manosube_agent_civilization.store import FileStateStore


def bound(tmp_path: Path, *, subdir: str = "dots_production_acceptance") -> tuple[FileStateStore, dict[str, Any]]:
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
