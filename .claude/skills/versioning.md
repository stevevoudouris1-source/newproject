---
name: versioning
description: Keep git invisible for non-technical users. Use for any save / back up / undo / "go back" / version / history request, and to follow the auto-save + main-only + plain-English rules. Triggers on "save my work", "back it up", "undo that", "go back to yesterday", "what changed", "restore", "save a version".
---

# Skill: version control, kept invisible

Turn 5 users are **not** developers. They must never need to understand git,
branches, worktrees, remotes, commits, or "push/pull." **You operate git on
their behalf; they speak plain English.** The mental model to reinforce: *their
app has a time machine — every change is saved and backed up, and they can go
back to any earlier version just by asking.*

## The rules

1. **Auto-save + auto-backup.** After you finish a change, **save and back it up
   automatically** — never ask permission to save. Run `bin/ci` first for a
   substantial change; a **minor tweak** (copy, styling, docs, small config) needs
   no test run. Then confirm in plain English: *"Saved your changes and backed
   them up."* (With lefthook installed, the backup push happens automatically on
   every save.) Saving is not something they should have to request.
2. **Main only, by default.** Work directly on the live app. Do **not** create
   branches, worktrees, or pull requests **unless the user explicitly asks** for
   them (e.g. they want a teammate to review, or to try two ideas in parallel).
   For one person on one app, branches/PRs only create "where did my change go?"
   confusion. Multiple people collaborating is a deliberate graduation — explain
   it and get a clear yes first.
3. **Speak plain English — never jargon.** Don't say commit, push, pull, branch,
   merge, rebase, remote, HEAD, etc. unless the user says the word first. Use the
   vocabulary table below.
4. **Undo is always forward-only.** Never use `git reset --hard`, force-push, or
   anything that rewrites/destroys history (they're also blocked in
   `.claude/settings.json`). To undo, make a **new** save that reverses the
   change. History is preserved, so nothing is ever truly lost.
5. **Handle conflicts silently.** If syncing produces a conflict, resolve it
   yourself. Only involve the user when there's a genuine "which version did you
   want?" choice — and ask it in plain terms, never showing conflict markers.
6. **Reassure proactively.** Periodically confirm their work is safe: *"Everything
   is saved and backed up — you're at 'Added customer search'."*

## Vocabulary — what they say → what you do

| They say (or it's automatic) | What you do | Never say to them |
|---|---|---|
| "save my work" / (automatic after a change) | `bin/save "<summary>"` (stage + commit + push) | "commit / push" |
| "back it up" / "is it saved?" | ensure it's pushed; confirm it's backed up | "remote / push" |
| "get the latest" / "sync" | `git pull` (resolve conflicts silently) | "pull / merge" |
| "undo that" | `git revert --no-edit HEAD` then push (a new, reversing save) | "revert / reset" |
| "go back to yesterday / before X" | restore files from that earlier point, then save it | "checkout / HEAD" |
| "save this as a version called X" | a clearly-named save (+ a tag if useful) | "tag / commit message" |
| "what changed?" / "what did you do?" | summarize the history/diff in plain English | "diff / log" |
| "start over from the last good version" | restore from the last green save, forward-only | "reset" |

## The mechanics (for you, not them)

- **Save + back up:** `bin/save "<plain summary>"` runs `git add -A` →
  `git commit` → `git push`. Run `bin/ci` first for substantial changes; minor
  tweaks can skip it.
- **Undo the last change:** `git revert --no-edit HEAD` then `git push`. Creates a
  new save that cleanly reverses the last one — fully recoverable, history intact.
- **Go back to an earlier version (history preserved):** find the target save
  (`git log --oneline`, for your eyes only), then
  `git restore --source=<commit> -- .`, review, `git commit -m "Restore version
  from <when>"`, push. This moves *forward* to a state matching the old one;
  nothing is discarded.
- **Name a version:** `git tag -a v-<slug> -m "<why>"` (optional) alongside a
  clearly-worded save.
- **What changed:** `git log --oneline -n N` / `git diff <a> <b>` → translate to
  plain English ("Yesterday I added the search box; today I fixed the date
  format").
- **Never:** `reset --hard`, `push --force`/`-f`, `rebase`, or branches/worktrees
  for solo work (all either blocked in settings or off-limits by default).

## When they want collaboration (the opt-out)

Only if the user explicitly asks for review/teamwork: explain in plain terms that
you'll start using "drafts" (branches) and "review requests" (pull requests), and
that turning on branch protection is worthwhile. Walk them through it. Until they
ask, stay main-only.
