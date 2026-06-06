---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate Workflow

Main orchestration logic for the ohtv workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

Unlike design-document-driven projects, ohtv uses **GitHub issues and PRs exclusively** as the source of truth. Issues go through two phases:

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
│    - Implementation, Testing, Review, or Merge worker            │
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
│     - Issues by label: ready, hold, priority:*                  │
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
lxa repo add jpshackelford/ohtv 2>/dev/null || true

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
        else:  # implementation, testing, review, merge
            ACTIVE_PR_WORKER=true

CAN_SPAWN_EXPANSION = !ACTIVE_EXPANSION
CAN_SPAWN_PR_WORKER = !ACTIVE_PR_WORKER
```

## Gather State

Use `gh` to discover open PRs and issues, `lxa` for quick status:

```bash
# 1. Discover open PRs (usually 0 or 1)
gh pr list --repo jpshackelford/ohtv --state open --json number,title,isDraft
# Output: [{"number": 42, "title": "Add --repair option", "isDraft": false}]

# 2. If a PR exists, get quick status with lxa
lxa pr list "jpshackelford/ohtv#42"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Check for manual test results in PR comments
gh pr view 42 --repo jpshackelford/ohtv --comments | grep -i "Manual Test Results"

# 4. List issues needing expansion (no 'ready' label, no 'hold' label)
gh issue list --repo jpshackelford/ohtv --state open --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | (contains(["ready"]) or contains(["hold"])) | not)] | sort_by(.number)'
# Issues without 'ready' or 'hold' label need expansion

# 5. List ready issues (have 'ready' label, no 'hold' label)
gh issue list --repo jpshackelford/ohtv --state open --label "ready" --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | contains(["hold"]) | not)] | sort_by(.number)'

# 6. Check for prioritized ready issues
gh issue list --repo jpshackelford/ohtv --state open --label "ready" --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | any(startswith("priority:")))]'
```

### Issue Categories

| Category | Labels | Action |
|----------|--------|--------|
| Needs expansion | No `ready`, no `hold` | Spawn expansion worker |
| Ready, not prioritized | `ready`, no `priority:*` | Run `/assess-priority` inline |
| Ready, prioritized | `ready` + `priority:*` | Spawn implementation worker |
| On hold | `hold` | Skip (wait for human to remove hold) |
| Blocked | `blocked`, `needs-info`, `needs-split` | Skip (needs human attention) |

## Decision Tree

The ohtv workflow uses **two parallel slots** and ensures **documentation is updated before testing** (so we test what's documented).

### Expansion Slot (can run parallel to PR work)

| Condition | Action |
|-----------|--------|
| `CAN_SPAWN_EXPANSION` + issues need expansion (no `ready`, no `hold`) | Spawn **expansion worker** for oldest unexpanded issue |
| `CAN_SPAWN_EXPANSION` + no issues need expansion | Slot idle (all issues expanded or on hold) |
| `!CAN_SPAWN_EXPANSION` | Wait (expansion worker running) |

### PR Slot (Implementation → Docs → Testing → Review → Merge)

| Condition | Action |
|-----------|--------|
| `!CAN_SPAWN_PR_WORKER` | Wait (PR worker running) |
| PR exists, draft, CI failing | Wait (impl worker may still be active) |
| PR exists, draft, CI green | Wait (impl worker finishing up) |
| PR exists, ready, CI green, **README not updated** | Spawn **docs worker** |
| PR exists, ready, CI green, docs updated, **no manual test results** | Spawn **testing worker** |
| PR exists, ready, CI green, **test results outdated** | Spawn **re-testing worker** |
| PR exists, ready, CI green, test results valid, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, test results valid, good rating, **docs outdated** | Spawn **docs spot-check worker** |
| PR exists, ready, test results valid, good rating, docs valid | Spawn **merge worker** |
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
│         ├─ YES → Handle PR state (docs/test/review/merge)       │
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
Implementation → CI Green → DOCS UPDATE → Manual Testing → Review → [Re-test?] → [Docs spot-check?] → Merge
                               ↑                                        ↑              ↑
                         (before testing)                    (if significant    (if significant
                                                              code changes)      doc-impacting changes)
```

### Key Principle: Test What's Documented

**Documentation must be updated BEFORE testing.** This ensures:
- Testers verify documented behavior matches actual behavior
- README examples are tested as part of manual testing
- Users get accurate docs when the PR merges

If you find a PR with:
- No docs update comment AND changes affect CLI/API → Spawn **docs worker** first
- Docs updated but no test results → Spawn **testing worker**
- Review comments (💬 > 0) but NO manual test results → Spawn **testing worker** (docs first if missing)
- Review comments AND test results that are outdated → Spawn **re-testing worker**
- Approved but significant review changes affected docs → Spawn **docs spot-check worker**

The testing step is NOT skipped just because review started. CI must be green to test.

### Detecting Documentation Updates

A PR has documentation updates if:
- README.md was modified in the PR diff, OR
- A PR comment contains "Documentation updated" or "README updated"

```bash
# Check if README.md is in the changed files
gh pr diff 42 --name-only | grep -i "readme"

# Check for docs update comment
gh pr view 42 --repo jpshackelford/ohtv --comments | grep -iE "(README|documentation|docs).*(updated|verified|checked)"
```

### When Docs Update is Required

Update README.md if the PR introduces ANY of:
- New CLI commands or subcommands
- New flags or options
- Changed default behavior
- New configuration options
- New environment variables
- Changed output formats

Do NOT require docs update if only:
- Internal refactoring (no user-facing changes)
- Bug fixes that don't change documented behavior
- Test-only changes
- Performance improvements

### Detecting Manual Test Results

A PR has been manually tested if there's a comment containing:
- `## Manual Test Results` (or similar header)
- Posted by `openhands-ai` or contains "AI agent (OpenHands)"

```bash
# Check for manual test comment with timestamp
gh api graphql -f query='
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        comments(first: 100) {
          nodes {
            body
            author { login }
            createdAt
          }
        }
      }
    }
  }
' -f owner=jpshackelford -f repo=ohtv -f number=42 | \
  jq '.data.repository.pullRequest.comments.nodes[] | select(.body | test("Manual Test Results"; "i"))'
```

### Detecting Outdated Test Results (Re-testing Required)

Test results are **outdated** and re-testing is required when:

1. **Significant commits after last test** - New commits pushed after the test comment timestamp
2. **Review requested substantial changes** - Review feedback that changes behavior (not just style/docs)

```bash
# Get timestamp of last manual test comment
TEST_TIMESTAMP=$(gh api graphql -f query='...' | jq -r '... | .createdAt' | tail -1)

# Get timestamp of last commit on PR branch
LAST_COMMIT=$(gh pr view 42 --json commits --jq '.commits[-1].committedDate')

# If last commit is AFTER last test, re-testing may be needed
if [[ "$LAST_COMMIT" > "$TEST_TIMESTAMP" ]]; then
  # Check if changes are significant (not just docs/style)
  CHANGED_FILES=$(gh pr diff 42 --name-only)
  # If .py files changed (not just tests), re-test is needed
  if echo "$CHANGED_FILES" | grep -E '\.py$' | grep -v '_test\.py$' | grep -v 'test_'; then
    echo "Re-testing required: code changes after last test"
  fi
fi
```

### Heuristics for "Significant Changes"

Re-test if ANY of these are true after the last test:
- Source files changed (`.py` excluding `*_test.py`, `test_*.py`)
- CLI argument handling changed
- Database/storage logic changed
- More than 50 lines of non-test code changed

Do NOT re-test if only:
- Test files changed
- Documentation/README changed
- Comments or docstrings changed
- Type hints added (no runtime effect)

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

Use `/spawn-conversation` skill to start worker conversations.

### Expansion Worker

**Worker Type:** `expansion`
**Slot:** Expansion slot (can run parallel to PR workers)

Use when: Issues exist that need technical detail before implementation.

```
Repository: jpshackelford/ohtv
Title: [Expansion] Issue #{issue_number} - {issue_title}
Prompt: |
  You are expanding GitHub Issue #{issue_number} for the ohtv project.

  **ISSUE TO EXPAND:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/ohtv/issues/{issue_number}

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

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
Issue Number: {issue_number}
Worker Type: expansion
```

### Implementation Worker

**Worker Type:** `implementation`
**Slot:** PR slot (serialized with testing/review/merge)

Use when: Ready issues exist with priority labels and no open PR.

```
Repository: jpshackelford/ohtv
Title: [Implementation] Issue #{issue_number} - {issue_title}
Prompt: |
  You are implementing GitHub Issue #{issue_number} for the ohtv project.

  **ISSUE TO IMPLEMENT:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/jpshackelford/ohtv/issues/{issue_number}
  - Priority: {priority_label}

  This issue has already been expanded with technical detail. Read the issue
  description AND comments for the implementation approach.

  1. Read the issue description AND comments: gh issue view {issue_number} --comments
  2. The technical approach comment tells you what to build
  3. Create a feature branch from main (ensure main is up-to-date)
  4. Implement following the approach in the issue comments
  5. Write tests (target >80% coverage for new code)
  6. Run lints and type checks, fix any issues
  7. Commit with clear messages, push, create a DRAFT PR
  8. Link PR to issue: Include "Fixes #{issue_number}" in PR description
  9. Monitor CI, fix any failures until green
  10. Once CI is green, REFLECT:
      - Are all acceptance criteria from the issue met?
      - Note any learnings or follow-up items
  11. Move PR from draft to ready (triggers review bot)
  12. Update WORKLOG.md on main with PR link
  13. Exit - docs/testing/review handling is a separate conversation

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
Issue Number: {issue_number}
Worker Type: implementation
```

### Documentation Worker

**Worker Type:** `docs`
**Slot:** PR slot (serialized with implementation/testing/review/merge)

Use when: PR has user-facing changes but README.md hasn't been updated yet.

```
Repository: jpshackelford/ohtv
Title: [Docs] PR #{number} - {title}
Prompt: |
  You are updating documentation for PR #{number}.
  
  This must happen BEFORE manual testing so testers verify documented behavior.
  
  1. Clone the repo and checkout the PR branch
  2. Read the PR diff to understand what changed
  3. Identify user-facing changes:
     - New commands or subcommands
     - New flags or options  
     - Changed default behavior
     - New environment variables
  4. Update README.md to document these changes:
     - Add new sections if needed
     - Update examples to show new flags/options
     - Ensure examples are copy-pasteable and accurate
  5. Commit with message: "docs: update README for {feature}"
  6. Push and verify CI passes
  7. Post a PR comment: "Documentation updated for: {list of changes}"
  8. Exit - testing worker will verify the docs

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

### Docs Spot-Check Worker (Before Merge)

Use when: PR is approved but significant review changes may have affected documented behavior.

```
Repository: jpshackelford/ohtv
Title: [Docs Check] PR #{number} - {title}
Prompt: |
  You are spot-checking documentation for PR #{number} before merge.
  
  Significant code changes occurred during review. Verify README is still accurate.
  
  1. Clone the repo and checkout the PR branch
  2. Compare current code against README.md:
     - Do documented examples still work?
     - Are all new flags/options documented?
     - Are default values correct?
  3. If discrepancies found:
     - Update README.md
     - Commit: "docs: update README after review changes"
     - Push
  4. Post a PR comment:
     - If changes made: "Docs spot-check: Updated {list}"
     - If no changes needed: "Docs spot-check: README is accurate ✓"
  5. Exit

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

### Testing Worker (Initial)

Use when: PR has docs updated but NO manual test results yet (even if review has already started).

```
Repository: jpshackelford/ohtv
Title: [Manual Test] PR #{number} - {title}
Prompt: |
  You are running manual tests for PR #{number}.
  
  This is a REQUIRED step before code review can proceed. Your job is to:
  1. Clone the repo and checkout the PR branch
  2. Install with `uv sync`
  3. Read the PR to understand what changed
  4. Design and execute blackbox tests for the new functionality
  5. Run the unit test suite
  6. Post a structured test report as a PR comment
  
  **NOTE:** Even if this PR already has review comments, testing is still
  required. Testing gates the review process - reviewers need to see what
  was tested before approving.
  
  Follow the /manual-test skill for the expected test report format.
  
  After posting the test report, EXIT. Do not continue to review.

Plugins: github:jpshackelford/.openhands/plugins/ohtv-workflow@feat/ohtv-workflow-plugin
PR Number: {number}
```

### Re-Testing Worker (After Significant Changes)

Use when: PR has test results, but significant code changes were made AFTER the last test.

```
Repository: jpshackelford/ohtv
Title: [Re-Test] PR #{number} - {title}
Prompt: |
  You are RE-TESTING PR #{number} after significant changes from code review.
  
  Previous test results exist, but code has changed since then. Your job is to:
  1. Clone the repo and checkout the PR branch
  2. Install with `uv sync`
  3. Read the PR diff to understand what changed SINCE the last test
  4. Focus testing on the areas that changed
  5. Re-run any tests that could be affected by the changes
  6. Run the full unit test suite
  7. Post a NEW test report as a PR comment (do not edit the old one)
  
  Your test report should note:
  - "Re-test after review round N"
  - What specifically was re-tested
  - Whether previously passing tests still pass
  
  Follow the /manual-test skill for the expected test report format.
  
  After posting the re-test report, EXIT.

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

### 🚨 Non-negotiable: status marker on every entry

**Every orchestrator worklog entry MUST end with exactly one of:**

```
<!-- orchestrator-status: spawn -->
```
or
```
<!-- orchestrator-status: quiet -->
```

This is the *only* signal the auto-disable detection reads — body phrasing like "All quiet", "No worker spawned", or "Counter = 1 of 2" is ignored by the script. Forgetting the marker silently breaks auto-disable. Detailed rules and detection script are in the **Auto-Disable on Consecutive Quiet Periods** section below.

**Before pushing your WORKLOG.md commit**, run this self-check to confirm the marker is present in the entry you just authored:

```bash
# The just-authored entry should contain exactly one orchestrator-status marker.
EXPECTED_TS="{your entry's timestamp, e.g. 2026-06-06 19:23 UTC}"
NEW_ENTRY_MARKER_COUNT=$(awk "/^### $EXPECTED_TS - Orchestrator/,/^---$/" WORKLOG.md \
  | grep -c "<!-- orchestrator-status:")

if [ "$NEW_ENTRY_MARKER_COUNT" -ne 1 ]; then
  echo "ERROR: Your new entry has $NEW_ENTRY_MARKER_COUNT markers (expected 1). Add the marker before pushing."
  exit 1
fi
```

If the check fails, edit the entry to add the missing marker before committing/pushing. Do **not** push a worklog entry without its marker.

### Log Entry Format with Active Workers Table

Include the conversation ID (first 7 chars) in the Active Workers table:

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #9 - Scope messages | running |
| `def5678` | implementation | Issue #7 - WebSocket | running |

**Current State:**
- [PR #42](https://github.com/jpshackelford/ohtv/pull/42): `oC green ready` 💬2
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
| `ghi9012` | expansion | Issue #11 - Session View | **NEW** |

**Spawned: Expansion Worker**
- Issue: [#11 - Session View](https://github.com/jpshackelford/ohtv/issues/11)
- Conversation: [`ghi9012`](https://app.all-hands.dev/conversations/ghi9012...)

**Current State:**
- No open PRs
- Ready issues: #9, #10 (awaiting implementation)
- Issues needing expansion: #11 (now being expanded), #12

<!-- orchestrator-status: spawn -->

---
```

### When Spawning Multiple Workers (Parallel)

```markdown
### 2025-05-05 14:30 UTC - Orchestrator

**Active Workers:**
| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | expansion | Issue #12 - CLI flag | **NEW** |
| `def5678` | implementation | Issue #9 - Scope messages | **NEW** |

**Spawned: 2 Workers (parallel)**

1. **Expansion Worker**
   - Issue: [#12 - CLI flag](https://github.com/jpshackelford/ohtv/issues/12)
   - Conversation: [`abc1234`](https://app.all-hands.dev/conversations/abc1234...)

2. **Implementation Worker**  
   - Issue: [#9 - Scope messages](https://github.com/jpshackelford/ohtv/issues/9) (priority:high)
   - Conversation: [`def5678`](https://app.all-hands.dev/conversations/def5678...)

<!-- orchestrator-status: spawn -->

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

<!-- orchestrator-status: spawn -->

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

- [PR #6](https://github.com/jpshackelford/ohtv/pull/6) in progress
- All issues expanded
- Next check in ~30 minutes

<!-- orchestrator-status: quiet -->

---
```

> Note: the `<!-- orchestrator-status: quiet -->` marker is **required** on every quiet entry. See the Auto-Disable section below for the full rule. Spawn entries use `<!-- orchestrator-status: spawn -->` instead.

## Auto-Disable on Consecutive Quiet Periods

**CRITICAL:** Before logging a quiet entry, check if WORKLOG.md already shows two consecutive quiet entries. If so, disable the automation instead of running indefinitely.

### Required Status Marker (MUST emit, do not paraphrase)

Every orchestrator worklog entry — **regardless of how the run was triggered (cron-fired, user-invoked, or manually dispatched)** — MUST end with **exactly one** of these HTML-comment markers on its own line, immediately before the trailing `---` separator:

```
<!-- orchestrator-status: spawn -->
```
or
```
<!-- orchestrator-status: quiet -->
```

Use `spawn` if you spawned a worker (expansion, implementation, review, docs, testing, etc.) or took a state-changing action on the repo (labels, PR ready, merge, archive, etc.). Use `quiet` if you took no state-changing action.

Do **not** vary, paraphrase, omit, or comment-around this marker. The auto-disable detection is a literal `grep` for the marker string — any phrasing drift in the entry body is ignored. **The marker is the only signal that matters.**

This requirement supersedes any historical convention in older worklog entries that used English phrases like "All quiet" or "No worker spawned" without the marker. Do not invent additional "trigger-source" categories (e.g. "user-invoked vs cron-fired") as a reason to skip the marker or the auto-disable check — every entry counts, regardless of how the run was triggered.

### Automation ID

This orchestrator's automation ID is:
```
ed08056a-b8d8-41ac-adb3-1d8d105e0cef
```

If the automation is recreated and this ID becomes stale, the disable-automation skill falls back to lookup-by-name using `?name=OHTV+Workflow+Orchestrator`.

#### 🚨 Do NOT use any other ID

`WORKLOG.md` history contains many references to a previous, archived automation ID `c202ca20-60d5-4f5b-9d53-3d7308c1d95b` (name suffix `(feature branch, disabled)`). **PATCHing that ID is a no-op — the live `ed08056a…` automation will keep firing.**

When you decide to disable, follow the pre-disable verification snippet in `disable-automation.md` (GET the automation first, assert `name == "OHTV Workflow Orchestrator"` exactly — not `"…(feature branch, disabled)"` — and assert `enabled == true`). The only trusted source for the ID is this skill file (or `disable-automation.md`). Never copy an ID out of `WORKLOG.md` history.

### Detection Logic

Read the last two status markers in WORKLOG.md (in order). If both are `quiet`, auto-disable instead of logging a third quiet entry:

```bash
# Get the last two status markers from WORKLOG.md (most recent two orchestrator decisions).
LAST_TWO_MARKERS=$(grep -oE "orchestrator-status: (spawn|quiet)" WORKLOG.md | tail -2)
QUIET_COUNT=$(echo "$LAST_TWO_MARKERS" | grep -c "quiet" || true)

# If both of the last two markers are 'quiet', this run would be the 3rd consecutive — disable.
if [ "$QUIET_COUNT" -eq 2 ]; then
  echo "Two consecutive quiet periods detected — disabling automation."
fi
```

Note: this counts markers, not entries. An entry without a marker (legacy or malformed) is simply skipped — it neither resets the counter nor counts toward it. New entries MUST carry the marker.

### How to Disable

When two consecutive quiet periods are detected:

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### WORKLOG Entry When Disabling

```markdown
### {timestamp} - Orchestrator

🔒 **Auto-disabled due to inactivity**

Two consecutive quiet periods detected — no new work to pick up.
Automation has been disabled to prevent unnecessary runs.

**To re-enable:**
- OpenHands UI: https://app.all-hands.dev/automations → Find "OHTV Workflow Orchestrator" → Toggle enable
- Or via API:
  ```bash
  curl -X PATCH "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
    -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"enabled": true}'
  ```

<!-- orchestrator-status: spawn -->

---
```

### Example Quiet Entry With Marker

```markdown
### {timestamp} - Orchestrator

✅ All quiet — PR slot occupied (PR #185 ready, waiting on review), expansion slot empty (no candidates).

<!-- orchestrator-status: quiet -->

---
```

### Decision Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Before logging a 'quiet' marker:                                │
├─────────────────────────────────────────────────────────────────┤
│  1. Read the last TWO markers in WORKLOG.md.                    │
│  2. Are both 'quiet'?                                            │
│     └─ YES → DISABLE automation + log disable entry             │
│              (uses 'spawn' marker — a disable is an action)     │
│              + EXIT                                              │
│     └─ NO  → Log normal entry with 'quiet' marker + EXIT        │
└─────────────────────────────────────────────────────────────────┘
```

See [Disable Automation Skill](disable-automation.md) for complete details.

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

### Pre-exit checklist (run before EXIT)

1. WORKLOG.md entry written? ☐
2. Entry ends with **exactly one** `<!-- orchestrator-status: spawn -->` or `<!-- orchestrator-status: quiet -->` marker line? ☐
3. Self-check script (in the WORKLOG.md Updates section) returned exit code 0? ☐
4. Auto-disable check (last two markers in WORKLOG.md) evaluated correctly? ☐
5. Entry committed and pushed to `main`? ☐

If any box is unchecked, fix it before EXIT. The marker requirement is the most commonly missed step — always confirm it explicitly.

## Cron Schedule

```
*/30 * * * *  # Every 30 minutes
```

Adjust based on expected review turnaround time.
