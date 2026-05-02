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

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. Check design doc / plan for pending work items               │
│  2. Check for any open PRs and their status                      │
│  3. Decide: Is there work to dispatch?                           │
│  4. If yes: spawn appropriate worker conversation                │
│  5. Log action taken                                             │
│  6. Exit                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Decision Logic

### Gather State

First, understand current state:

```bash
# Check for open PRs
gh pr list --repo OpenHands/conversation-search --state open

# For each PR, get status
gh pr view PR_NUMBER --repo OpenHands/conversation-search --json isDraft,statusCheckRollup,reviews

# Read the design doc / AGENTS.md for pending work items
cat AGENTS.md  # or wherever the plan lives
```

### Decision Tree

| Current State | Action |
|---------------|--------|
| No open PRs + pending work items in plan | Spawn `/implement-work-item` worker |
| PR exists, draft, CI failing | Wait (worker may still be active) |
| PR exists, draft, CI green | Wait (worker finishing up) |
| PR exists, ready, awaiting review | Wait (review bot running) |
| PR exists, ready, review done | Evaluate review outcome... |
| → Good taste rating | Spawn `/prepare-and-merge` worker |
| → Acceptable + issues spurious | Spawn `/prepare-and-merge` worker |
| → 3x Acceptable + solid code | Spawn `/prepare-and-merge` worker |
| → Otherwise | Spawn `/address-pr-review` worker |
| PR merged, more work items | Spawn `/implement-work-item` for next item |
| PR merged, no more items | Log completion, exit |

### Avoiding Duplicate Work

Before spawning a worker:
1. Check if there's a recent conversation for this repo (within last hour)
2. If so, check its `execution_status` - if `running`, don't spawn another
3. Only spawn if no active worker exists

```bash
# Check recent conversations
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?title__contains=conversation-search&created_at__gte=2024-01-01T00:00:00Z" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq '.items[] | {id, title, execution_status, created_at}'
```

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
  6. Monitor CI, fix any failures
  7. Once CI is green, REFLECT:
     - Update AGENTS.md: mark item complete, note learnings
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
  2. IMMEDIATELY set PR back to draft mode: gh pr ready PR_NUMBER --undo
  3. Read ALL review comments and threads carefully
  4. For each piece of feedback, decide:
     - Accept and implement (most suggestions improve code quality)
     - Reject only if it significantly increases scope/complexity without clear benefit
  5. Group related changes into logical commits
  6. For each commit:
     - Make the change
     - Run CI checks locally if possible
     - Commit with clear message referencing the feedback
     - Push
     - Verify CI passes before moving to next commit
  7. As you resolve each review thread:
     - Reply explaining what you did (or why you declined)
     - Mark thread as resolved
  8. After all feedback addressed, REFLECT:
     - Did you learn anything that impacts the overall plan?
     - If so, update AGENTS.md and commit
  9. Move PR back to ready: gh pr ready PR_NUMBER
  10. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
PR Number: {number}
```

### Merge Worker

```
Repository: OpenHands/conversation-search
Title: [Merge] PR #{number} - {title}
Prompt: |
  You are preparing PR #{number} for merge.
  
  1. Clone the repo and checkout the PR branch
  2. Study the full PR diff holistically
  3. Read all review history to understand the evolution
  4. Update PR description to reflect final state:
     - What was implemented
     - Key decisions made during review
     - Any notable technical details
  5. Craft a good conventional commit message for squash-merge:
     - feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line
     - Body with relevant details
  6. Squash and merge: gh pr merge PR_NUMBER --squash --body "commit message"
  7. Update AGENTS.md:
     - Mark this work item as complete
     - Note the PR number for reference
     - Identify the next work item to tackle
  8. Push the plan update to main
  9. Exit

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow
PR Number: {number}
```

## Logging

After each action, log what was done:

```
[Orchestrator] 2024-01-15T10:30:00Z
State: PR #42 ready, review done, 2x acceptable ratings
Action: Spawned review worker (conversation: abc123)
Reason: Need 3rd review round - not yet at merge criteria
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

## Cron Schedule Recommendation

Run every 15-30 minutes:
- `*/15 * * * *` - Every 15 minutes (more responsive)
- `*/30 * * * *` - Every 30 minutes (less resource usage)

Adjust based on how fast reviews typically come back.
