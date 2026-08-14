---
name: assess-pr
description: Assess a single PR I authored - relevance, problem still exists, fix still sensible, tested, reviews to react to
triggers:
  - /assess-pr
---

# Assess PR

Decide what one of **your** pull requests needs next. This is the heart of the
follow-up workflow: before doing any work, figure out whether the PR is still
worth finishing, and if so, what the single most useful next action is.

## Usage

```
/assess-pr
```

Provide: **repository** (`owner/repo`) and **PR number**. You also need the
**Agents** list (non-human accounts) from `config.md` — pass it through, because
the default bot detection does **not** catch `all-hands-bot`.

The output is a short verdict block and one recommended action (the same action
vocabulary `/follow-up` routes on).

## The five questions

Answer these in order. Stop early only when an earlier answer makes later ones
moot (e.g. if the PR is clearly no longer relevant, you don't need to QA it).

### 1. Is this PR still relevant?

A PR you opened a while ago may have been overtaken by events. Check:

```bash
gh pr view {N} --repo {REPO} --json title,body,state,isDraft,createdAt,updatedAt,mergeable,mergeStateStatus,labels,closingIssuesReferences
tkt pr list "{REPO}#{N}"          # compact lifecycle + CI + 💬
```

Signals that relevance is in doubt:

- A **linked issue is now closed** (someone else fixed it):
  `closingIssuesReferences` points at a closed issue, or search:
  `gh issue view <issue> --repo {REPO} --json state,stateReason`.
- The PR has been **idle a long time** and the area has churned (recent merged
  PRs touch the same files):
  `gh pr diff {N} --repo {REPO} --name-only` then
  `gh search prs --repo {REPO} --merged "<path>" --json number,title,mergedAt`.
- The branch is **badly diverged** (`mergeStateStatus` = `DIRTY`/`BEHIND`) and
  the diff no longer applies cleanly to what main looks like now.
- A **duplicate/superseding PR** exists:
  `gh pr list --repo {REPO} --search "<keywords>" --state all`.

> Relevance is a **judgment call that belongs to you**. If relevance is in
> doubt, the action is `flag-relevance`: write a clear note in the worklog's
> **Needs you** section (what changed, why it might be dead, your recommendation)
> and do **not** close the PR yourself.

### 2. Does the problem still exist?

Only meaningful for bug-fix / behaviour-fix PRs. If the PR is older than the
config's `Relevance recheck after days` threshold, or the base branch has moved
substantially since it was opened, re-verify the problem still reproduces on the
**current base** before investing in the fix.

This is delegated to [`/confirm-problem`](confirm-problem.md), which does a
proper before/after on current `main`. If you only have a moment here, at least
note whether re-confirmation is warranted; the recommended action becomes
`confirm-problem`.

If the problem provably no longer reproduces on current main → this folds back
into question 1: action `flag-relevance` ("problem appears fixed upstream").

### 3. Does the fix still make sense in the current shape of the code?

The code around the PR may have changed even if the bug remains. Check that the
PR's approach is still coherent:

```bash
gh pr diff {N} --repo {REPO}                       # what the PR changes
git -C <clone> log --oneline -15 -- <touched paths> # recent churn in those files
```

Ask:

- Do the functions/APIs the PR touches still exist with the same shape?
- Has the surrounding code been refactored so the fix now belongs elsewhere?
- Does the PR still apply cleanly, or does `mergeStateStatus` show `DIRTY`?

Outcomes: clean but behind base → action `rebase`. Approach no longer fits the
code → action `flag-relevance` (needs a rethink — your call) with specifics.

### 4. Is it tested — and what needs a human?

```bash
gh pr diff {N} --repo {REPO} --name-only | grep -iE 'test|spec' || echo "no test files in diff"
gh pr checks {N} --repo {REPO}                     # CI signal
```

- CI red → action `fix-ci`.
- Behaviour change with **no tests** that CI could cover → action `add-tests`.
- Tests present and CI green, but functional behaviour unverified → action `qa`
  (run [`/qa-pr`](qa-pr.md), which also reports the testing that **needs a
  human** — prod credentials, hardware, paid services, visual/UX judgment,
  security-sensitive or data-migration paths). Those land in **Needs you**.

### 5. Are there review comments to react to?

Gather all reviews and threads, then **classify each author as human or agent**.

```bash
# Reviews (state + author + association)
gh api repos/{OWNER}/{REPO}/pulls/{N}/reviews \
  --jq '.[] | {login:.user.login, assoc:.author_association, state:.state, submitted:.submitted_at}'

# Issue-style comments on the PR
gh api repos/{OWNER}/{REPO}/issues/{N}/comments \
  --jq '.[] | {login:.user.login, body:(.body[0:160])}'

# Unresolved review threads (count shown by tkt as 💬)
gh api graphql -f query='
{ repository(owner:"{OWNER}", name:"{REPO}") {
    pullRequest(number:{N}) {
      reviewThreads(first:50){ nodes { isResolved comments(first:1){ nodes { author{login} body } } } }
    } } }'
```

**Human vs agent classification (critical):**

- An author is an **agent** if its login is in the config `Agents` list, or its
  login ends in `[bot]`. Remember: **`all-hands-bot` is an org member, not a
  `[bot]` account** — it is only caught because it is in the `Agents` list. The
  OpenHands automated reviewer posts a taste rating (🟢 Good / 🟡 Acceptable /
  🔴 Needs work) with `[CRITICAL ISSUES]`, `[TESTING GAPS]`,
  `[IMPROVEMENT OPPORTUNITIES]`, `[RISK ASSESSMENT]` sections — recognisable, but
  always classify by login, not by content.
- Everyone else is a **human** (including `[NONE]`, `[MEMBER]`,
  `[COLLABORATOR]`, `[CONTRIBUTOR]` associations).

> Do not rely on `tkt`'s history-string case to tell humans from agents.
> Uppercase just means "not me" — it lumps human teammates and bots together.
> Use the login-based classification above.

Routing:

- Any **unresolved human** review/thread (especially `CHANGES_REQUESTED`) →
  action `address-human-review` (highest non-instruction priority).
- Only **agent** feedback outstanding → action `address-agent-review`.
- No outstanding feedback, CI green, tested/QA'd → action `waiting` (note the
  human reviewer you're waiting on) or ready to hand back to you.

See [`/address-review`](address-review.md) for how to actually respond
deferentially.

## Verdict output

Emit a compact block (this is what `/follow-up` consumes and partly logs):

```markdown
### Assessment: {REPO}#{N} — {title}
- tkt: `oRfC` red ready 💬2
- Relevant: yes | doubtful (<one-line why>)
- Problem still exists: yes | no | recheck-needed | n/a
- Fix still fits: yes | no (<why>)
- Tested: ci-green+tests | ci-red | untested | qa-needed
- Reviews: human:1 unresolved (CHANGES_REQUESTED by @alice) · agent:1 (all-hands-bot 🟡)
- **Action: address-human-review**
- Needs you: <anything only you can decide/do, or "none">
```

## Notes

- Keep it cheap: prefer `tkt` and `gh api --jq` over cloning. Only clone when an
  action (confirm-problem, qa, code changes) actually requires it.
- When two actions tie, prefer the one higher in the `/follow-up` priority list
  (humans and validation before polish).
- Never let an assessment end in a state where a human is waiting and you logged
  nothing — that's the whole point of this workflow.
