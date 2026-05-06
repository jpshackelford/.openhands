---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate PR Workflow

Main orchestration logic for the voice-relay PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

The project work items are tracked as **GitHub Issues**. Issues go through two phases:

1. **Expansion Phase** - Issues are analyzed, expanded with technical detail, and labeled `ready`
2. **Implementation Phase** - Ready issues are prioritized and implemented one at a time

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **CHECK FOR HUMAN INSTRUCTIONS FIRST** - Read WORKLOG.md for any `## INSTRUCTION:` entries
2. If human instructions exist, follow them before doing anything else
3. **CHECK FOR ACTIVE WORKERS** - Parse WORKLOG.md for running conversations
4. Discovers any open PRs for the repo (there should be 0 or 1 at a time)
5. Lists open GitHub issues by label (`ready` vs needs expansion)
6. Decides what action is needed based on current state
7. Spawns worker conversation(s) if work is available
8. Appends status update to WORKLOG.md on main
9. Exits (next check happens on next cron trigger)

## Parallel Work Model

The orchestrator can run **two workers simultaneously**:

```
┌─────────────────────────────────────────────────────────────────┐
│  PARALLEL WORK SLOTS                                             │
├─────────────────────────────────────────────────────────────────┤
│  SLOT 1: Expansion Worker (0 or 1 active)                       │
│    - Analyzes issues, finds root cause, adds technical detail   │
│    - Only touches issues (labels, comments) - no code changes   │
│                                                                   │
│  SLOT 2: PR Worker (0 or 1 active)                              │
│    - Implementation, Review, or Merge worker                     │
│    - Touches code, branches, PRs - must be serialized           │
│                                                                   │
│  ✅ Both slots can be filled simultaneously                      │
│  ❌ Cannot have 2 expansion workers                              │
│  ❌ Cannot have 2 PR workers                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  0. SETUP: Install tools (lxa, ohtv)                            │
│  0.5. HOUSEKEEPING: Truncate worklog if large (>300 lines)      │
│  1. READ WORKLOG.md for human instructions (FIRST!)             │
│  2. If human instructions found → follow them, then exit        │
│  3. PARSE WORKLOG.md for active workers (by conv ID)            │
│  4. CHECK which workers are still running (API query)           │
│  5. GATHER STATE:                                                │
│     - Open PRs (lxa pr list)                                    │
│     - Issues by label: ready, needs-triage, priority:*          │
│  6. DECIDE what to spawn (see Decision Tree)                    │
│  7. SPAWN worker(s) if slots available and work exists          │
│  8. UPDATE WORKLOG.md with current state                        │
│  9. EXIT                                                         │
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

## Step 0.5: Housekeeping - Truncate Worklog

If the worklog is getting large, archive old entries to keep the file manageable and ensure agents have focused context on recent productive work.

```bash
# Only run truncation if WORKLOG.md is large (>300 lines)
WORKLOG_LINES=$(wc -l < WORKLOG.md 2>/dev/null || echo 0)
if [ "$WORKLOG_LINES" -gt 300 ]; then
  echo "📦 WORKLOG.md has $WORKLOG_LINES lines - running truncation"
  
  # Run the truncation script (see /truncate-worklog skill for full implementation)
  python3 << 'TRUNCATE_SCRIPT'
import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def is_productive(content):
    """Determine if entry represents productive work (not just status checks)."""
    productive = ['🚀 **Launched:', '🚀 **Spawned:', '✅ **Completed:', '✅ **Merged:',
                  '✅ **Expanded', '✅ **Addressed', '✅ **Created:', '📋 **Following',
                  '🔒 **Auto-disabled']
    status = ['⏳ **Waiting**', '✅ **All quiet**', 'Action Taken: None', 'Action Taken:\nNone']
    
    for s in status:
        if s in content:
            return False
    for p in productive:
        if p in content:
            return True
    return False

def truncate_worklog(repo_path="."):
    worklog_path = os.path.join(repo_path, "WORKLOG.md")
    with open(worklog_path, 'r') as f:
        content = f.read()
    
    parts = re.split(r'(^## Log$)', content, maxsplit=1, flags=re.MULTILINE)
    if len(parts) < 3:
        return
    
    header = parts[0] + parts[1]
    entries_section = parts[2]
    
    entries = []
    for raw in re.split(r'\n---\n', entries_section):
        raw = raw.strip()
        if not raw:
            continue
        match = re.match(r'^### (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC', raw)
        if not match:
            continue
        date_str, time_str = match.groups()
        ts = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        entries.append({'timestamp': ts, 'date': date_str, 'content': raw, 'productive': is_productive(raw)})
    
    if not entries:
        return
    
    # Calculate cutoff: keep entries spanning 6 hours of productive work
    productive = sorted([e for e in entries if e['productive']], key=lambda e: e['timestamp'], reverse=True)
    if not productive:
        return  # Keep everything if no productive work
    
    newest, oldest_in_window = productive[0]['timestamp'], productive[0]['timestamp']
    for e in productive:
        oldest_in_window = e['timestamp']
        if newest - oldest_in_window >= timedelta(hours=6):
            break
    
    to_keep = [e for e in entries if e['timestamp'] >= oldest_in_window]
    to_archive = [e for e in entries if e['timestamp'] < oldest_in_window]
    
    if not to_archive:
        print("✅ Nothing to archive")
        return
    
    # Archive old entries by date
    by_date = defaultdict(list)
    for e in to_archive:
        by_date[e['date']].append(e)
    
    for date, date_entries in sorted(by_date.items()):
        date_entries.sort(key=lambda e: e['timestamp'])
        archive_file = os.path.join(repo_path, f"WORKLOG_ARCHIVE_{date}.md")
        archive_content = "\n\n---\n".join(e['content'] for e in date_entries)
        
        if os.path.exists(archive_file):
            with open(archive_file, 'a') as f:
                f.write(f"\n\n---\n{archive_content}")
        else:
            with open(archive_file, 'w') as f:
                f.write(f"# Voice Relay Worklog Archive - {date}\n\nArchived entries from WORKLOG.md.\n\n---\n\n{archive_content}")
        print(f"📦 Archived {len(date_entries)} entries to WORKLOG_ARCHIVE_{date}.md")
    
    # Rewrite WORKLOG.md
    to_keep.sort(key=lambda e: e['timestamp'])
    new_content = f"{header}\n\n" + "\n\n---\n".join(e['content'] for e in to_keep) + "\n"
    with open(worklog_path, 'w') as f:
        f.write(new_content)
    print(f"✅ WORKLOG.md updated - kept {len(to_keep)} entries")

truncate_worklog(".")
TRUNCATE_SCRIPT

  # Commit archived files if any were created
  if git status --porcelain | grep -q "WORKLOG"; then
    git add WORKLOG.md WORKLOG_ARCHIVE_*.md 2>/dev/null || true
    git commit -m "chore: archive worklog entries older than 6hr productive window" || true
    git push origin main || true
  fi
fi
```

### What Gets Archived

The truncation preserves **at least 6 hours of productive work context**:

| Entry Type | Counts Toward 6hr Span? | Examples |
|------------|------------------------|----------|
| **Productive** | ✅ Yes | `🚀 Launched`, `✅ Merged`, `✅ Completed` |
| **Status** | ❌ No | `⏳ Waiting`, `All quiet` |

This ensures:
- Agents have meaningful context about recent work
- Quiet periods don't result in an empty worklog
- The file stays manageable (<300 lines typically)

See `/truncate-worklog` skill for the full algorithm and edge case handling.

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

## Step 2: Check for Active Workers

Parse WORKLOG.md to find recently spawned workers, then verify if they're still running.

### Extract Worker Info from WORKLOG.md

Look for recent spawn entries with conversation IDs:

```bash
# Get last 100 lines, find spawn entries with conv IDs
# Format in WORKLOG: | `abc1234` | expansion | Issue #9 - Title | timestamp |
grep -E "^\| \`[a-f0-9]{7}\` \|" WORKLOG.md | tail -10
```

Or look for the "Active Workers" table format:

```bash
# Extract conv IDs and types from recent entries
grep -A10 "Active Workers:" WORKLOG.md | tail -15
```

### Check if Conversations are Still Running

For each conversation ID found, query the API:

```bash
# Check conversation status by ID prefix
conv_id="abc1234"
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=50" \
  -H "Authorization: Bearer ${OH_API_KEY}" \
| jq -r ".items[] | select(.id | startswith(\"$conv_id\")) | {id: .id[0:7], status: .execution_status, title: .title}"
```

**Status values:**
- `running` = worker is active, don't spawn duplicate
- `finished` = worker completed
- `error` / `stuck` = worker failed (may need attention)

### Determine Available Slots

```bash
# Pseudo-code for slot availability
ACTIVE_EXPANSION=false
ACTIVE_PR_WORKER=false

for each spawned_worker in WORKLOG.md (last 4 hours):
    status = query_api(worker.conv_id)
    if status == "running":
        if worker.type == "expansion":
            ACTIVE_EXPANSION=true
        else:  # implementation, review, merge
            ACTIVE_PR_WORKER=true

CAN_SPAWN_EXPANSION = !ACTIVE_EXPANSION
CAN_SPAWN_PR_WORKER = !ACTIVE_PR_WORKER
```

## Gather State

Use `gh` to discover PRs and issues by label:

```bash
# 1. Discover open PRs (usually 0 or 1)
gh pr list --repo jpshackelford/voice-relay --state open --json number,title,isDraft
# Output: [{"number": 3, "title": "Add semantic search", "isDraft": false}]

# 2. If a PR exists, get quick status with lxa
lxa pr list "jpshackelford/voice-relay#3"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. List issues needing expansion (no 'ready' label)
gh issue list --repo jpshackelford/voice-relay --state open --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | contains(["ready"]) | not)] | sort_by(.number)'
# Issues without 'ready' label need expansion

# 4. List ready issues (have 'ready' label)
gh issue list --repo jpshackelford/voice-relay --state open --label "ready" --json number,title,labels \
  --jq 'sort_by(.number)'

# 5. Check for prioritized ready issues
gh issue list --repo jpshackelford/voice-relay --state open --label "ready" --json number,title,labels \
  --jq '[.[] | {number, title, priority: (.labels | map(.name) | map(select(startswith("priority:"))) | .[0])}]'
```

### Issue Categories

| Category | Label State | What to Do |
|----------|-------------|------------|
| Needs expansion | No `ready` label | Spawn expansion worker |
| Ready, unprioritized | `ready` but no `priority:*` | Run `/assess-priority` inline |
| Ready, prioritized | `ready` + `priority:*` | Spawn implementation worker for highest priority |
| Blocked | Has `blocked` label | Skip until unblocked |
| Needs info | Has `needs-info` label | Skip until reporter responds |

## Decision Tree

### Expansion Slot (can run parallel to PR work)

| Condition | Action |
|-----------|--------|
| `CAN_SPAWN_EXPANSION` + issues need expansion | Spawn **expansion worker** for oldest unexpanded issue |
| `CAN_SPAWN_EXPANSION` + no issues need expansion | Slot idle (all issues expanded) |
| `!CAN_SPAWN_EXPANSION` | Wait (expansion worker running) |

### PR Slot (Implementation → Review → Merge)

| Condition | Action |
|-----------|--------|
| `!CAN_SPAWN_PR_WORKER` | Wait (PR worker running) |
| PR exists, draft, CI failing | Wait (impl worker may still be active) |
| PR exists, draft, CI green | Wait (impl worker finishing up) |
| PR exists, ready, no reviews yet | Wait (review bot running) |
| PR exists, ready, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, 💬 = 0, merge criteria met | Spawn **merge worker** |
| No open PR + ready issues with priority | Spawn **impl worker** for highest priority ready issue |
| No open PR + ready issues, no priority | Run `/assess-priority` inline, then spawn impl worker |
| No open PR + no ready issues | Nothing to implement (wait for expansion) |

### Combined Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  DECISION FLOW                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK EXPANSION SLOT                                         │
│     ├─ Active expansion worker? → Skip to PR slot               │
│     └─ Issues need expansion?                                    │
│         ├─ YES → Spawn expansion worker (oldest issue)          │
│         └─ NO  → Expansion slot idle                            │
│                                                                  │
│  2. CHECK PR SLOT                                                │
│     ├─ Active PR worker? → Log status, exit                     │
│     └─ Open PR exists?                                          │
│         ├─ YES → Handle PR state (wait/review/merge)            │
│         └─ NO  → Ready issues exist?                            │
│                   ├─ YES → Prioritized?                         │
│                   │         ├─ YES → Spawn impl (highest prio)  │
│                   │         └─ NO  → /assess-priority, spawn    │
│                   └─ NO  → Nothing to implement                 │
│                                                                  │
│  3. LOG STATUS TO WORKLOG.md                                    │
│                                                                  │
│  4. EXIT                                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Avoiding Duplicate Work

The orchestrator tracks active workers via **WORKLOG.md** entries. Each spawn is logged with a 7-character conversation ID prefix, worker type, and what it's working on.

### Primary Method: WORKLOG.md Tracking

When spawning a worker, log it in this format:

```markdown
**Active Workers:**
| Conv ID | Type | Working On | Started |
|---------|------|------------|---------|
| `abc1234` | expansion | Issue #9 - Scope messages | 14:00 UTC |
| `def5678` | implementation | Issue #7 - WebSocket | 13:15 UTC |
```

To check if a worker is still running:

```bash
# 1. Extract recent conv IDs from WORKLOG.md
CONV_IDS=$(grep -oE '\`[a-f0-9]{7}\`' WORKLOG.md | tr -d '`' | tail -10 | sort -u)

# 2. Query API for each
for cid in $CONV_IDS; do
  curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=50" \
    -H "Authorization: Bearer ${OH_API_KEY}" \
  | jq -r ".items[] | select(.id | startswith(\"$cid\")) | \"\(.id[0:7]) \(.execution_status)\""
done
```

### Backup Method: ohtv (Optional)

Use `ohtv` for additional visibility, especially to verify what issues/PRs a conversation touched:

```bash
# Sync recent conversations
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet

# Check conversations for this repo with idle time
ohtv list --repo voice-relay --since 4h --idle 15

# See what a conversation referenced (issues, PRs)
ohtv refs CONV_ID

# Generate object references (requires LLM)
ohtv gen objs -D
```

### Decision Rules

**For Expansion Slot:**
- Only spawn if no `expansion` type worker shows `running` status

**For PR Slot:**
- Only spawn if no `implementation`, `review`, or `merge` type worker shows `running` status

**Both slots can be filled simultaneously** - an expansion worker and a PR worker can run in parallel.

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

### Expansion Worker (NEW)

**Worker Type:** `expansion`
**Slot:** Expansion slot (can run parallel to PR workers)

```
Repository: jpshackelford/voice-relay
Title: [Expansion] Issue #{issue_number} - {issue_title}
Prompt: |
  You are expanding GitHub Issue #{issue_number} for the voice-relay project.
  
  **ISSUE TO EXPAND:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/voice-relay/issues/{issue_number}
  
  Your job is to analyze this issue and add technical detail so it's ready for implementation.
  
  **FOR BUG REPORTS:**
  1. Clone the repo and set up the environment
  2. Attempt to reproduce the bug
  3. If reproducible, investigate code to find root cause
  4. Rewrite issue body with: Problem, Steps to Reproduce, Expected/Actual behavior
  5. Add comment with: Root Cause Analysis, Proposed Fix, Files to modify
  
  **FOR ENHANCEMENTS:**
  1. Understand the user need / pain point
  2. Explore codebase to understand current architecture
  3. Rewrite issue body with: Problem Statement, Proposed Solution, Acceptance Criteria
  4. Add comment with: Technical Approach, Implementation Plan, Files affected
  
  **WHEN DONE:**
  1. Add `ready` label: gh issue edit {issue_number} --add-label ready
  2. Update WORKLOG.md on main with completion status
  3. Exit
  
  **IF BLOCKED:**
  - Can't reproduce bug → Add `needs-info` label, comment with questions
  - Too vague → Add `needs-info` label, ask for clarification
  - Should be split → Add `needs-split` label, suggest breakdown
  - Do NOT add `ready` label if blocked
  
  See /expand-issue skill for detailed guidance.
  
Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
Issue Number: {issue_number}
Worker Type: expansion
```

### Implementation Worker

**Worker Type:** `implementation`
**Slot:** PR slot (serialized with review/merge)

```
Repository: jpshackelford/voice-relay
Title: [Implementation] Issue #{issue_number} - {issue_title}
Prompt: |
  You are implementing GitHub Issue #{issue_number} for the voice-relay project.
  
  **ISSUE TO IMPLEMENT:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/voice-relay/issues/{issue_number}
  - Priority: {priority_label}
  
  This issue has already been expanded with technical detail. Read the issue 
  description AND comments for the implementation approach.
  
  **PRODUCTION CONTEXT:**
  - App auto-deploys to vr.chorecraft.net on merge to main
  - Production currently uses SQLite (sqlite.db)
  - All schema changes MUST include migrations
  - Migrations must be backward-compatible with existing data
  
  1. Read the issue description AND comments: gh issue view {issue_number} --comments
  2. The technical approach comment tells you what to build
  3. Create a feature branch from main (ensure main is up-to-date)
  4. Implement following the approach in the issue comments
  5. Write tests (target >80% coverage for new code)
  6. If adding/modifying database schema:
     - Create migration files (up and down)
     - Test migrations work on fresh DB and existing data
  7. Run lints and type checks, fix any issues
  8. Commit with clear messages, push, create a DRAFT PR
  9. Link PR to issue: Include "Fixes #{issue_number}" in PR description
  10. Monitor CI, fix any failures until green
  11. Once CI is green, REFLECT:
      - Are all acceptance criteria from the issue met?
      - Note any learnings or follow-up items
  12. Move PR from draft to ready (triggers review bot)
  13. Update WORKLOG.md on main with PR link
  14. Exit - review handling is a separate conversation
  
Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
Issue Number: {issue_number}
Worker Type: implementation
```

### Review Worker

**Worker Type:** `review`
**Slot:** PR slot (serialized with implementation/merge)

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
  10. Update WORKLOG.md on main with status
  11. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/voice-relay-workflow@add-voice-relay-workflow-plugin
PR Number: {number}
Worker Type: review
```

### Merge Worker

**Worker Type:** `merge`
**Slot:** PR slot (serialized with implementation/review)

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

After each orchestrator run, append a status update to `WORKLOG.md` in the repo root. This serves as:
1. **Persistent log** of all workflow activity
2. **Worker tracking** - conversation IDs and what they're doing
3. **Human visibility** - anyone can see what's happening

### Standard Log Entry Format

Always include the **Active Workers** table so we can track running conversations:

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #10 - QR code flow | running |
| `def5678` | implementation | Issue #9 - Scope messages | running |

**Current State:**
- [PR #5](https://github.com/jpshackelford/voice-relay/pull/5): `oCR green ready 💬2`
- Issues needing expansion: #11, #12
- Ready issues: #9 (priority:high), #10 (priority:medium)

**Action Taken:**
✅ Both worker slots occupied - no action needed

---
```

### When Spawning a Worker

Include the conversation ID (first 7 chars) in the Active Workers table:

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `ghi9012` | expansion | Issue #11 - Session View | **NEW** |

**Spawned: Expansion Worker**
- Issue: [#11 - Session View](https://github.com/jpshackelford/voice-relay/issues/11)
- Conversation: [`ghi9012`](https://app.all-hands.dev/conversations/ghi9012...)

**Current State:**
- No open PRs
- Ready issues: #9, #10 (awaiting implementation)
- Issues needing expansion: #11 (now being expanded), #12

---
```

### When Spawning Multiple Workers (Parallel)

```markdown
### 2025-05-05 14:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #12 - Join via QR | **NEW** |
| `def5678` | implementation | Issue #9 - Scope messages | **NEW** |

**Spawned: 2 Workers (parallel)**

1. **Expansion Worker**
   - Issue: [#12 - Join via QR](https://github.com/jpshackelford/voice-relay/issues/12)
   - Conversation: [`abc1234`](https://app.all-hands.dev/conversations/abc1234...)

2. **Implementation Worker**  
   - Issue: [#9 - Scope messages](https://github.com/jpshackelford/voice-relay/issues/9) (priority:high)
   - Conversation: [`def5678`](https://app.all-hands.dev/conversations/def5678...)

---
```

### When Workers Complete

Update status when checking workers:

```markdown
### 2025-05-05 15:00 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #12 | finished ✓ |
| `def5678` | implementation | Issue #9 | running |

**Worker Completed:** `abc1234` (expansion)
- Issue #12 now has `ready` label

**Current State:**
- PR #6 in progress (Issue #9)
- Ready issues: #10, #12
- No issues need expansion 🎉

---
```

### When No Action Needed

```markdown
### 2025-05-05 15:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `def5678` | implementation | Issue #9 | running |

✅ **All quiet** - PR slot occupied, expansion slot empty (nothing to expand)

- [PR #6](https://github.com/jpshackelford/voice-relay/pull/6) in progress
- All issues expanded
- Next check in ~30 minutes

---
```

### When All Issues Closed

```markdown
### 2025-05-05 18:00 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| (none) | - | - | - |

🎉 **All Issues Complete!**

All tracked issues have been implemented and closed.
- No open issues remaining
- Total PRs merged: 4 (Issues #9, #10, #11, #12)

---
```

## Auto-Disable on Consecutive Quiet Periods

**CRITICAL:** Before logging a "quiet" entry, check if WORKLOG.md already shows two consecutive quiet entries. If so, disable the automation instead of running indefinitely.

### Automation ID

This orchestrator's automation ID is:
```
a0219382-2e7c-4156-9991-7b9976739a66
```

### Detection Logic

Check WORKLOG.md for consecutive quiet entries:

```bash
# Extract last few orchestrator entries and check for consecutive "All quiet" patterns
# Look for entries that contain both the Orchestrator header and "All quiet"
QUIET_COUNT=$(tail -100 WORKLOG.md | grep -B2 "All quiet" | grep -c "Orchestrator" || echo 0)

# If 2 or more consecutive quiet entries exist, this would be the 3rd - disable instead
if [ "$QUIET_COUNT" -ge 2 ]; then
  echo "Two consecutive quiet periods detected - disabling automation"
fi
```

Alternative check using the most recent entries:

```bash
# Get the last 2 orchestrator log entries
LAST_ENTRIES=$(grep -E "(^### .*Orchestrator|All quiet)" WORKLOG.md | tail -4)

# Check if both recent orchestrator entries were quiet
if echo "$LAST_ENTRIES" | grep -q "All quiet" && \
   [ $(echo "$LAST_ENTRIES" | grep -c "All quiet") -ge 2 ]; then
  echo "Auto-disable triggered: two consecutive quiet periods"
fi
```

### How to Disable

When two consecutive quiet periods are detected:

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/a0219382-2e7c-4156-9991-7b9976739a66" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### WORKLOG Entry When Disabling

```markdown
### {timestamp} - Orchestrator

🔒 **Auto-disabled due to inactivity**

Two consecutive quiet periods detected - no new work to pick up.
Automation has been disabled to prevent unnecessary runs.

**To re-enable:**
- OpenHands UI: https://app.all-hands.dev/automations → Find "Voice Relay Workflow Orchestrator" → Toggle enable
- Or via API:
  ```bash
  curl -X PATCH "https://app.all-hands.dev/api/automation/v1/a0219382-2e7c-4156-9991-7b9976739a66" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"enabled": true}'
  ```

---
```

### Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Before logging "All quiet":                                     │
├─────────────────────────────────────────────────────────────────┤
│  1. Check: Are there 2+ consecutive "All quiet" entries?        │
│     └─ YES → DISABLE automation + log disable message + EXIT    │
│     └─ NO  → Log normal "All quiet" entry + EXIT                │
└─────────────────────────────────────────────────────────────────┘
```

See [Disable Automation Skill](disable-automation.md) for complete details.

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
