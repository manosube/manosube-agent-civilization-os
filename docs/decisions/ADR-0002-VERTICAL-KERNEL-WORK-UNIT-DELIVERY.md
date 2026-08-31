# ADR-0002 — Vertical Kernel Work-Unit Delivery

```text
ADR_ID=ADR-0002
STATUS=ACCEPTED
DATE=2026-08-31
DECISION_AUTHORITY=SHUKOU
AFFECTED_ELEMENT=KERNEL_DELIVERY_SEMANTICS
CANONICAL_CYCLE_CHANGED=false
KERNEL_ELEMENT_ADDED=false
COMPLETION_GATE_WEAKENED=false
```

## Context

Early v0.1 work often projected one Kernel element as separate Contract, Schema and Engine Issues and Pull Requests. This preserved review boundaries but multiplied handoffs, delayed predecessor integration and increased the probability that implementation completeness would be confused with connected completeness.

The Human directed the Structural Advisor to preserve canonical order while minimizing unnecessary Issue／PR fragmentation.

## Decision

Adopt `00_KERNEL/KERNEL_VERTICAL_WORK_UNIT_DELIVERY.md` as the mandatory default delivery protocol.

One Kernel element is normally delivered as one vertical package:

```text
Contract + Schema + Engine + Tests + Predecessor Integration
```

A split requires an evidenced permitted split condition. Kernel dependency order, Single Authority, Evidence Sufficiency, Completion Semantics and Human merge authority remain unchanged.

## Consequences

- fewer avoidable Issue／PR handoffs;
- earlier real-route integration;
- one executable completion boundary per Kernel element;
- larger but semantically cohesive Pull Requests;
- explicit fail-closed split decisions;
- no permission to combine multiple future Kernel elements in one package;
- no permission to add adapters before the v0.1 natural cycle.

## Authority and Compatibility

```text
HUMAN_EXPLICIT_APPROVAL=true
ORIGIN_COMPATIBLE=true
KERNEL_CONSTITUTION_COMPATIBLE=true
SINGLE_AUTHORITY_PRESERVED=true
EVIDENCE_REQUIREMENT_PRESERVED=true
HUMAN_MERGE_AUTHORITY_PRESERVED=true
```
