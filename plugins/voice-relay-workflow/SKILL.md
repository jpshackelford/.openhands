# Voice Relay Workflow Plugin

Automated PR workflow for the [voice-relay](https://github.com/jpshackelford/voice-relay) project. Orchestrates the full development cycle with **issue expansion, prioritization, and parallel work**.

## Overview

Work items are tracked as **GitHub Issues**. Each issue goes through two phases:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PROJECT LIFECYCLE                            │
├─────────────────────────────────────────────────────────────────────┤
│  PHASE 0: EXPANSION (parallel track)                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Issue #9 (bug)     → Investigate → Root cause + fix plan    │   │
│  │ Issue #10 (feature)→ Analyze → Requirements + approach      │   │
│  │ → Label "ready" when expanded                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  PHASE 1: PRIORITIZATION                                            │
│  Assess impact/urgency → Assign priority:critical/high/medium/low   │
│                                                                      │
│  PHASE 2: IMPLEMENTATION (highest priority first)                   │
│  Issue #9 (priority:high)  → PR → Review → Merge ✓                 │
│  Issue #10 (priority:medium)→ PR → Review → Merge ✓                │
│  → ALL ISSUES CLOSED                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Parallel Work Model

The orchestrator can run **up to 7 workers simultaneously**:

| Slot Type | Max | Worker Types | Purpose |
|-----------|-----|--------------|----------|
| **Expansion** | 4 | `expansion` | Analyze issues, add technical detail |
| **Implementation** | 1 | `implementation` | Create branch, write code, open PR |
| **Review** | 2 | `review`, `merge` | Address PR feedback, fix CI, merge |

**Total: up to 7 concurrent conversations**

✅ All slot types can run in parallel
✅ Implementation not blocked by review cycle
✅ Multiple issues can be expanded simultaneously


```
New Issue → Expansion → Ready → Prioritized → Implementation → PR → Review → Merge
    │           │          │         │              │                         │
    │           │          │         │              └── PR Slot ──────────────┘
    │           │          │         │
    │           │          │         └── /assess-priority (inline)
    │           │          │
    │           │          └── Has 'ready' label
    │           │
    │           └── Expansion Slot (parallel)
    │
    └── No 'ready' label
```

## Closing-Trailer Acceptance-Criteria Gate (cross-cutting rule)

This rule applies to **every worker that touches a PR body** — implementation, review, and merge. It is loaded as plugin context for all of them.

### Why this rule exists

Auto-close trailers (`Fixes #N` / `Closes #N` / `Resolves #N`) are a **one-way door**: when a PR with such a trailer merges, GitHub closes issue N regardless of whether N's acceptance criteria are satisfied. Without this gate, "we shipped most of it, the rest is a follow-up" silently closes the original tracker — the failure mode that produced [voice-relay #386](https://github.com/jpshackelford/voice-relay/issues/386) (PR #402 used `Fixes #386` against a server-only diff while #386's acceptance criteria explicitly required client-side work; the worker's pre-merge promise to "file follow-ups once this lands" was never executed, and the tracker was auto-closed with most ACs unmet).

### The rule

Before any worker writes an auto-close trailer for issue N into a PR body — **at PR-open time, at ready-for-review time, and at merge time** — the worker MUST verify that **every non-exempt item in issue N's `## Acceptance Criteria` section is satisfied by the PR's diff**.

- **Exempt items:** AC items explicitly marked `(deferred)` / `(out of scope)` / `(follow-up)` in the issue body itself.
- **Satisfied by the diff:** the PR diff contains a concrete change a reviewer can point to that delivers the behavior the AC describes.

**Verdict matrix:**

| Result | Trailer | Follow-up issues | PR body |
|---|---|---|---|
| All non-exempt ACs satisfied | `Fixes #N` / `Closes #N` / `Resolves #N` is allowed | none required | normal |
| Any non-exempt AC unsatisfied | MUST downgrade to `Refs #N` (or `Part of #N`) | MUST file one per gap (or per coherent group) **before** the PR moves to ready-for-review | MUST include a `## Deferred to follow-ups` section listing the new issue numbers |

**Verbal promises are not sufficient.** A PR or issue comment that says "I'll file follow-ups once this lands" does not satisfy the gate. The follow-up issues must exist as GitHub issues before merge.

### Where each worker enforces the gate

| Worker | Where | When |
|---|---|---|
| Implementation (`/implement-issue`) | At PR-open time and re-check after CI green | Initial trailer decision; re-check in case of late scope shifts |
| Review (`/address-review`) | After each review round | Review feedback can flip the gate verdict in either direction |
| Merge (`/prepare-merge`) | Final hard gate before squashing | Last line of defense — block the merge if the gate fails |

### Idempotence (no duplicate follow-ups)

The gate is run **multiple times against the same PR** by design — implementation Step 9 + Step 11, every review round, and the merge worker's hard gate. It can also run concurrently (e.g. a retroactive `## INSTRUCTION:` block and a normal forward tick on the same PR in parallel — the failure mode that produced duplicates [#414–#418](https://github.com/jpshackelford/voice-relay/issues/414) on 2026-06-06).

Before filing any follow-up issue, a worker MUST enumerate the existing follow-up set and reuse it:

1. **Read the PR body's `## Deferred to follow-ups` section** — these are follow-ups recorded by an earlier gate run on this PR. Each is canonical.
2. **Search by title pattern** for follow-ups filed by parallel runs that have not yet updated the PR body:
   ```bash
   gh issue list --repo <repo> --state all \
     --search 'in:title "follow-up to #<umbrella>"'
   ```
3. **Union** of (1) and (2) is the **existing follow-up set**.

When walking the AC checklist:

- For each uncovered AC item: first check whether an issue in the existing set already covers that item (read its body). If yes, **reuse** — do not file a new one.
- For each previously-filed follow-up whose AC item is now satisfied by the current diff: leave a comment on it noting the gap was closed in this PR, and remove its number from the body's `## Deferred to follow-ups` section. Do **not** auto-close — let the next normal triage tick decide whether the issue is truly superseded or merits a separate close.

When walking finishes, the PR body's `## Deferred to follow-ups` section must list exactly the union of (a) existing follow-ups that still cover an uncovered AC, plus (b) any new follow-ups filed in this run.

The per-worker skill files (`implement-issue.md`, `address-review.md`, `prepare-and-merge.md`) carry the concrete commands. The merge worker's hard gate uses the same pre-flight to **verify** the existing set matches the gap analysis — a discrepancy is a gate failure.

### Override

The gate may be overridden only by an open `## INSTRUCTION:` block in `WORKLOG.md` (on `main` of the target repo) that explicitly names the PR number, the issue number, and the AC items being waived. The override must be recorded in the cycle's WORKLOG entry and (for merge) in the squash commit body.

## Worker Tracking via .workflow-state.json

Active workers are tracked in `.workflow-state.json` (machine-readable) and logged to `WORKLOG.md` (human-readable):

```json
{
  "slots": {
    "expansion": [
      {"conv_id": "abc1234", "issue": 10, "started": "2025-05-17T18:00:00Z"}
    ],
    "implementation": [
      {"conv_id": "def5678", "issue": 9, "started": "2025-05-17T17:30:00Z"}
    ],
    "review": []
  },
  "limits": {"expansion": 4, "implementation": 1, "review": 2}
}
```

The orchestrator queries the OH API to check if each conversation is still `running` or `finished`, then updates the state file accordingly.


## lxa for Visibility

Use `lxa` to quickly see PR status (after discovering the PR number with `gh pr list`):

```bash
# Quick PR status with history codes
lxa pr list "jpshackelford/voice-relay#<PR_NUMBER>"

# Output: oCR green ready 2
# Meaning: opened → Changes requested → Review round, CI green, 2 unresolved threads
```

## Available Skills

### Issue Expansion & Prioritization (Phase 0-1)

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Expand Issue](skills/expand-issue.md) | `/expand-issue` | Analyze issue, find root cause (bugs), add technical detail |
| [Assess Priority](skills/assess-priority.md) | `/assess-priority` | Evaluate ready issues, assign priority labels |

### Orchestration & Workers

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Orchestrate](skills/orchestrate.md) | `/orchestrate` | Main decision loop - track workers, dispatch work |
| [Spawn Conversation](skills/spawn-conversation.md) | `/spawn-conversation` | Start OH conversation via API |

### PR Lifecycle (Phase 2)

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Implement Issue](skills/implement-issue.md) | `/implement-issue` | Full implementation worker procedure (branch, code, tests, PR, AC gate) |
| [Address Review](skills/address-review.md) | `/address-review` | Full review worker procedure (resolve feedback, AC-gate re-run) |
| [PR Workflow Status](skills/pr-workflow-status.md) | `/pr-workflow-status` | Get PR state using lxa + gh |
| [Update Project Plan](skills/update-project-plan.md) | `/update-plan` | Reflect and update docs |
| [Prepare and Merge](skills/prepare-and-merge.md) | `/prepare-merge` | Final merge workflow (hard AC gate, squash, manual close) |

### CI Failure Recovery

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Fix CI Failure](skills/fix-ci-failure.md) | `/fix-ci-failure` | Diagnose + forward-fix or revert CI failures (smoke tests, deploy regressions). Escalates to `needs-human` after 3 failed attempts. |

### Automation Management

| Skill | Trigger | Purpose |
|-------|---------|---------|
| [Disable Automation](skills/disable-automation.md) | `/disable-automation` | Auto-disable on consecutive quiet periods |

## Labels Reference

| Label | Meaning |
|-------|---------|
| `ready` | Issue expanded with technical detail, ready for implementation |
| `needs-info` | Cannot proceed without more info from reporter |
| `needs-split` | Issue too large, should be broken into smaller issues |
| `blocked` | Blocked by external factors |
| `needs-human` | Stop dispatching; a human must engage before the orchestrator works on this again |
| `priority:critical` | Blocking/urgent - do immediately |
| `priority:high` | Important - do soon |
| `priority:medium` | Standard priority |
| `priority:low` | Nice to have |
| `ci-failure` | Auto-filed when a smoke-test / post-deploy check fails. Routed to `/fix-ci-failure` by the orchestrator decision table. |
| `ci-fix-attempts:1` / `:2` / `:3` | Counter incremented by `/fix-ci-failure` on each attempt. At `:3` the worker adds `needs-human` and removes `ci-failure`. |
| `flaky-test` | Set by `/fix-ci-failure` when reruns of the same commit alternate pass/fail; partner with a tracking issue for deflaking. |

## Auto-Disable Behavior

The orchestrator automatically disables itself when it detects **two consecutive "quiet" entries** in WORKLOG.md (indicating no new work to pick up). This prevents unnecessary automation runs when the project is at a natural pause point or all issues are closed.

**Automation ID:** `a0219382-2e7c-4156-9991-7b9976739a66`

To re-enable after auto-disable:
- **UI:** https://app.all-hands.dev/automations → Toggle "Voice Relay Workflow Orchestrator"
- **API:** `curl -X PATCH ".../api/automation/v1/a0219382-2e7c-4156-9991-7b9976739a66" -d '{"enabled": true}'`

## Workflow Phases

### Phase 1: Implementation (`/implement-issue`)
A worker conversation:
- Reads the GitHub issue to understand requirements and acceptance criteria
- Creates feature branch, implements with tests
- Lints, type checks, commits, pushes
- Creates draft PR — **runs the Closing-Trailer AC Gate** (see above) to decide between `Fixes #N` and `Refs #N` + follow-up issues
- Monitors CI until green
- **Reflects** and **re-runs the AC Gate** in case scope shifted late
- Moves PR to ready (triggers review bot)

### Phase 2: Review Rounds (`/address-review`)
For each review round, a worker conversation:
- Clones PR, immediately sets back to draft
- Reads all review comments deeply
- Plans response (accept most suggestions that improve quality)
- Executes changes commit-by-commit, CI check after each
- Resolves review threads with explanations
- **Reflects**: Checks if learnings impact other issues
- **Re-runs the Closing-Trailer AC Gate** — review feedback can flip the verdict (an AC may become uncovered, or vice-versa); reconcile the trailer + follow-ups before going back to ready
- Moves PR back to ready for next review

### Phase 3: Merge (`/prepare-merge`)
When merge criteria met (good rating, or 3x acceptable, or acceptable+spurious):
- Runs the **Closing-Trailer AC Gate as a hard gate** (Step 0 of `/prepare-merge`) — if it fails, do not merge: post a PR comment, drop to draft, log, exit, and let the next orchestrator tick re-route
- Studies the full diff holistically
- Updates PR description to reflect final state and the gate verdict
- Crafts conventional commit message (records gate verdict in body)
- Squash-merges
- Linked-issue handling depends on the gate verdict: `Fixes/Closes/Resolves #N` lets GitHub auto-close N; `Refs/Part-of #N` leaves N open while follow-ups drain

### Phase 4 (preemptive): CI Failure Recovery (`/fix-ci-failure`)
A post-merge smoke-test / deploy check that fails files a `ci-failure` issue (often with auto-rollback already initiated). The orchestrator decision table routes such issues to the implementation slot as **higher priority than normal feature work** — production needs to be unblocked before more changes pile on top.

A `fix-ci-failure` worker:
- Reads the issue's failed-commit SHA + workflow-run URL + rollback target
- Classifies: real regression / flaky / test infra / deferred-work dependency
- Either opens a forward-fix PR (which then runs the normal Phase 1–3 lifecycle), or opens a revert PR, or labels `flaky-test` + files a deflaking tracker
- Increments `ci-fix-attempts:N` on the issue
- At `N = 3`, escalates: adds `needs-human`, removes `ci-failure`, posts a summary of all three attempts

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
      "schedule": "*/15 * * * *",
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
