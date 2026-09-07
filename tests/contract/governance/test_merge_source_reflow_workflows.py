"""Static-shape assertions for Issue #57's two GitHub Actions workflows
(`03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` sections 10-12).

This session cannot execute a live GitHub Actions run against a real Pull Request or the
protected `main` branch (contract section 12) -- these tests review the workflow YAML by
inspection, the identical text-based pattern `test_source_freshness_drift_detection.py`
already applies to the Issue #54 workflow (no YAML-parsing dependency added), never by a
live push. They prove: the pre-merge gate workflow makes no write of its own
(`contents: read`, no merge/approve/comment action); the post-merge workflow's `git add`
step names exactly the paths the reflow itself reports as written, never `git add -A` or
a wider glob; a commit only happens when `files_written` is non-empty; and neither
workflow can push to anywhere but `main` nor touch any Kernel, Schema, Binding, or
workflow-definition path itself (`WORKFLOW_SELF_MODIFICATION=false`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
PRE_MERGE_PATH = WORKFLOWS_DIR / "merge_source_pre_merge_gate.yml"
POST_MERGE_PATH = WORKFLOWS_DIR / "merge_source_post_merge_reflow.yml"


def _body_text(path: Path) -> str:
    """*path*'s own text with every full-line, `#`-prefixed comment removed -- used for
    forbidden-substring checks below so a header comment that *names* a prohibited
    pattern in prose (e.g. "never `git add -A`") is never itself mistaken for the
    workflow's own executable use of that pattern."""

    return "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("#")
    )


def test_both_workflow_files_exist() -> None:
    assert PRE_MERGE_PATH.is_file()
    assert POST_MERGE_PATH.is_file()


def test_both_workflows_are_present_alongside_the_pre_existing_source_freshness_workflow() -> None:
    names = {p.name for p in WORKFLOWS_DIR.glob("*.yml")}
    assert names == {
        "source_freshness_drift_detection.yml",
        "merge_source_pre_merge_gate.yml",
        "merge_source_post_merge_reflow.yml",
    }


# --------------------------------------------------------------------------- #
# Pre-merge gate: read-only, triggers on pull_request, never merges/comments
# --------------------------------------------------------------------------- #


def test_pre_merge_gate_declares_read_only_permissions_and_nothing_else() -> None:
    text = PRE_MERGE_PATH.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in text
    for forbidden_scope in ("issues:", "pull-requests:", "contents: write"):
        assert forbidden_scope not in text


def test_pre_merge_gate_triggers_only_on_pull_request_to_main() -> None:
    text = PRE_MERGE_PATH.read_text(encoding="utf-8")
    assert "pull_request:\n    branches: [main]" in text
    assert "\npush:" not in text
    assert "schedule:" not in text
    assert "workflow_dispatch" not in text


def test_pre_merge_gate_never_merges_approves_comments_or_writes() -> None:
    text = PRE_MERGE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "merge_pull_request",
        "gh pr merge",
        "gh pr review",
        "gh pr comment",
        "git push",
        "git commit",
        "git add",
    ):
        assert forbidden not in text


def test_pre_merge_gate_invokes_source_impact_gate_with_the_diff_of_base_and_head() -> None:
    text = PRE_MERGE_PATH.read_text(encoding="utf-8")
    assert "scripts/source_impact_gate.py" in text
    assert "github.event.pull_request.base.sha" in text
    assert "github.event.pull_request.head.sha" in text
    assert "--changed-paths-file" in text


# --------------------------------------------------------------------------- #
# Post-merge reflow: the one narrow, declared push exception
# --------------------------------------------------------------------------- #


def test_post_merge_reflow_triggers_only_on_push_to_main() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "push:\n    branches: [main]" in text
    assert "pull_request" not in text
    assert "schedule:" not in text
    assert "workflow_dispatch" not in text


def test_post_merge_reflow_declares_contents_write_and_nothing_broader() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "permissions:\n  contents: write\n" in text
    for forbidden_scope in ("issues:", "pull-requests:", "actions:", "id-token:"):
        assert forbidden_scope not in text


def test_post_merge_reflow_is_the_only_workflow_granted_contents_write() -> None:
    """The narrow, declared exception to `UNBOUNDED_DIRECT_PUSH_TO_MAIN=false` (contract
    section 11) must not be shared -- no other workflow in this repository may push."""

    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        if path == POST_MERGE_PATH:
            continue
        assert "contents: write" not in path.read_text(encoding="utf-8"), path


def test_post_merge_reflow_never_uses_git_add_dash_a_or_a_wildcard_glob() -> None:
    text = _body_text(POST_MERGE_PATH)
    assert "git add -A" not in text
    assert "git add ." not in text
    assert "git add --all" not in text


def test_post_merge_reflow_adds_only_the_paths_reflow_itself_reports_as_written() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "files_written" in text
    assert "git add --" in text
    assert "xargs git add" in text


def test_post_merge_reflow_skips_the_commit_when_nothing_was_written() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert 'if [ -z "$FILES_WRITTEN" ]' in text
    assert "not committing" in text


def test_post_merge_reflow_commits_and_pushes_at_most_once_per_run() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert text.count("git commit") == 1
    assert text.count("git push") == 1


def test_post_merge_reflow_pushes_only_to_main() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "git push origin HEAD:main" in text


def test_post_merge_reflow_invokes_the_reflow_script_with_verify_git_head() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "scripts/merge_source_reflow.py" in text
    assert "--verify-git-head" in text
    assert "git rev-parse HEAD" in text
    assert "github.sha" not in text  # same SFD-R1-F2 discipline: resolve, never trust the event


def test_post_merge_reflow_revalidates_source_freshness_after_writing() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "scripts/collect_repository_snapshot.py" in text
    assert "scripts/validate_source_freshness.py" in text
    assert "--fail-on-drift" in text


def test_post_merge_reflow_never_touches_workflow_definitions_or_kernel_paths_itself() -> None:
    """`WORKFLOW_SELF_MODIFICATION=false` and `KERNEL_SOURCE_AUTOWRITE=false`: this
    workflow's own script text must never reference a `.github/workflows/` or Kernel path
    as something it writes to (the allowlist enforced in `merge_source_reflow.py` already
    proves this at the Python level; this proves the workflow's own shell text agrees)."""

    text = _body_text(POST_MERGE_PATH)
    forbidden_fragments = (
        ".github/workflows/merge_source_pre_merge_gate.yml",
        ".github/workflows/merge_source_post_merge_reflow.yml",
        "src/manosube_agent_civilization",
        "00_KERNEL/",
        "03_BINDING/",
    )
    for fragment in forbidden_fragments:
        assert fragment not in text
