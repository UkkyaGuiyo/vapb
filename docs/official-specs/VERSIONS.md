# バージョン適用表

確認日: 2026-10-11 UTC。更新指示ではなく、根拠の適用範囲の表。

|対象|公式現行情報|VAPB側の読み取り|限界・適用|
|---|---|---|---|
|Unity最新Manual|U00はUnity **6.6 / 6000.6**、本文はlatest releaseと表記|VAPB実測対象ではない|配布最新patch番号、stable download一覧は取得本文から確定できず不明。Manual表示をpatchの証明にしない|
|Unity最新LTS|U39 support pageは **6.3 LTS**、2027年12月までsupport。6.0 LTSは2026年10月までと記載|VAPBに移行した根拠なし|最新LTS patch番号は不明。最新Manualが6.6でも最新LTSが6.3であることとは矛盾しない|
|VRC対応Unity|V01は **2022.3.22f1** と明記|`tests/unity_alias_oracle/ProjectSettings/ProjectVersion.txt`も2022.3.22f1。READMEも同版|現行製品checkoutの起動状態を検査していない。Unity仕様詳細は2022.3系列APIを主に使う。系列Manualの更新日は個別Editor patchの実証ではない|
|Blender VAPB target|B01固定tagはversion=502、patch=1、cycle=release、suffix=LTS|`BASELINE.md`、`README.md`は **5.2.1 LTS専用** と記載|公式download / LTS一覧本文取得不能。5.2.1 LTS tagの存在・定義は確認、2026-10-11時点の最新stable/最新LTS patch順位は**不明**|
|Blender latest/current docs|検索結果のlatest Manual表題に5.2 LTSが現れるが本文取得不能|既存実測文書は5.2.1を記録|検索snippetだけで最新patch・API本文を確定しない。APIの説明はSRCで補助しDOCへ昇格しない|
|VRC SDK|V02 release indexの最新項目は **3.10.5** / 2026-09-04、V03 changelogも同版|`docs/VAPB_BOUNDED_SKIN_ROUNDTRIP_ACCEPTANCE_20261001.md`にOracleのbase / avatars 3.10.5という既存記録|既存記録の版であり、Titanの稼働projectの現在manifestは不明。今回SDKを取得・起動・変更していない。SDK版とclient版は別|
|VRC client / platform|公式CreationはPC/mobile等に別制限を設ける|今回のclient測定なし|現client build番号、upload後runtime同等性は不明|

## 固定source参照

- Blender公式GitHub mirror `v5.2.1`: ref object SHA `9e2066aef7ef7e20c142ad7bd3303138a4304c93`。本文出典では読み取ったtagを使う。tagと実行binaryの一致確認は未実施。
- Unity公式 `UnityCsReference` 2022.3 branchを確認したcommit: `a322ce5f78a82cf7ea211857a45338136ed7a22f`。C# bindingsにnative externがあってもnative実装は見えない。
- VAPB実repo/remoteは `UkkyaGuiyo/vapb`。既定branchは取得時 `feature/multi-package-identity` だったが、本資料は明示指定された `feature/r2-material-slot-reorder` の基点SHAから分離した。既定branchを更新しない。

## 既存資料との差

`docs/CASE_B_PACKAGE_ONLY_MATERIAL_BOUNDARY.md` の3リンク（external map、GUID/fileID、materialName）は再取得する。前二者は今回API本文を確認済。既存資料の実測集計・私有データからの結論を新しい公式実測として扱わない。

`docs/EXPORT_RESEARCH_CORRECTIONS.md` のgzip tar / GUID directory / asset・asset.meta・pathnameの分類は**LOCAL/EMPIRICALのまま**。U08 Manualはunitypackageが圧縮されたファイル集合・metadataを保持することを説明するが、内部tar member schemaの安定保証は説明しない。

`docs/R2_STAGE3_NATIVE_FBX_SYNTHETIC_VERIFICATION.md` の座標変換は特定fixture・設定の既存実測。今回U33のaxis conversion / units説明を追加したが、当該数式を一般仕様へ昇格しない。
