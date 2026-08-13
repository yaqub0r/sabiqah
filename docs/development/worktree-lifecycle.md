# Worktree lifecycle

This runbook defines how contributors and agents isolate, validate, and clean up
repository work without leaving Git metadata or dependency trees in an unsafe
state. It applies to local development; CI jobs use disposable checkouts.

## Ownership model

A Codex-managed worktree is the unit of work for one active issue. Its branch,
working tree, pull request, and cleanup state belong to that task.

- Work directly in the worktree supplied by Codex.
- For parallel work, start a separate Codex worktree or thread.
- Do not run `git worktree add` beneath any existing checkout. Ignored paths such
  as `.runtime` and `tmp` are runtime storage, not worktree containers.
- The current Codex worktree is host-managed. Do not remove it from within its
  active session.

The canonical Windows clone must use a short local path outside synchronized
folders. The reference path for the current workstation is
`D:\Temp\Sabiqah`. Other workstations and non-Windows environments may use a
different short local path. Do not put the common `.git` directory in OneDrive,
Dropbox, or another filesystem-sync location.

## Dependency layout

This repository sets pnpm's project-local virtual store to `.pnpm`. Keeping the
virtual store one directory higher than `node_modules/.pnpm` reduces Windows
path length while preserving pnpm's isolated dependency model. Both `.pnpm` and
`node_modules` are generated and ignored.

Run dependency installation from the root of the active worktree:

```powershell
pnpm install --frozen-lockfile
```

Do not share one virtual store between separate projects or worktrees.

### Remove generated dependencies

Git for Windows may fail to remove pnpm's junction-heavy dependency tree even
when paths are short. Before removing a completed, non-current worktree, run the
repository-owned cleanup command from that worktree:

```powershell
pnpm cleanup:generated
pnpm cleanup:generated -- --apply
```

The first command is a dry run. Review every listed path before using the apply
mode. The command accepts no target path: it verifies the Sabiqah repository
root and removes only `.pnpm`, root `node_modules`, and `node_modules`
directories directly beneath workspace packages. It rejects symbolic-link
cleanup roots and verifies that every target parent remains within the
repository. Links inside those generated directories are unlinked without
removing their external targets.

## Start work

1. Confirm the GitHub issue exists and accurately scopes the change.
2. Confirm the current worktree and branch are dedicated to that issue.
3. Inspect `git status --short --branch` and preserve unrelated work.
4. Fetch current remote state before basing the branch on `origin/main`.
5. Install dependencies only in the active worktree.

If the current worktree already contains another task's changes, do not create a
nested worktree to work around it. Finish that task or start another
Codex-managed worktree.

## Preflight cleanup

Cleanup begins only after the task's pull request is merged or explicitly
abandoned and all work worth retaining is committed or otherwise preserved.
Perform read-only checks first:

```powershell
git fetch --prune origin
git worktree list --porcelain
git -C <exact-worktree-path> status --porcelain=v1
git branch --show-current
```

Verify all of the following:

- the exact cleanup target is a registered worktree;
- it is not the current Codex worktree;
- its working tree is clean;
- its pull request has reached a terminal state;
- merged work is present on `origin/main`;
- any retained local-only work has an explicit owner and location; and
- the target path is neither a filesystem root nor a reparse-point root.

A squash merge may not make the feature commit an ancestor of `main`. In that
case, use the merged pull request and a patch comparison such as `git cherry`
or an equivalent diff as evidence; do not infer that an unmerged-looking commit
is disposable.

## Remove a completed worktree

From the completed worktree, remove generated dependencies first:

```powershell
pnpm cleanup:generated
pnpm cleanup:generated -- --apply
```

If either command fails or lists an unexpected path, stop. Do not continue to
worktree removal.

From the canonical clone, use Git's own lifecycle commands:

```powershell
git worktree remove -- <exact-worktree-path>
git worktree prune
```

Delete the corresponding local branch only after removal succeeds and the merge
evidence is still valid. If a squash merge requires forced branch deletion,
record why patch equivalence proves the branch redundant before using
`git branch -D`.

Do not manually delete `.git/worktrees` entries. Git owns that metadata.

## Failure handling

A nonzero generated-cleanup or Git-cleanup exit is a stop condition, not
permission to use a stronger deletion command.

1. Preserve the command and exact error.
2. Re-run only read-only checks for worktree registration, status, ownership,
   locks, reparse points, and maximum path length.
3. Identify whether the failure belongs to Git metadata, a running process, a
   synchronized filesystem, or generated dependencies.
4. Correct the underlying workflow in a separately scoped issue.
5. Retry only through Git after the cause is corrected.

Never respond to a failed worktree removal with `Remove-Item -Recurse`, `rm -rf`,
manual junction traversal, ACL modification, direct deletion of the common Git
directory, or an improvised substitute for `pnpm cleanup:generated`. Those
approaches can cross link boundaries, discard untracked work, or leave Git's
registry inconsistent.

## Legacy worktrees

Worktrees created before this policy are migration debt. Inventory and reconcile
them in a dedicated cleanup issue. Do not mix their deletion into feature work,
and do not treat an ignored directory as proof that its contents are disposable.
