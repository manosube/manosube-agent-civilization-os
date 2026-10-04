"""Static-shape assertions for Issue #57's two GitHub Actions workflows
(`03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` sections 10-12), hardened by Structural
Review Round 1 (`ADOPT_MSR_R1_EVENT_BOUND_REVALIDATED_AND_PATH_HARDENED_REFLOW`, Issue
#57 comment 5567433361) and Round 2
(`ADOPT_MSR_R2_PR_INTRODUCED_DIFF_AND_COMPLETE_GENERATED_TREE`, Issue #57 comment
5567994773).

This session cannot execute a live GitHub Actions run against a real Pull Request or the
protected `main` branch (contract section 12) -- these tests review the workflow YAML by
inspection, the identical text-based pattern `test_source_freshness_drift_detection.py`
already applies to the Issue #54 workflow (no YAML-parsing dependency added), never by a
live push. They prove: the pre-merge gate workflow makes no write of its own
(`contents: read`, no merge/approve/comment action), and computes its changed-path diff
against the real merge-base commit rather than the base branch's current tip, so a
base-only change that landed after this Pull Request's branch diverged is never attributed
to this Pull Request (MSR-R2-F1); the post-merge workflow triggers only on a Pull Request
being closed as merged, never on every push to main (MSR-R1-F1); candidate-output
validation runs before any `git add`/`commit`/`push` (MSR-R1-F2); staging is gated by this
workflow's own literal, hardcoded path allowlist checked against the actual working-tree
diff, never by trusting `merge_source_reflow.py`'s own reported file list (MSR-R1-F3); and
neither workflow can push to anywhere but `main` nor touch any Kernel, Schema, Binding, or
workflow-definition path itself (`WORKFLOW_SELF_MODIFICATION=false`).

**PR #108 Structural Review Round 1 (F6)** widens this file's own closed workflow-filename
inventory to admit a fourth, genuinely unrelated workflow Issue #105 adds
(`runtime_observation.yml`, the Runtime Observation transport's own `workflow_dispatch`-only
render step) and adds assertions of its own: that it is dispatch-only (no push/pull_request/
schedule trigger of any kind, matching this file's own existing discipline for the two
workflows above), declares `contents: read` and nothing broader, and -- the one new class of
check this round adds, closing PR #108's own F5 -- that it interpolates no
`github.event.inputs.*` value directly into any `run:` script's own source text; every such
value reaches a step exclusively through that step's own `env:` mapping. ``main``'s own
`03_BINDING/MERGE_SOURCE_REFLOW_CONTRACT.md` governs the two Issue #57 workflows only;
`runtime_observation.yml`'s own full contract lives in `10_RUNTIME/RUNTIME_CONTRACT.md` and
`docs/runtime_observation_transports.md` -- this file pins only the narrow, mechanical
file-set and input-safety facts a change to either file could silently regress.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
PRE_MERGE_PATH = WORKFLOWS_DIR / "merge_source_pre_merge_gate.yml"
POST_MERGE_PATH = WORKFLOWS_DIR / "merge_source_post_merge_reflow.yml"
RUNTIME_OBSERVATION_PATH = WORKFLOWS_DIR / "runtime_observation.yml"


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
    """PR #108 SR1 F6: widened to admit ``runtime_observation.yml`` (Issue #105's own
    `workflow_dispatch`-only transport-rendering workflow) -- a genuine fourth workflow this
    repository now ships, not an unreviewed addition this test should keep hiding. Its own
    dispatch-only trigger, minimal permissions, and input-safety are asserted below, the
    identical discipline this file already keeps for the two Issue #57 workflows."""

    names = {p.name for p in WORKFLOWS_DIR.glob("*.yml")}
    assert names == {
        "source_freshness_drift_detection.yml",
        "merge_source_pre_merge_gate.yml",
        "merge_source_post_merge_reflow.yml",
        "runtime_observation.yml",
    }


# --------------------------------------------------------------------------- #
# runtime_observation.yml (Issue #105; PR #108 SR1 F5/F6) -- dispatch-only, read-only,
# input-injection-safe.
# --------------------------------------------------------------------------- #


def test_runtime_observation_workflow_triggers_only_on_workflow_dispatch() -> None:
    text = RUNTIME_OBSERVATION_PATH.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "\npush:" not in text
    assert "pull_request:" not in text
    assert "schedule:" not in text


def test_runtime_observation_workflow_declares_read_only_permissions_and_nothing_else() -> None:
    text = RUNTIME_OBSERVATION_PATH.read_text(encoding="utf-8")
    assert "permissions:\n  contents: read\n" in text
    for forbidden_scope in ("contents: write", "issues:", "pull-requests:", "id-token:"):
        assert forbidden_scope not in text


def test_runtime_observation_workflow_never_merges_approves_comments_or_pushes() -> None:
    text = RUNTIME_OBSERVATION_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "merge_pull_request",
        "gh pr merge",
        "gh pr review",
        "gh pr comment",
        "git push",
        "git commit",
    ):
        assert forbidden not in text


def test_runtime_observation_workflow_only_invokes_the_render_command_subcommand() -> None:
    """This workflow renders a command; it never invokes the ``observe`` subcommand (the one
    that can actually spawn a real SSH process) -- it cannot execute the bounded observation
    itself, by construction, not merely by convention."""

    text = RUNTIME_OBSERVATION_PATH.read_text(encoding="utf-8")
    assert "render-command" in text
    assert "transport.py observe" not in text
    assert " observe \\" not in text


def test_runtime_observation_workflow_interpolates_no_event_input_into_run_script_text() -> None:
    """PR #108 SR1 F5: the exact injection class the first delivery carried --
    ``${{ github.event.inputs.* }}`` interpolated directly into a `run:` step's own script
    source is expanded by GitHub Actions *before* the shell ever sees the script, so a value
    containing ``$(...)`` or backticks would be evaluated as a real command, not merely read
    as data. Every `${{ github.event.inputs.* }}` reference in this file must appear only on
    the right-hand side of an `env:` mapping entry -- never inside a `run:` block's own
    multi-line script body."""

    text = RUNTIME_OBSERVATION_PATH.read_text(encoding="utf-8")
    event_input_pattern = re.compile(r"\$\{\{\s*github\.event\.inputs\.[A-Za-z0-9_]+\s*\}\}")
    assert event_input_pattern.search(text), "expected at least one github.event.inputs reference"

    run_block_pattern = re.compile(r"^(\s*)run:\s*\|\n((?:\1 .*\n|\n)*)", re.MULTILINE)
    for match in run_block_pattern.finditer(text):
        run_body = match.group(2)
        assert not event_input_pattern.search(run_body), (
            f"a run: step's own script text directly interpolates github.event.inputs: "
            f"{run_body!r}"
        )

    # The one permitted form: a bare `run: echo "$GRANT_JSON" > grant.json` whose own value
    # comes from that exact step's own env: mapping, never from inline interpolation.
    inline_run_pattern = re.compile(r"^(\s*)run:\s*(?!\|)(.+)$", re.MULTILINE)
    for match in inline_run_pattern.finditer(text):
        assert not event_input_pattern.search(match.group(2)), (
            f"an inline run: step directly interpolates github.event.inputs: {match.group(2)!r}"
        )


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


def test_pre_merge_gate_diffs_against_the_real_merge_base_not_the_base_tip() -> None:
    """MSR-R2-F1: `github.event.pull_request.base.sha` is the base branch's tip *at event
    time*, which can have moved past where this Pull Request's own branch actually
    diverged. A plain two-way `git diff base_sha head_sha` would incorrectly attribute any
    base-only change landed after divergence to this Pull Request's own source-impact
    obligation -- the workflow must resolve the actual merge-base commit first and diff
    against that instead."""

    text = _body_text(PRE_MERGE_PATH)
    assert "git merge-base" in text
    merge_base_index = text.index("git merge-base")
    diff_index = text.index("git diff --name-only")
    assert merge_base_index < diff_index
    # The diff itself must consume the resolved merge-base, not the raw base_sha, directly.
    assert 'git diff --name-only "$MERGE_BASE"' in text


# --------------------------------------------------------------------------- #
# Post-merge reflow: the one narrow, declared push exception
# --------------------------------------------------------------------------- #


def test_post_merge_reflow_triggers_only_on_pull_request_closed_and_merged() -> None:
    """MSR-R1-F1: bound to the specific manually merged Pull Request, never to every push
    to main -- so this workflow's own reflow commit (a direct push, not a Pull Request
    being closed as merged) can never itself re-trigger this workflow."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "pull_request:\n    types: [closed]" in text
    assert "if: github.event.pull_request.merged == true" in text
    assert "\npush:" not in text
    assert "branches: [main]" not in text  # no push trigger of any shape
    assert "schedule:" not in text
    assert "workflow_dispatch" not in text


def test_post_merge_reflow_binds_main_sha_and_observed_at_to_the_merge_event_itself() -> None:
    """MSR-R1-F1: `main_sha` is the Pull Request's own `merge_commit_sha`, never a freshly
    resolved `HEAD`; `observed_at_utc` is the Pull Request's own `merged_at`, never the
    wall-clock time this job happens to run."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "github.event.pull_request.merge_commit_sha" in text
    assert "github.event.pull_request.merged_at" in text


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


def test_post_merge_reflow_never_trusts_files_written_as_staging_authority() -> None:
    """MSR-R1-F3: the workflow must never trust `merge_source_reflow.py`'s own reported
    `files_written` list as authority to stage paths -- staging is instead gated by this
    workflow's own literal allowlist checked against the actual working-tree diff."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert "files_written" not in text
    assert "git add --" in text


def test_post_merge_reflow_enforces_its_own_literal_hardcoded_path_allowlist() -> None:
    """MSR-R1-F3: a literal, workflow-defined allowlist (not sourced from
    `merge_source_reflow.py`'s own output) checked against `git status`'s actual report of
    the working-tree diff -- covering untracked new files too, since the very first reflow
    run creates paths that do not yet exist as tracked files."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    for allowlisted_path in (
        "docs/project_sources/generated/CURRENT_REPOSITORY_FACTS.json",
        "docs/project_sources/generated/REPOSITORY_TREE.txt",
        "docs/project_sources/generated/PHASE_EVIDENCE_INDEX.json",
        "docs/project_sources/generated/SOURCE_REFLOW_RECEIPT.json",
        "HANDOFF.md",
        "SHA256SUMS",
        "README.md",
    ):
        assert allowlisted_path in text
    assert "git status --porcelain" in text
    assert "--untracked-files=all" in text
    assert "refusing: changed path outside this workflow's own literal allowlist" in text


def test_post_merge_reflow_validates_the_candidate_before_any_commit_or_push() -> None:
    """MSR-R1-F2: source-freshness/drift validation against the candidate (already
    reflowed, not yet committed) working tree must run, and must run *before* `git add`,
    `git commit`, or `git push` appear in the file -- a validation failure aborts the job
    before any of those steps runs."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    validate_index = text.index("Validate the candidate output before any commit or push")
    add_index = text.index("git add --")
    commit_index = text.index("git commit")
    push_index = text.index("git push")
    assert validate_index < add_index < commit_index < push_index
    assert "convergence_proven" in text


def test_post_merge_reflow_allowlist_enforcement_precedes_staging() -> None:
    """MSR-R1-F3: the literal-allowlist check must run before the commit/push step stages
    anything -- never after."""

    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    allowlist_step_index = text.index(
        "Enforce this workflow's own literal path allowlist against the actual diff"
    )
    commit_step_index = text.index(
        "Commit and push only the paths this workflow's own allowlist check passed"
    )
    assert allowlist_step_index < commit_step_index


def test_post_merge_reflow_skips_the_commit_when_nothing_was_written() -> None:
    text = POST_MERGE_PATH.read_text(encoding="utf-8")
    assert 'if [ -z "$CHANGED" ]' in text
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


def test_post_merge_reflow_validates_source_freshness_before_committing() -> None:
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
