# EVIDENCE LEVELS — v0.1

```text
EVIDENCE COUNT != EVIDENCE STRENGTH
TEST PASS      != RUNTIME PROVEN
DECLARATION    != OBSERVATION EVIDENCE
```

---

# 1. Scale（憲法語彙）

第29条および`COMPLETION_SEMANTICS.md`第3章が同一のclosed ordered scaleを宣言する。

```text
E0 = 宣言のみ
E1 = 静的確認
E2 = 単体テスト
E3 = 統合テスト
E4 = 自然経路実行
E5 = 対象Runtime実証
E6 = 反復・独立Runtime実証
```

順序が意味である。`E0 < E1 < E2 < E3 < E4 < E5 < E6`。

```text
SCHEMA_VOCABULARY=E0..E6
```

v0.1のschemaはこの七語をすべて保持する。語彙を狭めることは憲法を書き換えることである。

---

# 2. Phase 6が導出できる範囲

```text
PHASE_6_DERIVABLE_LEVELS=E0..E3
CALLER_CLAIMED_E4_E5_E6=REFUSED
POLICY_REQUIRING_E4_E5_E6=INSUFFICIENT
```

E4〜E6について、凍結Kernelは**名称と禁止**しか持たない。`E-005`は過大申告を禁じるが、
何をもってE4が成立するかを述べない。加えてv0.1にRuntimeは存在せず、
`CLOSURE_POLICY.md`は`independent_verification_required`を`false`に固定し
`verification_independence_ref`を常にnullとするため、E6の言う「独立」は観測対象として
存在しない。

Phase 6がここで述語を発明することは、Evidenceが「Runtime実証とは何か」を決めることであり、
`E-005`が反対側から記述している欠陥そのものである。

したがってE4〜E6は**refuse**する。Policyが要求した場合は`INSUFFICIENT`として保持し、
Policyを弱めない。E4〜E6は将来のVertical Proof、Runtime、Independent Verificationが
述語を定義した時点で到達可能になる。

---

# 3. Method class → claimed level

Evidence levelはcallerのlabelから読まない。構造化されたObservation methodのclassから
導出する。requestには`evidence_level`を渡すkeyが存在しない。

```text
DECLARATION                          E0
STATIC_INSPECTION                    E1
UNIT_TEST                            E2
INTEGRATION_TEST                     E3
NATURAL_PATH_EXECUTION               E4   REFUSED
TARGET_RUNTIME_PROOF                 E5   REFUSED
REPEATED_INDEPENDENT_RUNTIME_PROOF   E6   REFUSED
```

三つの導出不能classは、省略ではなく**存在**させる。省略すれば「そんなmethod classはない」
という無内容な拒否になり、なぜ拒否されたかがcallerに伝わらない。

---

# 4. Structural ceiling（`E-005`の計算形）

Method classは**主張**である。recordが実際に何を含むかが**上限**を決める。

```text
completed attempt が 1 件以上      → 上限 E3
artifact reference のみ            → 上限 E1
どちらも無い                        → 上限 E0

evidence_level = min(claimed, ceiling)
```

`completed attempt`とは`result ∈ {COMPLETE, EMPTY}`のattemptである。BLOCKEDとFAILEDは
対象へ到達しておらず、PARTIALは終わっていない。走らなかったtestはtestではない。

E2とE3が同じ床を共有するのは、凍結Kernelが両者を「何を動かしたか」で区別しており、
Evidenceにはその差を観測する手段がないからである。上限は両方を許し、method classが
下向きにのみ決める。

上限は**下げるだけ**であり、上げない。上げる規則は、記録内容を超える主張を作る規則である。

---

# 5. Source resolution（G12）

`CLOSURE_POLICY.md` §5は、Evidence levelをcontent-addressed blob refで
`00_KERNEL/COMPLETION_SEMANTICS.md`から解決することを要求する。

純粋関数はfileを開けない。したがって義務を二つに分割し、**両方**を検査可能にする。

```text
levels.EVIDENCE_LEVEL_SCALE            pinned     → 生きた文書と等しいことをrepository testが証明
sufficiency.evidence_level_scale_...   addressed  → 別のscaleを名指すrefをengineが拒否
```

片方だけでは成立しない。文書と照合されないpinは漂流し、addressされない文書はPolicyの下で
差し替えられる。

Sufficiency requestは次を必須とする。

```text
completion_semantics_ref = {
  kind: git_blob
  repository, commit_sha, blob_sha
  path: "00_KERNEL/COMPLETION_SEMANTICS.md"
  evidence_level_scale_sha256
}
```

`path`が別文書を指す場合、`evidence_level_scale_sha256`が適用中のscaleと一致しない場合、
いずれもfail-closedで拒否する。
