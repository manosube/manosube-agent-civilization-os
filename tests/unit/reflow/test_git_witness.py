"""R4-F3: pure verification of an immutable Git object witness -- COMMIT -> TREE -> PATH
-> BLOB, from caller-supplied raw object bytes alone, never a live filesystem/Git read.

Every synthetic object here is built the same way ``git hash-object``/``git mktree``
would build a real one -- these are not fixtures describing what a Git object "should"
look like, they are real, well-formed Git objects this module's own hashing functions
independently reproduce the id of.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.reflow.errors import ReflowValidationError
from manosube_agent_civilization.reflow.git_witness import (
    blob_sha1,
    commit_sha1,
    parse_commit_tree_sha,
    parse_tree_entries,
    tree_sha1,
    verify_kernel_source_witness,
)

PATH = "00_KERNEL/KERNEL_INVARIANTS.md"


def _tree_entry(mode: str, name: str, sha_hex: str) -> bytes:
    return mode.encode() + b" " + name.encode("utf-8") + b"\0" + bytes.fromhex(sha_hex)


def _commit_object(tree_sha: str) -> bytes:
    return (
        f"tree {tree_sha}\n"
        "author A <a@example.com> 0 +0000\n"
        "committer A <a@example.com> 0 +0000\n"
        "\n"
        "test commit\n"
    ).encode()


def _build_real_repo() -> dict[str, Any]:
    """Build a real, self-consistent (commit, tree_objects, blob) witness for `PATH`."""

    blob_content = b"# KERNEL_INVARIANTS.md\n\nreal content\n"
    blob_sha = blob_sha1(blob_content)

    leaf_tree_bytes = _tree_entry("100644", "KERNEL_INVARIANTS.md", blob_sha)
    leaf_tree_sha = tree_sha1(leaf_tree_bytes)

    root_tree_bytes = _tree_entry("40000", "00_KERNEL", leaf_tree_sha)
    root_tree_sha = tree_sha1(root_tree_bytes)

    commit_bytes = _commit_object(root_tree_sha)
    commit_sha = commit_sha1(commit_bytes)

    witness = {
        "commit_object": commit_bytes.hex(),
        "tree_objects": {
            root_tree_sha: root_tree_bytes.hex(),
            leaf_tree_sha: leaf_tree_bytes.hex(),
        },
        "blob_object": blob_content.hex(),
    }
    return {
        "witness": witness,
        "commit_sha": commit_sha,
        "tree_sha": root_tree_sha,
        "blob_sha": blob_sha,
    }


def test_a_real_well_formed_witness_verifies() -> None:
    repo = _build_real_repo()
    verify_kernel_source_witness(
        witness=repo["witness"],
        expected_commit_sha=repo["commit_sha"],
        expected_tree_sha=repo["tree_sha"],
        expected_blob_sha=repo["blob_sha"],
        path=PATH,
    )


def test_object_hash_functions_reproduce_git_own_object_ids() -> None:
    # git hash-object semantics: sha1("<kind> <len>\0<content>")
    content = b"hello\n"
    expected = __import__("hashlib").sha1(b"blob 6\0" + content).hexdigest()
    assert blob_sha1(content) == expected


def test_a_tampered_commit_object_fails_its_own_content_address() -> None:
    repo = _build_real_repo()
    witness = dict(repo["witness"])
    tampered_commit = bytes.fromhex(witness["commit_object"]) + b"\n"
    witness["commit_object"] = tampered_commit.hex()
    with pytest.raises(ReflowValidationError, match="commit_object does not hash"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_a_commit_naming_a_foreign_tree_is_refused() -> None:
    repo = _build_real_repo()
    foreign_tree_bytes = _tree_entry("40000", "OTHER", repo["blob_sha"])
    foreign_tree_sha = tree_sha1(foreign_tree_bytes)
    foreign_commit = _commit_object(foreign_tree_sha)
    witness = dict(repo["witness"])
    witness["commit_object"] = foreign_commit.hex()
    with pytest.raises(ReflowValidationError, match="own tree does not match"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=commit_sha1(foreign_commit),
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_a_missing_tree_object_in_the_witness_is_refused() -> None:
    repo = _build_real_repo()
    witness = dict(repo["witness"])
    witness["tree_objects"] = {}
    with pytest.raises(ReflowValidationError, match="missing tree object"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_a_tree_object_that_does_not_hash_to_its_own_key_is_refused() -> None:
    repo = _build_real_repo()
    witness = dict(repo["witness"])
    tree_objects = dict(witness["tree_objects"])
    tampered = bytes.fromhex(tree_objects[repo["tree_sha"]]) + b"\x00extra"
    tree_objects[repo["tree_sha"]] = tampered.hex()
    witness["tree_objects"] = tree_objects
    with pytest.raises(ReflowValidationError, match="does not hash to its own claimed key"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_a_path_segment_absent_from_its_parent_tree_is_refused() -> None:
    repo = _build_real_repo()
    with pytest.raises(ReflowValidationError, match="no entry for path segment"):
        verify_kernel_source_witness(
            witness=repo["witness"],
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path="00_KERNEL/NOT_THE_REAL_FILE.md",
        )


def test_a_path_resolving_to_a_different_blob_than_pinned_is_refused() -> None:
    repo = _build_real_repo()
    substitute_blob = b"substituted content\n"
    substitute_sha = blob_sha1(substitute_blob)
    with pytest.raises(ReflowValidationError, match="blob other than the pinned blob_sha"):
        verify_kernel_source_witness(
            witness=repo["witness"],
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=substitute_sha,
            path=PATH,
        )


def test_a_tampered_blob_object_fails_its_own_content_address() -> None:
    repo = _build_real_repo()
    witness = dict(repo["witness"])
    witness["blob_object"] = (bytes.fromhex(witness["blob_object"]) + b"tampered").hex()
    with pytest.raises(ReflowValidationError, match="blob_object does not hash"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=repo["commit_sha"],
            expected_tree_sha=repo["tree_sha"],
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_r5f5_a_mode_inverted_graph_is_refused_even_though_every_hash_verifies() -> None:
    """R5-F5: the intermediate ``00_KERNEL`` entry declares a blob mode (``100644``) and the
    final ``KERNEL_INVARIANTS.md`` entry declares a tree mode (``40000``) -- every object's
    own content-addressed hash still verifies exactly (this is not a hash forgery), but the
    declared mode at each path position is now independently checked and refused."""

    blob_content = b"hello kernel invariants\n"
    blob_sha = blob_sha1(blob_content)
    leaf_entry = _tree_entry("40000", "KERNEL_INVARIANTS.md", blob_sha)
    leaf_tree_sha = tree_sha1(leaf_entry)
    root_entry = _tree_entry("100644", "00_KERNEL", leaf_tree_sha)
    root_tree_sha = tree_sha1(root_entry)
    commit_object = _commit_object(root_tree_sha)
    commit_sha = commit_sha1(commit_object)
    witness = {
        "commit_object": commit_object.hex(),
        "tree_objects": {root_tree_sha: root_entry.hex(), leaf_tree_sha: leaf_entry.hex()},
        "blob_object": blob_content.hex(),
    }

    with pytest.raises(ReflowValidationError, match="does not carry a tree \\(directory\\) mode"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=commit_sha,
            expected_tree_sha=root_tree_sha,
            expected_blob_sha=blob_sha,
            path=PATH,
        )


def test_r5f5_a_final_segment_with_a_non_blob_mode_is_refused() -> None:
    """The final path segment declaring a submodule/gitlink mode (``160000``) rather than a
    real blob-family mode is refused, even if its sha happens to equal the pinned blob sha."""

    repo = _build_real_repo()
    tampered_leaf = _tree_entry("160000", "KERNEL_INVARIANTS.md", repo["blob_sha"])
    tampered_leaf_sha = tree_sha1(tampered_leaf)
    tampered_root = _tree_entry("40000", "00_KERNEL", tampered_leaf_sha)
    tampered_root_sha = tree_sha1(tampered_root)
    tampered_commit = _commit_object(tampered_root_sha)
    tampered_commit_sha = commit_sha1(tampered_commit)
    witness = {
        "commit_object": tampered_commit.hex(),
        "tree_objects": {tampered_root_sha: tampered_root.hex(), tampered_leaf_sha: tampered_leaf.hex()},
        "blob_object": repo["witness"]["blob_object"],
    }

    with pytest.raises(ReflowValidationError, match="does not carry a blob-family mode"):
        verify_kernel_source_witness(
            witness=witness,
            expected_commit_sha=tampered_commit_sha,
            expected_tree_sha=tampered_root_sha,
            expected_blob_sha=repo["blob_sha"],
            path=PATH,
        )


def test_parse_tree_entries_rejects_a_duplicate_name() -> None:
    entry = _tree_entry("100644", "same", blob_sha1(b"x"))
    with pytest.raises(ReflowValidationError, match="duplicate entry"):
        parse_tree_entries(entry + entry)


def test_parse_commit_tree_sha_rejects_a_commit_with_no_tree_line() -> None:
    with pytest.raises(ReflowValidationError, match="no tree header line"):
        parse_commit_tree_sha(b"author A <a@example.com> 0 +0000\n\nmsg\n")


def test_witness_missing_required_fields_is_refused() -> None:
    with pytest.raises(ReflowValidationError, match="commit_object"):
        verify_kernel_source_witness(
            witness={},
            expected_commit_sha="a" * 40,
            expected_tree_sha="b" * 40,
            expected_blob_sha="c" * 40,
            path=PATH,
        )
