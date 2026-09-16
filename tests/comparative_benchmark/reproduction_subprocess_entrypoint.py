"""Phase 21 Comparative Benchmark -- P90-R1-F3's own genuinely separate reproduction-execution
child-process entrypoint.

Run as ``python -m tests.comparative_benchmark.reproduction_subprocess_entrypoint`` by
:func:`tests.comparative_benchmark.orchestrator._run_reproduction_subprocess`, in a real,
distinct OS process from the parent that produced the original ``result_bundle`` -- never
imported and called in-process, and never sharing that parent's own ``os.getpid()``. Builds its
own fresh Store and fresh genesis/Project Binding, drives the identical comparison-group
mechanism the parent's own original run used
(:func:`tests.comparative_benchmark.orchestrator.run_one_full_pass`), and prints exactly one
JSON payload to stdout: the reproduced raw events, and this child's own real ``os.getpid()`` and
real environment manifest -- both read from *inside this process itself*, never forwarded or
guessed by the parent. This is what makes ``engine.build_reproduction_receipt``'s own
same-process-refusal check (P90-R1-F3: a reproduction receipt cannot be built if
``reproduction_process_id`` equals the original bundle's own ``generation_process_id``) check
something real: this child process necessarily has a different ``os.getpid()`` than its parent.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sys
import tempfile
from typing import Any


def _environment_manifest() -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }


def main() -> None:
    # Deferred imports: this module must be importable (for its own ``-m`` invocation) with
    # only the repository root on ``sys.path`` -- exactly the state a genuinely fresh
    # subprocess launched with ``cwd=REPO_ROOT`` starts from.
    from tests.comparative_benchmark.orchestrator import run_one_full_pass
    from tests.long_running_proof import cycle

    tmp_root = Path(tempfile.mkdtemp(prefix="cb21-reproduction-"))
    store = cycle.build_store(tmp_root / "reproducer")
    bind_result = cycle.bind_genesis(store)
    reproduced_raw_events = run_one_full_pass(
        store,
        project_binding_id=bind_result["project_binding_id"],
        run_label="independent-reproducer",
        tmp_path=tmp_root / "reproducer-absent-groups",
    )
    payload = {
        "reproduced_raw_events": reproduced_raw_events,
        "reproduction_process_id": os.getpid(),
        "reproduction_environment_manifest": _environment_manifest(),
    }
    print(json.dumps(payload))  # noqa: T201 -- this process's own real return channel


if __name__ == "__main__":
    main()
