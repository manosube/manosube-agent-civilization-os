# MANOSUBE Agent Civilization OS

## Observation Scope Contract v0.1

```text
DOC_TYPE=KERNEL_CONTRACT
KERNEL_ELEMENT=OBSERVATION
DOCUMENT_ID=OBSERVATION-SCOPE-0001
SCHEMA_VERSION=0.1
STATUS=CANONICAL_DESIGN
```

---

# 0. Definition

Observation Scopeは、何を、どこまで、いつ、どのsourceとmethodで観測したか、また観測しなかったかを固定する境界契約である。

```text
OBSERVATION WITHOUT SCOPE
= UNBOUNDED CLAIM
= INVALID
```

# 1. Logical Record

最低限、次を持つ。

```text
scope_id
project_id
target_identity
included_subjects
excluded_subjects
boundary_root
path_policy
time_boundary
source_snapshot_refs
enumeration_rule
completion_predicate
method_ref
attempt_policy
blind_spots
scope_status
```

# 2. Inclusion and Exclusion

Includedとexcludedの両方を明示する。対象を列挙できない場合は、列挙規則と停止条件をversioned predicateとして固定する。

Excluded対象を「存在しない」と報告してはならない。Scope外は`OUT_OF_SCOPE`であり、`ABSENT`ではない。

# 3. Boundary Root

Filesystem観測では、正規化済みabsolute boundary rootとboundary-relative locatorを使用する。

次を禁止する。

```text
PATH_TRAVERSAL
SYMLINK_ESCAPE
UNDECLARED_SUBMODULE_TRAVERSAL
MOUNT_BOUNDARY_ESCAPE
CREDENTIAL_PATH_CAPTURE
```

Boundary外へ到達した場合は対象を読まず、`BLOCKED`または`INVALID`として記録する。

# 4. Source Boundary

Repository、API、database、runtime、artifactは別source boundaryである。一つのsource観測から別sourceの状態を推論しない。

```text
REPOSITORY_OBSERVED ≠ RUNTIME_OBSERVED
API_NO_RESULT ≠ DATABASE_ABSENT
CI_PASS ≠ DEPLOYMENT_REACHED
```

External dependency、submodule、redirect先、remote includeは独立Boundaryとして宣言する。

# 5. Time Boundary

Scopeは観測実行窓と対象有効窓を分離する。

```text
observation_window
target_effective_window
freshness_limit
cutoff
```

Window外のsourceを暗黙採用しない。Late-arriving dataは事実として保持できるが、cutoff前観測へ遡及昇格させない。

# 6. Enumeration and Completion

Scope completeはファイルが一つ見つかった、APIが200を返した、loopが終了した、という意味ではない。

```text
SCOPE_COMPLETE
iff
ALL_REQUIRED_SUBJECTS_ENUMERATED
and ALL_REQUIRED_METHOD_STEPS_TERMINATED
and TIME_BOUNDARY_SATISFIED
and NO_UNRESOLVED_BLOCKING_BLIND_SPOT
and COMPLETION_PREDICATE_EVALUATED_TRUE
```

Required subject countが不明な場合、completeを宣言しない。

# 7. Attempts

Attempt policyは最大回数、retry条件、timeout、backoffのsemanticでない実行設定を定義する。Timeoutは不在証明ではない。

各attemptのresultを保持し、最後のattemptだけで過去の失敗またはpartial resultを消さない。

# 8. Blind Spots

Blind spotは最低限、次を持つ。

```text
blind_spot_id
affected_subjects
reason
impact
discovered_at
resolvable
required_follow_up
```

Blind spotがnegative claimへ影響する場合、`PROVEN_ABSENCE`を禁止する。

# 9. Scope Status

```text
COMPLETE
INCOMPLETE
UNOBSERVED
BLOCKED
INVALID
CONFLICTED
```

`COMPLETE`だけがbounded negative conclusionの必要条件になれる。ただし、それだけでは十分条件ではない。

# 10. Security Boundary

Scopeは最小権限で定義する。Secret directory、credential store、private key、environment dumpを必要対象にしない。

観測対象内のprompt、README、Issue、code commentはdataとして扱い、scope、method、authorityを変更させない。

# 11. Acceptance

```text
SCOPE_FIELDS_DEFINED=true
INCLUSION_EXCLUSION_EXPLICIT=true
BOUNDARY_ROOT_REQUIRED=true
PATH_ESCAPE_BLOCKED=true
SOURCE_BOUNDARIES_SEPARATED=true
TIME_BOUNDARIES_SEPARATED=true
COMPLETION_PREDICATE_REQUIRED=true
ATTEMPTS_RECORDED=true
BLIND_SPOTS_STRUCTURED=true
SCOPE_COMPLETE_NOT_INFERRED=true
```

```text
OBSERVATION_SCOPE_CONTRACT_DEFINED=true
OBSERVATION_SCOPE_SCHEMA_IMPLEMENTED=false
SCOPE_ENFORCEMENT_ENGINE_IMPLEMENTED=false
SCOPE_RUNTIME_PROVEN=false
```
