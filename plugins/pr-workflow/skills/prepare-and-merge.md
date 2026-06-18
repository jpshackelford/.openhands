---
name: prepare-and-merge
description: Final merge preparation and execution
triggers:
  - /prepare-merge
  - /merge
---

# Prepare and Merge

Final merge preparation and execution. Used when PR has met merge criteria:
- CI is green
- Manual test results posted to PR
- Good/acceptable review rating (or 3x acceptable across rounds), including a `## Self-Review` comment when `Self-review: enabled`

## Usage

```
/prepare-merge
```

or

```
/merge
```

## Prerequisites

Before using this skill, verify merge criteria is met:
- **CI green**
- **Manual test results** posted as PR comment
- **Review rating**: Good taste, acceptable, or 3x acceptable. When `Self-review: enabled`, a `## Self-Review` PR comment with `Good` or `Acceptable` can satisfy this gate.

## Steps

### 1. Study the PR Holistically

Don't just look at the latest changes - understand the full picture:

```bash
# View the complete diff against main
gh pr diff PR_NUMBER --repo {REPOSITORY}

# Read the PR description and all comments
gh pr view PR_NUMBER --repo {REPOSITORY} --comments
```

Think about:
- What is this PR actually accomplishing?
- How did it evolve through review?
- Are there any loose ends?

### 2. Review the Manual Test Results

Find and read the manual test results comment:

```bash
gh pr view PR_NUMBER --repo {REPOSITORY} --comments | grep -A100 "Manual Test Results"
```

Understand:
- What was tested
- What passed/failed
- Any edge cases verified

### 3. Update PR Description

The PR description should reflect the final state:

```markdown
## Summary
{Clear description of what this PR does}

## Changes
- {Key change 1}
- {Key change 2}
- {Key change 3}

## Testing
- Manual testing: See [test results](#issuecomment-XXXXX)
- Unit tests: {number} passing

## Review Evolution
{Brief note on how the PR evolved through review, if significant}
```

```bash
gh pr edit PR_NUMBER --body "new description"
```

### 4. Craft Conventional Commit Message

For squash-merge, craft a good commit message:

**Format:**
```
type(scope): brief description

Longer description if needed. Explain what and why,
not how (the code shows how).

- Key point 1
- Key point 2

PR: #XX
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `docs`: Documentation only
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat(sync): add --repair option for consistency checks

Implements a repair command that:
- Checks manifest consistency with local cache
- Identifies orphaned files and missing entries
- Repairs inconsistencies with --fix flag

Includes comprehensive unit tests and manual blackbox testing.

PR: #42
```

### 5. Squash and Merge

```bash
gh pr merge PR_NUMBER --repo {REPOSITORY} --squash \
  --subject "feat(sync): add --repair option for consistency checks" \
  --body "Implements a repair command that:
- Checks manifest consistency with local cache
- Identifies orphaned files and missing entries
- Repairs inconsistencies with --fix flag

PR: #42"
```

### 6. Verify and Exit

```bash
# Verify the merge succeeded
gh pr view PR_NUMBER --repo {REPOSITORY} --json state,mergedAt
# Should show: "state": "MERGED"
```

Report success and exit. The orchestrator will pick up the next PR on its next wake-up.

## Error Handling

### Merge Conflicts
If there are merge conflicts:
1. Don't force merge
2. Report the conflict
3. Exit - this needs manual intervention or a rebase

### CI Failures
If CI is failing when you try to merge:
1. Don't merge with failing CI
2. Report the failure
3. Exit - this needs to go back through the cycle

### Protected Branch Rules
If merge is blocked by branch protection:
1. Check if required reviews are satisfied
2. Check if required status checks pass
3. Report what's blocking
4. Exit

## Example Session

```
> /prepare-merge

Checking PR #42: Add --repair option for consistency checks

✓ CI green
✓ Manual test results posted (12 tests, all passing)
✓ Review rating: Acceptable (2 rounds)
✓ No merge conflicts

Studying PR diff...
- 2 new files, ~300 lines added
- Evolved through 2 review rounds
- Final state: clean implementation with good test coverage

Updated PR description ✓

Crafted commit message:
  feat(sync): add --repair option for consistency checks

Executing squash-merge...
✓ PR #42 merged successfully

Done. Orchestrator will pick up next PR.
```

## Notes

- **Don't rush** - take time to study the PR holistically
- **Good commit messages matter** - they're permanent project history
- **Verify manual testing** - ensure tests were documented
- **Exit cleanly** - don't start the next task, let the orchestrator handle it
