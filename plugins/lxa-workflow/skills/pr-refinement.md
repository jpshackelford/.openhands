---
name: pr-refinement
description: Two-phase PR refinement using lxa - self-review and review response
triggers:
  - /pr-refinement
  - /refine
---

# PR Refinement

Two-phase automated PR refinement using LXA's `lxa refine` command.

## Usage

```
/refine <PR_URL>
/refine <PR_URL> --phase self-review
/refine <PR_URL> --phase respond
/refine <PR_URL> --auto-merge
```

## The Two Phases

### Phase 1: Self-Review

**When:** Draft PR with passing CI, before requesting human review.

The agent reviews its own code against quality principles:
- Data structures first (poor choices create complexity)
- Simplicity and "good taste" (no deep nesting, no special cases)
- Pragmatism (solve real problems, not theoretical ones)
- Testing (new behavior needs tests)

```bash
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase self-review
```

**What happens:**
1. Checks out the PR branch
2. Waits for CI to pass
3. Reviews its own code
4. Fixes any issues found
5. Commits improvements
6. Marks PR ready for human review

### Phase 2: Review Response

**When:** PR has unresolved review threads from human reviewers.

```bash
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase respond
```

**What happens:**
1. Reads each unresolved review thread
2. Evaluates if feedback is valid
3. Makes fixes (preferring root-cause solutions)
4. Commits with `Address review: [description]`
5. Pushes changes
6. Waits for CI
7. Replies to each thread with commit SHA
8. Marks threads as resolved

## Auto-Detection

If you don't specify a phase, LXA auto-detects:

```bash
lxa refine https://github.com/jpshackelford/lxa/pull/42
```

**Detection logic:**
- Draft PR → Self-Review phase
- Non-draft with unresolved threads → Respond phase
- Non-draft with no threads → Already complete

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--phase` | `auto` | Which phase: `auto`, `self-review`, `respond` |
| `--auto-merge` | false | Squash & merge when refinement passes |
| `--allow-merge` | `acceptable` | Quality bar: `good_taste` or `acceptable` |
| `--min-iterations` | 1 | Minimum iterations before accepting "acceptable" |
| `--max-iterations` | 5 | Maximum refinement iterations |

## Quality Verdicts

Self-review produces one of these verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| 🟢 **Good taste** | Code is clean, ready for review | Continue to human review |
| 🟡 **Acceptable** | Minor issues, but good enough | Continue (with `--allow-merge acceptable`) |
| 🔴 **Needs work** | Significant issues found | Fix and re-review |

## Examples

### Basic Self-Review

```bash
# Run self-review on a draft PR
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase self-review
```

### Respond to Review Comments

```bash
# Address reviewer feedback
lxa refine https://github.com/jpshackelford/lxa/pull/42 --phase respond
```

### Full Auto-Refinement with Merge

```bash
# Auto-detect phase, merge when ready
lxa refine https://github.com/jpshackelford/lxa/pull/42 --auto-merge
```

### Higher Quality Bar

```bash
# Only merge if verdict is "good taste" (highest quality)
lxa refine https://github.com/jpshackelford/lxa/pull/42 --auto-merge --allow-merge good_taste
```

## Running as Background Job

For long-running refinement:

```bash
# Run in background
lxa refine URL --background

# Check status
lxa job list
lxa job status refine-<job_id>

# View logs
lxa job logs refine-<job_id> --follow
```

## Integration with Orchestrator

The orchestrator uses this skill by running `lxa refine` directly:

```bash
# Orchestrator decision tree:
# - Draft PR, CI green → lxa refine URL --phase self-review
# - Ready PR, 💬 > 0 → lxa refine URL --phase respond
# - Approved PR → lxa refine URL --auto-merge (or spawn merge worker)
```

## When NOT to Use

- PR has failing CI → Fix CI first
- PR is waiting for human review (no threads) → Wait
- PR was just merged → Nothing to refine

## Troubleshooting

### "No unresolved threads" but review requested changes

The reviewer may have requested changes without leaving inline comments. Check the review status:

```bash
gh pr view 42 --json reviewDecision
```

If `CHANGES_REQUESTED`, read the review body for feedback.

### Refinement keeps failing

Check the job logs:

```bash
lxa job logs <job_id>
```

Common issues:
- CI flaky tests → May need manual investigation
- Reviewer feedback unclear → Ask for clarification in PR comment
- Scope creep in review → Consider opening follow-up issues
