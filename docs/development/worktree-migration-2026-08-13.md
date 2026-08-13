# Legacy worktree migration record — 2026-08-13

- **Issue:** [#73](https://github.com/yaqub0r/sabiqah/issues/73)
- **Canonical clone:** `D:\Temp\Sabiqah`
- **Legacy common Git directory:**
  `C:\Users\yaqub\OneDrive\Documents\ChatGPT\Sabiqa\.git`
- **Status:** Blocked by OneDrive placeholder deletion; do not retry until the
  account owner completes the intervention below.

## Evidence and decisions

The audit fetched `origin/main`, inspected every registered worktree with
`git status --porcelain=v1`, mapped branches to merged pull requests, and used
`git cherry -v origin/main <branch>` where squash merges prevented ancestor
checks. A `-` result established patch equivalence for the historical feature
commits.

Retain these paths:

- `D:\Temp\Sabiqah` is the canonical, non-synchronized clone.
- `C:\Users\yaqub\.codex\worktrees\9f93\Sabiqa` is the host-managed worktree
  for the active conversation. Its `codex/v8-alignment` branch has two unique
  commits and must not be removed.
- `C:\Users\yaqub\.codex\worktrees\7c9b\Sabiqa` is another host-managed
  worktree. Its ownership must be resolved by the host before cleanup.
- The OneDrive checkout temporarily remains the common Git administrative
  anchor for retained host-managed worktrees. It is not the canonical
  development clone and must not receive new work.

These completed historical branches were verified as patch-equivalent to
merged pull requests and selected for cleanup:

| Branch                                | Pull request | Cleanup state                                                                   |
| ------------------------------------- | ------------ | ------------------------------------------------------------------------------- |
| `codex/issue-32-corpus-review`        | #33          | Dependencies removed; Git removal not attempted after the blocker               |
| `codex/issue-40-translation-approval` | #42          | Dependencies removed; Git removal not attempted after the blocker               |
| `codex/issue-41-canonical-archive`    | #45          | Dependencies removed; Git removal not attempted after the blocker               |
| `codex/issue-49-translation-contract` | #50          | Retained; generated cleanup not completed before the stop condition             |
| `codex/issue-55-live-acceptance-copy` | #61          | Dependencies removed; Git removal not attempted after the blocker               |
| `codex/issue-62-r2-ingestion`         | #63          | Dependencies removed; Git removal not attempted after the blocker               |
| `codex/issue-66-excluded-passages`    | #67          | Worktree directory removed by Git; stale OneDrive administrative record remains |
| `codex/issue-66-reader-copy`          | #68          | Dependencies removed; Git removal not attempted after the blocker               |
| detached issue-48 worktree            | #52          | Retained; generated cleanup was interrupted by the batch timeout                |

The apparent tracked changes in the issue-55 and issue-66 worktrees were
line-ending filter noise: `git diff --quiet` proved no logical content change
and there were no untracked files before index-exact restoration. All cleanup
candidates were clean afterward.

The unregistered `D:\Temp\sq71-smoke` disposable directory is retained. Its
Git administrative record and `.git` marker were already removed by Git, so
the repository cleanup command correctly refuses it. Do not treat that
fail-closed result as permission for recursive deletion.

## Stop condition

`git worktree remove` removed the issue-66 worktree directory but returned:

```text
error: failed to delete '.git/worktrees/issue-66': Permission denied
```

A subsequent `git worktree prune --dry-run --verbose` selected six missing
records. Git's own prune then failed to delete every selected directory because
the old common `.git/worktrees` entries contain OneDrive reparse placeholders.
No force removal, manual metadata deletion, ACL change, or alternate deletion
primitive was attempted.

## Required owner intervention

In Windows Explorer, make the legacy repository's `.git` directory available
locally by selecting **Always keep on this device**, and wait for OneDrive to
finish hydration. Do not delete or move anything. Then verify the folder no
longer contains online-only placeholders and resume with Git's verbose prune
dry run. Only after prune succeeds may the remaining reviewed lifecycle steps
resume.

If hydration cannot be completed, retain the legacy common Git directory until
the host-managed worktrees are closed, archive any unique branches, and retire
the entire synchronized checkout through a separately approved migration.
