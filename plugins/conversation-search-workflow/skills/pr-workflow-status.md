# PR Workflow Status

Gather comprehensive status of PR(s) for a repository to inform workflow decisions. Uses `lxa` for efficient visualization and `gh` CLI for details.

## Usage

```
/pr-workflow-status
```

Then provide:
- **repository**: GitHub repo (e.g., `OpenHands/conversation-search`)
- **pr_number** (optional): Specific PR to check, or check all open PRs

## Using lxa pr list

The `lxa pr list` command provides a compact view of PR status:

```bash
# List specific PR(s)
lxa pr list "OpenHands/conversation-search#1"

# List all open PRs for a repo (need to add to board first)
lxa repo add OpenHands/conversation-search
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

**Example:**
```
  Repo                            PR   History   CI      State   💬   Age   Last
 ───────────────────────────────────────────────────────────────────────────────────
  OpenHands/conversation-search   #1   oCR       green   ready    2   18h   15h ago
```

This tells us: PR was opened, got Changes requested, is in Review round, CI is green, 2 unresolved threads.

## Using lxa review

See what needs review attention:

```bash
lxa review --repo OpenHands/conversation-search
```

## Getting Detailed Information

For deeper analysis, use `gh`:

```bash
# Full PR details
gh pr view PR_NUMBER --repo OWNER/REPO

# With all comments
gh pr view PR_NUMBER --repo OWNER/REPO --comments

# CI check status
gh pr checks PR_NUMBER --repo OWNER/REPO
```

## Reading Review Comments

Read through the reviews and comments to understand:
- **Taste rating**: Is the reviewer saying "good taste", "elegant", "acceptable", "needs work"?
- **Review rounds**: The history code shows this (e.g., `oCFCFA` = 2 review rounds with fixes)
- **Outstanding issues**: The 💬 column shows unresolved thread count
- **Reviewer sentiment**: Is the code close to merge-ready or needs significant rework?

## Determine PR Phase

Based on gathered information:

| Phase | Indicators |
|-------|------------|
| **Implementation** | PR is draft, author still pushing commits |
| **CI Stabilization** | PR exists, CI red or pending |
| **Awaiting Review** | PR ready, CI green, no reviews yet |
| **Review In Progress** | History shows `C` (changes requested), 💬 > 0 |
| **Addressing Review** | Author pushing fixes (history shows `F` after `C`) |
| **Ready for Merge** | Good/acceptable rating, 💬 = 0, CI green |

## Example Workflow

```bash
# Quick status check
lxa pr list "OpenHands/conversation-search#1"

# Output: oCR green ready 2 - needs attention (2 unresolved threads)

# Get details on what needs addressing
gh pr view 1 --repo OpenHands/conversation-search --comments

# Read the review comments, understand what's being asked
# Determine: is this good taste, acceptable, or needs work?
```

## Notes

- `lxa` requires repos to be added to a board for `--all` listing, or use explicit PR refs
- The history codes in `lxa pr list` tell the story of the PR at a glance
- Trust your natural language understanding for taste ratings - no special parsing needed
