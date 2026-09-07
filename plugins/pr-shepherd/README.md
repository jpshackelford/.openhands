# PR Shepherd Plugin

Orchestrate PRs through the development lifecycle - from discovery through merge.

## Overview

PR Shepherd automates the manual work of shepherding pull requests:

1. **Discover** PRs from today's agent work (via `ohtv`)
2. **Track** them on a board (via `lxa board`)
3. **Analyze** their status using history codes
4. **Advance** them through review and merge

## Skills

| Skill | Trigger | Purpose |
|-------|---------|---------|
| **shepherd** | `/shepherd` | Situational awareness - discover, track, analyze, report |
| **shepherd-advance** | `/shepherd-advance` | Determine and execute next action for a PR |
| **shepherd-fix-ci** | `/shepherd-fix-ci` | Diagnose and fix CI failures |
| **shepherd-respond** | `/shepherd-respond` | Respond to review comments |
| **shepherd-self-review** | `/shepherd-self-review` | Self-review draft PRs |
| **shepherd-merge** | `/shepherd-merge` | Merge approved PRs |
| **shepherd-codes** | `/shepherd-codes` | Reference for history code interpretation |

## Design Philosophy

**Separation of awareness and action:**

- `/shepherd` is for **situational awareness only** - it reports what needs attention
- Action skills (`/shepherd-advance`, `/shepherd-fix-ci`, etc.) execute specific actions
- This allows for human review of recommendations before taking action

## Typical Workflow

### Scheduled Check-In

```
Scheduled Job
     │
     ▼
/shepherd                    ← Awareness phase
     │
     ├─ Discovers PRs (ohtv)
     ├─ Tracks on board (lxa)
     ├─ Analyzes status
     └─ Reports recommendations
            │
            ▼
     For each PR with action:
            │
     ┌──────┴──────┐
     ▼             ▼
/shepherd-*    (or manual)   ← Action phase
```

### Manual Usage

```bash
# Get situational awareness
/shepherd

# Take action on specific PR
/shepherd-advance owner/repo#123

# Or use specific action skill
/shepherd-fix-ci owner/repo#123
/shepherd-respond owner/repo#456
/shepherd-merge owner/repo#789
```

## Prerequisites

### Required Tools

- **ohtv** - OpenHands Trajectory Viewer (discovers PRs from conversations)
- **lxa** - Long Execution Agent CLI (board management, refinement)
- **gh** - GitHub CLI

### Installation

```bash
uv tool install git+https://github.com/jpshackelford/ohtv.git
uv tool install git+https://github.com/jpshackelford/lxa.git
# gh is usually pre-installed or: brew install gh
```

## History Codes Quick Reference

The `lxa pr list` command shows a history column with codes:

| Code | Meaning | lowercase=you, UPPERCASE=other |
|------|---------|--------------------------------|
| `o` | Opened | |
| `r`/`R` | Changes requested | |
| `f`/`F` | Fixes pushed | |
| `a`/`A` | Approved | |
| `c`/`C` | Comment | |
| `m` | Merged | |
| `k` | Killed (closed) | |

**Common patterns:**
- `oRf` → Fixes pushed, awaiting re-review
- `oRfA` → Approved, ready to merge
- `oRfRf` → Multiple review cycles

See `/shepherd-codes` for complete reference.

## Integration with Other Skills

- **babysit-pr**: For intensive single-PR monitoring with continuous CI/review polling
- **parallel-tasks**: For batch processing multiple PRs via background jobs

## Related Commands

```bash
# Discovery (ohtv)
ohtv sync --process
ohtv refs -D --prs-only --write-only -1

# Tracking (lxa board)
lxa board add-item <PR_URL>
lxa board status --attention

# Status (lxa pr)
lxa pr list --title
lxa review --all

# Action (lxa refine)
lxa refine <URL> --phase self-review
lxa refine <URL> --phase respond
lxa refine <URL> --auto-merge

# Background jobs
lxa run --background --job-name <name> --task "<description>"
lxa job list --running
```

## License

MIT
