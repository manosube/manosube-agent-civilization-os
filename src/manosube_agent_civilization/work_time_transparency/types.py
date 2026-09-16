"""Closed vocabulary for the Human Wait-Time Transparency vertical (Issue #22).

Every enum here is the exact vocabulary Issue #22's own body and its SHUKOU adoption
(``ADOPT_ISSUE_22_HUMAN_WAIT_TIME_TRANSPARENCY_VERTICAL``) name -- nothing added, nothing
narrowed. ``ADAPTER_KINDS``/``WORK_UNIT_REF_KINDS`` are a matched pair: index *i* of one names
the adapter that starts the work unit kind at index *i* of the other, mirroring the owner/
entrypoint inventory the adoption's own return evidence records (00_KERNEL/HUMAN_AGENT_WORK_
COMMUNICATION.md's own observable-state vocabulary is 5 states with a single ``COMPLETE``;
``POSITION_KINDS`` restates its non-terminal 4 members exactly, and ``TERMINAL_OUTCOMES``
restates Issue #22's own "Terminal Notice" 5-member vocabulary, which supersedes that single
``COMPLETE`` state at the terminal boundary -- see WORK_TIME_TRANSPARENCY_CONTRACT.md §2).

The one exception to "nothing added": SHUKOU's Structural Review Round 1 correction to PR #87
(``ADOPT_P87_R1_F1_THROUGH_F9``, finding P87-R1-F7) explicitly authorized
(``WTT_BOUNDED_SCHEMA_ENUM_ADAPTER_CHANGE_ALLOWED=true``) adding exactly one ninth member,
``LONG_RUNNING_PROOF``, for Issue #86's own long-running Project production proof entrypoint --
the one caller Issue #86 itself requires to be WTT-coordinated (``WORK_TIME_COORDINATION_
REQUIRED=true``) but that the original Round 0 delivery incorrectly left un-coordinated on the
mistaken premise that this enum could never be extended without a full re-adoption. No other
kind is minted or reused for an unrelated caller.
"""

from __future__ import annotations

#: Every execution-capable adapter the adoption names, in the exact order its own "Mandatory
#: pre-design inventory" lists them, plus the one Round 1-authorized ninth member.
ADAPTER_KINDS: tuple[str, ...] = (
    "CLI",
    "BOOT",
    "TEMPORARY_AGENT",
    "MODEL_RUNTIME",
    "MULTI_AGENT",
    "CHANGE_EXECUTOR",
    "INDEPENDENT_VERIFICATION",
    "GITHUB_PROJECTION",
    "LONG_RUNNING_PROOF",
)

#: The ``work_unit_ref.kind`` each :data:`ADAPTER_KINDS` entry, at the identical index, opens a
#: coordination for.
WORK_UNIT_REF_KINDS: tuple[str, ...] = (
    "cli_invocation",
    "boot_session",
    "temporary_agent_session",
    "model_runtime_work_unit",
    "multi_agent_execution_plan",
    "change_executor_execution",
    "independent_verification_run",
    "github_projection_attempt",
    "long_running_proof_run",
)

ADAPTER_KIND_TO_WORK_UNIT_REF_KIND: dict[str, str] = dict(
    zip(ADAPTER_KINDS, WORK_UNIT_REF_KINDS, strict=True)
)

ESTIMATE_CONFIDENCE_LEVELS: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW")

#: Non-terminal observable positions a Work Coordination Update may report (Issue #22's own
#: "Progress Heartbeat"/"Estimate Revision"/"External Wait" sections; 00_KERNEL/HUMAN_AGENT_
#: WORK_COMMUNICATION.md §3's own vocabulary minus its terminal ``COMPLETE`` member, which this
#: vertical instead expresses only through :data:`TERMINAL_OUTCOMES`).
POSITION_KINDS: tuple[str, ...] = ("WORK_RUNNING", "EXTERNAL_REVIEW_WAIT", "BLOCKED", "ERROR")

#: The exact five-member vocabulary Issue #22's own "Terminal Notice" section requires: "Every
#: work unit ends with exactly one observable outcome."
TERMINAL_OUTCOMES: tuple[str, ...] = (
    "COMPLETED",
    "BLOCKED_HUMAN_ACTION_REQUIRED",
    "FAILED_RETRYABLE",
    "FAILED_TERMINAL",
    "PAUSED_BY_HUMAN",
)

__all__ = [
    "ADAPTER_KINDS",
    "ADAPTER_KIND_TO_WORK_UNIT_REF_KIND",
    "ESTIMATE_CONFIDENCE_LEVELS",
    "POSITION_KINDS",
    "TERMINAL_OUTCOMES",
    "WORK_UNIT_REF_KINDS",
]
