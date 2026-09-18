# Corrected Round 6 rebind -- frozen-protocol raw events

`ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN` (PR #90 comment 5715652626), adopting the
Structural Advisor's governance correction (comment 5715630976). This is the round's own final
run: `PROTOCOL_FROZEN_BEFORE_RESULTS=true` is a structural fact here, not merely followed order
-- `examples/comparative_benchmark/frozen_protocol_r6/protocol_freeze.json` was durably
committed and reload-verified equal (`tests/comparative_benchmark/
test_frozen_protocol_rebind.py::test_protocol_freeze_commit_is_durable_and_reload_equal`)
*before* any task below was executed or observed, and
`manosube_agent_civilization.comparative_benchmark.route.commit_result_bundle` itself refuses a
result-bundle commit against any protocol freeze it cannot resolve from the Store first
(`test_commit_result_bundle_refuses_without_a_prior_committed_protocol_freeze`).

```text
PROTOCOL_FREEZE_ID=CBPF-7734C3D061B73E03690A7D3C11DFFCA92C831040E373E17FDC1EE8D9457E088F
RESULT_BUNDLE_ID=CBRB-D3496F4F5A7909CCA20074376009D92046CA96210DAFBDDEED7F0CF3B3F2D45A
TRUST_ANCHOR_ID=CBTA-F4FEBDBC9C8E7309C1855E2E59072824F812382D7B11B744483F804C483C759E
```

Agent identity for every event below: this session's own native tool-using agent (Claude
Sonnet 5 running inside Claude Code, session
`https://claude.ai/code/session_0154miaUnGA543JWmVrxqamk`), acting with a real Bash/Write tool
surface, single-turn resource budget, no retries -- the identical declared identity in both
comparison groups (`SAME_AGENT_COMPARISON_AVAILABLE`). Every real write below is bound to a real,
machine-verifiable `tests.comparative_benchmark.agent_execution_receipt` alongside its output
file -- disclosed as integrity/provenance evidence only, never as platform-issued executor
authentication (`CONTENT_ADDRESS_IS_EXECUTOR_SIGNATURE=false`, `PLATFORM_ATTESTATION_CLAIMED=
false`; no independently verifiable native-Agent issuer signature is available in this
environment, comment 5715524639).

Published in full, including nothing withheld -- both tasks succeeded in both conditions under
this frozen corpus's own always-authorizing Authority Rule, exactly as predeclared
(`numeric_thresholds` in the protocol freeze).

## MANOSUBE_ABSENT condition (`claude_code_alone_real_agent_frozen_protocol`)

No Difference was raised, no Authority Decision was obtained, no Observation/Evidence/Reflow
wrapped either write -- the agent acted directly.

### Task A (hash computation)

- Start: `2026-09-17T14:11:57.840554974Z`
- Command run: `printf '%s' 'MANOSUBE_PHASE21_ROUND6_TASK_A' | sha256sum | awk '{printf "%s", $1}' > examples/comparative_benchmark/real_agent_corpus/frozen_protocol/absent/task_a_output.txt`
- Raw output: `b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8`
- End: `2026-09-17T14:11:57.845020216Z`
- Result: `SUCCESS` (`COMPLETED_VERIFIED`)
- Receipt: `absent/task_a_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-15A51C3FC5B9D459D455B7666A7C5224BE32D7D88402679950526F2A598A4327`.

### Task B (prime enumeration)

- Start: `2026-09-17T14:12:01.884835964Z`
- Command run: a Python 3 one-liner enumerating the primes in `[2, 50]`, writing to
  `examples/comparative_benchmark/real_agent_corpus/frozen_protocol/absent/task_b_output.txt`
- Raw output: `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47`
- End: `2026-09-17T14:12:01.898601838Z`
- Result: `SUCCESS` (`COMPLETED_VERIFIED`)
- Receipt: `absent/task_b_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-46E0CBA4E8ECD1A04C5E0CC70028C2CC69231CCDF8FC89A41258929E117F2B26`.

## MANOSUBE_PRESENT condition (`manosube_present_real_agent_frozen_protocol`)

Both tasks driven through this repository's own real Difference → Authority Decision → Change →
(the real Agent action, resolved and verified via its receipt) → Observation → Evidence →
Sufficiency → Reflow production route
(`tests/comparative_benchmark/frozen_protocol_present_cycle.py`, adapted from the P90-R6-IF1-
corrected composer and pointed at this round's own dedicated fixture pair
(`tests/fixtures/comparative_benchmark_frozen_protocol.py`) and corpus directory -- never
mutating the exploratory Round 6 fixture/corpus). `resolve_present_task` verifies each task's
receipt before taking any post-change Observation; a receipt that fails any check would raise
before that point.

### Task A (hash computation) -- real event

- Start: `2026-09-17T14:12:40.742297983Z`
- Command run: `printf '%s' 'MANOSUBE_PHASE21_ROUND6_TASK_A' | sha256sum | awk '{printf "%s", $1}' > examples/comparative_benchmark/real_agent_corpus/frozen_protocol/present/task_a_output.txt`
- Raw output: `b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8` (byte-identical to the
  `MANOSUBE_ABSENT` output above)
- End: `2026-09-17T14:12:40.746507579Z`
- Receipt: `present/task_a_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-7EEAE98A8B1F1748B60A38DEC34B66F0F70A88E23F82250EEB9003927E2A5237`.
- Identity ledger:

  | Record | id |
  | --- | --- |
  | `difference_id` | `D-E9628B379029804BC0E1288B677501A621311912C92FDEBA440333435B9FAB6A` |
  | `authority_decision_id` | `AUTH-DEC-2A24A14F421320D982E09EF90832F4BE4E5EDEB8D73FFEAAC0E497CAA7371FE8` |
  | `change_id` | `CHANGE-5A0C2F0F27C77232327788512F48AB5CF83647984112FA11E17DB6768631AAD2` |
  | `evidence_sufficiency_id` | `EVID-SUFF-FCC290455A56B882737557BF95FD2CE4185FDBDD0656F85BDE83A406721EDB09` |
  | `closure_evaluation_id` | `D-CLOSE-EVAL-829DCB4CAE92CBD9DD052B2068F3D2A43BBBECE27133115DA355580642C77963` |
  | `difference_lifecycle_event_id` | `D-EVT-F5B89B97C5EDF2932F824464E8E6775F9F3E7B8568899305A0B2554417598C53` |
  | `state_transition_ref.id` | `TX-D10EEBA4C975D08E1A511F9B88FBCC4B169706A71011673A3409ACD620494F5F` |
  | `final_terminal_status` | `CLOSED` |

### Task B (prime enumeration) -- real event

- Start: `2026-09-17T14:13:17.022287163Z`
- Command run: the identical Python 3 one-liner as the `MANOSUBE_ABSENT` event above, writing
  to `examples/comparative_benchmark/real_agent_corpus/frozen_protocol/present/task_b_output.txt`
- Raw output: `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47` (byte-identical to the `MANOSUBE_ABSENT`
  output above)
- End: `2026-09-17T14:13:17.035813513Z`
- Receipt: `present/task_b_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-670384795DA9571B55E79F89463F11A9ABBDAD5E8C4E7E0A60C93182A78DB08A`.
- Identity ledger:

  | Record | id |
  | --- | --- |
  | `difference_id` | `D-11EEEEC97751D92522D3A621257E87EC8B24A4ED2F32BE56E3E2DC5F5806D078` |
  | `authority_decision_id` | `AUTH-DEC-8F9782737F3EFA677316A84AE4DF0B17A1185CE9A38F86684367BF87C36B2784` |
  | `change_id` | `CHANGE-6FDC6E82C7A59145D4075D90BC1A5A212BB52CF183BC7782B58C40DF44CB073D` |
  | `evidence_sufficiency_id` | `EVID-SUFF-7C7E55D312B0FBADB814369F4BE2549FA2204009310A31315CA098D279E1B54C` |
  | `closure_evaluation_id` | `D-CLOSE-EVAL-649317E7F1B1D97B656FE67BE44D5927D5E95722521A23F63A3AC7A4D4400084` |
  | `difference_lifecycle_event_id` | `D-EVT-6336657ADF32E254A78B93D4CB1E66FB2C83863D1B2D6864EAF989C23EA37E72` |
  | `state_transition_ref.id` | `TX-7CF37795B23774AC224736CDEDE9097AAA04DAEB4BCF95FAED5B2178AF927EAB` |
  | `final_terminal_status` | `CLOSED` |

## Result bundle

Committed via `manosube_agent_civilization.comparative_benchmark.route.commit_result_bundle`
against the resolved, already-committed protocol freeze above -- `metrics`/`claims`/
`threshold_evaluations` are always recomputed from `raw_events` alone, never accepted as a
caller-supplied shortcut. Every predeclared `numeric_thresholds` entry passed:

```text
manosube_present_real_agent_frozen_protocol: raw_event_count=2, COMPLETED_VERIFIED=2
claude_code_alone_real_agent_frozen_protocol: raw_event_count=2, COMPLETED_VERIFIED=2
```

`tests/comparative_benchmark/test_frozen_protocol_rebind.py::
test_published_result_bundle_rederives_byte_for_byte_from_its_own_raw_events` independently
re-derives `metrics`/`claims`/`threshold_evaluations` from the published `result_bundle.json`'s
own `raw_events` and asserts byte-equality with the stored values.

### MANOSUBE_PRESENCE_IS_THE_ONLY_TREATMENT_DIFFERENCE

- Identical Agent identity: this session's own native tool-using agent, both conditions.
- Identical task inputs, tool surface (Bash/Write), and resource budget (single-turn, no
  retries), both conditions.
- Identical real output bytes in both conditions (confirmed above).
- The only difference: whether a real Difference/Authority Decision/Change/Observation/
  Evidence/Reflow lifecycle wrapped the identical write (`MANOSUBE_PRESENT`) or did not
  (`MANOSUBE_ABSENT`).

### Honest reproduction scope

This frozen corpus's own two tasks are fully deterministic and independently computable without
any native Agent capability. `tests/comparative_benchmark/frozen_protocol_reproduction.py`
mechanically recomputes both and reaches the identical recorded per-group outcome counts
(`tests/comparative_benchmark/test_frozen_protocol_rebind.py::
test_mechanical_reproduction_matches_the_published_result_bundles_metrics`) -- a narrower,
honest `THIRD_PARTY_REPRODUCIBLE` claim than "the original native Agent execution was
reproduced," which this repository has no capability to offer (see
`tests/fixtures/comparative_benchmark_rebind_protocol.py`'s own `comparability_loss_receipts`,
`CLR-CB21-R6F-0002`). The independent, third-party proof this protocol's own Gate 21 rests on
remains SHUKOU's separately executed Windows reproduction, signed with the already registered
Ed25519 key (comment 5709021178) and admitted against this protocol's own
Store-resolved trust anchor (`CBTA-F4FEBDBC9C8E7309C1855E2E59072824F812382D7B11B744483F804C483C759E`).
