"""PR #90 Round 6 (``ADOPT_P90_R6_REAL_AGENT_ORIGINAL_RUN_AND_FINAL_PROTOCOL``, comment
5714630885), corrected per Structural Advisor interim finding P90-R6-IF1 (comment
5715107317): decisive proof that the ``MANOSUBE_PRESENT`` condition of the two-task
real-Agent corpus (``examples/comparative_benchmark/real_agent_corpus/TASK_CORPUS.md``) runs
end-to-end through this repository's own real Difference -> Authority -> Change -> Observation
-> Evidence -> Reflow production route, to a real ``CLOSED`` outcome, driven by a real Agent
action -- resolved and verified through a real, machine-verifiable
:mod:`tests.comparative_benchmark.agent_execution_receipt`, never a Python callback this
test suite invokes and self-labels as "the real Agent action."

Each test replays the *real* receipt and *real* output bytes
(``examples/comparative_benchmark/real_agent_corpus/present/{task}_output.txt[.receipt.json]``)
that a genuine tool-using Agent action already produced, for real, outside this test suite
(``RAW_EVENTS.md``) -- it never recomputes the task's answer itself. Both the receipt and the
output bytes are read once from the tracked repository (read-only) and staged into a
disposable ``tmp_path`` for the actual lifecycle run, so a pytest rerun proves real receipt
verification and real lifecycle reconstruction without ever mutating the tracked corpus
artifacts (P90-R6-IF1's own reproducibility correction)."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.comparative_benchmark import (
    agent_execution_receipt as aer,
    real_agent_present_cycle as present,
)
from tests.fixtures import comparative_benchmark_real_agent as ra

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PRESENT_DIR = REPO_ROOT / "examples/comparative_benchmark/real_agent_corpus/present"

AGENT_IDENTITY = {
    "actor_kind": "claude_code_native_tool_using_agent",
    "session_ref": "https://claude.ai/code/session_0154miaUnGA543JWmVrxqamk",
}
TOOL_SURFACE = ["Bash", "Write"]
RESOURCE_BUDGET = {"max_turns": 1, "retries_allowed": 0}
TASK_INPUT = {
    "task_a": (
        "Compute the SHA-256 hex digest of the literal ASCII string "
        "MANOSUBE_PHASE21_ROUND6_TASK_A and write only that digest to the task's output file."
    ),
    "task_b": (
        "List every prime number p with 2 <= p <= 50, ascending, comma-separated, no spaces, "
        "and write only that line to the task's output file."
    ),
}

INSTANT = "2026-09-17T13:30:00Z"


def _stage_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, task_key: str
) -> dict[str, object]:
    """Read the real, published receipt and real, published output bytes for *task_key*
    (read-only, from the tracked repository) and stage a disposable replay world in
    *tmp_path*: a fresh ``NOT-READY`` before-state, and the real output bytes applied
    (copied verbatim, never recomputed) as the task's already-completed real change.
    Repoints :data:`ra.STATUS_PATH`/:data:`aer.ROOT` at the staged copies so the lifecycle
    reads and writes nothing outside *tmp_path*.

    Returns the real, unmodified receipt dict, loaded via :func:`aer.load_receipt` from a
    verbatim copy staged into *tmp_path* -- proving the real published receipt round-trips
    through the same loader production code would use, without ever touching the tracked
    repository file.
    """

    real_output_bytes = (CORPUS_PRESENT_DIR / f"{task_key}_output.txt").read_bytes()
    real_receipt_text = (CORPUS_PRESENT_DIR / f"{task_key}_output.txt.receipt.json").read_text(
        encoding="utf-8"
    )

    staged_present = tmp_path / "examples/comparative_benchmark/real_agent_corpus/present"
    staged_present.mkdir(parents=True, exist_ok=True)
    (staged_present / "STATUS.md").write_text(
        "task_a: NOT-READY\ntask_b: NOT-READY\n", encoding="utf-8"
    )
    (staged_present / f"{task_key}_output.txt.receipt.json").write_text(
        real_receipt_text, encoding="utf-8"
    )

    monkeypatch.setattr(ra, "STATUS_PATH", staged_present / "STATUS.md")
    monkeypatch.setattr(aer, "ROOT", tmp_path)

    receipt_relative = (
        f"examples/comparative_benchmark/real_agent_corpus/present/"
        f"{task_key}_output.txt.receipt.json"
    )
    receipt = aer.load_receipt(receipt_relative)

    # The real Agent action's own already-completed real change, applied now (verbatim
    # bytes, never recomputed) -- mirrors the point in the real timeline where the real
    # Agent action itself happened, between Authority and the post-change Observation.
    (staged_present / f"{task_key}_output.txt").write_bytes(real_output_bytes)
    lines = (staged_present / "STATUS.md").read_text(encoding="utf-8").splitlines()
    new_lines = [
        f"{task_key}: READY" if line.startswith(f"{task_key}:") else line for line in lines
    ]
    (staged_present / "STATUS.md").write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return receipt


def test_task_a_present_condition_closes_through_the_real_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _stage_replay(tmp_path, monkeypatch, task_key="task_a")

    store = present.build_store(tmp_path)
    committed_state = present.initialize_genesis(store)
    assembly = present.begin_present_task(
        store, k=0, committed_state=committed_state, instant=INSTANT
    )

    outcome = present.resolve_present_task(
        store,
        k=0,
        committed_state=committed_state,
        assembly=assembly,
        receipt=receipt,
        expected_agent_identity=AGENT_IDENTITY,
        expected_task_input=TASK_INPUT["task_a"],
        expected_tool_surface=TOOL_SURFACE,
        expected_resource_budget=RESOURCE_BUDGET,
    )

    assert outcome["identity"]["final_terminal_status"] == "CLOSED"

    # reflow()'s own real commit only ever advances generic bookkeeping (lineage,
    # open_differences) -- domain content such as `code.claims` is never itself
    # written back into the committed State (`tests/long_running_proof/cycle.py`'s own
    # `committed_cycle_count` docstring already documents this precisely, which is why
    # that composer counts `lineage.identity_refs` growth rather than `code.claims`).
    # The decisive, real-route proof is the CLOSED terminal status asserted above, plus
    # this real lineage advance -- not a domain-content check this Kernel never claims.
    reconstructed = store.reconstruct(ra.PROJECT_ID)
    assert len(reconstructed["semantic_state"]["lineage"]["identity_refs"]) == 1


def test_task_b_present_condition_closes_through_the_real_route(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt = _stage_replay(tmp_path, monkeypatch, task_key="task_b")

    store = present.build_store(tmp_path)
    committed_state = present.initialize_genesis(store)
    assembly = present.begin_present_task(
        store, k=1, committed_state=committed_state, instant=INSTANT
    )

    outcome = present.resolve_present_task(
        store,
        k=1,
        committed_state=committed_state,
        assembly=assembly,
        receipt=receipt,
        expected_agent_identity=AGENT_IDENTITY,
        expected_task_input=TASK_INPUT["task_b"],
        expected_tool_surface=TOOL_SURFACE,
        expected_resource_budget=RESOURCE_BUDGET,
    )

    assert outcome["identity"]["final_terminal_status"] == "CLOSED"

    reconstructed = store.reconstruct(ra.PROJECT_ID)
    assert len(reconstructed["semantic_state"]["lineage"]["identity_refs"]) == 1


def test_present_lifecycle_refuses_a_receipt_built_for_a_different_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integration-level reinforcement of P90-R6-IF1's required negative controls: the real
    published ``task_b`` receipt cannot be resolved where ``task_a`` is expected -- the
    lifecycle itself refuses, not merely the unit-level verifier."""

    receipt = _stage_replay(tmp_path, monkeypatch, task_key="task_b")

    store = present.build_store(tmp_path)
    committed_state = present.initialize_genesis(store)
    assembly = present.begin_present_task(
        store, k=0, committed_state=committed_state, instant=INSTANT
    )

    with pytest.raises(aer.TaskInputMismatchError):
        present.resolve_present_task(
            store,
            k=0,
            committed_state=committed_state,
            assembly=assembly,
            receipt=receipt,
            expected_agent_identity=AGENT_IDENTITY,
            expected_task_input=TASK_INPUT["task_a"],
            expected_tool_surface=TOOL_SURFACE,
            expected_resource_budget=RESOURCE_BUDGET,
        )
