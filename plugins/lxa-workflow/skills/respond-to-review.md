---
name: respond-to-review
description: Address reviewer feedback on a PR
triggers:
  - /respond-to-review
  - /address-review
---

# Respond to Review

Address reviewer feedback on a PR by making requested changes and responding to comments.

## Usage

```
/respond-to-review
```

Then provide:
- **pr_number**: The PR number with review feedback (e.g., 42)

## When to Use

- PR has unresolved review threads (💬 > 0)
- Reviewer requested changes
- Comments need responses

## Response Principles

### 1. Accept Most Feedback
Most review suggestions improve code quality. Default to accepting unless:
- It significantly increases scope
- It introduces unnecessary complexity
- It conflicts with project conventions

### 2. Prefer Root-Cause Fixes
Don't just patch the symptom. If a reviewer points out an issue, consider:
- Why did this happen?
- Are there similar issues elsewhere?
- What's the underlying fix?

### 3. Group Related Changes
Commit related fixes together with clear messages:
```
Address review: simplify error handling

- Consolidated duplicate try/catch blocks
- Added specific exception types
- Improved error messages
```

### 4. Respond to Every Thread
Even if you disagree, acknowledge the feedback and explain your reasoning.

## Review Response Workflow

### 1. Set PR Back to Draft

```bash
# Checkout the PR
gh pr checkout {pr_number}

# Mark as draft while making changes
gh pr ready {pr_number} --undo
```

### 2. Read All Review Comments

```bash
# View the PR with reviews
gh pr view {pr_number}

# Get detailed review information
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        reviews(last: 10) {
          nodes {
            author { login }
            state
            body
          }
        }
        reviewThreads(first: 50) {
          nodes {
            isResolved
            comments(first: 10) {
              nodes {
                author { login }
                body
                path
                line
              }
            }
          }
        }
      }
    }
  }
' -f owner=jpshackelford -f repo=lxa -f number={pr_number}
```

### 3. Categorize Feedback

Group comments into:
- **Must fix**: Bugs, security issues, incorrect behavior
- **Should fix**: Code quality, maintainability improvements
- **Consider**: Style preferences, alternative approaches
- **Discuss**: Disagreements needing clarification

### 4. Make Changes

For each piece of feedback:

```bash
# Make the change
# ... edit files ...

# Run checks
make check

# Commit with descriptive message referencing the feedback
git add -A
git commit -m "Address review: [description]

- [what you changed]
- [why]"
```

### 5. Push Changes

```bash
git push
```

### 6. Respond to Review Threads

For each thread, post a response:

**If you made a change:**
```markdown
Fixed in commit abc1234.

[Brief explanation of what you did]
```

**If you have questions:**
```markdown
I'm not sure I understand the concern here. Are you suggesting we [interpretation]?

Could you clarify what you'd like to see instead?
```

**If you disagree (respectfully):**
```markdown
I considered this approach, but chose the current implementation because:
- [reason 1]
- [reason 2]

Would you be open to keeping it as-is, or do you feel strongly about the change?
```

### 7. Mark Threads as Resolved

After addressing feedback and getting acknowledgment, resolve the thread (or let the reviewer resolve it).

### 8. Verify CI Passes

```bash
# Check CI status
gh pr checks {pr_number}

# Wait for checks to complete if needed
gh pr checks {pr_number} --watch
```

### 9. Mark PR Ready Again

```bash
gh pr ready {pr_number}
```

### 10. Post Summary Comment

```markdown
## Review Feedback Addressed

Addressed feedback from @reviewer in this round:

### Changes Made
| Feedback | Action | Commit |
|----------|--------|--------|
| Simplify error handling | Refactored try/catch | abc1234 |
| Add input validation | Added null checks | def5678 |
| Update docstring | Fixed parameter docs | ghi9012 |

### Discussion Points
- [Any items still needing clarification]

### CI Status
All checks passing ✅

---
*Review response by AI agent (OpenHands)*
```

## Handling Common Feedback Types

### "Please add tests"
```bash
# Add tests for the specific scenario
# ... write tests ...
make test
git add -A
git commit -m "test: add tests for [scenario]"
```

### "This could be simpler"
Look for:
- Unnecessary abstractions
- Over-complicated conditionals
- Redundant code paths

### "Consider using X instead of Y"
Evaluate the suggestion:
- Is X genuinely better for this use case?
- What are the tradeoffs?
- Does it align with project conventions?

### "What about edge case Z?"
```bash
# Handle the edge case
# Add test for it
make test
git commit -m "fix: handle edge case [Z]"
```

## Exit Conditions

Exit after:
- All review threads addressed
- PR marked ready
- Summary comment posted
- CI passing

Do NOT:
- Continue to merge (let orchestrator handle that)
- Start new features
- Address feedback from reviews that haven't happened yet
