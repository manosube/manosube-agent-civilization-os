# Governance continuity in AI-assisted software development

SHUKOU — English companion for external evaluation, draft, 2026-10-09.

This companion summarizes the [Japanese design and experience report](MANOSUBE_governance_continuity_ja.md). It is not a complete translation, a peer-reviewed article, or a newly conducted real-agent experiment. The Japanese report's fixed code version and public-trial references remain its evidence boundary.

An [English manuscript translation draft](MANOSUBE_governance_continuity_en.md) covers
all sections and appendices and awaits author review.

## Abstract

Persisting a conversation or resuming an execution does not necessarily preserve what a development agent was authorized to change or why its output may be accepted as complete. We call the continuity of these relationships governance continuity. MANOSUBE connects objectives, project state, observations, differences, authority decisions, changes, evidence and reflow in a common canonical-state cycle. Its design separates replaceable execution agents from the record of permitted actions and completion grounds. Four requirements organize the analysis: objective and subject identity; authorization bound to scope and version; evidence bound to its subject and freshness; and preservation of unresolved differences. Public code and scoped development receipts support implementation feasibility. Existing paired evidence contains two deterministic tasks, with both conditions succeeding; it does not establish a causal reliability advantage. We propose controlled comparisons of false acceptance, incorrect rejection, handoff performance and verification cost.

## Problem and contribution

A successor agent can read an earlier statement that tests passed even when the repository head has changed. A previous approval may concern a different work unit, actor or path set. Durable text preserves the statement; it does not by itself preserve its validity. MANOSUBE's contribution is an integration design connecting these meanings to transition and acceptance contracts. External persistence, authorization, event sourcing and durable execution are established techniques, not claimed inventions of this project.

The term OS denotes the project's agent-work governance kernel, not a general-purpose hardware operating system. The unit of acceptance is a declared project state and its evidence, rather than a model's confident final message.

## Design and enforcement boundary

The cycle is `OBJECTIVE → STATE → OBSERVATION → DIFFERENCE → AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE`. Canonical identity connects records to subjects and revisions. An authorization decision is distinct from capability. Evidence and sufficient evidence are distinct. A merged pull request is distinct from a demonstrated runtime result. Unresolved differences are retained instead of disappearing during a handoff.

Cryptographic hashes support integrity and identity; they do not prove that an observation is true. Signature verification relies on an authentic trust anchor and suitable key custody. An authority evaluator does not sandbox a process. A model with an independent shell or network credential can act outside the kernel; operating-system isolation, credential separation and mediation of real tool calls require separate verification. Static topology checks cover installed package source and have known limits; their success is not a proof about every possible external adapter.

## Evidence available

The Japanese report analyzes code at `c8f7cecd13e32133e183df8b2131859c524207b1` and separately cites the scoped Copilot trial in PR #107, its Human acceptance and the after-state record in Issue #106. That trial is a small public development receipt. It is not an independent adoption study or a demonstration of a general handoff benefit.

The saved paired comparison has two deterministic tasks, with both direct execution and the canonical route succeeding. It demonstrates that the compared procedures ran within the recorded scope. It estimates neither the size of a reliability benefit nor the cost of long-running development. An author's test receipt, a bot review and an independently operated external reproduction must be identified separately.

Recent independent work motivates the problem: [OverclaimBench](https://arxiv.org/abs/2609.20812) examines completion overclaims against agent transcripts; [False Success](https://arxiv.org/abs/2606.09863) examines claims inconsistent with environment state; [The Unreliable Progress Bar](https://arxiv.org/html/2609.08589) examines self-reported execution progress. These papers do not evaluate MANOSUBE, prove its effectiveness, or establish historical priority for this project's design.

## Falsifiable evaluation

H1: subject- and version-bound completion acceptance reduces false acceptance on independently grounded tasks. H2: explicit authorization binding reduces admitted out-of-scope changes under an equal execution boundary. H3: preserving unresolved differences and decisions reduces handoff errors and human re-explanation. H4: those benefits outweigh added verification and operation cost for identifiable task classes.

The [real-agent protocol draft](../../examples/false_completion/PROTOCOL.md) starts with H1. It requires matched models, capabilities and task versions; randomized paired order; independent after-state oracles; retained failures and abstentions; task-level confidence intervals; and actual elapsed time, spending and active human minutes. UNKNOWN observations remain unknown. Repeated deterministic closure controls are regression tests, not independent task samples or a substitute for a real-agent comparison.

## Threats to validity

The author designed the system and selected the analyzed examples. A small, controlled corpus cannot support generalization across tasks or operators. Static checks and synthetic witness chains support internal consistency within their declared scope; they do not establish external provenance or factual accuracy by themselves. Repeated experiments on one task are correlated. Assistance may compromise independence if the author operates the trial. Model/provider changes, task selection and evaluation-oracle errors can change measured outcomes. Overhead must be reported alongside benefit.

## External review requested

Please examine whether the four requirements adequately characterize governance continuity; whether existing persistence and authorization systems can provide equivalent behavior with simpler contracts; whether the enforcement boundary is accurately described; and which workload makes the integration worthwhile. A blocked reproduction or counterexample is useful. Use the [offline example](../../examples/01_minimal_kernel_cycle/README.md) and return version-bound success, failure or partial receipts to [Issue #100](https://github.com/manosube/manosube-agent-civilization-os/issues/100).

This English companion is a discussion entry point. Before an arXiv or journal submission, complete the full manuscript translation, verify every reference and authorship/affiliation declaration, review the measurement claims, and obtain the author's final submission decision. No submission is made by this file.
