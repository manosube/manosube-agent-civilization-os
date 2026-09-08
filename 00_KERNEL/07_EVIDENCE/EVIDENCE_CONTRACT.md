# EVIDENCE CONTRACT — v0.1

```text
EVIDENCE RECORDS WHAT WAS OBSERVED
EVIDENCE DOES NOT OBSERVE
EVIDENCE DOES NOT CLOSE A DIFFERENCE
```

Evidenceは、観測されたものの不変記録である。観測そのものは`03_OBSERVATION/`が、Closureは
`04_DIFFERENCE/`が所有する。本Contractはその二つのどちらにも立ち入らない。

---

# 1. 二位置

第27条はEvidenceを二種類に分離する。v0.1はこの分離を**record field**として保持する。

```text
OBSERVATION EVIDENCE
= before stateとDifferenceを裏付ける証拠

CHANGE RESULT EVIDENCE
= Change後の再観測結果を裏付ける証拠
```

`evidence_position`はcallerが宣言するのではなく、**入力から導出**する。Change requestを
伴う要求はChange Result Evidenceであり、伴わない要求はObservation Evidenceである。片方を
名乗って他方として埋めることは、拒否される以前に**表現できない**。

Changeを行わないObservation Cycleでも、Observation Evidenceを正式に保存できなければ
ならない。これは第27条の明示要件であり、Change不在を理由にEvidenceを省略してはならない。

`evidence_position`のほかに、`difference_ref`を第28条の最低fieldへ追加する。第27条の
Observation Evidenceは「before stateと**Difference**を裏付ける証拠」であり、Differenceを
名指さないrecordは弱い束縛ではなく**束縛の不在**である。

---

# 1A. Exact Difference Binding

Evidenceが束縛するDifferenceは、callerが書くのではなく**導出する**。

```text
observation_request              → observe()            → Observation bundle
difference_request + bundle      → derive_differences() → Difference
                                                        → difference_ref
```

再生成したbundleを derivation request へ**代入**してから producer を走らせる。「callerの
bundleがobserve()の結果と一致すること」を検査する形は弱い。両者が食い違いうるrequest
shapeが残り、そのようなshapeにはいずれ食い違わせるcallerが現れる。

bindingは一つ、Differenceは一つに限る。Evidence recordは一つのDifferenceを束縛するため、
二つ導出された場合に「どちらについてのrecordか」を選ぶ所有者が存在しない。

Change Result Evidenceでは、Changeが内包する`difference_ref`が導出Differenceと一致しな
ければならない。二つの独立した導出（Observationから来るDifference、Authority決定から来る
Change）に一致を要求するのであって、callerの二つのlabelを比較するのではない。

Sufficiencyは、投入された全Evidence recordの`difference_ref`が評価対象Differenceと一致
することを要求する。これがなければ次が成立していた。

```text
Difference A の Evidence
+ Difference B の Closure Policy
→ Difference B が SUFFICIENT
```

Policyの`subject_difference_ref`も同一Differenceを要求するため、request・Policy・全Evidence
の三者が一つのidentityへ固定され、三者とも導出により到達する。

---

# 1B. Evidence参照の唯一のvocabulary

```text
EVIDENCE_REFERENCE_KIND = observation_evidence
```

Evidence recordをこのKernelのどこかから参照するとき、kindは常に`observation_evidence`で
ある。これは新しい語彙ではなく、**consumerが既に宣言している語彙**である。

```text
graph.REFERENCE_EDGES
  evidence_sufficiency_result.evidence_refs.members[]   observation_evidence | negative_evidence
  difference.observation_evidence_refs[]                observation_evidence | negative_evidence
  closure_evaluation.change_result_evidence_refs[]      observation_evidence
  closure_evaluation.terminal_reason_evidence_refs[]    observation_evidence
  invariant_evaluation.evidence_refs.members[]          observation_evidence | negative_evidence

observation/engine.py
  observation_evidence_refs                             observation_evidence
```

`closure_evaluation.change_result_evidence_refs`が`observation_evidence`しか受理しない点が
決定的である。Difference層は第27条の**両位置**をこの一つのkindで参照している。

`observation_evidence`は`graph.EXTERNAL_KINDS`に属する。これにより、Evidence recordが
`01_SCHEMA/evidence/`に住んだまま——Difference bundleの外で——参照が閉じる。これが無ければ、
DifferenceのbundleにEvidence recordを同梱する必要が生じ、同じrecordに第二のownerが生まれる。

## 1B.1 tagであってpositionではない

第27条の二位置は`evidence_position`としてrecord上に残る。参照tagの統一は位置を統合しない。
identity空間も`EVIDENCE-<digest>`のまま変わらないため、全参照は依然として名指したrecordへ
解決する。

```text
REFERENCE TAG   observation_evidence     consumer の語彙
POSITION        OBSERVATION_EVIDENCE | CHANGE_RESULT_EVIDENCE   第27条
IDENTITY        EVIDENCE-<sha256>       解決先
```

`negative_evidence`はObservation層のNegative Observationを裏付けるkindであり、Phase 6は
生成しない。生成すれば、観測していない有界不在をEvidenceが主張することになる。

## 1B.2 往復が成立していること

producerとしての妥当性は、consumerが受理することを意味しない。

```text
Evidence
→ Sufficiency Result
→ evidence_sufficiency_results
→ derive_differences()
→ schema / identity / reference closure / relational gate
```

この往復を`tests/integration/evidence/test_difference_round_trip.py`が実行し、誤ったkindが
必ずclosure gateで落ちることをnegative controlで示す。往復できないproducerは、単体でどれ
ほど検証されていても未完成である。

---

# 2. 最低field（第28条）と欠落の禁止

第28条の14 fieldは、位置にかかわらず**一つのEvidence recordへ常設**する。適用されない
fieldは`null`とし、**省略しない**。

```text
ALL_MINIMUM_FIELDS_PRESENT=true
NOT_APPLICABLE=null
```

省略を許すと、「このEvidenceはChangeを持たない」と「このEvidenceは言い忘れた」が同一の
recordになる。前者は事実であり、後者は欠陥である。両者を区別できないrecordは、Evidenceの
用をなさない。

Observation Evidenceでは次を`null`とする。

```text
change_identity   = null
authority_used    = null
after_state       = null
expected_result   = null
```

Change Result Evidenceでは上記すべてを非nullとする。schemaがこれを位置ごとに強制する。

## 2.1 `after_state = before_state`を採らない

Observation Evidenceで「変化がなかったのだから after_state は before_state に等しい」と
書いてはならない。

```text
"NOTHING CHANGED"
= A CLAIM ABOUT A SECOND POINT IN TIME
= REQUIRES A SECOND OBSERVATION
```

Observation Evidenceは一回の観測しか持たない。`before_state`をコピーすることは、観測して
いない不変性を主張することであり、`NO_RESULT != PROVEN_ABSENCE`が禁じる代入である。

---

# 3. State binding（埋め込まない）

`before_state`と`after_state`は次の形で束縛する。

```text
STATE_BINDING = state_revision + semantic_fingerprint
STATE_BODY_EMBEDDED = false
```

Canonical State本体をEvidenceへ複製してはならない。複製されたStateは、Canonical Stateと
食い違いうる第二のStateである。第28条末尾の「StateはEvidence本文を無制限に埋め込まず、
不変Evidenceへの参照を保持する」は、逆向きにも成立する。

`semantic_fingerprint`は`01_SCHEMA/common/fingerprint.schema.json`の
`{profile, digest}`をそのまま用いる。Fingerprint profileを再定義しない。

---

# 4. Provenance by reproduction

Evidenceは他のrecordについてのrecordである。したがって偽造されたpredecessorの上に
立つEvidenceは、正しいfingerprintを身にまとった虚偽の主張である。

```text
INTERNAL HASH CONSISTENCY
!= PROVENANCE
```

`observation_identity`、`change_id`、`decision_id`はいずれも**公開された純関数**であり、
canonical ownerを一度も呼ばないcallerが、record を合成して内部整合させることができる。
これはPhase 5がP1として修復した欠陥そのものである。

v0.1のEvidence engineは、predecessorの**record**を受け取らない。predecessorの
**request**を受け取り、canonical ownerを実行して record を得る。

```text
observation_request              → observe()        → Observation
post_change_observation_request  → observe()        → Observation
change_request                   → derive_change()  → Change (+ 証明済みAuthority決定)
```

`derive_change`は自ら`evaluate_authority`で決定を再現するため、Evidenceは Phase 5 の
provenance をそのまま継承し、再実装しない。偽造されたpredecessorは拒否されるのではなく、
**表現できない**。

---

# 5. Change Result Evidenceの接地要件

```text
UNGROUNDED_CHANGE_RESULT_EVIDENCE=REFUSED
AUTHORIZED != EXECUTED
```

第27条のChange Result Evidenceは「Change後の**再観測**結果」である。`E-002`は、execution
return code、Agent success report、file existenceのいずれもAfter Stateの根拠にならないと
明示する。

v0.1にExecutorは存在せず、`change.schema.json`は`execution_result`を`null`に固定し、
`AUTHORIZED`は`EXECUTED`ではない。したがって**変換すべき結果が存在しない**。

post-change Observationを伴わないChange Result Evidenceは生成しない。UNKNOWN、BLOCKED、
INCOMPLETEは**Observation Evidence**として正式に保存でき、それは虚偽のrecordより弱い
recordではない。ungrounded recordをChange Result Evidenceと呼び替えて
`change_result_evidence_refs`を満たすことは、`E-002`が禁じる代入である。

post-change Observationが存在する場合でも、証明されるのは「after-stateが観測された」
ことだけである。

```text
POST_CHANGE_OBSERVATION
!= EXECUTION_RECEIPT
!= CAUSALITY_PROOF
!= E4_PROOF
```

`causality_claimed`と`execution_receipt_present`はschemaで`false`に固定する。反対を述べる
recordは存在できない。

## 5.1 独立性の構造的最小要件

`CLOSURE_POLICY.md` §4の独立性は、「Change自身が自身の成功flagをClosure Predicateとして
供給しない」ことを意味する。v0.1では次を構造的に強制する。

```text
post-change Observation identity != before-state Observation identity
post-change observed revision    >= change expected_state_revision
before-state Observation binding == change before_state_fingerprint / expected_state_revision
```

before-pictureが自らの再観測を兼ねることは、Changeが自らを証明することである。

なお、after-stateがbefore-stateと同一であること自体は拒否しない。それを拒否することは、
Changeが状態を変えたはずだという因果の主張になる。

---

# 6. Status（縮約の禁止）

Evidenceの`status`はObservation ownerのstatusをそのまま搬送する。Evidenceは第二の
status deriverを持たない。

```text
COMPLETE INCOMPLETE EMPTY UNKNOWN UNOBSERVED BLOCKED FAILED INVALID CONFLICTED
```

九つの値は互いに縮約してはならない。EMPTY、negative、missing、blocked、failed、unknown、
unobserved、incomplete、contradictionを一語へ潰した時点で、`NO_RESULT != PROVEN_ABSENCE`
は成立しなくなる。

---

# 7. Artifact References（秘密を含めず、可変物を権威にしない）

```text
artifact_reference = kind + id + content_sha256 + byte_length + media_type
                     [+ source_snapshot_ref]
```

URL、credential、host、tokenを含めない。可変外部locatorで解決するreferenceは、「今そこに
あるもの」をEvidenceの権威にする。それは不変record（`E-003`）の反対である。位置が必要な
場合は、Observation層が所有する不変の`source_snapshot`参照だけを添付できる。

`additionalProperties: false`により、他のkeyは表現できない。

---

# 8. Recording instant（時計を読まない）

`timestamp`は入力として**admit**する。engineは時計を読まない。

```text
CLOCK_READ_IN_ENGINE=false
RECORDING_INSTANT=ADMITTED_INPUT
```

書いた機械の時計から取った時刻は、reviewerが再現できない時刻である。決定的engineが
再現不能な値を含めば、record全体が再現不能になる。

時計なしで検査できる性質は一つあり、それを強制する。

```text
recorded_at >= observation_ended_at
```

Sufficiencyの`evaluation_instant`も同じくadmitted inputであり、age判定は**正確な
interval**で行う。整数への切り捨ては表示用の値にのみ使う。

観測が終わる前に、その観測についてのEvidenceを書くことはできない。

比較は`03_OBSERVATION/`所有のcanonical parserを通す。文字列比較にしてはならない。
`common/timestamp.schema.json`は小数秒を許すため、`...00.5Z`は`'.' < 'Z'`により`...00Z`
より**前**に並ぶが、実際には0.5秒**後**である。順序を主張しながらbyteを並べる比較は、
検査がないより悪い。

---

# 9. Identity と不変性

```text
evidence_id = EVIDENCE-<sha256 over the whole meaning>
```

意味projectionは第28条の14 fieldに`evidence_position`と`evidence_level`を加えた全体で
あり、`schema_version`・`evidence_id`・`evidence_semantic_fingerprint`だけを除く。

`CHANGE_SEMANTIC_FIELDS`が`status`を意図的に除外するのと対照的である。理由は非対称で
ある。

```text
A CHANGE LATER EXECUTED   = THE SAME CHANGE
AN EVIDENCE LATER SAYING SOMETHING ELSE = A DIFFERENT EVIDENCE
```

`E-003 EVIDENCE_IMMUTABLE`は、addressが意味全体を覆う場合にのみ強制可能である。
projectionから漏れたfieldは、addressを保ったまま書き換えられるfieldであり、それは
手順を増やしたEvidence上書きにほかならない。

---

# 10. 本Work Unitが主張しないもの

`KERNEL_INDEX.md` §4.7は`07_EVIDENCE/`に六文書を挙げる。本Work Unitは三文書を提出する。

```text
EVIDENCE_CONTRACT.md      CLAIMED
EVIDENCE_LEVELS.md        CLAIMED
EVIDENCE_SUFFICIENCY.md   CLAIMED

OBSERVATION_EVIDENCE.md      NOT CLAIMED  — §1,§2,§3が両位置を規定する
CHANGE_RESULT_EVIDENCE.md    NOT CLAIMED  — §5が規定する
NEGATIVE_EVIDENCE.md         NOT CLAIMED  — Negative Observationは
                                             03_OBSERVATION/が所有し、
                                             negative_observation.schema.json と
                                             negative_evidence_refs が既に存在する。
                                             第二のowner を作らない。
```

`NOT CLAIMED`は不足であり、達成ではない。ここに書かれていないことを、書かれたことの
代用にしてはならない。

---

# 11. 報告するが取らない決定（predecessor surface）

`03_OBSERVATION/`のEngineは、Observationの`observation_evidence_refs`に
`kind == "observation_evidence"`を要求する。Phase 6のrecordは`EVIDENCE-`空間に住み、
`kind == "evidence"`として参照される。したがって現時点では、ObservationがPhase 6の
Evidence recordを引用できない。

```text
observation/engine.py    kind == "observation_evidence"   を要求する
difference.schema.json   kind を制約しない                  → Difference は引用できる
evidence engine          kind == "evidence"                を発行する
```

これはPhase 6が解決しない。predecessorのreference vocabularyを広げることは、その
predecessorを所有するphaseの決定である。ここで変更することは、自らの出力に合わせて
Observationのcontractを書き換えることになる。

これはPhase 6で**解消済み**である（§1B）。Evidenceが`observation_evidence`を発行するように
なったため、ObservationはPhase 6のEvidence recordを引用できる。Observation Engineは変更して
いない。Evidenceが、そのEngineが既に要求していた語彙を話すようになっただけである。

`tests/contract/evidence/test_evidence_conformance.py`が両方向を固定する。

---

# 11A. 開示済みの欠落 — 第三の位置は本Contractに未記載

R6-F1b（Structural Review Round 6 以前のCompletion Repair）は`evidence_position`へ
`CHANGE_FREE_VERIFICATION_EVIDENCE`（`CLOSURE_POLICY.md` §6の`CHANGE_FREE`行）を追加した。
これは`evidence/engine.py`にも`01_SCHEMA/evidence/evidence.schema.json`にも実装済みであり、
§14が前提とする位置だが、本Contract自身の§1は依然「二位置」としてOBSERVATION_EVIDENCEと
CHANGE_RESULT_EVIDENCEのみを記述している。この節番号（11A）は、その記述漏れをこの
Work Unit（P13-R6）が偶然発見したことを示すためのものであり、§1を書き換えて解消する
ことは今回のadoptionの範囲外である——今回書き換えれば、Round 6自身の変更に紛れて
先行するR6-F1bの記述漏れが静かに埋められたことになり、いつ・どのroundが実際にそれを
直したかが不明瞭になる。したがって解消せず、ここに明示する。

---

# 12. FAILED Observation — 批准済みamendment（ADR-0030）

Evidenceは§1AによりDifference producerの受理性を継承する。`2730fab`時点では、そのproducerが
`FAILED`を拒否していたため、初回観測がFAILEDである場合にEvidenceを生成できなかった。

```text
INITIAL FAILED OBSERVATION
→ Difference producer が拒否
→ Observation Evidence を生成できない
```

第31条は「失敗、EMPTY、BLOCKED、STALE、未到達も正式なEvidenceとして還流する」と要求する。
これは機能不足ではなく憲法矛盾であり、Phase 6は自らの権限で解決せず保持してHuman Authority
へ差し戻した。批准された決定は次である。

```text
ACCEPT_FAILED_OBSERVATION_IN_DIFFERENCE
FAILED_PROJECTION=UNKNOWN
FAILED_ATTEMPT_AND_FAILURE_CLASS_PRESERVED=true
INVALID_OBSERVATION_REMAINS_REFUSED=true
EVIDENCE_MUST_NOT_BYPASS_DIFFERENCE=true
THIRD_EVIDENCE_POSITION_CREATED=false
```

## 12.1 意味論を発明していない

`04_DIFFERENCE/DIFFERENCE_CONTRACT.md` §4 は既に`FAILED`を「proven absenceへ昇格せず
`UNKNOWN` knowledgeのまま保持する」と規定し、`projection._NEGATIVE_STATUS_MAP`は既に
`FAILED → UNKNOWN`を実装していた。status gateがその写像へ到達する前に拒否していただけで
ある。amendmentはengineをContractへ整合させる。

## 12.2 経路

```text
FAILED Observation
→ Difference producer が受理
→ knowledge_status = UNKNOWN
→ Observation Evidence   status=FAILED  level=E0
→ Evidence Sufficiency   INSUFFICIENT（全floorで）
```

`status`は`FAILED`のままである。`UNKNOWN`はDifferenceの**射影**であってEvidenceの`status`
ではない。attempt結果とfailure classも保持する。射影で上書きすれば、
`NO_RESULT ≠ PROVEN_ABSENCE`が逆向きに崩れる。

FAILED Evidenceは`SUFFICIENT`へ到達しない。`_DETERMINATE_INSUFFICIENT_STATUSES`が
`FAILED`を含み、reason code `EVIDENCE_STATUS_FAILED`を伴って`INSUFFICIENT`とする。
第27条の位置は二つのままであり、失敗は第一の位置に記録される。

## 12.3 INVALIDは拒否のまま

```text
gate         _ACCEPTED_OBSERVATION_STATUS が INVALID を除外
projection   _NEGATIVE_STATUS_MAP が REJECT_OR_QUARANTINE へ写像して raise
```

二重であり冗長ではない。gateはObservation自身のstatusを、projectionはNegative Observation
のevaluationを読む。INVALIDなrecordはどちらの位置でも信頼しない。

`tests/integration/evidence/test_failed_observation_route.py`が全項目を実行し、誤kindの
注入で往復gateが実際に落ちることをcontrolで示す。

---

# 13. verification_result_provenance — Structural Review Round 6（P13-R6, Issue #51）

Issue #51 Structural Review Round 2/3/5-R1が開示を繰り越していた「Evidence handoff
provenance completeness」の欠落は、SHUKOU adoption `ADOPT_P13_R6_PROVENANCE_COMPLETE_
EVIDENCE_HANDOFF`によりここで解決する。

```text
以前: independent_verification が本物の VerificationResult を Change-Free Verification
      Evidence へ引き渡すが、その VerificationResult 自身の provenance は Evidence record
      本体のどこにも保持されない。
今回: Evidence record 自身が VerificationResult の完全な provenance projection を保持する。
```

## 13.1 新field — `verification_result_provenance`

第28条の最低fieldに、本Contractが追加する五番目のfieldとして加わる（既存の
`evidence_position`・`difference_ref`・`evidence_level`に続く）。

```text
verification_result_provenance
  = null                                          （OBSERVATION_EVIDENCE / CHANGE_RESULT_EVIDENCE）
  = { status, requirement_id, selection_id, project_id,
      target_refs, verifier_identity, selection_authority_ref,
      verification_boundary, input_refs, observations }
                                                    （CHANGE_FREE_VERIFICATION_EVIDENCE、必須。
                                                      null は許容されない — P13-R6-R1）
```

十fieldは`independent_verification.types.VerificationResult`自身のfield集合と完全に
一致する。これは意図的である——projectionが元recordの部分集合ではなく全体を捉えることを、
field名を並べて確認できるようにするためである。

## 13.2 schemaはpermissive、handoffがmandatory（開示済みの解釈、P13-R6-R1により覆された）

**この節はP13-R6時点の記録であり、SHUKOUが`ADOPT_P13_R6_R1_EVIDENCE_OWNER_GLOBAL_
PROVENANCE_ENFORCEMENT`（Issue #51 comment 5573559225）で明示的に覆した。以下、原文を
保持したまま、覆された事実をこの節自身に記す——沈黙して書き換えることは本protocolが
禁じる。**

（P13-R6時点の原文）

adoptionの文言は字義通りに読めば「Change-Free Verification Evidenceとして引き渡す場合、
provenanceを必須保持する」とも解釈できる。これをschema層で
`CHANGE_FREE_VERIFICATION_EVIDENCE`位置全体の必須非null制約として実装すると、
`tests/evidence_helpers.py::change_free_verification_evidence_request()`という、
Independent Verificationと無関係にR6-F1b以来この位置を使い続けている既存fixtureを破壊する
（Reflow/sufficiency側のテストが広く依拠している）。

そこで本Round は次の層分けを採る。

```text
SCHEMA LAYER    :  null-or-object を許容する（この位置に限り）。既存の非-Independent-
                    Verification callerを破壊しない。
HANDOFF LAYER   :  route_verification_result_to_evidence は常に real VerificationResult
                    から provenance を構築し、caller供給のprovenanceは受理しない。
                    derive_evidence が返した record 自身の provenance が、構築した値と
                    厳密に一致することを再検査し、不一致なら record を返さない。
```

これは字義通りの解釈をschema層でも強制する方向より弱いが、既存の合法的callerを破壊しない
唯一の道である。「重大に曖昧な決定は沈黙して狭めず開示する」という本protocolの標準義務に
従い、ここに明示する。

（P13-R6-R1による訂正）

SHUKOUは上記の層分けを既存fixtureを理由とした縮小として明示的に禁止し、
`derive_evidence`全体——handoffだけではなく——がこの位置の`verification_result_provenance`
を必須・非null・完全十fieldとして拒否・強制することを命じた。

```text
SCHEMA LAYER    :  CHANGE_FREE_VERIFICATION_EVIDENCE位置では type: object のみを許容する
                    （null は許容されない）。
ENGINE LAYER    :  _derive() が、CHANGE_FREE_VERIFICATION_EVIDENCE位置全体に対して、
                    verification_result_provenance が None のとき無条件に EvidenceError を
                    送出する——handoffを経由するcallerに限らない。
HANDOFF LAYER   :  §13.4の記述は変わらず有効（handoffは自ら構築し、caller供給を受理しない）。
                    ただし今やこれはengine自身の要求の上に立つ、追加の防御である。
```

「既存fixtureを破壊する」という上記の懸念は実際に生じた——
`tests/evidence_helpers.py::change_free_verification_evidence_request()`と
`tests/fixtures/vertical_proof.py`・`tests/natural_cycle/proof.py`の関連呼び出しは、
`None`の代わりに実在する十field projectionを既定値として構築するよう書き換えられた
（`tests/evidence_helpers.py::verification_result_provenance()`）。これは既存fixtureの
互換性維持よりSHUKOUの命令を優先した結果であり、本節が「唯一の道」と述べていた選択そのもの
が、非互換な変更を受け入れることで置き換えられたことを意味する。

## 13.3 position誤用の防止

`verification_result_provenance`は、この位置（CHANGE_FREE_VERIFICATION_EVIDENCE）専用
である。engine自身が——schema検証の失敗としてではなく、engineの語彙による明示的な
`EvidenceError`として——OBSERVATION_EVIDENCE・CHANGE_RESULT_EVIDENCEへの非null値を拒否
する。

## 13.4 handoffは常に自ら構築し、caller供給を受理しない

`evidence_handoff.py::route_verification_result_to_evidence`は、*verification_result*
自身の十fieldから決定的にprovenanceを構築する。*evidence_request*が既に非null値を
`verification_result_provenance`へ置いていた場合、その値を上書きするのではなく——
`EvidenceHandoffError`で拒否する。これは、handoffが「どのprovenanceを返すか」を
制御し続けるための決定であり、上書きは沈黙した代入（callerが供給した値がいつの間にか
別の値に変わる）になり、拒否より弱い。

`derive_evidence`が返したrecordの`verification_result_provenance`が、構築した値と
厳密に一致しない場合、handoffはrecordを返さず`EvidenceHandoffError`を送出する。

## 13.5 identityへの参加

`verification_result_provenance`は`evidence/identity.py::EVIDENCE_SEMANTIC_FIELDS`へ
追加され、`evidence_id`/`evidence_semantic_fingerprint`の一部になる。永続化後に
provenanceだけを差し替えることは、addressを保ったままEvidenceを上書きすることになり、
§9が禁じる代入である。

## 13.6 opaque fieldの権威

`verifier_identity`・`selection_authority_ref`・`verification_boundary`・`observations`
はこのschemaが何も制約しない——`authority/verifier_selection_grant.schema.json`の同名
fieldが既に使う不透明契約と同じ理由による。これらが何を意味するかはIndependent
Verification自身の関心であり、このschemaが決めることではない。
`difference/admissibility.py::UNCONSTRAINED_CONTRACT_LOCATIONS`が`VERIFICATION_INPUT`
としてこの四箇所を登録し、`tests/unit/evidence/test_request_totality.py`がその
generated coverageを持つ。
