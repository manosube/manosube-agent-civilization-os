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
EXACT ACTION FINGERPRINT
EXACT SCOPE
EXPLICIT VALIDITY WINDOW
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
APPROVAL_CANNOT_OVERRIDE_PROHIBITION=true
INFERRED_APPROVAL_REJECTED=true
EVALUATION_TIME_IS_AN_INPUT=true
```
