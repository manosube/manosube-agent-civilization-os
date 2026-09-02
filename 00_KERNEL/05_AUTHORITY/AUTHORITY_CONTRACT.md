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
  operation: {}                      # opaque canonical payload
  action_semantic_fingerprint: sha256:...

requested_scope:
  repository: ...
  branch: ...
  paths: []
  subjects: []
```

## 3.1 Complete Operation Binding

`action_kind`とreversibilityだけでは操作を同定できない。同一fileへ異なる内容を書く二つの操作は、kindもscopeも同じである。

```text
ACTION KIND + SCOPE
≠ OPERATION
```

そこでactionは**opaque canonical operation payload**を伴う。

```text
AUTHORITY BINDS THE PAYLOAD
AUTHORITY NEVER INTERPRETS OR EXECUTES IT
```

fingerprintはcanonical bytesから**Authority自身が導出する**。呼び出し側が申告したdigestを信頼しない。申告値は再計算値と一致しなければならず、一致しない要求は拒否する。

```text
CALLER-DECLARED DIGEST = A LABEL
DERIVED DIGEST = THE BINDING
```

## 3.2 Enumerated Resolved Scope

scopeは明示列挙である。次はscope memberとして受理しない。

```text
glob / wildcard        **  *  ?  [ ]  { }
traversal              ..
relative prefix        ./
absolute root          /...
trailing separator     src/
empty or repeated segment
```

これらの範囲はAuthorityが読まないfilesystemに依存する。読まない対象について包含を判定することは、locationの比較ではなく文字列の比較である。

```text
SCOPE MUST BE ENUMERATED
PATH EXPRESSION → FAIL CLOSED
```

**symlink解決は非主張である。** 列挙されたmemberがBoundary外へ解決しないことの証明はfilesystem読み取りを要し、決定的評価器はそれを行わない。それはBinding ownerの責務であり、v0.1には存在しない。Authorityは*式*を拒否することでこの空白を有界に保つ。

```text
AUTHORITY_RESOLVES_SYMLINKS=false
PATH_EXPRESSION_ACCEPTED=false
```

# 4. Evaluation Route

```text
RAW AUTHORITY INPUTS
→ STRUCTURAL ADMISSIBILITY
→ SCHEMA + IDENTITY + PROVENANCE + SCOPE + TIME CONFORMANCE
→ VERIFIED CANONICAL RULES / APPROVALS / PROHIBITIONS / REQUEST
→ EXACT BINDING VERIFICATION
→ PROHIBITION EVALUATION
→ RULE RESOLUTION
→ APPROVAL VERIFICATION (required only when the rule demands it)
→ DECISION BOUND TO COMPLETE OPERATION + SELECTED PROVENANCE
```

## 4.1 Canonical Input Conformance

rule、approval、prohibitionはすべて**呼び出し側が供給する**。いずれかがdecisionへ影響する前に、一つの共通admission pathを通す。

```text
1  canonical objectとして読めるか
2  canonical schemaを、supported versionで、unknown propertyなしに満たすか
3  content-addressed identityが、実際に存在する内容と一致するか
4  schemaが要求するauthorityによって宣言されているか
```

3が要である。identityは*内容についての主張*であり、再計算だけが偽造を可視化する。他のすべての検査は、addressされた後に書き換えられた記録を通してしまう。

```text
ONE ADMISSION PATH
NO WEAKER LOCAL COPY IN RULE OR APPROVAL SELECTION
```

有効期間の比較はparsed instantで行う。文字列順序は時系列順序ではない。

```text
LEXICOGRAPHIC ORDER ≠ CHRONOLOGICAL ORDER
```

`evaluation_time`はadmission段階で解釈する。approval検査の内側だけで解釈すると、そこへ到達しない経路—ruleが自律を与えた、prohibitionが先に返った、approvalが空だった—では不正なinstantがそのままdecisionを生む。

```text
TIME CONFORMANCE BELONGS TO ADMISSION
NOT TO THE ONE BRANCH THAT READS A CLOCK VALUE
```

受理するのはRFC 3339 §5.6であり、言語のISO parserが偶然受け入れる範囲ではない。`datetime.fromisoformat`はRFC 3339の**上位集合**であり、任意の区切り文字、空白区切り、ISO週日付、基本形式、カンマ小数、コロンなしoffsetを通す。いずれもRFC 3339ではない。

```text
PARSING IS NOT VALIDATION
CHECK THE GRAMMAR, THEN PARSE
```

timestampのadmissionは**一つのowner**が行う。evaluation timeもapprovalの両端も同じ関数を通る。

opaque operation payloadは、解釈されないがcanonicalには**直列化可能でなければならない**。直列化できない値にはfingerprintが存在せず、approvalが結合する対象が存在しない。

```text
OPAQUE ≠ UNREPRESENTABLE
NON-CANONICAL PAYLOAD → FAIL CLOSED THROUGH THE PUBLIC BOUNDARY
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

# 7.1 Decision Identity Includes Its Provenance

decision identityは、結論だけでなく**何がその結論を支配したか**を含む。

```text
DECISION IDENTITY INPUT
= project + difference + action + scope + state binding
+ decision + reason codes
+ resolved rule identity
+ approval identity
+ sorted prohibition identities
+ sorted excluding approval identities
```

引用されるruleは、**その結論を支えたrule**でなければならない。governing ruleのうちidentity最小のものを引くと、決定がruleの制限で`HUMAN_APPROVAL_REQUIRED`になったのに、`AUTONOMOUS`を主張したruleを指す記録が生じる。referenceがcontent addressへ参加する以上、それは答えの出所を指さなければならない。

```text
CITE A RULE THAT SUPPORTS THE RESOLVED RESTRICTION
NOT MERELY A RULE THAT WAS PRESENT
```

Human-only floorとirreversibility floorはruleではない。それらが決定を引き上げた場合はreason codeとして記録し、ruleを騙って引用しない。

そのため引用は、**全floorとapproval narrowingを適用したあとに導出する**。rule解決の時点で選ぶと、決定がまだ確定していない段階のruleを引くことになる。governing ruleのどれも確定した決定を宣言していない場合、引用は`null`であり、reason codeが「ruleは支配したが決定を説明しない」と述べる。

```text
RESOLVE RULES → APPLY FLOORS → APPLY APPROVAL NARROWING → THEN CITE
NO GOVERNING RULE            → NO_RULE_RESOLVED,   resolved_rule_ref = null
GOVERNED, DECLARES THE ANSWER → RULE_RESOLVED,      resolved_rule_ref = that rule
GOVERNED, DOES NOT           → RULE_NOT_DECISIVE,  resolved_rule_ref = null
```

同じ結論・同じreason codeでも、支配したruleやprohibition、あるいは除外したapprovalが異なれば別のdecisionである。provenanceを除いたaddressは、同一identityの下に異なるpayloadを許す。

```text
SAME ID / DIFFERENT PAYLOAD = NOT CANONICAL
```

使用可能なapprovalが複数ある場合、canonical identity順で選択する。入力順が返却記録を変えてはならない。

```text
INPUT ORDER DOES NOT CHANGE THE ANSWER
```

# 7.2 Future Change Obligation

Authorityはoperationを実行しない。実行段階へ次の義務を残す。

```text
CHANGE EXECUTION MUST PRESENT
THE IDENTICAL OPERATION FINGERPRINT
THAT THE AUTHORITY DECISION BOUND
```

異なるfingerprintの操作は、そのdecisionによって許可されていない。この義務はChange phaseが実装する。v0.1 Phase 4はこれを**記録するだけ**である。

```text
CHANGE_ENGINE_IMPLEMENTED=false
OPERATION_FINGERPRINT_OBLIGATION_RECORDED=true
```

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
COMPLETE_OPERATION_BOUND=true
CALLER_DECLARED_DIGEST_NOT_TRUSTED=true
ONE_CANONICAL_INPUT_ADMISSION_PATH=true
RECORD_IDENTITY_RECOMPUTED=true
HUMAN_AUTHORITY_PROVENANCE_REQUIRED=true
PATH_EXPRESSION_REJECTED=true
AUTHORITY_RESOLVES_SYMLINKS=false
CHRONOLOGICAL_VALIDITY_COMPARISON=true
DECISION_IDENTITY_INCLUDES_PROVENANCE=true
APPROVAL_SELECTION_CANONICAL=true
APPROVAL_EXCLUSION_INDEPENDENT_OF_RULE_LEVEL=true
CITED_RULE_SUPPORTS_THE_DECISION=true
EVALUATION_TIME_ADMITTED_BEFORE_RESOLUTION=true
NONCANONICAL_PAYLOAD_FAILS_THROUGH_THE_PUBLIC_BOUNDARY=true
```

```text
AUTHORITY_CONTRACT_DEFINED=true
AUTHORITY_SCHEMA_IMPLEMENTED=true
AUTHORITY_ENGINE_IMPLEMENTED=true
CHANGE_ENGINE_IMPLEMENTED=false
ONE_FULL_NATURAL_CYCLE_PASS=false
```
