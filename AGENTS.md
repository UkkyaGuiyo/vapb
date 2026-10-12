

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


## HOLMES-WATSON LOOP (2026-10-12)

User-authorized bounded workflow; existing model split, Failure Atlas, safety and GitHub save contract remain in force. The configured inference agent is separate from independent code review. Its explicit user-requested SOL/xhigh setting applies only to Holmes inference; existing SOL/medium code-review policy is unchanged.

A. WATSON performs the smallest authorized implementation, experiment and verification.
B. EVIDENCE records results, failures, counterexamples and unverified points in the existing evidence hierarchy; normally commit/push allowed files and verify exact remote readback before requesting Holmes.
C. HOLMES performs independent inference only in a fresh context. Prefer project `.codex/agents/holmes.toml`; if custom-agent selection is unavailable, pass the same role instructions and fixed evidence to a fresh native subagent. Pass fixed commit/files and product objective, avoiding Watson's reasoning or previous conclusions. Verify actual spawn/completion and report effective permissions accurately. Inherited workspace-write/auto_review is allowed and is not itself BLOCKED; role rules prohibit file edits, commit, push, product implementation and recursive spawning. Do not claim technical write prevention from role instructions or replace Holmes with Watson self-review.
D. REVIEW: Watson independently checks the returned evidence and proposal. Necessary independent code review remains a separate gate. A proposal does not grant approval.
E. NEXT: proceed with one clear action only if already authorized and grounded. Stop on insufficient evidence or conflicting authority. This configuration/dry run grants no new product scope.

User-authorized VAPB AUTONOMOUS CONTINUOUS MODE (2026-10-11 23:21:42 UTC) supersedes the three-cycle cap and per-cycle restart waiting. Continue existing PRODUCT_SPEC/approved work without a fixed cycle limit; ordinary completion, PASS/KEEP, save, inference or reporting does not end development. Watson action -> saved evidence/exact remote readback -> fresh Holmes -> verified next minimum -> Watson action. A blocked item or repeated failing method requires reassessment or another independent approved task, not automatic whole-project stop. Stop only for original/third-party data danger, unauthorized escalation/authentication bypass, indispensable Product Owner specification decision, unavailable hardware/resources or safe GitHub persistence, actual account/budget limits, secret/purchased-data exposure, all approved candidates BLOCKED, or explicit user stop. If no real action remains after checking candidates, save NO_NEW_ACTION with reasons; do not invent work. Preserve evidence and restart point. Actual account remaining <=5% retains existing safe save/handoff/stop conditions; do not confuse this with context remaining.

Keep original Package/FBX/Prefab/GUID/fileID/Material/Scene and existing evidence intact. Never publish purchased material, secrets or private logs. Parent owns next instruction/state persistence; Watson owns allowed work-branch source/evidence; Holmes reads only. Do not merge the instruction branch into the product branch. Check `docs/holmes-watson-handoff:HOLMES_TO_WATSON.md` and current chat authority: newer CHAT_FALLBACK supersedes stale GitHub READY, and completed/ongoing IDs are not rerun. Updating the fixed instruction file requires latest blob-SHA conflict detection and exact readback.

After session end, reread actual AGENTS/spec, Git state and latest saved restart record; verify authority and completed instruction IDs before spawning. No background or scheduled loop is established. The user correction (2026-10-11 19:01:05 UTC) removes mandatory read-only sandbox and custom-role loading as startup gates. Parent live permissions may be inherited without changing them; enforce the inference-only role, accurately distinguish requested/configured/effective settings, and never escalate permissions, test dangerous writes or bypass permissions.

Context soft landing: near5% context headroom, avoid large new work, finish a safe atomic step and save result/WIP/next action with exact remote verification. Use the platform's real continuation/compaction mechanism without duplicate owners. Automatic in-turn compaction is available; cross-session autonomous restart is NOT_CONFIGURED unless a real approved mechanism is verified. Do not create a daemon, scheduler or permissions workaround. Context headroom is not account usage and is not a permanent development stop. Existing model split, original protection, proposal/code-review separation and GitHub save contract remain.


### Action selection immediately after compaction or resume

Before acting or replying after compaction/resume, reconcile the existing project restart point with the latest explicit user instructions: current project/goal, latest approval or stop, ongoing/completed instruction ID, fixed save point and recorded NEXT_ACTION. Use actual current Git state where relevant. Historical delegations, quoted requests, handoffs and older unprocessed messages are context; their visibility or position alone does not renew authorization or make them the current task.

An expired or superseded request from another project must not trigger a reply, renewed delegation, product action or completion/stop of this project. A newer explicit user instruction may reopen or redirect that work and takes precedence; this is not a permanent prohibition based on request wording. When authority conflicts remain material, preserve the safe checkpoint and clarify only the dependent action while continuing independent approved work.

Resume the saved authorized NEXT_ACTION, receive an already-running inference/review instead of duplicating it, and keep ordinary reporting separate from whole-project completion. If current evidence/instructions supersede the restart point, minimally correct that existing record before proceeding; retain historical originals. Do not create a monitor or extra ledger. A document/scenario review is not an actual compaction runtime test; do not claim prevention, zero recurrence or runtime verification without observing it.
