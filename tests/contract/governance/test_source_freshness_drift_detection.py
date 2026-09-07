"""Issue #54 (`ADOPT_SOURCE_FRESHNESS_DRIFT_DETECTION_ONLY`): the drift-detection-only
governance automation never rewrites an immutable semantic source, the bounded README
status block writer never touches anything outside its own two markers, and the drift
validator itself proves both a real positive and a real negative case rather than a
vacuous one.

This is supporting governance automation, not a Kernel element -- see
``docs/project_sources/00_SOURCE_AUTHORITY_INDEX.md`` and the adoption's own
``SUPPORTING_GOVERNANCE_WORK_ONLY=true``. Nothing here evaluates Authority, Evidence,
Difference, or Reflow.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
import scripts.collect_repository_snapshot as collector
import scripts.generate_readme_status_block as readme_gen
import scripts.validate_source_freshness as freshness

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = ROOT / "docs" / "project_sources"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "source_freshness_drift_detection.yml"

_REAL_MAIN_SHA = "36b06d88cf779d9f04b79e41022b42d1f3d47510"


# --------------------------------------------------------------------------- #
# Immutability: no code path in this delivery ever writes to docs/project_sources/
# --------------------------------------------------------------------------- #


def _write_mode_calls(module: Any) -> list[str]:
    """Every ``open(...)``/``Path.write_text``/``Path.write_bytes`` call site's source
    line, found by walking the module's own AST -- not by trusting a docstring claim."""

    tree = ast.parse(inspect.getsource(module))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "open":
            for keyword in node.keywords:
                if (
                    keyword.arg == "mode"
                    and isinstance(keyword.value, ast.Constant)
                    and "w" in str(keyword.value.value)
                ):
                    found.append(ast.dump(node))
            for arg in node.args[1:2]:
                if isinstance(arg, ast.Constant) and "w" in str(arg.value):
                    found.append(ast.dump(node))
        if name in ("write_text", "write_bytes"):
            found.append(ast.dump(node))
    return found


def test_the_collector_never_writes_a_file() -> None:
    """The read-only observation component (Issue #54 section A) writes nothing --
    ``build_snapshot`` returns a value, and the CLI only ever writes to the caller's
    own ``--output`` stream, which defaults to stdout."""

    assert _write_mode_calls(collector) == []


def test_the_validator_never_writes_a_file() -> None:
    """The drift-detection component (Issue #54 section C) is equally read-only."""

    assert _write_mode_calls(freshness) == []


def test_the_readme_generator_writes_only_via_one_named_argument() -> None:
    """The one component in this delivery that writes anything writes only through its
    own ``--readme`` argument (default ``README.md``) -- never a path under
    ``docs/project_sources/`` and never anywhere else in the module."""

    calls = _write_mode_calls(readme_gen)
    assert len(calls) == 1


def test_the_readme_generators_one_write_call_targets_its_readme_argument() -> None:
    """The single write-mode call found above is ``args.readme.write_text(...)`` --
    the caller-supplied ``--readme`` path (default ``README.md``), never a path this
    module derives from ``docs/project_sources`` itself."""

    tree = ast.parse(inspect.getsource(readme_gen))
    write_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "write_text"
    ]
    assert len(write_calls) == 1
    (call,) = write_calls
    assert isinstance(call.func, ast.Attribute)
    receiver = call.func.value
    assert isinstance(receiver, ast.Attribute) and receiver.attr == "readme"


def test_the_nine_documents_on_disk_are_untouched_by_importing_these_modules() -> None:
    """A behavioural control alongside the static one: merely importing (already done
    at module load time above) and calling the read-only entry points must not change
    a single byte on disk."""

    before = {path.name: path.read_bytes() for path in sorted(DOCS_DIR.glob("*.md"))}
    freshness.load_recorded_facts(DOCS_DIR)
    collector.build_snapshot(_REAL_MAIN_SHA)
    after = {path.name: path.read_bytes() for path in sorted(DOCS_DIR.glob("*.md"))}
    assert before == after
    assert len(before) == 9


# --------------------------------------------------------------------------- #
# extract_fields: the one parser both the validator and the README generator share
# --------------------------------------------------------------------------- #


def test_extract_fields_reads_only_inside_fenced_text_blocks() -> None:
    text = (
        "prose FIELD_OUTSIDE=should_not_appear\n"
        "```text\n"
        "INSIDE_FIELD=yes\n"
        "not a field line\n"
        "```\n"
        "ANOTHER_OUTSIDE=nope\n"
    )
    assert freshness.extract_fields(text) == {"INSIDE_FIELD": "yes"}


def test_extract_fields_last_occurrence_wins() -> None:
    text = "```text\nX=first\n```\n\n```text\nX=second\n```\n"
    assert freshness.extract_fields(text) == {"X": "second"}


def test_extract_fields_on_the_real_current_development_state_document() -> None:
    fields = freshness.extract_fields(
        (DOCS_DIR / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(encoding="utf-8")
    )
    assert fields["MAIN_ACCEPTED_BASE_SHA"] == _REAL_MAIN_SHA
    assert "OBSERVED_AT_UTC" in fields


# --------------------------------------------------------------------------- #
# collect_repository_snapshot: fail closed on an unreadable observation
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "bad_sha",
    ["", "not-a-sha", "abc123", "g" * 40, _REAL_MAIN_SHA + "x", _REAL_MAIN_SHA[:-1]],
)
def test_the_collector_refuses_a_value_that_does_not_look_like_a_git_sha(bad_sha: str) -> None:
    with pytest.raises(SystemExit):
        collector.build_snapshot(bad_sha)


def test_the_collector_accepts_a_real_shaped_sha() -> None:
    snapshot = collector.build_snapshot(_REAL_MAIN_SHA)
    assert snapshot["main_sha"] == _REAL_MAIN_SHA
    assert snapshot["schema_version"] == collector.SCHEMA_VERSION
    assert snapshot["observed_at_utc"].endswith("Z")


# --------------------------------------------------------------------------- #
# validate_source_freshness: real positive and real negative drift proofs
# --------------------------------------------------------------------------- #


def test_no_drift_when_the_observed_main_sha_matches_every_recorded_copy() -> None:
    recorded = freshness.load_recorded_facts(DOCS_DIR)
    report = freshness.validate(recorded, {"main_sha": _REAL_MAIN_SHA, "observed_at_utc": "x"})
    assert report["source_drift_detected"] is False
    assert report["affected_files"] == []
    assert report["required_owner"] is None
    assert report["missing_recorded_fields"] == []


def test_drift_is_detected_and_fully_reported_on_a_real_mismatch() -> None:
    recorded = freshness.load_recorded_facts(DOCS_DIR)
    observed = {"main_sha": "f" * 40, "observed_at_utc": "2099-01-01T00:00:00Z"}
    report = freshness.validate(recorded, observed)
    assert report["source_drift_detected"] is True
    affected = {(entry["file"], entry["field"]) for entry in report["affected_files"]}
    assert affected == {
        ("03_CURRENT_DEVELOPMENT_STATE.md", "MAIN_ACCEPTED_BASE_SHA"),
        ("04_REPOSITORY_ARCHITECTURE.md", "AS_BUILT_REF"),
    }
    assert report["required_owner"] == ["CHATGPT_STRUCTURAL_ADVISOR"]
    assert (
        report["observed_values"]["03_CURRENT_DEVELOPMENT_STATE.md#MAIN_ACCEPTED_BASE_SHA"]
        == "f" * 40
    )
    assert (
        report["recorded_values"]["03_CURRENT_DEVELOPMENT_STATE.md#MAIN_ACCEPTED_BASE_SHA"]
        == _REAL_MAIN_SHA
    )


def test_a_missing_recorded_field_is_reported_separately_from_ordinary_drift() -> None:
    recorded: dict[str, dict[str, str]] = {
        "03_CURRENT_DEVELOPMENT_STATE.md": {},
        "04_REPOSITORY_ARCHITECTURE.md": {},
    }
    report = freshness.validate(recorded, {"main_sha": _REAL_MAIN_SHA, "observed_at_utc": "x"})
    assert report["source_drift_detected"] is False
    assert {(m["file"], m["field"]) for m in report["missing_recorded_fields"]} == {
        ("03_CURRENT_DEVELOPMENT_STATE.md", "MAIN_ACCEPTED_BASE_SHA"),
        ("04_REPOSITORY_ARCHITECTURE.md", "AS_BUILT_REF"),
    }


def test_validate_never_mutates_its_arguments() -> None:
    recorded = freshness.load_recorded_facts(DOCS_DIR)
    recorded_before = {k: dict(v) for k, v in recorded.items()}
    observed = {"main_sha": _REAL_MAIN_SHA, "observed_at_utc": "x"}
    observed_before = dict(observed)
    freshness.validate(recorded, observed)
    assert recorded == recorded_before
    assert observed == observed_before


def test_cli_exits_zero_on_no_drift_even_with_fail_on_drift(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    collector.main(["--main-sha", _REAL_MAIN_SHA, "--output", str(snapshot_path)])
    report_path = tmp_path / "report.json"
    exit_code = freshness.main(
        [
            "--docs-dir",
            str(DOCS_DIR),
            "--observed-snapshot",
            str(snapshot_path),
            "--fail-on-drift",
            "--output",
            str(report_path),
        ]
    )
    assert exit_code == 0
    assert '"source_drift_detected": false' in report_path.read_text(encoding="utf-8")


def test_cli_exits_nonzero_on_drift_only_when_fail_on_drift_is_passed(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    collector.main(["--main-sha", "e" * 40, "--output", str(snapshot_path)])

    report_path = tmp_path / "report_no_fail.json"
    assert (
        freshness.main(
            [
                "--docs-dir",
                str(DOCS_DIR),
                "--observed-snapshot",
                str(snapshot_path),
                "--output",
                str(report_path),
            ]
        )
        == 0
    )
    assert '"source_drift_detected": true' in report_path.read_text(encoding="utf-8")

    report_path_fail = tmp_path / "report_fail.json"
    assert (
        freshness.main(
            [
                "--docs-dir",
                str(DOCS_DIR),
                "--observed-snapshot",
                str(snapshot_path),
                "--fail-on-drift",
                "--output",
                str(report_path_fail),
            ]
        )
        == 1
    )


# --------------------------------------------------------------------------- #
# generate_readme_status_block: bounded, idempotent, refuses an unmarked README
# --------------------------------------------------------------------------- #


def test_apply_replaces_only_the_bytes_between_the_two_markers() -> None:
    before = "human text before\n<!-- SOURCE_STATUS:GENERATED:BEGIN -->old<!-- SOURCE_STATUS:GENERATED:END -->\nhuman text after\n"
    updated = readme_gen.apply(
        before, "<!-- SOURCE_STATUS:GENERATED:BEGIN -->new<!-- SOURCE_STATUS:GENERATED:END -->"
    )
    assert (
        updated
        == "human text before\n<!-- SOURCE_STATUS:GENERATED:BEGIN -->new<!-- SOURCE_STATUS:GENERATED:END -->\nhuman text after\n"
    )


@pytest.mark.parametrize(
    "broken",
    [
        "no markers at all here",
        "<!-- SOURCE_STATUS:GENERATED:BEGIN -->only begin, no end",
        "only end<!-- SOURCE_STATUS:GENERATED:END -->",
        "<!-- SOURCE_STATUS:GENERATED:BEGIN -->one<!-- SOURCE_STATUS:GENERATED:END -->"
        "<!-- SOURCE_STATUS:GENERATED:BEGIN -->two<!-- SOURCE_STATUS:GENERATED:END -->",
    ],
)
def test_apply_refuses_rather_than_silently_appending_when_markers_are_wrong(broken: str) -> None:
    with pytest.raises(SystemExit):
        readme_gen.apply(
            broken, "<!-- SOURCE_STATUS:GENERATED:BEGIN --><!-- SOURCE_STATUS:GENERATED:END -->"
        )


def test_the_generator_is_idempotent_on_the_real_readme() -> None:
    real_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    recorded = freshness.extract_fields(
        (DOCS_DIR / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(encoding="utf-8")
    )
    block = readme_gen.render_block(recorded)
    once = readme_gen.apply(real_readme, block)
    twice = readme_gen.apply(once, block)
    assert once == twice


def test_the_generator_preserves_every_byte_outside_the_markers(tmp_path: Path) -> None:
    real_readme = (ROOT / "README.md").read_text(encoding="utf-8")
    begin = real_readme.index(readme_gen.BEGIN_MARKER)
    end = real_readme.index(readme_gen.END_MARKER) + len(readme_gen.END_MARKER)
    before_block, after_block = real_readme[:begin], real_readme[end:]

    recorded = freshness.extract_fields(
        (DOCS_DIR / "03_CURRENT_DEVELOPMENT_STATE.md").read_text(encoding="utf-8")
    )
    updated = readme_gen.apply(real_readme, readme_gen.render_block(recorded))

    assert updated.startswith(before_block)
    assert updated.endswith(after_block)


def test_render_block_stays_within_its_own_markers() -> None:
    block = readme_gen.render_block({"OBSERVED_AT_UTC": "x", "CURRENT_PHASE": "y"})
    assert block.startswith(readme_gen.BEGIN_MARKER)
    assert block.endswith(readme_gen.END_MARKER)
    assert block.count(readme_gen.BEGIN_MARKER) == 1
    assert block.count(readme_gen.END_MARKER) == 1


# --------------------------------------------------------------------------- #
# The workflow itself: minimal permissions, no write/PR action anywhere
# --------------------------------------------------------------------------- #


def test_the_workflow_file_exists_and_is_the_only_one_in_the_repository() -> None:
    workflows_dir = WORKFLOW_PATH.parent
    assert workflows_dir.is_dir()
    assert [p.name for p in sorted(workflows_dir.glob("*.yml"))] == [WORKFLOW_PATH.name]


def test_the_workflow_declares_read_only_permissions_and_nothing_else() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in text
    for forbidden_scope in ("issues:", "pull-requests:", "contents: write"):
        assert forbidden_scope not in text


def test_the_workflow_never_creates_or_updates_a_pull_request_or_pushes() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "create-pull-request",
        "peter-evans",
        "git push",
        "git commit",
        "gh pr create",
        "gh pr edit",
    ):
        assert forbidden not in text


def test_the_workflow_only_triggers_on_push_to_main_or_manual_dispatch() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "branches: [main]" in text
    assert "pull_request" not in text
    assert "schedule:" not in text
