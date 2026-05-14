---
name: orchestrate
description: Main orchestration logic - assess state and dispatch work
triggers:
  - /orchestrate
---

# Orchestrate PR Workflow

Main orchestration logic for the lxa PR workflow. This skill is designed to run as a scheduled automation that wakes up periodically to assess state and dispatch work.

## Usage

```
/orchestrate
```

This skill runs automatically via cron automation. It:
1. **CHECK FOR HUMAN INSTRUCTIONS FIRST** - Read WORKLOG.md for any `## INSTRUCTION:` entries
2. If human instructions exist, follow them before doing anything else
3. Discovers any open PRs for the repo
4. Checks PR status (CI, reviews, refinement status)
5. Decides what action is needed based on current state
6. Spawns a worker conversation or runs `lxa refine` if work is available
7. Appends status update to WORKLOG.md on main
8. Exits (next check happens on next cron trigger)

## Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  1. READ WORKLOG.md for human instructions (FIRST!)             │
│  2. If human instructions found → follow them, then exit        │
│  3. Check PR status with lxa pr list + gh                       │
│  4. Check for unresolved review threads                          │
│  5. Decide: Is there work to dispatch?                           │
│  6. If yes: spawn worker or run lxa refine                       │
│  7. Append status update to WORKLOG.md (on main!)               │
│  8. Exit                                                         │
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

## Step 2: Gather State

Use `gh` to discover open PRs, `lxa` for quick status:

```bash
# 1. Discover open PRs
gh pr list --repo jpshackelford/lxa --state open --json number,title,isDraft,url

# 2. For each PR, get status with lxa
lxa pr list "jpshackelford/lxa#42" --title
# Output: oCR green ready 2
# History codes: o=opened, C=changes requested, F=fixes pushed, A=approved, m=merged

# 3. Check PR review status
gh pr view 42 --repo jpshackelford/lxa --json reviewDecision,reviews
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

## Step 3: Decision Tree

### Priority Order (evaluate top to bottom)

| Priority | Current State | Action |
|----------|---------------|--------|
| 1 | PR exists, CI failing | Wait or spawn **fix worker** |
| 2 | PR exists, draft, CI green | Run `lxa refine --phase self-review` |
| 3 | PR ready, CI green, 💬 > 0 | Run `lxa refine --phase respond` |
| 4 | PR ready, CI green, approved | Spawn **merge worker** or run with `--auto-merge` |
| 5 | PR merged | Log completion, move to next PR |
| 6 | No open PRs, issues exist | Spawn **implementation worker** |

### LXA Refinement Integration

LXA's refinement handles the self-review and review-response cycles automatically:

```bash
# For draft PRs with passing CI - self-review phase
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase self-review

# For PRs with unresolved review threads - respond phase
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase respond

# Auto-detect phase and optionally merge when ready
lxa refine https://github.com/jpshackelford/lxa/pull/42 --auto-merge
```

### Workflow Sequence

```
Implementation → CI Green → Self-Review → Human Review → Respond → Approval → Merge
                              ↑                           ↑
                        (lxa refine                 (lxa refine
                         --phase self-review)       --phase respond)
```

## Avoiding Duplicate Work

Before spawning a worker or running refinement, check if related work is already in progress:

```bash
# Check for active lxa background jobs
lxa job list --running

# If a refinement job is already running for this PR, skip
lxa job list | grep "refine.*#42" && echo "Already refining PR #42"
```

## Worker Prompts

### CI Fix Worker

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
  7. Exit - refinement will handle the rest

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
  2. Verify CI is green and approval is present
  3. Review the full PR diff
  4. Update PR description to reflect final state
  5. Craft a conventional commit message for squash-merge:
     - feat: / fix: / chore: / refactor: as appropriate
     - Clear summary line
     - Body with relevant details
  6. Squash and merge: gh pr merge {number} --squash --body "commit message"
  7. Verify the merge succeeded
  8. Exit

Plugins: github:jpshackelford/.openhands/plugins/lxa-workflow@feat/lxa-workflow-plugin
PR Number: {number}
```

## WORKLOG.md Updates

After each orchestrator run, append a status update to `WORKLOG.md` in the repo root.

### Log Entry Format

```markdown
### 2025-05-05 10:30 UTC - Orchestrator

**Current State:**
- [PR #42](https://github.com/jpshackelford/lxa/pull/42): `oC green ready`
  - History: opened → changes requested
  - Review status: 💬2 unresolved threads

**Action Taken:**
🔄 Running `lxa refine --phase respond`
- PR has unresolved review threads

---
```

### When Running LXA Refinement

```markdown
### 2025-05-05 14:00 UTC - Orchestrator

🔄 **Running: LXA Refinement (self-review)**

Refining [PR #42](https://github.com/jpshackelford/lxa/pull/42): Add board management
- CI is green, draft PR ready for self-review
- Command: `lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase self-review`

---
```

### When No Action Needed

```markdown
### 2025-05-05 14:30 UTC - Orchestrator

✅ **All quiet** - No action needed

- [PR #42](https://github.com/jpshackelford/lxa/pull/42): Waiting for review
  - Refinement: Self-review complete
  - Review: In progress (awaiting reviewer)
- No active lxa jobs found

---
```

## Auto-Disable on Consecutive Quiet Periods

**CRITICAL:** Before logging a "quiet" entry, check if WORKLOG.md already shows two consecutive quiet entries. If so, disable the automation instead of running indefinitely.

### Automation ID

**NOTE:** Update this ID after creating the automation.

```
<AUTOMATION_ID_PLACEHOLDER>
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
