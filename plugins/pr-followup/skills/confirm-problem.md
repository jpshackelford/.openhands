---
name: confirm-problem
description: Re-verify that the problem a PR fixes still reproduces on the current base branch (before/after)
triggers:
  - /confirm-problem
---

# Confirm Problem

Before you spend effort finishing an older PR, prove the problem it fixes still
exists on the **current** base branch. Code moves; bugs get fixed sideways by
other PRs; requirements change. This skill answers one question with evidence:

> If I dropped this PR today, would the problem still be real?

It uses the same "run the software, don't just read it" bar as
[`/qa-pr`](qa-pr.md), but its job is the **baseline**, not the fix.

## Usage

```
/confirm-problem
```

Provide: **repository**, **PR number**, and (if known) the **linked issue** that
describes the original problem.

## When to run

`/assess-pr` routes here when a PR is older than the config's relevance-recheck
threshold, or its base has moved a lot, or its linked issue's status is unclear.

## Procedure

### 1. Pin down the claimed problem

Read the PR description and any linked issue to extract a **concrete, runnable
reproduction**: the exact command / request / UI steps and the expected-vs-actual
behaviour.

```bash
gh pr view {N} --repo {REPO} --json title,body,closingIssuesReferences
gh issue view <issue> --repo {REPO} --json title,body,state,stateReason
```

If the linked issue is already **closed as completed**, that's a strong signal
the problem may be gone — note it and still try to reproduce.

### 2. Reproduce on current base (NOT the PR branch)

Check out the up-to-date base branch — the world as it is **without** your fix.

```bash
git clone https://github.com/{REPO} repo && cd repo
git checkout {base:-main} && git pull
# bootstrap per the repo's own instructions (AGENTS.md / README / Makefile)
```

Run the reproduction. Capture the exact command and its real output.

- **Problem reproduces** → the PR is still needed for its stated reason. Record
  the evidence and return `problem: still-exists`.
- **Problem does NOT reproduce** → before concluding it's fixed, rule out
  environment/setup differences (three materially different attempts, per the QA
  give-up rule). If it genuinely no longer reproduces, find out **why**:

  ```bash
  git log --oneline -20 -- <files the PR/issue concern>
  git log -S '<symbol or string from the repro>' --oneline -10
  ```

  Identify the commit/PR that addressed it upstream if you can.

### 3. (Optional) Confirm the fix still changes behaviour

If the problem still exists, optionally check out the PR branch and re-run the
same reproduction to confirm the fix still resolves it on top of current base
(it may need a rebase first — that's a separate `rebase` action, don't do it
silently here).

## Output

Post a concise comment to the PR **only when there is something the team should
know** (problem gone, or problem confirmed after a long gap), and always return
a verdict to the caller:

```markdown
## 🔁 Problem re-check on `{base}` @ {short-sha}

**Verdict:** still reproduces | no longer reproduces | inconclusive

<details><summary>Baseline (current base, no fix)</summary>

Ran `{exact command}`:
```
{actual output}
```
Interpretation: {what it means}.
</details>

{If gone:} Appears resolved by {commit/PR link or "unknown change"}.
This PR may no longer be needed — flagging for the author to decide.

_Posted by an AI agent (OpenHands) on behalf of @{author}._
```

Return one of:

- `problem: still-exists` → caller continues finishing the PR (rebase/CI/tests/QA/review).
- `problem: gone` → caller's action becomes `flag-relevance`; put a clear
  recommendation in the worklog **Needs you**. **Do not close the PR** — that's
  the author's decision.
- `problem: inconclusive` → `flag-relevance` with what you tried and what a human
  would need to verify.

## Notes

- Reproduce on the **base**, not the PR branch — you're validating the premise,
  not the patch.
- Honest "inconclusive, here's what I tried" beats a confident wrong call.
- This is read-only on the code: never push fixes from this skill.
