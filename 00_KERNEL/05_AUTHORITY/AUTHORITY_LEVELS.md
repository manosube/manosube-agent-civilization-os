# MANOSUBE Agent Civilization OS

## Authority Levels v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=AUTHORITY
DOCUMENT_ID=AUTHORITY-LEVELS-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Position

Authorityは三値である。段階を増やして曖昧さを吸収してはならない。

```text
AUTONOMOUS
HUMAN_APPROVAL_REQUIRED
PROHIBITED
```

三値以外の表現—「たぶん可」「注意して実行」「警告付き許可」—を正式決定として保存しない。判断できない入力は`HUMAN_APPROVAL_REQUIRED`へ落ちるのであって、`AUTONOMOUS`へは落ちない。

# 1. The Three Layers

`KERNEL_CONSTITUTION.md` 第4条の三層分離を、決定の語彙として固定する。

```text
HUMAN
= OBJECTIVE AUTHORITY
+ CONSTITUTIONAL AUTHORITY
+ IRREVERSIBLE RISK AUTHORITY

MANOSUBE KERNEL
= STRUCTURAL AUTHORITY
+ AUTHORITY EVALUATION
+ STATE TRANSITION ENFORCEMENT

AI AGENT
= EXECUTION CAPABILITY
```

Kernelは**評価**を所有し、**envelope**は所有しない。envelopeを定めるのはHumanである。KernelがHumanのenvelopeを広げることはできない。

```text
KERNEL EVALUATES THE ENVELOPE
KERNEL DOES NOT WIDEN IT
```

# 2. Level Semantics

## AUTONOMOUS

一致したruleが自律実行を許し、prohibitionに一致せず、scopeがrule scopeの内側にあり、bindingが正確である。

```text
AUTONOMOUS
= RULE PERMITS
∧ NO PROHIBITION MATCHES
∧ SCOPE ⊆ RULE SCOPE
∧ EXACT BINDING HOLDS
```

`AUTONOMOUS`はChangeの成功を意味しない。実行してよい、というだけである。

## HUMAN_APPROVAL_REQUIRED

ruleが自律実行を許さない、または一致するruleが存在しない、またはactionがHuman-only classへ属する。

```text
HUMAN_APPROVAL_REQUIRED
= RULE REQUIRES APPROVAL
∨ NO RULE RESOLVED
∨ ACTION ∈ HUMAN_ONLY
∨ APPROVAL PRESENT BUT NOT EXACTLY BOUND
```

**ruleの不在は`HUMAN_APPROVAL_REQUIRED`であって`AUTONOMOUS`ではない。** 沈黙は許可ではない。

## PROHIBITED

一致するprohibitionが存在する。approvalの有無、rule、risk、利便性、Agent能力に関わらず確定する。

```text
PROHIBITED
= ANY PROHIBITION MATCHES
```

# 3. Precedence

```text
PROHIBITED
> HUMAN_APPROVAL_REQUIRED
> AUTONOMOUS
```

この順序は絶対である。

```text
APPROVAL CANNOT OVERRIDE PROHIBITION
RULE CANNOT OVERRIDE PROHIBITION
CAPABILITY CANNOT OVERRIDE PROHIBITION
CONVENIENCE CANNOT OVERRIDE PROHIBITION
```

複数のruleが一致した場合、**最も制限的なlevelを採用する**。緩いruleが厳しいruleを上書きする経路を作らない。

```text
CONFLICTING RULES → MOST RESTRICTIVE WINS
```

# 4. Human-only Classes

次は原則としてHuman Authorityに保持する（`SECURITY.md` §3）。Projectごとに異なる設定を採るには、明示的なHuman Authority記録を必要とする。

canonical action kindとして次を固定する。実装側の集合はこの一覧へ双方向で拘束される。

```text
HUMAN_ONLY_ACTION_KINDS
CHANGE_OBJECTIVE
WIDEN_BOUNDARY
CHANGE_AUTHORITY
CHANGE_ORIGIN
CHANGE_KERNEL_CONSTITUTION
CHANGE_SECURITY_POLICY
DEPLOY_PRODUCTION
CHANGE_CREDENTIAL
CHANGE_BILLING
IRREVERSIBLE_OPERATION
DESTRUCTIVE_RECOVERY
MERGE
RELEASE
```

これらはruleが`AUTONOMOUS`を述べていても`HUMAN_APPROVAL_REQUIRED`以上へ引き上げられる。Kernel constitutionが明示的に別を述べる場合のみ例外となる。

# 5. Reversibility and Risk

Reversibilityは決定を緩めない。決定を**引き締める**方向にのみ働く。

```text
IRREVERSIBLE → AT LEAST HUMAN_APPROVAL_REQUIRED
```

Difference側の`risk_class`（LOW / MODERATE / HIGH / CRITICAL）は入力であって決定ではない。低いrisk_classがprohibitionやHuman-only classを解除することはない。

```text
LOW RISK ≠ AUTONOMOUS
HIGH RISK ≠ PROHIBITED
```

risk_classはruleが参照してよい観測値であり、それ自体がAuthorityではない。

# 6. Determinism

同じ意味入力は同じlevelを返す。levelはtimestamp、Agent identity、session、実行順序、retry回数に依存しない。

```text
SAME SEMANTIC INPUT → SAME DECISION IDENTITY
```

再試行によってlevelが緩むことはない。

```text
RETRY DOES NOT ESCALATE AUTHORITY
```

# 7. Acceptance

```text
THREE_VALUED_DECISION=true
NO_RULE_MEANS_APPROVAL_REQUIRED=true
PROHIBITION_PRECEDENCE=true
MOST_RESTRICTIVE_RULE_WINS=true
HUMAN_ONLY_OPERATIONS_PRESERVED=true
IRREVERSIBLE_REQUIRES_HUMAN=true
RISK_CLASS_NE_AUTHORITY=true
RETRY_DOES_NOT_ESCALATE=true
DECISION_DETERMINISTIC=true
```
