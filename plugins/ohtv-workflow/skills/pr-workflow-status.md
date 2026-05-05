---
name: pr-workflow-status
description: Get comprehensive PR status for workflow decisions
triggers:
  - /pr-workflow-status
  - /pr-status
---

# PR Workflow Status

Gather comprehensive status of PR(s) for a repository to inform workflow decisions. Uses `lxa` for efficient visualization and `gh` CLI for details.

## Usage

```
/pr-workflow-status
```

Then provide:
- **repository**: GitHub repo (e.g., `jpshackelford/ohtv`)
- **pr_number** (optional): Specific PR to check, or check all open PRs

## Using lxa pr list

The `lxa pr list` command provides a compact view of PR status:

```bash
# First, discover open PRs
gh pr list --repo jpshackelford/ohtv --state open --json number

# List specific PR (use the discovered number)
lxa pr list "jpshackelford/ohtv#<PR_NUMBER>"

# List all open PRs for a repo (need to add to board first)
lxa repo add jpshackelford/ohtv
lxa pr list --all
```

**Output columns:**
- **History**: Compact codes showing PR lifecycle
  - `o` = opened
  - `C` = changes requested
  - `F` = fixes pushed
  - `c` = comment
  - `A` = approved
  - `m` = merged
  - `k` = killed/closed
- **CI**: green/red/pending/conflict
- **State**: draft, ready, merged, closed
- **💬**: Count of unresolved review threads
- **Age/Last**: Time since creation and last activity

## Checking for Manual Test Results

For ohtv, manual testing is **required** before code review. Check if test results have been posted:

```bash
# Simple check via grep
gh pr view PR_NUMBER --repo jpshackelford/ohtv --comments | grep -i "Manual Test Results"

# More precise check via GraphQL
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        comments(first: 100) {
          nodes {
            body
            author { login }
            createdAt
          }
        }
      }
    }
  }
' -f owner=jpshackelford -f repo=ohtv -f number=42 | \
  jq '.data.repository.pullRequest.comments.nodes[] | select(.body | test("Manual Test Results"; "i"))'
```

## Determine PR Phase

Based on gathered information, determine where the PR is in the ohtv workflow:

| Phase | Indicators |
|-------|------------|
| **Implementation** | PR is draft, author still pushing commits |
| **CI Stabilization** | PR exists, CI red or pending |
| **Awaiting Manual Test** | PR ready, CI green, NO manual test comment |
| **Awaiting Review** | PR ready, CI green, manual test posted, no reviews |
| **Review In Progress** | History shows `C`, 💬 > 0 |
| **Addressing Review** | Author pushing fixes (history shows `F` after `C`) |
| **Ready for Merge** | Good/acceptable rating, 💬 = 0, CI green, test posted |

## Example Workflow

```bash
# 1. Discover current open PRs
gh pr list --repo jpshackelford/ohtv --state open --json number,title,isDraft

# 2. Quick status check for each
lxa pr list "jpshackelford/ohtv#42"
# Output: oC green ready 2 - needs attention

# 3. Check for manual test results
gh pr view 42 --repo jpshackelford/ohtv --comments | grep -c "Manual Test Results"
# Output: 1 (test results present) or 0 (not tested yet)

# 4. If tested, check review status
gh pr view 42 --repo jpshackelford/ohtv --comments | tail -50
```

## Notes

- `lxa` requires repos to be added to a board for `--all` listing
- The history codes in `lxa pr list` tell the story at a glance
- Always check for manual test results before spawning review worker
- Trust your natural language understanding for taste ratings
