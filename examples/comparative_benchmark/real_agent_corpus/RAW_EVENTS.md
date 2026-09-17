# Round 6 real-Agent corpus -- raw events

Published in full, including nothing withheld -- there were no failures in this batch.
Agent identity for every event below: this session's own native tool-using agent (Claude
Sonnet 5 running inside Claude Code, session
`https://claude.ai/code/session_0154miaUnGA543JWmVrxqamk`), acting with a real Bash/Write/Read
tool surface, single-turn resource budget, no retries.

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

### Task B (prime enumeration)

- Start: `2026-09-17T13:01:11.489090476Z`
- Command run: a short Python 3 one-liner (`[p for p in range(2, 51) if all(p % d for d in range(2, int(p**0.5)+1))]`, comma-joined) writing to
  `examples/comparative_benchmark/real_agent_corpus/absent/task_b_output.txt`
- Raw stdout captured back: `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47`
- End: `2026-09-17T13:01:11.509959344Z`
- Result: `SUCCESS`
- Independent re-check: the unique ascending prime list in `[2, 50]` is
  `2,3,5,7,11,13,17,19,23,29,31,37,41,43,47` -- matches exactly.

## MANOSUBE_PRESENT condition

Executed for real, both tasks, `CLOSED`. The identical two tasks above are performed by the
identical agent identity, wrapped by a real Difference -> Authority Decision -> Change ->
(real Agent action) -> Observation -> Evidence -> Sufficiency -> Reflow lifecycle through
this repository's own canonical production route (`manosube_agent_civilization.difference`,
`.authority`, `.change`, `.observation`, `.evidence`, `.reflow`) -- never a hand-built
substitute for any of those records. The composer,
`tests/comparative_benchmark/real_agent_present_cycle.py`, is a new, independently-kept
generalization of `tests/natural_cycle/proof.py`'s own audited one-shot pattern (the
repository's own `PHASE_8_FIXTURE_BINDING_NE_PHASE_20_FIXTURE_BINDING=true` convention: each
phase/round keeps its own fixture/composer pair rather than importing another's), with one
load-bearing structural addition: between the Change record's derivation and the post-change
Observation, the composer calls a caller-supplied `perform_real_change` callback -- the real
Agent action itself, identical to the `MANOSUBE_ABSENT` write above -- and only then takes
the post-change Observation, of the real, now-changed bytes on disk
(`examples/comparative_benchmark/real_agent_corpus/present/STATUS.md`, freshly read and
SHA-256-digested at each Observation, never a pre-baked fixture literal). Both real-agent
outputs are byte-identical to the `MANOSUBE_ABSENT` outputs above
(`present/task_a_output.txt` == `absent/task_a_output.txt`;
`present/task_b_output.txt` == `absent/task_b_output.txt`), independently confirmed after the
fact -- the only difference between the two conditions is whether the identical real write
was wrapped by MANOSUBE's real lifecycle, exactly as `TASK_CORPUS.md` defines both
conditions. Both real transactions closed via this repository's own G1-G22 Closure gate
engine, real Reflow commit, and real Store transaction (`tests/comparative_benchmark/
test_real_agent_present_condition.py`, 2/2 passed).

### Task A (hash computation) -- real identity ledger

| Record | id |
| --- | --- |
| `difference_id` | `D-F7FA5F56D42C112881BBFCDBB100828BD85B7D130317637E98354EFBEB662BEA` |
| `authority_decision_id` | `AUTH-DEC-BB3CB4B4BCF5E97C657A9A9740AB4FAC3B360E862922D8A6D16AE0E192FA5EF5` |
| `change_id` | `CHANGE-7F8FA99EB3E4256B47E28286AE2FA73BD158186DE9C4C8AA6D14C12DB7A6CE69` |
| `evidence_sufficiency_id` | `EVID-SUFF-2F1F2FDD9AEC838D077902B83CC7E5EC2BE390B175CA2E0AB3AB7AD3A632A36F` |
| `closure_evaluation_id` | `D-CLOSE-EVAL-E9F26D959D4A6658D253455AC41DED13C91C03752FBB0BBCF78661710B922445` |
| `difference_lifecycle_event_id` | `D-EVT-D34411A746841B302076C69572ACA56E9B8696099507B067B1D95D0ED60134FC` |
| `state_transition_ref.id` | `TX-28CBEA5F1F54B0ABEDC8EEA17FEB53D851EE6A080FEDE927DD68F97BB8377195` |
| `final_terminal_status` | `CLOSED` |

### Task B (prime enumeration) -- real identity ledger

| Record | id |
| --- | --- |
| `difference_id` | `D-E2C60B5200BCF97A243711766C8EE6023888F603C23A44E4A1A230A9F4EC03BC` |
| `authority_decision_id` | `AUTH-DEC-EC4A0C99038681AA88FC2BEF7E123ADDEC7869093215B200A80EFA4069DBAA59` |
| `change_id` | `CHANGE-76D939ACF27CD05D0BB3C04437C0DBE89F2187E4177FB6D9803DF4F7197D7441` |
| `evidence_sufficiency_id` | `EVID-SUFF-573AF6638B701A622F6E404BE3105DB1B7375BA6EF393DC9817AE99BE732128E` |
| `closure_evaluation_id` | `D-CLOSE-EVAL-80E429E1BA0DF6B655FE6406BF8C5C950D47E960348E3F4F143087986EF37601` |
| `difference_lifecycle_event_id` | `D-EVT-A5C7E7A2B8F4F4C78BF2A3F52823DC983AD95A6CC731DEF37D5E3D0E2F31965E` |
| `state_transition_ref.id` | `TX-E191238921533EECA30312FF8C56DB247CDFE9B2088277BA2BC70866A40C1725` |
| `final_terminal_status` | `CLOSED` |

Both runs above are reproducible by running
`tests/comparative_benchmark/test_real_agent_present_condition.py` -- each test uses a fresh,
disposable `FileStateStore` rooted outside the repository working tree, so the ids above are
deterministic given the pinned `TASK_CORPUS.md` inputs and fixed instants, but are not
themselves committed anywhere durable by the test run; they are recorded here as the public,
durable evidence of this condition's real execution.

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
