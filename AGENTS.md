

## Failure Atlas protocol

Before starting non-trivial implementation, debugging, refactoring, design changes, migrations, import/export, serialization, builds, or tooling work, consult the shared Failure Atlas directly.

Canonical local checkout:

.failure-atlas/

### Before work

1. If `.failure-atlas/.git` exists, update it to the latest version without using force.
2. If it does not exist, clone `ai-dev-failure-atlas` from the currently authenticated GitHub account into `.failure-atlas/`.
3. If GitHub CLI is available, obtain the current account when needed with `gh api user --jq .login`.
4. Read `.failure-atlas/INDEX.md` first.
5. Search only for lessons relevant to the current error text, tools/frameworks, operation, symptoms, components, or previously failed approaches; do not read every lesson.
6. Before choosing an implementation approach, check relevant lessons' Future rule, Applicability, certainty, and Rejected alternatives.
7. Do not repeat an approach recorded as previously failed without new evidence.

### After work

If this work yields reusable knowledge for other tasks, save it directly to the Failure Atlas. Examples include a non-obvious implementation failure, an incorrect initial hypothesis or diagnosis, problematic ChatGPT/Codex instructions or interpretation, a diagnosed build/test/import/export failure, an environment-specific issue, recurrence of an earlier problem, an API/SDK/Unity/Blender/Git constraint, an effective diagnostic procedure, or a reason not to use an apparently reasonable design.

When saving:

1. Follow `.failure-atlas/AGENTS.md`, `.failure-atlas/docs/ANONYMIZATION.md`, and `.failure-atlas/templates/lesson-template.md`.
2. Search existing lessons and update the existing lesson instead of creating a new one when the cause is the same.
3. Do not save information that identifies a person or real project.

   Never include real names, handles, private repository names or URLs, ChatGPT conversation URLs or IDs, local PC usernames, absolute paths containing personal information, email addresses, physical addresses, tokens, API keys, cookies, credentials, or raw private logs.

4. Update `INDEX.md` at the same time.
5. Run `python scripts/validate_lessons.py` at the Atlas root.
6. Review the diff before commit and check that it contains no personal or secret information.
7. Sync the Failure Atlas with the latest remote before commit/push. Never force-push.
8. If a conflict occurs, do not overwrite remote history. Fetch the latest state and resolve it safely, or stop and report.
9. If Failure Atlas access or writing is unavailable, do not claim success. Return `KNOWLEDGE_REPORT` so it can be saved through ChatGPT.

The Atlas does not need to be read in full each time. Use this sequence:

INDEX → search → relevant lessons only.


## GitHub 保存状態の報告契約

正規リポジトリ: https://github.com/UkkyaGuiyo/vapb

- 新しい Codex スレッドでも最初にこのルート `AGENTS.md` を読み、各進捗・完了報告に Project、作業項目、現在の作業ルート、対象 branch と SHA を明記する。報告に未置換のプレースホルダーを使わない。
- 作業開始時と報告前に、実際の Git remote を上記の正規リポジトリと照合する。SSH/HTTPS と末尾の `.git` の違いは正規化して比較する。不一致や確認不能なら変更・push を止めて確認する。スレッドの題名や到着順でプロジェクトを決めない。GitHub API のみの場合は checkout がない旨と対象 repository・branch・path を作業ルートとして示し、API のリポジトリ情報で同一性を確認する。
- 実際に remote 保存・push を行い、GitHub 上の対象 commit とファイルを再読込して確認できた場合だけ、「このGitHubに保存したので見てね」＋リポジトリ URL＋commit／ファイルの直接 URL＋branch／SHA を報告する。
- 未保存・ローカルのみ・読み取りのみの場合は、「私はこのGitHubを使用しています」＋リポジトリ URL＋未保存の変更内容＋branch／基準 SHA を報告する。変更がなければ「未保存の変更なし」、読み取りのみならその旨を明記する。ローカル commit を GitHub 保存済みと扱わない。
- 確認者がリンク先の GitHub を読んで検証できるようにする。未公開のローカル差分は GitHub では見えないため、保存済みの内容と分けて報告する。
- この報告契約は、編集・push・公開・merge・実装再開の権限を追加しない。現在のユーザー依頼の範囲と既存の承認条件を守る。

## Model and review budget

- Main implementation work uses GPT-6 LUNA at low reasoning.
- Design and code-review subagent calls use GPT-6.1 SOL at medium reasoning by default (two levels below xhigh).
- For a difficult unresolved issue, raise SOL reasoning stepwise only when the current level shows a concrete need; briefly report the reason for escalation.
- Do not rerun completed reviews. Apply this policy to the next SOL call; do not interrupt a long-running call solely to change its model setting.
- In each progress or completion report, state the actual model/reasoning settings used and their scope.
