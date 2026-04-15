---
name: parallel-research
description: This skill should be used when the user asks to "research multiple questions", "investigate several topics in parallel", "spawn background jobs", "delegate tasks to background agents", or has a list of questions/tasks that could benefit from parallel execution. Uses lxa CLI to spawn background research jobs that preserve main conversation context.
triggers:
  - research multiple
  - investigate several
  - parallel research
  - background jobs
  - spawn jobs
  - delegate tasks
  - lxa run background
  - multiple questions
  - research in parallel
---

# Parallel Research Pattern

This skill describes a pattern for handling complex multi-part user requests by delegating each part to a background job. This preserves context in the main conversation while enabling parallel execution.

## When to Use This Pattern

Apply this pattern when:
- The user has multiple distinct questions or research tasks
- Each task requires exploration that would consume significant context
- Tasks are independent and can run in parallel
- Results need to be collected and potentially acted upon (e.g., filing issues)

## Core Workflow

### 1. Break Down the Request

Parse the user's request into discrete, independent tasks. Each task should be:
- Self-contained with clear deliverables
- Scoped to produce a concise report
- Named descriptively for status tracking

### 2. Spawn Background Jobs

Use `lxa run --background` to spawn each task:

```bash
lxa run --background \
  --job-name "task-name" \
  --task "Description of what to research. Write findings to /tmp/research-task-name.md"
```

**Key parameters:**
- `--background` / `-b`: Run detached from terminal
- `--job-name`: Meaningful identifier for tracking (e.g., "q1-api-review", "feature-analysis")
- `--task` / `-t`: Full task description including expected output location

### 3. Monitor Job Status

Check progress with:

```bash
# List all jobs with status
lxa job list

# Show running jobs only
lxa job list --running

# Get detailed status for a specific job
lxa job status <job-id-or-prefix>
```

### 4. Review Results

Once jobs complete:

```bash
# View tail of job logs
lxa job logs <job-id> --lines 50

# Read the output files
cat /tmp/research-*.md
```

### 5. Take Follow-up Actions

Based on research findings, spawn additional jobs for actions:

```bash
lxa run --background \
  --job-name "issue-feature-x" \
  --task "File a GitHub issue based on /tmp/research-feature-x.md. Use gh issue create."
```

## Example: Multi-Question Research

**User request:** "I have 5 questions about this codebase. Research them and file issues for improvements."

**Implementation:**

```bash
# Spawn research jobs (all at once)
lxa run -b --job-name "q1-caching" \
  --task "Research caching strategy in src/cache.py. Write report to /tmp/q1-caching.md"

lxa run -b --job-name "q2-api-design" \
  --task "Review API design in src/api/. Write report to /tmp/q2-api.md"

lxa run -b --job-name "q3-error-handling" \
  --task "Analyze error handling patterns. Write report to /tmp/q3-errors.md"

# Monitor progress
lxa job list

# Once complete, review findings
for f in /tmp/q*.md; do echo "=== $f ===" && cat "$f"; done

# Spawn issue-filing jobs based on findings
lxa run -b --job-name "issue-caching" \
  --task "File GitHub issue based on /tmp/q1-caching.md using gh issue create"
```

## Best Practices

### Task Descriptions

Write clear, self-contained task descriptions:
- State what to investigate
- Specify where to look (files, commands)
- Define output location and format
- Set scope limits (word count, depth)

**Good example:**
```
Research question about project: Which commands support --verbose flag?
Look at src/cli.py for command definitions. Check if flag is documented
in README.md. Write a brief report (under 500 words) to /tmp/verbose-audit.md
with findings and recommendations.
```

### Job Naming

Use descriptive, prefixed names:
- `q1-`, `q2-` for numbered questions
- `research-`, `audit-`, `review-` for task types
- `issue-`, `pr-` for action jobs

### Output Files

Use consistent temp file patterns:
- `/tmp/research-<topic>.md` for research reports
- `/tmp/action-<topic>.log` for action results
- Include job name in filename for correlation

### Status Reporting

Summarize job status for the user in a table:

| Job | Status | Duration |
|-----|--------|----------|
| q1-caching | ✅ done | 1m 40s |
| q2-api | 🔄 running | 2m 10s |
| q3-errors | ⏳ pending | - |

## Handling Results

### Aggregating Findings

```bash
# Check if all reports exist
ls /tmp/research-*.md

# Concatenate all reports
for f in /tmp/research-*.md; do
  echo "=== $(basename $f) ==="
  cat "$f"
  echo ""
done
```

### Decision Framework

After reviewing research outputs:
1. Identify which findings warrant action (issues, PRs, docs)
2. Group related findings that should be addressed together
3. Spawn action jobs for confirmed items
4. Report final status and created artifacts to user

## Related Commands Reference

```bash
# Launch background job
lxa run --background --job-name NAME --task "DESCRIPTION"

# List jobs
lxa job list [--running] [--limit N] [--json]

# Job details
lxa job status JOB_ID [--json]

# View logs
lxa job logs JOB_ID [--lines N] [--follow]

# Stop a job
lxa job stop JOB_ID

# Clean old jobs
lxa job clean
```

## Context Preservation Benefit

This pattern keeps the main conversation context lean by:
- Offloading detailed exploration to background jobs
- Storing intermediate results in files (not conversation history)
- Enabling the main agent to summarize and act on findings
- Supporting iterative refinement without context bloat
