# Orchestrate PR Workflow

Main orchestration logic for the conversation-search PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. Assesses current state of the repository and any open PRs
2. Decides what action is needed
3. Dispatches worker conversations as appropriate
4. Logs what was done
5. Exits (next check happens on next cron trigger)

## Leveraging lxa

`lxa` (Long Execution Agent) provides powerful commands that handle much of the workflow:

| Command | Purpose |
|---------|---------|
| `lxa pr list "Owner/repo#N"` | Quick PR status with history codes |
| `lxa implement --loop --refine` | Full implementation through refinement |
| `lxa refine URL --phase respond` | Address review comments |
| `lxa refine URL --auto-merge` | Address comments and merge when done |

**Consider using `lxa implement --loop --refine --auto-merge`** for the full workflow in a single command!

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. Check PR status with lxa pr list                             │
│  2. Check design doc for pending work items                      │
│  3. Decide: Is there work to dispatch?                           │
│  4. If yes: spawn appropriate worker (or run lxa command)        │
│  5. Log action taken                                             │
│  6. Exit                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Decision Logic

### Gather State

```bash
# Quick PR status
lxa pr list "OpenHands/conversation-search#1"
# Output: oCR green ready 2 - shows history, CI, state, unresolved threads

# Check for open PRs
gh pr list --repo OpenHands/conversation-search --state open

# Read the design doc for pending work items
cat AGENTS.md
```

### Decision Tree

| Current State | Action |
|---------------|--------|
| No open PRs + pending work items | Spawn implementation worker |
| PR exists, draft, CI failing | Wait (worker may still be active) |
| PR exists, draft, CI green | Wait (worker finishing up) |
| PR exists, ready, 💬 = 0 | Check if merge criteria met |
| PR exists, ready, 💬 > 0 | Run `lxa refine URL --phase respond` |
| → Good taste rating | Run `lxa refine URL --auto-merge` or spawn merge worker |
| → 3x Acceptable + solid | Spawn merge worker |
| → Otherwise | Spawn review worker or run `lxa refine` |
| PR merged, more work items | Spawn implementation worker for next item |
| PR merged, no more items | Log completion, exit |

### Avoiding Duplicate Work

Before spawning:
1. Check `lxa job list --running` for active background jobs
2. Check recent conversations via API
3. Only spawn if no active worker exists

```bash
# Check for running lxa jobs
lxa job list --running

# Check recent OH conversations
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?title__contains=conversation-search" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq '.items[:5] | .[] | {id, title, execution_status, created_at}'
```

## Spawning Workers

### Option A: Use lxa Commands Directly

For simple cases, run lxa commands directly from the orchestrator:

```bash
# Full implementation through refinement and merge
lxa implement --loop --refine --auto-merge

# Just address review comments
lxa refine https://github.com/OpenHands/conversation-search/pull/1 --phase respond

# Run in background
lxa refine URL --background --job-name pr1-review
```

### Option B: Spawn OH Conversations

For more control, use `/spawn-conversation` skill:

**Implementation Worker:**
```
Repository: OpenHands/conversation-search
Title: [Implementation] {Work Item Title}
Prompt: |
  Implement the next pending item from AGENTS.md.
  
  1. Read AGENTS.md, find next pending item
  2. Create feature branch from main
  3. Implement with tests (>80% coverage)
  4. Lint, typecheck, fix issues
  5. Commit, push, create DRAFT PR
  6. Monitor CI, fix failures
  7. Once CI green, REFLECT and update AGENTS.md
  8. Move PR to ready (triggers review)
  9. Exit
  
Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
```

**Review Worker:**
```
Repository: OpenHands/conversation-search  
Title: [Review Round] PR #{number}
Prompt: |
  Address review feedback on PR #{number}.
  
  1. Checkout PR branch
  2. Set PR back to draft: gh pr ready {number} --undo
  3. Read ALL review comments
  4. For each: accept and implement (or explain why not)
  5. Commit changes, verify CI after each
  6. Reply to and resolve review threads
  7. REFLECT: update AGENTS.md if learnings impact plan
  8. Move PR back to ready
  9. Exit

PR Number: {number}
```

**Merge Worker:**
```
Repository: OpenHands/conversation-search
Title: [Merge] PR #{number}
Prompt: |
  Prepare and merge PR #{number}.
  
  1. Study full PR diff
  2. Update PR description
  3. Craft conventional commit message
  4. Squash and merge
  5. Update AGENTS.md: mark complete, identify next item
  6. Push to main
  7. Exit

PR Number: {number}
```

## Logging

```
[Orchestrator] 2024-01-15T10:30:00Z
State: PR #1 - oCR green ready 💬2
Action: Running lxa refine --phase respond --background
Reason: 2 unresolved review threads need addressing
Next check: ~30 minutes
```

## Exit Conditions

Always exit after:
- Starting a worker/job (one action per wake-up)
- Determining no action needed
- Encountering an error needing attention

## Cron Schedule

```
*/30 * * * *  # Every 30 minutes
```

Adjust based on expected review turnaround time.
