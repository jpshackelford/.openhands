---
name: worklog
description: Append an entry to the personal worklog repo (YYYY-week-WW/YYYY-MM-DD.md, US Eastern)
triggers:
  - /worklog
---

# Worklog

Record what the follow-up workflow did to a **personal** worklog repository,
organised by week and day in **US Eastern time**. The worklog is deliberately
*not* stored in the target repos — it spans all of them and it is yours.

## The worklog repo

A standalone repo, e.g. `github.com/<you>/worklog`, created once:

```bash
echo "# worklog" >> README.md
git init && git add README.md && git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/<you>/worklog.git
git push -u origin main
```

The follow-up automation clones this repo as its working directory (via the
automation's `repos` field), so in a normal run it is already your CWD. It also
holds `config.md` (see the [`/follow-up`](follow-up.md) skill).

## Layout

```
worklog/
  README.md
  config.md                      # follow-up configuration
  2026-week-00/
    2026-01-01.md
    2026-01-02.md
  2026-week-01/
    2026-01-05.md
  ...
```

- **Week folder:** `YYYY-week-WW`, where `WW` is the zero-padded US week number
  (`%U`, weeks starting Sunday — this is why early-January days land in
  `week-00`). Both the year and week are taken in `America/New_York`.
- **Day file:** `YYYY-MM-DD.md`, also in `America/New_York`.

Because each day is its own file, the worklog self-archives — there is no
truncation step to run. Old days simply stay as old files.

### Compute the path

```bash
TZ=America/New_York
WEEK_DIR="$(TZ=$TZ date +%Y-week-%U)"
DAY="$(TZ=$TZ date +%Y-%m-%d)"
TIME="$(TZ=$TZ date '+%H:%M %Z')"     # e.g. 09:14 EST / 10:14 EDT
DAY_FILE="$WEEK_DIR/$DAY.md"
mkdir -p "$WEEK_DIR"
```

> Use the same `%U` everywhere so reads (in `/follow-up`) and writes (here) agree.
> If you ever prefer Monday-start weeks, switch every `%U` to `%W` consistently.

## Day-file structure

A day file starts with a date header, then one entry per wake-up appended in
chronological order:

```markdown
# 2026-01-02 (US Eastern)

### 09:14 EST — Follow-up

🛠 **Acted: addressed review on OpenHands/OpenHands#15001**

- Implemented @ak684's two thread comments; replied + referenced commit `a1b2c3d`.
- Declined one all-hands-bot nit (over-engineered), resolved that agent thread.

**My Open PRs:**

| PR | tkt | Verdict / next |
|----|-----|----------------|
| [OpenHands/OpenHands#15001](https://github.com/OpenHands/OpenHands/pull/15001) | `oRfC` red ready 💬1 | addressing review (this) |
| [OpenHands/deploy#421](https://github.com/OpenHands/deploy/pull/421) | `oA` green ready | waiting on @maintainer review |
| [OpenHands/infra#88](https://github.com/OpenHands/infra/pull/88) | `of` green draft | relevance doubtful |

**Active Workers:**

| Conv ID | Repo#PR | Type |
|---------|---------|------|
| `7f3a9c1` | OpenHands/OpenHands#15001 | address-review |

**Needs you:**

- ⚠️ **infra#88** may be obsolete — issue #80 it fixed was closed by #85 last week. Close it, or tell me to rebase. (relevance call)
- 🧪 **deploy#421** QA: the SSO redirect path needs a real Okta tenant I can't reach — please click through staging once.

---
```

### Entry contract

Keep each entry ≈10–20 lines. Always include, in order:

1. `### HH:MM TZ — Follow-up` header (Eastern).
2. One bold action line with a status emoji:
   - 🛠 **Acted: …** (took a concrete action)
   - 🚀 **Spawned: …** (started a worker; add it to Active Workers)
   - 🔁 **Re-checked: …** (confirm-problem)
   - 🧪 **QA'd: …**
   - 🚩 **Flagged: …** (relevance / needs-you only)
   - 📋 **Following instruction: …**
   - ✅ **All quiet** (only when nothing is actionable and nothing needs you)
   - 🔒 **Auto-disabled** (see [`/disable-automation`](disable-automation.md))
3. 1–3 context bullets.
4. **My Open PRs** table (compact `tkt` line + verdict/next per PR).
5. **Active Workers** table, or `_None._`.
6. **Needs you** list — the most important section for you. Human-required items:
   relevance calls, human reviews awaiting your decision, tests only you can run,
   stuck/errored workers. Omit the heading only when truly empty.

Do **not** dump decision-tree traces, full command output, or re-explanations of
config into the worklog. That belongs in the conversation log, not on disk.

## Commit and push

```bash
git add "$DAY_FILE"
git commit -m "worklog: $DAY $TIME"
git pull --rebase origin main 2>/dev/null || true
git push origin main
```

If a push races with a concurrent run, `git pull --rebase` then push again.

## Reading the worklog (used by /follow-up)

```bash
# Today (and yesterday for overnight context)
TZ=America/New_York
cat "$(TZ=$TZ date +%Y-week-%U)/$(TZ=$TZ date +%Y-%m-%d).md" 2>/dev/null
cat "$(TZ=$TZ date -d 'yesterday' +%Y-week-%U)/$(TZ=$TZ date -d 'yesterday' +%Y-%m-%d).md" 2>/dev/null
```

From these, extract: unacknowledged `## INSTRUCTION:` entries, the latest
**Active Workers** table, and whether the last entry was quiet.

## Human instructions

You can drop instructions for the workflow directly into a day file (or any file
the workflow reads) as:

```markdown
## INSTRUCTION: Close infra#88, the issue was fixed by #85.
## INSTRUCTION: Don't touch deploy#421 until Thursday.
```

`/follow-up` reads these first, marks them `[ACKNOWLEDGED]`, acts, and exits.

## Notes

- All timestamps and folder/day names are **US Eastern** — compute with
  `TZ=America/New_York`, never the sandbox's UTC clock.
- The worklog is the single source of truth across repos; keep it skimmable.
