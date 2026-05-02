# Conversation Search Workflow Plugin

Automated PR workflow for the [conversation-search](https://github.com/OpenHands/conversation-search) project. Orchestrates the full development cycle: **multiple PRs**, each going through implementation → review → merge, until the project is complete.

## Overview

The project has a design doc with multiple work items. The orchestrator works through them **one PR at a time**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PROJECT LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────┤
│  Work Item 1 → PR #1 → Review Rounds → Merge ✓                      │
│  Work Item 2 → PR #2 → Review Rounds → Merge ✓                      │
│  Work Item 3 → PR #3 → Review Rounds → Merge ✓                      │
│  ...                                                                 │
│  Work Item N → PR #N → Review Rounds → Merge ✓ → PROJECT COMPLETE  │
└─────────────────────────────────────────────────────────────────────┘
```

Each PR follows this cycle:
```
Design Doc → Implementation → CI → Review → Address Feedback → Merge
     ↑                                              │
     └──────────── Update Plan with Learnings ──────┘
```

The workflow is driven by:
1. **Orchestrator automation** - Cron job that wakes up periodically to check state and dispatch work
2. **Worker conversations** - Spawned via OH API to do focused tasks (implement, review, merge)
3. **lxa for visibility** - `lxa pr list` for quick status checks

## lxa for Visibility

Use `lxa` to quickly see PR status (after discovering the PR number with `gh pr list`):

```bash
# Quick PR status with history codes
lxa pr list "OpenHands/conversation-search#<PR_NUMBER>"

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

## Workflow Phases

### Phase 1: Implementation
A worker conversation:
- Reads the design doc to find next pending work item
- Creates feature branch, implements with tests (>80% coverage)
- Lints, type checks, commits, pushes
- Creates draft PR, monitors CI until green
- **Reflects**: Updates plan with learnings, marks progress
- Moves PR to ready (triggers review bot)

### Phase 2: Review Rounds
For each review round, a worker conversation:
- Clones PR, immediately sets back to draft
- Reads all review comments deeply
- Plans response (accept most suggestions that improve quality)
- Executes changes commit-by-commit, CI check after each
- Resolves review threads with explanations
- **Reflects**: Checks if learnings impact the plan
- Moves PR back to ready for next review

### Phase 3: Merge
When merge criteria met (good rating, or 3x acceptable, or acceptable+spurious):
- Studies the full diff holistically
- Updates PR description to reflect final state
- Crafts conventional commit message
- Squash-merges
- Updates plan: marks complete, identifies next item

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
    "name": "Conversation Search Workflow Orchestrator",
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/conversation-search-workflow",
        "ref": "add-conversation-search-workflow-plugin"
      }
    ],
    "prompt": "/orchestrate",
    "trigger": {
      "type": "cron",
      "schedule": "*/30 * * * *",
      "timezone": "America/New_York"
    },
    "repos": [
      {"url": "https://github.com/OpenHands/conversation-search"}
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

## Environment Variables

- `OH_API_KEY` - OpenHands API key for spawning conversations
- `GITHUB_TOKEN` - GitHub token for `gh` CLI operations
