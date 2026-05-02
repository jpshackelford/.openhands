# Prepare and Merge

Final merge preparation and execution. Used when PR has met merge criteria (good rating, 3x acceptable, or acceptable with spurious issues).

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
- **Good taste** rating from reviewer, OR
- **Acceptable** rating where issues raised are spurious/incorrect/unimportant, OR
- **3 acceptable** ratings across review rounds AND code is solid

## Steps

### 1. Study the PR Holistically

Don't just look at the latest changes - understand the full picture:

```bash
# View the complete diff against main
gh pr diff PR_NUMBER --repo OpenHands/conversation-search

# Read the PR description and all comments
gh pr view PR_NUMBER --repo OpenHands/conversation-search --comments
```

Think about:
- What is this PR actually accomplishing?
- How did it evolve through review?
- Are there any loose ends?

### 2. Update PR Description

The PR description should reflect the final state, not the initial proposal. Update it to include:

```markdown
## Summary
{Clear description of what this PR does}

## Changes
- {Key change 1}
- {Key change 2}
- {Key change 3}

## Review Evolution
{Brief note on how the PR evolved through review, if significant}

## Testing
{How this was tested, coverage metrics if available}
```

```bash
gh pr edit PR_NUMBER --body "new description"
```

### 3. Craft Conventional Commit Message

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
feat(ingestion): add Minio event parser

Implements event parsing from Minio object storage:
- Handles gzipped JSON events
- Extracts text content from MessageEvent and ActionEvent types
- Filters to user-relevant events only

- Events are read lazily to handle large conversation histories
- Malformed events are logged and skipped rather than failing

PR: #42
```

### 4. Squash and Merge

```bash
gh pr merge PR_NUMBER --repo OpenHands/conversation-search --squash \
  --subject "feat(ingestion): add Minio event parser" \
  --body "Implements event parsing from Minio object storage:
- Handles gzipped JSON events
- Extracts text content from MessageEvent and ActionEvent types
- Filters to user-relevant events only

PR: #42"
```

### 5. Update the Plan

After merge, update the project documentation:

```bash
# Pull the latest main (which now includes the merge)
git checkout main
git pull

# Update AGENTS.md
# - Mark the work item as complete
# - Note the PR number
# - Identify next work item

git add AGENTS.md
git commit -m "docs: mark {item} complete after PR #{number}"
git push
```

### 6. Verify and Exit

```bash
# Verify the merge succeeded
gh pr view PR_NUMBER --repo OpenHands/conversation-search --json state,mergedAt

# Should show: "state": "MERGED"
```

Report success and exit. The next work item will be picked up by the orchestrator on its next wake-up.

## Error Handling

### Merge Conflicts
If there are merge conflicts:
1. Don't force merge
2. Report the conflict
3. Exit - this may need manual intervention or a new PR

### CI Failures
If CI is failing when you try to merge:
1. Don't merge with failing CI
2. Report the failure
3. Exit - this needs to go back through the review cycle

### Protected Branch Rules
If merge is blocked by branch protection:
1. Check if required reviews are satisfied
2. Check if required status checks pass
3. Report what's blocking
4. Exit

## Example Session

```
> /prepare-merge

Checking PR #42: Implement Minio event parser

✓ Merge criteria met: 3 acceptable ratings across review rounds
✓ All CI checks passing
✓ No merge conflicts

Studying PR diff... 
- 3 new files, ~450 lines added
- Evolved through 3 review rounds
- Final state: clean implementation with good test coverage

Updated PR description ✓

Crafted commit message:
  feat(ingestion): add Minio event parser
  
Executing squash-merge...
✓ PR #42 merged successfully

Updating plan...
✓ Marked "Minio client wrapper" as complete
✓ Identified next item: "Event parser (read from Minio)"

Done. Orchestrator will pick up next work item.
```

## Notes

- **Don't rush** - take time to study the PR holistically
- **Good commit messages matter** - they're permanent project history
- **Update the plan** - this closes the loop for the orchestrator
- **Exit cleanly** - don't start the next task, let the orchestrator handle it
