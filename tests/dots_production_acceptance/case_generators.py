"""WU2: materializes ``docs/validation/dots_production_acceptance/case-catalog.json``'s
fixed case/task definitions into concrete, runnable fixture objects.

Pure data transformation only -- no Kernel/Store call, no execution, no dots/GitHub
connection. Per ``WU2_PLAN.md``'s own implementation order (step 4) and verification
step 4 (a dry-run producing exactly the declared counts, no duplicate IDs).
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

DEFAULT_CASE_CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "validation"
    / "dots_production_acceptance"
    / "case-catalog.json"
)


class CaseGeneratorError(Exception):
    """Raised when case-catalog.json itself is malformed, or its own invariants (unique
    case/task IDs, declared counts) don't hold -- never silently patched over."""


@dataclass(frozen=True)
class FaultCaseFixture:
    case_id: str
    stimulus: str
    expected: str
    live_effect_scope: str
    oracle: str
    repetition_index: int  # 0-based; one fixture per repetition, per PROTOCOL.md Sec.5 Q2


@dataclass(frozen=True)
class ComparisonTaskFixture:
    task_id: str
    stratum: str
    stratum_index: int  # 0-based within the stratum (tasks_per_stratum entries)


def load_catalog(path: Path = DEFAULT_CASE_CATALOG_PATH) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaseGeneratorError(f"cannot load case catalog at {path}: {exc}") from exc


def generate_fault_case_fixtures(catalog: dict[str, Any] | None = None) -> list[FaultCaseFixture]:
    """Q2: each of the catalog's ``fault_cases``, repeated ``fault_repetitions`` times
    (a fresh environment per repetition, per PROTOCOL.md Sec.5 Q2) -- never deduplicated
    into fewer actual runs than the catalog declares."""

    catalog = catalog if catalog is not None else load_catalog()
    cases = catalog["fault_cases"]
    repetitions = catalog["fault_repetitions"]

    case_ids = [case["case_id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise CaseGeneratorError("duplicate case_id in case-catalog.json fault_cases")

    fixtures = [
        FaultCaseFixture(
            case_id=case["case_id"],
            stimulus=case["stimulus"],
            expected=case["expected"],
            live_effect_scope=case["live_effect_scope"],
            oracle=case["oracle"],
            repetition_index=rep,
        )
        for case in cases
        for rep in range(repetitions)
    ]
    expected_total = len(cases) * repetitions
    if len(fixtures) != expected_total:
        raise CaseGeneratorError(
            f"generated {len(fixtures)} fault-case fixtures, expected "
            f"{len(cases)} cases x {repetitions} repetitions = {expected_total}"
        )
    return fixtures


def generate_comparison_task_fixtures(catalog: dict[str, Any] | None = None) -> list[ComparisonTaskFixture]:
    """Q4: ``comparison.distinct_tasks`` total -- ``strata`` x ``tasks_per_stratum``,
    never ``strata`` x ``tasks_per_stratum`` x ``repetitions`` x ``conditions`` (that
    product is the *runs* count, computed separately by :func:`comparison_run_count`
    from these same task fixtures, per ``WU2_PLAN.md``'s own corrected arithmetic --
    this function returns tasks, not runs)."""

    catalog = catalog if catalog is not None else load_catalog()
    comparison = catalog["comparison"]
    strata = comparison["strata"]
    per_stratum = comparison["tasks_per_stratum"]
    expected_total = comparison["distinct_tasks"]

    fixtures = [
        ComparisonTaskFixture(task_id=f"TASK-{stratum}-{idx:02d}", stratum=stratum, stratum_index=idx)
        for stratum in strata
        for idx in range(per_stratum)
    ]

    task_ids = [fixture.task_id for fixture in fixtures]
    if len(task_ids) != len(set(task_ids)):
        raise CaseGeneratorError("duplicate task_id generated from case-catalog.json strata")
    if len(fixtures) != expected_total:
        raise CaseGeneratorError(
            f"generated {len(fixtures)} task fixtures, catalog declares "
            f"distinct_tasks={expected_total} -- catalog and generator have drifted"
        )
    return fixtures


def comparison_run_count(catalog: dict[str, Any] | None = None) -> int:
    """The actual Q4 run count: ``distinct_tasks x repetitions x len(conditions)`` --
    computed here once, from the catalog's own declared fields, so no caller re-derives
    (and risks re-breaking) the 240 = 40 x 3 x 2 arithmetic WU1-SR1 corrected."""

    catalog = catalog if catalog is not None else load_catalog()
    comparison = catalog["comparison"]
    count = comparison["distinct_tasks"] * comparison["repetitions"] * len(comparison["conditions"])
    if count != comparison["runs"]:
        raise CaseGeneratorError(
            f"computed run count {count} does not match catalog's declared runs={comparison['runs']}"
        )
    return count
