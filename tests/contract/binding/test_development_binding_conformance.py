"""The Binding, asserted where it is enforced rather than where it is written.

Two halves. The first checks that the ratified decision is recorded exactly and that the
protocols register it. The second checks the thing Issue #34 insisted on: that registering
a repository Binding did **not** make named providers part of Kernel semantics.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manosube_agent_civilization.development_binding import (
    HUMAN_AUTHORITY,
    ROLES,
    PolicyIntegrityError,
    load_policy,
    prohibited_trigger_in,
)
from manosube_agent_civilization.development_binding.policy import (
    BINDING_DOCUMENT_PATH,
    DECISION_ID,
    EXECUTOR,
    POLICY_PATH,
    RATIFIED_HUMAN_ONLY_STATES,
    RATIFIED_MAY,
    RATIFIED_MUST_NOT,
    RATIFIED_OWNERS,
    RATIFIED_TRANSITIONS,
    STRUCTURAL_ADVISOR,
)

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[3]
POLICY = load_policy()
BINDING = BINDING_DOCUMENT_PATH.read_text(encoding="utf-8")
DELIVERY = (ROOT / "00_KERNEL" / "KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md").read_text(
    encoding="utf-8"
)
COMMUNICATION = (ROOT / "00_KERNEL" / "HUMAN_AGENT_WORK_COMMUNICATION.md").read_text(
    encoding="utf-8"
)


# --------------------------------------------------------------------------- #
# 1. the ratified decision, recorded exactly
# --------------------------------------------------------------------------- #


def test_the_human_decision_is_recorded_with_its_identity() -> None:
    assert POLICY["decision_id"] == DECISION_ID
    assert DECISION_ID.endswith("0002")
    assert POLICY["supersedes"].endswith("0001")
    assert POLICY["decision_status"] == "RATIFIED"
    assert POLICY["decision_authority"] == HUMAN_AUTHORITY


def test_the_role_map_is_closed_and_exact() -> None:
    assert frozenset({"CHATGPT", "CLAUDE_CODE", "GITHUB", "SHUKOU"}) == ROLES
    assert frozenset(POLICY["roles"]) == ROLES


@pytest.mark.parametrize(
    "role,capability",
    [
        ("CHATGPT", "STRUCTURAL_ADVISOR"),
        ("CLAUDE_CODE", "IMPLEMENTATION_EXECUTOR"),
        ("GITHUB", "HUMAN_INTENT_AND_WORK_STATE_SURFACE"),
        ("SHUKOU", "HUMAN_CONSTITUTIONAL_AUTHORITY"),
    ],
)
def test_each_participant_holds_exactly_its_declared_capability(
    role: str, capability: str
) -> None:
    assert POLICY["roles"][role]["capability"] == capability


@pytest.mark.parametrize("role", ["CHATGPT", "CLAUDE_CODE", "GITHUB"])
@pytest.mark.parametrize("forbidden", ["FINAL_ACCEPTANCE_DECISION", "MERGE_OPERATION"])
def test_no_participant_but_the_human_may_accept_or_merge(role: str, forbidden: str) -> None:
    assert forbidden in POLICY["roles"][role]["must_not"]
    assert forbidden not in POLICY["roles"][role]["may"]


@pytest.mark.parametrize("owner_field,owner", sorted(RATIFIED_OWNERS.items()))
def test_every_owner_field_names_its_ratified_owner(owner_field: str, owner: str) -> None:
    assert POLICY[owner_field] == owner


def test_the_ambiguous_merge_decision_vocabulary_is_gone() -> None:
    """Decision 0002: one word must not cover a recommendation and an authority."""

    serialized = json.dumps(POLICY)
    assert "MERGE_DECISION" not in serialized
    assert "ACCEPTANCE_DECISION" not in serialized.replace("FINAL_ACCEPTANCE_DECISION", "")
    for separated in (
        "MERGE_READINESS_RECOMMENDATION",
        "FINAL_ACCEPTANCE_DECISION",
        "MERGE_OPERATION",
    ):
        assert separated in serialized


def test_the_human_holds_final_acceptance_merge_and_adoption() -> None:
    may = POLICY["roles"][HUMAN_AUTHORITY]["may"]
    for held in ("FINAL_ACCEPTANCE_DECISION", "MERGE_OPERATION", "ADOPT_EXTERNAL_FINDING"):
        assert held in may


def test_the_advisor_holds_review_and_recommendation_only() -> None:
    role = POLICY["roles"][STRUCTURAL_ADVISOR]
    assert "STRUCTURAL_REVIEW" in role["may"]
    assert "MERGE_READINESS_RECOMMENDATION" in role["may"]
    assert "FINAL_ACCEPTANCE_DECISION" in role["must_not"]
    assert "MERGE_OPERATION" in role["must_not"]


# --------------------------------------------------------------------------- #
# 1A. the ratified sets are pinned, not merely shaped
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("role", sorted(ROLES))
def test_each_role_holds_exactly_its_ratified_permission_sets(role: str) -> None:
    """The repair. The first version checked these were string lists and nothing more."""

    assert frozenset(POLICY["roles"][role]["may"]) == RATIFIED_MAY[role]
    assert frozenset(POLICY["roles"][role]["must_not"]) == RATIFIED_MUST_NOT[role]


def test_no_role_both_permits_and_forbids_an_action() -> None:
    for role in sorted(ROLES):
        assert not (RATIFIED_MAY[role] & RATIFIED_MUST_NOT[role]), role


def test_the_human_only_state_set_is_pinned_whole() -> None:
    assert frozenset(POLICY["human_only_states"]) == RATIFIED_HUMAN_ONLY_STATES
    assert RATIFIED_HUMAN_ONLY_STATES


def test_the_declared_transition_set_is_pinned_whole() -> None:
    declared = {
        (transition["actor"], transition["from"], transition["to"])
        for transition in POLICY["handoff_transitions"]
    }
    assert declared == RATIFIED_TRANSITIONS


def test_only_the_human_appears_as_the_actor_of_a_human_only_transition() -> None:
    """Read from the ratified set rather than the artifact, so an edit cannot satisfy it."""

    for actor, _, target in RATIFIED_TRANSITIONS:
        if target in RATIFIED_HUMAN_ONLY_STATES:
            assert actor == HUMAN_AUTHORITY, (actor, target)


def test_the_executor_is_never_the_actor_of_an_advisor_only_transition() -> None:
    for actor, _, target in RATIFIED_TRANSITIONS:
        if target in POLICY["advisor_only_states"]:
            assert actor == STRUCTURAL_ADVISOR, (actor, target)
        if actor == EXECUTOR:
            assert target not in RATIFIED_HUMAN_ONLY_STATES


# --------------------------------------------------------------------------- #
# 2. the prohibited route
# --------------------------------------------------------------------------- #


def test_automated_review_triggers_are_prohibited() -> None:
    assert POLICY["automated_review_trigger_allowed"] is False


@pytest.mark.parametrize("role", ["CHATGPT", "CLAUDE_CODE"])
def test_no_agent_may_request_an_automated_external_review(role: str) -> None:
    assert "REQUEST_AUTOMATED_EXTERNAL_REVIEW" in POLICY["roles"][role]["must_not"]


@pytest.mark.parametrize("role", ["CHATGPT", "CLAUDE_CODE", "GITHUB"])
def test_no_agent_may_adopt_an_external_finding(role: str) -> None:
    assert "ADOPT_EXTERNAL_FINDING" in POLICY["roles"][role]["must_not"]


def test_an_external_finding_begins_unverified() -> None:
    assert POLICY["external_finding_initial_status"] == "UNVERIFIED_EXTERNAL_OBSERVATION"
    assert POLICY["external_finding_adoption_authority"] == HUMAN_AUTHORITY


def test_the_executor_terminal_state_is_the_handoff_boundary() -> None:
    assert POLICY["executor_terminal_state"] == "READY_FOR_STRUCTURAL_REVIEW"
    for human_only in ("SHUKOU_ACCEPTED", "SHUKOU_REJECTED", "SHUKOU_MERGED"):
        assert human_only in POLICY["human_only_states"]


# --------------------------------------------------------------------------- #
# 3. the policy artifact refuses to be quietly widened
# --------------------------------------------------------------------------- #


def _mutated(tmp_path: Path, **edits: object) -> Path:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    document.update(edits)
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "edits",
    [
        {"final_acceptance_owner": "CHATGPT"},
        {"merge_operation_owner": "CLAUDE_CODE"},
        {"structural_review_owner": "CLAUDE_CODE"},
        {"merge_readiness_recommendation_owner": "SHUKOU"},
        {"external_finding_adoption_authority": "CODEX"},
        {"automated_review_trigger_allowed": True},
        {"decision_status": "DRAFT"},
        {"decision_authority": "CLAUDE_CODE"},
        {"executor_terminal_state": "SHUKOU_MERGED"},
        {"human_only_states": []},
        {"advisor_only_states": []},
        {"merge_operation_state": "MERGE_RECOMMENDED"},
        {"final_acceptance_state": "MERGE_RECOMMENDED"},
        {"supersedes": "SOMETHING_ELSE"},
        {"external_finding_initial_status": "VERIFIED"},
        {"kernel_element": "CHANGE"},
        {"kernel_provider_neutrality_preserved": False},
        {"policy_version": "0.3"},
        {"escape_hatch": True},
    ],
    ids=lambda edits: "-".join(sorted(edits)),
)
def test_a_policy_edited_across_a_boundary_is_refused(
    tmp_path: Path, edits: dict[str, object]
) -> None:
    """The artifact cannot hand any boundary to whoever edits the file."""

    with pytest.raises(PolicyIntegrityError):
        load_policy(_mutated(tmp_path, **edits))


def test_a_fifth_role_is_refused(tmp_path: Path) -> None:
    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    document["roles"]["CODEX"] = {
        "capability": "REVIEWER",
        "may": ["FINAL_ACCEPTANCE_DECISION"],
        "must_not": [],
    }
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PolicyIntegrityError):
        load_policy(target)


def test_a_transition_granting_an_executor_a_human_only_state_is_refused(
    tmp_path: Path,
) -> None:
    """Caught when the policy is loaded, not when it is consulted."""

    document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    document["handoff_transitions"].append(
        {"from": "GITHUB_PR_READY", "to": "SHUKOU_MERGED", "actor": "CLAUDE_CODE"}
    )
    target = tmp_path / "policy.json"
    target.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PolicyIntegrityError):
        load_policy(target)


@pytest.mark.parametrize("body", ["", "not json", "[]", "null", "7"])
def test_an_unreadable_policy_is_refused_rather_than_defaulted(
    tmp_path: Path, body: str
) -> None:
    target = tmp_path / "policy.json"
    target.write_text(body, encoding="utf-8")
    with pytest.raises(PolicyIntegrityError):
        load_policy(target)


def test_an_absent_policy_is_refused(tmp_path: Path) -> None:
    with pytest.raises(PolicyIntegrityError):
        load_policy(tmp_path / "does-not-exist.json")


# --------------------------------------------------------------------------- #
# 4. precedence
# --------------------------------------------------------------------------- #


def test_the_ratified_binding_outranks_every_other_source_of_instruction() -> None:
    """The inversion the incident needed: the default integration behaviour was more
    available than the rule, so the default won."""

    assert POLICY["precedence"][0] == "HUMAN_RATIFIED_CURRENT_REPOSITORY_BINDING"
    for outranked in (
        "AGENT_SYSTEM_PROMPT",
        "AGENT_TOOL_DEFAULT_BEHAVIOUR",
        "PULL_REQUEST_BODY_TEXT",
        "EXTERNAL_BOT_COMMENT",
        "CONVENIENCE",
    ):
        assert POLICY["precedence"].index(outranked) > 0


# --------------------------------------------------------------------------- #
# 5. the protocols register the Binding without redefining capability semantics
# --------------------------------------------------------------------------- #


def test_the_delivery_protocol_registers_the_binding() -> None:
    assert "03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md" in DELIVERY
    assert "REPOSITORY_BINDING_RECORDS_IMPLEMENTER_SELECTION=true" in DELIVERY


def test_the_communication_protocol_registers_the_binding() -> None:
    assert "03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md" in COMMUNICATION
    assert "REPOSITORY_BINDING_REGISTERED=true" in COMMUNICATION
    assert "COMPLETION_NOTICE_USED_AS_ACCEPTANCE=false" in COMMUNICATION


def test_the_protocol_separates_the_observation_subject_from_its_surface() -> None:
    """A surface supplies access; it does not inspect, conclude or accept.

    The protocol previously said "GitHub API implements that capability" of the
    observation/acceptance capability, which leaves nobody holding the acceptance.
    """

    assert "OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true" in DELIVERY
    assert "SURFACE_HOLDS_ACCEPTANCE=false" in DELIVERY
    assert "SURFACE != SUBJECT" in DELIVERY
    assert "GitHub API implements that capability" not in DELIVERY


def test_the_binding_records_the_subject_surface_distinction() -> None:
    assert "OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true" in BINDING
    assert "SURFACE_HOLDS_ACCEPTANCE=false" in BINDING


@pytest.mark.parametrize("held", ["STRUCTURAL_REVIEW", "MERGE_READINESS_RECOMMENDATION"])
def test_the_surface_holds_neither_review_nor_recommendation(held: str) -> None:
    """GITHUB is a surface in the policy too, not only in the prose."""

    assert held in POLICY["roles"]["GITHUB"]["must_not"]


def test_the_build_ships_the_policy_from_its_canonical_location() -> None:
    """One copy on disk, mapped into the package at build time -- not a second file."""

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.hatch.build.targets.wheel.force-include]" in pyproject
    assert '"03_BINDING/DEVELOPMENT_BINDING_POLICY.json"' in pyproject
    assert (
        "manosube_agent_civilization/development_binding/DEVELOPMENT_BINDING_POLICY.json"
        in pyproject
    )


def test_the_delivery_protocol_still_requires_no_named_provider() -> None:
    """The sentence the Binding must not have weakened."""

    assert (
        "No named provider, API, version-control product, model or Agent is required for "
        "protocol conformance." in DELIVERY
    )
    assert "REPOSITORY_BINDING_REDEFINES_CAPABILITY_SEMANTICS=false" in DELIVERY
    assert "NAMED_PROVIDER_REQUIRED_FOR_PROTOCOL_CONFORMANCE=false" in DELIVERY


# --------------------------------------------------------------------------- #
# 6. Kernel provider neutrality, proven rather than asserted
# --------------------------------------------------------------------------- #


def test_the_binding_declares_itself_not_a_kernel_element() -> None:
    assert POLICY["kernel_element"] is None
    assert POLICY["kernel_provider_neutrality_preserved"] is True


def test_no_participant_name_reaches_the_canonical_schema_registry() -> None:
    """The strongest available proof: read `01_SCHEMA/` and look."""

    for schema in sorted((ROOT / "01_SCHEMA").rglob("*.schema.json")):
        text = schema.read_text(encoding="utf-8").upper()
        for participant in ("CHATGPT", "CLAUDE_CODE", "SHUKOU", "CODEX"):
            assert participant not in text, f"{schema.name} names {participant}"


def test_the_policy_artifact_is_not_in_the_canonical_schema_registry() -> None:
    """Registering it there would make named providers part of Kernel semantics.

    ``01_SCHEMA/binding/`` exists and is empty. It is reserved for the future **Kernel
    Binding element** -- the OS concept that binds a Project to a repository -- which shares
    a word with this repository-development Binding and is otherwise unrelated. This artifact
    does not belong there and must not drift into it.
    """

    assert POLICY_PATH.parent.name == "03_BINDING"
    assert POLICY_PATH.suffix == ".json"
    assert not POLICY_PATH.name.endswith(".schema.json")
    assert list((ROOT / "01_SCHEMA" / "binding").glob("*.schema.json")) == []
    assert POLICY_PATH not in set((ROOT / "01_SCHEMA").rglob("*.json"))


def test_the_binding_is_not_a_kernel_record_type() -> None:
    """It must not appear anywhere the Kernel enumerates its own record types."""

    from manosube_agent_civilization.difference.conformance import (
        CARRIED_SECTIONS,
        EMITTED_SECTIONS,
        RECORD_TYPES,
    )

    for name in ("development_binding", "binding", "chatgpt", "claude_code", "shukou"):
        assert name not in RECORD_TYPES
        assert name not in CARRIED_SECTIONS
        assert name not in EMITTED_SECTIONS


def test_no_kernel_element_imports_the_binding() -> None:
    """Provider neutrality survives only while the dependency points one way."""

    package = ROOT / "src" / "manosube_agent_civilization"
    for element in ("state", "observation", "difference", "authority", "store"):
        for module in sorted((package / element).rglob("*.py")):
            source = module.read_text(encoding="utf-8")
            assert "development_binding" not in source, module


# --------------------------------------------------------------------------- #
# 7. the shipped route is clean
# --------------------------------------------------------------------------- #


def test_the_binding_document_records_the_acceptance_flags() -> None:
    for flag in (
        "CURRENT_REPOSITORY_DEVELOPMENT_BINDING_IMPLEMENTED=true",
        "CURRENT_REPOSITORY_ROLE_MAP_CLOSED=true",
        "CHATGPT_STRUCTURAL_ADVISOR_ONLY=true",
        "CLAUDE_CODE_IMPLEMENTER_ONLY=true",
        "GITHUB_INTENT_AND_RECEIPT_SURFACE_ONLY=true",
        "SHUKOU_SOLE_ACCEPTANCE_AND_MERGE_OWNER=true",
        "STRUCTURAL_REVIEW_OWNER_FIXED=true",
        "MERGE_READINESS_RECOMMENDATION_OWNER_FIXED=true",
        "FINAL_ACCEPTANCE_OWNER_FIXED=true",
        "MERGE_OPERATION_OWNER_FIXED=true",
        "AMBIGUOUS_MERGE_DECISION_RETAINED=false",
        "RATIFIED_POLICY_PINNED_NOT_ONLY_SHAPE_VALIDATED=true",
        "NO_EVALUATION_INPUT_RAISES=true",
        "INSTALLED_WHEEL_GUARD_WORKS=true",
        "DUPLICATE_MAINTAINED_COPY=false",
        "OBSERVATION_SUBJECT_DISTINCT_FROM_OBSERVATION_SURFACE=true",
        "SURFACE_HOLDS_ACCEPTANCE=false",
        "EXTERNAL_FINDING_DEFAULT_UNVERIFIED=true",
        "EXPLICIT_SHUKOU_ADOPTION_REQUIRED=true",
        "BOT_FINDING_AUTO_ADOPTION=false",
        "BOT_FINDING_AUTO_IMPLEMENTATION=false",
        "AUTOMATED_CODEX_REVIEW_TRIGGER_ALLOWED=false",
        "HANDOFF_TERMINATES_AT_READY_FOR_STRUCTURAL_REVIEW=true",
        "INCIDENT_REGRESSION_PROVEN=true",
        "HUMAN_MERGE_BOUNDARY_PRESERVED=true",
        "UNIVERSAL_KERNEL_PROVIDER_NEUTRALITY_PRESERVED=true",
        "RUNTIME_ENFORCEMENT_IMPLEMENTED=false",
    ):
        assert flag in BINDING, flag


def test_the_adr_records_the_root_cause() -> None:
    """Issue #34: an ADR recording why capability-neutral text was insufficient."""

    adr = (
        ROOT / "docs" / "decisions"
        / "ADR-0028-CAPABILITY_NEUTRALITY_WITHOUT_SELECTION_IS_UNBOUND.md"
    ).read_text(encoding="utf-8")
    for recorded in (
        "IMPLEMENTER SELECTED",
        "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0002",
        "HUMAN-DECISION-CURRENT-REPOSITORY-OPERATING-BINDING-0001",
        "RUNTIME_ENFORCEMENT_IMPLEMENTED=false",
        "REPOSITORY_BINDING_REDEFINES_CAPABILITY_SEMANTICS=false",
        # Decision 0002's two corrections, recorded rather than quietly applied.
        "SHAPE VALIDATED != CONTENT PINNED",
        "NO_EVALUATION_INPUT_RAISES=true",
        "MERGE_READINESS_RECOMMENDATION   owner=CHATGPT",
        # The two corrections structural review returned on 2a98af5.
        "SURFACE != SUBJECT",
        "force-include",
    ):
        assert recorded in adr, recorded


def test_the_binding_document_is_not_itself_a_prohibited_route() -> None:
    """The document names the triggers it forbids; it must not read as an invocation.

    Naming a forbidden thing and routing through it are different, and this is the one place
    the distinction has to be made by hand rather than by the detector.
    """

    assert "AUTOMATED_CODEX_REVIEW_TRIGGER_ALLOWED=false" in BINDING
    assert prohibited_trigger_in(BINDING) == []
