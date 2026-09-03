"""Every copy of the executor's terminal state agrees with the Binding that fixes it.

Decision 0002 renamed the executor's terminal state. The Binding, the policy artifact, both
executable templates and the evaluator were corrected. ``HUMAN_AGENT_WORK_COMMUNICATION.md``
§7A restated the same value in prose, nothing compared the two, and it stayed stale through
a structural review and a merge.

```text
A VALUE COPIED INTO FOUR DOCUMENTS AND CHECKED IN NONE WILL DRIFT
```

So this module does not check one line. It finds **every** ``EXECUTOR_TERMINAL_STATE=`` in
every active document and compares it against the policy, and it proves the superseded token
appears nowhere active. A future rename is covered without anyone remembering this file.

Historical records are not active documents. An ADR describes what was decided *then*, and an
incident regression reproduces what happened *then*; both may name a superseded token, and
scrubbing them would destroy the record. They are enumerated explicitly, each entry is
asserted to exist, and the enumeration is asserted to be small -- an exclusion list nobody
checks is the same defect one level up.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from manosube_agent_civilization.development_binding import load_policy
from manosube_agent_civilization.development_binding.policy import (
    EXECUTOR_TERMINAL_STATE,
    SUPERSEDED_EXECUTOR_TERMINAL_STATE,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
POLICY = load_policy()

#: Where an operating rule can be stated: the Kernel protocols, the repository Binding and
#: its executable templates, and the guard's own source.
ACTIVE_ROOTS: tuple[tuple[str, str], ...] = (
    ("00_KERNEL", "*.md"),
    ("03_BINDING", "*.md"),
    ("src/manosube_agent_civilization", "*.py"),
)

#: Records of what was decided or what happened, which may name a superseded token because
#: that is what they are recording. Each is asserted to exist below.
HISTORICAL: frozenset[Path] = frozenset(
    {
        ROOT / "docs" / "decisions" / "ADR-0028-CAPABILITY_NEUTRALITY_WITHOUT_SELECTION_IS_UNBOUND.md",
    }
)

#: The two places the guard must name the superseded token in order to guard against it.
GUARD_SOURCES: frozenset[Path] = frozenset(
    {
        ROOT / "src" / "manosube_agent_civilization" / "development_binding" / "policy.py",
        Path(__file__).resolve(),
    }
)

_TERMINAL_ASSIGNMENT = re.compile(r"EXECUTOR_TERMINAL_STATE\s*=\s*([A-Z_][A-Z0-9_]*)")


def _active_documents() -> list[Path]:
    found: list[Path] = []
    for directory, pattern in ACTIVE_ROOTS:
        found.extend(sorted((ROOT / directory).rglob(pattern)))
    return [path for path in found if path not in HISTORICAL]


ACTIVE = _active_documents()


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_active_inventory_is_neither_empty_nor_shrunk() -> None:
    assert len(ACTIVE) >= 20, len(ACTIVE)


def test_the_communication_protocol_is_in_the_inventory() -> None:
    """The document that drifted. If it ever leaves this set, this test says so."""

    assert ROOT / "00_KERNEL" / "HUMAN_AGENT_WORK_COMMUNICATION.md" in ACTIVE


@pytest.mark.parametrize("record", sorted(HISTORICAL), ids=lambda path: path.name)
def test_every_excluded_historical_record_exists(record: Path) -> None:
    """An exclusion list that names a missing file is a list nobody is reading."""

    assert record.is_file(), record


def test_the_exclusion_list_stays_small() -> None:
    """Exclusions are for history. A growing list is a hiding place."""

    assert len(HISTORICAL) <= 3, sorted(HISTORICAL)


# --------------------------------------------------------------------------- #
# Every copy agrees with the Binding
# --------------------------------------------------------------------------- #


def test_at_least_one_active_document_states_the_terminal_state() -> None:
    """Otherwise the parametrized check below would pass over an empty set."""

    stating = [
        path for path in ACTIVE if _TERMINAL_ASSIGNMENT.search(path.read_text(encoding="utf-8"))
    ]
    assert len(stating) >= 3, [path.name for path in stating]


@pytest.mark.parametrize("path", ACTIVE, ids=lambda path: path.name)
def test_every_stated_terminal_state_matches_the_binding(path: Path) -> None:
    """A copy is allowed. A copy that disagrees with its source is not."""

    for stated in _TERMINAL_ASSIGNMENT.findall(path.read_text(encoding="utf-8")):
        assert stated == POLICY["executor_terminal_state"], (path, stated)


def test_the_policy_and_the_module_constant_agree() -> None:
    assert POLICY["executor_terminal_state"] == EXECUTOR_TERMINAL_STATE


# --------------------------------------------------------------------------- #
# The superseded token is gone from everything active
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", ACTIVE, ids=lambda path: path.name)
def test_no_active_document_carries_the_superseded_terminal_state(path: Path) -> None:
    if path in GUARD_SOURCES:
        pytest.skip("the guard must name the token it forbids")
    assert SUPERSEDED_EXECUTOR_TERMINAL_STATE not in path.read_text(encoding="utf-8"), path


def test_the_superseded_token_is_not_a_declared_state() -> None:
    """It is not merely absent from prose -- the state machine does not have it."""

    assert SUPERSEDED_EXECUTOR_TERMINAL_STATE not in POLICY["handoff_states"]
    assert SUPERSEDED_EXECUTOR_TERMINAL_STATE != EXECUTOR_TERMINAL_STATE


def test_the_guard_would_catch_a_reintroduction(tmp_path: Path) -> None:
    """The control. Without it, every assertion above could be checking nothing.

    A document reintroducing either the superseded token or a disagreeing copy must fail the
    same two checks the active documents pass.
    """

    drifted = tmp_path / "STALE.md"
    drifted.write_text(
        f"EXECUTOR_TERMINAL_STATE={SUPERSEDED_EXECUTOR_TERMINAL_STATE}\n", encoding="utf-8"
    )
    body = drifted.read_text(encoding="utf-8")

    assert SUPERSEDED_EXECUTOR_TERMINAL_STATE in body
    stated = _TERMINAL_ASSIGNMENT.findall(body)
    assert stated == [SUPERSEDED_EXECUTOR_TERMINAL_STATE]
    assert stated[0] != POLICY["executor_terminal_state"]


def test_the_historical_record_still_names_what_was_superseded() -> None:
    """History is preserved rather than scrubbed -- that is why it is excluded, not deleted."""

    adr = next(iter(HISTORICAL)).read_text(encoding="utf-8")
    assert SUPERSEDED_EXECUTOR_TERMINAL_STATE in adr
