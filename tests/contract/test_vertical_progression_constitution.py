from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.contract
def test_constitution_forbids_local_exhaustion_as_an_implicit_phase_gate() -> None:
    constitution = (ROOT / "00_KERNEL" / "KERNEL_CONSTITUTION.md").read_text(
        encoding="utf-8"
    )

    required = (
        "PHASE_LOCAL_TOTALITY\n≠\nPHASE_COMPLETION",
        "VERTICAL_ROUTE_EXTENSION\n>\nUNREQUIRED_LOCAL_HARDENING",
        "NEXT_OWNER_INPUT_PRODUCED",
        "DEFERRED_NON_CLAIMS",
        "ONE_FULL_NATURAL_CYCLE_IMPACT",
    )

    for token in required:
        assert token in constitution


@pytest.mark.contract
def test_delivery_protocol_has_bounded_hardening_classification() -> None:
    protocol = (ROOT / "00_KERNEL" / "KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md").read_text(
        encoding="utf-8"
    )

    for token in (
        "CURRENT_ROUTE_BLOCKER",
        "REQUIRED_PHASE_GATE",
        "DEFERRED_NON_CLAIM",
        "FOLLOW_ON_DIFFERENCE",
        "FUTURE_OWNER_OBLIGATION",
        "LOCAL_HARDENING_MAY_CONTINUE_WITHOUT_BOUND=false",
        "VERTICAL_ROUTE_EXTENSION_IS_THE_DEFAULT=true",
    ):
        assert token in protocol
