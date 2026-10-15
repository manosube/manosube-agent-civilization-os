"""Contract tests for case_generators.py against the real case-catalog.json.

Tracks #116 (WU2). Pure data-shape checks, per WU2_PLAN.md's own verification step 4 --
no Kernel/Store call, no execution.
"""

from __future__ import annotations

from copy import deepcopy

import pytest
from tests.dots_production_acceptance import case_generators as cg


@pytest.fixture
def catalog() -> dict:
    return cg.load_catalog()


def test_fault_case_fixtures_match_catalog_counts_with_no_duplicates(catalog: dict) -> None:
    fixtures = cg.generate_fault_case_fixtures(catalog)

    assert len(fixtures) == len(catalog["fault_cases"]) * catalog["fault_repetitions"]
    assert len(fixtures) == 72, "case-catalog.json currently declares 24 fault cases x 3 repetitions"

    by_case = {}
    for fixture in fixtures:
        by_case.setdefault(fixture.case_id, set()).add(fixture.repetition_index)
    assert all(reps == {0, 1, 2} for reps in by_case.values()), (
        "every case_id must have exactly repetition indices 0, 1, 2"
    )


def test_comparison_task_fixtures_match_catalog_counts_with_no_duplicates(catalog: dict) -> None:
    fixtures = cg.generate_comparison_task_fixtures(catalog)

    assert len(fixtures) == 40, "case-catalog.json currently declares 8 strata x 5 tasks_per_stratum"
    task_ids = [fixture.task_id for fixture in fixtures]
    assert len(task_ids) == len(set(task_ids))

    by_stratum: dict[str, int] = {}
    for fixture in fixtures:
        by_stratum[fixture.stratum] = by_stratum.get(fixture.stratum, 0) + 1
    assert set(by_stratum) == set(catalog["comparison"]["strata"])
    assert all(count == catalog["comparison"]["tasks_per_stratum"] for count in by_stratum.values())


def test_comparison_run_count_is_240_not_a_separately_materialized_320(catalog: dict) -> None:
    # The exact arithmetic error WU1-SR1 corrected: 8 strata x 5 tasks = 40 distinct
    # tasks; 240 runs = 40 x 3 repetitions x 2 conditions -- never 40 x 8 = 320.
    assert cg.comparison_run_count(catalog) == 240
    assert cg.comparison_run_count(catalog) == catalog["comparison"]["runs"]


def test_duplicate_case_id_is_refused() -> None:
    catalog = cg.load_catalog()
    broken = deepcopy(catalog)
    broken["fault_cases"][1]["case_id"] = broken["fault_cases"][0]["case_id"]

    with pytest.raises(cg.CaseGeneratorError, match="duplicate case_id"):
        cg.generate_fault_case_fixtures(broken)


def test_catalog_run_count_drift_is_refused_not_silently_recomputed() -> None:
    catalog = cg.load_catalog()
    broken = deepcopy(catalog)
    broken["comparison"]["runs"] = 999

    with pytest.raises(cg.CaseGeneratorError, match="does not match catalog's declared runs"):
        cg.comparison_run_count(broken)


def test_missing_catalog_file_is_refused(tmp_path) -> None:
    with pytest.raises(cg.CaseGeneratorError, match="cannot load case catalog"):
        cg.load_catalog(tmp_path / "does-not-exist.json")
