---
name: lxa-pr-refinement
description: Two-phase automated PR refinement using LXA. Self-review catches issues before human review; respond phase addresses reviewer comments automatically.
triggers:
- lxa refine
- pr refinement
- self review
- address reviews
- review iteration
---

# LXA PR Refinement

This skill uses LXA's two-phase refinement loop to automatically improve PR quality and address reviewer feedback.

## The Review Iteration Problem

Traditional PR workflow requires many human-agent cycles:

```
Agent opens PR → Human reviews → Agent fixes → Human re-reviews → repeat...
```

LXA refinement automates this:

```
Agent opens PR → Self-Review (agent reviews itself) → Human reviews →
Respond Phase (agent addresses feedback) → Human approves
```

## Two Phases

### Phase 1: Self-Review

Before requesting human review, the agent:

1. Checks out the PR branch
2. Waits for CI to pass
3. Reviews its own code against quality principles
4. Fixes any issues found
5. Commits improvements
6. Marks PR ready for human review

**Quality Principles Used:**
- Data structures first (poor choices create complexity)
- Simplicity and "good taste" (no deep nesting, no special cases)
- Pragmatism (solve real problems, not theoretical ones)
- Testing (new behavior needs tests)
- Skip style nits (linter territory)

### Phase 2: Review Response

After human review, the agent:

1. Reads each unresolved review thread
2. Evaluates if feedback is valid
3. Makes fixes (preferring root-cause solutions)
4. Commits with `Address review: [description]`
5. Pushes changes
6. Waits for CI
7. Replies to each thread with commit SHA
8. Marks threads as resolved

## Quick Start

```bash
# Auto-detect which phase to run
lxa refine https://github.com/owner/repo/pull/42

# With automatic merge when done
lxa refine https://github.com/owner/repo/pull/42 --auto-merge
```

## Prerequisites

- LXA installed: `pip install lxa` or from [jpshackelford/lxa](https://github.com/jpshackelford/lxa)
- `LLM_API_KEY` or equivalent
- `GITHUB_TOKEN` with repo access
- The PR must already exist

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--phase` | `auto` | Which phase: `auto`, `self-review`, `respond` |
| `--auto-merge` | false | Squash & merge when refinement passes |
| `--allow-merge` | `acceptable` | Quality bar: `good_taste` or `acceptable` |
| `--min-iterations` | 1 | Minimum iterations before accepting "acceptable" |
| `--max-iterations` | 5 | Maximum refinement iterations |

### Phase Selection

```bash
# Auto-detect based on PR state
lxa refine URL

# Explicitly run self-review
lxa refine URL --phase self-review

# Explicitly run review response
lxa refine URL --phase respond
```

Auto-detection logic:
- Draft PR → Self-Review phase
- Non-draft with unresolved threads → Respond phase
- Non-draft with no threads → Already complete

### Quality Bar

```bash
# Only merge when self-review verdict is 🟢 (highest quality)
lxa refine URL --allow-merge good_taste

# Merge when verdict is 🟢 or 🟡 (default)
lxa refine URL --allow-merge acceptable
```

Verdicts:
- 🟢 **Good taste**: Code is clean, ready for review
- 🟡 **Acceptable**: Works correctly, minor improvements possible
- 🔴 **Needs rework**: Continue fixing issues

## Integration with Implementation

Combine implementation and refinement in one command:

```bash
# Implement all milestones, then refine the PR
lxa implement --loop --refine

# With auto-merge
lxa implement --loop --refine --auto-merge

# Custom refinement settings
lxa implement --loop --refine --allow-merge good_taste --max-refine-iterations 10
```

## Comparison with github-pr-workflow

### Traditional PR Workflow (neubig/workflow)

Manual iteration loop:

```bash
# Check unresolved threads
gh api graphql -f query='...'

# Fix each issue manually
# Push changes
# Reply to threads
gh api graphql -f query='mutation {...}'

# Resolve threads
gh api graphql -f query='mutation {...}'

# Wait for CI
sleep 300
gh pr checks
```

**Manual steps**: Check → Fix → Push → Reply → Resolve → Wait → Repeat

### LXA PR Refinement

Automated loop:

```bash
lxa refine https://github.com/owner/repo/pull/42
```

**Automated**:
- CI waiting with polling
- Thread fetching
- Code fixes based on feedback
- Commit with proper messages
- Thread replies with commit SHAs
- Thread resolution

### What LXA Refinement Adds

| Feature | github-pr-workflow | LXA Refine |
|---------|-------------------|------------|
| Self-review | ❌ | ✅ Agent reviews itself first |
| CI waiting | Manual sleep | Automatic polling |
| Thread handling | Manual GraphQL | Automatic |
| Quality assessment | Checklist-based | Verdict-based (🟢🟡🔴) |
| Auto-merge | ❌ | ✅ Optional |

### What Still Requires github-pr-workflow

- **Evidence gathering**: LXA refine doesn't generate test evidence
- **PR description structure**: Initial PR setup
- **Manual testing**: Platform-specific verification

## Review Response Principles

The agent follows these principles when responding to reviews:

1. **Evaluate Before Acting**
   - Not all feedback must be implemented
   - Consider: Does this genuinely improve the code?

2. **Fix Root Causes, Not Symptoms**
   - Prefer proper fixes over `# type: ignore`
   - Ask: "Am I fixing this, or hiding it?"

3. **Stay In Scope**
   - Don't implement new features during review response
   - Suggest follow-up PRs for out-of-scope suggestions

4. **Reasonable Cleanup Is OK**
   - Opportunistic cleanup in the touched area is acceptable
   - Keep cleanup proportional

5. **Explain Decisions**
   - When declining feedback, explain why respectfully
   - When implementing, reference the commit SHA

## Example: Complete Flow

```bash
# 1. Agent creates a draft PR during implementation
lxa implement --loop

# 2. Self-review runs automatically at end
# Agent reviews its own code, fixes issues, marks PR ready

# 3. Human reviews the PR, leaves comments
# ... on GitHub ...

# 4. Agent addresses review comments
lxa refine https://github.com/owner/repo/pull/42

# 5. If approved and auto-merge enabled, PR merges
lxa refine URL --auto-merge
```

## Monitoring Refinement

Watch the terminal for:

```
[bold blue]PR Refinement - Self-Review[/]
Repository: owner/repo
PR: #42
Auto-merge: False

✓ CI passing
📝 Reviewing code changes...
🔧 Fixed: Unnecessary nested conditionals
🔧 Fixed: Missing error handling
...
Verdict: 🟢 Good taste

[bold]Self-Review Complete[/]
Status: Completed
Duration: 0:05:32
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No unresolved threads" | PR may already be resolved |
| CI never passes | Check CI logs, fix issues manually |
| Wrong phase detected | Use `--phase` to force specific phase |
| Agent declines valid feedback | Review its explanation, provide context |

## When to Use Each Phase

| Scenario | Phase | Command |
|----------|-------|---------|
| Just opened PR, want review | Self-Review | `lxa refine URL --phase self-review` |
| Human left review comments | Respond | `lxa refine URL --phase respond` |
| Not sure | Auto | `lxa refine URL` |
| End of implementation | Integrated | `lxa implement --loop --refine` |

## References

- [LXA PR Refinement Reference](https://github.com/jpshackelford/lxa/blob/main/doc/reference/pr-refinement.md)
- [github-pr-workflow skill](https://github.com/neubig/workflow/blob/main/skills/github-pr-workflow/SKILL.md)
- [Code Review Principles](https://github.com/jpshackelford/lxa/blob/main/src/ralph/refinement_config.py)
