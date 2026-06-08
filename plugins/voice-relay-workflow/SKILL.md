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

### Override

The gate may be overridden only by an open `## INSTRUCTION:` block in `WORKLOG.md` (on `main` of the target repo) that explicitly names the PR number, the issue number, and the AC items being waived. The override must be recorded in the cycle's WORKLOG entry and (for merge) in the squash commit body.

## No prose-form `on-hold` on already-shipped work (cross-cutting rule)

This rule applies to every implementation worker (`/implement-issue`) and to any other worker that ever considers applying the `on-hold` label as an exit action. The procedural detail lives in `skills/implement-issue.md` → Step 1.5.

### Why this rule exists

The expansion → ready → implementation pipeline is asynchronous. By the time an implementation worker is dispatched against issue N, code merged by a sibling PR or a prior tick may have already satisfied N's acceptance criteria on `main`. The worker must do something about that — but what?

The orchestrator's Unblock Pass (added in #38) only lifts an `on-hold` label when it can parse a machine-form `Blocked by #N` comment whose referenced blockers are all closed. Prose like "depends on #N once it lands" or "shipped via #M but the e2e flip is tracked in #K" is deliberately ignored, so that long-form discussion in comments doesn't accidentally trigger unblocking (see `orchestrate.md` → "Unblock Pass" rationale). The cost of that safety property: an `on-hold` label applied with prose-only rationale is **un-liftable by the orchestrator**.

That made [voice-relay #446](https://github.com/jpshackelford/voice-relay/issues/446) sit open for hours after every one of its acceptance criteria had shipped to `main` (server-side via PR #450, e2e flip via PR #454, downstream tracker #433 closed). The 17:25Z implementation worker correctly recognized the work was already done and correctly avoided opening a duplicate PR (PR #451 had already raced #450 earlier — that lesson held). But its exit was wrong: it applied `on-hold` with a prose rationale instead of closing the issue, and subsequent Unblock Pass ticks left the label in place exactly as designed.

### The rule

When an implementation worker discovers, during pre-flight, that **every non-exempt acceptance-criterion item is already satisfied by code merged to `main`**, it MUST:

1. **Close the issue** with `--reason completed`, attributed to the shipping PR(s).
2. **Post an evidence comment first** listing each AC and the PR/commit that delivered it.
3. **NOT** apply `on-hold`.
4. **NOT** open a PR — even an empty-diff "documentation" PR that points at the shipping commit is wrong here; the close + comment is the artifact.

When ACs are *partially* already shipped, the worker proceeds with the remaining scope. If at Step 9 the gate still has uncovered ACs, the worker files follow-up issues per the existing Closing-Trailer AC Gate rule — and if the follow-ups themselves need to gate a `Refs` trailer, they are deferred via the **machine-form** `Blocked by #<follow-up>` comment so the Unblock Pass can act on them. Prose-form holds are never an acceptable exit.

The full pre-flight bash + table + closing-comment template live in `skills/implement-issue.md` → Step 1.5.

### Override

This rule has no override — a prose-form `on-hold` exit is always wrong because it strands the issue regardless of intent. The `## INSTRUCTION:` mechanism in `WORKLOG.md` can pause work on an issue (e.g., a human says "park this"), but pausing via INSTRUCTION is itself a machine-readable hook the orchestrator already honors; it doesn't require the `on-hold` label and doesn't require the worker to invent a rationale.

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
| `priority:critical` | Blocking/urgent - do immediately |
| `priority:high` | Important - do soon |
| `priority:medium` | Standard priority |
| `priority:low` | Nice to have |

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
