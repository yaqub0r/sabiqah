# Legacy worktree migration record — 2026-08-13

- **Issue:** [#73](https://github.com/yaqub0r/sabiqah/issues/73)
- **Canonical clone:** `D:\Temp\Sabiqah`
- **Legacy common Git directory:**
  `C:\Users\yaqub\OneDrive\Documents\ChatGPT\Sabiqa\.git`
- **Status:** Blocked by active host-managed worktrees and OneDrive-managed
  deletion permissions. Hydration did not correct the deletion failure. Do not
  retry cleanup from this legacy repository.

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

## Recovery archive

Before retirement, the complete legacy Git state was preserved outside
OneDrive:

- **Bundle:** `D:\Temp\Sabiqah-legacy-archive-20260813.bundle`
- **Size:** 434,765 bytes
- **SHA-256:**
  `83278DCC11A52934C5378807BE93AE3A9DC4602AEBBBADD9686C6700A171EAD1`
- **Verification:** `git bundle verify` passed and reported a complete history
  with 63 refs.

The bundle includes `refs/stash` for paused issue #39, both unique
`codex/v8-alignment` commits, issue #79, every local branch, remote-tracking
refs, and the retained worktree HEADs. It is intentionally local because
blindly publishing unfinished or compliance-sensitive content to the public
repository would expand disclosure.

Verify the archive before any later retirement step:

```powershell
Get-FileHash -Algorithm SHA256 "D:\Temp\Sabiqah-legacy-archive-20260813.bundle"
git bundle verify "D:\Temp\Sabiqah-legacy-archive-20260813.bundle"
```

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

The account owner then hydrated `.git` with **Always keep on this device** and
ran the same Git prune command from a normal PowerShell session. Git still
failed repeatedly while deleting `.git/worktrees/issue-26/logs`. Inspection
showed Microsoft directory reparse tags and inherited deny-delete ACL entries
on both stale and active administrative directories. Hydration is therefore
not a sufficient repair.

## Retirement condition

The legacy common Git directory cannot be retired while host-managed worktrees
depend on it. Issue #79 is also open and its clean branch is currently checked
out in the OneDrive repository. Future work must start from the canonical
`D:\Temp\Sabiqah` project, not the synchronized checkout.

After issue #79 and the retained Codex sessions are closed, verify the bundle
again, confirm no worktree or process depends on the legacy common directory,
and retire the synchronized checkout as one recoverable unit. Do not attempt
individual `.git/worktrees` deletion, ACL edits, or further prune retries. The
unregistered `D:\Temp\sq71-smoke` remnant remains a separately documented
fail-closed artifact until a tested recovery mechanism exists.
