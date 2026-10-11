# ホームズ → ワトソン：VAPB 日次指示

## 固定の受け渡し場所

- Repository: `UkkyaGuiyo/vapb`
- 指示専用branch: `docs/holmes-watson-handoff`
- 最新指示: `HOLMES_TO_WATSON.md`（このファイル）
- 固定URL: https://github.com/UkkyaGuiyo/vapb/blob/docs/holmes-watson-handoff/HOLMES_TO_WATSON.md
- 設定日: 2026-10-11 JST
- 指示用branchの作成元: `842067fb1aa29eeb4b9f3a4560ac6d529a21f50a`

このbranchは指示の受け渡し用。ここに含まれる製品sourceを最新版と見なさず、開発・実験の作業branchにもしない。ホームズは実際の開発branchと結果を読み、次の一手をこのファイルへ保存する。ワトソンは指示を検証して実行し、結果をGitHubへ保存する。

## 現在の指示

- Instruction ID: `NONE`
- Status: `WAITING_FOR_FIRST_DAILY_BRIEF`
- 種別: 受け渡し設定のみ。新しい技術実験・製品修正の指示はまだ発行していない。
- 初回日次捜査の予定: 2026-10-12 朝8時ごろ（Asia/Tokyo）。
- 次の指示は、発行時のGitHubと既存実行結果を確認してからここへ記載する。

この初期状態を理由に、別途承認済みの開発を停止しない。既存HOLMES実験を再実行しない。このファイルの公開はCodexの自動起動・自動購読の設定を意味しない。

## ワトソンの読み方

作業中のcheckoutを切り替えたり、未保存変更を上書きしたりせず、固定URLまたは次の読み取りで取得する。ローカルの`origin`が正規repositoryを指すことを先に確認する。

```sh
git remote get-url origin
git fetch origin docs/holmes-watson-handoff
git show FETCH_HEAD:HOLMES_TO_WATSON.md
```

- `READY`の指示があり、そのInstruction IDを未実行なら、指示の対象branch/SHA・目的・根拠・判定条件を読む。
- 実行前に対象開発branchの現在の差分、ローカル変更、AGENTS.md、PRODUCT_SPEC.md、既存権限・実機資源を確認する。指示作成後の変更で前提が崩れていたら、その差を記録し、古い指示を機械的に実行しない。
- ホームズの仮説も検証対象。指示を正解の証拠に使わない。入力生成と結果判定を独立させ、反例を残す。
- 同じInstruction IDを実行済みなら再実行しない。`WAITING_FOR_RESULT`、`BLOCKED`、`NO_NEW_ACTION`、この初期状態では新たな実験を自動的に開始しない。
- 製品作業は指示で特定した開発branchまたは既存ルールに沿う隔離branchで行う。指示専用branchを実装branchへmergeしない。無断merge、Release、force-push、未保存作業の破棄は行わない。

## 結果の戻し方

既存の実験・検証記録の保存先を優先し、作業branchへ結果をcommit/pushする。新しい管理システムは作らない。結果本文に以下を記録する。

- Instruction IDと、読んだ指示ファイルのcommit。
- 実際の開始branch/SHA、実行source、変更した範囲。
- 確認した証拠と、仮説を支持・反証・未判定とした理由。
- 実行したテストのPASS/FAIL、未実施のNOT_RUN。安全な拒否の成功と、製品としての復元成功を区別する。
- 実装・製品適用の有無、残る問題、原本保全、必要な追加証拠。
- 結果のbranch、ファイルpath、commit URL。push後にGitHubを再読込し、保存結果を確認する。

購入素材・私的アセット・個人情報・秘密・私的生ログは公開しない。検証に必要な私的結果は許可された環境内に保持し、公開記録には匿名化した要約のみを残す。

ホームズは次回、Instruction IDと結果の実ファイルを結び付けて読む。結果がGitHubに見当たらない場合は「実行結果未確認」と扱い、成功を推測しない。

## ホームズの更新方法

このファイルを最新指示の正本とし、過去の指示全文はGit履歴に残す。新規指示は`HOLMES-YYYYMMDD`、同日訂正は連番を付け、以前の指示commitと最新結果へのリンクを明記する。処理中の指示を競合する別指示へ黙って差し替えない。

発行時には「指示ID・状態・作成日時・対象開発branch/SHA・前回指示/結果・根拠・更新仮説・今回の目的・具体手順・必要な観測・支持/反証/未判定条件・製品適用範囲・原本保護・停止/ロールバック条件・結果保存先」を、単独で実行判断できる本文として記載する。

保存前にこのファイルの最新blob SHAと他者の変更を確認する。競合時は再取得して調整し、履歴を上書きしない。保存後はcommitと本文をGitHubから再読込する。保存失敗時は未保存と明記してチャットへ指示全文を退避する。

GitHubの指示更新自体を、ワトソンによる製品実装・テストの進捗として数えない。チャットには要点、変更理由、保存先とcommitを報告する。

## 既存証拠の入口

- 調査branch: `feature/holmes-material-correspondence-20261011`
- 確認済みbranch先端: `842067fb1aa29eeb4b9f3a4560ac6d529a21f50a`（設定時点。未来の最新版として固定しない）
- [HOLMES最終報告（固定commit）](https://github.com/UkkyaGuiyo/vapb/blob/842067fb1aa29eeb4b9f3a4560ac6d529a21f50a/tests/evidence/holmes-material-correspondence-20261011/FINAL_REPORT.md)

本ファイルは受け渡し方法の設定。実行していない実験の結果や、新たな技術的結論を追加していない。
