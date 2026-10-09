"""Generated convergence must not depend on changing Human-authored snapshots."""

from pathlib import Path

from scripts.merge_source_reflow import apply_reflow, validate_reflow_candidate
from tests.contract.governance.test_merge_source_reflow import _inputs


def test_candidate_readback_detects_tampering(tmp_path: Path) -> None:
    inputs = _inputs()
    apply_reflow(tmp_path, inputs)
    assert validate_reflow_candidate(tmp_path, inputs)["convergence_proven"]
    generated = tmp_path / "docs/project_sources/generated/CURRENT_REPOSITORY_FACTS.json"
    generated.write_text("{}")
    report = validate_reflow_candidate(tmp_path, inputs)
    assert not report["convergence_proven"]
    assert "docs/project_sources/generated/CURRENT_REPOSITORY_FACTS.json" in report["mismatched_generated_paths"]
