---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate PR Workflow

Main orchestration logic for the conversation-search PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

The project consists of **multiple work items**, each becoming a PR. The orchestrator works through them sequentially until the project is complete.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **CHECK FOR HUMAN INSTRUCTIONS FIRST** - Read the Slack channel for any messages from humans since the last run
2. If human instructions exist, follow them before doing anything else
3. Discovers any open PRs for the repo (there should be 0 or 1 at a time)
4. Reads the design doc to find pending work items
5. Decides what action is needed based on current state
6. Spawns a worker conversation if work is available
7. Posts status update to Slack
8. Exits (next check happens on next cron trigger)

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. READ SLACK for human instructions (FIRST!)                  │
│  2. If human instructions found → follow them, then exit        │
│  3. Check PR status with lxa pr list (visibility)               │
│  4. Check design doc for pending work items                      │
│  5. Decide: Is there work to dispatch?                           │
│  6. If yes: spawn worker conversation via OH API                 │
│  7. Post status update to Slack                                  │
│  8. Exit                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Step 1: Check for Human Instructions

**This is always the first thing the orchestrator does.**

Read recent messages from `#proj-conv-search-prototype` (ID: `C0B19PK8YR0`) to check if a human has provided instructions since the last orchestrator run (~30 minutes ago).

Use `slack_read_channel` with `channel_id: C0B19PK8YR0` and filter for messages from humans (not bots) in the last ~35 minutes.

### What Counts as Human Instructions

Look for messages from humans (not bot users) that contain actionable instructions:

**Examples of instructions to follow:**
- "Pause the workflow until tomorrow"
- "Skip the current PR and move to the next work item"  
- "Don't merge PR #5 yet, waiting for @alice to review"
- "Focus on fixing the test failures first"
- "Stop working on conversation-search for now"
- "Resume normal operations"
- "Prioritize the caching work item next"

**Ignore these (not instructions):**
- Bot messages (from the orchestrator itself)
- Reactions/emoji only
- General discussion not directed at the orchestrator
- Questions without actionable requests

### If Human Instructions Found

1. **Acknowledge** - Reply in the channel confirming you received the instruction
2. **Follow** - Execute what was requested
3. **Report** - Post what you did in response
4. **Exit** - Don't proceed with normal workflow this cycle

Example response:
```
📋 *Following Human Instructions*

Received from @jpshackelford:
> "Pause the workflow until the security review is complete"

✅ Pausing workflow. Will resume when instructed.
```

### If No Instructions Found

Proceed with normal workflow (Step 2 onwards).

## Gather State

Use `gh` to discover open PRs, `lxa` for quick status, design doc for work items:

```bash
# 1. Discover open PRs (usually 0 or 1)
gh pr list --repo OpenHands/conversation-search --state open --json number,title
# Output: [{"number": 3, "title": "Add semantic search"}]  # or []

# 2. If a PR exists, get quick status with lxa
lxa pr list "OpenHands/conversation-search#3"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Read the design doc for pending work items
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

Before spawning a worker, check if any related conversations are still active. A conversation is **quiet** when its last event timestamp is older than `QUIET_PERIOD` (e.g., 7-15 minutes).

### Using ohtv (Recommended)

Use `ohtv list` with the `--idle` flag to see active vs quiet conversations at a glance:

```bash
# Sync recent conversations (--quiet = minimal output for cron/automation)
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet

# Check conversations for this repo with idle time
# Red = active (< threshold), Green = quiet (>= threshold)
ohtv list --repo conversation-search --since 4h --idle 15
```

Example output:
```
ID      Source  Started          Idle   Events  Title
abc123  cloud   2025-05-02 10:30 3m     42      [Impl] Add semantic search
                                                 Refs: conversation-search#3
def456  cloud   2025-05-02 09:15 47m    28      [Review] PR #2
                                                 Refs: conversation-search#2
```

- **Red idle time** (e.g., `3m`) = conversation is active, don't spawn
- **Green idle time** (e.g., `47m`) = conversation is quiet, safe to spawn

### Why ohtv over direct API?

`ohtv` uses heuristics to find repos related to a conversation by parsing:
- `--repo` flags in gh commands
- Git push output (`To https://github.com/owner/repo`)
- PR/Issue URLs in commands and outputs
- Clone commands
- Merge success messages

This finds conversations that worked on a repo even if `selected_repository` wasn't set correctly.

### Additional ohtv commands

```bash
# See what repos a conversation touched
ohtv refs CONV_ID

# Filter by action type (e.g., only conversations that pushed)
ohtv list --repo conversation-search --action pushed --idle

# Check specific conversation stats
ohtv show CONV_ID -S
```

### Decision Rule

Only spawn if:
- All conversations show **green** idle time (>= QUIET_PERIOD)
- OR no conversations found for this repo in the lookback window

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
  
Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow@add-conversation-search-workflow-plugin
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

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow@add-conversation-search-workflow-plugin
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

Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow@add-conversation-search-workflow-plugin
PR Number: {number}
```

## Slack Notifications

**Channel**: `#proj-conv-search-prototype` (ID: `C0B19PK8YR0`)

After each orchestrator run, post a brief status update to Slack summarizing what's changed since the last run.

### Status Update Format

Use `slack_send_message` to post updates. Always include links to:
- The **PR** being worked on: `https://github.com/OpenHands/conversation-search/pull/{number}`
- Any **conversation** that was spawned: `https://app.all-hands.dev/conversations/{id}`

```
🤖 *Orchestrator Check-in*

*Current State:*
• <https://github.com/OpenHands/conversation-search/pull/5|PR #5>: `oCR green ready 💬2` (2 unresolved threads)
• Work items remaining: 3 of 7

*Action Taken:*
Spawned review worker to address feedback
→ <https://app.all-hands.dev/conversations/{conv_id}|Watch conversation>

*What Changed:*
• PR moved from draft → ready
• CI now passing (was failing)
• 1 review thread resolved

_Next check in ~30 minutes_
```

### When Spawning a Conversation

Always include:
1. What type of worker was launched (implementation/review/merge)
2. What it will do
3. Link to the **PR**: `https://github.com/OpenHands/conversation-search/pull/{number}`
4. Link to the **conversation**: `https://app.all-hands.dev/conversations/{conversation_id}`

Example for review worker:
```
🚀 *Launched: Review Worker*

Addressing feedback on <https://github.com/OpenHands/conversation-search/pull/5|PR #5: Add semantic search>

📎 <https://app.all-hands.dev/conversations/abc123def456|Watch progress>
```

Example for implementation worker:
```
🚀 *Launched: Implementation Worker*

Starting work on: "Add semantic search endpoint"
(No PR yet - will create one)

📎 <https://app.all-hands.dev/conversations/abc123def456|Watch progress>
```

Example for merge worker:
```
🚀 *Launched: Merge Worker*

Preparing to merge <https://github.com/OpenHands/conversation-search/pull/5|PR #5: Add semantic search>

📎 <https://app.all-hands.dev/conversations/abc123def456|Watch progress>
```

### When No Action Needed

Still post a brief update so we know it ran:
```
✅ *Orchestrator Check-in* - All quiet

• <https://github.com/OpenHands/conversation-search/pull/5|PR #5> is in review (waiting for reviewer)
• No active conversations found
• Nothing to do this cycle

_Next check in ~30 minutes_
```

### When Project Completes

```
🎉 *Project Complete!*

All work items have been implemented and merged.
• Total PRs merged: 7
• Project duration: 3 days

See AGENTS.md for the full summary.
```

## Logging

After each action, log what was done:

```
[Orchestrator] 2024-01-15T10:30:00Z
State: PR #5 - oCR green ready 💬2
Action: Spawned review worker (conversation: abc123)
Reason: 2 unresolved review threads need addressing
Next check: ~30 minutes (next cron trigger)
```

```
[Orchestrator] 2024-01-15T14:00:00Z
State: No open PRs, 3 work items remaining in AGENTS.md
Action: Spawned implementation worker for "Add caching layer"
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
