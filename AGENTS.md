

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
