---
name: follow-up
description: Scan my open PRs across tracked repos, assess each, take one action, and log to my personal worklog
triggers:
  - /follow-up
  - /followup
---

# Follow Up

This is the entry point. It is designed to run as a scheduled automation that
wakes up periodically, looks at the pull requests **you** have open across the
team repos you track, and helps you push each one closer to done — without
stepping on your collaborators.

It pairs with these skills, which do the detailed work:

- [`/assess-pr`](assess-pr.md) — decide what a single PR needs next
- [`/confirm-problem`](confirm-problem.md) — re-verify the problem still exists
- [`/qa-pr`](qa-pr.md) — run the software and report what needs a human
- [`/address-review`](address-review.md) — react to review feedback (humans first)
- [`/worklog`](worklog.md) — append to the personal worklog repo
- [`/spawn-conversation`](spawn-conversation.md) — start a worker
- [`/disable-automation`](disable-automation.md) — quiet-period auto-disable

## Operating principles (read first)

These are what make this workflow different from `pr-workflow`. Hold them the
whole time.

1. **You are in charge; this is your wingman.** It assists with PRs you started.
   It does not invent new work and it does not act on other people's PRs (except
   to read review threads on *your* PRs).
2. **Never merge.** These are collaborative repos with branch protection and
   human reviewers. Getting a PR review-ready is the goal; merging is the team's
   call. The only exception is an explicit human instruction in the worklog.
3. **Be deferential to humans, critical of agents.** Human review feedback is
   near-authoritative — implement it or escalate to you, never silently dismiss
   it. Automated review feedback (e.g. `all-hands-bot`) is advisory — apply what
   genuinely improves the code, decline the rest with a reason.
4. **Re-validate before investing.** For any PR that is more than a few days old
   or whose base has moved, confirm the problem still exists and the fix still
   makes sense *before* spending effort polishing it. A stale PR may need closing,
   not finishing — and that decision is yours, so flag it.
5. **Surface what needs you.** Anything you cannot do as an agent (testing that
   needs prod creds / hardware / human judgment, a relevance call, an unresolved
   human review) goes in the worklog's **Needs you** section.
6. **One action per wake-up, fire and forget.** Take the single highest-priority
   action (inline or via a spawned worker), log it, and exit. Do not loop or wait
   for workers to finish — the next wake-up reconciles.

## What runs where

The automation clones your **personal worklog repo** as its working directory.
It reaches into the target repos with `gh` and `tkt` (no full clone needed for
assessment). When heavy work is required on a specific PR, it spawns a worker
conversation with that target repo checked out.

```
worklog repo (cwd) ──reads──> config.md                (what to track, who is a bot)
        │            ──reads──> tkt pr list --author me  (my PRs across repos)
        │            ──reads──> tkt review                (PRs waiting on me, optional)
        │            ──writes─> YYYY-week-WW/YYYY-MM-DD.md (the log)
        └──spawns──> worker conversations (target repo cloned per PR)
```

## Wake-up sequence

```
┌────────────────────────────────────────────────────────────────────┐
│  FOLLOW-UP WAKE-UP                                                    │
├────────────────────────────────────────────────────────────────────┤
│  0. SETUP: ensure tkt installed; read config.md from worklog repo    │
│  1. READ TODAY's worklog day-file for:                               │
│       - human ## INSTRUCTION: entries  → follow them, then exit       │
│       - Active Workers table           → conv IDs to poll             │
│  2. POLL active workers (API). Mark finished/errored.               │
│  3. GATHER my open PRs:  tkt pr list --author me <repos>             │
│  4. For each PR, run /assess-pr to get a verdict + recommended action│
│  5. PICK one PR+action by priority (see Priority below)              │
│  6. ACT: inline for light work, or spawn a worker for heavy work     │
│  7. WRITE a worklog entry (action + per-PR state + Needs you)        │
│  8. EXIT                                                              │
└────────────────────────────────────────────────────────────────────┘
```

## Step 0: Setup and configuration

```bash
# tkt is the token-efficient GitHub viewer this workflow relies on.
which tkt || uv tool install git+https://github.com/jpshackelford/tickster

# Read personal configuration from the worklog repo root.
if [ -f "config.md" ]; then
  cat config.md
else
  echo "ERROR: config.md not found in the worklog repo."
  echo "This workflow needs config.md to know which repos to follow and who is a bot."
  echo "See the plugin README for the config.md format."
  exit 1
fi
```

### config.md format (lives in the worklog repo)

```markdown
# PR Follow-up Config

## Me
- GitHub user: jpshackelford
- Timezone: America/New_York

## Repos
# Repos to follow. Either list them here, or name a tkt board synced via gist.
- OpenHands/OpenHands
- OpenHands/deploy
- OpenHands/runtime-api
- OpenHands/infra

## Agents
# Accounts to treat as NON-human (automated). Critically:
# all-hands-bot is an org MEMBER, not a *[bot]* account, so it is NOT
# auto-detected as a bot. It MUST be listed here.
- all-hands-bot
- openhands-ai[bot]
- openhands-release-bot[bot]
- github-actions[bot]
- dependabot[bot]
- renovate[bot]

## Automation
- ID: <this-automation-uuid>          # used by /disable-automation
- Quiet threshold: 2

## Behaviour
- Worker mode: spawn        # spawn | inline
- Merge: never              # never (do not change for team repos)
- QA: enabled              # run /qa-pr when a PR is otherwise ready
- Relevance recheck after days: 3
```

Extract the values you need: `REPOS` (build `--repo X --repo Y ...`),
`AGENTS` (the non-human list used by `/assess-pr` and `/address-review`),
`AUTOMATION_ID`, `WORKER_MODE`, `RELEVANCE_DAYS`.

## Step 1: Human instructions and active workers

Open today's worklog day-file (and yesterday's, to catch overnight context). See
[`/worklog`](worklog.md) for the path convention.

```bash
WEEK_DIR=$(TZ=America/New_York date +%Y-week-%U)
DAY_FILE="$WEEK_DIR/$(TZ=America/New_York date +%Y-%m-%d).md"
[ -f "$DAY_FILE" ] && cat "$DAY_FILE"
```

- **Human instructions:** look for `## INSTRUCTION:` lines that are not yet
  `[ACKNOWLEDGED]`. If any exist, acknowledge, do exactly what they ask
  (including "pause", "skip PR #X", "close PR #Y", or "merge PR #Z"), log it,
  and exit this cycle.
- **Active Workers:** parse the table for `conv id | repo#pr | type`. These are
  workers spawned on previous wake-ups.

## Step 2: Poll active workers

For each active conv ID, check whether it is still running before you consider
spawning anything new for that PR.

```bash
conv_id="abc1234"
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?limit=50" \
  -H "Authorization: Bearer ${OH_API_KEY}" \
| jq -r ".items[] | select(.id | startswith(\"$conv_id\")) | {id: .id[0:7], status: .execution_status, title: .title}"
```

- `running` → that PR has a worker; do not spawn another for it this cycle.
- `finished` → reconcile from GitHub state (the worker should have pushed
  commits / replied to threads). Record the outcome in the worklog.
- `error` / `stuck` → note it in **Needs you**.

**Concurrency:** keep it polite. Default to **one active worker at a time**
across all your PRs (these are shared repos and shared CI). Raise this only if
your config says so.

## Step 3: Gather my open PRs

```bash
# Build the repo filter from config (REPO_ARGS="--repo A --repo B ...")
tkt pr list --author me $REPO_ARGS --title
# History codes: o opened, h review-requested, r changes-requested, a approved,
#                c comment, f fix-pushed, m merged, k killed.
# Case: lowercase = me, UPPERCASE = someone else. 💬 = unresolved threads.
```

Optionally also scan PRs waiting on *your* review (a different kind of "work you
started" — you owe a teammate a review):

```bash
tkt review $REPO_ARGS --title        # actionable review queue (review / re-review)
```

Reviews you owe are reported in the worklog under **Needs you** by default (so
you decide when to do them); only act on them if your config opts in.

## Step 4: Assess each of my PRs

For each PR from Step 3, run [`/assess-pr`](assess-pr.md). It returns a verdict
and a single recommended next action, drawn from:

| Action | When |
|--------|------|
| `flag-relevance` | Problem may be gone / superseded / fix no longer fits → **ask you**, do not close |
| `address-human-review` | An unresolved human review/thread needs a response |
| `confirm-problem` | Old PR or moved base; re-verify the problem still reproduces |
| `rebase` | Base diverged / merge conflict / out-of-date branch |
| `fix-ci` | CI is red |
| `add-tests` | Behaviour change lacks tests CI could cover |
| `qa` | Otherwise ready → run functional QA and surface human-needed testing |
| `address-agent-review` | Only automated review feedback remains |
| `waiting` | Ready and waiting on a human reviewer / external input — nothing to do |

## Step 5: Pick one action (priority)

Choose the single highest-priority actionable PR. Priority is ordered to respect
humans and avoid wasted effort:

```
1. Human INSTRUCTION (handled in Step 1)
2. address-human-review     (a person is waiting on you)
3. flag-relevance           (don't polish a PR that may be dead — ask first)
4. confirm-problem          (validate before investing)
5. rebase / fix-ci          (unblock the mechanics)
6. add-tests / qa           (raise quality, surface human-needed testing)
7. address-agent-review     (advisory polish)
8. waiting                  (log who we're waiting on; not an action)
```

If every PR is `waiting` (or there are no PRs), this is a **quiet** cycle.

## Step 6: Act

- **Light work inline** (rebase a clean branch, reply to a thread, kick CI,
  flag relevance): do it in this conversation against the target repo.
- **Heavy work via a worker** (`confirm-problem`, `qa`, `address-review` with
  code changes, `add-tests`): spawn a worker with [`/spawn-conversation`],
  passing the target repo, PR number, and the matching `/skill` prompt. Load
  this plugin in the worker so it has the skills:

  ```
  Plugins: github:jpshackelford/.openhands @ plugins/pr-followup @ main
  ```

Respect `Worker mode` from config (`spawn` vs `inline`).

## Step 7: Write the worklog

Append one entry to today's day-file with [`/worklog`](worklog.md). Keep it
tight (≈10–20 lines). It must contain:

- A timestamped header (US Eastern).
- One bold action line (e.g. `🛠 **Acted: addressed review on OpenHands/OpenHands#15001**`).
- **My Open PRs** — one compact line per PR using `tkt` shorthand + verdict.
- **Active Workers** — table of running conv IDs (or `_None._`).
- **Needs you** — human-required items (relevance calls, human reviews awaiting
  your decision, tests only you can run, stuck workers). Omit if empty.

## Step 8: Exit

Commit and push the worklog (see [`/worklog`](worklog.md)), then exit. Do not
wait for workers. The next wake-up reconciles.

### Quiet periods

If this cycle was quiet and the previous worklog entry was also quiet, invoke
[`/disable-automation`](disable-automation.md) instead of logging another quiet
entry. `waiting`, active workers, and `Needs you` items are **not** quiet.

## Cron

```
0 13 * * 1-5   # 9am ET on weekdays (cron in America/New_York)
```

Tune to how often your teammates review.
