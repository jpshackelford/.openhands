---
name: self-review
description: Self-review a draft PR before requesting human review
triggers:
  - /self-review
---

# Self-Review

Review your own code before requesting human review. This catches issues early and reduces review cycles.

## Usage

```
/self-review
```

Then provide:
- **pr_number**: The PR number to self-review (e.g., 42)

## When to Use

- Draft PR with passing CI
- Before marking PR ready for review
- After making significant changes during implementation

## Self-Review Principles

Review the code against these quality principles:

### 1. Data Structures First
Poor data structure choices create complexity everywhere. Ask:
- Are the data structures appropriate for the problem?
- Would a different structure simplify the code?
- Are there unnecessary transformations?

### 2. Simplicity and "Good Taste"
- No deep nesting (max 2-3 levels)
- No special cases that could be generalized
- Clear control flow
- Functions do one thing well

### 3. Pragmatism
- Solves the actual problem, not theoretical ones
- No over-engineering for hypothetical future needs
- Appropriate level of abstraction

### 4. Testing
- New behavior has tests
- Tests are meaningful, not just for coverage
- Edge cases are covered

### 5. Skip Style Nits
- Don't bikeshed on formatting (linters handle this)
- Focus on logic and structure

## Self-Review Workflow

### 1. Checkout the PR Branch

```bash
# Clone if needed
gh repo clone jpshackelford/lxa /tmp/lxa-review 2>/dev/null || true
cd /tmp/lxa-review

# Checkout the PR
gh pr checkout {pr_number}

# Ensure CI is passing
gh pr checks {pr_number}
```

### 2. Run Quality Checks

```bash
# Run all checks
make check

# Individual checks if needed
make lint
make typecheck
make test
```

### 3. Review the Diff

```bash
# See what changed
gh pr diff {pr_number}

# Review file by file
gh pr diff {pr_number} --name-only
```

### 4. Evaluate Against Principles

For each changed file, ask:
- [ ] Data structures appropriate?
- [ ] Logic is simple and clear?
- [ ] No over-engineering?
- [ ] Tests cover new behavior?
- [ ] No obvious bugs or edge cases missed?

### 5. Make Fixes

If issues found:

```bash
# Fix the issue
# ... edit files ...

# Verify fix
make check

# Commit with clear message
git add -A
git commit -m "fix: [description of what was fixed]"

# Push
git push
```

### 6. Determine Verdict

After review, determine the verdict:

| Verdict | Meaning | Action |
|---------|---------|--------|
| 🟢 **Good** | Code is clean, ready for review | Mark PR ready |
| 🟡 **Acceptable** | Minor issues, good enough | Mark PR ready (note issues) |
| 🔴 **Needs Work** | Significant issues | Fix before marking ready |

### 7. Mark PR Ready (if passing)

```bash
# Remove draft status
gh pr ready {pr_number}
```

### 8. Post Self-Review Comment

Post a comment documenting the self-review:

```markdown
## Self-Review Complete

**Verdict:** 🟢 Good / 🟡 Acceptable / 🔴 Needs Work

### What I Checked
- [ ] Data structures are appropriate
- [ ] Logic is simple and clear
- [ ] No over-engineering
- [ ] Tests cover new behavior
- [ ] All quality checks pass

### Issues Found & Fixed
- [List any issues you found and fixed]

### Notes for Reviewer
- [Any context that would help the reviewer]

---
*Self-review performed by AI agent (OpenHands)*
```

## Example Self-Review Comment

```markdown
## Self-Review Complete

**Verdict:** 🟢 Good

### What I Checked
- [x] Data structures are appropriate - using dict for O(1) lookups
- [x] Logic is simple and clear - single responsibility functions
- [x] No over-engineering - minimal abstraction for current needs
- [x] Tests cover new behavior - added 3 test cases for edge conditions
- [x] All quality checks pass

### Issues Found & Fixed
- Simplified nested conditionals in `process_item()` (commit abc123)
- Added missing error handling for empty input (commit def456)

### Notes for Reviewer
- The new `--verbose` flag affects output format, see updated README
- Performance tested with 1000 items, completes in <1s

---
*Self-review performed by AI agent (OpenHands)*
```

## Exit Conditions

Exit after:
- Marking PR ready and posting self-review comment
- Determining PR needs significant rework (leave as draft, post findings)
- CI is failing (fix CI first, then self-review)
