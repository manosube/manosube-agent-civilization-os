# WU1: dots Real-Connection Investigation

Tracks #116 / PR #117. This assessment is read-only research; it authorizes no live
dots launch, no new credential, no spend.

## 0. A disclosed, load-bearing limitation of this investigation itself

This session's outbound network policy **explicitly denies** `help.openai.com` and
`chatgpt.com` (confirmed via the agent proxy's own status endpoint: both hosts return
`connect_rejected` / "gateway answered 403 to CONNECT (policy denial)"), and the
`learn.chatgpt.com` URLs PROTOCOL.md §11 cites do not resolve via DNS from this
environment at all (`getaddrinfo ENOTFOUND`). **No item below was verified against
OpenAI's own primary documentation by this investigation.** Everything is drawn from
web-search-indexed secondary sources (OpenAI's help-center text as quoted by search
results, plus independent blogs/community posts), which is itself the correct, honest
classification for an item that would otherwise be reported as unverifiable guesswork.
Any future WU (WU2 or later) run from an environment that *can* reach these hosts
should re-verify every CONFIRMED/UNCONFIRMED item below directly and correct this file.

## 1. What dots is (UNCONFIRMED — secondary sources only)

An always-on ChatGPT agent feature (OpenAI help-center article id `20001530`,
reported launch ~2026-09-29) that keeps working on an ongoing goal between
conversations, runs on its own "cloud computer," and can connect to apps a user
chooses. A human gives a dot a goal, sets what it may do autonomously, and reviews
results; the dot asks the human when a decision needs judgment. Available to Pro
100/200/500 and Business Premium seats by default; Enterprise/Edu/Healthcare need an
admin-enabled beta (default off).

## 2. Classification of the five adapter responsibilities PROTOCOL.md §4 requires

PROTOCOL.md §4 defines the *requested* interface shape
(`read_state / submit_candidate / dispatch_authorized_work / collect_receipt /
stop_and_reconcile`) and is explicit that this is a requirement, not a claim that it
exists as a public API today. Investigation result, per responsibility:

| Adapter responsibility | Classification | Grounds |
|---|---|---|
| `read_state` (dots reading Kernel/repo state) | **UNCONFIRMED, likely HUMAN-MEDIATED ONLY** | No documented API lets an external caller push state *into* a dot's context besides a conversation message or a connected app's own native read (e.g., a dot "connects to apps," generically — no named GitHub connector found; "4000+ apps" is itself unconfirmed against a primary source). |
| `submit_candidate` (dots proposing a Difference candidate back to the Kernel) | **UNAVAILABLE as a programmatic call** | No documented API, SDK, CLI, MCP server, or webhook exists for a *dot* (distinct from OpenAI's general Responses API, which governs ordinary model calls, not a dot's own state). A live GitHub issue (`openai/codex#52332`) explicitly *requests* "a public messaging API for external clients to communicate with an existing Dot" — i.e., this is a known gap, not an oversight in this investigation. |
| `dispatch_authorized_work` (Kernel delegating a work unit *to* a dot programmatically) | **UNAVAILABLE as a programmatic call**, same grounds as above. The only documented delegation direction is dot→Codex (a dot can create a cloud task in a Codex cloud environment the human already set up, or continue an existing local Codex task) — the *reverse* direction (an external system dispatching work into a dot) is not documented. |
| `collect_receipt` (retrieving dots' own execution history/receipt) | **UNCONFIRMED / likely UNAVAILABLE as a durable audit log** | One secondary source states a human "can open a dot's computer at any time to inspect its work" — informal, UI-driven inspection, not a documented history/audit API. No dedicated "Activity view" with a stable, queryable record was confirmed. |
| `stop_and_reconcile` (stopping a dot / confirming the stop) | **PARTIALLY CONFIRMED, important caveat** | Secondary guidance (General Analysis) is explicit that *pausing a dot stops only its main task* — delegated tasks and recurring schedules require **separate** controls (stop delegated tasks in the Activity view; disable recurring work in Scheduled; remove the local-computer grant for a locally-authorized task). A single "pause" is therefore **not** sufficient evidence of full stop for this campaign's own `KILL_SWITCH` case or its `dispatch_stop_seconds_max=30` / `controlled_worker_stop_seconds_max=60` requirements — WU2 must treat "pause" and "stop delegated/scheduled work" as two distinct controls to exercise and confirm, never one. |

## 3. The structural conflict this investigation surfaces (not a minor footnote)

The only **documented** coding-delegation path for a dot is dot → Codex cloud/local
task. This project's own ratified policy (`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`,
confirmed directly from source) places `CODEX` in a capability
(`BOUNDED_TECHNICAL_REVIEWER`) that explicitly `must_not` perform `IMPLEMENTATION` or
`CODE_AUTHORSHIP`, and is not a member of `executor_providers`
(`["CLAUDE_CODE", "GITHUB_COPILOT"]`). If a dot's *normal, documented* way of doing
coding work is to hand it to Codex, and this project's own Decision 0004 forbids Codex
from implementing, then **the natural path PROTOCOL.md §4 describes
("dotsへの限定work unit → 実装executorの実変更") cannot run through dots' own
documented Codex-delegation mechanism without colliding with this project's existing
role separation.**

Two readings resolve this, and WU1 does not pick one — this is exactly the kind of
unconfirmed item that needs an explicit human decision, named in `OPEN_ITEMS.md`:

- **Reading A (narrow, role-preserving):** dots' role per PROTOCOL.md §2's own table is
  "状態読取、差異候補、許可済みwork unitの委任、進捗監視、結果候補提出" — read state,
  propose a Difference candidate, hand off an *authorized* work unit, monitor, submit a
  result candidate. Under this reading, "委任" (delegation) means dots proposes/hands
  off the work unit through the **existing human/Issue-driven mechanism** (the same
  GitHub Issue/handoff pattern already used for CLAUDE_CODE/GITHUB_COPILOT today), never
  dots invoking its own Codex cloud task as the implementer. This reading requires no
  policy change and no conflict — but it also means dots never "executes" anything
  itself; it is a proposer/monitor only, which may be narrower than SHUKOU intends by
  "dotsが本番運用に耐えられるか."
- **Reading B (wide):** dots is expected to actually *drive* implementation end-to-end,
  which — given the documented mechanism is dot→Codex — would require either (a) an
  explicit, separate SHUKOU-ratified policy amendment admitting Codex (or dots itself)
  as a bounded `executor_providers` member for this campaign only, or (b) dots driving
  CLAUDE_CODE/GITHUB_COPILOT through some other, currently undocumented connected-app
  mechanism (unconfirmed to exist).

## 4. Memory isolation between comparison conditions (Q4) — UNVERIFIED, with a concrete mechanism now known

`case-catalog.json`'s own `comparison.memory_isolation_status: "UNVERIFIED"` field is
now explainable, not merely flagged: secondary sources describe a dot's memory as
drawn from three sources (the current conversation, the user's general ChatGPT memory,
and the dot's own private notes), and state that **individual dot memories cannot be
viewed, deleted, or edited — the only way to clear a dot's memory is to delete the
whole dot.** There is no documented per-task memory reset.

Consequence for Q4 (240 runs, `DOTS_ALONE` vs `DOTS_WITH_REAL_MANOSUBE_KERNEL`, same
40 tasks × 3 repetitions): if both conditions must run against the *same* dot identity,
cross-condition memory contamination cannot be ruled out by any means this
investigation found. The only mechanism that plausibly resets memory between runs is
**deleting and recreating the dot entirely** between every isolated run (or at minimum
between every condition switch) — which is itself unconfirmed to fully clear private
notes versus only the dot's own identity. Per PROTOCOL.md §4's own instruction
("隔離不能なら因果比較をBLOCKED_CONTAMINATIONにする"), WU2's run manifest must record,
for every comparison run, whether a fresh dot identity was actually created, and if not,
the comparative-effect verdict for that run is `BLOCKED_CONTAMINATION`, not silently
treated as isolated.

## 5. Usage/cost controls — UNCONFIRMED hard stop exists

Secondary sources: a dot's own *conversation* does not count against ChatGPT usage
limits, but Work/Codex *tasks* a dot starts do count against those products' own
limits. One developer-forum thread (dated, unverified against current billing docs)
reports that OpenAI's "Organization budget" setting only sends alerts — it does not
stop spending — and no hard monthly spend cap was visible in that account's billing UI.
**This campaign's own `ADDITIONAL_SPENDING_ALLOWED_JPY=0`/"追加課金上限は初期値0"
requirement cannot be technically enforced by OpenAI's own platform alone if that
report is still accurate** — it would need an external control (a human monitoring
billing alerts in real time, or a prepaid/capped payment instrument) layered on top,
named explicitly as a required human operational control in `OPEN_ITEMS.md`, not
assumed to be automatic.

## 6. Net classification summary

```text
DOTS_PUBLIC_PROGRAMMATIC_API=UNAVAILABLE (confirmed absent; a feature request for one is open upstream)
DOTS_READ_STATE_CHANNEL=HUMAN_MEDIATED_ONLY (unconfirmed any automated alternative exists)
DOTS_DISPATCH_CHANNEL=HUMAN_MEDIATED_ONLY (same)
DOTS_EXECUTION_HISTORY_API=UNAVAILABLE (informal UI inspection only, unconfirmed as durable/queryable)
DOTS_STOP_CONTROL=PARTIALLY_CONFIRMED (pause = main task only; delegated/scheduled work needs separate, additional stop actions)
DOTS_MEMORY_PER_TASK_RESET=UNAVAILABLE (whole-dot deletion is the only documented reset)
DOTS_HARD_SPEND_CAP=UNCONFIRMED (platform-level alerts only, per one dated source; needs re-verification and/or an external control)
CODEX_DELEGATION_CONFLICT_WITH_DECISION_0004=STRUCTURAL_FINDING (see §3; needs explicit SHUKOU reading A/B decision)
PRIMARY_SOURCE_VERIFICATION_PERFORMED=false (network policy blocks help.openai.com/chatgpt.com from this environment)
```

Given this, the only adapter design that is **actually buildable today**, without an
unofficial/ToS-risk wrapper, is a **human-relay adapter**: a human operator reads the
driver's dispatch instruction, performs the corresponding action in the ChatGPT UI
against the dot, and enters the dot's response/timestamp back into the driver by hand.
This satisfies none of PROTOCOL.md §4's "承認を示す自然言語だけで発火しない" concern
automatically — WU2 must still structurally gate on the driver's own durable records
(per `MEASUREMENT_CONTRACT.md`), never on the human relay's unverified transcription
alone, but it is the one path this investigation can mark CONFIRMED-POSSIBLE rather
than UNAVAILABLE.
