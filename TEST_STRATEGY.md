# Test Strategy

## Policy

Acceptance Testを機能実装前に定義し、Blender 5.2.1 LTS onlyで実行する。単体テストや設定確認だけを実データ成功の代替にしない。Baselineとの差分、実Package結果、未検証事項を分けて記録する。

## Test Levels

1. **Unit**: parser、path safety、material model、identity変換、lifecycle cleanup。
2. **Synthetic Integration**: Blender登録、operator handoff、最小Scene、roundtrip manifest。
3. **Real Package Integration**: `RepresentativeAvatar-CaseA-Ver1.3.1.unitypackage`の実展開・FBX・Prefab・Material・Image。
4. **Foreground UI Lifecycle**: File Browserからのforeground開始、async prepare、Prefab handoff、modal終了。
5. **Post-Import Stress**: visibility、select/deselect、shading、frame、delete/restore後のprocess生存。
6. **Serial Import**: 同一Packageの連続実行とsession混線防止。
7. **Multi-Package Integration**: 複数Packageのidentity propagation、registry、reverse lookup、collision report。自動mergeは対象外。
8. **Roundtrip Export**: FBXとmaterialmap sidecarのschema、binding、再読込。
9. **Unity Finalizer**: Unity EditorでGUID/Path優先remap、元`.mat`非変更。
10. **End-to-End**: Blender編集 → Export → Unity import/finalize →最終Prefab。現状未完了。

## Baseline Regression

毎回最低限、次を確認する。

- Add-on register / unregister
- Real Package import returns `FINISHED`
- Object約113、Mesh約103、Armature 4、Shape Keys存在
- Native crashなし、完了後modal残留なし
- PackageReader性能と抽出件数の意図しない悪化なし
- ZIP `testzip None`

Material変更時は件数だけで合格にしない。Material bindingとTexture bindingの正確性を別途確認する。

## Multi-Package Identity Acceptance Tests (MPI-001..012)

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| MPI-001 | Package fingerprint | 同一bytesは同じSHA-256 package idになる |
| MPI-002 | Path independence | Package移動・改名でidentityが変わらない |
| MPI-003 | Byte distinction | 異なるbytesは別package idになる |
| MPI-004 | Canonical key | package + GUID + path/fileIDで一意化される |
| MPI-005 | Same-name assets | 同名でも別pathは衝突しない |
| MPI-006 | GUID collision | 異なるPackageの同一GUIDを報告する |
| MPI-007 | Path collision | 異なるPackageの同一Asset Pathを報告する |
| MPI-008 | No auto-merge | collision発生時もasset recordを統合しない |
| MPI-009 | Duplicate import | 同一Packageの再importを明示statusにする |
| MPI-010 | Legacy isolation | package metadataのない旧datablockを推測結合しない |
| MPI-011 | Propagation / reverse lookup | Object、Material、Imageのcustom propertyとlookupが一致する |
| MPI-012 | Scene persistence | registry JSON roundtripとsingle-package回帰が通る |
| MPI-013 | Same package / different prefab / same fileID | Asset Path scopeにより別identity・別recordになる |
| MPI-014 | fileID without parent | `AMBIGUOUS_IDENTITY`でcanonical registryへ登録しない |
| MPI-015 | GUID + fileID scope | 異なる親GUIDの同一fileIDが別identityになる |
| MPI-016 | Same package two prefabs | 同一Package内の別Prefabがoverwriteなしで登録される |
| MPI-017 | Save / reopen | `.blend`再開後もpackage/path/fileIDと別identityを保持する |

## BUG-002 Acceptance Tests

実装前に以下を受入条件として固定する。現Baselineでは未実装・未達であり、今回の移行では修正しない。

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| MAT-001 | Unity Renderer Material Slot → Blender Material Slot | 正しいUnity Material GUIDへ対応する |
| MAT-002 | Unity Material Main Texture GUID → Blender Image | 正しいTexture GUIDのImageへ対応する |
| MAT-003 | Blender Image filepath | sourceまたは保持された有効Pathが存在する |
| MAT-004 | Material Preview | missing texture由来のMAGENTAがない |
| MAT-005 | Save `.blend` → reopen | bindingが保持される |
| MAT-006 | 同名Material / 別GUID | 別Assetとして混同しない |
| MAT-007 | Prefab explicit Renderer binding | name fallbackより優先される |
| MAT-008 | FBX `.meta` externalObjects | GUID mappingを適切に利用する |

## BUG-003 Acceptance Tests

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| VIS-001 | Material uses nodes | 対象Materialで`use_nodes == True` |
| VIS-002 | Image Texture node identity | Main Texture相当のImage Texture Nodeが存在し、正しいImage datablockを参照する |
| VIS-003 | Base Color connection | Main Texture Color出力が最終的にPrincipled BSDF Base Colorへ到達する |
| VIS-004 | Shader output connection | Surface shaderがMaterial Output Surfaceへ接続されている |
| VIS-005 | Color multiplication | Unity Main Color / Base ColorとTexture Colorの乗算等が成立する |
| VIS-006 | UV path | Textureが適切なUV経路またはImage Texture default UVで参照される |
| VIS-007 | Alpha path | 透明MaterialのAlpha経路が成立し、不透明Materialを誤って透明化しない |
| VIS-008 | Representative real materials | Face/Skin、Hair、SampleGarment/Clothesの3系統でnode graphが成立する |
| VIS-009 | Save/reopen persistence | `.blend`再起動後もnode graphとImage bindingが保持される |
| VIS-010 | Human Material Preview | 通常UIで肌・髪・目・着物等のTextureが目視表示される。0.3.0 Baselineでユーザー実機確認PASS |

## BUG-003 Locale / Active Output Acceptance Tests

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| VIS-011 | Active Material Output | Textureを受け取るSurface Shaderが接続された`OUTPUT_MATERIAL`が`is_active_output == True` |
| VIS-012 | Locale-independent Node Lookup | 日本語UIでもPrincipled / Material Outputを表示名ではなくNode typeで取得できる |
| VIS-013 | Single Effective Surface Graph | 描画対象のactive Surface chainが一意で、不要なduplicate Principled / Outputを生成しない |
| VIS-014 | Japanese UI Regression | `ja_JP`条件でTexture → Shader → active Material Outputの到達性が成立する |

## Editable Texture Workflow Acceptance Tests

実装前に以下を受入条件として固定する。既存のImage datablockをSource of Truthとして使用し、同じworking fileへ手動保存・手動再読込する。自動watcher、コピー、backup、GUID再発行、`.meta`新規生成は行わない。

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| ETX-001 | Imported Texture Identity | ImageにUnity GUID、Asset Path、Source Path、filepathが表示・保持される |
| ETX-002 | Direct Save | Blender編集を同じworking fileへ保存し、filepathとImage datablockが変わらない |
| ETX-003 | External Edit Reload | 外部変更後、既存Image.reload()で同じImage datablockへ再読込できる |
| ETX-004 | Material Persistence | 再読込後もMaterialのImage Texture node bindingが同じImageを参照する |
| ETX-005 | No Automatic Copy | `_modified`、`_copy`、`_backup`等の自動ファイルを生成しない |
| ETX-006 | No New GUID | 保存・再読込でUnity GUIDを変更しない |
| ETX-007 | Meta Preservation | 既存のUnity `.meta`由来identityとworking filepathを保持する |
| ETX-008 | Save/Reopen | `.blend`保存・再開後もImage、filepath、GUID、Asset Path、bindingが保持される |
| ETX-009 | Missing Source File | source消失時に`MISSING_SOURCE`を返し、fallbackや代替Imageを生成しない |
| ETX-010 | Real Package Visual Reload | Face/Hair/SampleGarmentの実Packageで外部変更→再読込→Material Preview更新→元bytes復元を確認する。UI視認ができない場合は`UNVERIFIED`とする |

## External Texture Editor Launcher Acceptance Tests

実装前に以下を受入条件として固定する。Editor設定はAddon Preferencesに保存し、Texture identityや`.blend` Image custom propertyへ保存しない。外部起動は`[editor_executable, working_texture]`のargument list、`shell=False`、非同期`Popen`で行う。

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| EXT-001 | Editor Discovery | Windowsのknown editor候補をbest-effortで検出し、重複なく一覧化する |
| EXT-002 | Manual Selection | Browseで選択した実在`.exe`のpath/nameがAddon Preferencesへ保存される |
| EXT-003 | Persistence | Blender再起動相当後もAddon PreferencesからEditor path/nameを取得できる |
| EXT-004 | First Launch | Editor未設定時、OpenボタンからEditor selection menuへ進める |
| EXT-005 | Direct Launch | Editor設定済みならselectionなしで登録Editorを直接起動する |
| EXT-006 | Argument Safety | `subprocess.Popen([editor, texture], shell=False)`形式で、shell command連結を行わない |
| EXT-007 | Missing Editor | 保存Editorが存在しない場合`EDITOR_NOT_FOUND`を返し、勝手にfallbackしない |
| EXT-008 | Dirty Protection | `image.is_dirty == True`の場合`UNSAVED_CHANGES`で起動を拒否する |
| EXT-009 | Unity Identity Protection | 起動前後でGUID、Asset Path、Source Path、Image datablockが不変である |
| EXT-010 | Real UI | Blender 5.2.1実UIで代表Textureを選択Editorへ開く。Computer Use不可時は`UNVERIFIED`とする |
| EXT-011 | Launch Failure Handling | `Popen()`の`OSError`を`EDITOR_LAUNCH_FAILED`へ変換し、operatorが`ERROR` reportと`CANCELLED`相当で処理する |

### External Texture Editor Human Follow-up

2026-09-15、Blender 5.2.1 Japanese UI / Krita / `SampleGarment_col.png`で、ETX-010、EXT-003、EXT-005、EXT-010をPASS確認した。外部編集後の同一working file保存、BlenderのReload from Disk、Image Editor・Material Preview・3D avatarへの反映、再起動後のKrita保持、直接起動を含む。過去の未検証記録は履歴として保持し、現行結果へ追記する。

## MRUS Recovery Acceptance Tests (PLANNED / UNVERIFIED)

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| REC-001 | LipSync capture | Avatar DescriptorのLipSync modeとviseme assignmentを正しく記録する |
| REC-002 | LipSync restore | Shape Keyが維持されている場合、元viseme assignmentを復元する |
| REC-003 | Object rename rebind | Face → Face_Finalでもpersistent identityで対象を再発見する |
| REC-004 | Missing Shape Key | Shape Key削除時に代替割当せず`MISSING_TARGET`にする |
| REC-005 | Animator binding path rebind | identity対応が明確なHierarchy/path変更を新pathへ変換する |
| REC-006 | PhysBone target recovery | root / collider targetが存在する場合、正しいidentityへrestoreする |
| REC-007 | Missing dependency | Modular Avatar等の依存が無いProjectでは`MISSING_DEPENDENCY`を返し、代替Componentを生成しない |
| REC-008 | Ambiguous identity | 候補が複数ある場合、勝手に決めず`AMBIGUOUS`にする |
| REC-009 | Restore report | 全restore対象についてstatusを記録する |
| REC-010 | Roundtrip E2E | UnityPackage → Blender → edit → export → Unity Finalizer → Avatar validationを通す |

現時点ではREC-001〜REC-010はPLANNED / UNVERIFIEDであり、0.3.0 Baselineの達成済み機能を示さない。

## MRUS Roadmap

0.3.0 Importer Baseline → Multi-Package Identity → Bridge Manifest v2 / State Snapshot → Unity Finalizer（Material、LipSync / Avatar Descriptor、Animator / Expressions、PhysBone / Contact、Third-party Components）→ Full End-to-End Roundtrip。

## Evidence Rules

- `PASS`: 実行結果と対象環境が記録されている。
- `IMPLEMENTED`: sourceの存在だけでなく、該当テストがある。
- `UNVERIFIED`: UI操作、環境依存、または未実装機能を成功扱いしない。
- `experiment_logs/`は各実験の詳細証拠として保持し、現行`TEST_RESULTS.md`は現Baselineを主にする。

## Current Baseline Result

0.3.0 Baselineでは45 Python tests PASS、Blender 5.2.1 register/unregister PASS、実Package foreground FINISHED、BUG-002/BUG-003 CLOSED、ETX-010 / EXT-003 / EXT-005 / EXT-010 human verification PASSを確認済み。詳細は`TEST_RESULTS.md`と`experiment_logs/BASELINE_0_3_0_FREEZE_001/REPORT.md`を参照する。
-
## Real Multi-Package Visual E2E Acceptance Tests (MPV-001..012)

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| MPV-001 | Sequential A→B import | 同一SceneでA/Bのgeometryが共存する |
| MPV-002 | B Renderer slot | BのslotがB Material GUIDを参照する |
| MPV-003 | B Material node | BのImage Texture nodeがB Imageを参照する |
| MPV-004 | Same material name | 同名MaterialでもPackage identityが分離される |
| MPV-005 | Same texture filename | 同名Texture filenameでもcross-package共有しない |
| MPV-006 | externalObjects GUID | FBX externalObjectsのGUID解決がPackage scopedである |
| MPV-007 | Prefab Renderer GUID | Prefab明示Renderer参照がname fallbackより優先される |
| MPV-008 | Unique suffix fallback | `.###` suffix除去後の一意base名だけをfallback採用する |
| MPV-009 | Ambiguous refusal | 複数候補のname fallbackを未解決のまま拒否する |
| MPV-010 | No placeholder slot | placeholder Objectに解決済みMaterialを割り当てない |
| MPV-011 | Save / reopen | A/B bindingとpackage identityが再開後も保持される |
| MPV-012 | Regression | MPI-001..017とsingle-package material/texture回帰がPASSする |

## UnityPackage Exporter Acceptance (EXP-001..015, PLANNED)

Exporter、reachability pruning、GUID/path collision policy、Unity Finalizer roundtripはEXP-001..015として仕様化するが、0.4.0 candidateでは未実装・未検証である。Export時のみpruneし、編集時の未使用datablockを削除しないことを必須条件とする。
## Cross-Package Dependency Acceptance Tests (CPD-001..015)

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| CPD-001 | Material-only Package | FBX 0 / Material > 0でFINISHED |
| CPD-002 | Texture-only Package | FBX 0 / Material 0 / Texture > 0でFINISHED |
| CPD-003 | Geometry first pending | 未提供Material GUIDをUNRESOLVED保存 |
| CPD-004 | Material late bind | 後続Packageのunique Materialへcross-package bind |
| CPD-005 | Reverse import order | Provider firstでも最終結果が同一 |
| CPD-006 | Save/reopen pending | 保存・再開後もDependency recordを保持し解決可能 |
| CPD-007 | Ambiguous provider | 同GUID provider複数時はAMBIGUOUS_PROVIDER、無自動bind |
| CPD-008 | Local priority | local providerをcross-package providerより優先 |
| CPD-009 | Material→Texture | 後続Texture-only PackageでImage nodeをlate bind |
| CPD-010 | No name guessing | 同名だけではcross-package bindしない |
| CPD-011 | Idempotence | resolver再実行でslot/node/recordを増殖させない |
| CPD-012 | externalObjects | FBX externalObjects GUIDをDependency record化・解決 |
| CPD-013 | Registry roundtrip | JSON persistenceがsave/reopenで保持される |
| CPD-014 | MPI regression | MPI-001..017 PASS |
| CPD-015 | MPV regression | MPV-001..012 PASS |

## Phase B Sibling Package Acceptance (SPD-001..005)

| ID | Acceptance Test | 合格条件 |
|---|---|---|
| SPD-001 | Same-folder discovery | 選択Packageの親フォルダだけを探索し、別製品フォルダを見ない |
| SPD-002 | GUID exact provider | prefab/material/FBX externalObjectsのGUIDで候補を一意化し、名前推測しない |
| SPD-003 | Transitive discovery | A→B→Cの依存を未解決GUIDがなくなるまで検出 |
| SPD-004 | Ambiguity safe | 同GUID provider複数時はAMBIGUOUS/PARTIALとして自動選択しない |
| SPD-005 | Grouped import | SampleAvatarB起点のImport TogetherでGeometry/Material/Textureを同一Sceneへ反映 |

SPD-001..005はPython fixtureおよびBlender 5.2.1 synthetic SampleAvatarB-like testでPASS。実アセットのforeground目視は別途Human Retest。
