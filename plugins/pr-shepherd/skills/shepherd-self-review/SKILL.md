---
name: shepherd-self-review
description: Self-review a draft PR before marking it ready for human review. Reviews code against quality principles, fixes issues, and marks PR ready when quality bar is met. Use when /shepherd reports a draft PR with green CI.
triggers:
- /shepherd-self-review
---

# Shepherd Self-Review

Self-review a draft PR before requesting human review.

## When to Use

- `/shepherd` reports draft PR with green CI
- "Self-review PR #123"
- "Prepare this PR for review"
- "Check my own code before requesting review"

## Usage

```bash
/shepherd-self-review owner/repo#123
/shepherd-self-review https://github.com/owner/repo/pull/123

# Via lxa
lxa refine <URL> --phase self-review
```

## Workflow

### Step 1: Verify Prerequisites

```bash
# Check PR is draft and CI is passing
gh pr view <number> --json isDraft,statusCheckRollup

# Verify working tree is clean
git status
```

Prerequisites:
- [ ] PR is in draft state
- [ ] CI is passing (or no CI configured)
- [ ] Working tree is clean

### Step 2: Get the Diff

```bash
# View the full diff
gh pr diff <number>

# Or for specific files
gh pr diff <number> -- src/
```

### Step 3: Apply Quality Principles

Review the code against these criteria:

#### 1. Data Structures First

> "Bad programmers worry about the code. Good programmers worry about data structures."

- Are data structure choices appropriate?
- Is there unnecessary data copying/transformation?
- Is data ownership and flow clear?

#### 2. Simplicity and "Good Taste"

> "If you need more than 3 levels of indentation, you're screwed."

- Any functions with > 3 levels of nesting?
- Special cases that could be eliminated with better design?
- Code that could be 3 lines instead of 10?

#### 3. Pragmatism

> "Theory and practice sometimes clash. Theory loses."

- Is this solving a real problem?
- Is the solution complexity proportional to problem severity?
- Any over-engineering for theoretical edge cases?

#### 4. Testing

- Does new behavior have tests?
- Do tests actually test the behavior (not just mock assertions)?
- Would tests fail if the behavior regressed?

#### 5. Error Handling

- Are error cases handled appropriately?
- Are errors surfaced clearly, not swallowed?

### Step 4: Fix Issues Found

For each issue:

1. Make the fix
2. Commit with descriptive message:
   ```bash
   git commit -m "refactor: simplify nested conditionals in handler
   
   Self-review: reduced nesting from 4 to 2 levels"
   ```

3. Continue reviewing

### Step 5: Push and Verify CI

```bash
git push
gh pr checks <number> --watch
```

### Step 6: Determine Verdict

| Verdict | Meaning | Action |
|---------|---------|--------|
| 🟢 **Good taste** | Clean, elegant solution | Mark ready |
| 🟡 **Acceptable** | Works correctly, minor improvements possible | Mark ready |
| 🔴 **Needs rework** | Fundamental issues remain | Continue fixing |

### Step 7: Mark Ready (if 🟢 or 🟡)

```bash
gh pr ready <number>
```

Optionally add a comment:
```bash
gh pr comment <number> --body "Self-review complete. Ready for human review.

Focus areas:
- The new caching logic in src/cache.py
- Error handling in the API layer"
```

## Quality Checklist

Use this checklist during review:

```markdown
## Self-Review Checklist

### Code Quality
- [ ] No functions with > 3 levels of nesting
- [ ] No obvious code duplication
- [ ] Clear variable and function names
- [ ] Appropriate data structures

### Correctness
- [ ] Edge cases handled
- [ ] Error cases handled appropriately
- [ ] No obvious bugs

### Testing
- [ ] New behavior has tests
- [ ] Tests verify actual behavior (not just mocks)
- [ ] Tests would fail if behavior regressed

### Documentation
- [ ] Public APIs documented
- [ ] Complex logic has comments explaining "why"
- [ ] README updated if needed
```

## Output Format

```
Self-Review for owner/repo#123
==============================

Reviewing diff (15 files changed, +342 -128)...

Issues Found:
  1. src/handler.py:45 - 4 levels of nesting
     Action: Refactored to early returns
     Commit: abc1234

  2. src/utils.py:80 - Duplicate code with src/helpers.py
     Action: Extracted to shared function
     Commit: def5678

  3. tests/test_handler.py - Tests only assert mock calls
     Action: Added integration test with real objects
     Commit: ghi9012

Pushed 3 commits.
CI status: ✓ Passing

Verdict: 🟢 Good taste

Marking PR ready for review...
✓ PR #123 is now ready for review
```

## Alternative: lxa refine

For automated self-review with quality principles built in:

```bash
lxa refine <URL> --phase self-review
```

This handles the full loop including CI waits and verdict determination.

## Related Skills

- `/shepherd` - Get initial status
- `/shepherd-advance` - Auto-determine action
- `/shepherd-codes` - Understand history codes
