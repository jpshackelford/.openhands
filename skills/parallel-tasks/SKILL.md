---
name: parallel-tasks
description: This skill should be used when the user has multiple discrete tasks that can run in parallel, such as "file issues for each finding", "update several PRs", "research multiple questions", "process these items independently", or when tasks produce external work products (issues, PRs, comments) or local artifacts that need aggregation. Uses lxa CLI to spawn background jobs that preserve main conversation context.
triggers:
  - parallel tasks
  - multiple tasks
  - background jobs
  - spawn jobs
  - delegate tasks
  - lxa run background
  - file multiple issues
  - update several PRs
  - research in parallel
  - process independently
---

# Parallel Task Execution Pattern

This skill describes a pattern for handling multiple discrete tasks by delegating each to a background job. This preserves context in the main conversation while enabling parallel execution.

## When to Use This Pattern

Apply this pattern when:
- The user has multiple independent tasks that can run in parallel
- Each task produces its own work product (external or local)
- Tasks don't depend on each other's results
- The main conversation should remain responsive and context-lean

**Best suited for tasks producing:**
- **External work products**: GitHub issues filed, PRs created/updated, comments posted, API calls made
- **Local artifacts**: Reports, analysis files, generated code that needs review or aggregation

## Prerequisites: Installing lxa

The `lxa` CLI is required for this pattern. Install from GitHub using `uv`:

```bash
# Install as a tool from GitHub (recommended)
uv tool install git+https://github.com/jpshackelford/lxa.git

# Or run directly without installing
uvx --from git+https://github.com/jpshackelford/lxa.git lxa --help
```

Verify installation:
```bash
lxa --version
lxa run --help
```

**Note:** When using `uvx`, prefix commands with `uvx --from git+https://github.com/jpshackelford/lxa.git` (e.g., `uvx --from git+https://github.com/jpshackelford/lxa.git lxa run --background ...`). When installed as a tool, use `lxa` directly.

## Core Workflow

### 1. Break Down the Request

Parse the user's request into discrete, independent tasks. Each task should be:
- Self-contained with clear deliverables
- Produce a specific work product (issue, PR, report, etc.)
- Named descriptively for status tracking

### 2. Spawn Background Jobs

Use `lxa run --background` to spawn each task:

```bash
lxa run --background \
  --job-name "task-name" \
  --task "Description of the task. Include expected deliverable (file path, issue URL, etc.)"
```

**Key parameters:**
- `--background` / `-b`: Run detached from terminal
- `--job-name`: Meaningful identifier for tracking (e.g., "issue-auth", "pr-update-docs")
- `--task` / `-t`: Full task description including expected deliverable

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

# For jobs with local artifacts, read the output files
cat /tmp/report-*.md

# For jobs with external work products, extract URLs from logs
lxa job logs <job-id> --lines 30 | grep -E "https://github.com/"
```

### 5. Take Follow-up Actions (Optional)

For local artifacts that need further processing, spawn additional jobs:

```bash
lxa run --background \
  --job-name "issue-feature-x" \
  --task "File a GitHub issue based on /tmp/report-feature-x.md. Use gh issue create."
```

## Example: Filing Multiple Issues

**User request:** "Based on these 4 findings, file GitHub issues for each."

**Implementation:**

```bash
# Spawn issue-filing jobs (all at once)
lxa run -b --job-name "issue-auth" \
  --task "File GitHub issue for auth improvement. Title: 'Add OAuth2 support'. Body: <details>. Use gh issue create."

lxa run -b --job-name "issue-cache" \
  --task "File GitHub issue for caching. Title: 'Implement Redis caching'. Body: <details>. Use gh issue create."

lxa run -b --job-name "issue-logging" \
  --task "File GitHub issue for logging. Title: 'Add structured logging'. Body: <details>. Use gh issue create."

lxa run -b --job-name "issue-tests" \
  --task "File GitHub issue for tests. Title: 'Increase test coverage'. Body: <details>. Use gh issue create."

# Monitor progress
lxa job list

# Once complete, collect issue URLs from logs
for job in issue-auth issue-cache issue-logging issue-tests; do
  lxa job logs $job --lines 20 | grep -E "https://github.com/.*/issues/"
done
```

## Example: Research with Local Artifacts

**User request:** "Research these 3 topics and write reports I can review."

**Implementation:**

```bash
# Spawn research jobs
lxa run -b --job-name "research-api" \
  --task "Analyze API design in src/api/. Write report to /tmp/research-api.md"

lxa run -b --job-name "research-perf" \
  --task "Profile performance bottlenecks. Write report to /tmp/research-perf.md"

lxa run -b --job-name "research-deps" \
  --task "Audit dependencies for security issues. Write report to /tmp/research-deps.md"

# Monitor progress
lxa job list

# Once complete, review findings
for f in /tmp/research-*.md; do echo "=== $f ===" && cat "$f"; done

# Based on review, spawn follow-up action jobs
lxa run -b --job-name "issue-perf" \
  --task "File GitHub issue based on /tmp/research-perf.md using gh issue create"
```

## Best Practices

### Task Descriptions

Write clear, self-contained task descriptions:
- State the objective and expected deliverable
- Specify relevant context (files, commands, URLs)
- For local artifacts, define output location and format
- Set scope limits where appropriate

**Good example (external work product):**
```
File a GitHub issue for the ohtv project requesting OAuth2 support.
Title: "Add OAuth2 authentication option"
Body should include: current auth limitations, proposed OAuth2 flow,
and reference to similar implementations in the codebase.
Use gh issue create. Report the issue URL when complete.
```

**Good example (local artifact):**
```
Analyze the caching strategy in src/cache.py. Check for cache invalidation
patterns and TTL handling. Write a brief report (under 500 words) to
/tmp/cache-analysis.md with findings and recommendations.
```

### Job Naming

Use descriptive, prefixed names:
- `issue-`, `pr-`, `comment-` for external work products
- `research-`, `audit-`, `review-` for local analysis
- `q1-`, `q2-` for numbered items in a list

### Output Files (Local Artifacts)

Use consistent temp file patterns:
- `/tmp/report-<topic>.md` for analysis reports
- `/tmp/audit-<topic>.md` for audit results
- Include job name in filename for correlation

### Status Reporting

Summarize job status for the user in a table:

| Job | Status | Duration |
|-----|--------|----------|
| q1-caching | ✅ done | 1m 40s |
| q2-api | 🔄 running | 2m 10s |
| q3-errors | ⏳ pending | - |

## Handling Results

### For External Work Products

Collect and report the created artifacts:

```bash
# Extract issue/PR URLs from job logs
for job in issue-auth issue-cache issue-tests; do
  echo "=== $job ==="
  lxa job logs $job --lines 20 | grep -E "https://github.com/"
done
```

### For Local Artifacts

Aggregate and review before next steps:

```bash
# Check if all reports exist
ls /tmp/report-*.md

# Review all reports
for f in /tmp/report-*.md; do
  echo "=== $(basename $f) ==="
  cat "$f"
  echo ""
done
```

### Decision Framework

After jobs complete:
1. For external work products: collect URLs and report to user
2. For local artifacts: review findings and determine if follow-up actions needed
3. Spawn additional jobs for confirmed follow-up items
4. Report final status and all created artifacts to user

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

## Why Use This Pattern

This pattern keeps the main conversation context lean by:
- Offloading discrete tasks to background jobs
- External work products (issues, PRs) persist outside the conversation
- Local artifacts stored in files (not conversation history)
- Main agent stays responsive and can monitor/aggregate results
- Parallel execution completes faster than sequential processing
