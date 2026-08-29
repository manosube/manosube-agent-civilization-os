# MANOSUBE Agent Civilization OS

## Canonical Serialization Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=STATE
DOCUMENT_ID=CANONICAL-SERIALIZATION-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
SERIALIZATION_PROFILE=MANOSUBE-CANONICAL-JSON-0.1
```

---

# 0. Purpose

Canonical Serializationは、同一Semantic Stateを実行環境、Agent、model、session、入力順序に依存せず同一bytesへ変換する規約である。

```text
SAME_SEMANTIC_STATE
+ SAME_SERIALIZATION_PROFILE
→ SAME_CANONICAL_BYTES
```

# 1. Processing Pipeline

```text
SCHEMA VALIDATION
→ SEMANTIC / METADATA SEPARATION
→ VALUE NORMALIZATION
→ SET-LIKE COLLECTION ORDERING
→ OBJECT KEY ORDERING
→ UTF-8 ENCODING
→ CANONICAL BYTES
```

順序を飛ばしてfingerprintを生成してはならない。

# 2. Encoding Profile

v0.1はUTF-8 JSONを使用する。Canonical bytesは次を満たす。

```text
encoding=UTF-8
BOM=false
object_keys=lexicographic_by_unicode_code_point
insignificant_whitespace=none
line_ending=none
trailing_newline=false
duplicate_keys=reject
```

Human-readableなpretty JSONはprojectionであり、canonical bytesではない。

# 3. String Normalization

すべての文字列はUnicode NFCへ正規化する。無効なUnicode、unpaired surrogate、制御文字の不正表現を拒否する。

識別子のcase、全角半角、path separatorを暗黙変換して別identityを同一視してはならない。identityごとの正規化は対応ContractまたはSchemaが明示した場合だけ行う。

# 4. Scalar Values

```text
boolean = true | false
null    = null
string  = normalized JSON string
integer = base-10, no leading plus, no leading zero except 0
```

v0.1 Semantic Stateではbinary floating point値、NaN、Infinity、negative zeroを禁止する。小数が必要なdomainは、scaleを明示したdecimal stringまたはinteger minor unitとして別Contractで定義する。

# 5. Object and Collection Ordering

Object keyは常に昇順とする。

Sequenceは意味上の順序を持つ場合だけ入力順序を保持する。Set-like collectionは安定identity key、次にelement canonical bytesで昇順sortする。

```text
ORDERED_SEQUENCE → declared order is semantic
SET_LIKE_COLLECTION → input order is non-semantic
```

collection種別が未定義ならFail Closedする。

# 6. Paths, References and Timestamps

Semantic pathはProject boundaryからのrelative POSIX formを使用する。`..`、absolute path、drive letter、NUL、boundary escapeを拒否する。

Referenceは型付きidentityとして表現し、display URLだけに依存しない。

Semantic timestampが必要な場合はUTCへ正規化したRFC 3339形式を使用し、同一瞬間の異なるoffset表現を一意化する。処理時刻はMetadataへ置く。

# 7. Versioning

Serialization profileを必ず識別する。

```text
profile_id=MANOSUBE-CANONICAL-JSON-0.1
```

profile変更はcanonical bytesとfingerprintを変え得るため、silent upgradeを禁止する。Migrationは旧profile、旧fingerprint、新profile、新fingerprint、変換Evidenceを保存する。

# 8. Rejection Rules

次はCanonical化せず拒否またはquarantineする。

```text
schema-invalid value
unknown field or version
duplicate object key
ambiguous collection semantics
unsupported numeric value
invalid Unicode
boundary-escaping path
secret-bearing value
non-deterministic custom object
```

不正値をnull、空文字、0、空集合へcoerceしてはならない。

# 9. Conformance Vectors

後続実装は最低限、次をtest vectorとして証明する。

```text
different_object_key_order → same bytes
different_set_input_order  → same bytes
different_unicode_form     → same NFC bytes
metadata_only_change       → same semantic bytes
semantic_value_change      → different bytes
duplicate_key              → rejected
unsupported_float          → rejected
```

# 10. Acceptance

```text
CANONICAL_ENCODING_DEFINED=true
OBJECT_KEY_ORDER_DEFINED=true
COLLECTION_ORDER_DEFINED=true
UNICODE_NORMALIZATION_DEFINED=true
NUMBER_POLICY_DEFINED=true
INVALID_INPUT_FAILS_CLOSED=true
SERIALIZATION_VERSIONED=true
```

```text
CANONICAL_SERIALIZATION_CONTRACT_DEFINED=true
STATE_SERIALIZABLE=false
STATE_DETERMINISM_RUNTIME_PROVEN=false
```
