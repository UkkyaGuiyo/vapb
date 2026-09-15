# Public Repository Hygiene Audit

監査対象: current tracked tree / `feature/multi-package-identity`

## Current tree

- Developer absolute paths: PASS
- Username / home-directory dependency: PASS
- Real-world asset/product fixture identity: PASS
- Real UnityPackage filename dependency: PASS
- Obvious credentials / private keys / tokens: PASS
- Proprietary binary assets (`.unitypackage`, `.fbx`, `.blend`, `.psd`, `.tga`): PASS
- Public hygiene tests: PASS

## Real-package harness

`tests/blender_real_identity_verify.py`は`UNITYPACKAGE_REAL_TEST_FILE`またはBlender CLIの`--`引数だけを入力とし、未指定時は`REAL_PACKAGE_TEST_SKIPPED`で終了する。repository内に実Package名・実Package path・期待する第三者Asset identityは保持しない。

## History

Reachable historyには過去の実環境検証で生成された、実Package identityと開発者ローカルpathへの参照が存在した。credential、private key、tracked proprietary binaryは履歴監査で検出しなかった。history rewrite / force pushは実施していないため、Public化前にsanitized squashまたはclean public branchを採用するか、別途判断が必要である。

## Policy

Synthetic fixtureとgeneric harnessのみをrepositoryへ保存する。real-world testを実行する場合は、local-only environment variable / CLI inputを使い、結果はaggregate statisticsへ限定する。CPD、SPD、Identity、Material、Texture、Importerのproduction behaviorとExporter実装は今回変更していない。
