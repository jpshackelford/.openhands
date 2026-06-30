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
which tkt || uv tool install git+https://github.com/jpshackelford/tickster
tkt repo add owner/repo 2>/dev/null || true
```

## Phases
- Issue expansion: enabled
- Priority assessment: enabled
- Manual testing: required
- Self-review: disabled
- Docs update before testing: enabled

## Plugin Source
github:jpshackelford/.openhands/plugins/pr-workflow@main
```

### 2. Add Required Repository Workflows

The generic workflow assumes the target repository has three separate GitHub
Actions concerns wired up:

| Workflow | Purpose | Required? |
|----------|---------|-----------|
| Project CI, for example `tests.yml` | Produces the green/red signal the orchestrator waits on before testing/review/merge | Yes |
| Orchestrator enabler, for example `enable-orchestrator.yml` | Re-enables the OpenHands automation when new issues or PRs arrive after auto-disable | Recommended |
| PR review, for example `pr-review.yml` | Produces the review/approval/rating gate required before merge | Required when `Self-review: disabled` |

Do not treat the orchestrator enabler as a replacement for CI or PR review. It
is intentionally a small workflow that toggles the automation back on; it does
not test code and it does not review PRs.

#### PR review workflow

If `orchestration.md` says `Self-review: disabled`, install an external review
workflow like the one used by `OpenHands/hfox-sync-daemon` and
`jpshackelford/ohtv`:

```yaml
name: PR Review by OpenHands

on:
  pull_request:
    types: [opened, ready_for_review, labeled, review_requested]

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  pr-review:
    if: |
      github.event.pull_request.head.repo.full_name == github.repository &&
      (
        (github.event.action == 'opened' && github.event.pull_request.draft == false) ||
        github.event.action == 'ready_for_review' ||
        (github.event.action == 'labeled' && github.event.label.name == 'review-this') ||
        (
          github.event.action == 'review_requested' &&
          github.event.requested_reviewer.login == 'openhands-agent'
        )
      )
    concurrency:
      group: pr-review-${{ github.event.pull_request.number }}
      cancel-in-progress: true
    runs-on: ubuntu-24.04
    steps:
      - name: Run PR Review
        uses: OpenHands/extensions/plugins/pr-review@main
        with:
          llm-model: litellm_proxy/claude-sonnet-4-5-20250929
          llm-base-url: https://llm-proxy.app.all-hands.dev
          review-style: roasted
          llm-api-key: ${{ secrets.LLM_API_KEY }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

Required setup for this workflow:

- `LLM_API_KEY` must be available as a repository or organization Actions
  secret.
- Create a `review-this` label for manual retriggers.
- For an existing PR that was opened before this workflow existed, rebase or
  update the PR branch onto a base commit that contains the workflow, then add
  `review-this` or request `openhands-agent` as reviewer. A label event created
  before the workflow is present will not retroactively run review.

Without either this review workflow or a self-review fallback, the orchestrator
can get a PR to `ready + CI green + Manual Test Results` and then stall: the
merge worker requires an acceptable/good review signal, but no automation exists
to create it.


### 3. Create the Automation

Create an automation in OpenHands Cloud that uses this plugin:

```json
{
  "name": "My Project Workflow",
  "trigger": {
    "type": "cron",
    "schedule": "0 */2 * * *",
    "timezone": "UTC"
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

## Troubleshooting

### Ready PR stalls after manual testing

Symptom: `WORKLOG.md` shows a PR is `ready`, CI is green, and `Manual Test
Results` exists, but the orchestrator logs `All quiet` or auto-disables instead
of merging.

Most likely cause: `Self-review: disabled` is configured but the repository has
no working `pr-review.yml` workflow, or the PR was opened before the workflow
existed and has not been retriggered. The generic merge worker requires an
acceptable/good review signal before merging. Install the PR review workflow
above, verify `LLM_API_KEY` is available, and retrigger review with the
`review-this` label or a reviewer request.

If the repository intentionally does not use external PR review automation, do
not leave `Self-review: disabled`; add a project-specific self-review/review
fallback before relying on this orchestrator to merge PRs.

## Migration from Project-Specific Plugins

If you're using `ohtv-workflow`, `voice-relay-workflow`, or similar project-specific plugins:

1. Create `.agents/resources/orchestration.md` in your target repo
2. Move any `manual-test.md` skill to `.agents/skills/` in your target repo
3. Update your automation to use this generic plugin
4. Remove the old project-specific plugin reference
