# EVIDENCE SUFFICIENCY — v0.1

```text
DIFFERENCE OWNS   Closure Policy schema
                  Evidence Sufficiency Result schema
                  Difference Closure

EVIDENCE OWNS     Sufficiency Result production
```

---

# 1. 所有権境界

この分割は本Work Unitの設計判断ではない。凍結ツリーが既にそう述べている。

```text
01_SCHEMA/difference/closure_policy.schema.json              存在する（Difference所有）
01_SCHEMA/difference/evidence_sufficiency_result.schema.json 存在する（Difference所有）
difference/engine.py                                          結果を carry する。mint しない
ADR-0009                       evidence_sufficiency_results = NOT CLAIMED / LATER PHASE
```

producerが存在しなかった。Phase 6がそのproducerである。

```text
EVIDENCE_OWNS_SUFFICIENCY_PRODUCTION=true
EVIDENCE_OWNS_DIFFERENCE_CLOSURE=false
INDEPENDENCE_RECORD_PRODUCED_IN_PHASE_6=false
VERIFICATION_INDEPENDENCE_REF=null
E6_REACHABLE_IN_PHASE_6=false
```

第二のClosure Policy、第二のsufficiency schema、第二のDifference Closure ownerを作らない。
生成されたrecordはDifference所有のschemaでvalidateし、Difference所有のsection
`evidence_sufficiency_results`（key: `evidence_sufficiency_id`）へそのまま載る。

---

# 2. 本モジュールが決めること／決めないこと

決めるのは四つだけである。

```text
投入された全 Evidence がこの Difference の Evidence か   ← exact binding
Evidence が存在するか
最弱の Evidence が Policy の床以上か
すべての Evidence が Policy の age 上限内か（admitted instant 基準）
```

第一項が欠けると、Differenceを名指すものが三つあって、それらを一致させるものが何も無い
状態になる。

```text
Difference A の Evidence + Difference B の Policy → Difference B が SUFFICIENT
```

Evidence recordは自らが導出されたDifferenceを持つ（`EVIDENCE_CONTRACT.md` §1A）。
request・Policy・全Evidence recordの三者を一つのidentityへ固定する。

決めないものを、黙って飛ばすのではなく**名指す**。

```text
NOT_EVALUATED_HERE = required_claims
                     required_invariants
                     required_observation_scope
                     allowed_terminal_states
                     contradiction_policy
                     reopen_conditions
```

これらはDifferenceのClosure gateである。

```text
SUFFICIENT != CLOSED
```

`not_evaluated_here`は戻り値に含める。callerがこの境界を信用に基づいて受け取る必要はない。

---

# 3. Policy admission

Policyは`04_DIFFERENCE/`所有のschemaでvalidateし、Difference所有の
`closure_policy_semantic_errors`をそのまま呼ぶ。`independent_verification_required=true`は
そのschemaが（Phase 6ではなく）拒否する。

さらに`closure_policy_id`をPolicyの**内容から**再計算する。

```text
policy_semantic_fingerprint   再計算は Difference の Policy owner が行う
closure_policy_id             再計算は本モジュールが行う（owner が検査しない半分）
```

二つで一つである。addressを再計算しなければ、callerは`minimum_evidence_level`を下げ、
保存済みIDを保ったまま、誰も批准していない床を評価させられる。
一方、fingerprintを本モジュールが二重に比較しても、それは決して失敗しない検査になる。
**失敗しえない検査は、保護に見えて保護しない。**

---

# 4. 四値と reason codes

Difference所有のresult schemaは四値を持つ。

```text
SUFFICIENT | INSUFFICIENT | UNKNOWN | STALE
```

これを広げることは第二のownerを作ることである。したがってEMPTY、BLOCKED、FAILED、
UNKNOWN、UNOBSERVED、INCOMPLETE、CONFLICTED、absence、stalenessの区別は、canonical record
の**傍らに**`reason_codes`として保持する。

```text
SUFFICIENT
EVIDENCE_ABSENT
EVIDENCE_LEVEL_BELOW_MINIMUM
EVIDENCE_LEVEL_UNREACHABLE_IN_PHASE_6
EVIDENCE_AGE_EXCEEDED
EVIDENCE_FUTURE_DATED
EVIDENCE_STATUS_EMPTY
EVIDENCE_STATUS_INCOMPLETE
EVIDENCE_STATUS_UNKNOWN
EVIDENCE_STATUS_UNOBSERVED
EVIDENCE_STATUS_BLOCKED
EVIDENCE_STATUS_FAILED
EVIDENCE_STATUS_INVALID
EVIDENCE_STATUS_CONFLICTED
```

何も区別を保存しなければ、`NO_RESULT != PROVEN_ABSENCE`は既に崩れている。

## 4.1 優先順（fail-closed）

```text
1  age 違反 / future-dated                                        → STALE
2  level 不足 / 到達不能 / Evidence 不在 / BLOCKED / FAILED
   / INVALID / CONFLICTED                                         → INSUFFICIENT
3  INCOMPLETE / UNKNOWN / UNOBSERVED                               → UNKNOWN
4  上のいずれでもない                                              → SUFFICIENT
```

段2と段3の分離が本質である。段2は「観測した上で足りない」、段3は「観測が決着していない」
である。段3をINSUFFICIENTと報告することは、観測されていない否定の主張になる。

`EMPTY`は降格しない。完全に列挙された空はひとつの完了した観測であり、それがTarget
Satisfactionを満たすかはDifferenceの問いであって本モジュールの問いではない。区別は
reason codeで保存する。

---

# 5. 強度（件数で補わない）

```text
effective_level = weakest(levels of the required evidence)
```

主張は、それが依拠する最弱のEvidenceの強さしか持たない。弱いEvidenceを積み増しても床は
上がらない。`CLOSURE_POLICY.md` §5「要求level未満のEvidenceを件数で補ってはならない」の
実行形である。

---

# 6. Age（admitted instant、時計を読まない）

```text
EVALUATION_INSTANT=ADMITTED_INPUT
CLOCK_READ_IN_ENGINE=false

maximum_evidence_age = null  → 追加の age 上限なし
maximum_evidence_age ≠ null  → 0 <= evaluation_instant - evidence.timestamp <= max_age
```

単位はSI second、非負JSON integer。負の差（Evidenceが評価より後の日付）はageではなく
`EVIDENCE_FUTURE_DATED`であり、`STALE`とする。

判定は**正確なinterval**で行う。整数へ丸めてから比較してはならない。`int()`はゼロ方向へ
切り捨てるため、freshness gateが存在する理由そのものである境界を失う。

```text
int(0.5秒 未来)          → 0 → future-dated にならない
int(0.5秒 経過), max=0   → 0 → age 超過にならない
```

整数ageは報告値としてのみ用い、判定には用いない。

時計を読めば、freshnessの判定はreviewerが検証できない判定になる。再現不能な検査は検査で
はない。

---

# 7. Evidence の供給形式

Sufficiency requestはEvidence **record**を受け取らない。Evidence **request**を受け取り、
`derive_evidence`で生成する。理由は`EVIDENCE_CONTRACT.md` §4と同一である。合成されたrecord
は自分自身とだけ整合しうる。偽造Evidenceの上のsufficiency判定は、偽造についての判定である。
