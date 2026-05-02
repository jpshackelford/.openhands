# Conversation Search Workflow Plugin

Automated PR workflow for the [conversation-search](https://github.com/OpenHands/conversation-search) project. Orchestrates the full cycle from implementation through review to merge.

## Overview

This plugin provides skills for an automated development workflow:

```
Design Doc → Implementation → CI → Review → Address Feedback → Merge
     ↑                                              │
     └──────────── Update Plan with Learnings ──────┘
```

The workflow is driven by:
1. **Orchestrator automation** - Cron job that wakes up periodically to check state and dispatch work
2. **Worker conversations** - Focused conversations spawned to do specific tasks (implement, review, merge)

## Available Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Spawn Conversation](skills/spawn-conversation.md) | `/spawn-conversation` | Start OH conversation via API |
| [PR Workflow Status](skills/pr-workflow-status.md) | `/pr-workflow-status` | Get comprehensive PR state |
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
      {"source": "github:jpshackelford/.openhands", "repo_path": "plugins/conversation-search-workflow"}
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

## Key Principles

1. **Fire and forget**: Orchestrator spawns workers but doesn't monitor them. Next wake-up assesses new state.

2. **One action per wake-up**: Orchestrator does one thing (spawn a worker or decide nothing needed) then exits.

3. **Workers are focused**: Each worker conversation has a specific job (implement, review, merge) and exits when done.

4. **Continuous learning**: Every worker reflects and updates the plan with learnings before finishing.

5. **Natural language parsing**: No special formats needed - the agent reads PRs, reviews, and docs naturally.

## Environment Variables

- `OH_API_KEY` - OpenHands API key for spawning conversations
- `GITHUB_TOKEN` - GitHub token for `gh` CLI operations
