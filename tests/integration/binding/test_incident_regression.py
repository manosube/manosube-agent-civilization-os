"""The incident this Binding exists to prevent, replayed as records.

Issue #34 requires a regression fixture reproducing the exact incident:

```text
automated review requested
→ bot finding received
→ converted into work without Human adoption
→ expected: POLICY REJECTION before implementation handoff
```

This is not a hypothetical. It happened in this repository, on PR #33, and the executor that
did it is the one this file constrains. The sequence below is transcribed from what actually
occurred, not invented to be refutable.
"""

from __future__ import annotations

from typing import Any

import pytest

from manosube_agent_civilization.development_binding import (
    PERMITTED,
    REFUSED,
    evaluate,
    load_policy,
    prohibited_trigger_in,
)

pytestmark = pytest.mark.integration

POLICY = load_policy()

#: The observation identity of the finding in the incident: a Codex review comment on PR #33
#: reporting that `derive_change` accepted a caller-asserted Authority decision.
INCIDENT_OBSERVATION = "CODEX-PR33-P1-AUTHORITY-DECISION-PROVENANCE"


def finding(status: str = "UNVERIFIED_EXTERNAL_OBSERVATION") -> dict[str, Any]:
    return {"observation_id": INCIDENT_OBSERVATION, "source": "CODEX", "status": status}


def disposition(
    requested: str, adoption: dict[str, Any] | None, actor: str = "CLAUDE_CODE"
) -> dict[str, Any]:
    return {
        "record_type": "EXTERNAL_FINDING_DISPOSITION",
        "actor": actor,
        "finding": finding(),
        "requested_disposition": requested,
        "adoption": adoption,
    }


def shukou_adoption(
    observation: str = INCIDENT_OBSERVATION, for_disposition: str = "IMPLEMENTATION_INSTRUCTION"
) -> dict[str, Any]:
    return {
        "authority": "SHUKOU",
        "observation_id": observation,
        "disposition": for_disposition,
    }


# --------------------------------------------------------------------------- #
# Step 1: the executor requests an automated review
# --------------------------------------------------------------------------- #


def test_step_one_the_executor_requesting_automated_review_is_refused() -> None:
    """What actually happened: the executor posted an automated-review trigger itself.

    Nobody asked it to. It was not in the work package. It followed from the integration's
    default shape being more available than the Binding's route -- which is exactly the
    precedence this Binding inverts.
    """

    verdict = evaluate(
        {
            "record_type": "ACTOR_ACTION",
            "actor": "CLAUDE_CODE",
            "action": "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        }
    )
    assert verdict["decision"] == REFUSED
    assert "AUTOMATED_REVIEW_TRIGGER_PROHIBITED" in verdict["reason_codes"]
    assert "ROLE_DRIFT" in verdict["reason_codes"]


def test_the_structural_advisor_may_not_request_it_either() -> None:
    """The first substitution in the incident was the Advisor's, not the executor's."""

    verdict = evaluate(
        {
            "record_type": "ACTOR_ACTION",
            "actor": "CHATGPT",
            "action": "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        }
    )
    assert verdict["decision"] == REFUSED
    assert "AUTOMATED_REVIEW_TRIGGER_PROHIBITED" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# Step 2: the returned finding becomes work, without adoption
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "requested",
    [
        "IMPLEMENTATION_INSTRUCTION",
        "STRUCTURAL_DIFFERENCE",
        "PHASE_BLOCKER",
        "ACCEPTANCE_FAILURE",
        "NEW_WORK_UNIT",
    ],
)
def test_step_two_an_unadopted_finding_becomes_nothing(requested: str) -> None:
    """The gate the incident crossed, on every disposition it could have crossed it as."""

    verdict = evaluate(disposition(requested, adoption=None))
    assert verdict["decision"] == REFUSED
    assert "BOT_FINDING_AUTO_ADOPTION" in verdict["reason_codes"]
    assert "EXPLICIT_HUMAN_ADOPTION_ABSENT" in verdict["reason_codes"]


def test_the_only_thing_an_unadopted_finding_may_become_is_a_question() -> None:
    """Presenting an observation to the Human is permitted. It is the whole permitted set."""

    verdict = evaluate(disposition("PRESENT_TO_HUMAN", adoption=None))
    assert verdict["decision"] == PERMITTED
    assert "OBSERVATION_PRESENTED_NOT_ADOPTED" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# What adoption is, and what it is not
# --------------------------------------------------------------------------- #


def test_an_explicitly_adopted_finding_becomes_work() -> None:
    """The control that keeps every refusal above from passing vacuously.

    The gate is not "refuse everything". A finding SHUKOU adopts, bound to that exact
    observation and that exact disposition, is work.
    """

    verdict = evaluate(disposition("IMPLEMENTATION_INSTRUCTION", adoption=shukou_adoption()))
    assert verdict["decision"] == PERMITTED
    assert "HUMAN_ADOPTED_OBSERVATION" in verdict["reason_codes"]


@pytest.mark.parametrize("pretender", ["CHATGPT", "CLAUDE_CODE", "GITHUB", "CODEX"])
def test_nobody_but_the_human_can_adopt(pretender: str) -> None:
    adoption = shukou_adoption()
    adoption["authority"] = pretender
    verdict = evaluate(disposition("IMPLEMENTATION_INSTRUCTION", adoption=adoption))
    assert verdict["decision"] == REFUSED
    assert "ADOPTION_BY_NON_HUMAN_AUTHORITY" in verdict["reason_codes"]


def test_an_adoption_of_another_observation_does_not_cover_this_one() -> None:
    """An adoption that floats free is one a later finding can be filed under."""

    verdict = evaluate(
        disposition(
            "IMPLEMENTATION_INSTRUCTION",
            adoption=shukou_adoption(observation="CODEX-PR33-P2-SOMETHING-ELSE"),
        )
    )
    assert verdict["decision"] == REFUSED
    assert "ADOPTION_NOT_BOUND_TO_THIS_OBSERVATION" in verdict["reason_codes"]


def test_an_adoption_for_another_disposition_does_not_cover_this_one() -> None:
    """Adopting an observation as a note to read later is not adopting it as work."""

    verdict = evaluate(
        disposition(
            "NEW_WORK_UNIT",
            adoption=shukou_adoption(for_disposition="IMPLEMENTATION_INSTRUCTION"),
        )
    )
    assert verdict["decision"] == REFUSED
    assert "ADOPTION_NOT_BOUND_TO_THIS_DISPOSITION" in verdict["reason_codes"]


@pytest.mark.parametrize(
    "non_adoption",
    ["SILENCE", "SEVERITY_LABEL", "APPARENT_TECHNICAL_CORRECTNESS", "COMPLETED_AUTOMATED_REVIEW"],
)
def test_the_named_non_adoption_signals_are_recorded_as_non_adoption(non_adoption: str) -> None:
    """None of these is adoption, and the policy says so where a reader can check.

    The one that matters most is APPARENT_TECHNICAL_CORRECTNESS. The PR #33 finding *was*
    technically correct. If correctness could substitute for adoption, the adoption step
    would not exist.
    """

    assert non_adoption in POLICY["non_adoption_signals"]


def test_a_finding_asserting_its_own_verification_is_refused() -> None:
    """The claim under review cannot also be the evidence for it."""

    record = disposition("IMPLEMENTATION_INSTRUCTION", adoption=None)
    record["finding"] = finding(status="VERIFIED")
    verdict = evaluate(record)
    assert verdict["decision"] == REFUSED
    assert "FINDING_ASSERTS_ITS_OWN_VERIFICATION" in verdict["reason_codes"]


# --------------------------------------------------------------------------- #
# The whole incident, as one sequence
# --------------------------------------------------------------------------- #


def test_the_incident_is_rejected_before_any_implementation_handoff() -> None:
    """Both steps, in order, with the handoff that would have followed.

    The point of the sequence is the last assertion: the refusal lands *before* an
    implementation handoff exists, not after work has already been done.
    """

    requested_review = evaluate(
        {
            "record_type": "ACTOR_ACTION",
            "actor": "CLAUDE_CODE",
            "action": "REQUEST_AUTOMATED_EXTERNAL_REVIEW",
        }
    )
    converted = evaluate(disposition("IMPLEMENTATION_INSTRUCTION", adoption=None))
    resumed = evaluate(
        {
            "record_type": "HANDOFF_TRANSITION",
            "actor": "CLAUDE_CODE",
            "from_state": "READY_FOR_SHUKOU_REVIEW",
            "to_state": "IMPLEMENTATION_IN_PROGRESS",
        }
    )

    assert requested_review["decision"] == REFUSED
    assert converted["decision"] == REFUSED
    assert resumed["decision"] == REFUSED
    assert "EXECUTOR_CONTINUED_PAST_TERMINAL_STATE" in resumed["reason_codes"]


def test_a_phase_cannot_be_reopened_by_an_unadopted_finding() -> None:
    """`NO_PHASE_REOPEN`: a bot finding does not restart a phase that reached its terminal state."""

    assert evaluate(disposition("PHASE_BLOCKER", adoption=None))["decision"] == REFUSED
    assert (
        evaluate(
            {
                "record_type": "HANDOFF_TRANSITION",
                "actor": "CHATGPT",
                "from_state": "READY_FOR_SHUKOU_REVIEW",
                "to_state": "IMPLEMENTATION_IN_PROGRESS",
            }
        )["decision"]
        == REFUSED
    )


# --------------------------------------------------------------------------- #
# The executable templates stay clean
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "template",
    ["IMPLEMENTATION_HANDOFF_TEMPLATE.md", "PR_COMPLETION_TEMPLATE.md"],
)
def test_no_executable_template_carries_a_prohibited_trigger(template: str) -> None:
    """The weakest guard in the package, and deliberately not what it rests on.

    A template can be edited and a phrase can be paraphrased. That is why the record
    evaluators above exist; this only keeps the shipped route honest.
    """

    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    text = (root / "03_BINDING" / "templates" / template).read_text(encoding="utf-8")
    assert prohibited_trigger_in(text) == []
    assert "READY_FOR_SHUKOU_REVIEW" in text


@pytest.mark.parametrize("trigger", POLICY["prohibited_automated_review_triggers"])
def test_the_trigger_detector_actually_detects(trigger: str) -> None:
    """Otherwise the assertion above is a test of an empty list."""

    assert trigger in prohibited_trigger_in(f"please {trigger} when ready")
    assert trigger in prohibited_trigger_in(trigger.upper())


def test_the_trigger_detector_does_not_fire_on_clean_text() -> None:
    """A detector that flags everything is as useless as one that flags nothing."""

    assert prohibited_trigger_in("READY_FOR_SHUKOU_REVIEW. Shukou performs the check.") == []
