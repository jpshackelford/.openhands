---
name: address-review
description: React to review feedback on my PR - deferential to humans, critical of agents, multi-round
triggers:
  - /address-review
---

# Address Review

React to review feedback on one of **your** PRs. The defining rule of this skill:
**be deferential to humans, and critically evaluate agents.** You are responding
on the author's behalf in a shared repo, so the tone and the bar for declining
feedback differ sharply depending on who left it.

## Usage

```
/address-review
```

Provide: **repository**, **PR number**, and the **Agents** list from `config.md`
(needed to classify reviewers — `all-hands-bot` is not auto-detected).

## Step 1: Gather and classify all feedback

```bash
# Reviews (state, author, association)
gh api repos/{OWNER}/{REPO}/pulls/{N}/reviews \
  --jq '.[] | {id:.id, login:.user.login, assoc:.author_association, state:.state}'

# Review threads with resolution + IDs (for replying / resolving)
gh api graphql -f query='
{ repository(owner:"{OWNER}", name:"{REPO}") {
    pullRequest(number:{N}) {
      reviewThreads(first:50){ nodes {
        id isResolved isOutdated
        comments(first:20){ nodes { author{login} body path line } }
      } } } } }'

# Plain PR comments
gh api repos/{OWNER}/{REPO}/issues/{N}/comments \
  --jq '.[] | {login:.user.login, body:(.body[0:200])}'
```

**Classify each author:**

| Class | Test |
|-------|------|
| **agent** | login is in config `Agents` list, OR login ends in `[bot]` |
| **human** | everything else (incl. `[NONE]`/`[MEMBER]`/`[COLLABORATOR]`) |

> `all-hands-bot` is an org **member**, not a `[bot]` login. It is the OpenHands
> automated reviewer (taste rating + `[CRITICAL ISSUES]` / `[TESTING GAPS]` /
> `[IMPROVEMENT OPPORTUNITIES]` / `[RISK ASSESSMENT]`). It is an **agent** — it is
> only caught by the `Agents` list, so always classify by login. Do not let
> `tkt` history-string casing decide this; uppercase means "not me", not "human".

Handle **human feedback first and completely** before touching agent feedback.

## Step 2: Respond to HUMAN feedback (deferential)

Default posture: **the reviewer is right.** Implement the change. Humans are
scarce; their time spent reviewing your PR is a gift.

For each human comment/thread:

1. **Implement it** unless you have a strong, specific reason not to. "Adds a
   little verbosity" is not a strong reason when a human asked.
2. **If you genuinely disagree**, do **not** override and do **not** resolve the
   thread. Instead:
   - Reply politely with your reasoning and a proposed alternative, framed as a
     question ("Would X work instead? Happy to go either way.").
   - Leave the thread **unresolved** and add it to the worklog **Needs you** so
     the author (you) can make the final call with the human.
   - A human's `CHANGES_REQUESTED` is never dismissed by an agent. You may
     address it, but you do not re-request review or mark anything resolved on
     their behalf without their content being satisfied.
3. **Never** use the review-thread resolve mutation on a **human** thread unless
   you implemented exactly what they asked; even then, reply first explaining
   what you did and reference the commit.

## Step 3: Respond to AGENT feedback (critical)

Automated feedback (e.g. `all-hands-bot`) is advisory. Apply judgment:

- Implement suggestions that fix real bugs, close real testing gaps, or clearly
  improve clarity/safety.
- **Decline** suggestions that add verbosity without benefit, over-engineer for
  hypothetical edge cases, or contradict the repo's pragmatic conventions —
  reply with a one-line reason, then resolve the agent thread.
- Treat an agent's taste rating as a signal, not a gate. Agent `CHANGES_REQUESTED`
  can be resolved by an agent once addressed or reasonably declined.

## Step 4: Make changes safely (collaborative repo etiquette)

```bash
git clone https://github.com/{REPO} repo && cd repo
gh pr checkout {N}
```

- Work on the existing PR branch; **do not** rename it or force-push over
  collaborators' commits. Prefer additive commits; use `--force-with-lease` only
  if you rebased and you are certain no one else is on the branch.
- Group related changes into small, clearly-messaged commits that reference the
  feedback.
- Keep scope tight — address the feedback, don't sneak in unrelated changes.
- Push and let CI run: `git push`. Verify CI: `gh pr checks {N} --repo {REPO}`.
- Do **not** flip draft state or request reviewers on a human's behalf unless
  your config / a human instruction says to. Getting the PR back to "ready for
  the human" is the goal; the human drives merge.

## Step 5: Reply to and resolve threads

Reply explaining what you did (or why you didn't), referencing the commit SHA.
Use the GraphQL mutations:

```bash
# Reply in a thread
gh api graphql -f query='
mutation { addPullRequestReviewThreadReply(input:{
  pullRequestReviewThreadId:"<THREAD_ID>", body:"Done in <SHA>: <what changed>."
}){ comment { id } } }'

# Resolve a thread (see rules above: agent threads freely; human threads only
# when their ask is fully satisfied, and only after a reply)
gh api graphql -f query='
mutation { resolveReviewThread(input:{threadId:"<THREAD_ID>"}){ thread { isResolved } } }'
```

Every comment you post to GitHub must include an AI-disclosure line, e.g.:

```
_Replied by an AI agent (OpenHands) on behalf of @{author}._
```

## Step 6: Report back

Return to `/follow-up`:

- What human feedback was implemented (commits), what was queried back to a human
  (→ **Needs you**), and what agent feedback was applied vs declined.
- Whether any human thread remains unresolved awaiting the author's decision.
- CI status after the push.

## Multi-round behaviour

Each wake-up addresses **one round** of feedback, then exits — exactly like the
human/agent back-and-forth in `pr-workflow`. New commits may trigger another
agent review or a human re-review; the next `/follow-up` tick re-assesses and, if
there is fresh feedback, runs `/address-review` again. Do not loop within a
single conversation.

## Notes

- When in doubt on human feedback: implement it, or ask — never silently dismiss.
- Resolving a human's thread without satisfying it is the cardinal sin here.
- One round per wake-up; let CI and reviewers respond between rounds.
