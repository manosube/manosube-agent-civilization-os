# MANOSUBE Agent Civilization OS

## Approval Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=AUTHORITY
DOCUMENT_ID=APPROVAL-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Position

Human Approvalは、抽象的な「進めてよい」ではない。**正確な一つの操作へ結合した、独立したcanonical decision record**である。

```text
APPROVAL = SEPARATE CANONICAL RECORD
APPROVAL ≠ AUTHORSHIP
APPROVAL ≠ MENTION
APPROVAL ≠ REVIEW COMMENT
APPROVAL ≠ CONVERSATION
```

承認は推論されない。存在するか、しないかである。

```text
INFERRED APPROVAL = NO APPROVAL
```

# 1. Approval Record

```yaml
schema_version: "0.1"
approval_id: APPROVAL-...
project_id: PRJ-...
difference_ref: {kind: difference, id: D-...}
change_intent_fingerprint: sha256:...
change_ref: null
approved_state_revision: 0
approved_state_fingerprint: {profile: ..., digest: ...}
approved_action_fingerprint: sha256:...
approved_scope: {}
prohibited_actions: []
approved_by: {kind: human_authority, id: AUTH-...}
approved_at: "...Z"
expires_at: "...Z"
status: ACTIVE | REVOKED | EXPIRED
```

# 2. Change Intent Binding

`KERNEL_CONSTITUTION.md` 第22条と`SECURITY.md` §4は承認の結合先として`change_id`を挙げる。v0.1 Phase 4の時点でChange Engineは存在せず、束ねるべきChange identityがまだ生成されない。

そこでv0.1は結合先を次のように固定する。

```text
REQUIRED  change_intent_fingerprint   決定的なaction + scopeのdigest
OPTIONAL  change_ref                  Change recordが後に生じた場合のみ
```

`change_intent_fingerprint`は、`change_id`が指していた**意味**—「どの変更を承認したのか」—をChange識別子の存在に依存せず保持する。Change Engine実装時に`change_ref`が満たされても、承認の結合はこのfingerprintが決める。

```text
CHANGE_ID_UNAVAILABLE_IN_PHASE_4=true
CHANGE_INTENT_FINGERPRINT_IS_THE_BINDING=true
```

これは承認の厳密さを緩めない。fingerprintが変われば承認は無効である。

# 3. What an Approval Binds

承認は次のすべてへ同時に結合する。一つでも外れれば無効である。

```text
EXACT PROJECT
EXACT DIFFERENCE
EXACT CHANGE INTENT
EXACT STATE REVISION
EXACT STATE FINGERPRINT
EXACT ACTION FINGERPRINT (INCLUDING THE COMPLETE OPERATION PAYLOAD)
EXACT ENUMERATED SCOPE
EXPLICIT VALIDITY WINDOW
```

`approved_action_fingerprint`と`change_intent_fingerprint`はいずれもoperation payloadを含む。含まなければ、同一fileへ異なる内容を書く二つの操作が同じ承認を共有する。

```text
APPROVING A CATEGORY ≠ APPROVING AN OPERATION
```

## 3.1 Canonical Before Usable

承認は、bindingを比較される前に**canonical recordであること**を確認される。

```text
canonical schema / supported version / no unknown property
canonical approver identity (kind AND id)
recomputed approval_id matches its content
enumerated resolved approved_scope
```

`{"kind": "human_authority"}`だけでapprover identityを欠く記録は承認ではない。addressされた後に書き換えられた記録も承認ではない—それは偽造であり、bindingを比較する前に拒否する。

```text
INCOMPLETE APPROVER = NO APPROVAL
EDITED AFTER ADDRESSING = FORGERY, NOT A WEAK APPROVAL
```

# 4. Invalidation

次の場合、承認は無効となる（`SECURITY.md` §4、第22条）。

```text
Change intentが変わった
対象State revisionが変わった
State fingerprintが変わった
action fingerprintが変わった
scopeが拡張された
別Projectへ流用された
別Differenceへ流用された
期限が切れた
承認が撤回された
承認者identityを確認できない
```

```text
STALE_APPROVAL
→ REJECT
→ HUMAN_REAPPROVAL_REQUIRED
```

古い承認を新しいChangeへ流用しない。無効な承認は`AUTONOMOUS`へ落ちるのではなく、`HUMAN_APPROVAL_REQUIRED`のまま残る。

```text
INVALID APPROVAL ≠ NO APPROVAL NEEDED
```

# 5. Scope Widening

承認したscopeより広い要求は、承認されていない。

```text
REQUESTED SCOPE ⊆ APPROVED SCOPE
```

pathの追加、branchの変更、repositoryの変更、subjectの追加、recursive rootへの拡大はすべてscope widenであり、拒否する。部分一致による近似許可を作らない。

```text
PARTIAL SCOPE MATCH → REJECT
PREFIX MATCH IS NOT SCOPE MATCH
```

# 6. Prohibited Actions Carried by an Approval

承認は`prohibited_actions`を伴える。承認が明示的に除外した操作は、他のruleが許していても実行できない。

承認はprohibitionを**追加**できるが、**解除**はできない。

```text
APPROVAL MAY NARROW
APPROVAL MAY NOT WIDEN
APPROVAL CANNOT OVERRIDE A CONSTITUTIONAL PROHIBITION
```

## 6.1 Narrowing Is Independent of the Rule Level

除外の評価は、ruleが最初にどのlevelを出したかと**独立**である。

```text
BINDING      does this approval cover this request?
EXCLUSION    does it withhold this action?
```

二つは別の問いである。まとめて「使用不可」として扱うと、ruleが既に`AUTONOMOUS`を出した場合にapprovalが参照されず、除外が一度も適用されない。

```text
AN EXCLUSION THAT APPLIES ONLY WHEN A RULE ALREADY REQUIRED APPROVAL
IS NOT A NARROWING; IT IS A COINCIDENCE OF WHICH BRANCH RAN
```

要求へ結合するapprovalが一つでもその操作を除外していれば、decisionは`HUMAN_APPROVAL_REQUIRED`以上へ引き上げられる。除外したapprovalが、同じ操作を許可することはない。

除外したapprovalはdecision provenanceに記録する。記録しなければ、異なる二つのapprovalが同じrequestを同じlevel・同じreason codeへ狭めたとき、一つのidentityの下に異なる意味が並ぶ。

```text
EXCLUDING APPROVAL REFS ARE PROVENANCE
```

# 7. Validity Window

`approved_at`と`expires_at`は必須である。無期限承認は存在しない。

```text
UNBOUNDED APPROVAL = INVALID APPROVAL
```

有効期間の判定に用いる時刻は、評価入力として**明示的に与えられる**。Authority評価器はwall-clockを読まない。同じ入力が同じ判定を返すためであり、これは決定性の要件である。

```text
EVALUATION TIME IS AN INPUT
AUTHORITY DOES NOT READ THE CLOCK
```

三つのtimestampは比較前に**parseする**。文字列順序は時系列順序ではない。

```text
"2026-06-01T00:00:00Z" > "2026-06-01T00:00:00.5Z"   as strings
2026-06-01T00:00:00Z   < 2026-06-01T00:00:00.5Z     as instants
```

小数秒、等価offsetは同じinstantの別表記である。parseしなければ、期限内の承認が期限切れとして拒否され、あるいはその逆が起きる。timezoneを欠くtimestampはinstantを名指していないため拒否する。

```text
LEXICOGRAPHIC ORDER ≠ CHRONOLOGICAL ORDER
NAIVE TIMESTAMP → REJECT
```

# 8. Revocation

撤回は承認の削除ではない。`status: REVOKED`として保持し、lineageを残す。

```text
REVOCATION IS APPEND-ONLY
DELETED APPROVAL ≠ REVOKED APPROVAL
```

撤回済み承認は、期限内であっても無効である。

# 9. Approver Identity

`approved_by`はHuman Authority referenceである。Agent、Adapter、Bot、CI、Kernel自身は承認者になれない。

```text
AGENT CANNOT APPROVE
ADAPTER CANNOT APPROVE
KERNEL CANNOT APPROVE
SELF-APPROVAL = NO APPROVAL
```

# 10. Acceptance

```text
HUMAN_DECISION_SEPARATE_RECORD=true
APPROVAL_BOUND_TO_EXACT_CHANGE=true
APPROVAL_BOUND_TO_EXACT_STATE=true
APPROVAL_BOUND_TO_EXACT_SCOPE=true
STALE_APPROVAL_REJECTED=true
SCOPE_WIDENING_REJECTED=true
FOREIGN_PROJECT_DECISION_REJECTED=true
UNBOUNDED_APPROVAL_REJECTED=true
OPERATION_PAYLOAD_IN_BINDING=true
NONCANONICAL_APPROVAL_REJECTED=true
APPROVER_IDENTITY_REQUIRED=true
APPROVAL_IDENTITY_RECOMPUTED=true
CHRONOLOGICAL_WINDOW_COMPARISON=true
EQUIVALENT_APPROVALS_SELECTED_CANONICALLY=true
APPROVAL_CANNOT_OVERRIDE_PROHIBITION=true
INFERRED_APPROVAL_REJECTED=true
EVALUATION_TIME_IS_AN_INPUT=true
```
