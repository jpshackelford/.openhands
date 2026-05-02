# Orchestrate PR Workflow

Main orchestration logic for the conversation-search PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. Assesses current state of the repository and any open PRs
2. Decides what action is needed
3. Spawns worker conversations as appropriate
4. Logs what was done
5. Exits (next check happens on next cron trigger)

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. Check PR status with lxa pr list (visibility)               │
│  2. Check design doc for pending work items                      │
│  3. Decide: Is there work to dispatch?                           │
│  4. If yes: spawn worker conversation via OH API                 │
│  5. Log action taken                                             │
│  6. Exit                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Gather State

Use `lxa` for quick visibility, `gh` for details:

```bash
# Quick PR status - shows history, CI, state, unresolved threads
lxa pr list "OpenHands/conversation-search#1"
# Output: oCR green ready 2

# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# List all open PRs
gh pr list --repo OpenHands/conversation-search --state open

# Read the design doc for pending work items
cat AGENTS.md
```

## Decision Tree

| Current State | Action |
|---------------|--------|
| No open PRs + pending work items | Spawn **implementation worker** |
| PR exists, draft, CI failing | Wait (worker may still be active) |
| PR exists, draft, CI green | Wait (worker finishing up) |
| PR exists, ready, no reviews yet | Wait (review bot running) |
| PR exists, ready, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, 💬 = 0, good/acceptable taste | Spawn **merge worker** |
| PR exists, ready, 💬 = 0, 3x acceptable | Spawn **merge worker** |
| PR merged, more work items | Spawn **implementation worker** for next item |
| PR merged, no more items | Log completion, exit |

## Avoiding Duplicate Work

Before spawning a worker, check if any related conversations are still active. A conversation is considered **quiet** when its last event timestamp is older than `QUIET_PERIOD` (e.g., 10-15 minutes).

### Step 1: Find related conversations

```bash
# Get recent conversations for this repo
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?title__contains=conversation-search&limit=10" \
  -H "Authorization: Bearer $OH_API_KEY" \
| jq '.items[] | {id, title: .title[:50], updated_at}'
```

### Step 2: Check last event timestamp for each

```bash
# Get last event for a specific conversation
CONV_ID="abc123..."
curl -s "https://app.all-hands.dev/api/v1/conversation/${CONV_ID}/events/search?sort_order=TIMESTAMP_DESC&limit=1" \
  -H "Authorization: Bearer $OH_API_KEY" \
| jq '.items[0].timestamp'
# Returns: "2025-05-02T15:30:00.000000Z"
```

### Step 3: Calculate if quiet

```bash
QUIET_MINUTES=15
LAST_EVENT=$(curl -s "https://app.all-hands.dev/api/v1/conversation/${CONV_ID}/events/search?sort_order=TIMESTAMP_DESC&limit=1" \
  -H "Authorization: Bearer $OH_API_KEY" | jq -r '.items[0].timestamp // empty')

if [ -z "$LAST_EVENT" ]; then
  echo "No events - conversation never started or is brand new"
else
  LAST_EPOCH=$(date -d "$LAST_EVENT" +%s 2>/dev/null || echo 0)
  NOW_EPOCH=$(date +%s)
  DIFF_MINS=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))
  
  if [ "$DIFF_MINS" -gt "$QUIET_MINUTES" ]; then
    echo "Conversation quiet for ${DIFF_MINS}m - safe to spawn new worker"
  else
    echo "Conversation active ${DIFF_MINS}m ago - wait before spawning"
  fi
fi
```

### Alternative: Use ohtv (if synced)

If conversations are synced locally via `ohtv sync`, you can use ohtv for more efficient lookups:

```bash
# Sync recent conversations (do this periodically, not on every check)
ohtv sync --since $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) --quiet

# Check a conversation's last event timestamp
ohtv show CONV_ID -S  # Shows first_ts and last_ts in stats
```

**Decision rule:** Only spawn if:
- No conversation has last event within QUIET_PERIOD, OR
- All related conversations are clearly finished (have finish action)

## Spawning Workers

Use `/spawn-conversation` skill to start worker conversations.

### Implementation Worker

```
Repository: OpenHands/conversation-search
Title: [Implementation] {Work Item Title}
Prompt: |
  You are implementing a work item for the conversation-search project.
  
  1. Read AGENTS.md to understand the project and find the next pending item
  2. Create a feature branch from main (ensure main is up-to-date)
  3. Implement the feature with tests (target >80% coverage for new code)
  4. Run lints and type checks, fix any issues
  5. Commit with clear messages, push, create a DRAFT PR
  6. Monitor CI, fix any failures until green
  7. Once CI is green, REFLECT:
     - Update AGENTS.md: mark item as in-progress, note any learnings
     - Clarify next steps based on what you learned
     - Commit these plan updates
  8. Move PR from draft to ready (triggers review bot)
  9. Exit - review handling is a separate conversation
  
Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
```

### Review Worker

```
Repository: OpenHands/conversation-search  
Title: [Review Round] PR #{number} - {title}
Prompt: |
  You are addressing review feedback on PR #{number}.
  
  1. Clone the repo and checkout the PR branch
  2. IMMEDIATELY set PR back to draft mode: gh pr ready {number} --undo
  3. Read ALL review comments and threads carefully
  4. For each piece of feedback, decide:
     - Accept and implement (most suggestions improve code quality)
     - Reject only if it significantly increases scope/complexity without clear benefit
  5. Group related changes into logical commits
  6. For each commit:
     - Make the change
     - Commit with clear message referencing the feedback
     - Push and verify CI passes before moving to next commit
  7. As you resolve each review thread:
     - Reply explaining what you did (or why you declined)
     - Mark thread as resolved using GitHub GraphQL API
  8. After all feedback addressed, REFLECT:
     - Did you learn anything that impacts the overall plan?
     - If so, update AGENTS.md and commit
  9. Move PR back to ready: gh pr ready {number}
  10. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
PR Number: {number}
```

### Merge Worker

```
Repository: OpenHands/conversation-search
Title: [Merge] PR #{number} - {title}
Prompt: |
  You are preparing PR #{number} for merge. Merge criteria has been met.
  
  1. Clone the repo and checkout the PR branch
  2. Study the full PR diff holistically - understand what was built
  3. Read all review history to understand how it evolved
  4. Update PR description to reflect final state:
     - What was implemented
     - Key decisions made during review
     - Any notable technical details
  5. Craft a good conventional commit message for squash-merge:
     - feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line
     - Body with relevant details
  6. Squash and merge: gh pr merge {number} --squash --body "commit message"
  7. Update AGENTS.md:
     - Mark this work item as complete with PR reference
     - Identify the next work item to tackle
     - Note any learnings for future work
  8. Push the plan update to main
  9. Exit

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
PR Number: {number}
```

## Logging

After each action, log what was done:

```
[Orchestrator] 2024-01-15T10:30:00Z
State: PR #1 - oCR green ready 💬2
Action: Spawned review worker (conversation: abc123)
Reason: 2 unresolved review threads need addressing
Next check: ~30 minutes (next cron trigger)
```

## Exit Conditions

Always exit after:
- Spawning a worker (one action per wake-up)
- Determining no action needed (everything is in expected state)
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
