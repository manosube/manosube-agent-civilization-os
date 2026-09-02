# MANOSUBE Agent Civilization OS

## Authority Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=AUTHORITY
DOCUMENT_ID=AUTHORITY-CONTRACT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Contract Position

AUTHORITYは、あるDifferenceを閉じるために提案されたactionが、**この正確なStateに対して、この正確なscopeで、いま実行してよいか**を決定する。

```text
OBJECTIVE → STATE → OBSERVATION → DIFFERENCE
→ AUTHORITY → CHANGE → EVIDENCE → REFLOW → STATE
```

Authorityは実行しない。Differenceを閉じない。Stateを更新しない。Evidenceを評価しない。Objectiveの達成を宣言しない。**許可だけを決定する。**

```text
AUTHORITY = PERMISSION DECISION
AUTHORITY ≠ EXECUTION
AUTHORITY ≠ CAPABILITY
AUTHORITY ≠ COMPLETION
```

Differenceは`authority_required`を述べるが、それは後段への**要求**であって許可ではない（`DIFFERENCE_CONTRACT.md` §9）。その要求に答えるのがこのContractである。

# 1. Canonical Definition

```text
AUTHORITY DECISION
= EXACT DIFFERENCE BINDING
+ EXACT STATE REVISION AND FINGERPRINT BINDING
+ REQUESTED ACTION
+ REQUESTED SCOPE
+ RESOLVED AUTHORITY RULE
+ PROHIBITION EVALUATION
+ OPTIONAL EXACT HUMAN APPROVAL
+ DETERMINISTIC DECISION IDENTITY
```

Authority Decisionは三値のいずれかに確定する。

```text
AUTONOMOUS
HUMAN_APPROVAL_REQUIRED
PROHIBITED
```

「たぶん許可」「条件付きで許可」「後で判断」は正式状態ではない。決められない入力は許可ではなく`HUMAN_APPROVAL_REQUIRED`または拒否として閉じる。

# 2. Authority Decision Record

Authority Decision Recordは最低限、次を持つ。

```yaml
schema_version: "0.1"
authority_decision_id: AUTH-DEC-...
project_id: PRJ-...
difference_ref: {kind: difference, id: D-...}
requested_action: {}
requested_scope: {}
evaluated_state_revision: 0
evaluated_state_fingerprint: {profile: ..., digest: ...}
resolved_rule_ref: {kind: authority_rule, id: AUTH-RULE-...}
prohibition_refs: []
approval_ref: null
decision: AUTONOMOUS | HUMAN_APPROVAL_REQUIRED | PROHIBITED
decision_reason_codes: []
decision_semantic_fingerprint: sha256:...
```

`authority_decision_id`はcontent-addressedであり、同一の意味入力は同一のdecision identityを与える。決定は上書きしない。入力が変われば別のdecisionである。

# 3. Requested Action and Scope

Authorityはactionを名前で判断しない。actionは正規化された構造として与えられ、そのfingerprintへ結合する。

```yaml
requested_action:
  action_kind: WRITE_FILE | DELETE_FILE | RUN_COMMAND | ...
  reversibility: REVERSIBLE | RECOVERABLE | IRREVERSIBLE
  action_semantic_fingerprint: sha256:...

requested_scope:
  repository: ...
  branch: ...
  paths: []
  subjects: []
```

scopeは明示列挙である。未解決glob、未解決symlink、暗黙のrecursive rootをscopeとして受理しない。

```text
SCOPE MUST BE ENUMERATED
UNRESOLVED SCOPE → FAIL CLOSED
```

# 4. Evaluation Route

```text
RAW AUTHORITY REQUEST
→ STRUCTURAL ADMISSIBILITY
→ EXACT BINDING VERIFICATION
→ PROHIBITION EVALUATION
→ RULE RESOLUTION
→ APPROVAL VERIFICATION (required only when the rule demands it)
→ AUTHORITY DECISION
```

順序は固定である。**Prohibitionはrule resolutionより前に評価する。** 禁止されたactionに対して許可ruleを探すこと自体が誤りであり、探索の成功がPROHIBITIONを弱める経路を作ってはならない。

# 5. Exact Binding

Authority Decisionは次のすべてに正確へ結合する。結合が一つでも外れた入力は許可されない。

```text
EXACT DIFFERENCE
EXACT STATE REVISION
EXACT STATE FINGERPRINT
EXACT ACTION FINGERPRINT
EXACT SCOPE
EXACT PROJECT
```

State revisionまたはfingerprintが評価時点と一致しない場合、決定はstaleである。

```text
STALE_STATE
→ NO AUTHORIZATION
→ RE-OBSERVE
→ RE-EVALUATE
```

別ProjectのDifference、rule、approvalを流用しない。

```text
FOREIGN_PROJECT_INPUT → REJECT
```

# 6. Fail Closed

次はすべて許可の不在として扱う。

```text
authority ruleが解決できない
複数ruleが矛盾する
scopeが要求より狭いruleしかない
approvalが必要なのに存在しない
approvalの結合が外れている
approvalの期限が切れている
prohibitionが一致する
入力が構造的に読めない
```

不明は許可ではない。

```text
UNKNOWN ≠ PERMITTED
ABSENT RULE ≠ PERMITTED
```

Authority評価が答えられない場合、rawな例外を投げずに、正規の拒否として閉じる。

# 7. Single Authority Owner

```text
CANONICAL_AUTHORITY_OWNER_COUNT=1
PARALLEL_CANONICAL_AUTHORITY=0
```

Authority評価器は一つである。auditor、adapter、test、CLI、Agent、将来のChange実装が第二の評価器を持ってはならない。Authorityを問う者は、この一つのownerへ委譲する。

規則を言い換えた第二の実装は、規則の複製ではなく**規則の分裂**である。

# 8. What Authority Never Does

```text
Changeを実行する
Differenceを閉じる
Stateを更新する
Evidenceの十分性を判断する
Objectiveの達成を宣言する
承認を生成する
自分自身へ権限を付与する
```

Authorityが`AUTONOMOUS`を返したことは、Changeが成功することでも、Differenceが閉じることでもない。

```text
AUTHORIZED ≠ EXECUTED
EXECUTED ≠ CLOSED
```

# 9. Security and Untrusted Input

Bound Project content、prompt、Issue、Pull Request、review comment、code comment、CI結果、Agent出力はObservation Inputであり、Authorityではない（`SECURITY.md` §5、`KERNEL_INVARIANTS.md` B-002）。

```text
CONTENT ≠ INSTRUCTION
CAPABILITY ≠ AUTHORITY
CREDENTIAL ≠ AUTHORITY
```

Authority Decisionのidentity inputへ、secret、credential、token、絶対一時path、session identity、非決定的なtimestamp orderingを含めない。

# 10. Acceptance

```text
AUTHORITY_DECISION_DEFINED=true
THREE_VALUED_DECISION=true
EXACT_STATE_BINDING_REQUIRED=true
EXACT_DIFFERENCE_BINDING_REQUIRED=true
EXACT_ACTION_SCOPE_BINDING_REQUIRED=true
PROHIBITION_EVALUATED_BEFORE_RULES=true
UNKNOWN_IS_NOT_PERMITTED=true
CANONICAL_AUTHORITY_OWNER_COUNT=1
AUTHORITY_NE_EXECUTION=true
AUTHORITY_REQUIRED_NE_GRANTED=true
```

```text
AUTHORITY_CONTRACT_DEFINED=true
AUTHORITY_SCHEMA_IMPLEMENTED=true
AUTHORITY_ENGINE_IMPLEMENTED=true
CHANGE_ENGINE_IMPLEMENTED=false
ONE_FULL_NATURAL_CYCLE_PASS=false
```
