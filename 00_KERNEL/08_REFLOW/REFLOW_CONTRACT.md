# REFLOW CONTRACT — v0.1

```text
REFLOW APPLIES ADMITTED EVIDENCE TO STATE
REFLOW DOES NOT OBSERVE
REFLOW DOES NOT EXECUTE CHANGE
REFLOW DOES NOT INVENT EVIDENCE
REFLOW DOES NOT WEAKEN CLOSURE POLICY
```

Reflowは、Evidenceを保存するだけの終端処理ではない。

```text
REFLOW
= EVIDENCE EVALUATION
+ CLOSURE EVALUATION
+ ATOMIC STATE TRANSITION
+ LINEAGE APPEND
+ MATERIALIZED STATE UPDATE
+ NEXT OBSERVATION DERIVATION
```

（`KERNEL_INDEX.md` §4.8。以下、この定義の各項をどの owner が満たすかを固定する。）

---

# 1. Reflowの唯一のAuthority境界

```text
CANONICAL_REFLOW_OWNER_COUNT=1
CANONICAL_STATE_OWNER_COUNT=1
STATE_STORE_WRITE_OWNER_COUNT=1
DIFFERENCE_CLOSURE_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

Reflowは、State N から State N+1 への**唯一の**canonical transitionである。State Storeは
唯一のwrite/persistence owner のまま変わらず、Reflowはそれを**呼び出す**側であって、
第二のwrite pathを作らない。

```text
REFLOW MINTS      Closure Evaluation（Differenceが所有するschemaへ）
                  State Transition（Stateが所有するschemaへ、store.commit()経由）
                  Material Contradiction（本Contractが新規に所有する最小schema）
                  Difference Lifecycle Event（Differenceの既存owner関数を呼び出して merge）

REFLOW DOES NOT MINT
                  Observation, Difference, Authority Decision, Change, Evidence
                  （これらはすべて既存canonical ownerの出力を再生成なしに消費する）
```

## 1.1 Closure Evaluationの所有権

`difference/lifecycle.py`の`closure_evaluation_input_errors`と
`closure_evaluation_binding_errors`のdocstringは、この境界を明示的に述べている。

```text
"A Closure Evaluation is provenance a later canonical owner produces;
 this phase does not execute one and claims nothing about how it was decided."

"The CLOSED Reflow commitment window is not decided here: Reflow is a later
 element with no schema in v0.1, and its own owner enforces it."
```

Differenceは`closure_policy`のsemantics（gate名、lifecycle legality、Evaluationの
binding整合性）を所有し続ける。**Reflowはその later owner であり、Closure Evaluationの
唯一のproducer**である。DifferenceはEvaluationを検証するが生成しない。この分割は
Phase 6でEvidenceがSufficiency Resultをproduceし、Differenceがそのschemaをownし続けた
のと同型である。

## 1.2 `reflow_transitions` predecessor sectionの解決

`difference/graph.py`の`RESOLVABLE_KINDS`は次を同一sectionへ写像する。

```text
"reflow_transition":  "reflow_transitions"
"state_transition":   "reflow_transitions"
```

これは、DifferenceがcarryするReflow provenanceの実体が**Stateの既存
`state_transition.schema.json` record**であることを意味する。Reflowは、この
lineage eventのための第二のschemaを作らない。`01_SCHEMA/state/state_transition.schema.json`
をそのまま参照kind`state_transition`で引用する。

---

# 2. Canonical input set

Reflow requestは次を最低限持つ。

```text
project_id
current_state              -- store.load_current()の戻り値そのもの、caller提示値ではない
difference_bundle          -- derive_differences()の実出力
evidence_requests          -- derive_evidence()へ渡す実request（recordではない）
sufficiency_request        -- evaluate_sufficiency()へ渡す実request
closure_policy              -- Differenceが emit した実 policy record
authority_decision          -- Change-bound routeのみ。observation-onlyではnull
change_request               -- Change-bound routeのみ
reflow_instant               -- admitted input。時計を読まない
```

`current_state`はcallerの自己申告値を信頼せず、`store.load_current(project_id)`を
呼んで再取得する。同様にDifference・Evidence・Sufficiencyは、それぞれの既存canonical
ownerへ**request**として渡し、返ってきたrecordだけを使う。record を直接受け取る経路は
存在しない——これはPhase 5のP1、Phase 6のEvidence forgery防止と同じ理由による
provenance-by-reproductionである。

## 2.1 `authority_ref`

```text
authority_ref = null    -- Change-freeな観測のみのReflow
authority_ref = {...}   -- Change-boundなReflow。derive_change()が返した決定を束縛
```

`difference_lifecycle_event.schema.json`の`authority_ref`は`oneOf: [null, reference]`で
既にnullableである。Observation-only routeのためにAuthority Decisionを発明する必要は
ない。

---

# 3. Decision/Candidate と Committed Receiptの区別

```text
CLOSURE EVALUATION CANDIDATE_CLOSURE   result=SATISFIED
+ CURRENT REVISION = EXPECTED REVISION
+ ATOMIC STATE TRANSITION
+ LINEAGE APPEND
+ MATERIALIZED STATE UPDATE
→ DIFFERENCE CLOSED
```

`SATISFIED`はcommit前の**candidate**である。Atomic Reflowが成功するまで、Differenceの
canonical statusはOPENのままである。commitが失敗すれば、古いStateとDifference statusが
canonicalであり続ける。

```text
SUFFICIENT != CLOSED
SATISFIED != COMMITTED
```

この二つの不等式は、Evidence SufficiencyとClosure Evaluationのどちらの結果も、それ単独
ではDifferenceを閉じないことを言う。閉じるのは、Reflowの単一原子的commitだけである。

---

# 4. State N → State N+1

```text
next_revision = current.state_revision + 1
next_previous_fingerprint = current.semantic_fingerprint
next_semantic_fingerprint = fingerprint(next_semantic_state)   -- 再計算、信頼しない
```

## 4.1 Reflowが書き換えるsemantic_stateの範囲

`semantic_state`のdomain（`project`/`objective`/`repository`/`requirements`/`code`/
`tests`/`runtime`/`infrastructure`/`deployment`）は`claims: {}`を伴う不透明な構造であり、
Difference の `subject`（自由文字列、grammarなし——`normalized_target_state.subject`は
`{"type": "string", "minLength": 1}`のみ）をこれらdomainのどのclaim keyへ書き込むかを
決定するcanonical mappingはKernel全体のどこにも存在しない。

Reflowはこのmappingを**発明しない**。v0.1のReflowが書き換えるのは、Kernel自身の
bookkeeping fieldに限る。

```text
書き換える       open_differences, active_changes, evidence,
                unresolved_contradictions, reflow_state, lineage, authority
書き換えない     project, objective, repository, requirements, code, tests,
                runtime, infrastructure, deployment の claims/status/identity_refs
```

Domain claimsへの投影は、`subject`→domain-path grammarをKernelが確立した後の、
本Issueの範囲外の作業である。Issue #39は「Do not implement Phase 8's full
natural-cycle acceptance」を明示的に禁じており、業務claims投影はまさにその一部である。

## 4.2 `lineage_head_ref`

```text
project_state.lineage_head_ref = {"kind": "state_transition", "id": <transaction_id>}
```

`transaction_id`はReflowが決定的に導出する。次節で定義する。

---

# 5. `state_transition`のtransaction identity

```text
transaction_id = "TX-" + sha256(canonical({
  project_id, difference_id, closure_evaluation_semantic_fingerprint,
  evidence_sufficiency_id, expected_revision, reflow_instant
})).hexdigest().upper()
```

`reflow_instant`をidentityへ含める。理由は、`store.commit()`の`TransactionConflictError`
判定が**event全体**のcanonical bytes比較であり、`state_transition.committed_at`が
その一部だからである。

```text
IDEMPOTENT REPLAY
= 同じ commit instant を admitted input として再提示する呼び出し
= 同じ transaction_id
= 同じ canonical event
= store.commit() が既存recordを返す（二重commitしない）
```

Reflowは時計を読まない。`reflow_instant`はEvidenceの`recorded_at`、Sufficiencyの
`evaluation_instant`と同じ扱いのadmitted inputであり、再試行するcallerはこれを
verbatimに再提示する責任を持つ。callerが再試行のたびに異なる値を提示すれば、
`TransactionConflictError`が正しく発生する——これは欠陥ではなく、
「同じcommitを違う入力で二回主張してはならない」という保証そのものである。

---

# 6. Atomicity, CAS, Recovery, Replay — すべてState Storeを再利用する

```text
ATOMIC_REFLOW_PRECONDITIONS_PASS (G20)
→ store.commit(project_id, expected_revision, expected_fingerprint,
                next_state, transition)
```

`FileStateStore.commit()`は既に次を提供する（`store/file_store.py`）。

```text
CAS                     expected_revision/expected_fingerprintの一致を要求
IDEMPOTENT REPLAY       同一transaction_idの二回目呼び出しは既存stateを返す
TRANSACTION CONFLICT    同一transaction_id・異なるpayloadを拒否
ATOMIC COMMIT           journal → COMMIT_INTENT → append → current replace → COMMITTED
CRASH RECOVERY          recover()がCOMMIT_INTENTかつCOMMITTED未達のjournalを完了させる
RECONSTRUCTION          reconstruct()がlineageの先頭から再生し、contiguityを検証する
```

Reflowはこれらを**再実装しない**。Reflowの責務は、`next_state`と`transition`を正しく
**導出する**ことであり、それをatomicに書き込むことではない。書き込みは既存owner一つに
委ねる。

---

# 7. 各resultの取り扱い

```text
SUFFICIENT       -> Closure Evaluation候補が組み立てられる。commitが成功して初めてCLOSED。
INSUFFICIENT     -> Differenceは開いたまま。Evidence・失敗理由がStateへreflowされる。
UNKNOWN          -> 同上。決着していない観測として保持し、SATISFIEDへ昇格しない。
STALE            -> Closure Evaluationはevaluation_expires_atを超えた時点でSTALE。再評価要求。
FAILED           -> 第31条の還流対象。CLOSEDにならない。PR #38で確立したFAILED経路を、
                    State N+1まで保存する。
EMPTY            -> NO_RESULTから推論しない。証明済み空集合として区別を保つ。
BLOCKED          -> reason・resolution/next-observation lineageを伴ってreflowする。
INCOMPLETE       -> 未決着として保持。
CONTRADICTED     -> 第33条。矛盾するEvidenceを削除・上書き・平均化せず、
                    material_contradiction recordとしてStateへ保持する。
RETAINED         -> BLOCKEDと同型の扱い。
CLOSED           -> Atomic Reflowが成功した場合のみ。
REOPENED         -> 既存のClosure EvaluationとEvidenceを削除せず、CLOSED→REOPENEDを追記する。
```

---

# 8. Reopen

```text
CLOSED → REOPENED
```

は、旧いClosure Evaluationとその証拠づけたEvidenceを**削除しない**。新しい
lifecycle eventが追記され、旧いEvaluationは`evaluations`section内に
provenanceとして残る。`difference/lifecycle.py`の`is_legal_transition`が
この遷移の合法性を判定する——Reflowはこの判定を再実装しない。

---

# 9. Phase 8以降への境界

```text
REFLOW cannot redefine EVIDENCE
EVIDENCE cannot grant AUTHORITY
```

Reflowが証明するのは、admitted EvidenceがStateへ正しく適用されたことだけである。
次を主張しない。

```text
ONE_FULL_NATURAL_CYCLE_PASS=false
PHASE_8_VERTICAL_PROOF_COMPLETE=false
CHANGE_EXECUTOR_IMPLEMENTED=false
RUNTIME_PROVEN=false
INDEPENDENT_VERIFICATION_IMPLEMENTED=false
```

Phase 7が生成するのは、Phase 8 Vertical Proofが後で消費する**正確な**canonical
input（committed State N+1、closure_evaluation、state_transition、
material_contradiction）である。Phase 8のfixture bindingやnatural-cycle受入判定
そのものは、本Issueの範囲外である。

---

# 10. 本Work Unitが主張しないもの

`KERNEL_INDEX.md` §4.8は`08_REFLOW/`に五文書を挙げる。本Work Unitは一文書を提出する。

```text
REFLOW_CONTRACT.md      CLAIMED（本文書。§1〜9が五文書の内容を統合する）

STATE_TRANSITION.md     NOT CLAIMED — state_transition.schema.jsonの契約はStateが所有する。
                         Reflowは§5でtransaction identityの導出規則だけを追加する。
ATOMIC_COMMIT.md        NOT CLAIMED — atomicityはFileStateStore.commit()が実装済み。
                         §6がReflowからの利用契約を記す。
RECOVERY_CONTRACT.md    NOT CLAIMED — recover()/reconstruct()はStateが所有する。
LINEAGE_INVARIANT.md    NOT CLAIMED — R-001〜R-005として`KERNEL_INVARIANTS.md`が
                         既に規定し、§6・§8がその実行形を記す。
```

`NOT CLAIMED`は不足であり、達成ではない。文書を分割しなかったのは、分割すれば
Stateが既に所有する契約を別の場所で言い直すことになり、それ自体が第二ownerの
記述になるためである。

---

# 11. Closure Evaluation producer（G1〜G22）の実装範囲宣言

`src/manosube_agent_civilization/reflow/closure.py`が`§1.1`で述べたClosure Evaluation
producerである。G1〜G22の全ゲートを実際の入力に対する real check として実装するが、
`00_KERNEL/04_DIFFERENCE/CLOSURE_POLICY.md`が定義する範囲のうち、次の二点は本Work Unitが
実装しない。これは省略の見落としではなく、実装した範囲より小さいことを明示するための
宣言である。`NOT CLAIMED`は§10と同じ意味で使う。

*Phase 7構造レビュー是正（PR #40, findings F1〜F8・G19、`BOUND_HEAD=
9459af827b65ca18af07cf040b401e58e0843f98`）でG18・G21は完全実装へ、G19はID union
までの部分実装へ、それぞれ更新された。以下は是正後の現状であり、下の版と混同しては
ならない。*

```text
G9  (required_observation_scope ≠ null)                  NOT CLAIMED
G19 (v0.1 Mandatory Invariant Registry auto-derivation)  NOT CLAIMED（部分実装、is対象拡大）
```

**G9。** `CLOSURE_POLICY.md`は`required_observation_scope ≠ null`の場合に
`resolved_observation_scope`のcontent-addressed digest profileを要求する。本Work Unitは
`required_observation_scope = null`の経路だけを実装する。Policyがnull以外を宣言した場合、
G9はfail closed（`FAIL`、`result`は`BLOCKED`へ写像）であり、無実装の第二scope解決機構で
黙って評価しない。

**G19（是正後）。** `APPLICABLE_V0_1_MANDATORY_INVARIANT_REGISTRY`の完全な仕組み——
`KERNEL_INVARIANTS.md``# 16. v0.1 Mandatory Gate`を`kernel_source_ref_evaluated`の
`commit_sha`/`tree_sha`へexact Git blob provenanceで結合し、各Invariantの定義blockから
個別の`invariant_definition_sha256`を再計算する仕組み——は、それ自体が本Work Unitと
同等規模の独立したsub-systemであり、実装しない。是正で実装したのは、
`reflow/invariant_registry.py`が`evidence/levels.py`と同じ「pin-and-prove」方式で
`# 16.`節の`ID PASS`行から抽出したid集合（`P-003`を除く）を`expected_g19_invariant_ids()`
として保持し、`_evaluate_g19`がこれをClosure Policyの`required_invariants`へ**additive**
union することである（`required_invariants`が空でもG19は空集合上でPASSしない）。
mandatory-only の各idは`(kind, id)`一致とbinding上の非空な
`invariant_definition_sha256`の存在だけを要求し、その値が該当Invariantの定義blockの
digestと一致することまでは独立検証しない——これが残るgapである。
`tests/contract/reflow/test_invariant_registry_source.py`がpinしたid集合と
実文書の再parseが一致することを証明する。

**G21（是正後、実装済み）。** mandatory X-003 completion Claimはfixed closed-form
constant（`subject_type`・`subject_ref`・`claim`payloadがPolicy文書に固定されている）
であるため、その識別子は`difference/identity.py`の`completion_claim_id`で計算し、
Policyが何を宣言していてもG21の期待集合へ常に含める。是正前は、供給された
`candidate_claim_evaluation_binding`自身の`evaluation_status`をそのまま信頼していた。
是正後は`reflow/claims.py`の`reconstruct_claim_status`が`candidate_claim_evaluation_event`
のappend-only seriesを`revision 0`からbindingの宣言するheadまで実際に再構築し
（content-address自己整合性、contiguity、Difference/Claim/candidate一致を検証）、
その**再構築されたhead eventの`evaluation_status`**をG21の判定へ用いる。bindingの
`evaluation_status`フィールド自体はもはや信頼されない。

**G18（是正後、実装済み）。** `CLOSURE_POLICY.md`第8節はAtomic Reflow commit直前に
`evaluation_expires_at`を再検証することを要求する（Evaluation時点の検証とは別の、
二回目の検証）。是正前は`evaluation_expires_at`が常に`null`で、Evaluation時点の検証も
実質存在しなかった。是正後、`closure.py`は`maximum_evidence_age`が有限のとき、
Evidence Sufficiencyが再現した実際のEvidence記録群のうち最も古い`recorded_at`から
`evaluation_expires_at`を導出する（wall clockは一切読まない）。`reflow/commit.py`の
`commit_reflow`が、この`evaluation_expires_at`を明示的な`reflow_instant`と
commit直前に再検証し、超過していれば`StaleReflowError`でfail closedする——これが
RF6（Atomic State commit）の責務としての実装である。

これら二点はいずれも、Closure Evaluationのgate_resultsとresultを偽らない——宣言していない
機構を動かした「ふり」をして`PASS`を返すことは一つもない——という一点によって、
このKernelがGate 1〜22で守ろうとしている性質（`UNKNOWN_IS_PASS=false`）と両立している。
狭い範囲を確定的にfail closedで検証することと、広い範囲を虚偽にPASSさせることは別物であり、
本Work Unitは前者だけを行う。
