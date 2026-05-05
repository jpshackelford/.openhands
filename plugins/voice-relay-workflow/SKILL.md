# Voice Relay Workflow Plugin

Automated PR workflow for the [voice-relay](https://github.com/jpshackelford/voice-relay) project. Orchestrates the full development cycle: **one GitHub Issue at a time**, each going through implementation → review → merge, until all issues are closed.

## Overview

Work items are tracked as **GitHub Issues** filed against the repository. The orchestrator works through open issues **one at a time** (lowest issue number first):

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PROJECT LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────┤
│  Issue #9:  F1: Scope messages to sessions → PR → Review → Merge ✓ │
│  Issue #10: F2: Workspace Home             → PR → Review → Merge ✓ │
│  Issue #11: F3: Session View               → PR → Review → Merge ✓ │
│  Issue #12: F4: Join via QR                → PR → Review → Merge ✓ │
│  → ALL ISSUES CLOSED                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

Each issue follows this cycle:
```
GitHub Issue → Implementation → CI → Review → Address Feedback → Merge → Issue Closed
                    ↑                                  │
                    └──── Comment learnings on issues ─┘
```

The workflow is driven by:
1. **Orchestrator automation** - Cron job that wakes up periodically to check state and dispatch work
2. **Worker conversations** - Spawned via OH API to do focused tasks (implement, review, merge)
3. **lxa for visibility** - `lxa pr list` for quick status checks

## lxa for Visibility

Use `lxa` to quickly see PR status (after discovering the PR number with `gh pr list`):

```bash
# Quick PR status with history codes
lxa pr list "jpshackelford/voice-relay#<PR_NUMBER>"

# Output: oCR green ready 2
# Meaning: opened → Changes requested → Review round, CI green, 2 unresolved threads
```

## Available Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Spawn Conversation](skills/spawn-conversation.md) | `/spawn-conversation` | Start OH conversation via API |
| [PR Workflow Status](skills/pr-workflow-status.md) | `/pr-workflow-status` | Get PR state using lxa + gh |
| [Orchestrate](skills/orchestrate.md) | `/orchestrate` | Main decision loop |
| [Update Project Plan](skills/update-project-plan.md) | `/update-plan` | Reflect and update docs |
| [Prepare and Merge](skills/prepare-and-merge.md) | `/prepare-merge` | Final merge workflow |
| [Disable Automation](skills/disable-automation.md) | `/disable-automation` | Auto-disable on consecutive quiet periods |

## Auto-Disable Behavior

The orchestrator automatically disables itself when it detects **two consecutive "quiet" entries** in WORKLOG.md (indicating no new work to pick up). This prevents unnecessary automation runs when the project is at a natural pause point or all issues are closed.

**Automation ID:** `a0219382-2e7c-4156-9991-7b9976739a66`

To re-enable after auto-disable:
- **UI:** https://app.all-hands.dev/automations → Toggle "Voice Relay Workflow Orchestrator"
- **API:** `curl -X PATCH ".../api/automation/v1/a0219382-2e7c-4156-9991-7b9976739a66" -d '{"enabled": true}'`

## Workflow Phases

### Phase 1: Implementation
A worker conversation:
- Reads the GitHub issue to understand requirements and acceptance criteria
- Creates feature branch, implements with tests
- Lints, type checks, commits, pushes
- Creates draft PR with "Fixes #N" to link to issue
- Monitors CI until green
- **Reflects**: Comments learnings on related issues if needed
- Moves PR to ready (triggers review bot)

### Phase 2: Review Rounds
For each review round, a worker conversation:
- Clones PR, immediately sets back to draft
- Reads all review comments deeply
- Plans response (accept most suggestions that improve quality)
- Executes changes commit-by-commit, CI check after each
- Resolves review threads with explanations
- **Reflects**: Checks if learnings impact other issues
- Moves PR back to ready for next review

### Phase 3: Merge
When merge criteria met (good rating, or 3x acceptable, or acceptable+spurious):
- Studies the full diff holistically
- Updates PR description to reflect final state
- Crafts conventional commit message
- Squash-merges (issue auto-closes via "Fixes #N")
- Verifies issue is closed

## Merge Criteria

A PR is ready for merge when ANY of:
- Review has **good taste** rating
- Review has **acceptable** rating AND issues raised are spurious/incorrect
- PR has received **3 acceptable** ratings across review rounds AND code is solid

## Setting Up the Automation

Create a cron automation that loads this plugin:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Voice Relay Workflow Orchestrator",
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/voice-relay-workflow",
        "ref": "add-voice-relay-workflow-plugin"
      }
    ],
    "prompt": "/orchestrate",
    "trigger": {
      "type": "cron",
      "schedule": "*/30 * * * *",
      "timezone": "America/New_York"
    },
    "repos": [
      {"url": "https://github.com/jpshackelford/voice-relay"}
    ]
  }'
```

**Note:** The `ref` field loads the plugin from the PR branch. Change to `"ref": "main"` (or remove `ref`) once the plugin PR is merged.

## Key Principles

1. **Fire and forget**: Orchestrator spawns workers but doesn't monitor them. Next wake-up assesses new state.

2. **One action per wake-up**: Orchestrator does one thing (spawn a worker or decide nothing needed) then exits.

3. **Workers are focused**: Each worker conversation has a specific job (implement, review, merge) and exits when done.

4. **Continuous learning**: Every worker reflects and updates the plan with learnings before finishing.

5. **Natural language parsing**: No special formats needed - the agent reads PRs, reviews, and docs naturally.

## Required Tools Setup

Install these tools before running the orchestrator:

### lxa (PR Dashboard)

```bash
uv pip install git+https://github.com/jpshackelford/lxa.git
```

Then add the repo to your lxa board:
```bash
lxa repo add jpshackelford/voice-relay
```

### ohtv (OpenHands Conversation Viewer)

```bash
uv pip install git+https://github.com/jpshackelford/ohtv.git
```

Sync recent conversations:
```bash
ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S) --quiet
```

## Environment Variables

- `OH_API_KEY` - OpenHands API key for spawning conversations
- `GITHUB_TOKEN` - GitHub token for `gh` CLI operations
