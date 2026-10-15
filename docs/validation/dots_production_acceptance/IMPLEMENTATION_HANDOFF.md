# 実装引継ぎ

このPRは本番受入試験の設計・契約構築。実行harnessは未実装、real dots未接続、試験結果なし。

## WU1の成果物
1. PROTOCOL.mdの全gateに、既存ownerのexact関数・入力・consumerを対応。
2. 5体系の正規定義/commit/invariant/caseへの5行対応表。
3. dotsと利用可能なapp/環境/実行履歴取得のread-only preflight。別モデルや通常チャットをdotsに代入しない。
4. 実行対象・隔離資産・grant・モデル・金額/呼出/token上限・停止経路のmanifest。未確定fieldがあればlaunch不可。
5. 現行Codex専任/既存activation禁止と整合した担当・変更必要箇所を提示。

## WU2の成果物
実接続adapter、既存Kernel自然経路driver、独立oracle、raw recorder、recompute、stop/reconcile、ケース生成、実運用runbook。
case-catalog.jsonは試験契約データであり、実行可能harnessや実証receiptではない。結果fieldを手埋めしてPASSにしない。

## レビュー
開発policyを上書きしない。実装者と技術/構造検査者を分離し、SHUKOUの意味決定・最終受入・手動mergeを保持する。
freeze前にoracle仕様と実task40件を別検査し、達成可能性を検証する。条件ごとの通常検証能力をそろえる。
モデル間の記憶隔離とnative取消ができない場合は、その制限を実結果として提示する。

## 終了
仕様PRのmergeだけで本番合格にしない。Issueは実行・結果・受入まで追跡する。
