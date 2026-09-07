---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate Workflow

Main orchestration logic for the lxa workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

Work items are tracked as **GitHub Issues**. Issues go through two phases:

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
│    - Implementation, Self-Review, Review Response, or Merge      │
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
│  0. SETUP: Install tools (lxa)                                  │
│  0.5. HOUSEKEEPING: Truncate worklog if large (>300 lines)      │
│  1. READ WORKLOG.md for human instructions (FIRST!)             │
│  2. If human instructions found → follow them, then exit        │
│  3. PARSE WORKLOG.md for active workers (by conv ID)            │
│  4. CHECK which workers are still running (API query)           │
│  5. GATHER STATE:                                                │
│     - Open PRs (lxa pr list)                                    │
│     - Issues by label: ready, hold, priority:*                  │
│  6. DECIDE what to spawn (see Decision Tree)                    │
│  7. SPAWN worker(s) if slots available and work exists          │
│  8. UPDATE WORKLOG.md with current state                        │
│  9. EXIT                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Step 0: Ensure Tools Are Installed

Before anything else, ensure `lxa` is available:

```bash
# Install if not already present
which lxa || uv tool install git+https://github.com/jpshackelford/lxa.git

# Verify installation
lxa --version
```

## Step 0.5: Housekeeping - Truncate Worklog

If the worklog is getting large, archive old entries to keep the file manageable and ensure agents have focused context on recent productive work.

```bash
# Only run truncation if WORKLOG.md is large (>300 lines)
WORKLOG_LINES=$(wc -l < WORKLOG.md 2>/dev/null || echo 0)
if [ "$WORKLOG_LINES" -gt 300 ]; then
  echo "📦 WORKLOG.md has $WORKLOG_LINES lines - running truncation"
  # Use /truncate-worklog skill for implementation
fi
```

See [Truncate Worklog Skill](truncate-worklog.md) for complete implementation.

### What Gets Archived

- Entries older than 6 hours of productive work
- Status-check entries ("All quiet", "Waiting")
- Old spawn/completion entries

### What's Preserved

- Recent 6 hours of productive entries (spawns, completions, merges)
- Active worker table (always current)
- Human instructions (until acknowledged)

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
        else:  # implementation, self-review, review-response, merge
            ACTIVE_PR_WORKER=true

CAN_SPAWN_EXPANSION = !ACTIVE_EXPANSION
CAN_SPAWN_PR_WORKER = !ACTIVE_PR_WORKER
```

## Gather State

Use `gh` to discover open PRs and issues, `lxa` for quick status:

```bash
# 1. Discover open PRs (usually 0 or 1)
gh pr list --repo jpshackelford/lxa --state open --json number,title,isDraft,url

# 2. For each PR, get status with lxa
lxa pr list "jpshackelford/lxa#42" --title
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Check PR review status
gh pr view 42 --repo jpshackelford/lxa --json reviewDecision,reviews

# 4. List issues needing expansion (no 'ready' label, no 'hold' label)
gh issue list --repo jpshackelford/lxa --state open --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | (contains(["ready"]) or contains(["hold"])) | not)] | sort_by(.number)'
# Issues without 'ready' or 'hold' label need expansion

# 5. List ready issues (have 'ready' label, no 'hold' label)
gh issue list --repo jpshackelford/lxa --state open --label "ready" --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | contains(["hold"]) | not)] | sort_by(.number)'

# 6. Check for prioritized ready issues
gh issue list --repo jpshackelford/lxa --state open --label "ready" --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | any(startswith("priority:")))]'
```

### LXA History Codes Reference

| Code | Meaning |
|------|---------|
| `o` | Opened |
| `C` | Changes requested |
| `R` | Review round |
| `f` | Fixes pushed |
| `F` | Final fixes |
| `A` | Approved |
| `m` | Merged |
| `k` | Killed (closed without merge) |

### Issue Categories

| Category | Labels | Action |
|----------|--------|--------|
| Needs expansion | No `ready`, no `hold` | Spawn expansion worker |
| Ready, not prioritized | `ready`, no `priority:*` | Run `/assess-priority` inline |
| Ready, prioritized | `ready` + `priority:*` | Spawn implementation worker |
| On hold | `hold` | Skip (wait for human to remove hold) |
| Blocked | `blocked`, `needs-info`, `needs-split` | Skip (needs human attention) |

## Decision Tree

The lxa workflow uses **two parallel slots** for maximum throughput.

### Expansion Slot (can run parallel to PR work)

| Condition | Action |
|-----------|--------|
| `CAN_SPAWN_EXPANSION` + issues need expansion (no `ready`, no `hold`) | Spawn **expansion worker** for oldest unexpanded issue |
| `CAN_SPAWN_EXPANSION` + no issues need expansion | Slot idle (all issues expanded or on hold) |
| `!CAN_SPAWN_EXPANSION` | Wait (expansion worker running) |

### PR Slot (Implementation → Self-Review → Human Review → Merge)

| Condition | Action |
|-----------|--------|
| `!CAN_SPAWN_PR_WORKER` | Wait (PR worker running) |
| PR exists, CI failing | Wait or spawn **CI fix worker** |
| PR exists, draft, CI green | Spawn **self-review worker** |
| PR exists, ready, CI green, 💬 > 0 | Spawn **review response worker** |
| PR exists, ready, CI green, approved | Spawn **merge worker** |
| PR merged | Log completion |
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
│     └─ Issues need expansion (no ready, no hold)?               │
│         ├─ YES → Spawn expansion worker (oldest issue)          │
│         └─ NO  → Expansion slot idle                            │
│                                                                  │
│  2. CHECK PR SLOT                                                │
│     ├─ Active PR worker? → Log status, exit                     │
│     └─ Open PR exists?                                          │
│         ├─ YES → Handle PR state (self-review/respond/merge)    │
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

### Workflow Sequence (PR Slot)

```
Implementation → CI Green → Self-Review → Human Review → Respond → Approval → Merge
                              ↑                           ↑
                        (self-review              (respond-to-review
                           worker)                     worker)
```

## Avoiding Duplicate Work

Before spawning a worker, check if related work is already in progress using the Active Workers table in WORKLOG.md.

### Primary Method: WORKLOG.md Tracking

When spawning a worker, log it in this format:

```markdown
**Active Workers:**
| Conv ID | Type | Working On | Started |
|---------|------|------------|---------|
| `abc1234` | expansion | Issue #9 - Board command | 14:00 UTC |
| `def5678` | implementation | Issue #7 - Job tracking | 13:15 UTC |
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

### Decision Rules

**For Expansion Slot:**
- Only spawn if no `expansion` type worker shows `running` status

**For PR Slot:**
- Only spawn if no `implementation`, `self-review`, `review-response`, or `merge` type worker shows `running` status

**Both slots can be filled simultaneously** - an expansion worker and a PR worker can run in parallel.

## Worker Prompts

Use `/spawn-conversation` skill to start worker conversations.

### Expansion Worker

**Worker Type:** `expansion`
**Slot:** Expansion slot (can run parallel to PR workers)

Use when: Issues exist that need technical detail before implementation.

```
Repository: jpshackelford/lxa
Title: [Expansion] Issue #{issue_number} - {issue_title}
Prompt: |
  You are expanding GitHub Issue #{issue_number} for the lxa project.

  **ISSUE TO EXPAND:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/lxa/issues/{issue_number}

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

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
Issue Number: {issue_number}
Worker Type: expansion
```

### CI Fix Worker

**Worker Type:** `ci-fix`
**Slot:** PR slot (serialized with other PR workers)

Use when: PR has failing CI that needs investigation.

```
Repository: jpshackelford/lxa
Title: [CI Fix] PR #{number} - {title}
Prompt: |
  You are fixing CI failures on PR #{number}.

  1. Clone the repo and checkout the PR branch
  2. Run `make check` to reproduce the failure locally
  3. Analyze the failure output
  4. Fix the issue:
     - If test failure: fix the test or the code causing it
     - If lint failure: run `make lint` and fix
     - If type error: run `make typecheck` and fix
  5. Commit with message: "fix: resolve CI failure - {description}"
  6. Push and verify CI passes
  7. Exit

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
PR Number: {number}
```

### Self-Review Worker

Use when: Draft PR with passing CI, needs self-review before human review.

```
Repository: jpshackelford/lxa
Title: [Self-Review] PR #{number} - {title}
Prompt: |
  You are self-reviewing PR #{number} before requesting human review.

  1. Clone the repo and checkout the PR branch
  2. Verify CI is passing: gh pr checks {number}
  3. Review the code against quality principles:
     - Data structures appropriate for the problem?
     - Logic simple and clear? (no deep nesting, no special cases)
     - No over-engineering? (solve real problems, not theoretical)
     - Tests cover new behavior?
  4. Fix any issues you find:
     - Make the fix
     - Run `make check`
     - Commit with clear message
  5. Push all changes
  6. Mark PR ready for review: gh pr ready {number}
  7. Post a self-review comment:

     ## Self-Review Complete

     **Verdict:** 🟢 Good / 🟡 Acceptable

     ### What I Checked
     - [x] Data structures are appropriate
     - [x] Logic is simple and clear
     - [x] No over-engineering
     - [x] Tests cover new behavior
     - [x] All quality checks pass

     ### Issues Found & Fixed
     - [list any issues fixed]

     ---
     *Self-review by AI agent (OpenHands)*

  8. Exit

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
PR Number: {number}
```

### Review Response Worker

Use when: PR has unresolved review threads (💬 > 0).

```
Repository: jpshackelford/lxa
Title: [Review Round] PR #{number} - {title}
Prompt: |
  You are addressing review feedback on PR #{number}.

  1. Clone the repo and checkout the PR branch
  2. IMMEDIATELY set PR back to draft: gh pr ready {number} --undo
  3. Read ALL review comments and threads carefully
  4. For each piece of feedback, decide:
     - Accept and implement (most suggestions improve code quality)
     - Reject only if it significantly increases scope/complexity
  5. Group related changes into logical commits
  6. For each commit:
     - Make the change
     - Run `make check`
     - Commit with clear message referencing the feedback
     - Push and verify CI passes
  7. Reply to review threads explaining what you did
  8. Move PR back to ready: gh pr ready {number}
  9. Post a summary comment:

     ## Review Feedback Addressed

     ### Changes Made
     | Feedback | Action | Commit |
     |----------|--------|--------|
     | [feedback 1] | [what you did] | abc1234 |

     ---
     *Review response by AI agent (OpenHands)*

  10. Exit - next review round is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
PR Number: {number}
```

### Implementation Worker

Use when: Ready issue exists but no PR has been created yet.

```
Repository: jpshackelford/lxa
Title: [Implement] Issue #{issue_number} - {title}
Prompt: |
  You are implementing issue #{issue_number}.

  1. Clone the repo and create a feature branch
  2. Read the issue description and any expanded technical details
  3. Create `.pr/design.md` with:
     - Problem statement
     - Proposed solution
     - Implementation plan with milestones
  4. Implement the first milestone
  5. Run `make check` to verify
  6. Open a draft PR linking to the issue
  7. Exit - self-review worker will handle the next step

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
Issue Number: {issue_number}
```

### Merge Worker

Use when: PR is approved and ready to merge.

```
Repository: jpshackelford/lxa
Title: [Merge] PR #{number} - {title}
Prompt: |
  You are preparing PR #{number} for merge.

  1. Clone the repo and checkout the PR branch
  2. Verify CI is green: gh pr checks {number}
  3. Verify approval is present: gh pr view {number} --json reviewDecision
  4. Review the full PR diff: gh pr diff {number}
  5. Update PR description to reflect final state:
     - What was implemented
     - Key decisions made during review
     - Test coverage
  6. Craft a conventional commit message for squash-merge:
     - Type: feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line (50 chars max)
     - Body with relevant details
  7. Squash and merge:
     gh pr merge {number} --squash --body "commit message"
  8. Verify the merge succeeded
  9. Exit

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
PR Number: {number}
```

## WORKLOG.md Updates

After each orchestrator run, append a status update to `WORKLOG.md` in the repo root.

### Log Entry Format with Active Workers Table

Include the conversation ID (first 7 chars) in the Active Workers table:

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #9 - Board command | running |
| `def5678` | implementation | Issue #7 - Job tracking | running |

**Current State:**
- [PR #42](https://github.com/jpshackelford/lxa/pull/42): `oC green ready` 💬2
- Issues needing expansion: #11, #12
- Ready issues: #9 (priority:high), #10 (priority:medium)

**Action Taken:**
✅ Both worker slots occupied - no action needed

---
```

### When Spawning a Worker

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `ghi9012` | expansion | Issue #11 - Refine command | **NEW** |

**Spawned: Expansion Worker**
- Issue: [#11 - Refine command](https://github.com/jpshackelford/lxa/issues/11)
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
| `abc1234` | expansion | Issue #12 - Job status | **NEW** |
| `def5678` | implementation | Issue #9 - Board command | **NEW** |

**Spawned: 2 Workers (parallel)**

1. **Expansion Worker**
   - Issue: [#12 - Job status](https://github.com/jpshackelford/lxa/issues/12)
   - Conversation: [`abc1234`](https://app.all-hands.dev/conversations/abc1234...)

2. **Implementation Worker**  
   - Issue: [#9 - Board command](https://github.com/jpshackelford/lxa/issues/9) (priority:high)
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

- [PR #6](https://github.com/jpshackelford/lxa/pull/6) in progress
- All issues expanded
- Next check in ~30 minutes

---
```

## Auto-Disable on Consecutive Quiet Periods

**CRITICAL:** Before logging a "quiet" entry, check if WORKLOG.md already shows two consecutive quiet entries. If so, disable the automation instead of running indefinitely.

### Automation ID

**NOTE:** Update this ID after creating the automation.

```
54a6d9ad-d1e3-462b-8f74-b7fc6da7de71
```

### Detection Logic

Check WORKLOG.md for consecutive quiet entries:

```bash
# Extract last few orchestrator entries and check for consecutive "All quiet" patterns
QUIET_COUNT=$(tail -100 WORKLOG.md | grep -B2 "All quiet" | grep -c "Orchestrator" || echo 0)

# If 2 or more consecutive quiet entries exist, this would be the 3rd - disable instead
if [ "$QUIET_COUNT" -ge 2 ]; then
  echo "Two consecutive quiet periods detected - disabling automation"
fi
```

### How to Disable

When two consecutive quiet periods are detected, use the `/disable-automation` skill or:

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/<AUTOMATION_ID>" \
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
- OpenHands UI: https://app.all-hands.dev/automations → Find "LXA Workflow Orchestrator" → Toggle enable
- Or via API:
  ```bash
  curl -X PATCH "https://app.all-hands.dev/api/automation/v1/<AUTOMATION_ID>" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"enabled": true}'
  ```

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

## Exit Conditions

Always exit after:
- Running a refinement command (one action per wake-up)
- Spawning a worker (one action per wake-up)
- Determining no action needed
- Encountering an error that needs human attention

Do NOT:
- Wait for refinement or workers to complete
- Take multiple actions in one wake-up
- Loop continuously

## Cron Schedule

```
*/30 * * * *  # Every 30 minutes
```

Adjust based on expected review turnaround time.
