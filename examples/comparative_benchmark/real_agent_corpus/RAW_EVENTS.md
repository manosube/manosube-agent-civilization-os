# Round 6 real-Agent corpus -- raw events

**EXPLORATORY_NON_ACCEPTANCE_EVIDENCE.** Per the Structural Advisor's governance correction
(comment 5715630976) and SHUKOU's adoption of the corrected Round 6 rebind (comment 5715652626,
`ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN`): the events and identity ledger below --
committed at heads `dd7db5c` through `df13c4b` -- were produced **before** this protocol's own
final `comparative_benchmark_protocol_freeze` was committed, which reverses the founding Issue
#89 adoption's own required order (`PROTOCOL_FROZEN_BEFORE_RESULTS=true`). They remain valid,
real design/feasibility observations (a genuine Difference→Authority→Change→Observation→
Evidence→Reflow route, a genuine receipt-bound real Agent action per P90-R6-IF1), and are
retained here, untouched, exactly as they were -- but they are **not** the final Phase 21
benchmark result and may **not** be retroactively placed under a later protocol freeze
(`RETROACTIVE_PROTOCOL_FREEZE_ALLOWED=false`). The final, frozen-protocol-first run is published
separately at `examples/comparative_benchmark/real_agent_corpus/frozen_protocol/RAW_EVENTS.md`
and `examples/comparative_benchmark/frozen_protocol_r6/`.

Published in full, including nothing withheld -- there were no failures in this batch.
Agent identity for every event below: this session's own native tool-using agent (Claude
Sonnet 5 running inside Claude Code, session
`https://claude.ai/code/session_0154miaUnGA543JWmVrxqamk`), acting with a real Bash/Write/Read
tool surface, single-turn resource budget, no retries.

**P90-R6-IF1 correction** (Structural Advisor interim finding, comment 5715107317): every
real write below is now backed by a real, machine-verifiable
`tests.comparative_benchmark.agent_execution_receipt` -- a
`{output_path}.receipt.json` file alongside the corresponding output, binding the write's
own Agent identity, condition, task input, tool surface, resource budget, and a SHA-256
digest of the real output bytes, all independently re-derivable and re-checked from the real
bytes on disk. The `MANOSUBE_PRESENT` condition's own composer
(`tests/comparative_benchmark/real_agent_present_cycle.py`) resolves and verifies this
receipt -- it no longer performs the write itself via any callback.

## MANOSUBE_ABSENT condition

No Difference was raised, no Authority Decision was obtained, no Observation/Evidence/Reflow
wrapped either write below -- the agent acted directly, exactly as `TASK_CORPUS.md` defines
`MANOSUBE_ABSENT`.

### Task A (hash computation)

- Start: `2026-09-17T13:01:03.540796014Z`
- Command run: `printf '%s' 'MANOSUBE_PHASE21_ROUND6_TASK_A' | sha256sum | awk '{printf "%s", $1}' > examples/comparative_benchmark/real_agent_corpus/absent/task_a_output.txt`
- Raw stdout captured back: `b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8`
- End: `2026-09-17T13:01:07.593796545Z`
- Result: `SUCCESS`
- Independent re-check (run separately, after the fact, against the committed file): `printf '%s' MANOSUBE_PHASE21_ROUND6_TASK_A | sha256sum` reproduces the identical digest
  `b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8`.
- Receipt: `absent/task_a_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-35517C37C5F1C9804AE084AB163383C8A16CF82C66B5BF6E3C8CFCCD688A2BAC`.

### Task B (prime enumeration)

- Start: `2026-09-17T13:01:11.489090476Z`
- Command run: a short Python 3 one-liner (`[p for p in range(2, 51) if all(p % d for d in range(2, int(p**0.5)+1))]`, comma-joined) writing to
  `examples/comparative_benchmark/real_agent_corpus/absent/task_b_output.txt`
- Raw stdout captured back: `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47`
- End: `2026-09-17T13:01:11.509959344Z`
- Result: `SUCCESS`
- Independent re-check: the unique ascending prime list in `[2, 50]` is
  `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47` -- matches exactly.
- Receipt: `absent/task_b_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-3BF4443867EADEE2E222BA14BE2C4A766036BA1D5979F5C23E3942ABFF5B75BA`.

## MANOSUBE_PRESENT condition

Executed for real, both tasks, `CLOSED`, via the identical real-Agent mechanism as
`MANOSUBE_ABSENT` above -- this session's own genuine Bash/Write tool calls, directly, never
a Python function defined inside a test file and invoked by the test harness
(P90-R6-IF1 correction, Structural Advisor interim finding, comment 5715107317).

### Task A (hash computation) -- real event

- Start: `2026-09-17T13:34:29.067998918Z`
- Command run: `printf '%s' 'MANOSUBE_PHASE21_ROUND6_TASK_A' | sha256sum | awk '{printf "%s", $1}' > examples/comparative_benchmark/real_agent_corpus/present/task_a_output.txt`
- Raw stdout captured back: `b3148bae9d93ee08012f9b228b9bbe4bf9c4cfdec79c6615e5b6208e9ac1b3a8`
- End: `2026-09-17T13:34:29.074653177Z`
- Result: `SUCCESS`
- Receipt: `present/task_a_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-9BE848D16001A4C7BEAE894BAC0405943589929A2A1B0A87C0E2E20B265604B2`.

### Task B (prime enumeration) -- real event

- Start: `2026-09-17T13:34:33.319554047Z`
- Command run: the identical Python 3 one-liner as the `MANOSUBE_ABSENT` event above, writing
  to `examples/comparative_benchmark/real_agent_corpus/present/task_b_output.txt`
- Raw stdout captured back: `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47`
- End: `2026-09-17T13:34:33.334262772Z`
- Result: `SUCCESS`
- Receipt: `present/task_b_output.txt.receipt.json`,
  `receipt_id=AGENT-RECEIPT-414F2614D5BFBA9BA81180DC7CBF9DDD847A2D027458AABAA2E7083B8FEA90AC`.

Both real writes above are then wrapped by a real Difference -> Authority Decision -> Change
-> (the real Agent action above, resolved and verified via its receipt) -> Observation ->
Evidence -> Sufficiency -> Reflow lifecycle through this repository's own canonical
production route (`manosube_agent_civilization.difference`, `.authority`, `.change`,
`.observation`, `.evidence`, `.reflow`) -- never a hand-built substitute for any of those
records. The composer, `tests/comparative_benchmark/real_agent_present_cycle.py`, is a new,
independently-kept generalization of `tests/natural_cycle/proof.py`'s own audited one-shot
pattern (the repository's own
`PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true` convention: each phase/round keeps
its own fixture/composer pair rather than importing another's), split into
`begin_present_task` (before-Observation through Change) and `resolve_present_task` (receipt
verification through Reflow) so that the real Agent action happens, for real, strictly
between the two calls -- never inside either. `resolve_present_task` resolves and verifies
the receipt above; a receipt that fails any check (Agent identity, condition, task input,
tool surface, resource budget, or output digest) raises before any post-change Observation is
taken. Both real-agent outputs are byte-identical to the `MANOSUBE_ABSENT` outputs above
(`present/task_a_output.txt` == `absent/task_a_output.txt`;
`present/task_b_output.txt` == `absent/task_b_output.txt`), independently confirmed after the
fact -- the only difference between the two conditions is whether the identical real write
was wrapped by MANOSUBE's real lifecycle, exactly as `TASK_CORPUS.md` defines both
conditions. Both real transactions closed via this repository's own G1-G22 Closure gate
engine, real Reflow commit, and real Store transaction
(`tests/comparative_benchmark/test_real_agent_present_condition.py`, 3/3 passed, replaying
the real published receipts above into a disposable `tmp_path` without mutating any tracked
corpus artifact).

### Task A (hash computation) -- real identity ledger

| Record | id |
| --- | --- |
| `difference_id` | `D-4A36AD64C1749A18617665DDEB14FBD1F8F3055FA953A1EF11A5A71E19E0FE58` |
| `authority_decision_id` | `AUTH-DEC-2F68381494A20F851283F027B87A489BE3B768E5DC6F5E21AA932A3F3B2845DE` |
| `change_id` | `CHANGE-2FA752558E271D751741A294925BB943E78DD66C4FFEC2A38C5BE50541F8D313` |
| `evidence_sufficiency_id` | `EVID-SUFF-E878033BDCFE0BA5E4F14AD0DEFCCDB676B77DECB71287FED6D7F30168505549` |
| `closure_evaluation_id` | `D-CLOSE-EVAL-416397027CDD735ADE3C4BC78880405588587E7A32571A11E864048B6DBD2873` |
| `difference_lifecycle_event_id` | `D-EVT-255D1493D319E8A2461B6AAD77C381E70B4D0C114520BD07D447C074F0F20BEA` |
| `state_transition_ref.id` | `TX-C9C017836A4ABEBFBD0D0D0579BFBFA717FCFD38ABDF4E9A316499057F5CEAD6` |
| `final_terminal_status` | `CLOSED` |

### Task B (prime enumeration) -- real identity ledger

| Record | id |
| --- | --- |
| `difference_id` | `D-310B9FB9ECD3B84FA6B0E204B1B90346806C605D1C9976F1C83877CD883D10A2` |
| `authority_decision_id` | `AUTH-DEC-6FAAC0D0461C0C371B4B97708BD20B483486435B5E9D439BB607E7A8B1896C9B` |
| `change_id` | `CHANGE-F8F93F7EC2219293A58D1833ADC1F8B4F76526F47F06EA7F47DE70432174DF4C` |
| `evidence_sufficiency_id` | `EVID-SUFF-8E23D7D86AF260BD405AC1C89996BFECF0D0B66C7BE44249B0752A6FE4933366` |
| `closure_evaluation_id` | `D-CLOSE-EVAL-9B473995A344CA3D93CD0CD96D2854A133994E85FA708D90FF015D868703D570` |
| `difference_lifecycle_event_id` | `D-EVT-D86CFC3A1056B7E6E9F568B133BDDE68EB61CF309A301D7005D9B783956BBD9A` |
| `state_transition_ref.id` | `TX-F476931A78119AC30DC8FD8B4F4BBC39A620764D34E791D7466A74F4FBC90612` |
| `final_terminal_status` | `CLOSED` |

Both runs above are reproducible by running
`tests/comparative_benchmark/test_real_agent_present_condition.py` -- each test replays the
real receipt+output pair above into a fresh, disposable `FileStateStore` rooted outside the
repository working tree, so the ids above are deterministic given the pinned real receipt
inputs and fixed instants, but are not themselves committed anywhere durable by the test run;
they are recorded here as the public, durable evidence of this condition's real execution.

### MANOSUBE_PRESENCE_IS_THE_ONLY_TREATMENT_DIFFERENCE

- Identical Agent identity: this session's own native tool-using agent, both conditions.
- Identical task inputs: the literal string hashed for Task A and the `[2, 50]` range
  enumerated for Task B are identical in both conditions (`TASK_CORPUS.md`).
- Identical tool surface: Bash/Write/Read, both conditions -- the composer never grants the
  `MANOSUBE_PRESENT` condition a tool the `MANOSUBE_ABSENT` condition lacked, or vice versa.
- Identical resource budget: one real write per task, no retries, both conditions.
- Identical real output bytes: `present/task_{a,b}_output.txt` byte-equal to
  `absent/task_{a,b}_output.txt`, confirmed above.
- The only difference: whether a real Difference/Authority Decision/Change/Observation/
  Evidence/Reflow lifecycle wrapped the identical write (`MANOSUBE_PRESENT`) or did not
  (`MANOSUBE_ABSENT`).
