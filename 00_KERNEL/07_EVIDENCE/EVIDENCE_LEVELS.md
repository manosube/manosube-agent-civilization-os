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
PHASE_6_DERIVABLE_LEVELS=E0..E1
CALLER_CLAIMED_LEVEL=IMPOSSIBLE
POLICY_REQUIRING_E2..E6=INSUFFICIENT
```

Q2-Aは「E0〜E3を**構造的証明から**導出し、caller labelから導出しない」ことを要求する。
凍結ツリーを両条件で読むと、導出可能なのは**E0とE1**である。

E2（単体テスト）とE3（統合テスト）を判定するには「testが実行された」ことを知る必要がある。
凍結ツリーはそれを記録しない。

```text
observation_method.schema.json
  procedure_kind        {"const": "CANONICAL_OBSERVER"}
  normalization_profile {"const": "FIXTURE-0.1"}
```

canonical methodは一種類しかない。したがってE1・E2・E3を今日区別できる唯一の手段は、
callerに「どれだったか」を主張させることであり、それが本Phaseで除去した経路そのもので
ある。`E-005`が反対側から記述している欠陥でもある。

E4〜E6については既述のとおり述語が存在せず、v0.1にRuntimeも独立検証者も存在しない。

したがってE2〜E6を同一の理由で refuse する。これはQ2-AをE4〜E6について導いた推論を、
証拠が実際に尽きる位置へ適用した結果であり、最初に気づいた位置に留めた結果ではない。
語彙E0..E6はschemaに保持し、Policyは弱めず`INSUFFICIENT`として保持する。拒否は
「何が存在すれば到達可能か」を述べる。

---

# 3. 導出規則

Evidence requestには、levelを渡すkeyも、method classを渡すkeyも**存在しない**。

```text
E1  Observation Engine が自らの宣言Scopeを完全に観測したと判定し
    （status ∈ {COMPLETE, EMPTY}）、かつ content-addressed source snapshot を
    1件以上持つ
E0  それ以外
```

唯一の入力はObservation Engineが自らのScopeについて下した判定である。

artifact referenceはlevelに影響しない。Evidenceはartifactを取得できないため、artifact数
は最初から何の証明でもなかった。実装以前の版では、誰も見ていない内容への参照を1件添える
だけでE0がE1へ上がった。

---

# 4. Method binding

第28条の`observation_method`は、Observation Engineが自ら宣言Scopeに対して検証した
`method_ref`と`normalization_profile`で構成する。`observe()`はScope外のmethodを拒否する。

method recordそのものはlevelに寄与しない。`procedure_kind`がschema定数である以上、読んでも
第二の条件に**見えるだけで**条件ではない。

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

Sufficiency requestは次を必須とする。**ここに載るのは、engineが実際に検証するfieldだけ
である。**

```text
evidence_level_scale_ref = {
  kind: evidence_level_scale_source
  path:  "00_KERNEL/COMPLETION_SEMANTICS.md"      canonical path と照合
  blob_sha                                        pin と照合（pin は repository test が
                                                  git hash-object と照合）
  evidence_level_scale_sha256                     適用中の scale と照合
}
```

`repository`と`commit_sha`は持たない。純粋関数が検証できないためであり、blob addressは
commit非依存でもある。検証しないfieldを載せることは、`canonical content-addressed source`
という主張を、実際には何も指していないreferenceに与えることになる。

```text
REFERENCE_SHAPE_VALID=true
REFERENCED_BLOB_VERIFIED=false      ← これを残してはならない
CONTENT_ADDRESS_BINDING_PROVEN=false
```

三つのfieldはいずれも何かと照合される。一つでも不一致ならfail-closedで拒否する。
