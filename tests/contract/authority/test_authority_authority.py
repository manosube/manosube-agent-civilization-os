"""Authority has exactly one evaluator, and the vocabulary it uses is the documented one.

Two properties are pinned here, both in both directions.

**One owner.** ``PARALLEL_CANONICAL_AUTHORITY=0`` is a Kernel invariant (K-003), and the way
it fails is never a second module announcing itself as an evaluator -- it is a helper, an
auditor, an adapter or a test quietly deciding the same question its own way. So the second
direction is a source scan: the three decision values may not be produced anywhere outside
the owner, whether or not anyone remembered to add an assertion for it.

**One vocabulary.** ``AUTHORITY_LEVELS.md`` declares the levels and the Human-only action
kinds; ``levels.py`` is the executable copy. A copy that drifts is worse than no copy, so the
two are compared as sets rather than trusted to stay aligned.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re

import pytest

from manosube_agent_civilization import authority
from manosube_agent_civilization.authority import approval, engine, levels, prohibition, scope
from manosube_agent_civilization.difference import admissibility

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "manosube_agent_civilization"
AUTHORITY_SRC = SRC / "authority"
CONTRACTS = ROOT / "00_KERNEL" / "05_AUTHORITY"
SCHEMAS = ROOT / "01_SCHEMA" / "authority"

REQUIRED_CONTRACTS = (
    "AUTHORITY_CONTRACT.md",
    "AUTHORITY_LEVELS.md",
    "CAPABILITY_AUTHORITY_SEPARATION.md",
    "APPROVAL_CONTRACT.md",
    "PROHIBITION_CONTRACT.md",
)
REQUIRED_SCHEMAS = (
    "authority.schema.json",
    "authority_rule.schema.json",
    "approval.schema.json",
    "prohibition.schema.json",
)


# --------------------------------------------------------------------------- #
# The declared surface exists, and nothing else claims to be it
# --------------------------------------------------------------------------- #


def test_the_five_contracts_and_four_schemas_exist_and_are_exactly_those() -> None:
    assert {path.name for path in CONTRACTS.glob("*.md")} == set(REQUIRED_CONTRACTS)
    assert {path.name for path in SCHEMAS.glob("*.schema.json")} == set(REQUIRED_SCHEMAS)


def test_the_public_api_is_one_evaluator() -> None:
    """``evaluate_authority`` and nothing else answers the permission question."""

    exported = {name for name in authority.__all__ if not name.isupper()}
    callables = {name for name in exported if callable(getattr(authority, name))}
    assert callables == {"evaluate_authority"} | {
        name for name in callables if name.endswith("Error")
    }
    assert authority.evaluate_authority is engine.evaluate_authority


def test_no_module_outside_the_owner_produces_a_decision() -> None:
    """The coarse direction: the three values may not be returned from anywhere else.

    Deliberately coarse. A second evaluator does not need to be called an evaluator to be
    one, and a rule that reappears anywhere in the tree fails here whether or not a call-site
    assertion was ever written for it.
    """

    produced: dict[str, list[int]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if AUTHORITY_SRC in path.parents or path.parent == AUTHORITY_SRC:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and node.value in levels.DECISIONS
            ):
                produced.setdefault(str(path.relative_to(SRC)), []).append(node.lineno)
    assert not produced, produced


def test_only_the_engine_holds_the_evaluation_itself() -> None:
    """Within the package, the parts are parts. One module assembles the decision."""

    assemblers = [
        path.name
        for path in sorted(AUTHORITY_SRC.glob("*.py"))
        if "authority_decision_id" in path.read_text(encoding="utf-8")
    ]
    assert assemblers == ["engine.py"], assemblers


# --------------------------------------------------------------------------- #
# The vocabulary matches the contract, in both directions
# --------------------------------------------------------------------------- #


def _declared_block(document: str, header: str) -> set[str]:
    """Read one ``text`` block out of a contract, by the token that names it."""

    match = re.search(rf"```text\n{header}\n(.*?)```", document, re.DOTALL)
    assert match is not None, header
    return {line.strip() for line in match.group(1).splitlines() if line.strip()}


def test_the_human_only_action_kinds_match_the_contract_in_both_directions() -> None:
    document = (CONTRACTS / "AUTHORITY_LEVELS.md").read_text(encoding="utf-8")
    declared = _declared_block(document, "HUMAN_ONLY_ACTION_KINDS")
    assert declared == set(levels.HUMAN_ONLY_ACTION_KINDS)


def test_the_three_decisions_are_the_only_ones_and_are_documented() -> None:
    document = (CONTRACTS / "AUTHORITY_LEVELS.md").read_text(encoding="utf-8")
    assert len(levels.DECISIONS) == 3
    for decision in levels.DECISIONS:
        assert decision in document, decision
    schema = (SCHEMAS / "authority.schema.json").read_text(encoding="utf-8")
    for decision in levels.DECISIONS:
        assert decision in schema, decision


def test_precedence_is_total_and_prohibition_is_supreme() -> None:
    assert levels.most_restrictive(*levels.DECISIONS) == levels.PROHIBITED
    assert levels.most_restrictive(levels.AUTONOMOUS, levels.HUMAN_APPROVAL_REQUIRED) == (
        levels.HUMAN_APPROVAL_REQUIRED
    )
    # A permissive value can never lower an established one, in either argument order.
    for decision in levels.DECISIONS:
        assert levels.at_least_as_restrictive_as(levels.AUTONOMOUS, decision) == decision
        assert levels.at_least_as_restrictive_as(decision, levels.AUTONOMOUS) == decision


# --------------------------------------------------------------------------- #
# Structural readability is delegated, not restated
# --------------------------------------------------------------------------- #

DELEGATING_MODULES = {
    "authority.engine": engine,
    "authority.scope": scope,
    "authority.approval": approval,
    "authority.prohibition": prohibition,
}
DECISIONS_OWNED_ELSEWHERE = (
    "require_object",
    "require_collection",
    "require_scalar_tag",
)


@pytest.mark.parametrize("module_name", sorted(DELEGATING_MODULES))
def test_readability_is_the_existing_owner_and_not_a_copy(module_name: str) -> None:
    """ADR-0025's owner, held by object identity rather than by name.

    "Can this be read" already had one owner before Authority existed. Authority asks it
    rather than answering it again -- the dependency runs with the Kernel order
    (DIFFERENCE precedes AUTHORITY), and a re-implementation under the same name fails here.
    """

    module = DELEGATING_MODULES[module_name]
    bound = [name for name in DECISIONS_OWNED_ELSEWHERE if name in vars(module)]
    for name in bound:
        assert vars(module)[name] is getattr(admissibility, name), f"{module_name}.{name}"


def test_no_authority_module_rejects_by_a_negated_type_test() -> None:
    """The same coarse rule ADR-0025 applies to ``difference/``, applied to this package."""

    restated: dict[str, list[int]] = {}
    for path in sorted(AUTHORITY_SRC.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            if not any(isinstance(statement, ast.Raise) for statement in node.body):
                continue
            for sub in ast.walk(node.test):
                if not (isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not)):
                    continue
                for call in ast.walk(sub.operand):
                    if (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Name)
                        and call.func.id == "isinstance"
                        and len(call.args) == 2
                    ):
                        annotation = call.args[1]
                        names = (
                            [annotation]
                            if isinstance(annotation, ast.Name)
                            else list(getattr(annotation, "elts", []))
                        )
                        if any(
                            isinstance(name, ast.Name) and name.id in {"dict", "list", "str"}
                            for name in names
                        ):
                            restated.setdefault(path.name, []).append(node.lineno)
    assert not restated, restated


# --------------------------------------------------------------------------- #
# Capability is not authority, proven by the absence of a channel
# --------------------------------------------------------------------------- #


def test_the_request_key_set_is_closed_and_carries_no_capability_input() -> None:
    """``CAN_DO ≠ MAY_DO`` as a property of the interface, not of a filter inside it.

    There is no parameter for a credential, a token, a tool list, an Agent claim or any
    prose. A request that supplies one is refused rather than ignored, so a caller can never
    believe such an input was weighed.
    """

    declared = set(engine.REQUIRED_REQUEST_KEYS)
    for forbidden in (
        "credential",
        "credentials",
        "token",
        "capabilities",
        "tools",
        "agent",
        "agent_claim",
        "prompt",
        "issue_body",
        "pull_request_body",
        "review_comment",
        "ci_status",
        "session",
        "memory",
    ):
        assert forbidden not in declared, forbidden


def test_the_evaluator_reads_no_clock_no_network_and_no_filesystem() -> None:
    """Determinism as a source property: the evaluation time is an input, never a reading."""

    forbidden = ("datetime.now", "time.time", "utcnow", "requests.", "urlopen", "os.environ")
    for path in sorted(AUTHORITY_SRC.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source, f"{path.name}: {token}"
