# OHTV Workflow Plugin

Automated PR workflow for the [ohtv](https://github.com/jpshackelford/ohtv) project. Orchestrates the full development cycle: **issue → implementation → manual testing → review → merge**.

## Overview

Unlike design-document-driven projects, ohtv uses **GitHub issues and PRs exclusively** as the source of truth. The orchestrator picks up existing PRs and advances them through completion.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PR LIFECYCLE                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Implementation → CI Green → DOCS → TESTING → Review → Merge        │
│                                 ↑        ↑                           │
│                           (update    (test what's                    │
│                            first)     documented)                    │
└─────────────────────────────────────────────────────────────────────┘
```

**Key differences from other projects:**
1. **Documentation first**: README.md is updated BEFORE testing, so testers verify documented behavior
2. **Manual testing required**: Every PR must have documented test results before code review
3. **Spot-checks before merge**: If significant changes occurred during review, both docs and tests are re-verified

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
| [Disable Automation](skills/disable-automation.md) | `/disable-automation` | Auto-disable on consecutive quiet periods |

## Auto-Disable Behavior

The orchestrator automatically disables itself when it detects **two consecutive "quiet" entries** in WORKLOG.md (indicating no new work to pick up). This prevents unnecessary automation runs when the project is at a natural pause point.

**Automation ID:** `c202ca20-60d5-4f5b-9d53-3d7308c1d95b`

To re-enable after auto-disable:
- **UI:** https://app.all-hands.dev/automations → Toggle "OHTV Workflow Orchestrator"
- **API:** `curl -X PATCH ".../api/automation/v1/c202ca20-60d5-4f5b-9d53-3d7308c1d95b" -d '{"enabled": true}'`

## Workflow Phases

### Phase 1: Implementation
Work originates from GitHub issues or existing PRs:
- A worker picks up a PR that's stuck (needs work, CI failing, etc.)
- Creates feature branch, implements changes with tests
- Runs lints, type checks, fixes issues
- Creates/updates PR, monitors CI until green
- Moves PR to ready for next phase

### Phase 2: Documentation Update
**Documentation is updated BEFORE testing.**

A docs worker:
- Reviews the PR diff for user-facing changes
- Updates README.md with new commands, flags, options
- Ensures examples are accurate and copy-pasteable
- Posts a comment confirming docs are updated

### Phase 3: Manual Testing (REQUIRED)
**Testers verify the documented behavior works.**

A testing worker:
- Installs the PR branch code locally (`uv sync`)
- Syncs conversation history as needed (`ohtv sync -n 20/50/200`)
- **Tests README examples** to verify documentation accuracy
- Exercises the new functionality through blackbox testing
- Documents test setup, scenarios, expected/actual results
- Posts a detailed **Manual Test Results** comment to the PR

See [Manual Test Skill](skills/manual-test.md) for the expected format.

### Phase 4: Code Review
After manual testing is documented:
- Review bot runs automatically
- Worker addresses review feedback
- Resolves threads with explanations
- Returns PR to ready for next review round

### Phase 5: Spot-Checks (If Significant Changes)
Before merge, if review caused significant changes:
- **Re-testing**: Verify code changes didn't break functionality
- **Docs spot-check**: Verify README still matches actual behavior

### Phase 6: Merge
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
