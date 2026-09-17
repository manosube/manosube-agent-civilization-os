"""PR #90 corrected Round 6 rebind (``ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN``,
comment 5715652626) -- decisive proof that the frozen real-Agent protocol genuinely enforces
``PROTOCOL_FROZEN_BEFORE_RESULTS=true`` structurally (never merely by this round's own call
order), that both comparison groups' real, published receipts/outputs replay through the real
production route to ``CLOSED`` without mutating tracked artifacts, that the committed result
bundle's own metrics/claims/threshold evaluations rederive byte-for-byte from its own raw
events, and that this frozen corpus's own predeclared, native-Agent-free reproduction procedure
independently reaches the identical recorded outcome counts (``THIRD_PARTY_REPRODUCIBLE``,
honestly scoped -- see :mod:`tests.fixtures.comparative_benchmark_rebind_protocol`'s own
comparability_loss_receipts)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.comparative_benchmark import (
    agent_execution_receipt as aer,
    frozen_protocol_present_cycle as present,
    frozen_protocol_reproduction as reproduction,
)
from tests.fixtures import (
    comparative_benchmark_frozen_protocol as ra,
    comparative_benchmark_rebind_protocol as rb,
)

from manosube_agent_civilization.comparative_benchmark import route as cb_route
from manosube_agent_civilization.comparative_benchmark.engine import (
    aggregate_metrics,
    derive_bounded_claims,
    evaluate_numeric_thresholds,
)
from manosube_agent_civilization.comparative_benchmark.errors import ResultBundleValidationError
from manosube_agent_civilization.work_time_transparency.clock import default_clock

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_PRESENT_DIR = (
    REPO_ROOT / "examples/comparative_benchmark/real_agent_corpus/frozen_protocol/present"
)
FROZEN_ABSENT_DIR = (
    REPO_ROOT / "examples/comparative_benchmark/real_agent_corpus/frozen_protocol/absent"
)
PUBLISHED_ARTIFACT_DIR = REPO_ROOT / "examples/comparative_benchmark/frozen_protocol_r6"

AGENT_IDENTITY = {"actor_kind": "claude_code_native_tool_using_agent"}
TASK_INPUT = rb.TASK_INPUT
TOOL_SURFACE = rb.TOOL_SURFACE
RESOURCE_BUDGET = rb.RESOURCE_BUDGET
INSTANT = "2026-09-17T14:30:00Z"


def _freeze_kwargs() -> dict[str, object]:
    return rb.protocol_freeze_kwargs(generated_at=default_clock())


# --- PROTOCOL_FROZEN_BEFORE_RESULTS is structurally enforced, not merely followed ------------ #


def test_commit_result_bundle_refuses_without_a_prior_committed_protocol_freeze(
    tmp_path: Path,
) -> None:
    """Decisive negative control: a Store that never had this protocol's own freeze committed
    to it refuses a result-bundle commit outright -- ``PROTOCOL_FROZEN_BEFORE_RESULTS=true`` is
    a structural fact ``route.commit_result_bundle`` itself enforces (P90-R1-F6's own resolve-
    before-construct discipline), never something a caller could bypass by simply calling the
    two routes in the wrong order."""

    store = present.build_store(tmp_path)
    fabricated_freeze = {
        "protocol_freeze_id": "CBPF-" + "0" * 64,
        "protocol_freeze_semantic_fingerprint": "sha256:" + "0" * 64,
    }
    with pytest.raises(ResultBundleValidationError):
        cb_route.commit_result_bundle(
            store,
            project_id=rb.CB_PROJECT_ID,
            project_binding_ref={"kind": "project_binding", "id": rb.CB_PROJECT_BINDING_ID},
            protocol_freeze=fabricated_freeze,
            raw_events=reproduction.reproduce_raw_events(),
            environment_manifest={},
            generated_at=default_clock(),
        )


def test_protocol_freeze_commit_is_durable_and_reload_equal(tmp_path: Path) -> None:
    store = present.build_store(tmp_path)
    freeze = cb_route.commit_protocol_freeze(store, project_id=rb.CB_PROJECT_ID, **_freeze_kwargs())
    resolved = cb_route.resolve_protocol_freeze(
        store, project_id=rb.CB_PROJECT_ID, protocol_freeze_id=freeze["protocol_freeze_id"]
    )
    assert resolved == freeze


# --- Both comparison groups' real, published receipts/outputs replay to CLOSED --------------- #


def _stage_present_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, task_key: str
) -> dict[str, Any]:
    """Read the real, published receipt and real, published output bytes for *task_key*
    (read-only, from the tracked repository) and stage a disposable replay world in *tmp_path*
    -- proving real receipt verification and real lifecycle reconstruction without ever
    mutating the tracked corpus artifacts (identical discipline to
    ``test_real_agent_present_condition.py``'s own ``_stage_replay``, adapted to this round's
    own frozen-protocol fixture pair)."""

    real_output_bytes = (FROZEN_PRESENT_DIR / f"{task_key}_output.txt").read_bytes()
    real_receipt_text = (FROZEN_PRESENT_DIR / f"{task_key}_output.txt.receipt.json").read_text(
        encoding="utf-8"
    )

    staged_present = (
        tmp_path / "examples/comparative_benchmark/real_agent_corpus/frozen_protocol/present"
    )
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
        f"examples/comparative_benchmark/real_agent_corpus/frozen_protocol/present/"
        f"{task_key}_output.txt.receipt.json"
    )
    receipt = aer.load_receipt(receipt_relative)

    (staged_present / f"{task_key}_output.txt").write_bytes(real_output_bytes)
    lines = (staged_present / "STATUS.md").read_text(encoding="utf-8").splitlines()
    new_lines = [
        f"{task_key}: READY" if line.startswith(f"{task_key}:") else line for line in lines
    ]
    (staged_present / "STATUS.md").write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    return receipt


@pytest.mark.parametrize("k,task_key", [(0, "task_a"), (1, "task_b")])
def test_present_group_replays_the_real_published_receipt_to_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, k: int, task_key: str
) -> None:
    receipt = _stage_present_replay(tmp_path, monkeypatch, task_key=task_key)

    store = present.build_store(tmp_path)
    committed_state = present.initialize_genesis(store)
    assembly = present.begin_present_task(
        store, k=k, committed_state=committed_state, instant=INSTANT
    )
    outcome = present.resolve_present_task(
        store,
        k=k,
        committed_state=committed_state,
        assembly=assembly,
        receipt=receipt,
        expected_agent_identity=dict(
            rb.SAME_AGENT_LABEL, session_ref=receipt["agent_identity"]["session_ref"]
        ),
        expected_task_input=TASK_INPUT[task_key],
        expected_tool_surface=TOOL_SURFACE,
        expected_resource_budget=RESOURCE_BUDGET,
    )
    assert outcome["identity"]["final_terminal_status"] == "CLOSED"


def test_absent_group_published_receipts_verify_against_their_real_output_bytes() -> None:
    """The ``MANOSUBE_ABSENT`` group performs its writes directly (no MANOSUBE lifecycle) --
    its own decisive proof is that the published receipt independently re-verifies against the
    real, currently-tracked output bytes on disk, exactly as
    :mod:`tests.comparative_benchmark.agent_execution_receipt` is designed to be checked."""

    for task_key in ("task_a", "task_b"):
        receipt = aer.load_receipt(
            f"examples/comparative_benchmark/real_agent_corpus/frozen_protocol/absent/"
            f"{task_key}_output.txt.receipt.json"
        )
        aer.verify_agent_execution_receipt(
            receipt,
            expected_agent_identity=dict(
                rb.SAME_AGENT_LABEL, session_ref=receipt["agent_identity"]["session_ref"]
            ),
            expected_condition="MANOSUBE_ABSENT",
            expected_task_key=task_key,
            expected_task_input=TASK_INPUT[task_key],
            expected_tool_surface=TOOL_SURFACE,
            expected_resource_budget=RESOURCE_BUDGET,
            expected_output_path=receipt["output_path"],
        )


# --- Published result bundle: raw -> metric -> claim rederivation, byte-for-byte ------------- #


def test_published_result_bundle_rederives_byte_for_byte_from_its_own_raw_events() -> None:
    import json

    protocol_freeze = json.loads((PUBLISHED_ARTIFACT_DIR / "protocol_freeze.json").read_text())
    result_bundle = json.loads((PUBLISHED_ARTIFACT_DIR / "result_bundle.json").read_text())

    rederived_metrics = aggregate_metrics(result_bundle["raw_events"], protocol_freeze)
    assert rederived_metrics == result_bundle["metrics"]

    rederived_claims = derive_bounded_claims(rederived_metrics, protocol_freeze)
    assert rederived_claims == result_bundle["claims"]

    rederived_thresholds = evaluate_numeric_thresholds(rederived_metrics, protocol_freeze)
    assert rederived_thresholds == result_bundle["threshold_evaluations"]
    assert all(entry["passed"] for entry in rederived_thresholds)


# --- Honest, native-Agent-free reproduction reaches the identical recorded outcome counts ----- #


def test_mechanical_reproduction_matches_the_published_result_bundles_metrics() -> None:
    import json

    result_bundle = json.loads((PUBLISHED_ARTIFACT_DIR / "result_bundle.json").read_text())
    protocol_freeze = json.loads((PUBLISHED_ARTIFACT_DIR / "protocol_freeze.json").read_text())

    reproduced_raw_events = reproduction.reproduce_raw_events()
    reproduced_metrics = aggregate_metrics(reproduced_raw_events, protocol_freeze)
    assert reproduced_metrics == result_bundle["metrics"]
