# #118 WU1 — 実作業から人間への報告接続設計

```text
DIFFERENCE_ID=D-HUMAN-WAIT-REPORT-DELIVERY-CONNECTION
DOCUMENT_STATUS=PROPOSED_FOR_SHUKOU_ADOPTION
OBSERVATION_DATE_JST=2026-10-20
OBSERVED_MAIN=69f6b9732ca2899d99101b0f7f25f8e282810bb1
WORK_CLASS=POST_V1_0_OPERATIONAL_CONNECTION
IMPLEMENTATION_AUTHORIZED=false
LIVE_NOTIFICATION_AUTHORIZED=false
RUNTIME_PROVEN=false
ISSUE_CLOSURE_RECOMMENDED=false
```

## 1. 構造判断・到達点

既存coordination ownerを維持し、外側に「実行観測・単一writer・配送」を接続する。
推奨する最初の一経路は、指定Linux/POSIX環境のClaude Codeで行う一つの低リスクwork unit → 既存coordination ledger → 別processの配送器 → このrepositoryのIssue #118コメントである。
これは実装可能性に基づく提案であり、愁猴の現Claude Code環境で到達済みとは主張しない。
開始前の表示、稼働中の最大10分間隔、外部待機と停止の区別が目標。追加AI呼出しは不要。

## 2. 観測済みと未観測

| 項目 | 状態・証拠 |
|---|---|
| 正規契約 | `00_KERNEL/HUMAN_AGENT_WORK_COMMUNICATION.md`、`16_WORK_TIME_TRANSPARENCY/WORK_TIME_TRANSPARENCY_CONTRACT.md` |
| 記録API | `work_time_transparency/route.py` のopen/update/terminal、`adapters.py::ProgressReporter`を静的確認 |
| 永続化 | `store/file_store.py::commit_coordination_record_at_tip`。既存append-only ledgerとtip照合を再利用 |
| 遅延検出 | `engine.py::is_heartbeat_overdue`。検出器でありschedulerではない |
| 通知UI・scheduler | 既存契約§14が未実装と明示。今回の検索でもClaude固有hook設定・配送実装は確認できない |
| #117 | head `ae717f989a4343df621311cfe0dc532d8fe731b5`、merge `5a0cc5b952946270961586ce4da5e0bb2880048e`、merged |
| #119 | head `527d94b4f083acf34a7cc8010e8ff747de5ff281`、merge `163cc4a983095ceed818afa48f47cba5ca5a42e2`、merged |
| 後続#121 | main履歴にmerge `4d657def3a8a9b819b8befea2b23af4e28a643be`。`tests/dots_production_acceptance/driver.py::ProcessSupervisor`も存在。初期Issue本文の「設計のみ」から進展している |
| 実Claude環境 | OS、version、CLI/Desktop/cloud区分、hook実効性、Storeへの読書き、常時稼働性、認証権限はUNOBSERVED |
| 人間への到達 | コメントの保存、端末通知、既読、10分運用のいずれも本WUでは未実証 |

添付情報源は役割・憲法の参照に用いた。03の古いPhase 13 headerを現在状態として採用しない。
現在の役割はlive `03_BINDING/CURRENT_REPOSITORY_DEVELOPMENT_BINDING.md` Decision 0004に照合。
構造参謀が設計、選択済み適格executorが実装、SHUKOUが採択・最終受入・手動merge。

## 3. 実観測口と事前調査の限界

Anthropic公式hooks referenceを2026-10-20に読了。SessionStart、PreToolUse、PostToolUse、PostToolUseFailure、Notification、Stop、SessionEndと、共通入力session_id/cwd等が文書化されている。command hookのasync実行もある。
ただしNotificationは10分timerではなく、Stopは応答終了であってwork unitの合格ではない。hookの存在は導入先での実効性の証明ではない。

採択後、実装者が現在使用している環境で、モデルを新規起動せず確認できる設定・version・既存session情報からpreflightを行う。
必要項目：host種別、Claude Code versionと起動方式、repo/worktree、許可済みStore rootとBinding、hook設定の実効範囲、session照合方法、GitHub読取・Issueコメント書込の既存権限、background processの生存期間、0円の根拠。
既存sessionで確認できないhook発火はWU3までUNOBSERVED。cloudのprocess/認証にアクセスできなければBLOCKED_ENVIRONMENTとし、ローカルCLIを使用中と推定しない。
新credential発行、OS切替、モデル起動、常駐サービス導入をpreflightの名で行わない。

## 4. 一経路の具体構成

1. source tree外のrun manifestにrepository、issue=118、optional PR、base/head SHA、executor、session、project/Binding、work_unit_ref、許可記録、期待成果物、見積幅・確信度・主工程・変動要因を固定する。PR未作成はnullとして明示。
2. supervisorが既存`open_work_time_coordination`を呼び、開始通知を配送・readbackしてから、認可済みwork unitを開始可能にする。配送失敗・不明時には最初の仕事を開始しない。これは報告条件であり実装Authorityの付与ではない。
3. hookは短い許可済み観測eventをローカルqueueへ渡して即return。ネットワーク送信・長いtestをhook内で待たない。single supervisorだけが既存routeへ記録する。workerと配送processは同一coordinationへ直接並列書込しない。
4. supervisorは30秒以下のpoll目標で動き、通常5分ごと、重要変化時は即時に既存updateを記録。最大10分は既存契約のまま。実測遅延を残し、OS schedulingやnetworkまで無条件保証しない。
5. senderは別processでcommit済みrecordを検証・配送。worker/test/reviewのblocking waitから分離する。GitHub受理後のreadback時刻までを配送実績とし、記録時刻だけで期限内としない。
6. 最後は実work-unit receiptと観測結果に基づき既存terminalを記録し配送。Stop hook、process exit=0、報告成功だけでは業務完了にしない。`COMPLETED`は限定work unitの終了でありSHUKOU受入/mergeとは別。

hook観測から「テスト中のtoolが未完了」は言えるが「テストが何%終わったか」は言えない。
processが生きているだけなら「process生存を観測、工程進展は未観測」と表示する。
外部review待ちは対象PR/SHAのAPI実観測がある場合のみ、再予測=不明＋次回確認時刻。
情報不足なら最後の観測時刻を示し、正常稼働や残り時間を創作しない。
raw prompt、tool command、transcript、secretを公開コメントへ流さない。公開用はallowlistの短い工程名・状態・時刻・安全な参照のみ。

## 5. 既存APIと時刻の注意

`next_progress_update_due_minutes`はopenからの絶対経過分。開始時5、5分時10、10分時15のように渡す。「毎回5」ではない。
丸めを使う既存`clock.elapsed_minutes`、routeの遅延flagの意味を変更しない。
配送側はUTCの実timestamp差で表示期限と実配送遅延を測り、単調時計をpoll間隔に使用。UTC逆行等は時刻不整合として保全し、過去時刻を作って既存routeへ押し込まない。
`is_heartbeat_overdue`へ「過去に一回updateがあった」という理由で永久にhas_update=Trueを渡さない。terminal不在と最新tipの次期限を基準に、最新期限後に後続記録がないことを評価する。

再起動時は`resolve_open`、`resolve_tip`、`resolve_terminal_if_exists`を再読込し、sequence/predecessorを復元する。新しいProgressReporterがsequence=0へ戻ることに依存しない。
同じwork_unit_refから別openを捏造しない。復旧で新work unitが必要なら元openへのlineageと認可を先に固定する。
監視/配送はcanonical ledgerを手編集せず、独自のProject StateやAuthorityを作らない。

## 6. 配送候補・保証範囲

| 候補 | 適性・権限・制約 | 提案 |
|---|---|---|
| #118への新コメント | 既存作業面に集約可能。APIのIssueコメント書込とreadback権限が必要。公開repoなので本文は公開。通知設定・自身の投稿の扱いで端末到達は変わる | 第一経路。採択後の試験に限り許可する案 |
| PRコメント | 作成前の開始報告を置けず、PR横断時に分散。コメントは通知を発生させ得るが端末到達は別 | 初回は使わない |
| ローカルterminal/Desktop表示 | 端末利用中は見える。離席/スリープ中の到達に弱い | ローカル診断のみ。第二の通知宛先として追加しない |
| mail/Slack/独立VPS監視 | 別接続・権限・場合により費用が必要 | 今回範囲外 |

GitHub公式はコメント作成がnotificationを発生させると説明する一方、受信経路は利用者の通知設定に依存する。
本案はCOMMENT_SAVED、READBACK_VERIFIED、HUMAN_CONFIRMEDを別に記録し、端末pushや既読をAPI保存成功から推定しない。
同一identityのsenderを一つに限定し、定期コメントは5分ごと最大12件/時を目標。重要変化を含め全送信・retryに60秒以上の間隔を設け、間の変化は順序を保って一コメントへまとめる。rate-limit応答とRetry-Afterを優先する。
他appとの共有制限・サービス停止があるため、GitHubの一般上限内でも配送期限の無条件保証はしない。

worker停止時もsupervisor/senderが同じhostで生存すれば、未観測・期限超過を報告可能。
supervisor停止時はsenderが最新ledger期限を読んで警告可能。sender停止はローカルで可視化するがそのsender自身から遠隔通知はできない。
host停止・PCスリープ・回線断では遠隔配送保証なし。独立監視環境は未確認であり今回追加しない。復帰時に欠落区間と遅延を明示し、過去に正常通知した扱いにしない。

## 7. 再送・競合・receipt

transport sidecarはsource tree/Store外に置く配送履歴であり、coordination正本ではない。
key=(repository, issue, run_id, canonical record kind/id)。本文にそのevent markerとsequenceを入れる。receiptは本文digest、attempt時刻、comment ID/URL、readback時刻、status、任意のSHUKOU確認参照を持つ。
送信timeoutはUNKNOWN_DELIVERY。コメント一覧をmarkerで照合し、同じものが一つならreadback、複数なら重複を明示、確認不能なら盲目的なPOSTを止める。GitHubにexactly-onceの一般保証があるとは主張しない。
送信はcanonical順序。terminal後に古いprogressを最新状態として送らない。再開後の過去eventは遅延履歴としてまとめ、最新状態と区別。
保存失敗はdelivery receiptに成功を記入せず、通知失敗もwork-unit完了に変換しない。terminal後に残った配送はreconcile可能なoutboxに保持する。

## 8. 変更pathと分担

この設計PRは `docs/design/issue-118/REPORT_DELIVERY_DESIGN.md` のみ。
後続WU2の提案許可path：
- `scripts/human_work_reporting/`：preflight、observer bridge、単一writer supervisor、sender、renderer、transport sidecar。
- `tests/human_work_reporting/`：fixtureと有限ケース。
- `docs/design/issue-118/`：手順と結果。

既存WTT/Store/schema、Binding/policy、#116の`tests/dots_production_acceptance/`と契約、workflowは編集しない。
hook設定は導入先への設定変更になるためWU2は設定見本のみ、実activationはWU3の別途認可対象。
既存Python>=3.12と既存ownerを呼ぶ。既存#121のProcessSupervisorはtest harness内なのでproduction scriptsからimportしない。PID＋開始時刻による照合を設計参考にするが、今回監視器にkill権限は与えない。
実装開始直前にmain、open PR、changed paths、WTT署名を再観測。共通owner変更が必要ならそこで停止・順序調整。#116の計測閾値/168h運用/受入を変更せず、本Issueを追加gateにしない。

## 9. 有限受入ケース

| ID | 実施・合格証拠 |
|---|---|
| H01 | 実仕事開始より前にopenのコメントがreadbackされる。失敗時zero work-start |
| H02 | 一つの認可済みClaude Code work unitで実時間10分超区間、開始→進捗→外部待機→終了を人間が確認。短縮時計は代替不可。外部待機も本物のtest/review状態を使用 |
| H03 | 通常5分報告、実配送gap最大10分以内を実timestampで照合。超過があれば不合格として記録、記録だけの成功に置換しない |
| H04 | 見積超過、blocker、失敗、中断をfixtureで区別。残時間不明を0にしない |
| H05 | worker停止とsupervisor停止を別に注入。生存senderは最終観測と期限超過を表示。全host停止は通知不能の保証範囲を残す |
| H06 | 通信断・保存失敗・POST応答不明・再送・sender再起動・順序逆転で照合、未配送保全、重複の正直な表示 |
| H07 | 同時二work unitでrepo/PR/SHA/open/sessionを混同しない。新headは記録し、旧レビューの受入対象へ自動継承しない |
| H08 | secret canaryが公開payloadに出ない。報告成功でState/Authority/業務完了/mergeが変化しない |
| H09 | #116契約・既存owner無変更、追加課金0、新規モデル起動なし、許可path内。SHUKOUが到達と保証範囲を最終受入 |

H01/H02/H03は実環境、H04〜H08は隔離fault fixture＋必要な認可済み配送確認、H09は差分とreceiptで検証。
無断でモデルを起動して11分待たせる試験を作らない。既に認可された低リスクの実仕事へ結び付けられない場合H02はBLOCKED。

## 10. 見積・停止・次の人間判断

| 工程 | 予測幅 | 条件 |
|---|---|---|
| 実環境preflight | 20〜40分 | 既存環境への設定読取が可能。アクセス不能ならそこで結果報告 |
| WU2接続実装 | 2〜4時間 | 一host/一宛先、既存API無変更、既存認証で可能な場合 |
| WU2 fixture・統合検証 | 1〜2時間 | 上記有限ケース、実GitHub配送とモデル起動を含まない |
| WU3実時間試験・結果整理 | 30〜60分 | 環境/通知先/対象work unitを別途認可済みの場合 |
| 外部レビュー/CI待ち | 不明 | 最後の観測、次の確認時刻を報告。見積時間へ混ぜて完了を確約しない |

以上は作業予測でありSLAではない。環境差・新findingは即再見積。レビュー3roundで範囲/続行方針をSHUKOUに戻す案を維持し、回数だけで不具合を受容しない。
停止条件は環境未確認、権限不足、secret混入、追加支出の必要、共通owner変更、受入範囲外の修正、時計/identity矛盾。

採択対象：本設計、第一通知先#118、同一hostの限界、上記WU2許可path、preflight後に適格executorへ渡す順序、3round checkpoint案。
採択後もWU3の実通知/設定activation/実作業起動は対象と既存権限を固定して別途認可する。
現時点の残存Differenceは実環境観測、採択、限定handoff、実装、10分超到達実証、SHUKOU受入。Issue #118はopenを維持する。

## 11. 一次資料

- 観測したrepository: https://github.com/manosube/manosube-agent-civilization-os/tree/69f6b9732ca2899d99101b0f7f25f8e282810bb1
- Claude Code hooks: https://code.claude.com/docs/en/hooks （2026-10-20確認。製品機能と導入先実証を区別）
- GitHub issue comments: https://docs.github.com/en/rest/issues/comments
- GitHub rate limits: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- GitHub notifications: https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications
