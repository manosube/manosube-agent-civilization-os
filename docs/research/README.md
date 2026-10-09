# MANOSUBEの統治状態の連続性に関する設計と公開証拠

AIエージェントが交代しても、目的、権限、完了の根拠、未解決事項を次の判断へ接続できるか。本稿は、この問題をMANOSUBE Agent Civilization OSの設計と公開開発記録から検討する、公開議論用の設計・経験報告である。

[日本語本文](MANOSUBE_governance_continuity_ja.md)では、四つの不変条件、先行技術との重なり、実装と強制の境界、既存証拠、次の比較評価を説明する。[検証対象と版情報](publication_sources.json)から主要な固定参照を確認できる。

既存の二課題比較は両条件で成功し、限定されたCopilot試行には受理・マージ・変更後状態の確認記録がある。信頼性や安全性の一般的な優位性は、今後の比較評価の対象である。

## 議論したい問い

- 目的と対象、権限の範囲、証拠の鮮度、未解決事項の継承という四条件は、統治状態の連続性を十分に捉えているか。
- 永続化、認可、実行時制御を備えた既存基盤に対し、共通の遷移契約が追加する価値はどこにあるか。
- 誤った完了受理を減らす効果と、記録・検証の費用を、どの課題分布と指標で比較すべきか。

## English overview

An [English companion for external evaluation](EXTERNAL_EVALUATION_EN.md) now provides
the main argument, implementation boundaries and planned evaluation. It is a summary,
not a complete translation of the Japanese manuscript.

The [English manuscript translation draft](MANOSUBE_governance_continuity_en.md) covers
all sections and appendices of the second Japanese edition and awaits author review.
It preserves the original code-analysis version and evidence date.


This Japanese design and experience report examines governance continuity in AI-assisted software development: whether objectives, authorization scope, completion evidence, and unresolved differences remain usable when the executor changes. It analyzes MANOSUBE's canonical state cycle and public development records in relation to persistence, durable execution, authorization, and runtime controls.

The available comparison contains two deterministic tasks, with both conditions succeeding. A bounded Copilot trial has public records of review, human acceptance, merge, and after-state confirmation. These support feasibility within their recorded scope. General improvements in reliability and safety remain hypotheses for controlled evaluation. The report invites scrutiny of the proposed invariants, enforcement boundaries, and evaluation design.

## 版と位置付け

著者：愁猴（SHUKOU）。第2版：2026年10月7日。コード分析は固定コミット、Copilot試行は別の受理headと変更後コミットを対象とする。査読済み論文ではなく、公開議論用の草稿である。

このディレクトリは設計の分析と議論のための資料を保持する。Kernel契約、正規状態、Phase受理記録、開発上の権限を更新するものではない。引用は本文とリポジトリのCITATION.cffを参照されたい。
