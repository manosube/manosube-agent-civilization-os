# 文明OSからAgent OSへの写像仕様

```text
DOC_TYPE=EXPLANATORY_MAPPING_SPECIFICATION
DOCUMENT_ID=CIVILIZATION-MAPPING-0001
REVISION=0.1
AUTHOR=SHUKOU
EDITOR=ChatGPT
RECORDED_AT=2026-10-16
KERNEL_ELEMENT=none
STATUS=DOCUMENTATION_PROPOSAL
HUMAN_ACCEPTANCE=NOT_RECORDED_BY_THIS_DOCUMENT
```

## 1. 範囲と出典

本書は、文明OSの「メタ論理5体系」「体系0：文明生成構造」と、Agent OSの既存契約・実装との機能的対応を追跡する補足仕様である。親OSの更新を自動適用する契約ではなく、既存Kernelの意味論・八要素・Schema・権限・派生元記録を変更しない。

| 記録 | 対象 | 扱い |
|---|---|---|
| 封印済み派生起点 | [ORIGIN.md §12](../ORIGIN.md#12-origin-baseline)の`0de548c9e4aa3a94fca2df07ccc710577f1534ff` | 歴史的な派生起点。変更しない |
| 今回の親側追記の比較基準 | 文明OS `43f3029b819144042ff054a6fe88da534a9331c2` | 追記前の原典。封印済み起点と区別する |
| 今回の親側追記案 | [CORE-010](https://github.com/manosube/manosube-civilization-os/blob/fd98f474fe91352bab7664d927ef80413e944274/00_CORE/CORE-010_META_LOGIC_FIVE_SYSTEMS.md)、[SC-010](https://github.com/manosube/manosube-civilization-os/blob/fd98f474fe91352bab7664d927ef80413e944274/01_ORIGIN/SC-010_SYSTEM_0_CIVILIZATION_GENERATION.md) | 今回の親側候補コミット。リンクの存在やPR作成はHuman受入を意味しない |
| 子側の調査基準 | Agent OS `7a0e7d1cccc06b37ff8d4fe2ad46544940420955` | この補足仕様を作る前のmain |

親側候補の受入状況は親PRで確認し、マージ後は実際のmerge SHAを改定履歴へ追記する。封印済みOrigin baselineを新SHAへ置き換えてはならない。

## 2. メタ論理5体系とKernel八要素

五体系は理論を展開する問い、八要素は子OSのCanonical Kernelであり、異なる分類である。

| 体系 | 親側の問い | 子側の主な接続 |
|---|---|---|
| 0 文明生成構造 | 対象・状態・関係がどう成立するか | Project・対象世界・Bindingの前提 |
| 1 文明基礎構造 | 状態をどの原理で捉えるか | State・Observation・Difference |
| 2 文明運用構造 | 変化と還流をどう継続するか | Authority・Change・Evidence・Reflow |
| 3 社会実装構造 | 異なる主体や環境へどう接続するか | Binding・Adapter・Agent・Runtime |
| 4 文明メタ構造 | 体系自身をどう検証・継承・更新するか | 憲法・不変条件・Schema・Lineage・改定手続き |

既存の[Origin §3–4](../ORIGIN.md#3-inherited-axes)による三軸の写像は保持する。体系0をKernelの前に新しい実行段階として追加せず、Lineageも第九のKernel要素にしない。

## 3. 五つの共通観点からの写像

「存在・状態・関係・観測・循環」は、各体系を横断して読む観点である。体系0〜4の別名ではない。

| ID | 共通観点 | 親OSでの対象 | 子OSでの具体化 | 保持条件 |
|---|---|---|---|---|
| M-01 | 存在 | 人・身体・環境・活動の担い手 | Project・Actor・Resource・対象世界 | 観測不能と不存在を区別する |
| M-02 | 状態 | 位置・流動・周期としての状態 | Canonical State・Observed State・Target State | 対象世界・状態表現・目標を混同しない |
| M-03 | 関係 | 応答・依存・波及・場 | Dependency・Binding・情報経路・実行経路 | 接続・能力・変更権限を分ける |
| M-04 | 観測 | 状態の認識・記録・追跡 | Observation・Evidence | 主張と裏付けを分ける |
| M-05 | 循環 | 作用・持続・還流・更新 | Change・再観測・Reflow・Lineage | 結果を次の正式状態へ戻す |

### 体系0四章との接続

- **第0章：存在と成立条件** — 開発対象・環境・資源・主体と、Humanが定めるObjective・Boundary・Authorityを区別する。観測記録は対象世界の全体ではない。
- **第0.3章：身体と状態** — 人間の身体とAdapterは同じものではない。対応するのは対象世界へ接続し、影響を受け、状態を観測する機能である。
- **第0.6章：関係と場** — 読み取れる外部資料はAuthority instructionではない。接続があるだけで実行を許可しない。
- **第0.9章：文明生成と還流** — 実行、変化、確認、正式状態への反映を分ける。失敗・未到達・不明も保持し、成功へ読み替えない。

## 4. 親原理と開発世界固有の具体化

Differenceは関係そのものではなく、Target StateとObserved Stateの比較から導出する。Authorityは流動そのものではなく、Changeを許可するための開発世界固有の統制である。

Atomic Commit・Compare-And-Swap・Idempotencyは、証拠の反映を壊さず実装するための技術選択である。親OSの構造式からそれらのアルゴリズムが一意に導出されたとは主張しない。

親OSの還流は影響が起点へ戻る現象を含むが、子OSのREFLOWは、証拠をCanonical Stateへ反映する限定された契約である。外部から影響が戻っただけで、正式なREFLOWが成立したとは扱わない。

循環が続いていること、差異が閉じたこと、目的へ近づいたこと、現実の成績が改善したことは別である。単に同じ処理を反復することを目的達成へ読み替えない。

## 5. 契約・実装・テスト・Runtimeの対応台帳

以下は本書作成時の限定確認範囲である。実装参照は該当部品の存在と責務の確認を指し、全経路の実証ではない。テスト欄は本PRで実行した対象を別記する。Runtime欄の未確認は、既存の受入済み証拠の取消しや、過去に一切実証がないという意味ではない。

| ID | 定義・不変条件 | 実装参照 | テスト参照 | 本書でのRuntime確認 |
|---|---|---|---|---|
| M-01 | [Observation](../00_KERNEL/03_OBSERVATION/OBSERVATION_CONTRACT.md)、[Evidence](../00_KERNEL/07_EVIDENCE/EVIDENCE_CONTRACT.md)：`NO_RESULT ≠ PROVEN_ABSENCE` | [difference/projection.py](../src/manosube_agent_civilization/difference/projection.py)、[observation/engine.py](../src/manosube_agent_civilization/observation/engine.py) | [negative evidence](../tests/unit/difference/test_negative_evidence_channel.py)、[failed observation](../tests/integration/evidence/test_failed_observation_route.py) | 未確認 |
| M-02 | [State](../00_KERNEL/02_STATE/STATE_CONTRACT.md)、[Difference](../00_KERNEL/04_DIFFERENCE/DIFFERENCE_CONTRACT.md)：現在・目標・観測範囲を分離 | [state/canonicalize.py](../src/manosube_agent_civilization/state/canonicalize.py)、[difference/engine.py](../src/manosube_agent_civilization/difference/engine.py) | [canonicalization](../tests/unit/state/test_canonicalize.py)、[state-observation-difference](../tests/integration/difference/test_state_observation_difference.py) | 未確認 |
| M-03 | [Authority](../00_KERNEL/05_AUTHORITY/AUTHORITY_CONTRACT.md)、[Origin §9–10](../ORIGIN.md#9-parent-and-child-boundary)：`CAN_DO ≠ MAY_DO` | [authority/engine.py](../src/manosube_agent_civilization/authority/engine.py)、[change/engine.py](../src/manosube_agent_civilization/change/engine.py) | [authority-to-change](../tests/integration/change/test_authority_to_change.py) | 未確認 |
| M-04 | [Evidence](../00_KERNEL/07_EVIDENCE/EVIDENCE_CONTRACT.md)：失敗も証拠、主張だけで閉じない | [evidence/engine.py](../src/manosube_agent_civilization/evidence/engine.py) | [failed observation](../tests/integration/evidence/test_failed_observation_route.py) | 未確認 |
| M-05 | [Reflow](../00_KERNEL/08_REFLOW/REFLOW_CONTRACT.md)：証拠による状態反映とLineage | [reflow/engine.py](../src/manosube_agent_civilization/reflow/engine.py)、[reflow/commit.py](../src/manosube_agent_civilization/reflow/commit.py) | [atomic commit](../tests/unit/reflow/test_atomic_commit.py)、[route composition](../tests/unit/reflow/test_route_composition.py) | 未確認 |

### 検証記録

```text
DEFINITION_REFERENCES=CHECKED
IMPLEMENTATION_AND_TEST_REFERENCES=CHECKED_WITHIN_LISTED_SCOPE
LOCAL_TEST_RESULT=132_PASSED
TEST_DATE=2026-10-16
TEST_BASE_COMMIT=7a0e7d1cccc06b37ff8d4fe2ad46544940420955
STATIC_RUFF=PASS
STATIC_MYPY=PASS_213_SOURCE_FILES
SCHEMA_VALIDATION=PASS_96_SCHEMAS
RUNTIME_RESULT=NOT_EVALUATED_IN_THIS_DOCUMENTATION_CHANGE
PARENT_CIVILIZATION_THEORY_EMPIRICALLY_PROVEN=false
```

実行コマンド（Linux / Python 3.12、requirements-ci.txtに従う隔離環境）:

```bash
python -m pytest -q --no-cov tests/unit/difference/test_negative_evidence_channel.py tests/integration/evidence/test_failed_observation_route.py tests/unit/state/test_canonicalize.py tests/integration/difference/test_state_observation_difference.py tests/integration/change/test_authority_to_change.py tests/unit/reflow/test_atomic_commit.py tests/unit/reflow/test_route_composition.py
ruff check src
mypy src --platform linux
python scripts/validate_schemas.py
```

各IDのテスト確認範囲は上表の参照先であり、7ファイル合計132件が成功した。全テストスイートの実行結果ではない。

参照先の存在、テストPASS、実際のRuntimeでの証拠消費は異なる状態である。対象実装は各リンク先にあり、この文書自身がKernel契約やRuntime Evidenceになるわけではない。

## 6. 更新と受入の境界

本書は[ORIGIN.md](../ORIGIN.md)と[Kernel Constitution](../00_KERNEL/KERNEL_CONSTITUTION.md)に従属する説明文書であり、独立したAuthority ownerではない。既存の封印記録・Kernel契約・開発Bindingの改定をこの追記で授権しない。

親の追加定義が既存のOrigin・Kernel契約と実質的に衝突する場合は、本書の表を根拠に下位層で上書きせず、Origin compatibility observationと明示的な改定手続きへ戻す。新体系の名称を過去の実装・Human受入へ遡及適用しない。

親側のマージ、子側のマージ、情報源の更新は別の状態である。両者がマージされた後に対象SHAを再照合し、添付情報源を再生成する。本PRの作成・CI・採択・mergeを相互に代替させない。
