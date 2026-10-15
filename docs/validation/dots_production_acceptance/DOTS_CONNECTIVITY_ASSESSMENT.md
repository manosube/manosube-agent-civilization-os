# WU1: dots Real-Connection Investigation

Tracks #116 / PR #117. This assessment is read-only research; it authorizes no live
dots launch, no new credential, no spend.

## 0. A disclosed, load-bearing limitation of this investigation itself

This session's outbound network policy **explicitly denies** `help.openai.com`,
`chatgpt.com`, **and `learn.chatgpt.com`** (confirmed via the agent proxy's own status
endpoint on two separate occasions: all three hosts return `connect_rejected` /
"gateway answered 403 to CONNECT (policy denial)"). **No item below is verified against
OpenAI's own primary documentation by this investigation** — not because the primary
documentation says something different, but because this environment cannot reach it
at all. This is a disclosed gap in *this investigation's own reach*, never evidence
that a feature does not exist. Where this document says UNCONFIRMED, read it strictly
as "not established either way from here," never as a soft synonym for "probably
absent" — a prior revision of this file conflated the two in several rows below
(§2's `collect_receipt`/`read_state` rows), corrected in this revision after a
reviewer's own direct reading of `learn.chatgpt.com/docs/dots` surfaced GitHub-connector
and Activity-view facts this investigation's own secondary-source search had missed or
undersold.

Everything below is drawn from (a) a reviewer's own cited reading of the primary page
(where explicitly attributed as such), and (b) web-search-indexed secondary sources
(independent blogs, OpenAI's help-center text as quoted by search results, and live
`openai/codex` GitHub issue threads) for everything else. Any future WU run from an
environment that *can* reach `learn.chatgpt.com`/`help.openai.com` should still
re-verify every row below directly against the primary page and correct this file —
this revision narrows the gap, it does not close it.

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
| `read_state` (dots reading Kernel/repo state) | **PARTIALLY CONFIRMED (feature exists) / UNCONFIRMED (external-harness access)** | **Corrected in this revision.** GitHub is confirmed to be among dots' documented connected-app/plugin set: a dot "can use supported plugins installed and enabled for your account, with their connected accounts and existing permissions," and `learn.chatgpt.com/docs/dots` is cited (by a reviewer's own direct reading) as giving a worked example of using a dot to investigate code and prepare changes — i.e., a dot *can* read repository state once a human gives it that goal. What remains UNCONFIRMED is narrower than previously stated: whether an *external automated harness* (not a human typing a prompt) can trigger that read without a human-authored conversational turn. |
| `submit_candidate` (dots proposing a Difference candidate back to the Kernel) | **UNCONFIRMED as a programmatic call** (revised from UNAVAILABLE) | No documented API, SDK, CLI, MCP server, or webhook was found for a *dot* specifically (distinct from OpenAI's general Responses API). A live GitHub issue (`openai/codex#52332`) requests "a public messaging API for external clients to communicate with an existing Dot," which is evidence the gap is real as of that issue's filing, but an open feature request proves absence only as of that date, not permanently — this row is downgraded from a flat UNAVAILABLE to UNCONFIRMED per the §0 correction. |
| `dispatch_authorized_work` (Kernel delegating a work unit *to* a dot programmatically) | **UNCONFIRMED as a programmatic call** (revised from UNAVAILABLE), same grounds as above. The only delegation direction with concrete documented/secondary-source support remains dot→Codex (a dot can create a cloud task in a Codex cloud environment the human already set up, or continue an existing local Codex task); the *reverse* direction (an external system dispatching work into a dot without a human prompt) has not been found documented, but "not found" is this investigation's own search limit, not a primary-source negative. |
| `collect_receipt` (retrieving dots' own execution history/receipt) | **CONFIRMED (feature exists) / UNCONFIRMED (API-level access)** | **Corrected in this revision.** "Activity" is a real, specifically-named feature — corroborated independently across multiple secondary sources (OpenAI's own help text as quoted in search results, and live `openai/codex` GitHub issue threads such as #49531/#50671 that refer to delegated tasks' status and follow-up turns inside it) — not merely "a human can informally open the dot's computer." A dot's delegated-task status and results are reviewed there. What remains UNCONFIRMED is whether Activity exposes a stable, queryable, API-level record a WU2 harness could poll automatically, versus being a human-facing UI view only. |
| `stop_and_reconcile` (stopping a dot / confirming the stop) | **PARTIALLY CONFIRMED, important caveat** | Independently corroborated across multiple sources: *pausing a dot stops only its main task* — delegated tasks are reviewed and stopped specifically in **Activity**, not via Pause, and recurring/scheduled work is controlled separately in **Scheduled**. One source additionally states stopping a task does **not** roll back actions it already completed — relevant to this campaign's own RPO requirement (committed-transition-loss = 0) and to `MEASUREMENT_CONTRACT.md`'s reconciliation gate. A single "pause" remains **not** sufficient evidence of full stop for `KILL_SWITCH` or the `dispatch_stop_seconds_max=30`/`controlled_worker_stop_seconds_max=60` requirements — WU2 must treat pause, Activity-stop, and Scheduled-disable as three distinct controls to exercise and confirm, never conflated into one. |

## 3. The structural conflict this investigation surfaces (not a minor footnote)

The only coding-delegation path with any documented/corroborated support remains dot →
Codex cloud/local task. This project's own ratified policy
(`03_BINDING/DEVELOPMENT_BINDING_POLICY.json`, confirmed directly from source) places
`CODEX` in a capability (`BOUNDED_TECHNICAL_REVIEWER`) that explicitly `must_not`
perform `IMPLEMENTATION` or `CODE_AUTHORSHIP`, and is not a member of
`executor_providers` (`["CLAUDE_CODE", "GITHUB_COPILOT"]`). If a dot's normal way of
doing coding *work* is to hand it to Codex, and this project's own Decision 0004
forbids Codex from implementing, that is a real, structural tension worth surfacing —
**but §2's correction changes the shape of the resolution space**, because the
confirmed GitHub connector gives dots a *second*, non-Codex channel into this
repository: reading Issues/PRs, and (per the cited "prepare changes" example) possibly
posting/opening them directly, without necessarily routing through a Codex cloud task
at all. This is evidence *for* Reading A below, not a reason to treat the conflict as
unresolvable.

Three readings now exist, and WU1 still does not pick one — this remains the kind of
decision that needs an explicit human call, named in `OPEN_ITEMS.md`:

- **Reading A (narrow, role-preserving, now better supported):** dots' role per
  PROTOCOL.md §2's own table is "状態読取、差異候補、許可済みwork unitの委任、進捗監視、
  結果候補提出" — read state, propose a Difference candidate, hand off an *authorized*
  work unit, monitor, submit a result candidate. Under this reading, dots performs these
  steps through its own confirmed GitHub connector (reading/commenting/opening against
  Issues and PRs directly) feeding the **existing human/Issue-driven mechanism** already
  used for CLAUDE_CODE/GITHUB_COPILOT today — never a Codex cloud task as implementer.
  This reading requires no policy change and no conflict with Decision 0004.
- **Reading B (wide, dot→Codex):** dots is expected to drive implementation end-to-end
  via its own documented Codex-delegation path, which would require an explicit,
  separate SHUKOU-ratified policy amendment admitting Codex (or dots itself) as a
  bounded `executor_providers` member for this campaign only.
- **Reading C (wide, dot→GitHub connector directly, new in this revision):** dots uses
  its GitHub connector to prepare/propose changes itself, without Codex at all — still
  requires a `executor_providers`-equivalent decision (is "dots acting through its
  GitHub connector" an implementer, and if so under what boundary?), but does not
  inherit the Codex/Decision-0004 conflict, since Codex is never involved.

WU2 cannot select among these three on its own; `OPEN_ITEMS.md` item 1 is updated to
name all three.

## 4. Memory isolation between comparison conditions (Q4) — UNCONFIRMED (corrected framing)

`case-catalog.json`'s own `comparison.memory_isolation_status: "UNVERIFIED"` field is
now better explained, not resolved: secondary sources describe a dot's memory as drawn
from three sources (the current conversation, the user's general ChatGPT memory, and
the dot's own private notes), and state that individual dot memories cannot be viewed,
deleted, or edited through means those sources describe, and that deleting the whole
dot is one way to clear it. **This investigation found no alternative per-task reset
mechanism — that is a limit of this investigation's own search, not a primary-source
confirmation that no such mechanism exists.** A prior revision stated "there is no
documented per-task memory reset" as if settled; corrected here to UNCONFIRMED.

Consequence for Q4 (240 runs, `DOTS_ALONE` vs `DOTS_WITH_REAL_MANOSUBE_KERNEL`, same 40
tasks × 3 repetitions): if both conditions must run against the *same* dot identity,
cross-condition memory contamination cannot be ruled out by any means this
investigation found. Until a per-task reset is either confirmed or ruled out against
the primary source, the conservative default is unchanged: treat deleting and
recreating the dot entirely between every isolated run (or at minimum between every
condition switch) as the only mechanism this investigation can currently rely on — itself
also unconfirmed to fully clear private notes versus only the dot's own identity. Per
PROTOCOL.md §4's own instruction ("隔離不能なら因果比較をBLOCKED_CONTAMINATIONにする"),
WU2's run manifest must record, for every comparison run, whether a fresh dot identity
was actually created, and if not, the comparative-effect verdict for that run is
`BLOCKED_CONTAMINATION`, not silently treated as isolated. This default is a risk
posture pending better information, not a claim that no better mechanism exists.

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
DOTS_GITHUB_CONNECTOR=CONFIRMED (feature exists; corroborated by multiple independent secondary sources plus a reviewer's direct primary-source reading)
DOTS_ACTIVITY_VIEW=CONFIRMED (feature exists, named, used for reviewing/stopping delegated tasks)
DOTS_PUBLIC_PROGRAMMATIC_API=UNCONFIRMED (no evidence found of one; an open upstream feature request is evidence of a gap as of its filing date, not proof of permanent absence)
DOTS_READ_STATE_CHANNEL=UNCONFIRMED_FOR_EXTERNAL_HARNESS (the dot itself can read via GitHub connector once a human sets the goal; whether an external harness can trigger this without a human-authored prompt is unconfirmed)
DOTS_DISPATCH_CHANNEL=UNCONFIRMED_FOR_EXTERNAL_HARNESS (same distinction)
DOTS_EXECUTION_HISTORY_API=UNCONFIRMED (Activity is a real UI feature; API-level/queryable access to it is unconfirmed)
DOTS_STOP_CONTROL=PARTIALLY_CONFIRMED (pause = main task only; Activity-stop and Scheduled-disable are separate, both now corroborated as named controls; stopping does not roll back completed actions)
DOTS_MEMORY_PER_TASK_RESET=UNCONFIRMED (whole-dot deletion is the only reset found; not confirmed this is the ONLY possible mechanism)
DOTS_HARD_SPEND_CAP=UNCONFIRMED (platform-level alerts only, per one dated source; needs re-verification and/or an external control)
CODEX_DELEGATION_CONFLICT_WITH_DECISION_0004=STRUCTURAL_FINDING, NARROWED (see §3; a non-Codex GitHub-connector path now also exists; needs explicit SHUKOU reading A/B/C decision)
PRIMARY_SOURCE_VERIFICATION_PERFORMED=partial (one reviewer's direct reading of learn.chatgpt.com/docs/dots is reflected above where cited; this investigation's own environment still cannot reach that host)
```

**This revision does not select an adapter design.** The previous revision concluded
that a human-relay adapter was the only buildable path and treated that as settled;
per the correction above, that conclusion was premature — the confirmed GitHub
connector and Activity view reopen Reading A (and the new Reading C) as plausibly
buildable *without* a human manually relaying every step, specifically for the pieces
of `read_state`/`collect_receipt`/`stop_and_reconcile` that route through GitHub
Issues/PRs and Activity rather than through a bespoke dots API. What remains genuinely
unconfirmed — and still blocks picking a final design — is whether any of this is
reachable by an *external, automated* WU2 harness versus requiring a human to be the
one typing into the ChatGPT UI each time. `OPEN_ITEMS.md` items 1 and 7 are updated
to reflect this as the live open question, not "human-relay, decided."
