---
name: fix-ci-failure
description: Worker procedure for diagnosing and fixing CI failures (smoke tests, deploy failures, post-merge regressions). Escalates to needs-human after repeated failed attempts.
triggers:
  - /fix-ci-failure
  - /fix-ci
---

# Fix CI Failure

Full procedure for the **CI-failure worker**. Dispatched by the orchestrator when an issue carries the `ci-failure` label without `needs-human`. Investigates the failed run, attempts a forward fix or a clean rollback verification, and escalates to `needs-human` only after the attempt counter passes the threshold.

## Triggering issues

Two common shapes:

- **Smoke test failure after deploy** (auto-filed). Issue body contains: `Failed Commit: <sha>`, `Workflow Run: <url>`, `Automatic rollback initiated to commit <sha>`. Production is already on the rollback target; the question is whether to forward-fix or accept the rollback as resolution.
- **Post-merge regression discovered later** (human or bot filed). May or may not have an auto-rollback. The PR responsible may need a revert or a forward fix.

This skill handles both.

## Escalation policy (attempt counter)

The worker attempts a fix in **up to 3 cycles** per issue. Each attempt:

1. Increments a counter label on the issue: `ci-fix-attempts:1` → `ci-fix-attempts:2` → `ci-fix-attempts:3`.
2. Logs a WORKLOG entry titled `CI failure fix attempt N for issue #<N> — <verdict>`.

When the counter reaches **3**, the worker:

- Adds `needs-human` to the issue.
- Posts a summary comment listing all three attempts (with conversation links and verdicts).
- Removes the `ci-failure` label so the orchestrator's decision table no longer routes it to a new fix worker.
- Exits.

The orchestrator's decision table treats `needs-human` as "stop dispatching" (existing convention). A human can re-engage by removing `needs-human` and adding back `ci-failure` after they've contributed context or unblocked the underlying problem.

## Production Context

The voice-relay app auto-deploys to **vr.chorecraft.net** on every merge to `main`. There is a smoke-test → auto-rollback pipeline downstream of deploy. When a smoke test fails, production goes back to the prior commit automatically — but the failing commit stays on `main`. That means: the next merge to `main` is going to deploy the failing commit AGAIN, on top of whatever new change you make. Forward-fixes must be designed accordingly (don't leave a broken commit on `main` and assume the rollback is permanent).

## Procedure

The procedure below is presented in reading order. Headings are stable names — cross-references in this skill, in the orchestrator dispatch template, and in other worker skills target section names. See `SKILL.md` → "Procedure section naming convention" for the rationale.

1. **Read the issue**
2. **Pull workflow logs**
3. **Classify the failure**
4. **Forward-fix verdict**
5. **Revert verdict**
6. **Flaky-test verdict**
7. **Test-infra verdict**
8. **Deferred-work verdict**
9. **WORKLOG entry**
10. **Exit**

Sections 4–8 are mutually exclusive verdicts — pick one based on **Classify the failure** and skip the others. **WORKLOG entry** and **Exit** always run.

### Read the issue

```bash
gh issue view ISSUE_NUMBER --repo jpshackelford/voice-relay --json body,labels,comments
```

Extract:

- **Failed commit SHA** (look for `Failed Commit:` in the body).
- **Workflow run URL** (look for `Workflow Run:` or follow the auto-generated link).
- **Rollback target SHA** (look for `Automatic rollback initiated to commit`).
- **Current attempt counter** (look for `ci-fix-attempts:N` in `labels`).

If `ci-fix-attempts:N` is already at 3, the issue should have `needs-human` and not be in this worker's queue — bail out with a WORKLOG entry noting the dispatch was unexpected.

### Pull workflow logs

```bash
RUN_ID=$(echo "$WORKFLOW_URL" | grep -oE '[0-9]+$')
gh run view "$RUN_ID" --repo jpshackelford/voice-relay --log-failed | head -500
```

If the smoke test produced artifacts (screenshots, server logs), download them:

```bash
gh run download "$RUN_ID" --repo jpshackelford/voice-relay --name smoke-artifacts -D /tmp/smoke-artifacts
```

Read enough to understand: which test failed, what assertion / error, and (for runtime errors) what was the stack trace pointing to.

### Classify the failure

Classify the failure into one of:

| Failure mode | Definition | Verdict section |
|---|---|---|
| **Real regression** | The failing commit's code change is the responsible party. A revert or forward fix changes behavior. | **Forward-fix verdict** or **Revert verdict** |
| **Flaky test** | The test is non-deterministic; the failing commit is unrelated. Evidence: re-running the same workflow on the same commit produces a different result. | **Flaky-test verdict** |
| **Test infra issue** | The test or deploy infrastructure broke independently of code. Evidence: similar smoke tests on unrelated PRs around the same time also failed, or the failure is in setup/teardown not in app code. | **Test-infra verdict** |
| **Deferred work blocking smoke** | The failing commit is correct but the smoke test exercises a code path that depends on a deferred follow-up. Evidence: the failing test exercises behavior listed in a `## Deferred to follow-ups` item. | **Deferred-work verdict** |

Don't agonize over the classification — pick the most likely and proceed. If the next section's evidence contradicts the classification, come back here and re-classify.

### Forward-fix verdict

1. Branch from current `main`: `git checkout -b fix/<short-slug>`.
2. Reproduce the failure locally if possible (the smoke test command is in the workflow YAML; try to run a focused subset).
3. Make the targeted fix. Add a regression test that fails on the broken state and passes on the fixed state.
4. Lint, typecheck, push, open a draft PR with `Fixes #ISSUE_NUMBER` in the body.
5. **The opened PR goes through the normal lifecycle**: implementation worker AC gate → review worker → merge worker. This skill does NOT merge or skip CI — it only opens the PR.
6. Update the original ISSUE with a comment linking the fix PR, and increment the attempt counter (`ci-fix-attempts:N` → `ci-fix-attempts:N+1`).
7. Log a **WORKLOG entry** and **Exit**. The next orchestrator tick will pick up the PR.

If after one attempt the smoke test fails on the fix PR too, the next tick will treat it as a NEW smoke-test-failure issue (the smoke-test machinery files one per failed deploy). The orchestrator's decision table should route THAT new issue back to this skill, which will read the previous attempt counter on the original issue and increment.

### Revert verdict

Choose revert over forward-fix when:

- The failing commit's diff is small and self-contained (easy to revert without conflicts).
- The failing commit is **dormant in production** anyway (e.g. a hook that's only invoked when another follow-up wires it in — exactly PR #419's situation on 2026-06-06).
- Forward-fixing requires significant work that's better tracked as a fresh issue.

```bash
git checkout -b revert/<failing-commit-shortsha>
git revert <failing-commit-sha>
# Resolve any conflicts. Push, open draft PR with body explaining: "reverts <sha>;
# the work it represents is re-tracked at #<new-issue> for the forward-fix attempt".
```

File a fresh tracking issue for the work the revert undoes (so it's not lost). Cross-link from both: the revert PR body, the tracking issue, and a comment on the ORIGINAL issue (the one the revert PR closes by deferring).

The revert PR ALSO goes through the normal lifecycle (it has a `Fixes #ISSUE_NUMBER` for the ci-failure issue, and the new tracking issue uses `Refs #<umbrella>` if applicable).

### Flaky-test verdict

If you believe the test is flaky:

1. Re-run the failed workflow run with `gh run rerun RUN_ID --repo jpshackelford/voice-relay --failed`.
2. If it now passes, you have one data point. Take a second: re-run a third time.
3. If the test passes 2-of-3 reruns of the same commit, treat as flaky:
   - Add a `flaky-test` label to the original ISSUE.
   - Post a comment with the workflow run URLs of the three attempts and which passed/failed.
   - Increment `ci-fix-attempts:N+1`.
   - **Do NOT close the issue** — file (or find) a tracking issue under `area:test-infra` to deflake the test, and link it.
   - Log a **WORKLOG entry** and **Exit**.

Flaky-test verdicts use up an attempt counter slot the same as forward-fixes. If a test keeps showing up flaky, the threshold-3 escalation lands on `needs-human` and a human can decide whether to disable the test or invest in deflaking.

### Test-infra verdict

If the failure is in test infrastructure (CI runner, setup script, environment variable, secrets, etc.) and not in app code:

1. Post a comment on the ISSUE explaining what infra component failed and your evidence.
2. If the fix is within scope of this repo (e.g. a workflow YAML change), proceed as in **Forward-fix verdict** with a `chore(ci):` PR.
3. If the fix is out of scope (cloud infra, secrets, third-party service), add `needs-human` with a comment summarizing what you can't fix from inside this repo.
4. Either path: increment `ci-fix-attempts:N+1`, log a **WORKLOG entry**, **Exit**.

### Deferred-work verdict

If the failing test exercises a code path that depends on a `## Deferred to follow-ups` item that hasn't landed yet:

1. Identify the responsible follow-up issue (read the `## Deferred to follow-ups` section of the closing PR).
2. Two options:
   - **Disable the smoke test temporarily** (annotate with the follow-up issue number; remove the disable once that issue lands). Open a `chore(test):` PR with `Fixes #ISSUE_NUMBER`, body explaining the dependency and the cleanup-on-landing plan.
   - **Mark the original PR's responsible commit for revert** — proceed as in **Revert verdict**.
3. Increment counter, log, exit.

### WORKLOG entry

Every attempt logs an entry titled:

```
### YYYY-MM-DD HH:MM UTC - CI-failure worker (attempt N for issue #ISSUE_NUMBER)
```

Body must include:

- Failure mode classification (one of the four from **Classify the failure**).
- Action taken (opened PR #X / posted comment / labelled flaky / etc.).
- Attempt counter now at N (or escalated to `needs-human` at threshold).
- One-line root-cause hypothesis (even if uncertain — useful context for the next attempt).

⚠️ **WORKLOG.md changes ALWAYS go directly to `main`** — never in feature branches/PRs.

### Exit

Do not loop. Each tick is one attempt.

## See also

- `/orchestrate` — decision table includes a `ci-failure` row that dispatches this worker.
- `/implement-issue` — the forward-fix and revert PRs go through this normal procedure with the AC gate.
- `/prepare-merge` — the fix PR's merge worker still runs the hard AC gate.
