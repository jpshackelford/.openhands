---
name: pr-workflow-status
description: Get comprehensive PR status for workflow decisions
triggers:
  - /pr-workflow-status
  - /pr-status
---

# PR Workflow Status

Gather comprehensive status of PR(s) for a repository to inform workflow decisions. Uses `tkt` for efficient visualization and `gh` CLI for details.

## Usage

```
/pr-workflow-status
```

Then provide:
- **repository**: GitHub repo (e.g., `{REPOSITORY}`)
- **pr_number** (optional): Specific PR to check, or check all open PRs

## Using tkt pr list

The `tkt pr list` command provides a compact view of PR status:

```bash
# First, discover open PRs
gh pr list --repo {REPOSITORY} --state open --json number

# List specific PR (use the discovered number)
tkt pr list "{REPOSITORY}#<PR_NUMBER>"

# List all open PRs for a repo (need to add to board first)
tkt repo add {REPOSITORY}
tkt pr list --all
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

If manual testing is enabled for this project (see `.agents/resources/orchestration.md`), check if test results have been posted:

```bash
# Simple check via grep
gh pr view PR_NUMBER --repo {REPOSITORY} --comments | grep -i "Manual Test Results"

# More precise check via GraphQL (replace {OWNER}, {REPO}, PR_NUMBER)
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
' -f owner={OWNER} -f repo={REPO} -f number=PR_NUMBER | \
  jq '.data.repository.pullRequest.comments.nodes[] | select(.body | test("Manual Test Results"; "i"))'
```

## Determine PR Phase

Based on gathered information, determine where the PR is in the PR workflow:

| Phase | Indicators |
|-------|------------|
| **Implementation** | PR is draft **and** an active worker owns the slot, or a draft author is still pushing (head SHA changed since last tick). A draft with no active worker and no new commits is **not** Implementation — adopt it (see orchestrate "Anti-Stall: Drafts"). |
| **CI Stabilization** | PR exists, CI red or pending |
| **Awaiting Manual Test** | PR ready, CI green, NO manual test comment |
| **Awaiting Review** | PR ready, CI green, manual test posted, no reviews; trigger external review when `Self-review: disabled`, or spawn self-review worker when `Self-review: enabled` |
| **Review In Progress** | History shows `C`, 💬 > 0 |
| **Addressing Review** | Author pushing fixes (history shows `F` after `C`) |
| **Ready for Merge** | Good/acceptable rating, 💬 = 0, CI green, test posted |

## Example Workflow

```bash
# 1. Discover current open PRs
gh pr list --repo {REPOSITORY} --state open --json number,title,isDraft,headRefOid

# 2. Quick status check for each
tkt pr list "{REPOSITORY}#42"
# Output: oC green ready 2 - needs attention

# 3. Check for manual test results
gh pr view 42 --repo {REPOSITORY} --comments | grep -c "Manual Test Results"
# Output: 1 (test results present) or 0 (not tested yet)

# 4. If tested, check review status
gh pr view 42 --repo {REPOSITORY} --comments | tail -50
```

## Notes

- `tkt` requires repos to be added to a board for `--all` listing
- The history codes in `tkt pr list` tell the story at a glance
- Always check for manual test results before spawning review worker
- `Awaiting Review` is not an `All quiet` state while an open PR remains actionable
- If `Self-review: disabled`, verify the target repo has a PR review workflow and trigger it with `review-this` or a reviewer request when no review exists
- Trust your natural language understanding for taste ratings
