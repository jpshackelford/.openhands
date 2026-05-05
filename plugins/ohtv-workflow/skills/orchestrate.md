---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate PR Workflow

Main orchestration logic for the ohtv PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

Unlike design-document-driven projects, ohtv uses **GitHub issues and PRs exclusively** as the source of truth. The orchestrator picks up existing PRs and advances them through completion.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **CHECK FOR HUMAN INSTRUCTIONS FIRST** - Read WORKLOG.md for any `## INSTRUCTION:` entries
2. If human instructions exist, follow them before doing anything else
3. Discovers any open PRs for the repo
4. Checks PR status (CI, reviews, manual testing)
5. Decides what action is needed based on current state
6. Spawns a worker conversation if work is available
7. Appends status update to WORKLOG.md on main
8. Exits (next check happens on next cron trigger)

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. READ WORKLOG.md for human instructions (FIRST!)             │
│  2. If human instructions found → follow them, then exit        │
│  3. Check PR status with lxa pr list + gh (visibility)          │
│  4. Check PR comments for manual test results                    │
│  5. Decide: Is there work to dispatch?                           │
│  6. If yes: spawn worker conversation via OH API                 │
│  7. Append status update to WORKLOG.md (on main!)               │
│  8. Exit                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Step 0: Ensure Tools Are Installed

Before anything else, ensure `lxa` and `ohtv` are available:

```bash
# Install if not already present
which lxa || uv pip install git+https://github.com/jpshackelford/lxa.git
which ohtv || uv pip install git+https://github.com/jpshackelford/ohtv.git

# Ensure the repo is on the lxa board
lxa repo add jpshackelford/ohtv 2>/dev/null || true

# Sync recent ohtv data
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet
```

## Step 1: Check for Human Instructions

**This is the first thing the orchestrator does after setup.**

Read the `WORKLOG.md` file in the repo root to check for human instructions. Look for entries marked with `## INSTRUCTION:` that haven't been acknowledged yet.

```bash
# Check for unacknowledged instructions
cat WORKLOG.md | grep -A5 "## INSTRUCTION:" | grep -v "ACKNOWLEDGED"
```

### What Counts as Human Instructions

Look for `## INSTRUCTION:` entries that contain actionable requests:

**Examples of instructions to follow:**
- `## INSTRUCTION: Pause the workflow until tomorrow`
- `## INSTRUCTION: Skip PR #42 - waiting for external dependency`
- `## INSTRUCTION: Focus on fixing the test failures first`
- `## INSTRUCTION: Resume normal operations`

### If Human Instructions Found

1. **Acknowledge** - Add `[ACKNOWLEDGED]` to the instruction entry
2. **Follow** - Execute what was requested
3. **Report** - Log what you did in response to WORKLOG.md
4. **Exit** - Don't proceed with normal workflow this cycle

### If No Instructions Found

Proceed with normal workflow (Step 2 onwards).

## Gather State

Use `gh` to discover open PRs, `lxa` for quick status:

```bash
# 1. Discover open PRs
gh pr list --repo jpshackelford/ohtv --state open --json number,title,isDraft
# Output: [{"number": 42, "title": "Add --repair option", "isDraft": false}]

# 2. For each PR, get quick status with lxa
lxa pr list "jpshackelford/ohtv#42"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Check for manual test results in PR comments
gh pr view 42 --repo jpshackelford/ohtv --comments | grep -i "Manual Test Results"
```

## Decision Tree

The ohtv workflow has a **mandatory manual testing step** before review.

| Current State | Action |
|---------------|--------|
| PR exists, draft, CI failing | Wait (worker may still be active) |
| PR exists, draft, CI green | Wait (implementation finishing up) |
| PR exists, ready, CI green, **no manual test results** | Spawn **testing worker** |
| PR exists, ready, CI green, test results posted, no reviews | Wait (review bot running) |
| PR exists, ready, CI green, test results posted, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, test results posted, good/acceptable rating | Spawn **merge worker** |
| PR merged | Log completion, move to next PR |

### Detecting Manual Test Results

A PR has been manually tested if there's a comment containing:
- `## Manual Test Results` (or similar header)
- Posted by `openhands-ai` or contains "AI agent (OpenHands)"

```bash
# Check for manual test comment
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        comments(first: 100) {
          nodes {
            body
            author { login }
          }
        }
      }
    }
  }
' -f owner=jpshackelford -f repo=ohtv -f number=42 | \
  jq '.data.repository.pullRequest.comments.nodes[] | select(.body | test("Manual Test Results"; "i"))'
```

## Avoiding Duplicate Work

Before spawning a worker, check if any related conversations are still active:

```bash
# Sync recent conversations
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet

# Check conversations for this repo with idle time
ohtv list --repo ohtv --since 4h --idle 15
```

- **Red idle time** = conversation is active, don't spawn
- **Green idle time** = conversation is quiet, safe to spawn

## Worker Prompts

### Testing Worker

```
Repository: jpshackelford/ohtv
Title: [Manual Test] PR #{number} - {title}
Prompt: |
  You are running manual tests for PR #{number}.
  
  This is a REQUIRED step before code review. Your job is to:
  1. Clone the repo and checkout the PR branch
  2. Install with `uv sync`
  3. Read the PR to understand what changed
  4. Design and execute blackbox tests for the new functionality
  5. Run the unit test suite
  6. Post a structured test report as a PR comment
  
  Follow the /manual-test skill for the expected test report format.
  
  After posting the test report, EXIT. Do not continue to review.

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

### Review Worker

```
Repository: jpshackelford/ohtv
Title: [Review Round] PR #{number} - {title}
Prompt: |
  You are addressing review feedback on PR #{number}.
  
  1. Clone the repo and checkout the PR branch
  2. IMMEDIATELY set PR back to draft mode: gh pr ready {number} --undo
  3. Read ALL review comments and threads carefully
  4. For each piece of feedback, decide:
     - Accept and implement (most suggestions improve code quality)
     - Reject only if it significantly increases scope/complexity
  5. Group related changes into logical commits
  6. For each commit:
     - Make the change
     - Commit with clear message referencing the feedback
     - Push and verify CI passes
  7. Reply to review threads explaining what you did
  8. Move PR back to ready: gh pr ready {number}
  9. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

### Merge Worker

```
Repository: jpshackelford/ohtv
Title: [Merge] PR #{number} - {title}
Prompt: |
  You are preparing PR #{number} for merge. Merge criteria has been met.
  
  1. Clone the repo and checkout the PR branch
  2. Study the full PR diff holistically
  3. Read the manual test results to understand what was verified
  4. Update PR description to reflect final state:
     - What was implemented
     - Key decisions made during review
     - Test coverage
  5. Craft a conventional commit message for squash-merge:
     - feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line
     - Body with relevant details
  6. Squash and merge: gh pr merge {number} --squash --body "commit message"
  7. Verify the merge succeeded
  8. Exit

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

## WORKLOG.md Updates

After each orchestrator run, append a status update to `WORKLOG.md` in the repo root.

### Log Entry Format

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Current State:**
- [PR #42](https://github.com/jpshackelford/ohtv/pull/42): `oC green ready` 
  - Manual testing: ✅ Posted
  - Review status: 💬2 unresolved threads

**Action Taken:**
🚀 Spawned review worker to address feedback
- Conversation: https://app.all-hands.dev/conversations/{conv_id}

---
```

### When Spawning a Testing Worker

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

🧪 **Launched: Testing Worker**

Testing [PR #42](https://github.com/jpshackelford/ohtv/pull/42): Add --repair option
- CI is green, ready for manual testing
- Conversation: https://app.all-hands.dev/conversations/{conv_id}

---
```

### When No Action Needed

```markdown
### 2025-05-05 14:30 UTC - Orchestrator

✅ **All quiet** - No action needed

- [PR #42](https://github.com/jpshackelford/ohtv/pull/42): Waiting for review
  - Manual testing: ✅ Posted
  - Review: In progress (awaiting reviewer)
- No active conversations found

---
```

### Committing WORKLOG.md Updates

**IMPORTANT:** WORKLOG.md updates MUST go to `main`, not to any feature branch.

```bash
# Save current branch
CURRENT_BRANCH=$(git branch --show-current)

# Stash any uncommitted work
git stash --include-untracked

# Switch to main and pull latest
git checkout main
git pull origin main

# Append your update to WORKLOG.md
cat >> WORKLOG.md << 'EOF'
### 2025-05-05 10:30 UTC - Orchestrator

... your update here ...

---
EOF

# Commit and push to main
git add WORKLOG.md
git commit -m "chore: worklog update $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push origin main

# Return to previous branch
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
  git checkout "$CURRENT_BRANCH"
  git stash pop 2>/dev/null || true
fi
```

## Logging

After each action, log to stdout for the conversation record:

```
[Orchestrator] 2025-05-05T10:30:00Z
State: PR #42 - oC green ready, no manual test results
Action: Spawned testing worker (conversation: abc123)
Reason: PR ready for manual testing
Next check: ~30 minutes (next cron trigger)
```

## Exit Conditions

Always exit after:
- Spawning a worker (one action per wake-up)
- Determining no action needed
- Encountering an error that needs human attention

Do NOT:
- Wait for spawned workers to complete
- Take multiple actions in one wake-up
- Loop continuously

## Cron Schedule

```
*/30 * * * *  # Every 30 minutes
```

Adjust based on expected review turnaround time.
