# OHTV Workflow Plugin

Automated PR workflow for the [ohtv](https://github.com/jpshackelford/ohtv) project. Orchestrates the full development cycle: **issue → implementation → manual testing → review → merge**.

## Overview

Unlike design-document-driven projects, ohtv uses **GitHub issues and PRs exclusively** as the source of truth. The orchestrator picks up existing PRs and advances them through completion.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PR LIFECYCLE                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Implementation → CI Green → MANUAL TESTING → Review → Merge        │
│                                    ↑                                 │
│                              (REQUIRED STEP)                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Key difference from other projects:** Before code review begins, a manual testing step is **required**. The tester exercises the new functionality and posts a detailed test report as a PR comment. This enables human reviewers to understand what was tested and repeat the tests.

## lxa for Visibility

Use `lxa` to quickly see PR status (after discovering the PR number with `gh pr list`):

```bash
# Quick PR status with history codes
lxa pr list "jpshackelford/ohtv#<PR_NUMBER>"

# Output: oCR green ready 2
# Meaning: opened → Changes requested → Review round, CI green, 2 unresolved threads
```

## Available Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Spawn Conversation](skills/spawn-conversation.md) | `/spawn-conversation` | Start OH conversation via API |
| [PR Workflow Status](skills/pr-workflow-status.md) | `/pr-workflow-status` | Get PR state using lxa + gh |
| [Orchestrate](skills/orchestrate.md) | `/orchestrate` | Main decision loop |
| [Manual Test](skills/manual-test.md) | `/manual-test` | Run manual blackbox tests and post results |
| [Prepare and Merge](skills/prepare-and-merge.md) | `/prepare-merge` | Final merge workflow |

## Workflow Phases

### Phase 1: Implementation
Work originates from GitHub issues or existing PRs:
- A worker picks up a PR that's stuck (needs work, CI failing, etc.)
- Creates feature branch, implements changes with tests
- Runs lints, type checks, fixes issues
- Creates/updates PR, monitors CI until green
- Moves PR to ready for next phase

### Phase 2: Manual Testing (REQUIRED)
**This step is mandatory before code review.**

A testing worker:
- Installs the PR branch code locally (`uv sync`)
- Exercises the new functionality through blackbox testing
- Documents test setup, scenarios, expected/actual results
- Posts a detailed **Manual Test Results** comment to the PR
- The comment enables human reviewers to repeat the tests

See [Manual Test Skill](skills/manual-test.md) for the expected format.

### Phase 3: Code Review
After manual testing is documented:
- Review bot runs automatically
- Worker addresses review feedback
- Resolves threads with explanations
- Returns PR to ready for next review round

### Phase 4: Merge
When merge criteria met:
- Studies the full diff holistically
- Updates PR description to reflect final state
- Crafts conventional commit message
- Squash-merges
- Verifies on main

## Merge Criteria

A PR is ready for merge when ALL of:
1. **CI is green**
2. **Manual test results posted** as PR comment
3. **Review has acceptable/good rating** OR 3x acceptable across rounds

## Setting Up the Automation

Create a cron automation that loads this plugin:

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OHTV Workflow Orchestrator",
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/ohtv-workflow",
        "ref": "feat/ohtv-workflow-plugin"
      }
    ],
    "prompt": "/orchestrate",
    "trigger": {
      "type": "cron",
      "schedule": "*/30 * * * *",
      "timezone": "America/New_York"
    },
    "repos": [
      {"url": "https://github.com/jpshackelford/ohtv"}
    ]
  }'
```

**Note:** The `ref` field loads the plugin from the PR branch. Change to `"ref": "main"` (or remove `ref`) once the plugin PR is merged.

## Key Principles

1. **Issue/PR-driven**: No design documents - work comes from GitHub issues and PRs.

2. **Manual testing required**: Every PR must have documented manual test results before review.

3. **Fire and forget**: Orchestrator spawns workers but doesn't monitor them. Next wake-up assesses new state.

4. **One action per wake-up**: Orchestrator does one thing (spawn a worker or decide nothing needed) then exits.

5. **Workers are focused**: Each worker has a specific job (implement, test, review, merge) and exits when done.

6. **Reproducible testing**: Test reports are structured so humans can repeat the tests.

## Required Tools Setup

Install these tools before running the orchestrator:

### lxa (PR Dashboard)

```bash
uv pip install git+https://github.com/jpshackelford/lxa.git
```

Then add the repo to your lxa board:
```bash
lxa repo add jpshackelford/ohtv
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
