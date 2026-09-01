---
name: qa-pr
description: Functionally verify a PR by running the software, and report explicitly what testing needs a human
triggers:
  - /qa-pr
---

# QA PR

Functionally verify one of your PRs by **running the software the way a user
would** — not by reading code and not by re-running the test suite. Then do the
thing this workflow cares about most: clearly separate what **you (an agent)
verified** from what **a human still needs to test**.

This skill follows the OpenHands QA methodology. If the `qa-changes` skill is
available in the environment, invoke it for the full method; this skill adds the
follow-up-specific framing (agent-testable vs human-required, and routing the
human items into the worklog **Needs you** section).

## Usage

```
/qa-pr
```

Provide: **repository** and **PR number**.

## Method (four phases)

1. **Understand the change.** Read the PR diff, title, and description. State the
   goal in one sentence and form a hypothesis: "this PR should {goal} by
   {approach}." Classify each change (feature / bug fix / refactor / config-docs)
   and find the user-facing entry point for each.
2. **Set up the environment.** Use the repo's own bootstrap (AGENTS.md / README /
   Makefile / package manager). Note CI status — do **not** re-run the test
   suite; that's CI's job. If setup fails, report and stop.
3. **Exercise the changed behaviour.** Actually use it: run the CLI with real
   inputs, make real HTTP requests, open the UI in a real browser, call the
   changed library function from a script. For bug fixes, do before/after on the
   base vs the PR branch. `--help`/`--version` is **not** verification.
4. **Report.** Post a scannable QA review to the PR (verdict + table up top,
   evidence in `<details>`), and surface the human-required items.

## The follow-up-specific part: what needs a human?

As you work Phase 3, sort every intended verification into one of two buckets.

**Agent-verifiable (do it now):**
- CLI behaviour with synthetic inputs
- Local API endpoints against a dev server
- UI rendering/interaction reachable from a local dev server in a headless browser
- Library/SDK calls via a short script
- Reproducing a bug and confirming the fix end-to-end locally

**Needs a human (report, don't fake):**
- Anything requiring **production credentials or secrets** you must not use for
  test traffic
- **Paid or rate-limited third-party services** (real billing, real external
  accounts)
- **Real hardware / devices / OS** the sandbox doesn't have (mobile, GPU,
  specific OS, peripherals)
- **Visual / UX / accessibility / copy taste** judgments a human should eyeball
- **Security-sensitive flows** (auth bypass, permissions) where a careless test
  could do harm
- **Data migrations / destructive operations** against production-like data
- Anything you attempted but couldn't verify after three materially different
  approaches (per the QA give-up rule) — switch approaches once, then report.

Be honest. An explicit "I could not verify X because Y; a human should do Z" is
far more valuable here than a false "everything works" — surfacing exactly this
is a core purpose of the follow-up workflow.

## Report format (posted to the PR)

```markdown
## {✅|⚠️|❌|🟡} QA Report: {PASS | PASS WITH ISSUES | FAIL | PARTIAL}

{One sentence: what was verified and the outcome.}

### Does this PR achieve its stated goal?
{Yes / Partially / No + 2-3 sentences of evidence from running the software.}

| Phase | Result |
|-------|--------|
| Environment setup | {emoji} {one line} |
| CI status | {emoji} {note from gh pr checks} |
| Functional verification | {emoji} {one line} |

<details><summary>Functional verification</summary>
{before/after narrative: exact command → actual output → interpretation}
</details>

### Needs a human
{Bulleted list of human-required verifications, each with WHY and the suggested
action. Write "None — fully agent-verifiable." if empty.}

### Issues found
{🔴 blocker / 🟠 issue / 🟡 minor, or "None."}

_Posted by an AI agent (OpenHands) on behalf of @{author}._
```

## Return to the caller

- Post the QA report comment to the PR (use `gh pr comment` or a PR review).
- Return the **Needs a human** bullets to `/follow-up` so they go into the
  worklog **Needs you** section. If that list is non-empty, the PR is **not**
  "done" from your side — it's "agent-verified, awaiting human QA".
- Never merge. QA passing does not authorise a merge in a team repo.

## Notes

- Run the software, not the tests. Don't re-run `pytest`/`npm test`/linters.
- Don't analyse code style here — that's review's job (`/address-review`).
- Keep the report scannable; bury logs in `<details>`.
