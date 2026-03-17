---
name: github-pr-inline-comments
description: Add inline review comments to GitHub Pull Requests using gh CLI and the GitHub API. Use when reviewing PRs and wanting to comment on specific lines of code.
triggers:
  - "inline comment"
  - "pr review comment"
  - "review comment"
  - "comment on line"
  - "github review"
  - "add review comment"
  - "comment on pr"
  - "pr comment"
---

# GitHub PR Inline Review Comments

This skill provides guidance for adding inline review comments to GitHub Pull Requests using the `gh` CLI.

## Prerequisites

- `gh` CLI installed and authenticated (`gh auth status` to verify)
- Appropriate permissions on the repository

## Creating Inline Review Comments

Inline comments must be submitted as part of a **review**, not as standalone comments. Use the `/pulls/{pull_number}/reviews` endpoint.

### Step 1: Get the PR's HEAD Commit SHA

```bash
gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json headRefOid --jq '.headRefOid'
```

### Step 2: Find the Exact Line Number

The line number must be the line number in the **new version** of the file (the PR's version), not the diff line number.

```bash
# Get the file content at the PR's HEAD commit and find line numbers
gh api repos/<OWNER>/<REPO>/contents/<FILE_PATH>?ref=<COMMIT_SHA> \
  --jq '.content' | base64 -d | grep -n "<search_pattern>"
```

### Step 3: Create the Review Payload

Create a JSON file with the review payload. **Important:** Use a file for the body to avoid shell escaping issues with complex markdown.

```json
{
  "commit_id": "<COMMIT_SHA>",
  "event": "COMMENT",
  "comments": [
    {
      "path": "path/to/file.py",
      "line": 81,
      "body": "Your comment in markdown format"
    }
  ]
}
```

**Event types:**
- `COMMENT` - Leave a comment without approval/rejection
- `APPROVE` - Approve the PR
- `REQUEST_CHANGES` - Request changes

### Step 4: Submit the Review

```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews \
  --method POST \
  --input /path/to/payload.json
```

## Complete Example

```bash
# 1. Get commit SHA
COMMIT_SHA=$(gh pr view 1740 --repo OpenHands/software-agent-sdk --json headRefOid --jq '.headRefOid')

# 2. Find line number
gh api repos/OpenHands/software-agent-sdk/contents/path/to/file.py?ref=$COMMIT_SHA \
  --jq '.content' | base64 -d | grep -n "pattern"

# 3. Create payload file (use file_editor tool to avoid escaping issues)
# Save to /tmp/review_payload.json

# 4. Submit
gh api repos/OpenHands/software-agent-sdk/pulls/1740/reviews \
  --method POST \
  --input /tmp/review_payload.json
```

## Common Pitfalls

### ❌ Don't Use the Comments Endpoint Directly

```bash
# THIS DOES NOT WORK for inline comments:
gh api repos/OWNER/REPO/pulls/123/comments --method POST ...
```

The `/pulls/{pull_number}/comments` endpoint requires a `position` parameter that references diff hunks, which is complex and error-prone. Always use the `/reviews` endpoint instead.

### ❌ Don't Use Shell Heredocs for Complex JSON

Shell heredocs with markdown content often hang or fail due to escaping issues. Instead:

1. Use the `file_editor` tool to create the JSON file
2. Then use `--input /path/to/file.json` with `gh api`

### ❌ Don't Use `-f` for the Body

```bash
# This can cause escaping issues:
gh api ... -f body="complex **markdown** with `code`"

# Use -F with a file instead:
gh api ... -F body=@/tmp/comment.md
```

### ✅ Always Use `--input` with a JSON File

This is the most reliable approach for complex review comments with code blocks and markdown formatting.

## Multi-Line Comments

To comment on a range of lines, add `start_line` and `start_side`:

```json
{
  "commit_id": "<SHA>",
  "event": "COMMENT", 
  "comments": [
    {
      "path": "file.py",
      "line": 85,
      "start_line": 80,
      "body": "This entire block needs refactoring"
    }
  ]
}
```

## Multiple Comments in One Review

You can include multiple inline comments in a single review:

```json
{
  "commit_id": "<SHA>",
  "event": "COMMENT",
  "comments": [
    {
      "path": "file1.py",
      "line": 42,
      "body": "First comment"
    },
    {
      "path": "file2.py", 
      "line": 17,
      "body": "Second comment"
    }
  ]
}
```

## Reference

- [GitHub REST API - Create a review](https://docs.github.com/en/rest/pulls/reviews#create-a-review-for-a-pull-request)
- [GitHub REST API - Pull request review comments](https://docs.github.com/en/rest/pulls/comments)
