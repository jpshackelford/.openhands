# PR Workflow Status

Gather comprehensive status of PR(s) for a repository to inform workflow decisions. Uses GitHub CLI (`gh`) for efficient querying.

## Usage

```
/pr-workflow-status
```

Then provide:
- **repository**: GitHub repo (e.g., `OpenHands/conversation-search`)
- **pr_number** (optional): Specific PR to check, or check all open PRs

## What to Gather

### 1. List Open PRs

```bash
gh pr list --repo OWNER/REPO --state open --json number,title,isDraft,headRefName,author,createdAt,updatedAt
```

### 2. For Each PR, Get Details

```bash
gh pr view PR_NUMBER --repo OWNER/REPO --json number,title,state,isDraft,body,reviews,comments,statusCheckRollup,labels,headRefName,mergeable
```

### 3. Check CI Status

```bash
gh pr checks PR_NUMBER --repo OWNER/REPO
```

Look for:
- All checks passing ✓
- Any checks failing ✗
- Checks still running (pending)

### 4. Read Review Comments

```bash
gh pr view PR_NUMBER --repo OWNER/REPO --comments
```

Read through the reviews and comments to understand:
- **Taste rating**: Is the reviewer saying "good taste", "elegant", "acceptable", "needs work"?
- **Review rounds**: How many review cycles have occurred? (Count review submissions followed by author responses)
- **Outstanding issues**: Are there unresolved review threads?
- **Reviewer sentiment**: Is the code close to merge-ready or needs significant rework?

### 5. Determine PR Phase

Based on gathered information, determine which phase the PR is in:

| Phase | Indicators |
|-------|------------|
| **Implementation** | PR is draft, author still pushing commits |
| **CI Stabilization** | PR exists, CI failing or running |
| **Awaiting Review** | PR ready (not draft), CI green, no reviews yet |
| **Review In Progress** | Reviews submitted, author hasn't responded yet |
| **Addressing Review** | Author responded to review, may be pushing fixes |
| **Ready for Merge** | Good/acceptable rating, all threads resolved, CI green |

## Output

After gathering information, summarize:

1. **PR State**: Draft or Ready
2. **CI Status**: Passing, Failing, Pending
3. **Review Status**: No reviews, Reviews pending response, All addressed
4. **Taste Assessment**: Based on reviewer comments (good/acceptable/needs-work)
5. **Review Round Count**: How many review cycles
6. **Phase**: Which workflow phase this PR is in
7. **Recommended Action**: What should happen next

## Example Output

```
PR #42: Implement Ingestion Pipeline

State: Ready (not draft)
CI: ✓ All checks passing
Reviews: 2 reviews submitted
  - Round 1: Acceptable - addressed style issues, refactored chunking
  - Round 2: Acceptable - minor nits about naming
Taste: Acceptable (2 rounds)
Outstanding Threads: 0 unresolved
Phase: Ready for Merge (3rd acceptable would trigger merge)

Recommended Action: 
Since we have 2 acceptable ratings and no outstanding issues,
one more review round with acceptable rating would meet merge criteria.
Current state is good - if next review is acceptable, proceed to merge.
```

## Notes

- Use `gh auth status` to verify GitHub CLI is authenticated
- The `--json` flag gives structured output for programmatic use
- For reading comments/reviews, the plain text output is often clearer for understanding sentiment
- Trust your natural language understanding for taste ratings and sentiment - no special parsing needed
