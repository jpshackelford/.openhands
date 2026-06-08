---
name: implement-issue
description: Full implementation worker procedure for voice-relay — branch, code, tests, PR, AC gate
triggers:
  - /implement-issue
  - /implement
---

# Implement Issue

Full procedure for the **implementation worker**. The orchestrator spawns workers with a short inline prompt; this skill carries the detailed steps including the **Closing-Trailer Acceptance-Criteria Gate** (defined in `SKILL.md`).

## Usage

```
/implement-issue
```

Then supply (the orchestrator's inline prompt already provides these):
- **issue_number** — the GitHub issue you are implementing
- **issue_title** — for branch / commit naming
- **priority_label** — for context only

## Production Context

The voice-relay app auto-deploys to **vr.chorecraft.net** on every merge to `main`. Production currently uses SQLite (`sqlite.db`). All schema changes MUST include migrations. Migrations MUST be backward-compatible with existing production data. Additive changes (new tables, new columns with defaults) are safe; destructive changes need careful planning.

## Procedure

The procedure below is presented in reading order. **Headings are stable names, not step numbers** — cross-references in this skill and in sibling worker skills (`/address-review`, `/prepare-merge`) target section names so insertions and reorderings don't require coordinated edits across files. The numbered roadmap here exists only as a reading aid:

1. **Understand the issue**
2. **Pre-flight: is this issue already done?**
3. **Branch from up-to-date main**
4. **Implement**
5. **Tests**
6. **Database migrations** (if applicable)
7. **Lint, commit, push, draft PR**
8. **Monitor CI**
9. **Final diff review**
10. **AC Gate (pre-ready)**
11. **CI re-green**
12. **AC Gate (re-run after CI)**
13. **Move PR to ready**
14. **WORKLOG entry**
15. **Exit**

### Understand the issue

```bash
gh issue view {issue_number} --repo jpshackelford/voice-relay --comments
```

Read the issue description AND every comment. The technical-approach comment (added by the expansion worker) is the canonical implementation plan — it tells you what to build and which files to touch.

**Identify the AC checklist now.** Find the `## Acceptance Criteria` section in the issue body and note every item. These are what the **AC Gate (pre-ready)** below will check.

### Pre-flight: is this issue already done?

Before branching, walk the AC checklist from **Understand the issue** against the current `main`. The expansion → ready → implementation pipeline is asynchronous; by the time you're dispatched, another worker (or a prior tick on a sibling PR) may have already shipped the code. See `SKILL.md` → "No prose-form `on-hold` on already-shipped work" for the cross-cutting rule.

```bash
# Pull latest main + read the shipping commit history for this scope
git -C voice-relay fetch origin main
git -C voice-relay log --oneline -20 origin/main -- {hint_paths_from_technical_approach}

# Also enumerate any PRs that already reference this issue (open or merged)
gh pr list --repo jpshackelford/voice-relay --state all \
  --search "in:body OR in:title '#{issue_number}'" \
  --json number,state,mergeCommit,title,body,closingIssuesReferences
```

Walk each non-exempt AC item against the code on `main`:

| Finding | Exit action |
|---|---|
| **Every** non-exempt AC is already satisfied by code merged to `main` | **Close the issue directly** (see "Already-done exit" below). Do not branch. Do not open a PR. Do not apply `on-hold`. |
| **Some** ACs satisfied, others still need work | Proceed to **Branch from up-to-date main** with the still-open ACs as your scope. In the PR you eventually open, carve the satisfied items out via the normal **AC Gate (pre-ready)** follow-up procedure or note them as "already shipped via #PR" in the body's gate-verdict line. |
| **No** ACs satisfied yet | Proceed to **Branch from up-to-date main** normally. |

#### Already-done exit (no PR opened)

When all non-exempt ACs are already on `main`:

1. **Close the issue** with `--reason completed`.
2. **Post a comment first** listing each AC and the PR/commit (or chain of PRs) that satisfied it, with permalinks. Use the template below.
3. **Do NOT** apply `on-hold`. Prose-form `on-hold` is invisible to the orchestrator's Unblock Pass (see `orchestrate.md`) and will strand the issue in policy-tracked limbo — the failure mode that produced [voice-relay #446](https://github.com/jpshackelford/voice-relay/issues/446) (the 17:25Z worker recognized the work was already shipped via PR #450 + chain #452 → #449, but applied a prose `on-hold` instead of closing, so subsequent unblock passes correctly left it alone and the issue sat open for hours until a human caught it).
4. **Do NOT** open a duplicate PR — see voice-relay PR #451, which raced PR #450 and had to be closed.
5. Write a WORKLOG entry on `main` recording the no-op outcome and the close link. Exit (skip the rest of the procedure).

Closing-comment template:

```markdown
## ✅ Closing — all ACs shipped

All acceptance criteria from this issue are landed on `main`:

- **AC #1** — shipped via #<PR> (`<sha>`, <date>). <one-line evidence>
- **AC #2** — shipped via #<PR> (`<sha>`, <date>). <one-line evidence>
- …

<one-paragraph context for why a worker was still dispatched, if non-obvious — e.g., racy ready labeling, prior prose-form hold being lifted, etc.>

_This comment was created by an AI agent (OpenHands) on behalf of @jpshackelford._
```

#### When ACs are *partially* already shipped

If the diff for the remaining scope ends up satisfying **all** the still-open ACs, the **AC Gate (pre-ready)** below will produce a `Fixes #N` trailer normally. If the diff still leaves some ACs uncovered, follow the normal **AC Gate (pre-ready)** follow-up procedure. Never use prose-form `on-hold` — if you need to defer remaining ACs to follow-up issues, the convention from `expand-issue.md` ("Issue is hard-blocked") applies: add a machine-form `Blocked by #<follow-up>` comment on the issue so the next Unblock Pass can lift the hold automatically when the follow-up closes.

### Branch from up-to-date main

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/{issue_number}-{slug}
```

### Implement

Follow the implementation plan from the issue's technical-approach comment. Don't drift — if the approach turns out to be wrong, write that down before deviating (it goes in the PR body's "Review Evolution" section later).

### Tests

Target >80% coverage for new code. Real code paths only — no mocks of internal business logic. If you mock, justify it in the test comment.

### Database migrations

If you touch the schema:

1. Create migration files (`up` and `down`).
2. Test migrations on a fresh DB AND on a copy of production data.
3. Confirm rollback works.
4. Note any post-deploy manual steps in the PR body.

The highest migration on `main` is the next-numbered slot; pick `NNN_<descriptor>.ts` and keep numbering contiguous.

### Lint, commit, push, draft PR

```bash
# Run repo's lint + typecheck commands (see voice-relay package.json scripts)
npm run lint && npm run typecheck

git add -A
git commit -m "feat({scope}): ..."   # conventional commit
git push -u origin feat/{issue_number}-{slug}
gh pr create --draft --repo jpshackelford/voice-relay --title "..." --body "..."
```

### Monitor CI

Watch the PR checks. Fix failures with focused follow-up commits.

### Final diff review

Re-read your own diff end-to-end before running the gate. You want to know exactly what's in it.

```bash
gh pr diff $(gh pr view --json number -q .number) --repo jpshackelford/voice-relay
```

### AC Gate (pre-ready)

Run the gate now — this is the **first** of two checkpoints (the second is **AC Gate (re-run after CI)** below).

For issue {issue_number}, walk the `## Acceptance Criteria` checklist item-by-item against the final diff from **Final diff review**:

| Item type | Action |
|---|---|
| Explicitly marked `(deferred)` / `(out of scope)` / `(follow-up)` in the issue body | EXEMPT — skip |
| Has a concrete change in the diff that delivers the behavior | SATISFIED |
| Does not have a concrete change in the diff | UNSATISFIED |

**Verdict — all non-exempt items SATISFIED:**

- Add `Fixes #{issue_number}` to the PR body.
- Proceed to **CI re-green**.

**Verdict — any non-exempt item UNSATISFIED:**

1. **Do NOT** write `Fixes` / `Closes` / `Resolves`. Use `Refs #{issue_number}` (or `Part of #{issue_number}`).
2. **File a follow-up issue for each unsatisfied item** (or coherent group of items). Each follow-up MUST:
   - Open with one line stating which AC item from #{issue_number} it covers.
   - Reference back: `Refs #{issue_number}` (no auto-close trailer).
   - Carry forward the relevant slice of the technical-approach comment so the next expansion worker doesn't re-derive it.
   - Inherit the same priority label and `scope:*` label as #{issue_number} unless the gap is obviously different in scope.
3. Add a `## Deferred to follow-ups` section to the PR body listing the new issue numbers + a one-line summary of each.
4. Post a comment on issue #{issue_number} listing the deferred items and linking each follow-up.

**A worker comment that promises to "file follow-ups once this lands" is NOT a substitute for this step.** The follow-up issues must exist as GitHub issues before the PR moves to ready-for-review. This is the failure mode that produced [voice-relay #386](https://github.com/jpshackelford/voice-relay/issues/386).

```bash
# Update the PR body once the verdict is decided
gh pr edit $(gh pr view --json number -q .number) \
  --repo jpshackelford/voice-relay \
  --body "$(cat new_body.md)"
```

### CI re-green

If you pushed any additional commits while writing follow-up issues, wait for CI to re-green.

### AC Gate (re-run after CI)

Sometimes scope shifts late: a CI fix had side effects, a follow-up commit dropped a piece you thought was covered, etc. Re-walk the **AC Gate (pre-ready)** procedure against the now-final diff.

- If the verdict is **unchanged** → record it in the PR body's status and proceed.
- If the verdict **changed**:
  - SATISFIED → now UNSATISFIED: downgrade the trailer, file the missing follow-ups, append to `## Deferred to follow-ups`. (Same as the **AC Gate (pre-ready)** fail path.)
  - UNSATISFIED → now SATISFIED (e.g. a CI fix happened to cover the gap): you MAY upgrade the trailer to `Fixes #{issue_number}` and close the now-spurious follow-up issues with an explanatory comment.

Also note any non-gate learnings in this step (architecture pitfalls, surprising test failures, etc.).

### Move PR to ready

```bash
gh pr ready $(gh pr view --json number -q .number) --repo jpshackelford/voice-relay
```

This triggers the review bot.

### WORKLOG entry

Update `WORKLOG.md` on `main` with:

- PR link
- The AC-gate verdict (one of: `closes #{issue_number}` / `refs #{issue_number} + N follow-ups #X, #Y, ...`)
- Any follow-up issue numbers filed during either AC-gate run
- Anything notable from the **AC Gate (re-run after CI)** reflection

⚠️ **WORKLOG.md changes ALWAYS go directly to `main`** — never in feature branches/PRs. See `orchestrate.md` for the rationale.

### Exit

Review handling is a separate conversation. Do not loiter waiting for review feedback.

## Override

The gate may be overridden only by an open `## INSTRUCTION:` block in `WORKLOG.md` (on `main` of the target repo) that explicitly names this PR's eventual number, issue #{issue_number}, and the AC items being waived. If you spot such a block in the worklog, record the override in the PR body's gate-verdict line and the WORKLOG entry.

## See also

- **Closing-Trailer Acceptance-Criteria Gate** — the rule itself, defined in the plugin's `SKILL.md`.
- `/prepare-merge` — the merge worker re-runs the gate as the final hard check.
- `/address-review` — the review worker re-runs the gate after each round.
