# MANOSUBE Agent Civilization OS

## Prohibition Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=AUTHORITY
DOCUMENT_ID=PROHIBITION-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Position

Prohibitionは「許可の不在」ではない。**明示された拒否**である。

```text
NO RULE        → HUMAN_APPROVAL_REQUIRED
PROHIBITION    → PROHIBITED
```

この二つを同じ状態へ潰してはならない。前者は人間に問える。後者は問えない。

# 1. Prohibition Record

```yaml
schema_version: "0.1"
prohibition_id: PROHIBIT-...
project_id: PRJ-...
prohibition_class: CONSTITUTIONAL | PROJECT
action_kinds: []
scope: {}
reason_code: ...
declared_by: {kind: human_authority, id: AUTH-...}
```

# 2. Supremacy

`KERNEL_CONSTITUTION.md` 第23条を実行語彙へ固定する。

```text
PROHIBITED > HUMAN_APPROVAL_REQUIRED > AUTONOMOUS
```

禁止は次によって解除されない。

```text
Agent能力
Tool permission
credential scope
admin access
CI PASS
利便性
時間短縮
成功可能性
retry
別ruleの許可
review approval
```

```text
TOOL CAN EXECUTE ≠ CHANGE IS AUTHORIZED
```

# 3. Constitutional Prohibitions Cannot Be Approved Away

`prohibition_class: CONSTITUTIONAL`は、正確に結合された有効なHuman Approvalが存在しても`PROHIBITED`のままである。

```text
APPROVAL + CONSTITUTIONAL PROHIBITION → PROHIBITED
```

憲法的禁止の解除は、承認ではなくConstitutional Change—`SECURITY.md` §21が定める手続き—を必要とする。日常のapproval経路が憲法を書き換える経路になってはならない。

`prohibition_class: PROJECT`は、Human Authorityが明示的にProject rule側で置き換えられる。ただし置換もまた記録された決定であり、承認一件で暗黙に消えることはない。

# 4. Evaluation Order

Prohibitionはrule resolutionより**前**に評価する。

```text
ADMISSIBILITY → BINDING → PROHIBITION → RULES → APPROVAL → DECISION
```

順序を逆にすると、許可ruleの探索成功がprohibitionの評価を飛ばす経路が生まれる。禁止は「見つからなかった許可」ではなく「見つかった拒否」であり、先に問う。

# 5. Matching

Prohibitionは`action_kinds`と`scope`の交差で一致する。

```text
MATCH = action_kind ∈ action_kinds ∧ scope ∩ prohibited_scope ≠ ∅
```

**交差で一致する。** 包含ではない。要求scopeの一部でも禁止scopeに触れれば、その要求全体が`PROHIBITED`である。禁止されたpathを含む要求を、含まない部分だけ実行してよいとは判断しない。

```text
PARTIAL OVERLAP → WHOLE REQUEST PROHIBITED
```

これは許可側の`⊆`と非対称であり、意図的である。許可は狭く、禁止は広く働く。

# 6. Scope Resolution

禁止scopeも列挙である。未解決globやsymlinkで禁止範囲を判定しない。判定できない場合は禁止側へ倒す。

```text
UNRESOLVED SCOPE IN PROHIBITION CHECK → TREAT AS MATCH
```

これはfail closedの適用であり、Authority Contract §6と同じ方向である。

# 7. Project Isolation

別Projectのprohibitionを流用しない。ただし`CONSTITUTIONAL`なprohibitionはKernel全体に属し、Project境界で消えない。

```text
PROJECT PROHIBITION: project-scoped
CONSTITUTIONAL PROHIBITION: kernel-wide
```

# 8. Prohibition Is Not Failure

`PROHIBITED`はsystemの誤動作ではなく、正常な決定である。禁止された操作が拒否されたことは、脆弱性でも障害でもない（`SECURITY.md` §20）。

禁止を回避するためにGate、Objective、Closure Policy、Boundaryを弱めてはならない（`SECURITY.md` §14）。

```text
DO NOT WEAKEN THE GATE TO PASS IT
```

# 9. Acceptance

```text
PROHIBITION_PRECEDENCE=true
PROHIBITION_EVALUATED_BEFORE_RULES=true
CONSTITUTIONAL_PROHIBITION_SURVIVES_APPROVAL=true
PARTIAL_SCOPE_OVERLAP_PROHIBITS=true
UNRESOLVED_SCOPE_TREATED_AS_MATCH=true
PROHIBITION_NE_MISSING_RULE=true
CAPABILITY_CANNOT_LIFT_PROHIBITION=true
```
