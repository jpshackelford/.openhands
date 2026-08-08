---
name: shepherd-merge
description: Merge a PR that is approved and ready. Verifies all checks pass, no conflicts, required approvals obtained, then performs squash merge. Use when /shepherd reports history ending in 'A' with green CI.
triggers:
- /shepherd-merge
---

# Shepherd Merge

Merge an approved, ready PR.

## When to Use

- `/shepherd` reports history ends `A`, CI green, 0 threads
- "Merge PR #123"
- "This PR is ready, merge it"
- PR is approved and all checks pass

## Usage

```bash
/shepherd-merge owner/repo#123
/shepherd-merge https://github.com/owner/repo/pull/123

# Via lxa with auto-merge
lxa refine <URL> --auto-merge
```

## Pre-Merge Checklist

Before merging, verify all conditions are met:

```bash
gh pr view <number> --json state,mergeable,reviewDecision,statusCheckRollup,isDraft
```

| Check | Required Value | Command to Verify |
|-------|----------------|-------------------|
| State | OPEN | `gh pr view --json state` |
| Mergeable | MERGEABLE | `gh pr view --json mergeable` |
| Review Decision | APPROVED | `gh pr view --json reviewDecision` |
| CI Status | All passing | `gh pr checks <number>` |
| Draft | false | `gh pr view --json isDraft` |
| Threads | 0 unresolved | Check review threads |

### Verification Commands

```bash
# Full status check
gh pr view <number> --json state,mergeable,reviewDecision,isDraft

# CI checks
gh pr checks <number>

# Unresolved threads count
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: NUMBER) {
      reviewThreads(first: 100) {
        nodes { isResolved }
      }
    }
  }
}' | jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved == false)] | length'
```

## Merge Process

### Step 1: Final Verification

```bash
# Comprehensive check
gh pr view <number> --json state,mergeable,reviewDecision,statusCheckRollup,isDraft,title,body
```

### Step 2: Update Branch (if needed)

If the branch is behind main:

```bash
# Option A: Merge main into branch
gh pr update-branch <number>

# Wait for CI to re-run
gh pr checks <number> --watch
```

### Step 3: Merge

```bash
# Squash merge (recommended)
gh pr merge <number> --squash --delete-branch

# Or with custom commit message
gh pr merge <number> --squash --delete-branch \
  --subject "feat: add new feature (#123)" \
  --body "Description of the change"
```

### Step 4: Verify

```bash
# Confirm merge
gh pr view <number> --json state,mergedAt,mergeCommit
```

## Merge Options

| Option | Flag | When to Use |
|--------|------|-------------|
| Squash | `--squash` | Default - clean history |
| Merge commit | `--merge` | Preserve all commits |
| Rebase | `--rebase` | Linear history |
| Delete branch | `--delete-branch` | Always (unless needed) |
| Auto-merge | `--auto` | Set to merge when checks pass |

## Handling Issues

### Branch Not Mergeable

```bash
# Check mergeable status
gh pr view <number> --json mergeable,mergeStateStatus

# If CONFLICTING:
/shepherd-fix-ci <number>  # to resolve conflicts

# If BEHIND:
gh pr update-branch <number>
```

### Missing Approvals

```bash
# Check review decision
gh pr view <number> --json reviewDecision,reviews

# If REVIEW_REQUIRED or CHANGES_REQUESTED:
# Wait for human approval - don't merge
```

### CI Failing

```bash
# Check CI status
gh pr checks <number>

# If any failing:
/shepherd-fix-ci <number>
```

### Unresolved Threads

```bash
# If threads > 0:
/shepherd-respond <number>
```

## Output Format

```
Merge Check for owner/repo#123
==============================

Pre-merge verification:
  ✓ State: OPEN
  ✓ Mergeable: MERGEABLE
  ✓ Review Decision: APPROVED
  ✓ CI Status: All checks passing (5/5)
  ✓ Draft: false
  ✓ Unresolved threads: 0

All checks passed. Proceeding with merge...

Merging with squash...
✓ Merged PR #123 into main
✓ Deleted branch feature/add-feature

Merge commit: abc1234
```

## When NOT to Merge

Do not merge if:
- Review decision is not APPROVED
- CI is failing or pending
- There are unresolved review threads
- Branch has merge conflicts
- PR is still in draft state
- Required reviewers haven't reviewed

Instead, report the blocking condition and suggest next action.

## Alternative: lxa refine --auto-merge

For automated merge after refinement passes:

```bash
lxa refine <URL> --auto-merge
```

This completes any pending refinement phases before merging.

## Related Skills

- `/shepherd` - Get initial status
- `/shepherd-advance` - Auto-determine action
- `/shepherd-fix-ci` - Resolve conflicts or CI issues
- `/shepherd-respond` - Address unresolved threads
