# PR Workflow Plugin

Generic PR workflow orchestration plugin for OpenHands automations.

## Overview

This plugin provides automated PR workflow orchestration that works with **any repository**. Project-specific configuration is provided via resource files in the target repository, not hard-coded in the plugin.

The orchestrator watches your repository, expands and prioritizes issues, and spawns AI "workers" that implement, test, review, and merge changes automatically. This document covers both **how to use it as a contributor** and **how to set it up** for your repository.

## Table of Contents

- [For Contributors](#for-contributors)
  - [What happens when I file an issue?](#what-happens-when-i-file-an-issue)
  - [Labels that matter](#labels-that-matter)
  - [What happens when I open a PR?](#what-happens-when-i-open-a-pr)
  - [How tests, reviews, and manual QA fit together](#how-tests-reviews-and-manual-qa-fit-together)
  - [What is WORKLOG.md?](#what-is-worklogmd)
- [For Repository Maintainers](#for-repository-maintainers)
  - [Quick Start](#quick-start)
  - [How It Works](#how-it-works)
  - [Resource Files](#resource-files)
  - [Skills Provided](#skills-provided)
  - [Required Environment Variables](#required-environment-variables)
  - [Troubleshooting](#troubleshooting)

---

## For Contributors

If you're filing an issue or opening a PR in a repository that uses this orchestration plugin, here's what to expect.

### What happens when I file an issue?

When a new issue is opened, a GitHub workflow typically wakes the orchestrator automation. Once active, the orchestrator may:

1. **Expand the issue.** If the issue is light on detail, an expansion worker can rewrite it into a Problem Statement / Proposed Solution / Acceptance Criteria structure and add a technical-approach comment. Check your repository's orchestration configuration to see if issue expansion is enabled.

2. **Assess priority.** A `priority:*` label (`critical`, `high`, `medium`, `low`) may be applied to help order the work.

3. **Mark it actionable.** When an issue is expanded enough to implement, it receives the `ready` label.

4. **Pick up the work.** When a worker slot is free, the orchestrator may start an implementation worker for a `ready` issue. That worker typically opens a **draft PR** and iterates until local checks pass.

None of this is guaranteed or instantaneous. Automation outcomes depend on labels, queue/worker availability, and the orchestrator's quiet threshold. You can follow along in `WORKLOG.md`, which records orchestration decisions and worker status.

### Labels that matter

Labels are the main way humans steer (or pause) the automation:

| Label | Meaning for contributors |
| --- | --- |
| `ready` | The issue is expanded enough to implement. The orchestrator may start an implementation worker and open a draft PR. Remove or withhold it if the issue is not ready for code. |
| `hold` | **Pauses automation-driven work.** While `hold` is present, the orchestrator will not start new work on the issue. A human must remove `hold` before automation resumes. Use it to claim an issue, request discussion, or block premature implementation. |
| `needs-info` | The issue lacks enough detail to act on. It should be clarified by a human (or expansion) before it can become `ready`. |
| `needs-split` | The issue is too large for a single PR and should be broken into smaller issues before implementation. |
| `review-this` | Adding this label to a **pull request** triggers the OpenHands PR review workflow. It's a PR-level trigger, not an issue label. |

Other labels you may see — `priority:critical|high|medium|low`, `blocked`, `bug`, `enhancement`, `documentation`, `area:*`, `package:*` — help with triage and ordering but don't directly start or stop workers the way `ready` and `hold` do.

#### What `hold` and `ready` do, specifically

- **`hold` pauses automation.** It's the human override: as long as it's applied, automation-driven work on that issue should not begin. Removing it is a deliberate human action that lets the orchestrator consider the issue again.
- **`ready` means "expanded enough to implement."** It signals that the issue has actionable acceptance criteria and a worker can reasonably attempt it. It doesn't promise that work will start immediately — only that the issue is eligible.

### What happens when I open a PR?

Two things typically happen when you open or update a pull request:

#### 1. Continuous integration (always)

The repository's CI workflow (e.g., `tests.yml`) runs on every pull request. It typically installs dependencies and runs checks like linting, type checking, tests, and coverage validation. CI must be green before a change is considered merge-ready.

#### 2. OpenHands PR review (conditional)

An automated PR review workflow may run on your PR. Because it needs repository secrets, it **only runs for PRs opened from the same repository, not from forks.** When eligible, it's typically triggered when:

- a **non-draft** PR is opened,
- a draft PR is **marked ready for review**,
- the **`review-this`** label is added, or
- a review is **requested from `openhands-agent`**.

A draft PR opened from the repo will therefore not get an automated review until it's marked ready (or you add `review-this` / request the reviewer). Fork PRs run CI but don't receive the secret-dependent OpenHands review; a maintainer can bring those changes in-repo if a review is wanted.

The orchestrator may also notice your PR and record status in `WORKLOG.md`, coordinating follow-up work such as manual testing.

### How tests, reviews, and manual QA fit together

Several roles cooperate to get a change merged. Some are GitHub Actions; some are AI workers; humans can perform any of them too:

- **CI (tests workflow)** — lint, type check, tests, and coverage on every PR. The objective gate.
- **Implementation worker** — turns a `ready` issue into a draft PR, runs the local checks, updates docs for user-visible behavior, then marks the PR ready.
- **OpenHands PR review** — automated code review on eligible same-repo PRs (see above).
- **Manual testing** — Often **required** for changes to CLI behavior, examples, or user-visible library behavior. The procedure and required report format typically live in `.agents/skills/manual-test.md`: run the preflight checks, exercise the functionality, and post a PR comment that starts with exactly `Manual Test Results`.

Check your repository's configuration to understand which gates are required before merge.

### What is WORKLOG.md?

`WORKLOG.md` is the orchestration **coordination log** — an append-only operational record, not user-facing product documentation. It captures:

- orchestration decisions (which workers were launched and why),
- active and completed worker status (who's working on which issue or PR), and
- coordination context (current ready/expansion queues, PR state, blockers).

It changes frequently because workers and the orchestrator append entries as work progresses. If you want to know the *current* orchestration status — what's in flight, what's queued, what just merged — `WORKLOG.md` is the place to look. Older entries are periodically archived to keep it readable.

Because it's operational, don't rely on `WORKLOG.md` for how to *use* the project — that lives in the main `README.md` and package documentation.

### Limitations and safety notes

- **Secrets stay server-side.** Workflows use repository/organization secrets (for example the automation API key and the LLM key) that are never exposed in logs, issues, PRs, or `WORKLOG.md`. Don't paste sensitive tokens into issues, PRs, or comments.
- **Fork PRs are limited.** Secret-dependent automation — notably the OpenHands PR review — doesn't run for pull requests from forks. Forks still get CI.
- **Automation is best-effort.** Labels, worker availability, and the quiet threshold all affect whether and when the orchestrator acts. Phrasings like "may" and "can" above are deliberate.

---

## For Repository Maintainers

The following sections explain how to set up and configure the pr-workflow plugin for your repository.

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

#### Project CI workflow

Your repository needs a CI workflow (e.g., `.github/workflows/tests.yml`) that runs on pull requests. The orchestrator waits for this workflow to produce a green (passing) or red (failing) signal before proceeding with testing and merge decisions.

This workflow should:
- Run on `pull_request` events
- Install dependencies and run your project's test suite
- Run linters, type checkers, and any other code quality checks
- Report status back to GitHub (this happens automatically)

The specific implementation depends on your project (Python with pytest, Node with Jest, Go with go test, etc.), but the key requirement is that it provides a clear pass/fail signal that the orchestrator can observe via the GitHub API.

Example triggers:
```yaml
on:
  pull_request:
  push:
    branches: [main]
```

#### Orchestrator enabler workflow

This workflow "wakes up" the orchestrator automation when new issues or PRs are created. When the orchestrator auto-disables itself after consecutive quiet periods, this workflow re-enables it so work can resume.

Create `.github/workflows/enable-orchestrator.yml`:

```yaml
name: Enable Orchestrator on New Issue or PR

on:
  issues:
    types: [opened]
  pull_request:
    types: [opened, ready_for_review, reopened]
  workflow_dispatch:

jobs:
  enable-orchestrator:
    runs-on: ubuntu-latest
    steps:
      - name: Check and enable orchestrator if disabled
        env:
          OPENHANDS_API_KEY: ${{ secrets.OPENHANDS_API_KEY }}
          AUTOMATION_ID: "your-automation-uuid-here"
        run: |
          set -euo pipefail

          STATUS=$(curl -sf \
            -H "Authorization: Bearer $OPENHANDS_API_KEY" \
            "https://app.all-hands.dev/api/automation/v1/$AUTOMATION_ID" | jq -r '.enabled') || {
            echo "Error: Failed to read orchestrator status from automation API."
            exit 1
          }

          if [ "$STATUS" = "false" ]; then
            echo "Orchestrator is disabled. Enabling..."
            curl -sf -X PATCH \
              -H "Authorization: Bearer $OPENHANDS_API_KEY" \
              -H "Content-Type: application/json" \
              -d '{"enabled": true}' \
              "https://app.all-hands.dev/api/automation/v1/$AUTOMATION_ID" > /dev/null
            echo "Orchestrator enabled!"
          elif [ "$STATUS" = "true" ]; then
            echo "Orchestrator already enabled. Nothing to do."
          else
            echo "Error: Unexpected status from automation API: '$STATUS'"
            exit 1
          fi
```

Required setup for this workflow:
- Replace `your-automation-uuid-here` with your actual automation ID (from step 3 below)
- `OPENHANDS_API_KEY` must be available as a repository or organization Actions secret
- This workflow runs on issue open, PR open/ready/reopen, or manual trigger

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

## Example Implementation

For a real-world example of this orchestration workflow in action, see:

**[OpenHands/automation-kv-client](https://github.com/OpenHands/automation-kv-client)**

This repository uses the pr-workflow plugin and includes:
- Complete orchestration configuration in [`.agents/resources/orchestration.md`](https://github.com/OpenHands/automation-kv-client/blob/main/.agents/resources/orchestration.md)
- GitHub workflows for [CI testing](https://github.com/OpenHands/automation-kv-client/blob/main/.github/workflows/tests.yml), [orchestrator enablement](https://github.com/OpenHands/automation-kv-client/blob/main/.github/workflows/enable-orchestrator.yml), and [PR review](https://github.com/OpenHands/automation-kv-client/blob/main/.github/workflows/pr-review.yml)
- A comprehensive [contributor guide](https://github.com/OpenHands/automation-kv-client/blob/main/ORCHESTRATION.md) explaining the workflow from a user's perspective
- Active `WORKLOG.md` showing real orchestration decisions and worker coordination

---

## Acknowledgments

The contributor-focused sections of this README were inspired by and adapted from the [automation-kv-client orchestration guide](https://github.com/OpenHands/automation-kv-client/blob/main/ORCHESTRATION.md), which provides an excellent example of user-facing documentation for repositories using this plugin.
