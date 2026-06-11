# PR Workflow Plugin

Generic PR workflow orchestration plugin for OpenHands automations.

## Overview

This plugin provides automated PR workflow orchestration that works with **any repository**. Project-specific configuration is provided via resource files in the target repository, not hard-coded in the plugin.

## Quick Start

### 1. Add Resource Files to Your Repository

Create `.agents/resources/orchestration.md` in your target repository:

```markdown
# Orchestration Hints

## Project
- Repository: owner/repo
- Type: cli

## Automation
- ID: your-automation-uuid-here
- Quiet threshold: 2

## Setup Commands
```bash
which lxa || uv tool install lxa
lxa repo add owner/repo 2>/dev/null || true
```

## Phases
- Issue expansion: enabled
- Priority assessment: enabled
- Manual testing: required
- Self-review: disabled

## Plugin Source
github:jpshackelford/.openhands/plugins/pr-workflow@main
```

### 2. Create the Automation

Create an automation in OpenHands Cloud that uses this plugin:

```json
{
  "name": "My Project Workflow",
  "trigger": {
    "type": "cron",
    "cron_expression": "0 */2 * * *"
  },
  "plugins": [
    {
      "source": "github:jpshackelford/.openhands",
      "repo_path": "plugins/pr-workflow",
      "ref": "main"
    }
  ],
  "repos": [
    {"url": "https://github.com/owner/repo"}
  ],
  "prompt": "/orchestrate"
}
```

## How It Works

```
┌──────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR WAKE-UP                                            │
├──────────────────────────────────────────────────────────────────┤
│  0. READ PROJECT CONFIG from .agents/resources/orchestration.md │
│  0.5. SETUP: Run setup commands from config                     │
│  0.6. HOUSEKEEPING: Truncate worklog if large (>300 lines)      │
│  1. READ WORKLOG.md for human instructions                      │
│  2. If human instructions found → follow them, then exit        │
│  3. PARSE WORKLOG.md for active workers (by conv ID)            │
│  4. CHECK which workers are still running (API query)           │
│  5. GATHER STATE: Open PRs, issues by label                     │
│  6. DECIDE what to spawn                                        │
│  7. SPAWN worker(s) if slots available and work exists          │
│  8. UPDATE WORKLOG.md with current state                        │
│  9. EXIT                                                         │
└──────────────────────────────────────────────────────────────────┘
```

## Resource Files

The plugin reads project-specific configuration from `.agents/resources/` in the target repository:

| File | Purpose | Used By |
|------|---------|---------|
| `orchestration.md` | Orchestrator configuration | `/orchestrate` |
| `implementation-worker.md` | Implementation hints | Implementation workers |
| `testing-worker.md` | Testing hints | Testing workers |
| `review-worker.md` | Review hints | Review workers |

### Why Resources Instead of AGENTS.md?

- **Focused**: Each file serves one purpose
- **Separation**: AGENTS.md stays general project context
- **Worker isolation**: Each worker type has its own hints
- **Not invocable**: Resources are read, not executed as skills

## Skills vs Resources

| Type | Location | Invocable? | Purpose |
|------|----------|------------|---------|
| **Skills** | `.agents/skills/` | Yes (`/skill-name`) | Standalone procedures |
| **Resources** | `.agents/resources/` | No | Context files read by procedures |

## Optional Target Repo Skills

For project-specific invocable procedures, add skills to your target repo:

| Skill | Purpose | When Needed |
|-------|---------|-------------|
| `manual-test.md` | CLI testing procedure | CLI tools only |
| `smoke-test.md` | Custom smoke tests | Web apps with special needs |

These are loaded alongside the plugin skills and can be invoked by workers.

## Skills Provided

| Skill | Trigger | Description |
|-------|---------|-------------|
| orchestrate | `/orchestrate` | Main orchestration loop |
| spawn-conversation | `/spawn-conversation` | Start worker conversations |
| pr-workflow-status | `/pr-status` | Get comprehensive PR status |
| expand-issue | `/expand-issue` | Analyze and expand issues |
| assess-priority | `/prioritize` | Prioritize ready issues |
| prepare-and-merge | `/merge` | Final merge workflow |
| truncate-worklog | `/truncate-worklog` | Archive old worklog entries |
| disable-automation | `/disable-automation` | Auto-disable on quiet periods |
| update-project-plan | `/reflect` | Capture learnings |

## Required Environment Variables

- `OH_API_KEY` - OpenHands API key for spawning conversations
- `GITHUB_TOKEN` - GitHub token for gh CLI operations

## Migration from Project-Specific Plugins

If you're using `ohtv-workflow`, `voice-relay-workflow`, or similar project-specific plugins:

1. Create `.agents/resources/orchestration.md` in your target repo
2. Move any `manual-test.md` skill to `.agents/skills/` in your target repo
3. Update your automation to use this generic plugin
4. Remove the old project-specific plugin reference
