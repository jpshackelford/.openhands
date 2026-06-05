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

### Step 1: Understand the issue

```bash
gh issue view {issue_number} --repo jpshackelford/voice-relay --comments
```

Read the issue description AND every comment. The technical-approach comment (added by the expansion worker) is the canonical implementation plan — it tells you what to build and which files to touch.

**Identify the AC checklist now.** Find the `## Acceptance Criteria` section in the issue body and note every item. These are what the gate at Step 9 will check.

### Step 2: Branch from up-to-date main

```bash
git checkout main
git pull --rebase origin main
git checkout -b feat/{issue_number}-{slug}
```

### Step 3: Implement following the technical approach

Follow the implementation plan from the issue's technical-approach comment. Don't drift — if the approach turns out to be wrong, write that down before deviating (it goes in the PR body's "Review Evolution" section later).

### Step 4: Tests

Target >80% coverage for new code. Real code paths only — no mocks of internal business logic. If you mock, justify it in the test comment.

### Step 5: Database migrations (if applicable)

If you touch the schema:

1. Create migration files (`up` and `down`).
2. Test migrations on a fresh DB AND on a copy of production data.
3. Confirm rollback works.
4. Note any post-deploy manual steps in the PR body.

The highest migration on `main` is the next-numbered slot; pick `NNN_<descriptor>.ts` and keep numbering contiguous.

### Step 6: Lints, type checks, commit, push, draft PR

```bash
# Run repo's lint + typecheck commands (see voice-relay package.json scripts)
npm run lint && npm run typecheck

git add -A
git commit -m "feat({scope}): ..."   # conventional commit
git push -u origin feat/{issue_number}-{slug}
gh pr create --draft --repo jpshackelford/voice-relay --title "..." --body "..."
```

### Step 7: Monitor CI until green

Watch the PR checks. Fix failures with focused follow-up commits.

### Step 8: Final diff review (pre-gate)

Re-read your own diff end-to-end before running the gate. You want to know exactly what's in it.

```bash
gh pr diff $(gh pr view --json number -q .number) --repo jpshackelford/voice-relay
```

### Step 9: Closing-Trailer Acceptance-Criteria Gate (REQUIRED before ready-for-review)

Run the gate now — this is the **first** of two checkpoints (the second is Step 11).

For issue {issue_number}, walk the `## Acceptance Criteria` checklist item-by-item against the final diff from Step 8:

| Item type | Action |
|---|---|
| Explicitly marked `(deferred)` / `(out of scope)` / `(follow-up)` in the issue body | EXEMPT — skip |
| Has a concrete change in the diff that delivers the behavior | SATISFIED |
| Does not have a concrete change in the diff | UNSATISFIED |

**Verdict — all non-exempt items SATISFIED:**

- Add `Fixes #{issue_number}` to the PR body.
- Proceed to Step 10.

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

### Step 10: CI re-green if you edited the PR body or added commits

If you pushed any additional commits while writing follow-up issues, wait for CI to re-green.

### Step 11: REFLECT — re-run the AC Gate against the final diff

Sometimes scope shifts late: a CI fix had side effects, a follow-up commit dropped a piece you thought was covered, etc. Re-walk Step 9 against the now-final diff.

- If the verdict is **unchanged** → record it in the PR body's status and proceed.
- If the verdict **changed**:
  - SATISFIED → now UNSATISFIED: downgrade the trailer, file the missing follow-ups, append to `## Deferred to follow-ups`. (Same as Step 9 fail path.)
  - UNSATISFIED → now SATISFIED (e.g. a CI fix happened to cover the gap): you MAY upgrade the trailer to `Fixes #{issue_number}` and close the now-spurious follow-up issues with an explanatory comment.

Also note any non-gate learnings in this step (architecture pitfalls, surprising test failures, etc.).

### Step 12: Move PR to ready

```bash
gh pr ready $(gh pr view --json number -q .number) --repo jpshackelford/voice-relay
```

This triggers the review bot.

### Step 13: WORKLOG entry on main

Update `WORKLOG.md` on `main` with:

- PR link
- The AC-gate verdict (one of: `closes #{issue_number}` / `refs #{issue_number} + N follow-ups #X, #Y, ...`)
- Any follow-up issue numbers filed in Step 9 / Step 11
- Anything notable from Step 11's reflection

⚠️ **WORKLOG.md changes ALWAYS go directly to `main`** — never in feature branches/PRs. See `orchestrate.md` for the rationale.

### Step 14: Exit

Review handling is a separate conversation. Do not loiter waiting for review feedback.

## Override

The gate may be overridden only by an open `## INSTRUCTION:` block in `WORKLOG.md` (on `main` of the target repo) that explicitly names this PR's eventual number, issue #{issue_number}, and the AC items being waived. If you spot such a block in the worklog, record the override in the PR body's gate-verdict line and the WORKLOG entry.

## See also

- **Closing-Trailer Acceptance-Criteria Gate** — the rule itself, defined in the plugin's `SKILL.md`.
- `/prepare-merge` — the merge worker re-runs the gate as the final hard check.
- `/address-review` — the review worker re-runs the gate after each round.
