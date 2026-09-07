"""Every state name in a route-bearing document is a state the Binding actually declares.

The first version of this file checked ``EXECUTOR_TERMINAL_STATE=<VALUE>`` assignments and
the absence of one superseded token, and claimed to check "every copy". The templates state
the route in four other forms:

```text
EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW      an assignment
READY_FOR_STRUCTURAL_REVIEW=true                          a flag line
READY_FOR_STRUCTURAL_REVIEW                               bare, inside a fence
The executor stops at `READY_FOR_STRUCTURAL_REVIEW`.      backticked prose
```

Changing any of the last three to a *different wrong value* passed. The claim was wider than
the check -- the same defect the guard exists to catch, in the guard.

So this file does not look for a syntactic form. It extracts **every** upper-case token from
every route-bearing document and asks whether it is a state name the Binding declares.

## What this proves, and what it does not

```text
SUPERSEDED_NAME_IN_ANY_ACTIVE_DOCUMENT      -> caught, repository-wide
STATE_SHAPED_UNKNOWN_TOKEN_IN_ROUTE_DOC     -> caught
RATIFIED_STATE_LEAKING_INTO_A_NEW_DOCUMENT  -> caught, forcing that document into the set
SINGLE_SEGMENT_STATE_OUTSIDE_ROUTE_DOCS     -> not caught
```

The last is stated rather than hidden. ``BLOCKED`` is a ratified state *and* an ordinary
English word appearing in ~20 unrelated Kernel documents, so the closure check below skips
single-segment names. Inside route-bearing documents it is checked like any other.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path
import re

import pytest

from manosube_agent_civilization.development_binding import load_policy
from manosube_agent_civilization.development_binding.policy import (
    EXECUTOR_TERMINAL_STATE,
    RATIFIED_MAY,
    RATIFIED_MUST_NOT,
    ROLES,
    SUPERSEDED_STATE_NAMES,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
POLICY = load_policy()
RATIFIED: frozenset[str] = frozenset(POLICY["handoff_states"])

PACKAGE = ROOT / "src" / "manosube_agent_civilization" / "development_binding"

#: The documents that state the development route. Everything here is swept token by token.
ROUTE_BEARING: tuple[Path, ...] = (
    ROOT / "03_BINDING" / "CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md",
    ROOT / "03_BINDING" / "GOVERNANCE_ADOPTION_RECORD_ENFORCEMENT.md",
    ROOT / "03_BINDING" / "templates" / "IMPLEMENTATION_HANDOFF_TEMPLATE.md",
    ROOT / "03_BINDING" / "templates" / "PR_COMPLETION_TEMPLATE.md",
    ROOT / "00_KERNEL" / "HUMAN_AGENT_WORK_COMMUNICATION.md",
    ROOT / "00_KERNEL" / "KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md",
    *sorted(PACKAGE.glob("*.py")),
)

#: Records of what was decided or what happened. They may name a superseded state, because
#: naming it is what they are for; scrubbing them would destroy the record, not fix anything.
HISTORICAL: frozenset[Path] = frozenset(
    {
        ROOT
        / "docs"
        / "decisions"
        / "ADR-0028-CAPABILITY_NEUTRALITY_WITHOUT_SELECTION_IS_UNBOUND.md",
        Path(__file__).resolve(),
        PACKAGE / "policy.py",
    }
)

#: Acceptance flags whose names look like state names by the shape rule below. Each is
#: asserted to appear as an actual ``NAME=value`` line, and the list is asserted to stay
#: small -- an unchecked allowance is a hiding place.
DECLARED_FLAGS: frozenset[str] = frozenset(
    {
        "CLAUDE_CODE_EXECUTOR_FIXED",
        "CLAUDE_CODE_IMPLEMENTER_ONLY",
        "CLAUDE_CODE_IS_A_KERNEL_ORGAN",
        "STRUCTURAL_REVIEW_OWNER_FIXED",
        "HANDOFF_TERMINATES_AT_READY_FOR_STRUCTURAL_REVIEW",
        "EXECUTOR_SELF_REVIEW_AS_ACCEPTANCE",
    }
)

_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
_ASSIGNMENT = re.compile(r"^([A-Z][A-Z0-9_]*)\s*=", re.MULTILINE)


def _codes_from_source(source: str) -> frozenset[str]:
    """The precise AST extraction :func:`_reason_codes` applies to one module's source.

    Factored out from :func:`_reason_codes` so the precision itself -- what counts as a
    reason code and what does not -- is directly testable against crafted snippets, not only
    observable indirectly through this repository's own current file contents.

    A reason code an evaluator can emit reaches its caller through exactly two syntactic
    forms in this codebase: a string literal passed as a non-decision argument to
    ``_verdict(...)``, or a string literal ``.append()``-ed onto the ``reasons`` list that
    ``_verdict(REFUSED, *reasons)`` later unpacks. A small helper (``_closed``, ``_scalars``)
    hands its caller a reason code by ``return``-ing the literal directly rather than calling
    ``_verdict`` itself, so a bare ``return "SOME_CODE"`` is read as a reason code too --
    still never a bare assignment, docstring, or regex pattern, which are none of these three
    AST shapes.
    """

    codes: set[str] = set()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                codes.add(node.value.value)
            continue
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "_verdict":
            literal_args = node.args[1:]
        elif name == "append":
            literal_args = node.args
        else:
            continue
        for arg in literal_args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                codes.add(arg.value)
    return frozenset(codes)


def _reason_codes() -> frozenset[str]:
    """Every reason code any evaluator in this package has explicitly declared.

    Swept across every module in the package, not only ``evaluation.py`` -- a second
    evaluator sharing this owner (mirroring ``authority``'s own ``evaluate_authority`` +
    ``evaluate_verifier_selection`` precedent) has its own reason-code vocabulary, and
    hardcoding one file's name here is the same kind of blind spot this file's own
    docstring names: a claim ("every verdict reason code") wider than what was checked.

    GAR-R1-F2 (Issue #53 comment 5565302174) replaced an earlier version of this function
    that matched *any* quoted upper-case string anywhere in the source with the precise AST
    extraction :func:`_codes_from_source` performs. GAR-R2-F2 (Issue #53 comment 5565703135)
    replaced *that* in turn: even a precise inference over source shape is still an
    inference, and the allowlist must derive only from an explicit declared surface. Each
    evaluator module now names its own reachable vocabulary in a module-level
    ``EMITTED_REASON_CODES`` constant; this function imports every module in the package and
    unions whichever ones declare it, so a module that emits verdicts without declaring the
    constant is a completeness gap this file cannot silently paper over.

    :func:`_codes_from_source` is not dead code -- it is now the static half of the
    bidirectional proof GAR-R2-F2 requires (every declared code is reachable; every emitted
    code is declared), applied against each module's own ``EMITTED_REASON_CODES`` in
    ``test_adoption_record_enforcement.py`` and
    ``test_evaluation_reason_code_reachability.py``. It no longer builds this allowlist.
    """

    codes: set[str] = set()
    for path in sorted(PACKAGE.glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = importlib.import_module(
            f"manosube_agent_civilization.development_binding.{path.stem}"
        )
        declared = getattr(module, "EMITTED_REASON_CODES", None)
        if declared is not None:
            codes.update(declared)
    return frozenset(codes)


def _policy_vocabulary() -> frozenset[str]:
    """Names that are legitimately not states, derived from the policy rather than listed.

    Roles, actions, upper-cased policy keys and evaluator reason codes. Deriving them means a
    new action or key is covered without anyone remembering this file.
    """

    actions: set[str] = set()
    for role in ROLES:
        actions |= set(RATIFIED_MAY[role]) | set(RATIFIED_MUST_NOT[role])
    keys = {key.upper() for key in POLICY}
    values = {value for value in POLICY.values() if isinstance(value, str)}
    return frozenset(actions | keys | values | set(ROLES) | _reason_codes())


NON_STATE = _policy_vocabulary() | DECLARED_FLAGS


def _segments(token: str) -> set[str]:
    return set(token.split("_"))


def _state_shaped(token: str) -> bool:
    """Whether *token* reads as a handoff state name without being one.

    Shape is measured against the ratified states themselves: sharing two or more
    underscore-separated segments with a declared state. ``READY_FOR_HUMAN_REVIEW`` shares
    three with ``READY_FOR_STRUCTURAL_REVIEW`` and is flagged; ``MERGE_ALLOWED`` shares one
    with ``MERGE_RECOMMENDED`` and is not.
    """

    if token in RATIFIED:
        return False
    return any(len(_segments(token) & _segments(state)) >= 2 for state in RATIFIED)


def drifted_tokens(body: str) -> list[str]:
    """Every token in *body* that reads as a state name the Binding does not declare."""

    return [
        token
        for token in sorted(set(_TOKEN.findall(body)))
        # A name a superseded decision retired, or a name that reads as a state and is not
        # one. Either way the document is stating a route the Binding does not declare.
        if token in SUPERSEDED_STATE_NAMES or (_state_shaped(token) and token not in NON_STATE)
    ]


def _active_documents() -> list[Path]:
    found: list[Path] = []
    for directory, pattern in (
        ("00_KERNEL", "*.md"),
        ("03_BINDING", "*.md"),
        ("src/manosube_agent_civilization", "*.py"),
        ("docs/decisions", "*.md"),
    ):
        found.extend(sorted((ROOT / directory).rglob(pattern)))
    return [path for path in found if path not in HISTORICAL]


ACTIVE = _active_documents()
SWEPT = [path for path in ROUTE_BEARING if path not in HISTORICAL]


# --------------------------------------------------------------------------- #
# The harness, before its subject
# --------------------------------------------------------------------------- #


def test_the_inventories_are_neither_empty_nor_shrunk() -> None:
    assert len(ACTIVE) >= 40, len(ACTIVE)
    assert len(SWEPT) >= 7, [path.name for path in SWEPT]


def test_the_document_that_drifted_is_swept() -> None:
    assert ROOT / "00_KERNEL" / "HUMAN_AGENT_WORK_COMMUNICATION.md" in SWEPT


@pytest.mark.parametrize("record", sorted(HISTORICAL), ids=lambda path: path.name)
def test_every_excluded_record_exists(record: Path) -> None:
    """An exclusion naming a missing file is an exclusion nobody is reading."""

    assert record.is_file(), record


def test_the_exclusion_and_allowance_lists_stay_small() -> None:
    assert len(HISTORICAL) <= 4, sorted(HISTORICAL)
    assert len(DECLARED_FLAGS) <= 10, sorted(DECLARED_FLAGS)


@pytest.mark.parametrize("flag", sorted(DECLARED_FLAGS))
def test_every_declared_flag_is_really_a_flag(flag: str) -> None:
    """Declared as an assignment somewhere, so the allowance cannot hold an invented name."""

    assert any(flag in _ASSIGNMENT.findall(path.read_text(encoding="utf-8")) for path in SWEPT), (
        flag
    )


def test_the_superseded_set_is_complete_and_disjoint() -> None:
    """Decision 0001 retired two states. The first version of this guard knew one."""

    assert "READY_FOR_SHUKOU_REVIEW" in SUPERSEDED_STATE_NAMES
    assert "SHUKOU_CHECK" in SUPERSEDED_STATE_NAMES
    assert not (SUPERSEDED_STATE_NAMES & RATIFIED)


# --------------------------------------------------------------------------- #
# The sweep
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("path", SWEPT, ids=lambda path: path.name)
def test_no_route_bearing_document_names_an_undeclared_state(path: Path) -> None:
    """Every occurrence form at once: assignment, flag line, bare token, backticked prose."""

    assert drifted_tokens(path.read_text(encoding="utf-8")) == [], path


@pytest.mark.parametrize("path", ACTIVE, ids=lambda path: path.name)
def test_no_active_document_carries_a_superseded_state_name(path: Path) -> None:
    """Repository-wide, not only in the swept set."""

    body = path.read_text(encoding="utf-8")
    present = sorted(name for name in SUPERSEDED_STATE_NAMES if name in body)
    assert present == [], (path, present)


@pytest.mark.parametrize("path", ACTIVE, ids=lambda path: path.name)
def test_a_document_stating_the_route_is_in_the_swept_set(path: Path) -> None:
    """The closure that keeps the swept set from going stale.

    A document outside the swept set that names a multi-segment ratified state is a document
    that has begun stating the route without being checked. It must join ``ROUTE_BEARING``.

    Single-segment names are exempt: ``BLOCKED`` is a ratified state and an ordinary English
    word, and treating every mention of it as route text would make this check meaningless.
    """

    if path in SWEPT:
        return
    body = path.read_text(encoding="utf-8")
    named = sorted(
        state for state in RATIFIED if "_" in state and re.search(rf"\b{re.escape(state)}\b", body)
    )
    assert named == [], (path, named)


def test_the_terminal_state_is_stated_and_agrees_everywhere() -> None:
    """The value that drifted, asserted present and correct in each document that states it."""

    stating = [
        path
        for path in SWEPT
        if re.search(rf"\b{re.escape(EXECUTOR_TERMINAL_STATE)}\b", path.read_text(encoding="utf-8"))
    ]
    assert len(stating) >= 4, [path.name for path in stating]
    assert POLICY["executor_terminal_state"] == EXECUTOR_TERMINAL_STATE


# --------------------------------------------------------------------------- #
# Controls: the sweep is proven against every real occurrence form
# --------------------------------------------------------------------------- #
#
# Each case takes the *real* text of a route-bearing document, mutates one occurrence, and
# requires the sweep to reject it. Without these, every assertion above could be checking a
# pattern that never matches anything.


_FORMS: tuple[tuple[str, str, str], ...] = (
    (
        "assignment",
        "EXECUTOR_TERMINAL_STATE=READY_FOR_STRUCTURAL_REVIEW",
        "EXECUTOR_TERMINAL_STATE=READY_FOR_HUMAN_REVIEW",
    ),
    (
        "flag line",
        "READY_FOR_STRUCTURAL_REVIEW=true",
        "READY_FOR_HUMAN_REVIEW=true",
    ),
    (
        "backticked prose",
        "stops at `READY_FOR_STRUCTURAL_REVIEW`",
        "stops at `READY_FOR_HUMAN_REVIEW`",
    ),
    (
        "bare token in a fence",
        "\nREADY_FOR_STRUCTURAL_REVIEW\n",
        "\nREADY_FOR_HUMAN_REVIEW\n",
    ),
    (
        "reverted to a superseded name",
        "READY_FOR_STRUCTURAL_REVIEW",
        "READY_FOR_SHUKOU_REVIEW",
    ),
    (
        "a different retired name",
        "READY_FOR_STRUCTURAL_REVIEW",
        "SHUKOU_CHECK",
    ),
)


@pytest.mark.parametrize("label,original,mutation", _FORMS, ids=[form[0] for form in _FORMS])
def test_the_sweep_rejects_every_occurrence_form(label: str, original: str, mutation: str) -> None:
    real = "\n".join(path.read_text(encoding="utf-8") for path in SWEPT)
    assert original in real, f"no document contains the {label} form any more"
    assert drifted_tokens(real) == []
    assert drifted_tokens(real.replace(original, mutation, 1)) != [], label


def test_the_sweep_does_not_flag_the_documents_as_they_stand() -> None:
    """The control that keeps every rejection above from being a detector that fires always."""

    for path in SWEPT:
        assert drifted_tokens(path.read_text(encoding="utf-8")) == [], path


def test_the_historical_record_still_names_what_was_superseded() -> None:
    """History is preserved rather than scrubbed -- that is why it is excluded, not deleted."""

    adr = (
        ROOT
        / "docs"
        / "decisions"
        / "ADR-0028-CAPABILITY_NEUTRALITY_WITHOUT_SELECTION_IS_UNBOUND.md"
    ).read_text(encoding="utf-8")
    assert "READY_FOR_SHUKOU_REVIEW" in adr


# --------------------------------------------------------------------------- #
# GAR-R1-F2: the reason-code sweep itself is precise, not merely wide
# --------------------------------------------------------------------------- #
#
# The naive predecessor of ``_reason_codes`` matched any quoted upper-case string anywhere in
# the package's source -- which silently admitted role constants, decision constants, and any
# future upper-case prose into the very allowlist this file uses to decide what is *not*
# drift. These cases prove the AST-based replacement admits exactly the two syntactic forms a
# reason code actually reaches its caller through, and nothing wider.


def test_a_verdict_argument_is_admitted() -> None:
    source = 'def f():\n    return _verdict(REFUSED, "SOME_REASON_CODE")\n'
    assert _codes_from_source(source) == frozenset({"SOME_REASON_CODE"})


def test_the_verdict_decision_argument_itself_is_not_admitted() -> None:
    """Position 0 of ``_verdict(...)`` is the decision (``PERMITTED``/``REFUSED``), never a
    reason code -- admitting it would let a decision constant masquerade as one."""

    source = 'def f():\n    return _verdict(REFUSED, "SOME_REASON_CODE")\n'
    assert "REFUSED" not in _codes_from_source(source)


def test_a_reasons_append_argument_is_admitted() -> None:
    source = 'def f():\n    reasons = []\n    reasons.append("SOME_REASON_CODE")\n'
    assert _codes_from_source(source) == frozenset({"SOME_REASON_CODE"})


def test_a_bare_return_literal_is_admitted() -> None:
    """The one indirection real code in this package actually uses: a helper hands its
    caller a reason code by returning the literal, not by calling ``_verdict`` itself."""

    source = 'def _closed():\n    return "SOME_REASON_CODE"\n'
    assert _codes_from_source(source) == frozenset({"SOME_REASON_CODE"})


@pytest.mark.parametrize(
    "label,source",
    [
        ("a bare module-level constant", 'HUMAN_AUTHORITY = "SHUKOU"\n'),
        ("a decision constant assignment", 'PERMITTED = "PERMITTED"\n'),
        (
            "an upper-case mention in a docstring",
            'def f():\n    """Mentions SOME_REASON_CODE in prose, not code."""\n',
        ),
        (
            "an upper-case string inside a regex pattern",
            'import re\nre.compile(r"SOME_REASON_CODE")\n',
        ),
        (
            "an upper-case string passed to an unrelated call",
            'def f():\n    logging.warning("SOME_REASON_CODE")\n',
        ),
    ],
)
def test_an_uppercase_string_outside_verdict_or_append_is_never_admitted(
    label: str, source: str
) -> None:
    assert "SOME_REASON_CODE" not in _codes_from_source(source), label


def test_every_modules_declared_reason_codes_exactly_match_its_own_emittable_codes() -> None:
    """GAR-R2-F2's bidirectional proof (Issue #53 comment 5565703135): every declared reason
    code is reachable, and every emitted reason code is declared -- checked as one set
    equality per module, generically, for whichever modules in the package declare
    ``EMITTED_REASON_CODES`` at all. Not hardcoded to one module's name, for the identical
    reason :func:`_reason_codes` is not: a second evaluator sharing this owner has its own
    vocabulary, and this proof must catch it drifting too.
    """

    for path in sorted(PACKAGE.glob("*.py")):
        if path.name == "__init__.py":
            continue
        module = importlib.import_module(
            f"manosube_agent_civilization.development_binding.{path.stem}"
        )
        declared = getattr(module, "EMITTED_REASON_CODES", None)
        if declared is None:
            continue
        emittable = _codes_from_source(path.read_text(encoding="utf-8"))
        assert frozenset(declared) == emittable, path.name


def test_an_undeclared_route_token_is_still_flagged_regardless_of_sweep_precision() -> None:
    """The precision fix narrows what counts as a *reason code*; it must not narrow what
    counts as a *drifted state token*. An unknown, state-shaped token is still caught."""

    mutated = "EXECUTOR_TERMINAL_STATE=READY_FOR_HUMAN_REVIEW"
    assert drifted_tokens(mutated) == ["READY_FOR_HUMAN_REVIEW"]
