"""Issue #96 (`ADOPT_V101_PUBLIC_RELEASE_SURFACE_CONSISTENCY_D1_D5`, SHUKOU adoption comment
5772769121): after v1.0.0 was Human-accepted and publicly released (Issue #92), the
public-facing surfaces -- package/release identity, maturity classifier, security support
window, the ten previously-tolerated known test failures, and citation metadata -- had never
been synced to reflect that acceptance. This file proves each of the five adopted decisions
(D1-D5) actually landed on disk, mechanically, rather than trusting a restated summary.

This is supporting governance/release-surface verification, not a Kernel element -- see
``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md``. Nothing here evaluates Authority,
Evidence, Difference, or Reflow.
"""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]

_EXPECTED_VERSION = "1.0.1"
_EXPECTED_CLASSIFIER = "Development Status :: 4 - Beta"

# --------------------------------------------------------------------------- #
# D1: release/package version identity -> 1.0.1 (the v1.0.0 tag is immutable)
# --------------------------------------------------------------------------- #


def test_pyproject_version_is_1_0_1() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == _EXPECTED_VERSION


def test_package_dunder_version_is_1_0_1() -> None:
    """Reads the source file directly rather than importing the package: an import
    depends on the package being installed (editable or otherwise), which is a real
    project-environment setup step, not something this focused test should assume --
    a plain `git clone` plus `python -m pytest` on this one file must still pass."""

    source = (ROOT / "src" / "manosube_agent_civilization" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', source, flags=re.MULTILINE)
    assert match is not None, "src/manosube_agent_civilization/__init__.py has no __version__"
    assert match.group(1) == _EXPECTED_VERSION


def test_no_stale_pre_release_version_string_remains_in_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "0.1.0.dev0" not in text


# --------------------------------------------------------------------------- #
# D2: maturity classifier -> Development Status :: 4 - Beta
# --------------------------------------------------------------------------- #


def test_pyproject_classifier_is_beta() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    classifiers = data["project"]["classifiers"]
    assert _EXPECTED_CLASSIFIER in classifiers
    assert not any("Pre-Alpha" in c or "Production/Stable" in c for c in classifiers)


# --------------------------------------------------------------------------- #
# D3: fixed latest-1.x security support window, with recorded decision lineage
# --------------------------------------------------------------------------- #


def test_security_md_declares_fixed_1x_support_window() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "## 18. Supported Versions" in text
    assert "Latest published 1.x release" in text
    assert "Supported" in text
    assert "Pre-1.0 releases" in text
    assert "Unsupported" in text


def test_security_md_decision_lineage_cites_issue_96_adoption() -> None:
    text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "### 18.1 Security decision lineage" in text
    lineage_start = text.index("### 18.1 Security decision lineage")
    lineage_end = text.index("## 19. Reporting a Vulnerability")
    lineage_block = text[lineage_start:lineage_end]
    assert "HUMAN_SECURITY_APPROVAL=manosube (OWNER), Issue #96 comment 5772769121" in (
        lineage_block
    )
    assert "DECISION_LINEAGE_GOVERNING_ISSUE=#96" in lineage_block
    assert "DECISION_LINEAGE_ADOPTION_COMMENT=5772769121" in lineage_block
    assert "FAIL_CLOSED_WEAKENED=false" in lineage_block
    assert "HUMAN_ONLY_AUTHORITY_DELEGATED=false" in lineage_block


# --------------------------------------------------------------------------- #
# D4: the 10 previously-tolerated known failures are genuinely fixed, not hidden
# --------------------------------------------------------------------------- #


def test_source_freshness_drift_test_file_has_no_xfail_or_skip_markers() -> None:
    """D4 requires the 10 known failures to be fixed for real -- never hidden behind
    ``xfail``/``skip``. Decisive over a passing count alone: a suite that merely wraps
    the same failures in ``xfail`` would still report a green run."""

    text = (
        ROOT / "tests" / "contract" / "governance" / "test_source_freshness_drift_detection.py"
    ).read_text(encoding="utf-8")
    assert "xfail" not in text
    assert "@pytest.mark.skip" not in text
    assert "pytest.skip(" not in text


def test_current_development_state_v101_section_documents_the_d4_fix_taxonomy() -> None:
    text = (ROOT / "docs" / "project_sources" / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(
        encoding="utf-8"
    )
    assert "# 79. v1.0.1 public release surface consistency" in text
    section_start = text.index("# 79. v1.0.1 public release surface consistency")
    assert "ADOPT_V101_PUBLIC_RELEASE_SURFACE_CONSISTENCY_D1_D5" in text[section_start:]


# --------------------------------------------------------------------------- #
# D5: CITATION.cff with only verified fields -- no fabricated ORCID/DOI
# --------------------------------------------------------------------------- #


def _citation_lines() -> list[str]:
    return (ROOT / "CITATION.cff").read_text(encoding="utf-8").splitlines()


def test_citation_cff_exists_and_has_required_top_level_fields() -> None:
    lines = _citation_lines()
    joined = "\n".join(lines)
    assert re.search(r"^cff-version:\s*1\.2\.0\s*$", joined, flags=re.MULTILINE)
    assert re.search(r'^title:\s*"MANOSUBE Agent Civilization OS"\s*$', joined, flags=re.MULTILINE)
    assert re.search(r"^type:\s*software\s*$", joined, flags=re.MULTILINE)
    assert re.search(rf'^version:\s*"{_EXPECTED_VERSION}"\s*$', joined, flags=re.MULTILINE)
    assert re.search(r"^license:\s*Apache-2\.0\s*$", joined, flags=re.MULTILINE)


def test_citation_cff_author_is_shukou_with_bare_name_field() -> None:
    joined = "\n".join(_citation_lines())
    assert re.search(r'^authors:\n\s*-\s*name:\s*"SHUKOU"\s*$', joined, flags=re.MULTILINE)


def test_citation_cff_contains_no_fabricated_identity_fields() -> None:
    """D5 explicitly forbids fabricating unverifiable fields: no ORCID, DOI, affiliation,
    or contact email may appear anywhere in the file."""

    text = (ROOT / "CITATION.cff").read_text(encoding="utf-8").lower()
    for forbidden in ("orcid", "doi:", "affiliation", "contact", "email"):
        assert forbidden not in text


def test_citation_cff_repository_url_matches_the_real_repository() -> None:
    joined = "\n".join(_citation_lines())
    assert "https://github.com/manosube/manosube-agent-civilization-os" in joined


# --------------------------------------------------------------------------- #
# README / current-state / ledger final synchronization
# --------------------------------------------------------------------------- #


def test_readme_status_declares_v1_0_accepted_and_publicly_released() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PROJECT_STATUS=V1_0_0_ACCEPTED_AND_PUBLICLY_RELEASED" in text
    assert "V1_0_DECLARED=true" in text
    assert "V1_0_0_RELEASE_TAG=v1.0.0" in text


def test_readme_status_no_longer_claims_phase_22_in_progress() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    status_start = text.index("## Status")
    status_end = text.index("<!-- SOURCE_STATUS:GENERATED:BEGIN -->")
    human_status_prose = text[status_start:status_end]
    assert "PHASE_22_V1_0_ACCEPTANCE_IN_PROGRESS" not in human_status_prose
    assert "V1_0_DECLARED=false" not in human_status_prose


def test_current_development_state_records_v1_0_0_final_acceptance() -> None:
    text = (ROOT / "docs" / "project_sources" / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(
        encoding="utf-8"
    )
    assert "# 78. v1.0.0 final Human acceptance and public release receipt (Issue #92)" in text
    section_start = text.index(
        "# 78. v1.0.0 final Human acceptance and public release receipt (Issue #92)"
    )
    section = text[section_start : section_start + 4000]
    assert "RELEASE_TAG_TARGET_COMMIT=f384e6acc01cd3d7a1992e931faba94e36f523a3" in section
    assert "ISSUE_92_STATE=CLOSED" in section


def test_phase_acceptance_ledger_records_v1_0_0_final_acceptance_receipt() -> None:
    text = (ROOT / "docs" / "project_sources" / "05_PHASE_ACCEPTANCE_LEDGER.md").read_text(
        encoding="utf-8"
    )
    heading = "# 32. v1.0.0 final Human acceptance and public release receipt (Issue #92)"
    assert heading in text
    section_start = text.index(heading)
    section = text[section_start:]
    assert "GITHUB_RELEASE_ID=393492078" in section
    assert "RELEASE_TAG_TARGET_COMMIT=f384e6acc01cd3d7a1992e931faba94e36f523a3" in section
    assert "ISSUE_92_STATE=CLOSED" in section
    assert "ISSUE_92_STATE_REASON=COMPLETED" in section


def test_ledger_and_current_state_v1_0_0_receipts_agree_on_release_commit() -> None:
    """The release target commit recorded in the ledger's §32 and the current-state's §78
    must be the exact same SHA -- two independent copies of the same fact must not drift."""

    ledger = (ROOT / "docs" / "project_sources" / "05_PHASE_ACCEPTANCE_LEDGER.md").read_text(
        encoding="utf-8"
    )
    state = (ROOT / "docs" / "project_sources" / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(
        encoding="utf-8"
    )
    sha = "f384e6acc01cd3d7a1992e931faba94e36f523a3"
    assert f"RELEASE_TAG_TARGET_COMMIT={sha}" in ledger
    assert f"RELEASE_TAG_TARGET_COMMIT={sha}" in state
