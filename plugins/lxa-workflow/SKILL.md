# LXA Workflow Plugin

Automated PR orchestration for the [jpshackelford/lxa](https://github.com/jpshackelford/lxa) project.

## What This Plugin Does

This plugin provides **automated orchestration** for the lxa development workflow:

1. **Discovers work** - checks for open issues and active PRs
2. **Assesses state** - determines what needs attention (CI failures, review comments, ready to merge)
3. **Dispatches workers** - spawns OpenHands conversations to handle specific tasks
4. **Monitors progress** - tracks PR status and worklog entries
5. **Maintains housekeeping** - archives old worklogs, captures learnings

## About LXA

LXA (Long Execution Agent) is a command-line tool for autonomous long-horizon task execution. Key features:

- **Design-driven implementation** - uses `.pr/design.md` documents for persistent context
- **PR refinement** - automated self-review and review response via `lxa refine`
- **Board management** - tracks issues/PRs on GitHub Projects via `lxa board`
- **Background jobs** - manages long-running tasks via `lxa job`

Install: `uv tool install git+https://github.com/jpshackelford/lxa.git`

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **orchestrate** | `/orchestrate` | Main entry point - assess state and dispatch work |
| **spawn-conversation** | `/spawn-conversation` | Start an OpenHands worker conversation |
| **pr-workflow-status** | `/pr-status` | Get comprehensive PR status |
| **prepare-and-merge** | `/merge` | Final merge preparation and execution |
| **expand-issue** | `/expand-issue` | Analyze and expand a GitHub issue |
| **assess-priority** | `/prioritize` | Prioritize ready issues for implementation |
| **truncate-worklog** | `/truncate-worklog` | Archive old worklog entries |
| **update-project-plan** | `/update-plan` | Reflect on learnings, update issue comments |
| **disable-automation** | `/disable-automation` | Auto-disable on quiet periods |

## Quick Start

### Prerequisites

```bash
# Install required tools
uv tool install git+https://github.com/jpshackelford/lxa.git
gh auth login
```

### Manual Usage

```bash
# Run orchestration manually
/orchestrate
```

### Automated Usage

Set up a cron automation that loads this plugin and runs `/orchestrate` on a schedule.

## Orchestration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    /orchestrate Entry Point                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Issue Lifecycle                                         │
│                                                                  │
│   New Issues ──► /expand-issue ──► Add 'ready' label            │
│   Ready Issues ──► /assess-priority ──► Add priority labels     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: PR Lifecycle                                            │
│                                                                  │
│   Draft PRs ──► /refine --phase self-review                     │
│   PRs with reviews ──► /refine --phase respond                  │
│   Approved PRs ──► /merge                                        │
│   CI failures ──► /spawn-conversation to fix                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Housekeeping                                            │
│                                                                  │
│   /truncate-worklog ──► Archive old entries                     │
│   /update-plan ──► Capture learnings as issue comments          │
└─────────────────────────────────────────────────────────────────┘
```

## Issue Lifecycle

Issues progress through states managed by GitHub labels:

```
New Issue                 Expanded Issue              Implementation
    │                          │                           │
    ▼                          ▼                           ▼
[no labels]    ──►    [ready] + [priority:*]    ──►    PR Created
    │                          │
    └── /expand-issue ─────────┘
              │
              └── /assess-priority
```

### Issue Expansion (`/expand-issue`)

For bugs:
- Identifies root cause location
- Documents reproduction steps
- Lists files likely needing changes

For enhancements:
- Scopes the work required
- Identifies affected components
- Estimates complexity

### Priority Assessment (`/assess-priority`)

Evaluates `ready` issues and assigns priority labels:

| Label | Criteria |
|-------|----------|
| `priority:critical` | Blocking issue, production impact |
| `priority:high` | Important feature or significant bug |
| `priority:medium` | Standard priority |
| `priority:low` | Nice to have |

## PR Lifecycle

PRs progress through phases managed by **worker conversations** spawned by the orchestrator:

### Self-Review Phase

For draft PRs with passing CI, the orchestrator spawns a **self-review worker** that:
- Reviews the code against quality principles
- Fixes any issues found
- Marks the PR ready for human review
- Posts a self-review comment documenting what was checked

### Review Response Phase

For PRs with unresolved review threads (💬 > 0), the orchestrator spawns a **review response worker** that:
- Sets PR back to draft
- Reads all review comments
- Addresses each piece of feedback
- Commits fixes with clear messages
- Replies to review threads
- Marks PR ready again

### Merge Phase

For approved PRs, the orchestrator spawns a **merge worker** that:
- Verifies all checks pass
- Crafts a conventional commit message
- Squash merges the PR

Worker prompts are defined in the `/orchestrate` skill.

## Parallel Work Model

The orchestrator can track multiple parallel work streams:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Parallel Work Tracking                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Issue #42 ──► PR #50 (Draft, CI Green)                        │
│                    └── Status: Self-review in progress           │
│                                                                  │
│   Issue #43 ──► PR #51 (Ready, Has Reviews)                     │
│                    └── Status: Responding to feedback            │
│                                                                  │
│   Issue #44 ──► [No PR yet]                                     │
│                    └── Status: Ready for implementation          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Status Tracking in WORKLOG.md

```markdown
## Active Work

| Issue | PR | Status | Last Update |
|-------|-----|--------|-------------|
| #42 | #50 | self-review | 2024-01-15 10:30 |
| #43 | #51 | responding | 2024-01-15 11:00 |
| #44 | - | ready | 2024-01-15 09:00 |
```

## Labels Reference

| Label | Meaning |
|-------|---------|
| `ready` | Issue expanded with technical detail, ready for implementation |
| `needs-info` | Cannot proceed without more info from reporter |
| `needs-split` | Issue too large, should be broken into smaller issues |
| `blocked` | Blocked by external factors |
| `hold` | Issue should not be implemented yet (human decision) |
| `priority:critical` | Blocking/urgent - do immediately |
| `priority:high` | Important - do soon |
| `priority:medium` | Standard priority |
| `priority:low` | Nice to have |

## Auto-Disable Behavior

The orchestrator automatically disables itself when it detects **two consecutive "quiet" entries** in WORKLOG.md (indicating no new work to pick up). This prevents unnecessary automation runs when the project is at a natural pause point.

## LXA CLI Reference

Key commands used by this workflow:

```bash
# PR Status
lxa pr list "owner/repo#42" --title    # Get PR status with history codes

# Board Management (optional)
lxa board status --attention           # What needs attention
lxa board sync                         # Sync with GitHub state

# Development
make check                             # Run all quality checks
make lint                              # Run linter
make typecheck                         # Run type checker
make test                              # Run tests
```

## Setting Up the Automation

Create a cron automation that loads this plugin:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "LXA Workflow Orchestrator",
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/lxa-workflow",
        "ref": "feat/lxa-workflow-plugin"
      }
    ],
    "prompt": "/orchestrate",
    "trigger": {
      "type": "cron",
      "schedule": "15,45 * * * *",
      "timezone": "America/New_York"
    },
    "repos": [
      {"url": "https://github.com/jpshackelford/lxa"}
    ]
  }'
```

This runs the orchestrator every 30 minutes (at :15 and :45 past each hour).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OH_API_KEY` | Yes | OpenHands API key for spawning conversations |
| `GITHUB_TOKEN` | Yes | GitHub token for gh CLI operations |
