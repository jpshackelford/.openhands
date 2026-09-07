---
name: lxa-board-workflow
description: Daily workflow using LXA board management for unified issue/PR tracking across multiple repositories. Replaces manual Linear + GitHub scanning with a Kanban-style board.
triggers:
- lxa board
- board workflow
- daily board
- project board
- what needs attention
---

# LXA Board Workflow

This skill uses the LXA (Long Execution Agent) board management tools to provide a unified daily workflow for tracking issues and PRs across multiple repositories.

## Why Use LXA Board Instead of Separate Linear + GitHub Scans?

| Traditional Approach | LXA Board Approach |
|---------------------|-------------------|
| Scan Linear for tickets | Single `lxa board status` command |
| Scan GitHub for PRs | Automatic column placement |
| Manual state tracking | Rule-based workflow columns |
| Context switching | Unified Kanban view |

## Quick Start

```bash
# Check what needs your attention right now
lxa board status --attention

# Full board sync and status
lxa board sync && lxa board status --verbose
```

## Prerequisites

- LXA installed: `pip install lxa` or from [jpshackelford/lxa](https://github.com/jpshackelford/lxa)
- `GITHUB_TOKEN` with `repo`, `project`, and `notifications` scopes
- Board initialized (see First-Time Setup)

## First-Time Setup

### 1. Initialize the Board

```bash
# Create a new GitHub Project board
lxa board init --create "My Daily Workflow Board"

# Or connect to an existing GitHub Project
lxa board init --project-number 5
```

### 2. Add Repositories to Watch

```bash
# Add each repository you work with
lxa board config repos add owner/repo1
lxa board config repos add owner/repo2
lxa board config repos add All-Hands-AI/openhands

# Or scan all your user/org repos automatically
lxa board scan --user          # Your personal repos
lxa board scan --org myorg     # Organization repos
```

### 3. Initial Population

```bash
# Scan all watched repos and populate the board
lxa board scan

# Or limit to recent items
lxa board scan --since 30  # Last 30 days
```

## Daily Workflow

### Phase 1: Board Sync

Start each session by syncing the board with current GitHub state:

```bash
# Quick incremental sync using notifications
lxa board sync

# Full reconciliation (weekly recommended)
lxa board sync --full
```

### Phase 2: Check Attention Items

```bash
# Show items needing human attention
lxa board status --attention
```

This shows items in columns requiring action:
- **Human Review**: Draft PRs needing your review/evidence
- **Agent Refinement**: PRs with unresolved review comments
- **Final Review**: Ready PRs awaiting approval

### Phase 3: Work Through Columns

#### Items in "Human Review" (Draft PRs)

These are PRs created by agents that need human attention:

1. Check if the PR has adequate evidence
2. Review the code changes
3. Either:
   - Mark ready for review (moves to Final Review)
   - Request changes (moves to Agent Refinement)
   - Merge if approved

#### Items in "Agent Refinement"

PRs with `CHANGES_REQUESTED` review decision:

```bash
# Let LXA's refine command handle it
lxa refine https://github.com/owner/repo/pull/42
```

See [lxa-pr-refinement](../lxa-pr-refinement/SKILL.md) for details.

#### Items in "Final Review"

Non-draft PRs awaiting approval:

1. Review the PR yourself
2. Request reviews from teammates
3. Approve and merge when ready

### Phase 4: Summary

After working through items, check progress:

```bash
lxa board status --verbose
```

## Board Columns

Items flow through these columns automatically based on state:

| Column | Description | Action Needed |
|--------|-------------|---------------|
| **Icebox** | Auto-closed by stale bot | Triage: reopen or close permanently |
| **Backlog** | Ready to work | Pick up and implement |
| **Agent Coding** | Agent actively working | Monitor progress |
| **Human Review** | Draft PRs | Review evidence, gather if missing |
| **Agent Refinement** | PRs with change requests | Run `lxa refine` |
| **Final Review** | Ready PRs | Approve or request changes |
| **Approved** | Ready to merge | Merge it! |
| **Done** | Merged | 🎉 |
| **Closed** | Won't fix | Archive |

## Configuration

Board config is stored at `~/.lxa/config.toml`:

```toml
[board]
project_id = "PVT_kwHOABcd1234"
project_number = 5
username = "your-github-username"
watched_repos = ["owner/repo1", "owner/repo2"]
scan_lookback_days = 90
agent_username_pattern = "openhands"
```

### View/Modify Config

```bash
# Show current config
lxa board config

# Add a repo
lxa board config repos add owner/new-repo

# Set lookback days
lxa board config set scan_lookback_days 60
```

## Comparison with neubig/workflow daily-workflow

### What LXA Board Replaces

| daily-workflow Step | LXA Board Equivalent |
|---------------------|---------------------|
| Fetch Linear tickets | `lxa board scan` (if using GitHub Issues) |
| Priority sorting | Column-based workflow (customizable rules) |
| Check ready PRs | `lxa board status --attention` |
| Check draft PRs | Human Review column |
| Stale PR detection | Items in Final Review column |

### What LXA Board Adds

- **Unified view**: All repos in one board
- **Automatic state tracking**: Column rules detect PR state
- **Incremental sync**: Notifications-based updates
- **Persistent cache**: Offline status queries
- **Custom rules**: YAML-based workflow customization

### What Still Requires Separate Tools

- **Linear tickets**: LXA board tracks GitHub only
  - Keep using Linear for task intake
  - Create GitHub issues for implementation
- **Slack communication**: No agent access
- **Platform-specific testing**: Manual QA

## Advanced: Custom Board Rules

For complex workflows, use YAML configuration:

```yaml
# ~/.lxa/boards/custom.yaml
board:
  name: "Custom Workflow Board"

repos:
  - owner/repo1
  - owner/repo2

columns:
  - name: Needs Investigation
    color: RED
    description: "Issues requiring root cause analysis"

  - name: Ready for Agent
    color: BLUE
    description: "Issues ready for autonomous implementation"

rules:
  - column: Needs Investigation
    priority: 90
    when:
      type: issue
      $has_label: needs-investigation

  - column: Ready for Agent
    priority: 80
    when:
      type: issue
      $has_label: agent-ready
      $has_agent_assigned: false
```

Apply with:

```bash
lxa board apply --config ~/.lxa/boards/custom.yaml
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Board not syncing | Run `lxa board sync --full` |
| Missing items | Check `watched_repos` in config |
| Wrong column | Check rule priorities with `lxa board macros` |
| Stale data | Clear cache: `rm ~/.lxa/board-cache.db` |

## References

- [LXA Board Management Reference](https://github.com/jpshackelford/lxa/blob/main/doc/reference/board-management.md)
- [daily-workflow skill](https://github.com/neubig/workflow/blob/main/skills/daily-workflow/SKILL.md) (original pattern)
