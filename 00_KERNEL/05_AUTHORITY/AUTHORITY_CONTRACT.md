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

## 3.3 Set-valued scopeの正準表現

`paths`と`subjects`は**listとして書かれたset**である。containmentとoverlapはすでに`set(...)`で計算し、canonical schemaは`uniqueItems`を宣言する。順序は意味を持たない。

```text
SCOPE_AUTHORIZATION_SEMANTICS=SET
SCOPE_IDENTITY_SEMANTICS=SET
SCOPE_PATHS_ORDER_SEMANTIC=false
SCOPE_SUBJECTS_ORDER_SEMANTIC=false
```

したがって同じ member を別の順序で並べた二つの要求は**同一の要求**であり、同一のdecision identityを導く。正準化は`authority.scope.canonical_scope`ただ一箇所で行う。

```text
CANONICAL_SCOPE_NORMALIZATION_OWNER_COUNT=1
```

`authority.identity`と`change.identity`は自前でsortせず、このownerを呼ぶ。第二のsortは「正準形とは何か」への第二の答えであり、二つが食い違った最初の瞬間、食い違いは無音である。

正準化はduplicateを**畳み込まない**。重複memberは`require_scope`が拒否する。黙って重複を除去することは、入力の欠陥を受理された記録へ変えることである。

`repository`と`branch`はscalarであってsetではない。触れない。

## 3.4 供給recordのscopeは書き換えない

rule・prohibition・approvalは、人が著しcontent-addressedされた記録である。それらのscopeをin-placeで正準化すれば、**誰も再署名していない記録のaddressを変える**ことになる。したがってそれらに対する`require_scope`は検証としてのみ呼ばれ、戻り値は意図的に破棄される。

```text
SUPPLIED_RECORD_SCOPE_REWRITTEN=false
```

containmentとoverlapはすでにsetとして比較するので、これらの順序差は許可判断に影響しない。

# 4. Evaluation Route

<!-- EVALUATION_ROUTE:BEGIN -->
```text
RAW REQUEST
→ REQUEST + DIFFERENCE ADMISSION
→ AUTHORITY RECORD ADMISSION + DISTINCTNESS
→ EXACT BINDING
→ PROHIBITIONS
→ RULES + FLOORS
→ APPROVAL BINDING + EXCLUSION (independent of rule level)
→ FINAL PROVENANCE
→ DECISION
```
<!-- EVALUATION_ROUTE:END -->

この経路は`engine.EVALUATION_ROUTE`の描画であり、module docstringも同一の描画を持つ。三箇所を手で保守した結果、三つの**異なる**経路になっていた。approvalは「ruleが要求したときだけ検証する」と書かれていたが、round 2以降それは実装ではない。contract testが三者を等しく保つ。

ただし、その保証の範囲を明示する。**この検査は三箇所のwordingがdriftしないことだけを示し、codeがこの順序で実行することの証明ではない。** 実行順序は振る舞いのtestが担う。

## 4.1 Canonical Input Conformance

bound Difference、rule、approval、prohibitionはすべて**呼び出し側が供給する**。いずれかがdecisionへ影響する前に、一つの共通admission pathを通す。bound Differenceは五つのうち最後に加わった。他の四つにadmission pathが与えられた時点で、Differenceは別の入口から入り、古い扱いのまま残っていた。

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

供給されたcollectionは**集合であり、listとして書かれているに過ぎない**。同一identityの記録が二度現れることは、一つの記録が二度供給されたということであり、入力の誤りである。黙って畳み込まず、境界で拒否する。畳み込みは評価器が入力を勝手に訂正することであり、非canonicalなtimestampを書き換えないという判断と同じ理由で採らない。

```text
rule / approval / prohibition   同一identityの重複 → REJECT
scope paths / subjects          同一memberの重複   → REJECT
DEDUPLICATE SILENTLY            → NEVER
```

### identityの再計算が示す範囲

`difference_id`は**semantic identity**であり、記録全体のcontent hashではない。再計算が検出するのは`difference_identity_input`に含まれる場のみである。`observed_state_revision`と`observed_state_fingerprint`はそこに**含まれない**。

staleness比較は、**admitされた入力どうしの厳密な一致検査**である。DifferenceとcurrentとされるStateが互いに整合することは示すが、そのどちらかが途中で書き換えられていないことは示さない。

```text
RECOMPUTED difference_id  → identity projectionが改変されていない
STALE STATE CHECK         → 入力どうしが整合する
NEITHER                   → observed-State pairの真正性の証明
```

現在のStateとDifference記録全体を、信頼できるbackendに対して認証することは**Binding**の義務である。Phase 4にBinding ownerは存在しない。したがってこれは実装漏れではなく、明示された非主張である。

```text
TRUSTED_STATE_PROVENANCE=BINDING_OBLIGATION
AUTHORITY_AUTHENTICATES_SUPPLIED_STATE=false
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

異なるfingerprintの操作は、そのdecisionによって許可されていない。v0.1 Phase 4はこの義務を**記録するだけ**であった。Phase 5のChange Engineがそれを果たす（`CHANGE_CONTRACT.md` §7）——actionのfingerprintを再計算し、さらにaction全体をdecisionが束縛したものと完全一致で照合する。

```text
CHANGE_ENGINE_IMPLEMENTED=true
OPERATION_FINGERPRINT_OBLIGATION_RECORDED=true
OPERATION_FINGERPRINT_OBLIGATION_DISCHARGED=true
```

# 7.3 Verifier Selection Decision (Structural Review Round 3, Issue #51, P13-R3-F1)

`evaluate_authority`が答えるのは「このexact StateとDifferenceに対して、このactionをいま実行してよいか」である。Independent Verification（Phase 13）は別の問いを持つ——「特定の`VerificationRequirement`に対して、特定の`VerifierSelection`（verifier identity・permitted boundary・selection status）をSHUKOUが選んだと、既存Authority ownerは再検証できるか」。

`boot_project(...).human_authority_ref`は、Project Bindingの正規Human Authorityを再検証する参照であり、この問いへの答えではない。project全体が正しいHuman Authorityへ束縛されていることは、その中の**特定のVerifierSelection**をそのHuman Authorityが選んだことを意味しない。二つの問いを混同すれば、`human_authority_ref`を単に複製したcaller-created selectionが、実在するAuthority Decisionであるかのように扱われる。

`evaluate_verifier_selection`は、この一つの owner の中の、**第二の、狭く限定された評価器**である。

```text
CANONICAL_AUTHORITY_OWNER_COUNT=1
VERIFIER_SELECTION_EVALUATOR_COUNT=1
NEW_AUTHORITY_OWNER=false
NEW_AUTHORITY_REGISTRY=false
NEW_SELECTION_TOKEN=false
NEW_SELECTION_CACHE=false
CALLER_MAPPING_EQUALITY_AS_AUTHORITY=false
BOOT_HUMAN_AUTHORITY_REF_ALONE_IS_SELECTION_DECISION=false
```

Verifier Selection Decisionは、少なくとも次のすべてを一つのimmutable・content-addressedな決定へ束縛する。

```text
VERIFIER SELECTION DECISION IDENTITY INPUT
= project_id + requirement_id + selection_id
+ verifier_identity + permitted_boundary + selection_status
+ selection_authority_ref（Boot-verified human_authority_ref、caller供給の等価claimではない）
+ grant_ref + sorted excluding_grant_refs
+ decision + decision_reason_codes
```

決定が有効になるのは、既存Authority ownerが公開する`admit`/`admit_all`——`authority_rule`・`approval`・`prohibition`と同じ admission gate——を通過した、実在する`verifier_selection_grant`（Human Authorityにより宣言され、content addressが再計算され一致する）が、上記の全フィールドへ完全一致で束縛するときだけである。一つも束縛しなければ`VERIFIER_SELECTION_REFUSED`であり、束縛するが`status`が`ACTIVE`でないgrantは、approvalのexclusionと同じ理由で選択を無効にする。caller が偽造した、または単に既知の値を複製しただけのgrantは、`grants`自体の欠如と同じく決定を`SELECTED`にしない。

```text
GRANT_MISSING → VERIFIER_SELECTION_REFUSED
GRANT NAMES A DIFFERENT project/requirement/selection/verifier/boundary/status → does not bind
GRANT NOT DECLARED BY THE REAL human_authority_ref → GRANT_AUTHORITY_MISMATCH
GRANT BINDS BUT status != ACTIVE → withholds, VERIFIER_SELECTION_REFUSED
EXACTLY ONE GENUINE, FULLY-BOUND, ACTIVE GRANT → VERIFIER_SELECTION_SELECTED
```

Independent Verificationのroute（`08_VERIFICATION/VERIFICATION_CONTRACT.md`）は、この決定をVerifier呼び出しの前に一度だけ再検証する。既存Authority ownerが読めない入力へ返す typed error は、そのまま伝播する——このroute自身は例外を捕捉も再分類もしない。

**Structural Review Round 4（Issue #51, P13-R4, Authority Provenance Bypass, P13-R3-F2）:** `evaluate_verifier_selection`自身の`admit`/`admit_all`は、grantの*内容*が自己無矛盾であること（宣言identityが再計算値と一致し、`granted_by.kind`がHuman Authorityの形をしている）だけを検証する——それはgrantが実在するHuman Authorityによって著されたことの証明ではない。`human_authority_ref`は秘密ではないため、grant内容そのものを呼び出し側の引数として直接受理すれば、`granted_by`が実在の参照を単に複製しただけの自己ハッシュgrantを、呼び出し側が作り出せてしまう——Round 1が`human_authority_ref`自身について既に閉じたのと同じ種類の欠落が、一段深いところで再発する。この評価器自身のadmission/binding意味論はRound 4で変更しない。変更するのは、Independent Verificationのroute（`route.py`）がこの評価器へ渡す内容そのものである：routeはgrant内容を直接受理せず、`{"kind": "verifier_selection_grant", "id": ...}`参照のみを受理し、既存Storeの`resolve_record`（`observation_evidence`のtarget解決と同一の呼び出し箇所）を通じて解決した後の、実際にdurably committedされた本体だけを、この評価器へ候補として渡す。解決できない参照はVerifierを呼び出す前に拒否する。これにより`CALLER_ASSERTED_GRANT_AS_PROVENANCE`を閉じるが、第二のAuthority owner・registry・token・cacheは一切追加しない——`evaluate_verifier_selection`自身は不変のままである。

```text
VERIFIER_SELECTION_GRANT_CONTENT_ACCEPTED_AS_CALLER_ARGUMENT=false
VERIFIER_SELECTION_GRANT_REF_RESOLVED_FROM_STORE=true
CALLER_ASSERTED_GRANT_AS_PROVENANCE=false
```

```text
INDEPENDENT_VERIFICATION_DIRECT_STORE_WRITE=false
VERIFIER_SELECTION_DECISION_IMPLIES_CHANGE_EXECUTION=false
VERIFIER_SELECTION_DECISION_IMPLIES_CLOSURE=false
```

**Structural Review Round 5（Issue #51, P13-R5, Canonical Human Grant Declaration Anchor）:** Round 4は grant を Store 解決参照へ限定したが、それでも証明できるのは「この内容が実際に durably committed された」ことだけである——`granted_by`が実在の`human_authority_ref`を複製し、identityが自己無矛盾で、実際に Store へ commit されている grant であっても、それを commit したのが Store 書き込み能力を持つ任意の caller であり、実在する Human ではない可能性は排除されない。`human_authority_ref`は秘密ではないため、Store への durable commission という事実だけでは、その grant を**Humanが宣言した**ことの証明にならない。

この欠落を閉じるのは、第二のAuthority ownerではなく、既存のBinding owner が公開する新しい第二のroute、`declare_human_grant`（`binding/route.py`）が生成する新しい正準record種別、`human_grant_declaration`（`01_SCHEMA/binding/human_grant_declaration.schema.json`）である。この record は特定の`verifier_selection_grant`を`grant_ref`（content-addressed参照）で一意に束縛し、`declared_by`には呼び出し側が供給する値ではなく、`declare_human_grant`自身が実在のProject Bindingから再解決した`human_authority_ref`だけが入る——grant自身の`granted_by`と同型の、しかし独立した第二の束縛である。

```text
CANONICAL_AUTHORITY_OWNER_COUNT=1
NEW_AUTHORITY_OWNER=false
HUMAN_GRANT_DECLARATION_OWNER=BINDING
HUMAN_GRANT_DECLARATION_DECLARED_BY_CALLER_SUPPLIED=false
HUMAN_GRANT_DECLARATION_DECLARED_BY_RESOLVED_FROM_REAL_PROJECT_BINDING=true
```

`evaluate_verifier_selection`は、この Round で`grant_declarations`という新しい必須request keyを受理する——Round 4の`grants`と対になる、`human_grant_declaration`のadmit済み集合である。SELECTEDへ到達する各grantは、この集合の中に、次のすべてを満たすdeclarationを少なくとも一つ持たなければならない。

```text
DECLARATION ANCHORS THIS EXACT GRANT（project_id + grant_ref が一致） → 一致しなければ DECLARATION_MISSING
DECLARATION.declared_by == 実在の human_authority_ref → 不一致なら DECLARATION_AUTHORITY_MISMATCH
DECLARATION.status == ACTIVE → 不一致（REVOKEDなど）なら DECLARATION_NOT_ACTIVE
```

`declaration_ref`（束縛に使われたdeclaration自身への content-addressed参照）は、Round 3が`grant_ref`について確立したのと同じ理由で、決定自身のsemantic identityへ参加する——どのdeclarationが束縛したかも、決定が何であるかの一部である。

```text
VERIFIER SELECTION DECISION IDENTITY INPUT（Round 5で更新）
= project_id + requirement_id + selection_id
+ verifier_identity + permitted_boundary + selection_status
+ selection_authority_ref
+ grant_ref + sorted excluding_grant_refs
+ declaration_ref
+ decision + decision_reason_codes
```

Independent Verificationのroute（`route.py`）は、`human_grant_declaration_refs`という新しい引数を受理し、`verifier_selection_grant_refs`と同一のStore call site（`resolve_record`）を通じて解決する——grant contentがRound 4で直接引数として受理されなくなったのと同じ理由で、declaration contentもこのroute自身の直接引数として受理されない。

```text
HUMAN_GRANT_DECLARATION_CONTENT_ACCEPTED_AS_CALLER_ARGUMENT=false
HUMAN_GRANT_DECLARATION_REF_RESOLVED_FROM_STORE=true
STORE_COMMISSION_ALONE_AS_HUMAN_PROVENANCE=false
```

TRUST_MODEL.mdが既に確立している非暗号学的信頼哲学（`HUMAN_AUTHORITY_STORE_RECORD_REQUIRED=false`、Human Authorityはこのシステムの外部constitutional identityであり、Store recordそのものではない）は、この Round で変更しない。`declare_human_grant`は署名・秘密トークン・隠しregistryのいずれも導入しない——信頼の根拠は、closed admission gate同士の独立したcross-reference一致という、既存の構造的規律のままである。

```text
PHASE_13_ACCEPTANCE=false
PHASE_14_ALLOWED=false
```

**Structural Review Round 5-R1（Issue #51, P13-R5-R1, `ADOPT_P13_R5_R1_SIGNED_HUMAN_DECLARATION_AND_SINGLE_COMMITTER`）:** Round 5は`human_grant_declaration`の durable Store commission と自己無矛盾な形——`grant_ref`による一意束縛、`declared_by`の実在Project Binding再解決、`status == ACTIVE`——を要求したが、これらすべてを満たす record であっても、それを commit したのが実在の Human であることの証明にはならない。`human_authority_ref`が秘密でない以上、Store 書き込み能力を持つ任意の caller が、この形をした record を自ら組み立てて commit できてしまう。Round 5の直前の一文（本節500行目）が述べた「非暗号学的信頼哲学は変更しない」という判断は、この Round で明示的に覆る——SHUKOUの採択は、Human自身の検証可能な署名だけが、この欠落を閉じる唯一の正当な根拠であると判断した。

Project Binding（`03_BINDING/PROJECT_BINDING.md` §11、`01_SCHEMA/binding/project_binding.schema.json#/$defs/signing_key`）は、`human_authority_signing_key`（`{algorithm: "ed25519", key_id, public_key}`）という公開検証鍵を新たに保持する。この鍵は Human 自身の秘密鍵を一切含まない——秘密鍵はこのシステムのどのコードにも触れず、production コードは検証のみを行う（`manosube_agent_civilization.binding.signature`）。

`human_grant_declaration`はRound 5-R1で、`grant_ref`の content address による間接束縛だけでなく、対象grantの`requirement_id`/`selection_id`/`verifier_identity`/`permitted_boundary`を**直接restate**し、かつ自身の`project_id`/`project_binding_id`/`declared_by`/`status`/`declared_at`とあわせて、この完全な payload 全体に対するHuman自身の署名（`signature: {algorithm, key_id, value}`）を運ぶ。署名が保護する payload と content-addressed identity が保護する payload は同一の派生元（`binding.identity.human_grant_declaration_signing_payload`）を共有する——「何を宣言したか」と「何に署名したか」が別々の投影に分裂することはない。`declared_at`はRound 5の`bound_at`型の除外規約に反し、この Round から identity/署名 payload に**参加する**——時刻を束縛しない署名は、任意の後続時点で無限に再生可能になってしまうためである。

```text
HUMAN_GRANT_DECLARATION_SIGNATURE_REQUIRED=true
HUMAN_GRANT_DECLARATION_SIGNATURE_ALGORITHM=ed25519
HUMAN_GRANT_DECLARATION_SIGNING_KEY_OWNER=PROJECT_BINDING
HUMAN_GRANT_DECLARATION_PRIVATE_KEY_TOUCHES_PRODUCTION_CODE=false
HUMAN_GRANT_DECLARATION_RESTATES_GRANT_CONTENT=true
STORE_COMMISSION_ALONE_AS_HUMAN_PROVENANCE=false
CALLER_SUPPLIED_BODY_ALONE_AS_HUMAN_PROVENANCE=false
```

Binding owner自身が、記名前に署名をread-onlyで検証する（`binding.engine.assemble_human_grant_declaration`が`verify_declaration_signature`を呼ぶ）。しかしBindingによる検証は、`evaluate_verifier_selection`自身の**独立した**再検証を代替しない——この評価器は、request自身が新たに運ぶ`human_authority_signing_key`（呼び出し側が実在のProject Bindingから独立に解決した値、Binding自身の以前の検証結果を信頼するのではない）に対して、各候補declarationの署名を自ら再検証する。加えて、declarationが自ら restate した`requirement_id`/`selection_id`/`verifier_identity`/`permitted_boundary`が、束縛対象のgrant自身の同名フィールドと一致することも独立に再確認する（`DECLARATION_CONTENT_MISMATCH`）。署名が無効、または鍵が一致しない場合は`DECLARATION_SIGNATURE_INVALID`で拒否する——いずれも新しい`grant_declarations`束縛段階の理由コードであり、`SELECTED`へ到達する前に評価される。

```text
GRANT BINDS BUT DECLARATION.declared_by != 実在の human_authority_ref → DECLARATION_AUTHORITY_MISMATCH
GRANT BINDS AND DECLARATION.declared_by 一致だが status != ACTIVE → DECLARATION_NOT_ACTIVE
GRANT BINDS AND DECLARATION ACTIVE だが restate 内容が実在grantと不一致 → DECLARATION_CONTENT_MISMATCH
GRANT BINDS AND DECLARATION 内容一致だが署名が実在の human_authority_signing_key で検証できない → DECLARATION_SIGNATURE_INVALID
すべてを満たす → 束縛（SELECTEDの候補）
```

**単一の共有 State-transition commit primitive（R5-R1の第二の要求）:** Round 5が`declare_human_grant`に導入した`store.commit`直接呼び出しは、`topology.py`のK-003/R-001（単一の正準 State-transition committer）静的走査に違反していた——`_SANCTIONED_COMMIT_CALL_MODULES`は`reflow.commit`一箇所のみを許可していたためである。この違反はSHUKOU自身への開示の後、`store/commit.py::commit_state_transition`という、パッケージ内で唯一`.commit(...)`を呼ぶドメイン非依存の pass-through 関数の抽出によって是正された。`reflow.commit.commit_reflow`と`binding.route.declare_human_grant`はいずれも、自身のドメイン意味論（Closure / Human宣言）に従って`next_state`/`transition`/`records`を組み立てた上で、実際の永続化呼び出しだけをこの一つの共有 primitive に委譲する。`topology.py`の`_SANCTIONED_COMMIT_CALL_MODULES`はこの共有 primitive 一箇所のみを指すよう更新され、K-003/R-001はこの唯一の許可された呼び出し箇所を維持する限り引き続きPASSする。

```text
SHARED_STATE_TRANSITION_COMMIT_PRIMITIVE=store.commit.commit_state_transition
SANCTIONED_COMMIT_CALL_MODULE_COUNT=1
BINDING_DIRECT_STORE_COMMIT=false
REFLOW_DIRECT_STORE_COMMIT=false
```

```text
PHASE_13_ACCEPTANCE=false
PHASE_14_ALLOWED=false
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
SCOPE_PATHS_ORDER_SEMANTIC=false
SCOPE_SUBJECTS_ORDER_SEMANTIC=false
CANONICAL_SCOPE_NORMALIZATION_OWNER_COUNT=1
SUPPLIED_RECORD_SCOPE_REWRITTEN=false
AUTHORITY_RESOLVES_SYMLINKS=false
CHRONOLOGICAL_VALIDITY_COMPARISON=true
DECISION_IDENTITY_INCLUDES_PROVENANCE=true
APPROVAL_SELECTION_CANONICAL=true
APPROVAL_EXCLUSION_INDEPENDENT_OF_RULE_LEVEL=true
CITED_RULE_SUPPORTS_THE_DECISION=true
EVALUATION_TIME_ADMITTED_BEFORE_RESOLUTION=true
NONCANONICAL_PAYLOAD_FAILS_THROUGH_THE_PUBLIC_BOUNDARY=true
VERIFIER_SELECTION_DECISION_IMPLEMENTED=true
VERIFIER_SELECTION_DECISION_IDENTITY_INCLUDES_PROVENANCE=true
VERIFIER_SELECTION_GRANT_SAME_ADMISSION_GATE_AS_EXISTING_RECORDS=true
```

```text
AUTHORITY_CONTRACT_DEFINED=true
AUTHORITY_SCHEMA_IMPLEMENTED=true
AUTHORITY_ENGINE_IMPLEMENTED=true
CHANGE_ENGINE_IMPLEMENTED=true
ONE_FULL_NATURAL_CYCLE_PASS=false
```
