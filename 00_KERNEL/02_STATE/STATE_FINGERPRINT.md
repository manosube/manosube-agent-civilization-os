# MANOSUBE Agent Civilization OS

## State Fingerprint Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=STATE
DOCUMENT_ID=STATE-FINGERPRINT-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
FINGERPRINT_PROFILE=MANOSUBE-STATE-SHA256-0.1
```

---

# 0. Definition

Semantic Fingerprintは、正規化されたSemantic Stateをcontent-addressed identityへ写像する決定論的digestである。

```text
SEMANTIC FINGERPRINT
= SHA-256(
    DOMAIN_SEPARATOR
    || PROFILE_IDENTIFIER
    || CANONICAL_SEMANTIC_STATE_BYTES
  )
```

Fingerprintは真実性、Evidence sufficiency、Authority、Completionを証明しない。同一内容の検出とState transition結合に使用する。

# 1. Input Boundary

入力は`CANONICAL_SERIALIZATION.md`に従って生成したSemantic State bytesだけである。State Metadata、wrapper、保存path、圧縮形式を入力へ含めない。

```text
INCLUDED   = canonical semantic state bytes
EXCLUDED   = metadata + transport + storage context
```

# 2. Profile

v0.1 profileを次で固定する。

```text
profile_id=MANOSUBE-STATE-SHA256-0.1
algorithm=SHA-256
domain_separator=MANOSUBE_AGENT_CIVILIZATION_OS\u0000STATE\u00000.1\u0000
output_encoding=lowercase_hex
output_length=64
```

Domain separatorはUTF-8 bytesとしてcanonical semantic bytesの直前へ連結する。

# 3. Mandatory Exclusions

次はfingerprint入力に含めない。

```text
observed_at
created_at
recorded_at
observer
producer
agent_name
model_name
session_id
run_id
process_id
hostname
temporary_path
serialization_order
volatile_log
credential
secret
```

除外とは、値を空文字へ置換して含めることではない。Semantic State projectionの入力対象外にすることである。

# 4. Comparison

Fingerprint比較はprofile identityとdigestの組として行う。

```text
(profile_id, digest) = (profile_id, digest)
→ SAME_SEMANTIC_CONTENT

profile_id mismatch
→ NOT_DIRECTLY_COMPARABLE
```

異なるprofileのdigestだけを直接比較してはならない。

# 5. Transition Binding

Change、Approval、State Transitionはexact before-state fingerprintへ結合する。

```text
CURRENT_FINGERPRINT = EXPECTED_FINGERPRINT
→ evaluation may continue

CURRENT_FINGERPRINT ≠ EXPECTED_FINGERPRINT
→ STALE
```

After-state fingerprintはatomic ReflowでState recordとlineage eventへ同時に確定する。

# 6. Verification and Failure

State reload時はcanonical semantic bytesからfingerprintを再計算する。

```text
RECOMPUTED = RECORDED → integrity check passes
RECOMPUTED ≠ RECORDED → QUARANTINE
MISSING PROFILE       → REJECT
UNSUPPORTED PROFILE   → MIGRATION REQUIRED
```

Mismatch時にrecorded fingerprintを黙って再生成・上書きしてはならない。

# 7. Collision Handling

SHA-256 collisionが疑われる場合、両方のcanonical bytesとEvidenceを隔離し、State transitionを停止する。

```text
SAME_DIGEST + DIFFERENT_CANONICAL_BYTES
→ SECURITY_INCIDENT
→ QUARANTINE
→ NO_CANONICAL_TRANSITION
```

片方を自動選択してはならない。

# 8. Algorithm Migration

Algorithmまたはprofileの変更はHuman Constitutional Authorityを要する。Migration recordは次を保持する。

```text
old_profile_id
old_digest
new_profile_id
new_digest
canonical_bytes_reference
migration_reason
authority_ref
evidence_ref
```

旧fingerprintを消去せず、lineageの参照可能性を維持する。

# 9. Conformance Vectors

後続実装は最低限、次を証明する。

```text
same_semantics_different_key_order → same fingerprint
same_semantics_different_set_order → same fingerprint
same_semantics_different_metadata  → same fingerprint
same_semantics_different_agent     → same fingerprint
same_semantics_different_session   → same fingerprint
semantic_value_change              → different fingerprint
profile_change                     → not directly comparable
recorded_digest_tamper              → quarantine
```

# 10. Acceptance

```text
FINGERPRINT_INPUT_BOUNDARY_DEFINED=true
FINGERPRINT_PROFILE_DEFINED=true
VOLATILE_METADATA_EXCLUDED=true
PROFILE_AWARE_COMPARISON_DEFINED=true
STALE_STATE_BINDING_DEFINED=true
MISMATCH_FAILS_CLOSED=true
COLLISION_POLICY_DEFINED=true
MIGRATION_LINEAGE_PRESERVED=true
```

```text
STATE_FINGERPRINT_CONTRACT_DEFINED=true
SEMANTIC_FINGERPRINT_STABLE=false
STATE_FINGERPRINT_RUNTIME_PROVEN=false
```
