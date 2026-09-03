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

`tests/contract/evidence/test_evidence_conformance.py`が現状を固定し、どちらかが動いた
場合に検出する。
