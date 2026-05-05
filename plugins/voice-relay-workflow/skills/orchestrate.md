---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate PR Workflow

Main orchestration logic for the voice-relay PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

The project work items are tracked as **GitHub Issues**. The orchestrator works through open issues sequentially (lowest number first) until all issues are complete.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **CHECK FOR HUMAN INSTRUCTIONS FIRST** - Read WORKLOG.md for any `## INSTRUCTION:` entries
2. If human instructions exist, follow them before doing anything else
3. Discovers any open PRs for the repo (there should be 0 or 1 at a time)
4. Lists open GitHub issues to find pending work items
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
│  3. Check PR status with lxa pr list (visibility)               │
│  4. List open GitHub issues for pending work items               │
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
lxa repo add jpshackelford/voice-relay 2>/dev/null || true

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
- `## INSTRUCTION: Skip the current PR and move to the next work item`
- `## INSTRUCTION: Don't merge PR #5 yet, waiting for review`
- `## INSTRUCTION: Focus on fixing the test failures first`
- `## INSTRUCTION: Resume normal operations`

### If Human Instructions Found

1. **Acknowledge** - Add `[ACKNOWLEDGED]` to the instruction entry
2. **Follow** - Execute what was requested
3. **Report** - Log what you did in response to WORKLOG.md
4. **Exit** - Don't proceed with normal workflow this cycle

Example acknowledgment (append to WORKLOG.md):
```markdown
### 2025-05-05 10:30 UTC - Orchestrator

📋 **Following Human Instructions**

Received instruction:
> "Pause the workflow until the security review is complete"

✅ Pausing workflow. Will resume when instructed.
[ACKNOWLEDGED: ## INSTRUCTION: Pause the workflow...]
```

### If No Instructions Found

Proceed with normal workflow (Step 2 onwards).

## Gather State

Use `gh` to discover open PRs, `lxa` for quick status, and GitHub issues for work items:

```bash
# 1. Discover open PRs (usually 0 or 1)
gh pr list --repo jpshackelford/voice-relay --state open --json number,title
# Output: [{"number": 3, "title": "Add semantic search"}]  # or []

# 2. If a PR exists, get quick status with lxa
lxa pr list "jpshackelford/voice-relay#3"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. List open GitHub issues for pending work items (sorted by issue number)
gh issue list --repo jpshackelford/voice-relay --state open --json number,title --jq 'sort_by(.number)'
# Output: [{"number": 9, "title": "F1: Scope messages to sessions"}, ...]

# 4. Get details of the next issue to work on (lowest number)
gh issue view 9 --repo jpshackelford/voice-relay --json number,title,body
```

## Decision Tree

| Current State | Action |
|---------------|--------|
| No open PRs + open issues exist | Spawn **implementation worker** for lowest-numbered issue |
| PR exists, draft, CI failing | Wait (worker may still be active) |
| PR exists, draft, CI green | Wait (worker finishing up) |
| PR exists, ready, no reviews yet | Wait (review bot running) |
| PR exists, ready, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, 💬 = 0, good/acceptable taste | Spawn **merge worker** |
| PR exists, ready, 💬 = 0, 3x acceptable | Spawn **merge worker** |
| PR merged, more open issues | Spawn **implementation worker** for next issue |
| PR merged, no open issues | Log completion, exit |

## Avoiding Duplicate Work

Before spawning a worker, check if any related conversations are still active. A conversation is **quiet** when its last event timestamp is older than `QUIET_PERIOD` (e.g., 7-15 minutes).

### Using ohtv (Recommended)

Use `ohtv list` with the `--idle` flag to see active vs quiet conversations at a glance:

```bash
# Sync recent conversations (--quiet = minimal output for cron/automation)
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet

# Check conversations for this repo with idle time
# Red = active (< threshold), Green = quiet (>= threshold)
ohtv list --repo voice-relay --since 4h --idle 15
```

Example output:
```
ID      Source  Started          Idle   Events  Title
abc123  cloud   2025-05-02 10:30 3m     42      [Impl] Add semantic search
                                                 Refs: voice-relay#3
def456  cloud   2025-05-02 09:15 47m    28      [Review] PR #2
                                                 Refs: voice-relay#2
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
ohtv list --repo voice-relay --action pushed --idle

# Check specific conversation stats
ohtv show CONV_ID -S
```

### Decision Rule

Only spawn if:
- All conversations show **green** idle time (>= QUIET_PERIOD)
- OR no conversations found for this repo in the lookback window

## Production Deployment Context

**CRITICAL:** The application auto-deploys to **vr.chorecraft.net** on every merge to main.

- **Current production database:** SQLite (`sqlite.db`)
- **Target:** SQLite (dev) / MariaDB (prod) - but SQLite is live NOW
- **Migrations are essential:** Every schema change must include migrations that work on the existing SQLite database
- **No breaking changes:** Production must continue working after each merge

**Migration Guidelines:**
1. Use a migration tool (e.g., `knex`, `drizzle-orm`, or raw SQL migration files)
2. Always provide both `up` and `down` migrations
3. Test migrations against a copy of production data before merging
4. Additive changes are safe (new tables, new columns with defaults)
5. Destructive changes require careful planning (column renames, type changes, deletions)

## Spawning Workers

Use `/spawn-conversation` skill to start worker conversations.

### Implementation Worker

```
Repository: jpshackelford/voice-relay
Title: [Implementation] Issue #{issue_number} - {issue_title}
Prompt: |
  You are implementing GitHub Issue #{issue_number} for the voice-relay project.
  
  **ISSUE TO IMPLEMENT:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/voice-relay/issues/{issue_number}
  
  **PRODUCTION CONTEXT:**
  - App auto-deploys to vr.chorecraft.net on merge to main
  - Production currently uses SQLite (sqlite.db)
  - All schema changes MUST include migrations
  - Migrations must be backward-compatible with existing data
  
  1. Read the issue description carefully: gh issue view {issue_number}
  2. Review acceptance criteria in the issue - these define "done"
  3. Create a feature branch from main (ensure main is up-to-date)
  4. Implement the feature with tests (target >80% coverage for new code)
  5. If adding/modifying database schema:
     - Create migration files (up and down)
     - Test migrations work on fresh DB and existing data
  6. Run lints and type checks, fix any issues
  7. Commit with clear messages, push, create a DRAFT PR
  8. Link PR to issue: Include "Fixes #{issue_number}" in PR description
  9. Monitor CI, fix any failures until green
  10. Once CI is green, REFLECT:
      - Are all acceptance criteria from the issue met?
      - Note any learnings or follow-up items
  11. Move PR from draft to ready (triggers review bot)
  12. Exit - review handling is a separate conversation
  
Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
Issue Number: {issue_number}
```

### Review Worker

```
Repository: jpshackelford/voice-relay  
Title: [Review Round] PR #{number} - {title}
Prompt: |
  You are addressing review feedback on PR #{number}.
  
  **PRODUCTION CONTEXT:**
  - App auto-deploys to vr.chorecraft.net on merge to main
  - Production currently uses SQLite (sqlite.db)
  - Verify any migration changes are backward-compatible
  
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
     - Did you learn anything that impacts other issues?
     - If so, add comments to relevant issues
  9. Move PR back to ready: gh pr ready {number}
  10. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
PR Number: {number}
```

### Merge Worker

```
Repository: jpshackelford/voice-relay
Title: [Merge] PR #{number} - {title}
Prompt: |
  You are preparing PR #{number} for merge. Merge criteria has been met.
  
  **PRODUCTION CONTEXT:**
  - App auto-deploys to vr.chorecraft.net on merge to main
  - Production currently uses SQLite (sqlite.db)
  - This merge will immediately affect production
  - Verify migrations are safe before merging
  
  1. Clone the repo and checkout the PR branch
  2. Study the full PR diff holistically - understand what was built
  3. **MIGRATION CHECK:** If this PR includes database changes:
     - Verify migration files exist and are correct
     - Confirm migrations are additive/safe for existing data
     - Note any manual steps needed post-deploy
  4. Read all review history to understand how it evolved
  5. Update PR description to reflect final state:
     - What was implemented
     - Key decisions made during review
     - Any notable technical details
     - **Migration notes** if applicable
  6. Craft a good conventional commit message for squash-merge:
     - feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line
     - Body with relevant details
  7. Squash and merge: gh pr merge {number} --squash --body "commit message"
  8. The linked issue will auto-close if PR description has "Fixes #N"
  9. Verify issue closed; if not, close manually: gh issue close {issue_number}
  10. Exit

Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
PR Number: {number}
```

## WORKLOG.md Updates

After each orchestrator run, append a status update to `WORKLOG.md` in the repo root. This serves as a persistent log of all workflow activity.

### Log Entry Format

Always include:
- Timestamp (UTC)
- Current state summary
- Action taken (if any)
- Links to PRs and conversations

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Current State:**
- [PR #5](https://github.com/jpshackelford/voice-relay/pull/5): `oCR green ready 💬2` (2 unresolved threads)
- Open issues: #9, #10, #11, #12

**Action Taken:**
🚀 Spawned review worker to address feedback
- Conversation: https://app.all-hands.dev/conversations/{conv_id}

**What Changed Since Last Run:**
- PR moved from draft → ready
- CI now passing (was failing)
- 1 review thread resolved

---
```

### When Spawning a Worker

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

🚀 **Launched: Implementation Worker**

Starting work on: Issue #9 - F1: Scope messages to sessions
- No PR yet - will create one
- Issue URL: https://github.com/jpshackelford/voice-relay/issues/9
- Conversation: https://app.all-hands.dev/conversations/{conv_id}

---
```

### When No Action Needed

```markdown
### 2025-05-05 14:30 UTC - Orchestrator

✅ **All quiet** - No action needed

- [PR #5](https://github.com/jpshackelford/voice-relay/pull/5) is in review (waiting for reviewer)
- No active conversations found
- Next check in ~30 minutes

---
```

### When All Issues Closed

```markdown
### 2025-05-05 18:00 UTC - Orchestrator

🎉 **All Issues Complete!**

All tracked issues have been implemented and closed.
- No open issues remaining
- Total PRs merged: 4 (Issues #9, #10, #11, #12)

---
```

### Committing WORKLOG.md Updates

**IMPORTANT:** WORKLOG.md updates MUST go to `main`, not to any feature branch.

```bash
# Save current branch (if on one)
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

# Return to previous branch if there was one
if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
  git checkout "$CURRENT_BRANCH"
  git stash pop 2>/dev/null || true
fi
```

This ensures:
1. WORKLOG.md is always on main (not buried in PR branches)
2. All orchestrator/worker updates are visible immediately
3. Human instructions can be added directly to main

## Logging

After each action, also log to stdout for the conversation record:

```
[Orchestrator] 2025-05-05T10:30:00Z
State: PR #5 - oCR green ready 💬2
Action: Spawned review worker (conversation: abc123)
Reason: 2 unresolved review threads need addressing
Next check: ~30 minutes (next cron trigger)
```

```
[Orchestrator] 2025-05-05T14:00:00Z
State: No open PRs, 3 work items remaining
Action: Spawned implementation worker for "Phase 2: Authentication"
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
