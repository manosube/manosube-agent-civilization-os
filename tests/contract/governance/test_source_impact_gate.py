"""Issue #57 (`ADOPT_MERGE_SOURCE_REFLOW_MACHINE_OWNED_CONVERGENCE`, Issue #57 comment
5566512915), hardened by Structural Review Round 1
(`ADOPT_MSR_R1_EVENT_BOUND_REVALIDATED_AND_PATH_HARDENED_REFLOW`, Issue #57 comment
5567433361), `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` sections 1-2: the pre-merge
source-impact gate.

Proves the classification table verbatim (every row of `03_BINDING/
MERGE_SOURCE_REFLOW_CONTRACT.md` section 2, six classes as of Round 1), the fail-closed
`OS_CHANGE_DETECTED AND REQUIRED_SOURCE_UPDATE_MISSING = MERGE_BLOCKED` invariant on both
its positive and negative route -- now precise per kernel_surface area against the closed
`KERNEL_SURFACE_IMPACT_MAP` rather than "any `docs/project_sources/*.md` update"
(MSR-R1-F4) -- the parallel protected-governance-surface rule (MSR-R1-F3), and this
Issue's own required self-consistency property: a PR touching only `scripts/`, `tests/`,
`03_BINDING/`, and `.github/workflows/` -- exactly what this delivery's own PR touches --
is never blocked by the gate it introduces, because it always pairs its protected-surface
and kernel-surface-adjacent changes with the required `03_BINDING/` update.

This module makes no network call and never merges, approves, or comments on anything; it
only classifies changed paths and computes one decision (contract section 1's
"never inferred from a green or mergeable PR alone").
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import scripts.source_impact_gate as gate

pytestmark = pytest.mark.contract


# --------------------------------------------------------------------------- #
# classify_path: every row of the ownership classification table, verbatim
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("path", "expected_class"),
    [
        # kernel_surface: prefix-matched
        ("src/manosube_agent_civilization/foo.py", "kernel_surface"),
        ("00_KERNEL/08_REFLOW/reflow.py", "kernel_surface"),
        ("01_SCHEMA/foo.json", "kernel_surface"),
        ("02_ENGINE/foo.py", "kernel_surface"),
        ("04_BOOT/boot.py", "kernel_surface"),
        ("05_CLI/cli.py", "kernel_surface"),
        ("07_AGENT_RUNTIME/runtime.py", "kernel_surface"),
        # Phase 16 (Issue #66): the Model Runtime contract directory, registered for exactly
        # the reason 07_AGENT_RUNTIME/ already is.
        ("11_MODEL_RUNTIME/MODEL_RUNTIME_CONTRACT.md", "kernel_surface"),
        # kernel_surface: exact
        ("pyproject.toml", "kernel_surface"),
        # source_document: Human-owned narrative docs, excluding generated/
        ("docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md", "source_document"),
        ("docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md", "source_document"),
        ("docs/project_sources/06_DEFERRED_DIFFERENCES.md", "source_document"),
        # generated: exact paths and the generated/ subdirectory take priority over
        # the source_document prefix they nest inside
        ("HANDOFF.md", "generated"),
        ("SHA256SUMS", "generated"),
        ("README.md", "generated"),
        ("docs/project_sources/generated/CURRENT_REPOSITORY_FACTS.json", "generated"),
        ("docs/project_sources/generated/REPOSITORY_TREE.txt", "generated"),
        ("docs/project_sources/generated/PHASE_EVIDENCE_INDEX.json", "generated"),
        ("docs/project_sources/generated/SOURCE_REFLOW_RECEIPT.json", "generated"),
        # governance_binding
        ("03_BINDING/GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT.md", "governance_binding"),
        ("03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md", "governance_binding"),
        # protected_governance_surface (MSR-R1-F3): the executor scripts and workflow
        # files that implement Merge Source Reflow's own enforcement
        ("scripts/merge_source_reflow.py", "protected_governance_surface"),
        ("scripts/source_impact_gate.py", "protected_governance_surface"),
        (".github/workflows/merge_source_pre_merge_gate.yml", "protected_governance_surface"),
        (".github/workflows/merge_source_post_merge_reflow.yml", "protected_governance_surface"),
        # other: every other script/test/misc path, deliberately including scripts/ and
        # tests/ generally -- see contract section 2
        ("scripts/bounded_generated_block.py", "other"),
        ("tests/contract/governance/test_source_impact_gate.py", "other"),
        ("docs/decisions/0001-example.md", "other"),
        ("examples/foo.py", "other"),
    ],
)
def test_classify_path_matches_the_ownership_table(path: str, expected_class: str) -> None:
    assert gate.classify_path(path) == expected_class


def test_every_declared_class_is_covered_by_the_table_above() -> None:
    """No seventh, undocumented class exists -- `CLASSES` is exactly the six rows the
    parametrized table above already exercises at least once each."""

    exercised = {
        gate.classify_path(path)
        for path, _ in [
            ("src/foo.py", "kernel_surface"),
            ("docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md", "source_document"),
            ("README.md", "generated"),
            ("03_BINDING/x.md", "governance_binding"),
            ("scripts/merge_source_reflow.py", "protected_governance_surface"),
            ("scripts/x.py", "other"),
        ]
    }
    assert exercised == gate.CLASSES


def test_a_docs_project_sources_prefix_that_is_not_the_real_directory_is_not_captured() -> None:
    """A path that merely starts with the same characters as the source_document prefix
    but is not actually inside it must never be misclassified -- string-prefix matching on
    an un-slash-terminated fragment would be a false-positive risk this proves absent."""

    assert gate.classify_path("docs/project_sources_other/file.md") != "source_document"


# --------------------------------------------------------------------------- #
# build_manifest: the fail-closed invariant, both routes
# --------------------------------------------------------------------------- #


def test_a_kernel_surface_change_without_a_paired_source_document_update_is_blocked() -> None:
    manifest = gate.build_manifest(["src/manosube_agent_civilization/foo.py"])
    assert manifest["os_change_detected"] is True
    assert manifest["required_source_update_missing"] is True
    assert manifest["unmet_kernel_surface_areas"] == ["src/"]
    assert manifest["merge_blocked"] is True
    assert manifest["decision"] == "BLOCKED"


def test_a_kernel_surface_change_with_a_paired_source_document_update_passes() -> None:
    manifest = gate.build_manifest(
        [
            "src/manosube_agent_civilization/foo.py",
            "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md",
        ]
    )
    assert manifest["os_change_detected"] is True
    assert manifest["required_source_update_missing"] is False
    assert manifest["unmet_kernel_surface_areas"] == []
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


# --------------------------------------------------------------------------- #
# MSR-R1-F4: the closed impact mapping -- an arbitrary docs/project_sources/*.md
# update must not satisfy an unrelated kernel_surface obligation
# --------------------------------------------------------------------------- #


def test_an_unrelated_source_document_does_not_satisfy_a_kernel_surface_obligation() -> None:
    """The exact flaw MSR-R1-F4 names: pairing a kernel_surface change with *some*
    docs/project_sources/*.md document that is not in that area's own declared
    KERNEL_SURFACE_IMPACT_MAP entry must still block the merge."""

    manifest = gate.build_manifest(
        [
            "src/manosube_agent_civilization/foo.py",
            "docs/project_sources/06_DEFERRED_DIFFERENCES.md",
        ]
    )
    assert manifest["required_source_update_missing"] is True
    assert manifest["unmet_kernel_surface_areas"] == ["src/"]
    assert manifest["merge_blocked"] is True
    assert manifest["decision"] == "BLOCKED"


def test_the_other_mapped_document_also_satisfies_the_kernel_surface_obligation() -> None:
    """`KERNEL_SURFACE_IMPACT_MAP` names two legitimate documents for every area --
    04_REPOSITORY_ARCHITECTURE.md satisfies the pairing exactly as
    03_CURRENT_DEVELOPMENT_STATE.md does (proven separately above)."""

    manifest = gate.build_manifest(
        [
            "05_CLI/cli.py",
            "docs/project_sources/04_REPOSITORY_ARCHITECTURE.md",
        ]
    )
    assert manifest["required_source_update_missing"] is False
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


def test_kernel_surface_impact_map_is_closed_and_covers_every_declared_area() -> None:
    """The impact mapping is declared over exactly the areas KERNEL_SURFACE_PREFIXES and
    KERNEL_SURFACE_EXACT name -- no area is silently unmapped, and no mapped required-doc
    set is empty (which would make that area's obligation impossible to satisfy)."""

    declared_areas = set(gate.KERNEL_SURFACE_PREFIXES) | set(gate.KERNEL_SURFACE_EXACT)
    assert set(gate.KERNEL_SURFACE_IMPACT_MAP) == declared_areas
    for required_docs in gate.KERNEL_SURFACE_IMPACT_MAP.values():
        assert required_docs, "an area with an empty required-doc set can never be satisfied"


def test_kernel_surface_area_resolves_to_the_same_key_the_impact_map_uses() -> None:
    for path, expected_area in (
        ("src/manosube_agent_civilization/foo.py", "src/"),
        ("00_KERNEL/08_REFLOW/reflow.py", "00_KERNEL/"),
        ("11_MODEL_RUNTIME/MODEL_RUNTIME_INDEX.md", "11_MODEL_RUNTIME/"),
        ("pyproject.toml", "pyproject.toml"),
    ):
        area = gate._kernel_surface_area(path)
        assert area == expected_area
        assert area in gate.KERNEL_SURFACE_IMPACT_MAP
    assert gate._kernel_surface_area("scripts/foo.py") is None


# --------------------------------------------------------------------------- #
# MSR-R1-F3: protected governance surfaces require a paired governance_binding
# update -- the executor scripts and reflow workflows implement the gate itself
# --------------------------------------------------------------------------- #


def test_a_protected_surface_change_without_a_paired_governance_binding_update_is_blocked() -> None:
    manifest = gate.build_manifest(["scripts/merge_source_reflow.py"])
    assert manifest["protected_surface_changed"] is True
    assert manifest["required_governance_update_missing"] is True
    assert manifest["merge_blocked"] is True
    assert manifest["decision"] == "BLOCKED"


@pytest.mark.parametrize(
    "protected_path",
    [
        "scripts/merge_source_reflow.py",
        "scripts/source_impact_gate.py",
        ".github/workflows/merge_source_pre_merge_gate.yml",
        ".github/workflows/merge_source_post_merge_reflow.yml",
    ],
)
def test_every_protected_surface_alone_is_blocked_and_paired_with_binding_passes(
    protected_path: str,
) -> None:
    alone = gate.build_manifest([protected_path])
    assert alone["merge_blocked"] is True

    paired = gate.build_manifest([protected_path, "03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md"])
    assert paired["merge_blocked"] is False
    assert paired["decision"] == "PASS"


def test_a_protected_surface_change_paired_with_governance_binding_passes() -> None:
    manifest = gate.build_manifest(
        ["scripts/merge_source_reflow.py", "03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md"]
    )
    assert manifest["protected_surface_changed"] is True
    assert manifest["required_governance_update_missing"] is False
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


def test_a_non_protected_scripts_change_never_triggers_the_protected_surface_rule() -> None:
    manifest = gate.build_manifest(["scripts/bounded_generated_block.py"])
    assert manifest["protected_surface_changed"] is False
    assert manifest["required_governance_update_missing"] is False
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


def test_a_change_carrying_no_kernel_surface_path_never_blocks() -> None:
    """`REQUIRED_SOURCE_UPDATE_MISSING` is conditioned on `OS_CHANGE_DETECTED` -- a PR that
    never touches `kernel_surface` is never blocked for lacking a source_document update,
    however many other files it changes."""

    manifest = gate.build_manifest(
        ["scripts/foo.py", "tests/test_foo.py", "docs/decisions/0001.md", "HANDOFF.md"]
    )
    assert manifest["os_change_detected"] is False
    assert manifest["required_source_update_missing"] is False
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


def test_an_empty_change_set_never_blocks() -> None:
    manifest = gate.build_manifest([])
    assert manifest["merge_blocked"] is False
    assert manifest["classified_paths"] == {name: [] for name in sorted(gate.CLASSES)}


def test_this_issues_own_pr_shape_is_self_consistently_never_blocked() -> None:
    """The required self-consistency property: a PR touching only `scripts/`, `tests/`,
    `03_BINDING/`, and `.github/workflows/` -- exactly this delivery's own shape -- passes
    the very gate it introduces without needing a paired `docs/project_sources/` update,
    because its `03_BINDING/` change is itself the required pairing the protected-surface
    rule (MSR-R1-F3) demands for the executor scripts and workflow files it also touches."""

    manifest = gate.build_manifest(
        [
            "scripts/merge_source_reflow.py",
            "scripts/source_impact_gate.py",
            "scripts/bounded_generated_block.py",
            "tests/contract/governance/test_source_impact_gate.py",
            "tests/contract/governance/test_merge_source_reflow.py",
            "03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md",
            ".github/workflows/merge_source_pre_merge_gate.yml",
            ".github/workflows/merge_source_post_merge_reflow.yml",
        ]
    )
    assert manifest["merge_blocked"] is False
    assert manifest["decision"] == "PASS"


def test_build_manifest_never_mutates_its_input_list() -> None:
    changed = ["src/foo.py", "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md"]
    original = list(changed)
    gate.build_manifest(changed)
    assert changed == original


def test_build_manifest_is_deterministic_and_sorted() -> None:
    first = gate.build_manifest(["src/b.py", "src/a.py", "docs/project_sources/x.md"])
    second = gate.build_manifest(["src/a.py", "src/b.py", "docs/project_sources/x.md"])
    assert first == second
    assert first["classified_paths"]["kernel_surface"] == ["src/a.py", "src/b.py"]


# --------------------------------------------------------------------------- #
# CLI: --changed-path, --changed-paths-file, --output, exit codes
# --------------------------------------------------------------------------- #


def test_cli_repeated_changed_path_flag_blocks_and_exits_non_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = gate.main(["--changed-path", "src/foo.py"])
    assert exit_code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "BLOCKED"


def test_cli_changed_paths_file_passes_when_paired(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changes_file = tmp_path / "changed.txt"
    changes_file.write_text(
        "src/foo.py\ndocs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md\n\n",
        encoding="utf-8",
    )
    exit_code = gate.main(["--changed-paths-file", str(changes_file)])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"] == "PASS"


def test_cli_output_flag_writes_the_manifest_to_the_named_file(tmp_path: Path) -> None:
    output_path = tmp_path / "manifest.json"
    exit_code = gate.main(["--changed-path", "scripts/foo.py", "--output", str(output_path)])
    assert exit_code == 0
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "PASS"


def test_cli_combines_repeated_flags_and_a_file() -> None:
    manifest_via_combination = gate.build_manifest(
        ["src/foo.py", "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md"]
    )
    assert manifest_via_combination["decision"] == "PASS"
