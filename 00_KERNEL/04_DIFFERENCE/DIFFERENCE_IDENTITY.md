# MANOSUBE Agent Civilization OS

## Difference Identity Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-IDENTITY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Purpose

本Contractは、同じStructural DifferenceがAgent、session、Observation回数、GitHub表現の変化によって別仕事へ分裂することを防ぐ。

```text
SAME SEMANTIC DIFFERENCE → SAME DIFFERENCE ID
MATERIALLY DIFFERENT DIFFERENCE → DIFFERENT ID OR EXPLICIT SUPERSESSION
```

# 1. Identity Profile

v0.1のidentity profileを次で固定する。

```text
PROFILE=MANOSUBE-DIFFERENCE-SHA256-0.1
DIGEST=SHA-256
TEXT_NORMALIZATION=UNICODE_NFC
SERIALIZATION=CANONICAL_JSON_UTF8
KEY_ORDER=LEXICOGRAPHIC
UNKNOWN_FIELDS=REJECT
```

`difference_id`の形式は次とする。

```text
D-<UPPERCASE_SHA256_HEX>
```

# 2. Semantic Identity Input

Identity inputは次のsemantic tupleだけで構成する。

```text
DIFFERENCE_IDENTITY_INPUT
= project_id
+ objective_semantic_fingerprint
+ target_predicate_ref
+ subject
+ predicate
+ effective_boundary
+ normalized_target_state
+ normalized_structural_mismatch
+ identity_profile
```

`objective_revision_ref`はexact provenance bindingとしてDifference Recordへ保持するが、identity inputには含めない。Objectiveの`EDITORIAL` revisionはsemantic fingerprintが不変であるため、同じTargetとMismatchのDifference IDを維持する。

Target value、Objective semanticsまたはMismatchの意味が変わればidentityは変わる。Observed valueはMismatchへ正規化された範囲だけidentityへ反映する。

# 3. Excluded Inputs

次をidentity inputへ含めてはならない。

```text
observed_at
observer
Agent name
model name
session ID
process ID
temporary path
serialization order
Observation ID
Evidence ID
State revision
State fingerprint
Issue number
branch name
commit SHA
Pull Request number
Change ID
approval ID
volatile log
credential
secret
```

これらはprovenanceまたはmetadataとして保存できるが、semantic identityを変えてはならない。

# 4. Canonicalization

Identity生成前に、tuple全体をCanonical Stateと同じ原則で正規化する。

```text
1. schemaで未知fieldを拒否
2. UnicodeをNFCへ正規化
3. numberをcanonical numberへ正規化
4. unordered collectionをcanonical member bytesで整列
5. duplicate semantic memberを拒否
6. object keyを辞書順へ整列
7. UTF-8 canonical JSON bytesへserialize
8. SHA-256 digestを生成
9. D- prefixを付与
```

NaN、Infinity、曖昧なlocal time、credential-bearing locator、schema外valueはFail Closedする。

# 5. Stability Across Re-observation

同一Objective semantic fingerprint、Target Predicate、boundary、normalized mismatchを再観測した場合、ObjectiveのEDITORIAL revision、Observation ID、State revision、Evidenceが変わっても同じ`difference_id`を生成する。

```text
REOBSERVATION
→ SAME DIFFERENCE ID
→ APPEND OBSERVATION BINDING
→ APPEND LIFECYCLE EVENT
```

新しいObservationを得るたびにDifference Recordを複製してはならない。

# 6. New Identity and Supersession

次のいずれかがmaterially変わった場合、新しいDifference identityを生成する。

```text
project
Objective semantic fingerprint
Target Predicate
subject or predicate
effective boundary
Target State semantics
Mismatch kind or semantic content
identity profile
```

旧Differenceとの意味上の連続性がある場合、append-onlyなSupersession Relationで双方向関係を記録する。

```yaml
schema_version: "0.1"
supersession_relation_id: D-SUP-...
old_difference_ref: {kind: difference, id: D-OLD...}
new_difference_ref: {kind: difference, id: D-NEW...}
old_terminal_event_ref: {kind: difference_event, id: D-EVT-...}
new_genesis_event_ref: {kind: difference_event, id: D-EVT-...}
reason_code: TARGET_OR_MISMATCH_CHANGED
evidence_refs: []
```

Relationは両Differenceと双方のLifecycle Eventから解決可能でなければならない。Canonical Difference Recordを上書きせず、materialized viewの`superseded_by`と`supersedes`をRelationから導出する。

片方向、循環、自己参照、存在しないDifferenceへのsupersessionは拒否する。同一Relation ID・同一payloadはidempotent、異なるpayloadはcollisionとして拒否する。

# 7. Idempotency and Collision

```text
SAME DIFFERENCE ID + SAME IMMUTABLE SEMANTIC IDENTITY PAYLOAD
→ IDEMPOTENT ACCEPT

SAME DIFFERENCE ID + DIFFERENT IMMUTABLE SEMANTIC IDENTITY PAYLOAD
→ IDENTITY COLLISION
→ REJECT OR QUARANTINE
```

Collision比較の対象は第2節のimmutable semantic identity inputだけである。Observation bindings、State revision、Evidence references、status、Lifecycle Event、Supersession Relationなどのappend-only provenanceは比較対象から除外する。

したがって、同じidentityに新しいre-observation provenanceをappendすることはcollisionではない。ただし、同じprovenance event IDに異なるpayloadを与えた場合はprovenance collisionとして拒否する。

Identity Collision時に後着payloadで上書きしない。新しいIDを任意生成して衝突を隠さない。

# 8. Identity versus Instance State

Difference identityとDifference lifecycle stateを分離する。

```text
IDENTITY
= 何が構造的に異なるか

LIFECYCLE
= 現在どの評価段階にあるか
```

status、priority、assignee、attempt count、last observed time、Evidence levelはidentityへ含めない。

# 9. Acceptance Vectors

最低限、次のconformance vectorを要求する。

```text
KEY_ORDER_CHANGED → SAME ID
UNICODE_EQUIVALENT → SAME ID
OBSERVATION_CHANGED_SEMANTICS_SAME → SAME ID
STATE_REVISION_CHANGED_SEMANTICS_SAME → SAME ID
ISSUE_NUMBER_CHANGED → SAME ID
TARGET_CHANGED → DIFFERENT ID
OBJECTIVE_EDITORIAL_REVISION_CHANGED → SAME ID
OBJECTIVE_SEMANTIC_FINGERPRINT_CHANGED → DIFFERENT ID
BOUNDARY_CHANGED → DIFFERENT ID
MISMATCH_CHANGED → DIFFERENT ID
SAME_ID_DIFFERENT_SEMANTIC_IDENTITY_PAYLOAD → REJECT
SAME_ID_NEW_REOBSERVATION_PROVENANCE → APPEND
```

# 10. Acceptance

```text
DIFFERENCE_IDENTITY_PROFILE_DEFINED=true
SEMANTIC_INPUT_CLOSED=true
VOLATILE_INPUTS_EXCLUDED=true
REOBSERVATION_ID_STABLE=true
SUPERSESSION_BIDIRECTIONAL=true
DUPLICATE_IDEMPOTENT=true
COLLISION_FAIL_CLOSED=true
```

```text
DIFFERENCE_IDENTITY_DEFINED=true
DIFFERENCE_IDENTITY_IMPLEMENTED=false
DIFFERENCE_IDENTITY_RUNTIME_PROVEN=false
```
