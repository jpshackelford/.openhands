---
name: address-review
description: Full review worker procedure for voice-relay — resolve feedback, re-run the AC gate
triggers:
  - /address-review
  - /review-feedback
---

# Address Review

Full procedure for the **review worker**. The orchestrator spawns workers with a short inline prompt; this skill carries the detailed steps including the **Closing-Trailer Acceptance-Criteria Gate** re-run (defined in `SKILL.md`).

## Usage

```
/address-review
```

Then supply (the orchestrator's inline prompt already provides these):
- **number** — the PR number you are addressing
- **title** — for context

## Production Context

The voice-relay app auto-deploys to **vr.chorecraft.net** on every merge to `main`. Production currently uses SQLite. If review feedback involves migration changes, the same backward-compatibility rules apply as in `/implement-issue`.

## Procedure

The procedure below is presented in reading order. Headings are stable names — cross-references in this skill, in sibling worker skills, and in `SKILL.md` target section names rather than step numbers. See `SKILL.md` → "Procedure section naming convention" for the rationale.

1. **Clone and checkout**
2. **Drop PR back to draft**
3. **Read all review threads**
4. **Plan responses**
5. **Group changes into commits**
6. **Commit, push, watch CI**
7. **Resolve review threads**
8. **Reflect**
9. **Re-run AC Gate** (REQUIRED)
10. **Move PR back to ready**
11. **WORKLOG entry**
12. **Exit**

### Clone and checkout

```bash
gh repo clone jpshackelford/voice-relay
cd voice-relay
gh pr checkout {number}
```

### Drop PR back to draft

```bash
gh pr ready {number} --undo --repo jpshackelford/voice-relay
```

This prevents the review bot from re-firing while you're still working.

### Read all review threads

```bash
gh pr view {number} --repo jpshackelford/voice-relay --comments
```

Don't skim. The reviewer's framing matters as much as the literal asks.

### Plan responses

For each thread, decide:

- **Accept and implement** — most suggestions improve quality; the default.
- **Reject with explanation** — only when the suggestion significantly increases scope/complexity without clear benefit. Write the explanation now; you'll post it in **Resolve review threads**.

### Group changes into commits

Don't bundle everything into one commit. The reviewer should be able to read your response commit-by-commit.

### Commit, push, watch CI

1. Make the change.
2. Commit with a clear message that references the thread (e.g. `refactor(server): inline the token-renewal timer per @reviewer's suggestion`).
3. Push.
4. Wait for CI to pass before moving to the next commit. If CI fails, fix it before continuing — don't pile up red commits.

### Resolve review threads

For each thread you addressed:

- Reply explaining what you did (or, for rejects, why).
- Mark the thread as resolved via the GitHub GraphQL API.

```bash
# Example: resolve a thread
gh api graphql -f query='
  mutation { resolveReviewThread(input: {threadId: "THREAD_ID"}) { thread { isResolved } } }
'
```

### Reflect

- Did you learn anything that impacts other open issues (e.g. an architectural smell, a missing test pattern)?
- If so, comment on the relevant issues with the learning. Do NOT block this PR on it.

### Re-run AC Gate (REQUIRED)

**Pre-flight: enumerate existing follow-ups (idempotence).** Before walking the AC checklist, build the **existing follow-up set** for the umbrella issue — these are issues filed by the implementation worker, prior review rounds, or any parallel retroactive gate run. The gate's idempotence rule (see `SKILL.md` → "Idempotence (no duplicate follow-ups)") requires you to reuse them, not duplicate.

```bash
PR_NUMBER=$(gh pr view --json number -q .number)

# (a) Follow-ups already recorded in this PR's body
gh pr view "$PR_NUMBER" --repo jpshackelford/voice-relay --json body -q '.body' \
  | awk '/^## Deferred to follow-ups/{flag=1; next} /^## /{flag=0} flag && /#[0-9]+/' \
  | grep -oE '#[0-9]+' | sort -u > /tmp/existing-in-body.txt

# (b) Follow-ups filed by parallel runs against the same umbrella issue
UMBRELLA=$(gh pr view "$PR_NUMBER" --repo jpshackelford/voice-relay --json body -q '.body' \
  | grep -ioE '(fixes|closes|resolves|refs|part of) #[0-9]+' \
  | head -1 | grep -oE '[0-9]+')
gh issue list --repo jpshackelford/voice-relay --state all \
  --search "in:title \"follow-up to #${UMBRELLA}\"" \
  --json number -q '.[].number' | sed 's/^/#/' | sort -u > /tmp/existing-by-title.txt

# Union = the existing follow-up set
sort -u /tmp/existing-in-body.txt /tmp/existing-by-title.txt > /tmp/existing-followups.txt
```

For each issue in the existing set, read its body so you know which AC item(s) it covers:

```bash
while read -r ref; do
  num=${ref#\#}
  echo "=== $ref ==="
  gh issue view "$num" --repo jpshackelford/voice-relay --json title,body \
    -q '.title + "\n---\n" + (.body | .[0:600])'
done < /tmp/existing-followups.txt
```

You now have the **existing follow-up set**. Use it in the fail-path below: reuse before filing.

Review feedback can change the diff's coverage of the original acceptance criteria. An AC item that was covered may now be uncovered (e.g. the reviewer asked you to drop a piece of scope), or vice-versa (a CI fix incidentally covered a gap). The gate verdict from `/implement-issue` → **AC Gate (pre-ready)** / **AC Gate (re-run after CI)** is no longer authoritative.

**Procedure:**

1. **Find the linked issue** referenced by an auto-close or non-closing trailer:

   ```bash
   gh pr view {number} --repo jpshackelford/voice-relay --json body -q '.body' \
     | grep -ioE '(fixes|closes|resolves|refs|part of) #[0-9]+'
   ```

   If the PR has no issue link at all, skip this step (the gate has nothing to check) but note it in the WORKLOG.

2. **For each linked issue N**, walk N's `## Acceptance Criteria` checklist against the now-current diff:

   ```bash
   gh issue view N --repo jpshackelford/voice-relay --json body -q '.body'
   gh pr diff {number} --repo jpshackelford/voice-relay
   ```

   Apply the gate's standard rules (exempt items, satisfied-by-diff definition — see `SKILL.md`).

3. **Compare to the previous verdict** recorded in the PR body's `## Deferred to follow-ups` section (or absence thereof):

   | Previous verdict | New verdict | Action |
   |---|---|---|
   | `Fixes #N` (all satisfied) | All still satisfied | No change. Note "gate re-verified" in your review-round comment. |
   | `Fixes #N` (all satisfied) | Now some unsatisfied | **Downgrade trailer to `Refs #N`**, file follow-up issues for the new gaps, add a `## Deferred to follow-ups` section. Same procedure as `/implement-issue` → **AC Gate (pre-ready)** fail path. |
   | `Refs #N` + follow-ups | Still has unsatisfied items | Update `## Deferred to follow-ups` if the gap composition changed (some closed, new ones appeared). |
   | `Refs #N` + follow-ups | All now satisfied (CI fix etc. covered the gap) | **Upgrade trailer to `Fixes #N`**, close the now-spurious follow-up issues with explanatory comments. |

4. **Note the re-verdict** in the comment that closes out this review round (when you **Move PR back to ready**). Be explicit: "AC gate re-run: verdict unchanged" or "AC gate re-run: now `Refs #386 + 2 follow-ups #408, #409` (was `Fixes #386`); reviewer asked us to drop the workspace-settings UI from this PR."

### Move PR back to ready

```bash
gh pr ready {number} --repo jpshackelford/voice-relay
```

This triggers the next review round.

### WORKLOG entry

Update `WORKLOG.md` on `main` with:

- PR link + review round number
- Summary of threads addressed
- Gate re-verdict from **Re-run AC Gate** (one of: `unchanged`, `now refs + N follow-ups`, `now closes`)
- Any new follow-up issue numbers, or any spurious follow-ups you closed

⚠️ **WORKLOG.md changes ALWAYS go directly to `main`** — never in feature branches/PRs.

### Exit

The next review round is a separate conversation. Don't wait for it.

## Override

The gate's re-run may be skipped only by an open `## INSTRUCTION:` block in `WORKLOG.md` (on `main` of the target repo) that explicitly names this PR number and the issue number being waived. Record the override in the review-round comment and the WORKLOG entry.

## See also

- **Closing-Trailer Acceptance-Criteria Gate** — the rule itself, defined in the plugin's `SKILL.md`.
- `/implement-issue` — the implementation worker establishes the initial verdict.
- `/prepare-merge` — the merge worker enforces the gate as the final hard check before squashing.
