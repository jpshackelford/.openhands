---
name: shepherd
description: Get situational awareness on active PRs. Discovers PRs from today's agent work via ohtv, adds them to a board via lxa, analyzes status using history codes, and reports recommendations. Does NOT take action - use action skills (/shepherd-advance, /shepherd-fix-ci, etc.) to act on recommendations.
triggers:
- /shepherd
- /shepherd-status
---

# PR Shepherd - Situational Awareness

Discover, track, and analyze PRs. Reports what needs attention with recommended actions.

## When to Use

- Scheduled periodic check-in (cron/automation entry point)
- "What PRs need attention?"
- "Show me active work"
- "Check on my PRs"
- Beginning of a work session

## What This Skill Does

1. **Discovers** PRs from recent agent work (via ohtv)
2. **Tracks** them on a board (via lxa board)
3. **Analyzes** status using history codes (via lxa pr list)
4. **Reports** what needs attention with recommended actions

**This skill does NOT take action.** Use action skills to execute recommendations:
- `/shepherd-advance` - Auto-determine and take next action
- `/shepherd-fix-ci` - Fix CI failures
- `/shepherd-respond` - Respond to review comments
- `/shepherd-self-review` - Self-review draft PRs
- `/shepherd-merge` - Merge ready PRs

## Prerequisites

Required tools:
- `ohtv` - OpenHands Trajectory Viewer
- `lxa` - Long Execution Agent CLI  
- `gh` - GitHub CLI

Install if needed:
```bash
uv tool install git+https://github.com/jpshackelford/ohtv.git
uv tool install git+https://github.com/jpshackelford/lxa.git
```

## Workflow

### Step 1: Discover PRs from Today's Work

```bash
# Sync cloud conversations (gets latest trajectory data)
ohtv sync --process --quiet

# Get PRs with write actions from today
ohtv refs -D --prs-only --write-only -1
```

Output: List of PR URLs, one per line.

**Variations:**
```bash
# PRs from this week
ohtv refs -W --prs-only --write-only -1

# PRs that pushed to a specific repo
ohtv refs -D --action pushed --repo owner/repo --prs-only -1

# All PRs touched today (including read-only)
ohtv refs -D --prs-only -1
```

### Step 2: Track PRs on Board

```bash
# Add each discovered PR to the board
lxa board add-item <PR_URL>

# Or batch add
lxa board add-item owner/repo#123 owner/repo#456
```

The board auto-assigns columns based on PR state (draft → Human Review, ready → Final Review, etc.).

### Step 3: Analyze Status

```bash
# Get PR status with history codes
lxa pr list --title
```

**Output columns:**
| Column | Values | Meaning |
|--------|--------|---------|
| History | `oRfA...` | Lifecycle codes (see `/shepherd-codes`) |
| CI | 🟢/🔴/⏳/⚠️ | green/red/pending/conflict |
| State | draft/ready/merged/closed | PR state |
| 💬 | 0, 1, 2... | Unresolved review thread count |

**Additional status commands:**
```bash
# Board overview
lxa board status --attention

# Review queue (PRs needing your review)
lxa review --all
```

### Step 4: Report Recommendations

For each PR, determine the recommended action based on:

1. **CI Status** (highest priority)
2. **Unresolved Threads**
3. **History Code** (what just happened)
4. **PR State** (draft vs ready)

## Decision Framework

| Condition | Recommendation | Action Skill |
|-----------|----------------|--------------|
| CI = RED | Fix CI failure | `/shepherd-fix-ci` |
| CI = CONFLICT | Resolve merge conflicts | `/shepherd-fix-ci` |
| CI = PENDING > 30min | Check for stuck build | Manual investigation |
| Threads > 0 | Respond to reviews | `/shepherd-respond` |
| History ends `A`, CI green | Ready to merge | `/shepherd-merge` |
| History ends `R` | Address review feedback | `/shepherd-respond` |
| History ends `f` | Wait for reviewer | No action (inform user) |
| Draft + CI green | Self-review | `/shepherd-self-review` |
| Ready, stalled > 48h | Escalate | Manual (ping reviewers) |
| `m` (merged) | Done | Remove from tracking |
| `k` (killed) | Closed | Investigate if unexpected |

## Output Format

Report findings as a structured table:

```
PR Shepherd Status Report
=========================

Discovered 3 PRs from today's work.

| PR | History | CI | State | 💬 | Recommendation | Action |
|----|---------|-----|-------|-----|----------------|--------|
| owner/repo#123 | oRf | 🟢 | draft | 2 | Respond to reviews | /shepherd-respond |
| owner/repo#456 | oRfA | 🟢 | ready | 0 | Ready to merge | /shepherd-merge |
| owner/repo#789 | o | 🔴 | draft | 0 | Fix CI failure | /shepherd-fix-ci |

Summary:
- 1 PR needs review response
- 1 PR ready to merge  
- 1 PR has CI failure

Next steps:
- Run `/shepherd-advance owner/repo#123` to respond to reviews
- Run `/shepherd-merge owner/repo#456` to merge
- Run `/shepherd-fix-ci owner/repo#789` to fix CI
```

## History Codes Quick Reference

| Code | Meaning | lowercase=you, UPPERCASE=other |
|------|---------|--------------------------------|
| `o` | Opened | — |
| `r`/`R` | Changes requested | |
| `f`/`F` | Fixes pushed | |
| `a`/`A` | Approved | |
| `c`/`C` | Comment | |
| `m` | Merged | |
| `k` | Killed (closed) | |

**Common patterns:**
- `oRf` → Fixes pushed, awaiting re-review
- `oRfA` → Approved after fixes, ready to merge
- `oRfRf` → Multiple review cycles, still iterating

See `/shepherd-codes` for complete reference.

## Example Session

```bash
# 1. Discover
$ ohtv refs -D --prs-only --write-only -1
https://github.com/owner/repo/pull/123
https://github.com/owner/repo/pull/456

# 2. Track
$ lxa board add-item owner/repo#123 owner/repo#456
Added 2 items to board

# 3. Analyze
$ lxa pr list --title
┌─────────┬─────────┬───────┬────┬─────────────────────────────────┐
│ History │ CI      │ State │ 💬 │ PR                              │
├─────────┼─────────┼───────┼────┼─────────────────────────────────┤
│ oRf     │ 🟢 green│ draft │ 2  │ owner/repo#123 Add feature X    │
│ oA      │ 🟢 green│ ready │ 0  │ owner/repo#456 Fix bug Y        │
└─────────┴─────────┴───────┴────┴─────────────────────────────────┘

# 4. Report
PR #123: History oRf, 2 threads → Recommend: /shepherd-respond
PR #456: History oA, approved → Recommend: /shepherd-merge
```

## Integration with Scheduled Jobs

For automated check-ins, the scheduler invokes `/shepherd` which:
1. Runs the discovery/analysis workflow
2. Reports findings
3. Agent then invokes appropriate action skills based on recommendations

The separation of awareness from action allows for:
- Human review of recommendations before action
- Selective action on specific PRs
- Batch processing via `/shepherd-advance --all`

## Related Skills

- `/shepherd-advance` - Advance a PR (auto-determines action)
- `/shepherd-fix-ci` - Fix CI failures
- `/shepherd-respond` - Respond to review comments
- `/shepherd-self-review` - Self-review draft PRs
- `/shepherd-merge` - Merge ready PRs
- `/shepherd-codes` - History code reference
- `/babysit-pr` - Intensive single-PR monitoring (external skill)
