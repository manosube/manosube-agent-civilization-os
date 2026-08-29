"""Fixtures shared by state engine tests."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "01_SCHEMA"


def initial_state() -> dict[str, Any]:
    cases = json.loads(
        (ROOT / "tests/contract/fixtures/schema/valid/cases.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(case for case in cases if case["name"] == "initial_state_revision_zero")
    return deepcopy(case["instance"])
