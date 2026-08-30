# MANOSUBE Agent Civilization OS

## Difference Closure Policy v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=DIFFERENCE
DOCUMENT_ID=DIFFERENCE-CLOSURE-POLICY-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Purpose

本Policyは、Difference ClosureをChange実行者の自己申告、test pass、PR merge、artifact存在から分離し、after-stateの独立再観測と十分なEvidenceを必須にする。

```text
DIFFERENCE CLOSED
= TARGET SATISFIED
+ AFTER STATE RE-OBSERVED
+ SUFFICIENT RESOLUTION EVIDENCE
+ NO MATERIAL CONTRADICTION
+ POLICY PASS
+ ATOMIC REFLOW
```

# 1. Closure Policy Record

Closure Policyはversioned immutable recordである。

```yaml
schema_version: "0.1"
closure_policy_id: CP-...
policy_version: "0.1"
subject_difference_ref: {kind: difference, id: D-...}
target_predicate_ref: {kind: target_predicate, id: TP-...}
required_observation_scope: null
minimum_evidence_level: E1
required_claims:
  - kind: completion_claim
    id: CLAIM-...
    subject_type: OBJECTIVE_PREDICATE_COMPLETION
    subject_ref: {kind: target_predicate, id: OBJ-PRED-...}
    claim_semantic_fingerprint: sha256:...
required_invariants:
  - kind: kernel_invariant
    id: D-001
    contract_source_ref:
      kind: git_blob
      repository: manosube/manosube-agent-civilization-os
      commit_sha: <40 lowercase hex>
      path: 00_KERNEL/KERNEL_INVARIANTS.md
      blob_sha: <40 lowercase git blob hex>
      invariant_definition_sha256: sha256:<64 lowercase hex>
allowed_terminal_states: [CLOSED, BLOCKED, RETAINED]
independent_verification_required: false
maximum_evidence_age: null
contradiction_policy: FAIL_CLOSED
reopen_conditions:
  - kind: target_predicate
    id: TP-REOPEN-...
    objective_revision_ref: {kind: objective_revision, id: OBJ-REV-...}
    predicate_semantic_fingerprint: sha256:...
```

`maximum_evidence_age`は`null`または非負のJSON integerで表し、単位をSI secondへ固定する。fraction、negative value、float、文字列、ISO-8601 duration、millisecond表現を拒否する。Policy fingerprintにはこのintegerをそのままcanonical numberとして含める。

`policy_semantic_fingerprint`は次のversioned profileで決定的に算出する。

```text
PROFILE=MANOSUBE-CLOSURE-POLICY-SHA256-0.1
DIGEST=SHA-256
OUTPUT=sha256:<64 lowercase hexadecimal characters>
OUTPUT_LENGTH=71
TEXT_NORMALIZATION=UNICODE_NFC
SERIALIZATION=CANONICAL_JSON_UTF8
OBJECT_KEY_ORDER=LEXICOGRAPHIC
UNKNOWN_FIELDS=REJECT
UNORDERED_SETS=required_claims,required_invariants,allowed_terminal_states,reopen_conditions
SET_ORDER=CANONICAL_MEMBER_BYTES
DUPLICATE_SET_MEMBER=REJECT
```

Fingerprint inputのincluded fieldsを次へ固定する。

```text
target_predicate_ref
required_observation_scope
minimum_evidence_level
required_claims
required_invariants
allowed_terminal_states
independent_verification_required
maximum_evidence_age
contradiction_policy
reopen_conditions
```

循環を避けるため、次をfingerprint inputへ含めない。

```text
subject_difference_ref
closure_policy_id
policy_version
schema_version
serialization metadata
```

除外fieldは別のexact provenance bindingとして検証する。特に`subject_difference_ref`は、Policyを使用するDifference IDと一致しなければならない。

Conformance vectorsでは少なくとも、object key順序と上記unordered set順序を変えた同値Policyが同じfingerprintを生成すること、member変更・重複・未知fieldが同一扱いされないことを証明する。

`reopen_conditions`は新しい自由形式Condition recordではない。`00_KERNEL/01_OBJECTIVE/OBJECTIVE_CONTRACT.md`で定義されるTarget Predicateへの次のexact typed referenceだけを許可する。

```yaml
kind: target_predicate
id: TP-REOPEN-...
objective_revision_ref: {kind: objective_revision, id: OBJ-REV-...}
predicate_semantic_fingerprint: sha256:...
```

Predicate fingerprintはObjective semantic canonicalizationに従うpredicate payloadだけから決定し、出力は`sha256:`＋64 lowercase hexとする。`PREDICATE_MODIFY`でsemanticsが変わればfingerprintも変わり、Policy semantic fingerprintとDifference identityも変わる。各refのID／Objective revision／fingerprintはexactに解決可能でなければならず、inline predicate、自由記述condition、unknown kindを拒否する。

Predicate fingerprint profileを次へ固定する。

```text
PROFILE=MANOSUBE-TARGET-PREDICATE-SHA256-0.1
DIGEST=SHA-256
OUTPUT=sha256:<64 lowercase hexadecimal characters>
SERIALIZATION=CANONICAL_JSON_UTF8
TEXT_NORMALIZATION=UNICODE_NFC
INCLUDED_FIELDS=subject,operator,expected_value,observation_scope,evidence_requirement,unknown_policy,criticality
EXCLUDED_FIELDS=predicate_id,objective_revision_ref,recorded_at,metadata
UNKNOWN_FIELDS=REJECT
COLLECTION_SEMANTICS=EXPLICIT_KIND_WRAPPER
BARE_ARRAY=REJECT
```

Predicate semantic fields内のcollectionは`{"collection_kind":"ORDERED_LIST","members":[]}`または`{"collection_kind":"UNORDERED_SET","members":[]}`だけを許可する。前者は順序を保持し、後者はcanonical member bytesで整列してduplicateを拒否する。

Conformance vectorsはobject key順序の不変性、各included field変更によるdigest変更、excluded provenance変更によるdigest不変性、unordered collection順序の不変性、ordered collection順序変更によるdigest変更、unknown field／bare array rejectを含む。

Policy fingerprintへ投入する各`reopen_conditions` memberは、`kind + id + predicate_semantic_fingerprint`だけのclosed semantic projectionとする。`objective_revision_ref`はexact provenance検証には必須だがPolicy semantic fingerprintから除外する。同じpredicate ID／semanticsを保持するEDITORIAL Objective revision更新ではPolicy fingerprintを変えず、predicate semantic fingerprint変更時だけ変える。

`required_claims` memberは上記例のclosed five-field objectだけを許可する。`claim_semantic_fingerprint`はCompletion Recordの`subject_type`、`subject_ref`、`claim`、`target_state_ref`だけから同じcanonical JSON／SHA-256出力規則で算出する。

全Policy-required Claimのstable IDはmandatory X-003と同じnamespace規則へ統一する。ID inputは次のclosed projectionだけである。

```json
{
  "subject_type": "OBJECTIVE_PREDICATE_COMPLETION",
  "subject_ref": {},
  "claim_semantic_fingerprint": "sha256:..."
}
```

`claim_identity_digest = SHA-256(UTF8("MANOSUBE:COMPLETION_CLAIM_IDENTITY:0.1:") || CANONICAL_JSON_UTF8(closed_projection))`、`id = "CLAIM-" || uppercase_hex(claim_identity_digest)`とする。`kind`と`id`自身はinputへ含めない。同じsemantic Claimへ別IDを割り当てること、同じIDへ別projectionを割り当てることを拒否する。mandatory X-003もこのgeneral algorithmを使用し、専用domainで別ID空間を作らない。

Fingerprint循環を避けるため、Completion Recordの`closure_policy_ref`、completion ID、evaluation status、Evidence refsをclaim semantic fingerprintへ含めない。Claim側Policy bindingは`candidate_claim_evaluation_bindings`を解決するG21で別途exact検証し、現在のClosure Policyを自己参照させない。

`required_invariants` memberは上記例のclosed three-field objectだけを許可する。Markdown blockを別のcanonical objectへ変換せず、Gitが権威的に計算するexact source blobへ固定する。`repository + commit_sha + path + blob_sha`が同一blobへ解決され、そのblob内にexact Invariant IDが一意に存在することを要求する。

Policy semantic fingerprintへ投入する`required_invariants` memberは、provenance record全体ではなく次のclosed semantic projectionである。

```yaml
kind: kernel_invariant
id: D-001
contract_source_blob:
  kind: git_blob
  repository: manosube/manosube-agent-civilization-os
  path: 00_KERNEL/KERNEL_INVARIANTS.md
  invariant_definition_sha256: sha256:<64 lowercase hex>
```

`invariant_definition_sha256`は、指定Invariant IDに属する完全な定義blockをContract parserで抽出し、UTF-8、Unicode NFC、LF改行、末尾改行1個へ正規化したbytesのSHA-256である。抽出はInvariant見出し開始から始め、次に現れる同levelまたは上位levelのMarkdown ATX heading直前で必ず停止し、見出しがなければEOFで停止する。停止headingがInvariant見出しかsection見出しかは問わず、停止heading自体を含めない。開始見出し、ID行、NAME、本文、全code blockを含む。fenced code block内の`#`はheadingとして扱わない。

Registry grammarでは、code fence外にあり、Invariant block末尾のblank line群を除いた最後のlineで、かつ後続する最初のnonblank lineが停止headingである単独`---`だけを`INVARIANT_SECTION_DELIMITER`と定義する。この位置の`---`はInvariant bodyではなくdelimiterでありdigestから除外する。`***`、`___`、Invariant途中の`---`、fenced code内の`---`は常にbody contentとして保持する。Invariantを視覚的なthematic breakで終える必要がある場合は`***`／`___`またはfenced literalを使用し、delimiter位置の`---`をbodyとして解釈してはならない。

停止後、末尾blank lineを除去し、上記grammarに一致する`INVARIANT_SECTION_DELIMITER`が一つあればそれだけを除去し、再度末尾blank lineを除去してから末尾改行1個を付与する。これによりdelimiter判定はtrailing positionだけでなく、exact token、fence state、後続headingとの関係で一意になる。抽出不能、ID欠落・重複、正規化後digest不一致を拒否する。

`commit_sha`とwhole-file `blob_sha`はexact provenance検証には必須だがsemantic projectionから除外する。同じInvariant定義が別commit、別whole-file blobに存在してもPolicy fingerprintを変えない。repository、path、Invariant IDまたは`invariant_definition_sha256`の変更はfingerprintを変える。

これによりheading由来のID／NAME、multiline `REQUIRED_FIELDS`、Invariant固有fieldを含む選択定義blockだけがcontent-addressed semantic bindingへ入る。選択Invariantの定義が一文字でも変わればdefinition digestとPolicy fingerprintが変わるが、同一file内の無関係なInvariantまたはprose変更では変わらない。moving branch、default branch、working tree、line rangeだけの参照を禁止する。unknown kind、SHA形式不正、commit／blob不一致、definition digest不一致、ID欠落・重複を拒否する。

PolicyはDifference導出時に固定する。実装失敗またはEvidence不足に合わせて弱化してはならない。

# 2. Closure Evaluation Record

```yaml
schema_version: "0.1"
closure_evaluation_id: D-CLOSE-EVAL-...
difference_id: D-...
difference_event_head_ref: {kind: difference_event, id: D-EVT-...}
target_predicate_ref: {kind: target_predicate, id: TP-...}
objective_revision_ref_evaluated: {kind: objective_revision, id: OBJ-REV-...}
objective_semantic_fingerprint_evaluated: {}
before_state_ref: {}
resolution_mode: CHANGE_BOUND
change_refs: []
after_state_candidate:
  kind: after_state_candidate
  candidate_id: STATE-CANDIDATE-...
  base_state_ref: {kind: state, revision: 0, fingerprint: {}}
  semantic_state: {}
  semantic_fingerprint: {}
  source_snapshot_refs:
    collection_kind: UNORDERED_SET
    members: []
  producing_change_refs:
    collection_kind: UNORDERED_SET
    members: []
after_observation_refs: []
change_result_evidence_refs: []
change_free_verification_evidence_refs: []
verification_independence_ref: null
evidence_sufficiency_ref: {}
candidate_invariant_evaluation_bindings: []
candidate_claim_evaluation_bindings: []
contradiction_refs: []
evaluated_state_revision: 0
evaluated_state_fingerprint: {}
evaluated_at: "2026-01-01T00:00:00Z"
evaluation_expires_at: null
policy_ref: {kind: closure_policy, id: CP-..., version: "0.1", semantic_fingerprint: sha256:...}
policy_version_evaluated: "0.1"
policy_semantic_fingerprint_evaluated: sha256:...
proposed_terminal_status: CLOSED
gate_results:
  G1: PASS
  G2: PASS
  G3: PASS
  G4: PASS
  G5: PASS
  G6: PASS
  G7: PASS
  G8: PASS
  G9: PASS
  G10: PASS
  G11: PASS
  G12: PASS
  G13: PASS
  G14: PASS
  G15: PASS
  G16: PASS
  G17: PASS
  G18: PASS
  G19: PASS
  G20: PASS
  G21: PASS
  G22: PASS
result: NOT_EVALUATED
failure_reasons: []
reflow_transition_ref: null
```

Evaluation resultは`COMPLETION_SEMANTICS.md`のCanonical Completion Evaluation Statusと完全に同じclosed enumとする。

```text
NOT_EVALUATED
EVALUATING
SATISFIED
NOT_SATISFIED
BLOCKED
STALE
CONTRADICTED
REVOKED
```

`gate_results`はG1からG22までをexactly once保持するclosed mapで、各値は`PASS | FAIL | UNKNOWN | NOT_APPLICABLE`のclosed enumである。G22はClosure全体のaggregate `result`とは独立に永続化し、`CLOSED`、`BLOCKED`、`RETAINED`へのLifecycle transitionはexact Evaluationの`proposed_terminal_status`がto-statusと一致し、かつ`gate_results.G22=PASS`であることを要求する。`BLOCKED`または`RETAINED`用Evaluationは他gateがFAIL／UNKNOWNでもG22を独立評価でき、aggregate `result=SATISFIED`を要求しない。`CLOSED`だけは全mandatory gateがPASSでaggregate `result=SATISFIED`でなければならない。

# 3. Mandatory Closure Gates

`SATISFIED`には次の全条件を要求する。

```text
G1  DIFFERENCE_ID_VALID
G2  DIFFERENCE_STATUS_VERIFYING
G3  OBJECTIVE_SEMANTIC_FINGERPRINT_EXACT
G4  TARGET_PREDICATE_EXACT
G5  BEFORE_STATE_EXACT
G6  RESOLUTION_MODE_BINDING_EXACT
G7  AFTER_STATE_NEWER_AND_EXACT
G8  INDEPENDENT_REOBSERVATION_PRESENT
G9  REQUIRED_OBSERVATION_SCOPE_EXACT
G10 OBSERVED_TARGET_SATISFIED
G11 RESOLUTION_EVIDENCE_PRESENT
G12 EVIDENCE_LEVEL_SUFFICIENT
G13 OBSERVATION_SCOPE_COMPLETE
G14 NO_BLOCKING_BLIND_SPOT
G15 NO_UNKNOWN_OR_UNOBSERVED_INPUT
G16 NO_FAILED_OR_INVALID_INPUT
G17 NO_UNRESOLVED_CONFLICT
G18 EVIDENCE_FRESHNESS_AND_BINDINGS_CURRENT
G19 INVARIANTS_PASS
G20 ATOMIC_REFLOW_PRECONDITIONS_PASS
G21 ALL_REQUIRED_CLAIMS_SATISFIED
G22 PROPOSED_TERMINAL_STATE_ALLOWED
```

一つでもfalseまたはunknownなら`SATISFIED`にしない。

`after_state_candidate`はCanonical Stateではなく、Atomic Reflowへ提案されるclosed staged recordである。`candidate_id`は次のprofileで決定的に生成する。

```text
PROFILE=MANOSUBE-AFTER-STATE-CANDIDATE-SHA256-0.1
DIGEST=SHA-256
DOMAIN_SEPARATOR=MANOSUBE:AFTER_STATE_CANDIDATE:0.1:
SERIALIZATION=CANONICAL_JSON_UTF8
TEXT_NORMALIZATION=UNICODE_NFC
OBJECT_KEY_ORDER=LEXICOGRAPHIC
UNORDERED_SETS=source_snapshot_refs,producing_change_refs
SET_ORDER=CANONICAL_MEMBER_BYTES
DUPLICATE_SET_MEMBER=REJECT
UNKNOWN_FIELDS=REJECT
OUTPUT=STATE-CANDIDATE-<64 uppercase hexadecimal characters>
```

ID canonical payloadは次のclosed objectである。

```json
{
  "base_state_ref": {},
  "producing_change_refs": {"collection_kind":"UNORDERED_SET","members":[]},
  "semantic_fingerprint": {},
  "semantic_state": {},
  "source_snapshot_refs": {"collection_kind":"UNORDERED_SET","members":[]}
}
```

`kind`、`candidate_id`、profile nameをpayload fieldとして含めない。digest input bytesは、ASCII／UTF-8でexactなdomain separator `MANOSUBE:AFTER_STATE_CANDIDATE:0.1:`の末尾colonを含むbytesへ、直後にseparatorや改行を追加せずcanonical payload UTF-8 bytesを連結したものである。

```text
candidate_digest =
SHA-256(
  UTF8("MANOSUBE:AFTER_STATE_CANDIDATE:0.1:")
  ||
  CANONICAL_JSON_UTF8(closed_payload)
)

candidate_id =
"STATE-CANDIDATE-" || uppercase_hex(candidate_digest)
```

collectionはexplicit duplicate-free `UNORDERED_SET` wrapperだけを許可し、bare arrayを拒否する。固定payload／digest、key順序、set順序、duplicate、included field変更のconformance vectorsを公開する。base StateはEvaluation時点のcurrent Canonical revision／fingerprintへexactに結合し、source snapshotsはimmutable content-addressed refsでなければならない。

After-state Observationは存在しない未来revisionへ結合しない。Observation Contract上のState bindingは`base_state_ref`へ結合し、観測対象と結果provenanceはcandidateのimmutable `source_snapshot_refs`へexactに結合する。

Observation wireの`source_snapshot_refs` bare arrayは既存Schema互換のまま保持する。Candidateとのexact比較では、Observation arrayをduplicate拒否後に各memberのcanonical bytesで昇順整列し、`{"collection_kind":"UNORDERED_SET","members":[...]}`へ投影する`MANOSUBE-OBSERVATION-SNAPSHOT-SET-PROJECTION-0.1`を使用する。Candidate側wrapperとのmember canonical bytes集合が完全一致しなければならない。順序だけの差は同値、duplicate、unknown member field、解決不能refはrejectする。Observationから導出されたsemantic factsが`semantic_state`および`semantic_fingerprint`と一致することをG7〜G10で検証する。

`after_state_candidate`はClosure EvaluationだけではCanonicalにならない。G20 PASS後のAtomic Reflowがcurrent base revisionをCAS確認し、candidate semantic stateをrevision N+1としてcommitする。base revision／fingerprintまたはsource snapshotが変化した場合はEvaluationを`STALE`としてrejectする。

`G3`はClosure Evaluation時点のactive `objective_revision_ref_evaluated`をexact provenanceとして保存し、その`objective_semantic_fingerprint_evaluated`がDifference identityに結合されたfingerprintと一致することを要求する。EDITORIAL revisionではrevision refの変更を許すがsemantic fingerprintの変更を許さない。semantic fingerprintが変わった場合はClosureせず、新しいDifference identityへsupersedeする。

`G6`と`G11`は`resolution_mode`により分岐する。

```text
CHANGE_BOUND
→ change_refs NON-EMPTY
→ exact before Canonical State／after-state candidate binding
→ change_result_evidence_refs NON-EMPTY
→ change_free_verification_evidence_refs EMPTY

CHANGE_FREE
→ change_refs EMPTY
→ change_result_evidence_refs EMPTY
→ change_free_verification_evidence_refs NON-EMPTY
→ independent after-state Observation Evidence proves the Target directly
```

`CHANGE_FREE`はEvidence要件の免除ではない。`REOPENED → VERIFYING`など、変更を必要とせず新しい観測でTarget Satisfactionを再検証する経路でのみ使用し、Observation Evidence、scope completeness、Evidence Sufficiencyおよび全required claimsを通常どおり評価する。Changeが存在しないことを理由に`G11`を自動PASSさせてはならない。

`G9`はafter-state Observationのeffective scopeをCanonical field `required_observation_scope`と照合する。

```text
required_observation_scope = null
→ additional scope constraintなし
→ ただしObservation自身のdefined scope、completion、blind spot gateは必須

required_observation_scope ≠ null
→ after-state Observation effective scopeとexact match必須
```

method、normalization profileおよびschema versionの追加制約が必要な場合は`required_claims`としてversioned identityを指定し、scope fieldへ暗黙に混在させない。単に独立したObservationが存在するだけでは満たさない。

`G21`のexpected claim setは次の和集合であり、Closure Policyの`required_claims`が空でもv0.1 mandatory claimを免除しない。

```text
EXPECTED_COMPLETION_CLAIMS
=
MANDATORY_V0_1_COMPLETION_CLAIMS
UNION
CLOSURE_POLICY.required_claims
```

v0.1の`MANDATORY_V0_1_COMPLETION_CLAIMS`は、`KERNEL_INVARIANTS.md`のv0.1 Mandatory GateでX-003に代えて要求される次の一件だけである。

```yaml
kind: completion_claim
id: CLAIM-<64 uppercase hex>
subject_type: CONTRACT_COMPLETION
subject_ref: {kind: kernel_invariant, id: X-003}
claim_semantic_fingerprint: sha256:<64 lowercase hex>
```

このdescriptorが参照するCompletion Recordのclosed claim projectionを次へ固定する。

```json
{
  "subject_type": "CONTRACT_COMPLETION",
  "subject_ref": {"kind":"kernel_invariant","id":"X-003"},
  "claim": {
    "AGENT_REQUIRED_FOR_KERNEL": false,
    "SESSION_INDEPENDENT": true
  },
  "target_state_ref": null
}
```

上記closed claim projectionから通常のclaim semantic fingerprintを算出し、その`subject_type + subject_ref + claim_semantic_fingerprint`を第1章のgeneral `MANOSUBE:COMPLETION_CLAIM_IDENTITY:0.1:` algorithmへ入力してstable `CLAIM-` IDを生成する。producerが別ID、別claim、別targetを選ぶことを禁止する。この`CLAIM-` IDはsemantic Claim identityであり、candidate固有のCanonical Completion Record IDではない。

G21 binding集合はEXPECTED COMPLETION CLAIMSのexact identity集合と完全一致し、mandatory X-003 bindingの欠落、余分、duplicateをrejectする。Policy claimと同じIDが重なる場合はsubject type、subject ref、claim fingerprintが完全一致するときだけ一件へ統合し、不一致は`BLOCKED`とする。各expected claimについて、exact claim identity、evaluated candidate State、Evidence references、Completion Evaluation statusを解決し、全件が`SATISFIED`であることを要求する。

```text
REQUIRED CLAIM NOT_EVALUATED → CLOSURE NOT SATISFIED
REQUIRED CLAIM EVALUATING → CLOSURE NOT SATISFIED
REQUIRED CLAIM NOT_SATISFIED → CLOSURE NOT SATISFIED
REQUIRED CLAIM BLOCKED / STALE / CONTRADICTED / REVOKED
→ CLOSURE NOT SATISFIED
```

`G19`のexpected invariant setは次の和集合である。

```text
EXPECTED_INVARIANTS
=
APPLICABLE_V0_1_MANDATORY_INVARIANTS
UNION
CLOSURE_POLICY.required_invariants
```

`APPLICABLE_V0_1_MANDATORY_INVARIANTS`のauthority sourceは、Closure Evaluation時点でexact Git blobへ固定した`00_KERNEL/KERNEL_INVARIANTS.md`の`# 16. v0.1 Mandatory Gate`だけである。producerが`mandatory_in_v0_1`、`applies_to`または除外flagを供給することを禁止する。v0.1では同Gateの`ID PASS`行をauthoritative source setとする。G19はpre-Reflow Difference Closure gateであるため、source setからversion-level post-Reflow invariant `P-003`だけを除いた集合をmandatory setとする。この除外はproducer入力ではなく本profileの固定phase ruleであり、追加除外を認めない。`P-003`はAtomic Reflow後の`VERSION_COMPLETION`で必ず評価し、Difference Closure PASSをv0.1 natural-cycle PASSへ昇格させてはならない。

versioned authoritative derivation profileを次へ固定する。

```text
PROFILE=MANOSUBE-V0_1-MANDATORY-INVARIANT-REGISTRY-0.1
AUTHORITY_SOURCE=00_KERNEL/KERNEL_INVARIANTS.md
SOURCE_SECTION=# 16. v0.1 Mandatory Gate
ENTRY_GRAMMAR=^(K|A|S|O|D|C|E|R|B|X|P)-[0-9]{3} PASS$
ENTRY_ORDER=SOURCE_ORDER
DUPLICATE_ID=REJECT
UNKNOWN_LINE_IN_TEXT_FENCE=REJECT
SOURCE_SET=ALL_DERIVED_ENTRIES
G19_PHASE=PRE_REFLOW_DIFFERENCE_CLOSURE
G19_EXCLUDED_POST_REFLOW_IDS=P-003
G19_REQUIRED_SET=SOURCE_SET_MINUS_EXACTLY_P-003
P-003_EVALUATION_PHASE=POST_REFLOW_VERSION_COMPLETION
PRODUCER_SELECTOR_FIELDS=FORBIDDEN
```

parserはexact heading直後の説明文に続く最初の`text` fenced blockだけを読み、上記grammarへ一致する各lineをsource orderで抽出する。blank lineだけを無視し、未知line、重複ID、二つ目のcandidate block、heading欠落を拒否する。`X-003`の限定Claimは同blockに`X-003 PASS`として存在しないためInvariant binding集合へ捏造せず、直後の限定ClaimをG21のCompletion claimとして別途評価する。

この導出結果から、次のauthoritative registry instanceを機械生成する。

```yaml
schema_version: "0.1"
profile: MANOSUBE-V0_1-MANDATORY-INVARIANT-REGISTRY-0.1
registry_id: V01-MANDATORY-INV-REG-...
authority_source_ref:
  kind: git_blob
  repository: manosube/manosube-agent-civilization-os
  commit_sha: <40 lowercase hex>
  path: 00_KERNEL/KERNEL_INVARIANTS.md
  blob_sha: <40 lowercase git blob hex>
source_section_sha256: sha256:<64 lowercase hex>
entries:
  collection_kind: ORDERED_LIST
  members:
    - invariant_id: K-001
      invariant_definition_sha256: sha256:<64 lowercase hex>
registry_semantic_fingerprint: sha256:<64 lowercase hex>
```

`source_section_sha256`はheading開始から次の同levelまたは上位heading直前までを第1章と同じUTF-8／NFC／LF／末尾改行規則で正規化したbytesのSHA-256である。各entryのdefinition digestは第1章のInvariant block抽出規則で同一source blobから再計算する。entriesは抽出された全IDをsource orderでexactly once含み、追加・欠落・並べ替え・selector fieldを拒否する。 Registryはsource set全体を保持する。G19 expected invariant setを作る際だけ`P-003`をexactly one除外し、`P-003`不在、重複または他ID除外をrejectする。

registry digestは`registry_id`、commit SHA、whole-file blob SHAを除き、`profile + schema_version + repository + path + source_section_sha256 + entries`のclosed projectionをcanonical JSON UTF-8化し、domain `MANOSUBE:V0_1_MANDATORY_INVARIANT_REGISTRY:0.1:`のexact UTF-8 bytesをseparatorなしで前置してSHA-256する。

```text
registry_digest =
SHA-256(
  UTF8("MANOSUBE:V0_1_MANDATORY_INVARIANT_REGISTRY:0.1:")
  ||
  CANONICAL_JSON_UTF8(closed_projection)
)

registry_semantic_fingerprint =
"sha256:" || lowercase_hex(registry_digest)

registry_id =
"V01-MANDATORY-INV-REG-" || uppercase_hex(registry_digest)
```

したがって同じauthoritative source semanticsから別IDを選べず、任意IDを受理しない。registry instance、source blob ref、section digest、registry fingerprintをEvaluation Evidenceへ保存し、Atomic Reflow直前に再導出してIDとfingerprintをexact一致確認する。producer-supplied registry、未承認fingerprint allowlist、手動applicability overrideは受理しない。欠落、解決不能、digest不一致、再導出不一致は`BLOCKED`であり、mandatory setを空集合へ縮小してはならない。

Canonical Invariant Evaluation Recordを変更せず、expected setを作る前に同一Invariant IDの定義を照合する。Applicability Registry entryと`CLOSURE_POLICY.required_invariants`が同じIDを要求する場合、両者の`repository + path + invariant_definition_sha256`が完全一致するときだけ一件へ統合する。一つでも異なる場合はdefinition conflictとして`BLOCKED`にし、先勝ち、後勝ち、IDだけのdeduplicationを禁止する。

expected setの各memberは`invariant_id + repository + path + invariant_definition_sha256`でqualifyされたrequirementである。各requirementについて次のclosed Difference-owned bindingを`candidate_invariant_evaluation_bindings`へexactly one保存する。Bindingのqualified requirement集合はexpected setと完全一致し、missing、extra、duplicateをrejectする。

```yaml
kind: candidate_invariant_evaluation_binding
binding_id: CAND-INV-EVAL-...
candidate_id: STATE-CANDIDATE-...
candidate_semantic_fingerprint: {}
base_state_ref: {kind: state, revision: 0, fingerprint: {}}
invariant_ref: {kind: kernel_invariant, id: D-001}
invariant_definition_ref:
  repository: manosube/manosube-agent-civilization-os
  path: 00_KERNEL/KERNEL_INVARIANTS.md
  invariant_definition_sha256: sha256:<64 lowercase hex>
invariant_evaluation_ref: {kind: invariant_evaluation, id: INV-EVAL-...}
evaluation_record_fingerprint: sha256:...
evaluation_result: PASS
evaluation_evidence_refs: {collection_kind: UNORDERED_SET, members: []}
evaluated_at: "2026-01-01T00:00:00Z"
```

Binding IDはID自身を除く全closed fieldのcanonical JSON UTF-8／SHA-256から`CAND-INV-EVAL-`＋64 uppercase hexとして生成する。 Binding profileは`MANOSUBE-CANDIDATE-EVALUATION-BINDING-SHA256-0.1`とし、`evaluation_evidence_refs`をduplicate-free `UNORDERED_SET`としてcanonical member bytes順に整列する。bare array、duplicate、unknown fieldをrejectする。`evaluation_record_fingerprint`は`MANOSUBE-RESOLVED-EVALUATION-RECORD-SHA256-0.1`が定義する次のrecord-kind別closed projectionから算出する。

```text
COMPLETION_RECORD_SCALARS=
completion_id,subject_type,subject_ref,claim,target_state_ref,
observed_state_ref,closure_policy_ref,evaluation_status,
evaluated_state_revision,evaluated_state_fingerprint,evaluated_at

COMPLETION_RECORD_UNORDERED_SETS=
required_evidence_refs,invariant_evaluation_refs,material_contradiction_refs

INVARIANT_EVALUATION_SCALARS=
evaluation_id,invariant_id,subject_ref,state_revision,state_fingerprint,
verification_stage,method,expected,observed,status,evaluated_at,
evaluator_capability,authority_ref

INVARIANT_EVALUATION_UNORDERED_SETS=
evidence_refs,remaining_differences
```

Bare array fields listed as unordered sets areduplicate拒否後にcanonical member bytes順へ整列し、explicit `UNORDERED_SET` wrapperへ投影する。scalar `observed`内にcollectionがある場合はexplicit collection wrapperを必須とし、未定義bare arrayをrejectする。unknown field、欠落required field、非canonical valueをrejectする。

Fingerprint bytesはrecord kind domain `MANOSUBE:COMPLETION_RECORD:0.1:`または`MANOSUBE:INVARIANT_EVALUATION:0.1:`のexact UTF-8 bytesと、closed projectionのcanonical JSON UTF-8 bytesを追加separatorなしで連結したものとする。SHA-256出力は`sha256:`＋64 lowercase hexである。timestamp、Evidence refs、status／resultを含む。ただしCompletion Recordの`reflow_transition_ref`はAtomic Reflow後にのみ設定されるpost-commit lineage fieldとしてprojectionから除外する。この除外によりpre-promotion bindingを循環させず、transition ref設定だけではstaleにしない。他のincluded fieldが一byteでも変わればpre-promotion recheckでSTALEとして拒否する。

Bindingはqualified expected requirementのInvariant ID、repository、path、definition digestとexact一致し、underlying Invariant EvaluationのInvariant、result、Evidence、evaluated_at、record fingerprintともexact一致する。Evaluation Evidenceは同じdefinition digestのInvariantをcandidate semantic state bytesへ適用したことを証明する。IDだけが一致する別definition、base Stateだけを評価したrecord、definition provenanceを解決できないrecordを流用しない。

Atomic Reflow直前にbindingとunderlying recordを再解決し、candidate ID／semantic fingerprint、record fingerprint、resultおよびEvidence refsが不変かつPASSであることを再検査する。欠落、余分、duplicate、STALE相当のfingerprint変更、Evidence失効、非PASSを一件でも検出した場合はpromotionをrejectする。Policy required setが空でもapplicable mandatory setは免除しない。両集合の和が空である場合だけbinding setを空にでき、その適用判定Evidenceを必須とする。

`G22`は`proposed_terminal_status`が`CLOSED | BLOCKED | RETAINED`のclosed enumに属し、かつPolicyの`allowed_terminal_states`に明示されていることを要求する。未許可statusへのEvaluationを`SATISFIED`にせず、Lifecycle transitionも拒否する。各statusについて別Evaluationを生成し、あるstatusの許可を別statusへ流用しない。

`policy_ref`、`policy_version_evaluated`および`policy_semantic_fingerprint_evaluated`は、Difference Recordに固定されたPolicy ID／version／semantic fingerprintと同一Policyへexactに解決されなければならない。さらにPolicyの`subject_difference_ref`をDifference IDとexactに照合する。

Current Policyのversionだけが進みsemantic fingerprintが同一の場合、Difference-bound versionによるEvaluationを`STALE`にしない。Current Policyのsemantic fingerprintが異なる場合は旧Differenceを新identityへsupersedeし、旧bindingを新Policyへ読み替えない。

`G8`はChange result、Change executor report、command return、test outputとは別に生成されたafter-state Observationを常に要求する。独立性の最小意味は、Change自身がClosureを自己確定せず、Observation Contractに準拠した新しいObservation recordがcurrent base Stateとimmutable candidate source snapshotsへexactに結合されることである。

```text
CHANGE RESULT
≠
AFTER-STATE OBSERVATION

CHANGE EXECUTOR CLAIM
≠
DIFFERENCE CLOSURE
```

v0.1 Difference Contractは、暗号鍵、署名、trust root、issuer identity、executor identityまたはAuthority Decisionのwire contractを所有しない。これらは後続の`05_AUTHORITY/`、`06_CHANGE/`、`07_EVIDENCE/`が定義する。

`independent_verification_required`は将来のPolicy互換fieldとして保持するが、Difference v0.1では`false`だけを許可する。`true`のPolicyは`UNSUPPORTED_AUTHORITY_CONTRACT`としてFail-Closedでrejectし、`verification_independence_ref`は常にnullでなければならない。後続Contractが独立実行主体と認証済みprovenanceを定義した後、schema version更新とPolicy semantic fingerprint変更を伴ってのみ`true`を有効化できる。

この制約は再観測を免除しない。`independent_verification_required=false`でも、G7からG18、Observation scope completeness、blind spot、Evidence Sufficiency、conflictおよびfreshness gateをすべて通常どおり評価する。

`G21`は各required claimについて、Canonical Completion Evaluation Recordを変更せず、次のclosed Difference-owned bindingを`candidate_claim_evaluation_bindings`へexactly one保存する。

```yaml
kind: candidate_claim_evaluation_binding
binding_id: CAND-CLAIM-EVAL-...
difference_id: D-...
policy_ref: {kind: closure_policy, id: CP-..., version: "0.1", semantic_fingerprint: sha256:...}
candidate_id: STATE-CANDIDATE-...
candidate_semantic_fingerprint: {}
base_state_ref: {kind: state, revision: 0, fingerprint: {}}
required_claim_ref: {kind: completion_claim, id: CLAIM-...}
evaluation_series_id: CAND-CLAIM-SERIES-...
evaluation_head_event_ref: {kind: candidate_claim_evaluation_event, id: CAND-CLAIM-EVT-..., revision: 0}
completion_record_ref: {kind: completion_record, id: CMP-...}
evaluation_record_fingerprint: sha256:...
evaluation_status: SATISFIED
evaluation_evidence_refs: {collection_kind: UNORDERED_SET, members: []}
evaluated_at: "2026-01-01T00:00:00Z"
```

Candidate固有の`completion_record_ref.id`は、Completion Recordから`completion_id`とpost-commit `reflow_transition_ref`だけを除いた第3章のclosed Completion Record projectionへ、domain `MANOSUBE:CANDIDATE_COMPLETION_RECORD:0.1:`を前置してSHA-256し、`"CMP-" || uppercase_hex(digest)`として生成する。このprojectionは`observed_state_ref`、`closure_policy_ref`、evaluated State revision／fingerprint、Evidence refs、evaluation status、evaluated_atを含むため、同じstable Claimを別candidate、別Policy、別時点で評価したrecordは別IDになる。同一record IDの異なるpayloadはconflictとして拒否する。

Completion Recordの更新履歴は、次のDifference-owned append-only series eventで連結する。

```yaml
kind: candidate_claim_evaluation_event
event_id: CAND-CLAIM-EVT-...
evaluation_series_id: CAND-CLAIM-SERIES-...
event_revision: 0
predecessor_event_ref: null
difference_id: D-...
policy_ref: {kind: closure_policy, id: CP-..., version: "0.1", semantic_fingerprint: sha256:...}
candidate_id: STATE-CANDIDATE-...
required_claim_ref: {kind: completion_claim, id: CLAIM-...}
completion_record_ref: {kind: completion_record, id: CMP-...}
completion_record_fingerprint: sha256:...
evaluation_status: SATISFIED
recorded_at: "2026-01-01T00:00:00Z"
```

`evaluation_series_id`は`difference_id + policy_ref + candidate_id + required_claim_ref`のclosed projectionへdomain `MANOSUBE:CANDIDATE_CLAIM_EVALUATION_SERIES:0.1:`を前置したSHA-256をuppercase hex化し、`CAND-CLAIM-SERIES-`へ連結する。`policy_ref`はEvaluation対象Differenceに固定されたexact Policy ID／version／semantic fingerprintでなければならない。同じcandidate／ClaimでもDifferenceまたはPolicyが異なれば別seriesとなり、一方のhead更新が他方をstale化してはならない。event revisionは0から連続し、predecessorは直前eventへexactに結合する。event IDはID自身を除く全closed fieldへdomain `MANOSUBE:CANDIDATE_CLAIM_EVALUATION_EVENT:0.1:`を前置したSHA-256のuppercase hexを`CAND-CLAIM-EVT-`へ連結する。同一event ID／同一payloadはidempotent、異なるpayloadはconflictである。

新しいSATISFIED、STALE、REVOKEDその他のCompletion Recordが生じるたび同じseriesへeventをappendする。Candidate bindingの`evaluation_head_event_ref`はEvaluation時点の連続series headを指す。

Binding IDと検証規則はG19 bindingと同じcanonical profileを使用し、prefixだけを`CAND-CLAIM-EVAL-`とする。 両binding IDはSHA-256 digestをuppercase hexadecimalでprefixへ連結し、semantic fingerprintだけをlowercase `sha256:`形式で表す。 `evaluation_evidence_refs`も同じexplicit duplicate-free `UNORDERED_SET` wrapperを使用する。Underlying Completion Recordのclaim、status、Evidence、time、record fingerprintとexact一致し、candidate semantic stateを評価対象としたことを証明する。base State評価の流用を禁止する。

Atomic Reflow直前に各`evaluation_series_id`のappend-only event chainをrevision 0から再構築し、最新head eventを解決する。bindingの`evaluation_head_event_ref`がその最新headとexact一致し、headが参照するCompletion Record／fingerprint／status／Evidenceもbindingとexact一致する場合だけcurrentとする。後続event、gap、fork、predecessor不一致、`REVOKED`、`STALE`、fingerprint／Evidence変更、candidate mismatch、非SATISFIEDを一件でも検出した場合はpromotionをrejectする。古いSATISFIED recordを直接参照して最新head解決を省略してはならない。

# 4. Independent Re-observation

Change result、command return code、test output、Agent reportはafter-state Observationの代替ではない。

```text
CHANGE EXECUTION RESULT
→ RE-OBSERVATION REQUEST
→ NORMALIZED AFTER FACTS
→ CHANGE RESULT EVIDENCE
→ CLOSURE EVALUATION
```

独立性とは、Change自身が自身の成功flagをClosure Predicateとして供給しないことを意味する。同じprocessが技術的に観測する場合でも、Observation method、input snapshot、result schema、Evidence identityをChange resultから分離する。

# 5. Evidence Sufficiency

Evidence levelは現存するCanonical定義`00_KERNEL/COMPLETION_SEMANTICS.md`第3章「Evidence Levelとの対応」のclosed ordered scale `E0 < E1 < E2 < E3 < E4 < E5 < E6`に従う。G12はこのexact sourceをcontent-addressed blob refで解決し、unknown level、順序不明またはsource不一致を`BLOCKED`とする。要求level未満のEvidenceを件数で補ってはならない。

```text
EVIDENCE COUNT ≠ EVIDENCE STRENGTH
TEST PASS ≠ RUNTIME PROVEN
DECLARATION ≠ OBSERVATION EVIDENCE
```

Negative Evidenceはscope、期間、method、attempt count、completion、blind spotを持たなければならない。

# 6. Fail-Closed Mapping

| Observed condition | Closure result |
|---|---|
| Target satisfied and all gates pass | `SATISFIED` candidate |
| Targetを観測したが満たさない | `NOT_SATISFIED` |
| Targetは満たすがEvidenceが欠落または要求level未満 | `NOT_SATISFIED` |
| Policy `required_invariants`がfail | `NOT_SATISFIED` |
| Kernel Mandatory InvariantがPASS以外 | `BLOCKED` |
| required claimが`NOT_SATISFIED` | `NOT_SATISFIED` |
| `proposed_terminal_status`がallowed terminal statesに含まれない | `NOT_SATISFIED` |
| 評価がまだ実行されていない | `NOT_EVALUATED` |
| 必要Evidenceを評価中 | `EVALUATING` |
| Truthを決定するInputまたはObservationが不足 | `BLOCKED` |
| required invariantまたはclaimが未評価／評価中 | `BLOCKED`または`EVALUATING` |
| Observation or Authority path blocked | `BLOCKED` |
| State、Change、Approval、Evidence binding is stale | `STALE` |
| Policy、required claim evaluation、invariant evaluationのhead不一致 | `STALE` |
| Positive／NegativeまたはMaterial Evidence conflict | `CONTRADICTED` |
| 以前受理した評価またはClosureの前提が無効化 | `REVOKED` |
| 初回評価時にschema、identity、boundary、lineageがinvalid | `NOT_SATISFIED` |

`EMPTY`は対象collectionのcomplete enumerationが証明された場合だけTarget Satisfactionへ使用できる。`NO_RESULT`、`FAILED`、`INCOMPLETE`をabsenceまたはmatchへ昇格させない。

# 7. Atomic Closure

Closure Evaluationの`SATISFIED`だけではDifferenceはまだ`CLOSED`ではない。

```text
CLOSURE EVALUATION SATISFIED
+ CURRENT REVISION = EXPECTED REVISION
+ ATOMIC STATE TRANSITION
+ LINEAGE APPEND
+ MATERIALIZED STATE UPDATE
→ DIFFERENCE CLOSED
```

Compare-And-Swap失敗、partial write、lineage append失敗、current state不整合の場合、ClosureをCanonicalとして受理しない。

# 8. Staleness

Closure Evaluationは`evaluated_at`をtimezone-aware UTC timestampとして保存し、`maximum_evidence_age`を評価時点とAtomic Reflow commit直前の双方で強制する。

```text
maximum_evidence_age = null
→ Policyによる追加のage上限なし
→ evaluation_expires_at = null

maximum_evidence_age ≠ null
→ 0 <= evaluated_at - evidence_observed_at <= maximum_evidence_age
→ timezone-aware timestamp必須
→ evaluation_expires_at = oldest_required_evidence_observed_at + maximum_evidence_age
→ age不明、future-dated Evidence、timestamp不正、上限超過はG18=false
```

複数Evidenceを使う場合は、Closure Claimに必要な全Evidenceがage predicateを満たさなければならない。古いEvidenceを新しいEvidenceの件数で補ってはならない。上限超過は`STALE`とし、`SATISFIED`を返さない。

Atomic Reflowはcommit clockをtimezone-aware UTCとして取得し、`evaluation_expires_at`がnon-nullなら次を再検証する。

```text
commit_at <= evaluation_expires_at
```

commit前にexpiryへ到達したEvaluationは、他のbindingが変化していなくても`STALE`である。再観測・再評価なしにcommitしてはならない。

次のいずれかがEvaluation後に変わった場合、未commitのClosure Evaluationは`STALE`である。

```text
Objective revision
Target Predicate
Difference lifecycle head
before State revision or after-state candidate
State fingerprint
Change identity or result
Authority or Approval binding
Evidence set
Closure Policy semantic fingerprint（version-only変更かつsemantic fingerprint同一の場合を除く）
```

Stale Evaluationを再利用せず、最新Stateから再観測・再評価する。

# 9. Reopen Policy

同じsemantic identity boundary内で、`CLOSED`後のObservationがTarget不一致を示した場合、またはClosureに使用したEvidenceの失効・provenance不正・material contradictionがObservationの有無にかかわらず判明した場合、Differenceを`REOPENED`へ遷移させる。

加えて、Closure Policyの`reopen_conditions`が参照するTarget Predicate集合を評価する。いずれかがexact current State／Evidence上で`SATISFIED`になった場合は同じ`CLOSED → REOPENED`経路を使用し、`POLICY_REOPEN_CONDITION_SATISFIED`、triggered Target Predicate ref、Completion Evaluation refおよび評価EvidenceをReopen Eventへ保存する。未知condition、評価不能、stale inputをtrueまたはfalseへ推測せず、fail closedで再観測へ送る。

Reopenは旧Closureを削除しない。すべてのtriggerで次をappendする。

```text
reopen event
affected closure evaluation ref
new State revision and fingerprint
next required observation
```

Observation refs、contradiction／invalidated／revoked Evidence refs、reopen condition refsとそのEvaluation refsは、`DIFFERENCE_LIFECYCLE.md`第8節のtrigger-specific表に従って必須または禁止を決定する。全triggerへ同じref集合を無条件要求してはならない。

Objective、Target、effective boundaryまたはnormalized mismatch semanticsがmaterialに変更された場合は、旧Differenceを`SUPERSEDED`とし、新しいDifference identityとappend-only Supersession Relationを導出する。Boundary変更を旧Differenceの`REOPENED`として扱わない。

# 10. Non-Authorities

次はClosure authorityではない。

```text
Agent report
Issue close
PR merge
commit exists
CI success
test pass
artifact exists
deployment succeeded
Change status EXECUTED
human informal statement
```

HumanはObjectiveとconstitutional authorityを持つが、Evidenceなしの手動flagでKernel invariantを迂回しない。Risk acceptanceはTarget Satisfactionの代替ではない。

# 11. Acceptance

```text
CLOSURE_GATES_CLOSED=true
REOBSERVATION_REQUIRED=true
CHANGE_BOUND_RESULT_EVIDENCE_REQUIRED=true
CHANGE_FREE_VERIFICATION_EVIDENCE_REQUIRED=true
RESOLUTION_MODE_EVIDENCE_EXCLUSIVE=true
EVIDENCE_SUFFICIENCY_REQUIRED=true
MAXIMUM_EVIDENCE_AGE_ENFORCED=true
EVALUATION_TIMESTAMP_RECORDED=true
EVIDENCE_AGE_RECHECKED_AT_REFLOW=true
FUTURE_DATED_EVIDENCE_REJECTED=true
REQUIRED_INVARIANTS_BOUND=true
ALLOWED_TERMINAL_STATES_ENFORCED=true
POLICY_VERSION_EXACT=true
REQUIRED_CLAIM_EVALUATIONS_BOUND=true
POLICY_SEMANTIC_FINGERPRINT_DETERMINISTIC=true
VERSION_ONLY_POLICY_UPDATE_CLOSABLE=true
INDEPENDENT_VERIFICATION_SETTING_ENFORCED=true
REOPEN_CONDITIONS_ENFORCED=true
UNKNOWN_IS_PASS=false
NO_RESULT_NE_PROVEN_ABSENCE=true
CHANGE_CANNOT_SELF_CLOSE=true
PR_MERGE_IS_COMPLETION=false
STALE_CLOSURE_BLOCKED=true
ATOMIC_REFLOW_REQUIRED=true
REOPEN_POLICY_DEFINED=true
```

```text
DIFFERENCE_CLOSURE_POLICY_DEFINED=true
CLOSURE_EVALUATOR_IMPLEMENTED=false
ATOMIC_DIFFERENCE_CLOSURE_PROVEN=false
```
