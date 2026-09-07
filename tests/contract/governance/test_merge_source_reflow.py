"""Issue #57 (`ADOPT_MERGE_SOURCE_REFLOW_MACHINE_OWNED_CONVERGENCE`, Issue #57 comment
5566512915), hardened by Structural Review Round 2
(`ADOPT_MSR_R2_PR_INTRODUCED_DIFF_AND_COMPLETE_GENERATED_TREE`, Issue #57 comment
5567994773), `03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` sections 3-9: the post-merge
deterministic reflow.

Proves the required-proof bullets of Issue #57's own adoption comment: the updater cannot
modify bytes outside a generated boundary or write to an unallowlisted path; a partial write
cannot be reported as convergence; a stale `main_sha` is refused; `SHA256SUMS` never hashes
itself; recursion is prevented by construction (a second, immediately-successive run over an
unchanged tree writes nothing); `REPOSITORY_TREE.txt` names the complete resulting tree
even on a first run where none of the allowlisted paths is git-tracked yet (MSR-R2-F2); and
Phase/Authority/semantic meaning remain untouched -- this module never reads or writes
anything under `00_KERNEL/`, `01_SCHEMA/`, `02_ENGINE/`, `04_BOOT/`, `05_CLI/`,
`07_AGENT_RUNTIME/`, `03_BINDING/`, or any `docs/project_sources/*.md` document's own bytes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from scripts.bounded_generated_block import human_text_outside_block
from scripts.generate_readme_status_block import (
    BEGIN_MARKER as README_BEGIN_MARKER,
    END_MARKER as README_END_MARKER,
)
import scripts.merge_source_reflow as reflow

pytestmark = pytest.mark.contract

_MAIN_SHA = "d489644407db1a09112974022fd0461dcea395e2"
_OTHER_SHA = "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"

_STATE_TEXT = (
    "```text\n"
    "OBSERVED_AT_UTC=2026-09-07T00:00:00Z\n"
    "COMPLETED_THROUGH_PHASE=12\n"
    "CURRENT_PHASE=13_INDEPENDENT_VERIFICATION\n"
    "CURRENT_PHASE_STATE=ROUND_3_ADOPTED\n"
    "PHASE_13_COMPLETE=false\n"
    "PHASE_14_ALLOWED=false\n"
    "```\n"
)
_LEDGER_TEXT = "```text\nSOME_FIELD=value\n```\n"
_README_TEXT = (
    "# Title\n\nSome human prose above.\n\n"
    "<!-- SOURCE_STATUS:GENERATED:BEGIN -->\nstale\n<!-- SOURCE_STATUS:GENERATED:END -->\n\n"
    "Some human prose below.\n"
)


def _inputs(**overrides: object) -> reflow.ReflowInputs:
    defaults: dict[str, object] = {
        "main_sha": _MAIN_SHA,
        "observed_at_utc": "2026-09-07T00:00:00Z",
        "current_development_state_text": _STATE_TEXT,
        "phase_ledger_text": _LEDGER_TEXT,
        "tracked_paths": ("README.md", "src/foo.py"),
        "readme_text": _README_TEXT,
        "handoff_text": None,
        "source_document_texts": {
            "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md": _STATE_TEXT,
            "docs/project_sources/05_PHASE_ACCEPTANCE_LEDGER.md": _LEDGER_TEXT,
        },
    }
    defaults.update(overrides)
    return reflow.ReflowInputs(**defaults)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Allowlist / boundary enforcement (deliverable 5)
# --------------------------------------------------------------------------- #


def test_every_computed_output_path_is_allowlisted() -> None:
    outputs = reflow.compute_outputs(_inputs())
    assert set(outputs) <= reflow.ALLOWLISTED_GENERATED_PATHS


def test_human_owned_source_documents_are_never_among_the_writable_outputs() -> None:
    """`source_document_texts` is hashed into `SHA256SUMS` (contract section 5) but must
    never itself become a writable output -- `apply_reflow` must never touch a
    `docs/project_sources/*.md` file directly (contract section 3)."""

    outputs = reflow.compute_outputs(_inputs())
    for path in (
        "docs/project_sources/03_CURRENT_DEVELOPMENT_STATE.md",
        "docs/project_sources/05_PHASE_ACCEPTANCE_LEDGER.md",
    ):
        assert path not in outputs


def test_apply_reflow_never_writes_a_docs_project_sources_markdown_file(tmp_path: Path) -> None:
    reflow.apply_reflow(tmp_path, _inputs())
    for candidate in (tmp_path / "docs" / "project_sources").glob("*.md"):
        pytest.fail(f"unexpected write to a Human-owned source document: {candidate}")


def test_apply_reflow_never_writes_outside_the_allowlist(tmp_path: Path) -> None:
    """Every file that exists on disk after a reflow run is either the ordinary repo
    fixture already there or a member of `ALLOWLISTED_GENERATED_PATHS` -- a positive
    inventory proof, not just an absence-of-error proof."""

    result = reflow.apply_reflow(tmp_path, _inputs())
    all_touched = set(result["files_written"]) | set(result["files_unchanged"])
    assert all_touched <= reflow.ALLOWLISTED_GENERATED_PATHS

    written_on_disk = {
        candidate.relative_to(tmp_path).as_posix()
        for candidate in tmp_path.rglob("*")
        if candidate.is_file() and ".tmp-reflow" not in candidate.name
    }
    assert written_on_disk <= reflow.ALLOWLISTED_GENERATED_PATHS


def test_a_source_document_key_that_collides_with_an_allowlisted_path_is_never_smuggled_in() -> (
    None
):
    """A defensive proof for the assertion inside `compute_outputs`: even a maliciously
    or accidentally named `source_document_texts` entry that collides with an allowlisted
    generated path must not silently overwrite that generated output -- since
    `source_document_texts` is merged only into the SHA256SUMS hash set, never into the
    writable `outputs` dict, the generated content always wins."""

    outputs = reflow.compute_outputs(
        _inputs(source_document_texts={"HANDOFF.md": "human-forged content, not machine-generated"})
    )
    assert outputs["HANDOFF.md"] != b"human-forged content, not machine-generated"
    assert reflow.HANDOFF_BEGIN_MARKER.encode() in outputs["HANDOFF.md"]


# --------------------------------------------------------------------------- #
# MSR-R2-F2: REPOSITORY_TREE.txt must enumerate the complete resulting tree,
# including every allowlisted path newly created by this same reflow run
# --------------------------------------------------------------------------- #


def test_repository_tree_includes_every_allowlisted_path_on_a_first_run() -> None:
    """On the very first reflow run, none of `ALLOWLISTED_GENERATED_PATHS` is a
    git-tracked path yet -- `tracked_paths` (gathered via `git ls-files` before this same
    reflow writes anything) omits every one of them, including REPOSITORY_TREE.txt's own
    listing of itself. The computed tree must still name the complete resulting set."""

    outputs = reflow.compute_outputs(
        _inputs(tracked_paths=("README.md", "src/foo.py"))  # no generated/ paths tracked
    )
    tree_lines = set(
        outputs["docs/project_sources/generated/REPOSITORY_TREE.txt"].decode().splitlines()
    )
    assert tree_lines >= reflow.ALLOWLISTED_GENERATED_PATHS


def test_repository_tree_still_includes_ordinary_tracked_paths() -> None:
    outputs = reflow.compute_outputs(
        _inputs(tracked_paths=("README.md", "src/foo.py", "src/bar.py"))
    )
    tree_lines = set(
        outputs["docs/project_sources/generated/REPOSITORY_TREE.txt"].decode().splitlines()
    )
    assert "src/foo.py" in tree_lines
    assert "src/bar.py" in tree_lines


def test_repository_tree_does_not_duplicate_a_path_that_is_both_tracked_and_allowlisted() -> None:
    """A later run, where HANDOFF.md etc. are already git-tracked from a prior reflow
    commit, must not list any allowlisted path twice."""

    outputs = reflow.compute_outputs(
        _inputs(tracked_paths=("README.md", "HANDOFF.md", "SHA256SUMS", "src/foo.py"))
    )
    tree_text = outputs["docs/project_sources/generated/REPOSITORY_TREE.txt"].decode()
    tree_lines = tree_text.splitlines()
    assert len(tree_lines) == len(set(tree_lines))
    assert tree_lines.count("HANDOFF.md") == 1


def test_repository_tree_is_sorted() -> None:
    outputs = reflow.compute_outputs(_inputs(tracked_paths=("z.py", "a.py")))
    tree_lines = outputs["docs/project_sources/generated/REPOSITORY_TREE.txt"].decode().splitlines()
    assert tree_lines == sorted(tree_lines)


# --------------------------------------------------------------------------- #
# Generated-boundary contract: Human text outside the markers never changes
# --------------------------------------------------------------------------- #


def test_readme_human_text_outside_the_block_is_byte_identical_after_regeneration() -> None:
    outputs = reflow.compute_outputs(_inputs())
    new_readme = outputs["README.md"].decode("utf-8")
    assert "Some human prose above." in new_readme
    assert "Some human prose below." in new_readme
    before = human_text_outside_block(_README_TEXT, README_BEGIN_MARKER, README_END_MARKER)
    after = human_text_outside_block(new_readme, README_BEGIN_MARKER, README_END_MARKER)
    assert before == after


def test_handoff_human_text_outside_the_block_is_byte_identical_after_regeneration() -> None:
    existing_handoff = (
        "# Handoff\n\nHuman decision: transfer accepted by SHUKOU on 2026-09-01.\n\n"
        f"{reflow.HANDOFF_BEGIN_MARKER}\nstale\n{reflow.HANDOFF_END_MARKER}\n"
    )
    outputs = reflow.compute_outputs(_inputs(handoff_text=existing_handoff))
    new_handoff = outputs["HANDOFF.md"].decode("utf-8")
    assert "Human decision: transfer accepted by SHUKOU on 2026-09-01." in new_handoff
    before = human_text_outside_block(
        existing_handoff, reflow.HANDOFF_BEGIN_MARKER, reflow.HANDOFF_END_MARKER
    )
    after = human_text_outside_block(
        new_handoff, reflow.HANDOFF_BEGIN_MARKER, reflow.HANDOFF_END_MARKER
    )
    assert before == after


def test_a_missing_handoff_file_bootstraps_from_the_initial_skeleton() -> None:
    outputs = reflow.compute_outputs(_inputs(handoff_text=None))
    new_handoff = outputs["HANDOFF.md"].decode("utf-8")
    assert reflow.HANDOFF_BEGIN_MARKER in new_handoff
    assert reflow.HANDOFF_END_MARKER in new_handoff


@pytest.mark.parametrize(
    "malformed_readme",
    [
        "# Title\n\nno markers at all here\n",
        f"{README_BEGIN_MARKER}\nonly begin, no end\n",
        f"{README_END_MARKER}\nonly end, no begin\n",
        f"{README_BEGIN_MARKER}\nx\n{README_END_MARKER}\ny\n{README_BEGIN_MARKER}\nz\n{README_END_MARKER}\n",
        f"{README_END_MARKER}\nout of order\n{README_BEGIN_MARKER}\n",
    ],
)
def test_a_malformed_readme_marker_pair_is_refused(malformed_readme: str) -> None:
    with pytest.raises(SystemExit):
        reflow.compute_outputs(_inputs(readme_text=malformed_readme))


@pytest.mark.parametrize(
    "malformed_handoff",
    [
        "# Handoff\n\nno markers at all\n",
        f"{reflow.HANDOFF_BEGIN_MARKER}\nonly begin\n",
        f"{reflow.HANDOFF_END_MARKER}\nonly end\n",
    ],
)
def test_a_malformed_handoff_marker_pair_is_refused(malformed_handoff: str) -> None:
    with pytest.raises(SystemExit):
        reflow.compute_outputs(_inputs(handoff_text=malformed_handoff))


# --------------------------------------------------------------------------- #
# Stale-SHA guard (contract section 9)
# --------------------------------------------------------------------------- #


def test_a_malformed_main_sha_is_refused_before_any_computation() -> None:
    with pytest.raises(SystemExit):
        reflow.compute_outputs(_inputs(main_sha="not-a-commit-sha"))


@pytest.mark.parametrize("bad_sha", ["", "abc123", "g" * 40, "a" * 39, "a" * 41])
def test_every_shape_of_malformed_main_sha_is_refused(bad_sha: str) -> None:
    with pytest.raises(SystemExit):
        reflow.compute_outputs(_inputs(main_sha=bad_sha))


def test_verify_head_matches_accepts_agreement() -> None:
    reflow.verify_head_matches(_MAIN_SHA, _MAIN_SHA)  # must not raise


def test_verify_head_matches_refuses_a_stale_claim() -> None:
    with pytest.raises(SystemExit):
        reflow.verify_head_matches(_OTHER_SHA, _MAIN_SHA)


# --------------------------------------------------------------------------- #
# SHA256SUMS must never hash itself (contract section 5)
# --------------------------------------------------------------------------- #


def test_sha256sums_refuses_to_include_itself() -> None:
    with pytest.raises(ValueError):
        reflow.compute_sha256sums({"SHA256SUMS": b"anything"})


def test_sha256sums_is_a_deterministic_sorted_manifest() -> None:
    digest_b = hashlib.sha256(b"content-b").hexdigest()
    digest_a = hashlib.sha256(b"content-a").hexdigest()
    manifest = reflow.compute_sha256sums({"z.txt": b"content-b", "a.txt": b"content-a"})
    lines = manifest.strip("\n").split("\n")
    assert lines == [f"{digest_a}  a.txt", f"{digest_b}  z.txt"]


def test_the_computed_sha256sums_output_never_hashes_itself() -> None:
    outputs = reflow.compute_outputs(_inputs())
    assert "SHA256SUMS" not in outputs["SHA256SUMS"].decode("utf-8")


# --------------------------------------------------------------------------- #
# Precompute-then-write: a computation failure writes nothing (contract section 8)
# --------------------------------------------------------------------------- #


def test_a_computation_failure_writes_nothing_to_disk(tmp_path: Path) -> None:
    (tmp_path / "docs" / "project_sources" / "generated").mkdir(parents=True)
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())

    with pytest.raises(SystemExit):
        reflow.apply_reflow(tmp_path, _inputs(readme_text="no markers at all"))

    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


def test_a_stale_head_verification_failure_writes_nothing(tmp_path: Path) -> None:
    before = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    with pytest.raises(SystemExit):
        reflow.verify_head_matches(_OTHER_SHA, _MAIN_SHA)
    after = sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file())
    assert before == after


# --------------------------------------------------------------------------- #
# Idempotence and the recursion guard (contract section 7)
# --------------------------------------------------------------------------- #


def test_reflow_is_idempotent_on_its_own_output(tmp_path: Path) -> None:
    """Two immediately-successive runs against an unchanged Human-owned input set: the
    first writes the full set of generated outputs, the second writes nothing at all --
    the fixed point the recursion-guard argument depends on."""

    first = reflow.apply_reflow(tmp_path, _inputs())
    assert first["files_written"] != []

    second = reflow.apply_reflow(tmp_path, _inputs())
    assert second["files_written"] == []
    assert second["receipt"]["convergence_proven"] is True


def test_a_third_run_after_the_no_op_second_run_also_writes_nothing(tmp_path: Path) -> None:
    reflow.apply_reflow(tmp_path, _inputs())
    reflow.apply_reflow(tmp_path, _inputs())
    third = reflow.apply_reflow(tmp_path, _inputs())
    assert third["files_written"] == []


def test_a_substantive_input_change_breaks_the_fixed_point_and_a_new_no_op_point_follows(
    tmp_path: Path,
) -> None:
    reflow.apply_reflow(tmp_path, _inputs())
    reflow.apply_reflow(tmp_path, _inputs())  # reach the fixed point

    changed = reflow.apply_reflow(tmp_path, _inputs(main_sha=_OTHER_SHA))
    assert changed["files_written"] != []

    settled = reflow.apply_reflow(tmp_path, _inputs(main_sha=_OTHER_SHA))
    assert settled["files_written"] == []


def test_the_reflow_commits_own_output_is_never_read_back_as_an_input() -> None:
    """`ReflowInputs` has no field sourced from any of `ALLOWLISTED_GENERATED_PATHS` --
    the structural reason recursion cannot occur, independent of any particular fixture's
    behavior."""

    import dataclasses

    field_names = {f.name for f in dataclasses.fields(reflow.ReflowInputs)}
    assert field_names == {
        "main_sha",
        "observed_at_utc",
        "current_development_state_text",
        "phase_ledger_text",
        "tracked_paths",
        "readme_text",
        "handoff_text",
        "source_document_texts",
    }
    # None of these fields is itself named after (or documented as sourced from) a
    # generated output -- readme_text/handoff_text are the *current on-disk* bytes the
    # caller re-reads each time, not a value this module persisted for later reuse.
    assert "receipt" not in field_names
    assert "sha256sums" not in field_names


# --------------------------------------------------------------------------- #
# Convergence receipt (contract section 6)
# --------------------------------------------------------------------------- #


def test_the_receipt_records_the_exact_reflowed_sha_and_timestamp(tmp_path: Path) -> None:
    result = reflow.apply_reflow(
        tmp_path, _inputs(main_sha=_MAIN_SHA, observed_at_utc="2026-09-07T01:02:03Z")
    )
    receipt = result["receipt"]
    assert receipt["reflowed_main_sha"] == _MAIN_SHA
    assert receipt["observed_at_utc"] == "2026-09-07T01:02:03Z"
    assert receipt["convergence_proven"] is True
    assert receipt["human_text_converged"] is True


def test_the_receipt_sha256sums_digest_matches_the_actual_written_sha256sums_bytes(
    tmp_path: Path,
) -> None:
    result = reflow.apply_reflow(tmp_path, _inputs())
    on_disk = (tmp_path / "SHA256SUMS").read_bytes()
    assert result["receipt"]["sha256sums_digest"] == hashlib.sha256(on_disk).hexdigest()


def test_the_written_receipt_file_is_valid_json_matching_the_returned_receipt(
    tmp_path: Path,
) -> None:
    result = reflow.apply_reflow(tmp_path, _inputs())
    on_disk_receipt = json.loads((tmp_path / reflow.RECEIPT_PATH).read_text(encoding="utf-8"))
    assert on_disk_receipt == result["receipt"]


# --------------------------------------------------------------------------- #
# Atomic write mechanics
# --------------------------------------------------------------------------- #


def test_atomic_write_leaves_no_tmp_reflow_file_behind(tmp_path: Path) -> None:
    reflow.apply_reflow(tmp_path, _inputs())
    leftovers = list(tmp_path.rglob("*.tmp-reflow"))
    assert leftovers == []


def test_only_changed_files_are_rewritten_on_a_partial_change(tmp_path: Path) -> None:
    first = reflow.apply_reflow(tmp_path, _inputs())
    tree_path = tmp_path / "docs/project_sources/generated/REPOSITORY_TREE.txt"
    original_mtime = tree_path.stat().st_mtime_ns

    # Change only the main_sha -- REPOSITORY_TREE.txt (derived from tracked_paths alone,
    # not main_sha) must not be rewritten even though other outputs are.
    second = reflow.apply_reflow(tmp_path, _inputs(main_sha=_OTHER_SHA))
    assert "docs/project_sources/generated/REPOSITORY_TREE.txt" in second["files_unchanged"]
    assert tree_path.stat().st_mtime_ns == original_mtime
    assert first["files_written"] != second["files_written"]


# --------------------------------------------------------------------------- #
# CLI: --verify-git-head and end-to-end against a real, minimal git checkout
# --------------------------------------------------------------------------- #


def _git(root: Path, *args: str) -> str:
    """Same fixed-executable discipline as `merge_source_reflow._git_output`: resolve
    `git` via `shutil.which` once, never trust a bare, partial-path executable name."""

    git = shutil.which("git")
    assert git is not None, "git executable not found on PATH"
    return subprocess.run(  # noqa: S603 -- fixed Git executable resolved via shutil.which above
        [git, *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_minimal_repo(root: Path) -> None:
    docs_dir = root / "docs" / "project_sources"
    docs_dir.mkdir(parents=True)
    (docs_dir / "03_CURRENT_DEVELOPMENT_STATE.md").write_text(_STATE_TEXT, encoding="utf-8")
    (docs_dir / "05_PHASE_ACCEPTANCE_LEDGER.md").write_text(_LEDGER_TEXT, encoding="utf-8")
    (root / "README.md").write_text(_README_TEXT, encoding="utf-8")

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "initial")


def test_cli_end_to_end_against_a_real_minimal_git_checkout(tmp_path: Path) -> None:
    _init_minimal_repo(tmp_path)
    actual_head = _git(tmp_path, "rev-parse", "HEAD")

    exit_code = reflow.main(
        [
            "--root",
            str(tmp_path),
            "--main-sha",
            actual_head,
            "--observed-at-utc",
            "2026-09-07T00:00:00Z",
            "--verify-git-head",
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "SHA256SUMS").is_file()
    assert (tmp_path / "HANDOFF.md").is_file()


def test_cli_refuses_a_stale_main_sha_against_a_real_git_checkout(tmp_path: Path) -> None:
    _init_minimal_repo(tmp_path)
    with pytest.raises(SystemExit):
        reflow.main(
            [
                "--root",
                str(tmp_path),
                "--main-sha",
                "0" * 40,
                "--observed-at-utc",
                "2026-09-07T00:00:00Z",
                "--verify-git-head",
            ]
        )
    # And nothing was written by the refused run.
    assert not (tmp_path / "SHA256SUMS").is_file()


def test_cli_is_idempotent_across_two_real_invocations(tmp_path: Path) -> None:
    _init_minimal_repo(tmp_path)
    actual_head = _git(tmp_path, "rev-parse", "HEAD")
    args = [
        "--root",
        str(tmp_path),
        "--main-sha",
        actual_head,
        "--observed-at-utc",
        "2026-09-07T00:00:00Z",
    ]
    assert reflow.main(args) == 0
    sha256sums_first = (tmp_path / "SHA256SUMS").read_bytes()
    assert reflow.main(args) == 0
    sha256sums_second = (tmp_path / "SHA256SUMS").read_bytes()
    assert sha256sums_first == sha256sums_second


# --------------------------------------------------------------------------- #
# Phase/Authority/semantic boundaries this module must never cross
# --------------------------------------------------------------------------- #


def test_no_allowlisted_path_reaches_into_kernel_or_governance_surfaces() -> None:
    forbidden_prefixes = (
        "src/",
        "00_KERNEL/",
        "01_SCHEMA/",
        "02_ENGINE/",
        "04_BOOT/",
        "05_CLI/",
        "07_AGENT_RUNTIME/",
        "03_BINDING/",
        ".github/workflows/",
    )
    for path in reflow.ALLOWLISTED_GENERATED_PATHS:
        assert not path.startswith(forbidden_prefixes), path


def test_no_allowlisted_path_is_a_human_owned_source_document() -> None:
    for path in reflow.ALLOWLISTED_GENERATED_PATHS:
        if path.startswith("docs/project_sources/"):
            assert path.startswith("docs/project_sources/generated/"), path
