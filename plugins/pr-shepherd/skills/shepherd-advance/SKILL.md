---
name: shepherd-advance
description: Advance a PR to the next stage in its lifecycle. Determines the appropriate action based on current status and executes it. Use after /shepherd identifies PRs needing attention, or to advance a specific PR.
triggers:
- /shepherd-advance
---

# Shepherd Advance - Take Next Action

Determine and execute the next action for a PR based on its current status.

## When to Use

- After `/shepherd` identifies PRs needing action
- "Advance this PR"
- "Move PR #123 forward"
- "Process all PRs that need attention"

## Usage

```bash
# Advance a specific PR
/shepherd-advance owner/repo#123
/shepherd-advance https://github.com/owner/repo/pull/123

# Advance all PRs with pending actions (batch mode)
/shepherd-advance --all
```

## How It Works

1. **Get current status** - Query PR via `lxa pr list` or `gh pr view`
2. **Apply decision matrix** - Determine appropriate action
3. **Execute action** - Run directly or delegate to specific skill
4. **Report result** - What was done and outcome

## Decision Matrix

Evaluate in this priority order:

### Priority 1: CI Issues (Blocking)

| Condition | Action | Method |
|-----------|--------|--------|
| CI = RED | Fix CI failure | `/shepherd-fix-ci` |
| CI = CONFLICT | Resolve conflicts | Checkout, merge main, push |
| CI = PENDING > 30min | Investigate stuck | Manual check |

### Priority 2: Review Issues

| Condition | Action | Method |
|-----------|--------|--------|
| Threads > 0 | Respond to reviews | `/shepherd-respond` |

### Priority 3: History-Based

| History Ends | Condition | Action | Method |
|--------------|-----------|--------|--------|
| `A` | CI green, ready | Merge | `/shepherd-merge` |
| `R` | You're author | Address feedback | `/shepherd-respond` |
| `f` | — | Wait for reviewer | Report status |

### Priority 4: State-Based

| State | Condition | Action | Method |
|-------|-----------|--------|--------|
| draft | CI green | Self-review | `/shepherd-self-review` |
| ready | No activity > 48h | Escalate | Ping reviewers |

### Terminal States

| History | Action |
|---------|--------|
| `m` (merged) | Done - remove from tracking |
| `k` (killed) | Closed - investigate if unexpected |

## Execution Methods

### Interactive (Foreground)

For immediate execution with feedback:

```bash
/shepherd-fix-ci owner/repo#123
/shepherd-respond owner/repo#123
/shepherd-self-review owner/repo#123
/shepherd-merge owner/repo#456
```

### Background (Long-running or Batch)

For parallel processing or long operations:

```bash
# Background refinement
lxa refine <URL> --background --phase respond
lxa refine <URL> --background --phase self-review

# Background fix job
lxa run --background --job-name "fix-ci-123" \
  --task "Fix CI failure on owner/repo#123. Error: <details>"

# Monitor jobs
lxa job list --running
lxa job status <job-id>
```

### Delegate to babysit-pr

For intensive single-PR monitoring (complex CI issues, multiple review cycles):

```bash
/babysit-pr owner/repo#123
```

## Batch Processing (--all)

When `--all` is specified:

1. Run `/shepherd` to get current status of all PRs
2. Filter to PRs with actionable recommendations
3. For each PR:
   - Determine action
   - Launch background job
   - Record job ID
4. Report summary of launched jobs
5. Monitor with `lxa job list`

```bash
# Example batch output
Processing 3 PRs...

| PR | Action | Job ID |
|----|--------|--------|
| owner/repo#123 | respond | refine-pr123-respond |
| owner/repo#456 | merge | (immediate) |
| owner/repo#789 | fix-ci | fix-ci-789 |

Launched 2 background jobs. 1 PR merged immediately.
Monitor with: lxa job list --running
```

## Output Format

For single PR:

```
PR owner/repo#123:
  Current: History=oRf, CI=green, State=draft, Threads=2
  Action: Responding to review comments
  Method: lxa refine --background --phase respond
  Job ID: refine-pr123-respond
```

For batch:

```
Shepherd Advance Summary
========================
Processed: 3 PRs
Actions taken:
  - owner/repo#123: Responding to reviews (job: refine-pr123)
  - owner/repo#456: Merged
  - owner/repo#789: Fixing CI (job: fix-ci-789)

Background jobs running: 2
Monitor: lxa job list --running
```

## Examples

### Single PR - Review Response Needed

```bash
$ /shepherd-advance owner/repo#123

Analyzing owner/repo#123...
  History: oRf
  CI: green
  State: draft  
  Threads: 2

Decision: Unresolved threads (2) → Respond to reviews

Executing: lxa refine https://github.com/owner/repo/pull/123 --background --phase respond

Job launched: refine-pr123-respond
Monitor with: lxa job logs refine-pr123-respond --follow
```

### Single PR - Ready to Merge

```bash
$ /shepherd-advance owner/repo#456

Analyzing owner/repo#456...
  History: oRfA
  CI: green
  State: ready
  Threads: 0

Decision: Approved + CI green + no threads → Merge

Executing: gh pr merge 456 --squash --delete-branch

✓ Merged owner/repo#456
```

### Batch Processing

```bash
$ /shepherd-advance --all

Running /shepherd for status...

Found 3 PRs needing action:
  owner/repo#123: threads=2 → respond
  owner/repo#456: approved → merge
  owner/repo#789: CI red → fix

Processing...
  ✓ owner/repo#123: Job refine-pr123-respond launched
  ✓ owner/repo#456: Merged
  ✓ owner/repo#789: Job fix-ci-789 launched

Summary: 1 merged, 2 jobs launched
```

## Error Handling

| Error | Response |
|-------|----------|
| PR not found | Report error, skip |
| No action determined | Report "waiting" status |
| CI still pending | Report "wait for CI" |
| Permission denied | Report, suggest manual action |
| Job launch failed | Report error, suggest retry |

## Related Skills

- `/shepherd` - Get situational awareness first
- `/shepherd-fix-ci` - Specific CI fixing guidance
- `/shepherd-respond` - Specific review response guidance
- `/shepherd-self-review` - Specific self-review guidance
- `/shepherd-merge` - Specific merge guidance
