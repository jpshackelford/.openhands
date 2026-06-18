---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate Workflow

Generic PR workflow orchestration. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

**Project-specific configuration is read from `.agents/resources/orchestration.md`** in the target repository. This includes:
- Repository name and type
- Automation ID
- Setup commands
- Enabled phases (manual testing, self-review, etc.)
- Plugin source for spawned workers

## Worklog brevity guardrail (read this first)

WORKLOG.md exists for two readers: a human skimming "what happened and what's next", and the next orchestrator wake-up scraping a small set of facts (active conv IDs, last cycle's outcome, standing instructions). Anything beyond that is noise.

Each orchestrator entry MUST be **~10-20 lines**, not 50-100. See [WORKLOG.md Updates](#worklogmd-updates) below for the exact contract. Concretely:

- **Do** include: action line, 1-3 context bullets, Active Workers table, Current State bullets.
- **Don't** include: decision-tree traces, "what changed since last cycle" prose, prophecy about likely next transitions, repeated re-enable instructions, plugin paths, housekeeping commentary.

If you find yourself writing a numbered "1. Read config, 2. Check workers..." rationale into WORKLOG.md, stop — that belongs in your scratchpad / stdout log, not on disk.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **READ PROJECT CONFIG** - Load `.agents/resources/orchestration.md`
2. **CHECK FOR HUMAN INSTRUCTIONS** - Read WORKLOG.md for any `## INSTRUCTION:` entries
3. If human instructions exist, follow them before doing anything else
4. **CHECK FOR ACTIVE WORKERS** - Parse WORKLOG.md for running conversations
5. Discovers any open PRs for the repo
6. Lists open GitHub issues by label (`ready` vs needs expansion)
7. Decides what action is needed based on current state
8. Spawns worker conversation(s) if work is available
9. Appends status update to WORKLOG.md on main
10. Exits (next check happens on next cron trigger)

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
│  0. READ PROJECT CONFIG from .agents/resources/orchestration.md │
│  0.5. SETUP: Run setup commands from config                     │
│  0.6. HOUSEKEEPING: Truncate worklog if large (>300 lines)      │
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

## Step 0: Read Project Configuration

**This is the first thing the orchestrator does.**

Read the project-specific orchestration hints:

```bash
if [ -f ".agents/resources/orchestration.md" ]; then
    cat .agents/resources/orchestration.md
else
    echo "ERROR: No orchestration hints found at .agents/resources/orchestration.md"
    echo "This plugin requires project-specific configuration."
    echo ""
    echo "Create .agents/resources/orchestration.md with:"
    echo "  - Repository name (e.g., owner/repo)"
    echo "  - Automation ID"
    echo "  - Setup commands"
    echo "  - Enabled phases"
    echo "  - Plugin source for workers"
    exit 1
fi
```

### Expected Configuration Format

The orchestration.md file should contain (in markdown format):

```markdown
# Orchestration Hints

## Project
- Repository: owner/repo
- Type: cli | web

## Automation
- ID: uuid-here
- Quiet threshold: 2

## Setup Commands
```bash
# Commands to run before orchestration
which lxa || uv tool install lxa
lxa repo add owner/repo 2>/dev/null || true
```

## Phases
- Issue expansion: enabled
- Priority assessment: enabled
- Manual testing: enabled | disabled | required
- Self-review: enabled | disabled
- Docs update before testing: enabled | disabled

## Plugin Source
github:owner/.openhands/plugins/pr-workflow@main
```

### Extract Key Values

After reading the config, extract the key values you'll need:

- **REPOSITORY**: The `owner/repo` from "Repository:" line
- **AUTOMATION_ID**: The UUID from "Automation ID:" line
- **PLUGIN_SOURCE**: The plugin reference from "Plugin Source:" section
- **MANUAL_TESTING**: Whether manual testing is enabled/required
- **PROJECT_TYPE**: cli or web

## Step 0.5: Run Setup Commands

Execute any setup commands specified in the orchestration.md config.

Common setup includes:
- Installing required tools (lxa, project-specific CLIs)
- Adding the repo to lxa board
- Syncing data if the project has a sync command

```bash
# Always ensure lxa is available
which lxa || uv tool install git+https://github.com/jpshackelford/lxa.git

# Add repo to lxa board (use REPOSITORY from config)
lxa repo add $REPOSITORY 2>/dev/null || true

# Run any additional setup commands from the config
# (These are project-specific and defined in orchestration.md)
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
gh pr list --repo {REPOSITORY} --state open --json number,title,isDraft
# Output: [{"number": 42, "title": "Add --repair option", "isDraft": false}]

# 2. If a PR exists, get quick status with lxa
lxa pr list "{REPOSITORY}#42"
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Check for manual test results in PR comments
gh pr view 42 --repo {REPOSITORY} --comments | grep -i "Manual Test Results"

# 4. List issues needing expansion (no 'ready' label, no 'hold' label)
gh issue list --repo {REPOSITORY} --state open --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | (contains(["ready"]) or contains(["hold"])) | not)] | sort_by(.number)'
# Issues without 'ready' or 'hold' label need expansion

# 5. List ready issues (have 'ready' label, no 'hold' label)
gh issue list --repo {REPOSITORY} --state open --label "ready" --json number,title,labels \
  --jq '[.[] | select(.labels | map(.name) | contains(["hold"]) | not)] | sort_by(.number)'

# 6. Check for prioritized ready issues
gh issue list --repo {REPOSITORY} --state open --label "ready" --json number,title,labels \
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

The PR workflow uses **two parallel slots** and ensures **documentation is updated before testing** (so we test what's documented).

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
| PR exists, ready, CI green, test results valid, no reviews yet, `Self-review: enabled` | Spawn **self-review worker** |
| PR exists, ready, CI green, test results valid, no reviews yet, `Self-review: disabled` | Trigger/request external review; log **Waiting for Review** (not quiet) |
| PR exists, ready, CI green, test results valid, 💬 > 0 | Spawn **review worker** |
| PR exists, ready, test results valid, good rating, **docs outdated** | Spawn **docs spot-check worker** |
| PR exists, ready, test results valid, good rating, docs valid | Spawn **merge worker** |
| No open PR + ready issues with priority | Spawn **impl worker** for highest priority ready issue |
| No open PR + ready issues, no priority | Run `/assess-priority` inline, then spawn impl worker |
| No open PR + no ready issues | Nothing to implement (wait for expansion) |

### Anti-Stall: Review Gates Must Be Actionable

The decision table is exhaustive. Do **not** classify an open PR as "quiet" unless every applicable gate is either satisfied or explicitly parked by a codified hold.

The orchestrator may defer a PR/issue only when at least one of these gates is present:

1. A live `## INSTRUCTION:` block in `WORKLOG.md` explicitly defers that PR/issue.
2. A blocking label (`hold`, `blocked`, `needs-info`, `needs-split`) on the PR or tracking issue.
3. An active worker still owns the slot.
4. CI is failing/pending, manual testing is missing/outdated, docs are missing/outdated, or another documented project policy in `AGENTS.md` / `.agents/resources/*` applies.

A missing first review is **not** quiet by itself. If `Self-review: disabled`, the orchestrator must make the external review gate actionable before waiting: verify the target repo has a PR review workflow (usually `.github/workflows/pr-review.yml`), then add the `review-this` label or request `openhands-agent` if no review is present. If no review workflow exists, log a configuration error and do not auto-disable. If `Self-review: enabled`, spawn a self-review worker instead.

External review trigger checklist when `Self-review: disabled`:

```bash
# Workflow presence check. Accept equivalent filenames only if they call
# OpenHands/extensions/plugins/pr-review or otherwise produce GitHub reviews.
gh api repos/{REPOSITORY}/contents/.github/workflows/pr-review.yml >/dev/null

# Manual trigger. Create the label if missing, then add it. If the label was
# already present and no review run appears after one orchestrator tick, remove
# and re-add the label or request openhands-agent/all-hands-bot as reviewer.
gh label create review-this --repo {REPOSITORY} --color 5319E7 --description "Trigger OpenHands PR review workflow" --force
gh pr edit {number} --repo {REPOSITORY} --add-label review-this
```

After triggering review, write `⏳ **Waiting for Review**` to `WORKLOG.md`. Do not spawn another implementation worker while an open PR is waiting for its first review.


Only use `✅ **All quiet**` when there are no open actionable PRs, no ready issues, and no expansion candidates. Use `⏳ **Waiting for Review**` or another waiting status when work exists but a real gate is pending.


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
gh pr view 42 --repo {REPOSITORY} --comments | grep -iE "(README|documentation|docs).*(updated|verified|checked)"
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
' -f owner={OWNER} -f repo={REPO} -f number=42 | \
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

Before spawning a worker, check if any related conversations are still active.

If the project uses `ohtv` for conversation tracking (specified in orchestration.md), run:

```bash
# Sync recent conversations (if ohtv is available)
if command -v ohtv &> /dev/null; then
    ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet
    # Check conversations for this repo with idle time
    ohtv list --repo {REPO} --since 4h --idle 15
fi
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
Repository: {REPOSITORY}
Title: [Expansion] Issue #{issue_number} - {issue_title}
Prompt: |
  You are expanding GitHub Issue #{issue_number} for the {PROJECT}.

  **ISSUE TO EXPAND:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/{REPOSITORY}/issues/{issue_number}

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

Plugins: {PLUGIN_SOURCE}
Issue Number: {issue_number}
Worker Type: expansion
```

### Implementation Worker

**Worker Type:** `implementation`
**Slot:** PR slot (serialized with testing/review/merge)

Use when: Ready issues exist with priority labels and no open PR.

```
Repository: {REPOSITORY}
Title: [Implementation] Issue #{issue_number} - {issue_title}
Prompt: |
  You are implementing GitHub Issue #{issue_number} for the {PROJECT}.

  **ISSUE TO IMPLEMENT:**
  - Issue: #{issue_number} - {issue_title}
  - URL: https://github.com/{REPOSITORY}/issues/{issue_number}
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

Plugins: {PLUGIN_SOURCE}
Issue Number: {issue_number}
Worker Type: implementation
```

### Documentation Worker

**Worker Type:** `docs`
**Slot:** PR slot (serialized with implementation/testing/review/merge)

Use when: PR has user-facing changes but README.md hasn't been updated yet.

```
Repository: {REPOSITORY}
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

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

### Docs Spot-Check Worker (Before Merge)

Use when: PR is approved but significant review changes may have affected documented behavior.

```
Repository: {REPOSITORY}
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

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

### Testing Worker (Initial)

Use when: PR has docs updated but NO manual test results yet (even if review has already started).

```
Repository: {REPOSITORY}
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
  
  Read testing instructions from .agents/resources/testing-worker.md if available.
  If a /manual-test skill is available in this repo, follow its test report format.
  
  After posting the test report, EXIT. Do not continue to review.

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

### Re-Testing Worker (After Significant Changes)

Use when: PR has test results, but significant code changes were made AFTER the last test.

```
Repository: {REPOSITORY}
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
  
  Read testing instructions from .agents/resources/testing-worker.md if available.
  If a /manual-test skill is available in this repo, follow its test report format.
  
  After posting the re-test report, EXIT.

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

### Self-Review Worker

Use when: `Self-review: enabled` and a ready, tested PR has no first review yet.

```
Repository: {REPOSITORY}
Title: [Self Review] PR #{number} - {title}
Prompt: |
  You are performing the first review pass for PR #{number} because this project has `Self-review: enabled` and no external review exists yet.

  1. Clone the repo and inspect the PR diff, CI status, and manual test results.
  2. Review the code critically for correctness, simplicity, test coverage, docs accuracy, and scope control.
  3. If the PR needs changes, post a PR comment headed `## Self-Review` with a clear rating (`Needs work`) and bullet-pointed required fixes. Do not modify code in this worker; exit so the next orchestrator tick can route review work.
  4. If the PR is acceptable, post a PR comment headed `## Self-Review` with rating `Acceptable` or `Good`, a concise rationale, and any non-blocking follow-ups.
  5. Exit. Do not merge; the merge worker handles final merge preparation.

  The comment must include the literal rating word (`Good`, `Acceptable`, or `Needs work`) so `/prepare-and-merge` can evaluate the review gate. Include an AI disclosure line because the comment is posted to GitHub.

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```


### Review Worker

```
Repository: {REPOSITORY}
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

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

### Merge Worker

```
Repository: {REPOSITORY}
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

Plugins: {PLUGIN_SOURCE}
PR Number: {number}
```

## WORKLOG.md Updates

After each orchestrator run, append **one short status entry** to `WORKLOG.md` on `main`.

### Brevity contract

The worklog is read by humans skimming for "what happened and what's next", and by the next orchestrator wake-up scraping a small set of facts. Keep entries tight — target **10-20 lines**, not 50-100.

**Each entry MUST contain (in this order):**

1. `### YYYY-MM-DD HH:MM UTC - Orchestrator` header
2. One bold action line with a status emoji — e.g. `🚀 **Launched: Testing Worker**`, `⏳ **Waiting for Review**`, `✅ **All quiet**`, `🔒 **Auto-disabled**`, `📋 **Following Human Instructions**`
3. 1–3 short context bullets (what was spawned, why, link to the spawned conversation)
4. **Active Workers** section — this is how the next orchestrator finds running conv IDs. Render the table when workers are running, and replace it with a single `_None._` line under the heading when both slots are empty (skim-faster, and Step 2's table-row grep stays indifferent):

   ```markdown
   **Active Workers:**

   _None._
   ```

5. **Current State** — 3–6 bullets summarizing open PRs, ready/expansion-needing issues, and any blocked items. This is what a human skimming sees first.

**Do NOT include in entries:**

- Decision-tree traces / numbered "1. Read config, 2. Check workers..." rationale — that's scratchpad, not log
- "What changed since last cycle" prose diffs — the next wake-up computes state fresh from `gh`
- "Likely transitions to watch for" prophecy — the next wake-up decides based on actual state
- Repeated re-enable curl snippets, plugin paths, sandbox status codes
- Housekeeping commentary on why truncation was deferred (just truncate or don't)
- Restating the standing `## INSTRUCTION:` rules every cycle

Use `lxa pr list` shorthand (`oCR green ready 💬2`) instead of paragraphs to describe PR state.

### Template (one entry covers all cases)

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

🚀 **Launched: Testing Worker**

Testing [PR #42](https://github.com/{REPOSITORY}/pull/42): {title}
- CI green, no manual test results yet
- Conversation: https://app.all-hands.dev/conversations/{full-conv-id}

**Active Workers:**

| Conv ID | Type | Working On | Status |
|---------|------|------------|--------|
| `abc1234` | testing | PR #42 | **NEW** |

**Current State:**

- [PR #42](https://github.com/{REPOSITORY}/pull/42): `oC green ready` — testing in flight
- Ready issues: #9 (`priority:high`), #10 (`priority:medium`)
- Issues needing expansion: #11

---
```

**Variant cues** (just swap the action line and 1-3 context bullets — keep the table + Current State sections):

| Situation | Action line |
|-----------|-------------|
| Spawned an expansion worker | `🔍 **Launched: Expansion Worker**` |
| Spawned implementation | `🛠 **Launched: Implementation Worker**` |
| Spawned 2 workers in parallel | `🚀 **Launched: 2 workers in parallel**` (list both under one bullet group; add a row in **Active Workers** for _each_ worker so the next wake-up can poll both conv IDs) |
| PR worker still running, slot busy | `⏳ **PR slot busy**` (1 bullet pointing at the conversation) |
| Ready PR has no first review yet and review was requested/triggered | `⏳ **Waiting for Review**` (not quiet; do not count toward auto-disable) |
| Nothing to do this cycle | `✅ **All quiet**` (only when no actionable PRs/issues remain) |
| Auto-disabled after 2 quiet cycles | `🔒 **Auto-disabled due to inactivity**` — see `disable-automation` skill |
| Acting on a human `## INSTRUCTION:` | `📋 **Following Human Instructions**` (1 bullet stating what was done) |

The 🔍/🛠/📋 indicators above are also recognized by `truncate-worklog.md`'s productive-entry classifier, so single-worker expansion/implementation spawns and instruction-follow cycles correctly anchor the 6-hour retention window. If you add a new variant cue, mirror the indicator string into `truncate-worklog.md`'s `productive_indicators` list and the indicator table.

A worker that completes can append its own short closing entry in the same shape — header, one ✅ line, 2–4 bullets, no table.

## Auto-Disable on Consecutive Quiet Periods

Before logging an "All quiet" entry, first apply the anti-stall rule above: confirm there are no actionable PRs/issues and no pending review trigger to request. `Waiting for Review`, `PR slot busy`, configuration errors, and other real gates are not quiet and must not count toward auto-disable.

After confirming the current tick is truly quiet, check whether the previous orchestrator entry was also "All quiet". If yes, this would be the second consecutive quiet cycle → disable the automation instead of logging another quiet entry.

```bash
# Of the last 2 orchestrator entries, how many were quiet?
# Each entry contributes 1-2 matching lines: 1 header (`### … Orchestrator`)
# plus 1 body line if the entry contains "All quiet". So the last 4 matching
# lines cover the last 2 entries; if 2 of those 4 are "All quiet" body lines,
# both of the last 2 entries were quiet → second consecutive quiet → disable.
LAST=$(grep -E "(^### .*Orchestrator|All quiet)" WORKLOG.md | tail -4)
QUIET_COUNT=$(echo "$LAST" | grep -c "All quiet")
if [ "$QUIET_COUNT" -ge 2 ]; then
  # Both of the last 2 entries were quiet → invoke /disable-automation,
  # log a 🔒 entry, exit.
  :
fi
```

The disable curl, the automation ID, the WORKLOG entry shape, and the re-enable instructions all live in [`disable-automation.md`](disable-automation.md). The orchestrator just decides _when_ to disable; it does not embed the API call inline in this skill, and it does not repeat re-enable instructions into every disable entry.

## Committing WORKLOG.md Updates

**IMPORTANT:** WORKLOG.md updates go to `main`, not to any feature branch.

```bash
CURRENT_BRANCH=$(git branch --show-current)
git stash --include-untracked
git checkout main && git pull origin main
# append the entry (see Template above)
git add WORKLOG.md
git commit -m "chore(worklog): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git push origin main
if [ "$CURRENT_BRANCH" != "main" ]; then
  git checkout "$CURRENT_BRANCH" && git stash pop 2>/dev/null || true
fi
```

## Logging (stdout)

After each action, log one structured line to stdout — this is for the conversation record, not the worklog:

```
[Orchestrator] 2025-05-05T10:30:00Z action=spawn_testing pr=42 conv=abc1234 reason="CI green, no test results"
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
