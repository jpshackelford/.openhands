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

The orchestrator can run **up to 7 workers simultaneously** across three slot types:

```
┌─────────────────────────────────────────────────────────────────┐
│  PARALLEL WORK SLOTS (max 7 concurrent conversations)           │
├─────────────────────────────────────────────────────────────────┤
│  EXPANSION SLOTS (0-4 active)                                   │
│    - Analyzes issues, finds root cause, adds technical detail   │
│    - Only touches issues (labels, comments) - no code changes   │
│    - Can run up to 4 in parallel                                │
│                                                                   │
│  IMPLEMENTATION SLOT (0-1 active)                               │
│    - Implements the next priority issue                         │
│    - Creates branch, writes code, opens PR                      │
│    - Only 1 at a time to avoid branch conflicts                 │
│                                                                   │
│  REVIEW SLOTS (0-2 active)                                      │
│    - Addresses review feedback on open PRs                      │
│    - Fixes CI failures                                          │
│    - Can work on up to 2 PRs simultaneously                     │
│                                                                   │
│  ✅ All slot types can run in parallel                          │
│  ✅ Implementation not blocked by review cycle                  │
│  ✅ Multiple issues can be expanded simultaneously              │
└─────────────────────────────────────────────────────────────────┘
```

### Slot Limits

| Slot Type | Max Active | Purpose |
|-----------|------------|---------|
| Expansion | 4 | Analyze and expand issues in parallel |
| Implementation | 1 | Implement one issue at a time (avoids conflicts) |
| Review | 2 | Address PR feedback / fix CI on multiple PRs |

**Total max: 7 concurrent conversations**

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  0. SETUP: Install tools (lxa, ohtv)                            │
│  0.5. HOUSEKEEPING: Truncate worklog if large (>300 lines)      │
│  1. READ WORKLOG.md for human instructions (FIRST!)             │
│  2. If human instructions found → follow them, then exit        │
│  3. LOAD .workflow-state.json for active workers                │
│  4. CHECK which workers are still running (API query)           │
│  4.5. UPDATE .workflow-state.json (remove finished workers)     │
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

Load `.workflow-state.json` and verify which workers are still running via API.

### State File Structure

The orchestrator uses `.workflow-state.json` to track active and completed conversations:

```json
{
  "version": 2,
  "slots": {
    "expansion": [
      {"conv_id": "abc1234", "issue": 9, "started": "2025-05-17T18:00:00Z"}
    ],
    "implementation": [
      {"conv_id": "def5678", "issue": 12, "started": "2025-05-17T17:30:00Z"}
    ],
    "review": [
      {"conv_id": "ghi9012", "pr": 42, "started": "2025-05-17T17:45:00Z"}
    ]
  },
  "limits": {
    "expansion": 4,
    "implementation": 1,
    "review": 2
  },
  "completed": [
    {
      "conv_id": "xyz7890",
      "type": "expansion",
      "issue": 8,
      "started": "2025-05-17T16:00:00Z",
      "finished": "2025-05-17T16:25:00Z",
      "status": "success",
      "outcome": "Added ready label, posted analysis comment"
    },
    {
      "conv_id": "uvw4567",
      "type": "implementation",
      "issue": 7,
      "started": "2025-05-17T14:00:00Z",
      "finished": "2025-05-17T15:30:00Z",
      "status": "success",
      "outcome": "Created PR #45"
    }
  ],
  "last_updated": "2025-05-17T18:15:00Z"
}
```

**Schema v2 additions:**
- `completed[]` - Array of recently completed workers (last 24 hours) for audit trail
- Each completed entry includes: `type`, `finished`, `status` (success/failed/stuck), `outcome`

**Why track completed workers?**
- Debug issues when workers are respawned unexpectedly
- Verify work was actually done (not just slots cleared)
- Audit trail for orchestrator decisions

### Load and Validate State

```bash
# Load state file (create if missing, or migrate from v1)
STATE_FILE=".workflow-state.json"
if [ ! -f "$STATE_FILE" ]; then
  echo '{"version":2,"slots":{"expansion":[],"implementation":[],"review":[]},"limits":{"expansion":4,"implementation":1,"review":2},"completed":[],"last_updated":null}' > "$STATE_FILE"
elif [ "$(jq -r '.version' "$STATE_FILE")" = "1" ]; then
  # Migrate v1 to v2: add completed array
  jq '. + {version: 2, completed: []}' "$STATE_FILE" > "$STATE_FILE.tmp" && mv "$STATE_FILE.tmp" "$STATE_FILE"
  echo "Migrated .workflow-state.json from v1 to v2"
fi

# Parse current slots
EXPANSION_WORKERS=$(jq -r '.slots.expansion | length' "$STATE_FILE")
IMPL_WORKERS=$(jq -r '.slots.implementation | length' "$STATE_FILE")
REVIEW_WORKERS=$(jq -r '.slots.review | length' "$STATE_FILE")

echo "Current workers: expansion=$EXPANSION_WORKERS, impl=$IMPL_WORKERS, review=$REVIEW_WORKERS"
```

### Check if Conversations are Still Running

For each conversation ID in state, query the API to check status:

```bash
# Check conversation status by ID prefix
check_conv_status() {
  local conv_id="$1"
  curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=50" \
    -H "Authorization: Bearer ${OH_API_KEY}" \
  | jq -r ".items[] | select(.id | startswith(\"$conv_id\")) | .execution_status" \
  | head -1
}

# Example: check_conv_status "abc1234" → "running" or "finished"
```

**Status values:**
- `running` = worker is active, don't spawn duplicate
- `finished` = worker completed, remove from state
- `error` / `stuck` = worker failed (may need attention)

### Update State - Move Finished Workers to Completed

When workers finish, move them to the `completed` array (not just remove them). This creates an audit trail.

```python
#!/usr/bin/env python3
import json
import subprocess
import os
from datetime import datetime, timezone, timedelta

STATE_FILE = ".workflow-state.json"
OH_API_KEY = os.environ.get("OH_API_KEY")

def check_conv_status(conv_id):
    """Query API for conversation status and title."""
    result = subprocess.run([
        "curl", "-s", 
        f"https://app.all-hands.dev/api/v1/app-conversations/search?limit=50",
        "-H", f"Authorization: Bearer {OH_API_KEY}"
    ], capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        for item in data.get("items", []):
            if item["id"].startswith(conv_id):
                return {
                    "status": item.get("execution_status", "unknown"),
                    "title": item.get("title", ""),
                }
    except:
        pass
    return {"status": "unknown", "title": ""}

def infer_outcome(slot_type, conv_info):
    """Infer what the worker accomplished based on type and title."""
    title = conv_info.get("title", "")
    if slot_type == "expansion":
        return "Added ready label, posted analysis comment"
    elif slot_type == "implementation":
        if "PR #" in title:
            return title
        return "Created PR (check GitHub for details)"
    elif slot_type == "review":
        return "Addressed review feedback"
    return "Completed"

def update_state():
    """Move finished workers from slots to completed array."""
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    
    # Ensure v2 schema
    if "completed" not in state:
        state["completed"] = []
    
    now = datetime.now(timezone.utc)
    updated = False
    
    for slot_type in ["expansion", "implementation", "review"]:
        active = []
        for worker in state["slots"][slot_type]:
            conv_info = check_conv_status(worker["conv_id"])
            status = conv_info["status"]
            
            if status == "running":
                active.append(worker)
            else:
                # Move to completed array with full details
                completed_entry = {
                    "conv_id": worker["conv_id"],
                    "type": slot_type,
                    "issue": worker.get("issue"),
                    "pr": worker.get("pr"),
                    "started": worker["started"],
                    "finished": now.isoformat(),
                    "status": "success" if status == "finished" else status,
                    "outcome": infer_outcome(slot_type, conv_info)
                }
                # Remove None values
                completed_entry = {k: v for k, v in completed_entry.items() if v is not None}
                state["completed"].append(completed_entry)
                print(f"✓ {slot_type} worker {worker['conv_id']} → completed ({status})")
                updated = True
        
        state["slots"][slot_type] = active
    
    # Prune completed entries older than 24 hours
    cutoff = now - timedelta(hours=24)
    state["completed"] = [
        c for c in state["completed"]
        if datetime.fromisoformat(c["finished"].replace("Z", "+00:00")) > cutoff
    ]
    
    if updated or state.get("version") != 2:
        state["version"] = 2
        state["last_updated"] = now.isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    return state

state = update_state()
print(f"Active: expansion={len(state['slots']['expansion'])}, "
      f"impl={len(state['slots']['implementation'])}, "
      f"review={len(state['slots']['review'])}")
print(f"Recently completed: {len(state['completed'])} workers (last 24h)")
```

### Determine Available Slots

```python
# After updating state, check available slots
LIMITS = state["limits"]
SLOTS = state["slots"]

CAN_SPAWN_EXPANSION = len(SLOTS["expansion"]) < LIMITS["expansion"]
CAN_SPAWN_IMPL = len(SLOTS["implementation"]) < LIMITS["implementation"]
CAN_SPAWN_REVIEW = len(SLOTS["review"]) < LIMITS["review"]

EXPANSION_AVAILABLE = LIMITS["expansion"] - len(SLOTS["expansion"])  # 0-4
IMPL_AVAILABLE = LIMITS["implementation"] - len(SLOTS["implementation"])  # 0-1
REVIEW_AVAILABLE = LIMITS["review"] - len(SLOTS["review"])  # 0-2

print(f"Available slots: expansion={EXPANSION_AVAILABLE}, impl={IMPL_AVAILABLE}, review={REVIEW_AVAILABLE}")
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

## Handling Stuck PRs Requiring Human Intervention

**CRITICAL:** When a PR cannot progress without human intervention, the orchestrator should NOT become idle. Instead, it should continue working on other issues to maintain productivity.

### Stuck PR Indicators

A PR is considered "stuck" and requiring human intervention when:

| Indicator | Detection Method | How to Handle |
|-----------|------------------|---------------|
| PR has `blocked` label | `gh pr view --json labels` | Add `needs-human` label, move to next issue |
| PR has `needs-human` label | `gh pr view --json labels` | Skip PR, work on other issues |
| Multiple consecutive failed review rounds | Check WORKLOG.md for repeated review failures on same PR | Mark with `needs-human`, proceed to other work |
| CI consistently failing with infrastructure issues | Check workflow conclusions | Add `needs-human` label if not code-related |
| Merge conflicts that can't be auto-resolved | Check PR mergeable status | Add `needs-human` label, move to next issue |

### Detection Logic

```bash
# Check if current PR is stuck/needs human intervention
PR_LABELS=$(gh pr view --repo jpshackelford/voice-relay --json labels -q '.labels[].name')

IS_STUCK=false
if echo "$PR_LABELS" | grep -qE "(blocked|needs-human|needs-info)"; then
  IS_STUCK=true
fi

# Also check for repeated review failures (same PR, multiple rounds without progress)
REVIEW_ATTEMPTS=$(grep -c "Review Round.*PR #$PR_NUMBER" WORKLOG.md 2>/dev/null || echo 0)
if [ "$REVIEW_ATTEMPTS" -ge 3 ]; then
  # Check if last 3 were all failures or no progress
  RECENT_PROGRESS=$(tail -50 WORKLOG.md | grep -c "✅.*PR #$PR_NUMBER")
  if [ "$RECENT_PROGRESS" -eq 0 ]; then
    IS_STUCK=true
    # Add needs-human label
    gh pr edit $PR_NUMBER --add-label "needs-human"
  fi
fi
```

### When a PR is Stuck: Work on Other Issues

**If a PR is stuck but other ready issues exist:**

1. **Do NOT wait** for the stuck PR to be unblocked
2. **Continue expansion work** if issues need expansion (expansion slot)
3. **Start a new implementation** for the next priority issue (PR slot)
   - This creates a second open PR, which is acceptable when the first is stuck
4. **Log clearly** in WORKLOG.md that the stuck PR is being deferred

```markdown
### 2025-05-05 16:00 UTC - Orchestrator

**Stuck PR Deferred:**
- [PR #5](https://github.com/jpshackelford/voice-relay/pull/5) - blocked: `needs-human` label
- Reason: Requires manual conflict resolution
- Deferred until human resolves the issue

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `xyz7890` | implementation | Issue #10 - Dashboard redesign | **NEW** |

**Action Taken:**
🚀 **Spawned implementation worker** for Issue #10 (next priority)
- Stuck PR #5 bypassed - work continues on Issue #10

---
```

### Decision Priority for Stuck PRs

```
┌─────────────────────────────────────────────────────────────────┐
│  STUCK PR HANDLING                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK: Is current PR stuck?                                 │
│     ├─ Has blocked/needs-human/needs-info label                 │
│     ├─ Multiple failed review rounds without progress           │
│     ├─ Unresolvable merge conflicts                             │
│     └─ Infrastructure CI failures                               │
│                                                                  │
│  2. IF STUCK:                                                   │
│     ├─ Add `needs-human` label (if not already present)         │
│     ├─ Log deferral in WORKLOG.md                               │
│     └─ Treat PR slot as AVAILABLE for next issue                │
│                                                                  │
│  3. CONTINUE WORK:                                              │
│     ├─ If other ready+prioritized issues exist → Spawn impl    │
│     ├─ If issues need expansion → Spawn expansion worker        │
│     └─ If ALL issues depend on stuck PR → Log + wait            │
│                                                                  │
│  4. ONLY STOP WORK WHEN:                                        │
│     └─ ALL remaining issues are blocked by the stuck PR         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Detection

Before starting work on another issue, check if it depends on the stuck PR:

```bash
# Check if an issue mentions the stuck PR or its issue number
STUCK_PR_ISSUE=$(gh pr view $STUCK_PR_NUMBER --json body -q '.body' | grep -oP 'Fixes #\K\d+' | head -1)

for issue_num in $READY_ISSUES; do
  # Check if issue body/comments reference the stuck PR's issue
  ISSUE_BODY=$(gh issue view $issue_num --comments)
  
  if echo "$ISSUE_BODY" | grep -qE "(depends on|blocked by|after).*(#$STUCK_PR_ISSUE|PR #$STUCK_PR_NUMBER)"; then
    echo "Issue #$issue_num depends on stuck PR - skipping"
    continue
  fi
  
  # This issue is independent - can be worked on
  echo "Issue #$issue_num is independent - can proceed"
  break
done
```

### WORKLOG Entry When All Work is Blocked

Only if ALL remaining issues depend on the stuck PR should work stop:

```markdown
### 2025-05-05 17:00 UTC - Orchestrator

**⚠️ All Work Blocked**

All remaining issues depend on stuck PR #5 which requires human intervention.

**Stuck PR:**
- [PR #5](https://github.com/jpshackelford/voice-relay/pull/5) - `needs-human` label
- Blocking issues: #10, #11, #12 (all depend on session architecture from PR #5)

**Waiting for human to:**
1. Resolve merge conflicts in PR #5
2. Or close PR #5 and re-prioritize remaining issues

**No action taken** - automation will continue checking but cannot progress.

---
```

### Key Principle

**Maximize productivity:** The orchestrator should always be doing useful work when possible. A single stuck PR should never halt progress on independent issues. Only when ALL issues are genuinely blocked should the orchestrator wait.

## Decision Tree

### Expansion Slots (up to 4 parallel)

| Condition | Action |
|-----------|--------|
| `EXPANSION_AVAILABLE > 0` + issues need expansion | Spawn expansion worker(s) for oldest unexpanded issues (up to available slots) |
| `EXPANSION_AVAILABLE > 0` + no issues need expansion | Slots idle (all issues expanded) |
| `EXPANSION_AVAILABLE = 0` | All 4 expansion slots full, wait |

### Implementation Slot (1 max)

| Condition | Action |
|-----------|--------|
| `IMPL_AVAILABLE = 0` | Wait (implementation worker running) |
| `IMPL_AVAILABLE = 1` + ready issues with priority | Spawn **impl worker** for highest priority ready issue |
| `IMPL_AVAILABLE = 1` + ready issues, no priority | Run `/assess-priority` inline, then spawn impl worker |
| `IMPL_AVAILABLE = 1` + no ready issues | Nothing to implement (wait for expansion) |

### Review Slots (up to 2 parallel)

| Condition | Action |
|-----------|--------|
| `REVIEW_AVAILABLE = 0` | Both review slots full, wait |
| `REVIEW_AVAILABLE > 0` + PR needs review (💬 > 0) | Spawn **review worker** |
| `REVIEW_AVAILABLE > 0` + PR ready to merge | Spawn **merge worker** |
| **PR STUCK** (blocked/needs-human/needs-info) | Skip this PR, check for other PRs needing review |

### Combined Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  DECISION FLOW (7 slots: 4 expansion + 1 impl + 2 review)       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK EXPANSION SLOTS (0-4 available)                       │
│     ├─ Count issues needing expansion                           │
│     ├─ For each available slot (up to 4):                       │
│     │     └─ Spawn expansion worker for next oldest issue       │
│     └─ Log how many spawned                                     │
│                                                                  │
│  2. CHECK IMPLEMENTATION SLOT (0-1 available)                   │
│     ├─ Slot occupied? → Skip to review slots                    │
│     └─ Slot available?                                          │
│         └─ Ready issues exist?                                  │
│               ├─ YES → Prioritized?                             │
│               │         ├─ YES → Spawn impl worker              │
│               │         └─ NO  → /assess-priority, then spawn  │
│               └─ NO  → Nothing to implement                     │
│                                                                  │
│  3. CHECK REVIEW SLOTS (0-2 available)                          │
│     ├─ List open PRs needing review (💬 > 0 or merge-ready)     │
│     ├─ Skip any STUCK PRs (blocked/needs-human)                 │
│     ├─ For each available slot (up to 2):                       │
│     │     └─ Spawn review/merge worker for next PR              │
│     └─ Log how many spawned                                     │
│                                                                  │
│  4. UPDATE .workflow-state.json with new workers                │
│                                                                  │
│  5. LOG STATUS TO WORKLOG.md                                    │
│                                                                  │
│  6. COMMIT state changes and EXIT                               │
└─────────────────────────────────────────────────────────────────┘
```

## Avoiding Duplicate Work

The orchestrator tracks active workers via **`.workflow-state.json`** (primary) and logs to **WORKLOG.md** (human-readable history).

### Primary Method: JSON State Tracking

When spawning a worker, update `.workflow-state.json`:

```python
def spawn_worker(slot_type, conv_id, target_id, target_type="issue"):
    """Add a new worker to the state file."""
    with open(".workflow-state.json", 'r') as f:
        state = json.load(f)
    
    worker = {
        "conv_id": conv_id[:7],  # 7-char prefix
        target_type: target_id,   # "issue": 9 or "pr": 42
        "started": datetime.now(timezone.utc).isoformat()
    }
    state["slots"][slot_type].append(worker)
    state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    with open(".workflow-state.json", 'w') as f:
        json.dump(state, f, indent=2)
    
    # Also log to WORKLOG.md for human visibility
    log_to_worklog(slot_type, conv_id, target_id)
```

### Check Slot Availability

```python
def get_available_slots(state):
    """Return count of available slots per type."""
    return {
        "expansion": state["limits"]["expansion"] - len(state["slots"]["expansion"]),
        "implementation": state["limits"]["implementation"] - len(state["slots"]["implementation"]),
        "review": state["limits"]["review"] - len(state["slots"]["review"])
    }

# Example output: {"expansion": 2, "implementation": 1, "review": 0}
# Means: can spawn 2 more expansion, 1 impl, 0 review (both full)
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
```

### Decision Rules

**For Expansion Slots (max 4):**
- Spawn up to `EXPANSION_AVAILABLE` workers for issues needing expansion
- Each targets a different issue (oldest first)

**For Implementation Slot (max 1):**
- Only spawn if `IMPL_AVAILABLE = 1` 
- Targets highest priority ready issue

**For Review Slots (max 2):**
- Spawn up to `REVIEW_AVAILABLE` workers for PRs needing review
- Each targets a different PR

**All slot types run independently** - expansion, implementation, and review workers can all run in parallel.

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
     ⚠️ WORKLOG.md changes ALWAYS go directly to main, never in feature branches/PRs
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
      ⚠️ WORKLOG.md changes ALWAYS go directly to main, never in feature branches/PRs
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
      ⚠️ WORKLOG.md changes ALWAYS go directly to main, never in feature branches/PRs
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

> ⚠️ **CRITICAL: State files ALWAYS live on main branch.**
>
> Both `.workflow-state.json` and `WORKLOG.md` must be read from and written to
> the **main branch only**. Never include these files in feature branches or PRs.
>
> When updating state:
> 1. Checkout main: `git checkout main && git pull origin main`
> 2. Update `.workflow-state.json` and/or `WORKLOG.md`
> 3. Commit and push directly to main: `git commit -am "..." && git push origin main`
>
> This ensures all orchestrator runs see consistent state, regardless of which
> feature branches exist or what PRs are open.

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

**🛑 DO NOT commit a WORKLOG entry.**

If this tick took no productive action (no worker spawned, no PR merged, no human instruction followed, no review addressed), **do not write to `WORKLOG.md` or `.workflow-state.json`**. Heartbeats belong in logs, not in source history.

Instead:

1. **Log to stdout** in the standard format from the [Logging](#logging) section.
2. **Increment the quiet-tick counter** in memory (see [Auto-Disable](#auto-disable-on-consecutive-quiet-periods) below). The counter lives in `.workflow-state.json` field `quiet_ticks` — but only **commit the state change when the counter resets to 0** (productive tick), or when the auto-disable threshold is reached (final state write before turning off).
3. **Exit cleanly.**

This rule applies to **both** cron-triggered ticks and manual `/orchestrate` invocations. A human running `/orchestrate` against an idle backlog must not produce repo commits.

#### Why

Between 2026-05-22 03:38Z and 11:30Z the orchestrator emitted **18 consecutive `chore: worklog update — Nth consecutive blocked /orchestrate`** commits to `main` while PR #272 was halted on `needs-human` (see jpshackelford/voice-relay#272 and jpshackelford/.openhands#22). Each commit widened the divergence from every open feature branch and produced no useful signal a human couldn't already see from the PR status itself.

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

**CRITICAL:** If two consecutive ticks take no productive action, disable the automation.

The trigger is now **state-counter based**, not WORKLOG.md grep. Because the [When No Action Needed](#when-no-action-needed) rule prohibits emitting WORKLOG entries on quiet ticks, the prior "grep for `All quiet`" detection is obsolete and will never fire.

### Automation ID

Read from the environment variable `ORCHESTRATOR_AUTOMATION_ID`. The deployed v2 orchestrator uses `5f180989-ed9c-42b4-ac9f-5f30f0623316`; do not hardcode this — the v1 ID (`a0219382-2e7c-4156-9991-7b9976739a66`) referenced in earlier revisions of this skill is stale and points at the wrong automation, which is why the 2026-05-22 livelock never self-resolved.

```bash
AUTOMATION_ID="${ORCHESTRATOR_AUTOMATION_ID:-5f180989-ed9c-42b4-ac9f-5f30f0623316}"
```

### Detection Logic

The quiet-tick counter lives in `.workflow-state.json`:

```json
{
  "version": 2,
  "slots": { … },
  "limits": { … },
  "completed": [ … ],
  "quiet_ticks": 0,
  "last_updated": "…"
}
```

At the end of every tick:

1. **Productive tick** (spawned, merged, addressed, followed instruction) → `quiet_ticks = 0`, commit state.
2. **Quiet tick** (no action) → `quiet_ticks += 1`.
   - If `quiet_ticks >= 2`: **disable the automation**, commit final state, exit.
   - If `quiet_ticks < 2`: do NOT commit state (see [When No Action Needed](#when-no-action-needed)).

```bash
QUIET=$(jq -r '.quiet_ticks // 0' .workflow-state.json)

if [ "$THIS_TICK_PRODUCTIVE" = "true" ]; then
  jq '.quiet_ticks = 0 | .last_updated = now | todate' .workflow-state.json > .workflow-state.json.tmp \
    && mv .workflow-state.json.tmp .workflow-state.json
  # commit and push
else
  NEW=$((QUIET + 1))
  if [ "$NEW" -ge 2 ]; then
    # disable + persist + exit (see "How to Disable" below)
    echo "Auto-disable triggered: $NEW consecutive quiet ticks"
  else
    # increment in-memory only; do NOT commit
    echo "Quiet tick $NEW of 2 — no commit"
  fi
fi
```

### How to Disable

```bash
AUTOMATION_ID="${ORCHESTRATOR_AUTOMATION_ID:-5f180989-ed9c-42b4-ac9f-5f30f0623316}"
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
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
*/15 * * * *  # Every 15 minutes (America/New_York)
```

This is the actual deployed cadence (verified against the v2 automation on 2026-05-22). Earlier revisions of this doc said `*/30`; that's stale.

Adjust based on expected review turnaround time — but bear in mind that more frequent ticks compound any heartbeat commits, so the [When No Action Needed](#when-no-action-needed) rule (no repo writes on quiet ticks) is the primary defense against tick-cadence noise.
