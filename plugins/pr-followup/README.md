# PR Follow-up Plugin

A personal "wingman" that follows you around the **team** repos where you have
open pull requests and helps you finish the work you started — without stepping
on your collaborators.

## How this differs from `pr-workflow`

| | `pr-workflow` | `pr-followup` (this plugin) |
|---|---|---|
| Designed for | Solo projects you own; agent does most of the work | Collaborative repos with other engineers |
| Drives | Issue → implement → test → review → **merge** | Your existing PRs → finish & hand back |
| Merges? | Yes, auto-merges when gates pass | **Never** — the team/author merges |
| Review stance | Runs its own review rounds | **Deferential to humans**, critical of agents |
| Worklog | `WORKLOG.md` inside the target repo | **Personal** repo, by week/day, US Eastern |
| Scope | One repo per automation | Many repos, centred on **you** |
| Re-validates relevance? | Not really (work is fresh) | Yes — old PRs may be stale or already fixed |

## What it does on each wake-up

For every PR **you** authored across the repos you track, it assesses:

1. **Still relevant?** Superseded, linked issue closed, badly diverged, or
   duplicated → it flags it for you (it never closes your PR).
2. **Does the problem still exist?** For older PRs / moved bases it re-confirms
   the bug still reproduces on current `main` (before/after).
3. **Does the fix still make sense?** Given how the code has changed since.
4. **Is it tested — and what needs a human?** It runs the software (QA), and
   reports the testing it *can't* do (prod creds, hardware, paid services,
   visual/UX judgment, security/data-migration paths).
5. **Review feedback to react to?** Humans first and deferentially; automated
   feedback (e.g. `all-hands-bot`) critically.

It then takes **one** action (rebase, re-confirm, fix CI, add tests, QA, address
review) or flags the PR, and writes a tight entry to your personal worklog.

## Key facts it relies on

- **`tkt` (tickster)** — token-efficient GitHub viewer.
  `tkt pr list --author me` is the core query; `tkt review` finds PRs awaiting
  your review. History strings encode each PR's lifecycle (`o`pened, changes
  `r`equested, `f`ix, `a`pproved, `m`erged; lowercase = you, UPPERCASE = others).
  Installed automatically from `git+https://github.com/jpshackelford/tickster`.
- **The OpenHands review system is automation-based, not CI-based.** The
  automated reviewer is **`all-hands-bot`** — an org **MEMBER**, *not* a `*[bot]`
  account, so it is **not** auto-detected as a bot. It posts a taste rating
  (🟢 Good / 🟡 Acceptable / 🔴 Needs work) with `[CRITICAL ISSUES]`,
  `[TESTING GAPS]`, `[IMPROVEMENT OPPORTUNITIES]`, and `[RISK ASSESSMENT]`
  sections as a real PR review. You **must** list it under `Agents` in
  `config.md` so the workflow treats it as an agent, not a human.
- **QA = run the software, not the tests.** Functional verification with explicit
  reporting of what needs a human (mirrors the `qa-changes` methodology).

## Setup

### 1. Create your personal worklog repo

```bash
echo "# worklog" >> README.md
git init && git add README.md && git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/<you>/worklog.git
git push -u origin main
```

The automation clones this repo as its working directory. Day files live in
`YYYY-week-WW/YYYY-MM-DD.md` (US Eastern; `WW` = `%U`, Sunday-start weeks, which
is why early-January falls in `week-00`).

### 2. Add `config.md` to the worklog repo

```markdown
# PR Follow-up Config

## Me
- GitHub user: <you>
- Timezone: America/New_York

## Repos
- OpenHands/OpenHands
- OpenHands/deploy
- OpenHands/runtime-api
- OpenHands/infra

## Agents
# Non-human accounts. all-hands-bot is a MEMBER (not *[bot]*) and MUST be listed.
- all-hands-bot
- openhands-ai[bot]
- openhands-release-bot[bot]
- github-actions[bot]
- dependabot[bot]
- renovate[bot]

## Automation
- ID: <this-automation-uuid>
- Quiet threshold: 2

## Behaviour
- Worker mode: spawn
- Merge: never
- QA: enabled
- Relevance recheck after days: 3
```

### 3. Create the automation

```bash
curl -X POST "https://app.all-hands.dev/api/automation/v1/preset/plugin" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "PR Follow-up (<you>)",
    "plugins": [
      {"source": "github:jpshackelford/.openhands", "repo_path": "plugins/pr-followup", "ref": "main"}
    ],
    "repos": [
      {"url": "https://github.com/<you>/worklog"}
    ],
    "prompt": "/follow-up",
    "trigger": {"type": "cron", "schedule": "0 13 * * 1-5", "timezone": "America/New_York"}
  }'
```

Put the returned automation `id` into `config.md` under `## Automation`.

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| follow-up | `/follow-up` | Scan my PRs across repos, assess, take one action, log |
| assess-pr | `/assess-pr` | Single-PR verdict: relevant? problem exists? fix fits? tested? reviews? |
| confirm-problem | `/confirm-problem` | Re-verify the problem still reproduces on current base |
| qa-pr | `/qa-pr` | Run the software; report what needs a human |
| address-review | `/address-review` | React to feedback — deferential to humans, critical of agents |
| worklog | `/worklog` | Append to the personal worklog (week/day, US Eastern) |
| spawn-conversation | `/spawn-conversation` | Start a worker conversation |
| disable-automation | `/disable-automation` | Auto-disable after consecutive quiet cycles |

## Operating principles

1. **You are in charge.** The plugin assists with PRs you started; it doesn't
   start new work or act on others' PRs.
2. **Never merge** in team repos — that's the team's call.
3. **Deferential to humans, critical of agents.** Implement human feedback or
   escalate to you; never silently dismiss or resolve a human's thread.
4. **Re-validate before investing** in old or diverged PRs.
5. **Surface what needs you** in the worklog's **Needs you** section.
6. **One action per wake-up**, fire-and-forget workers.

## Environment variables

- `OH_API_KEY` — spawn worker conversations
- `OPENHANDS_API_KEY` — manage this automation (enable/disable)
- `GITHUB_TOKEN` — `gh` and `tkt`
- `GIST_TOKEN` — optional, for `tkt` board state gists

## Interactive use

Every skill works on demand in a normal conversation too — e.g. open a chat in a
repo and run `/assess-pr` or `/address-review` for a specific PR. The cron
automation just runs `/follow-up` for you on a schedule.
