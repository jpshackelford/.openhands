---
name: expand-issue
description: Analyze and expand a GitHub issue with technical detail
triggers:
  - /expand-issue
---

# Expand Issue

Analyze a GitHub issue and expand it with technical detail so it's ready for implementation. This skill handles both bug reports and enhancement requests.

## Usage

```
/expand-issue
```

The orchestrator spawns an expansion worker with the issue number. This skill guides that worker.

## Goal

Transform a vague or incomplete issue into a well-defined, implementable work item by:
- Understanding the problem or request deeply
- Investigating the codebase for context
- For bugs: reproducing and finding root cause
- For enhancements: scoping the solution
- Adding technical detail as comments
- Labeling as `ready` when complete

## Issue Types

### Bug Reports

**Investigation Steps:**
1. Read the issue description carefully
2. Clone the repo, set up the environment (`uv sync`)
3. Attempt to reproduce the bug using described steps
4. If reproducible, investigate code to find root cause
5. If NOT reproducible, document what you tried and ask for clarification

**Rewrite Issue Body With:**
```markdown
## Problem
[Clear description of the bug]

## Steps to Reproduce
1. [Verified step 1]
2. [Verified step 2]
3. [...]

## Expected Behavior
[What should happen]

## Actual Behavior
[What actually happens]

## Environment
- Version/commit: [...]
- OS if relevant: [...]
```

**Add Comment With Technical Detail:**
```markdown
## 🔍 Root Cause Analysis

**Location:** `src/lxa/path/to/file.py` lines 42-58

**Cause:** [Explanation of why the bug occurs]

**Evidence:**
- [Code snippet or log output showing the issue]

## 💡 Proposed Fix

**Approach:** [High-level description]

**Files to modify:**
- `src/lxa/path/to/file.py` - [what changes]
- `tests/test_file.py` - [what tests to add]

**Complexity:** Low / Medium / High

**Risks:** [Any risks or side effects to consider]
```

### Enhancement Requests

**Investigation Steps:**
1. Read the issue description and any linked context
2. Understand the user need / pain point
3. Explore the codebase to understand current architecture
4. Identify where the enhancement would fit
5. Consider multiple approaches, select the best one

**Rewrite Issue Body With:**
```markdown
## Problem Statement
[What pain point or need does this address?]

## Proposed Solution
[High-level description of what we'll build]

## Acceptance Criteria
- [ ] [Specific, testable criterion 1]
- [ ] [Specific, testable criterion 2]
- [ ] [...]

## Out of Scope
- [What this issue explicitly does NOT include]
```

**Add Comment With Technical Detail:**
```markdown
## 🔧 Technical Approach

**Architecture:**
[How this fits into the existing system]

**Implementation Plan:**
1. [Step 1 - what to build first]
2. [Step 2 - ...]
3. [...]

**Files likely affected:**
- `src/lxa/path/to/file.py` - [what changes]
- `src/lxa/new_file.py` - [new file if needed]
- `tests/...` - [test files]

**CLI changes:** [New commands, flags, or options]

**Complexity:** Low / Medium / High

**Dependencies:** [Any blockers or prerequisites]
```

### Feature Requests (Larger Scope)

For larger features, the expansion should also consider:
- Breaking into smaller issues if too large
- Identifying a minimal viable implementation
- Noting what can be deferred to follow-up issues

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  EXPANSION WORKER FLOW                                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Clone repo, read issue: gh issue view {number}              │
│  2. Determine issue type (bug vs enhancement)                    │
│  3. Investigate:                                                 │
│     - Bug: Reproduce, find root cause                           │
│     - Enhancement: Understand need, explore codebase            │
│  4. Rewrite issue body with structured format                    │
│  5. Add technical detail comment                                 │
│  6. Add `ready` label: gh issue edit {number} --add-label ready │
│  7. Log completion to WORKLOG.md                                 │
│  8. Exit                                                         │
└─────────────────────────────────────────────────────────────────┘
```

## Commands Reference

```bash
# Read the issue
gh issue view {number} --repo jpshackelford/lxa

# Update issue body
gh issue edit {number} --repo jpshackelford/lxa --body "new body here"

# Or use body from file
gh issue edit {number} --repo jpshackelford/lxa --body-file /tmp/issue-body.md

# Add a comment
gh issue comment {number} --repo jpshackelford/lxa --body "comment here"

# Add ready label
gh issue edit {number} --repo jpshackelford/lxa --add-label "ready"

# Remove needs-triage label if present
gh issue edit {number} --repo jpshackelford/lxa --remove-label "needs-triage"
```

## When Expansion Fails

If you cannot fully expand the issue:

**Can't reproduce a bug:**
```markdown
## ⚠️ Unable to Reproduce

Attempted reproduction on [date] with commit [sha].

**Steps tried:**
1. [...]
2. [...]

**Result:** [What happened instead]

**Questions for reporter:**
- [Specific question 1]
- [Specific question 2]
```
- Add label: `needs-info`
- Do NOT add `ready` label

**Enhancement is too vague:**
```markdown
## ⚠️ Needs Clarification

The request is understood at a high level, but more detail is needed:

**Unclear aspects:**
- [What's unclear 1]
- [What's unclear 2]

**Questions:**
- [Specific question]
```
- Add label: `needs-info`
- Do NOT add `ready` label

**Issue should be split:**
```markdown
## 📋 Recommend Splitting

This issue covers multiple distinct pieces of work. Recommend splitting into:

1. **[Title 1]** - [brief description]
2. **[Title 2]** - [brief description]

Would you like me to create these as separate issues?
```
- Add label: `needs-split`
- Do NOT add `ready` label

## WORKLOG.md Update

Before exiting, update WORKLOG.md on main:

```markdown
### {timestamp} - Expansion Worker (`{conv_id}`)

✅ **Expanded Issue #{number}**

- Issue: [{title}](https://github.com/jpshackelford/lxa/issues/{number})
- Type: Bug / Enhancement
- Status: Ready for implementation / Needs info / Needs split
- Root cause: [brief summary if bug]
- Approach: [brief summary if enhancement]

---
```

## Labels Reference

| Label | When to Apply |
|-------|---------------|
| `ready` | Issue fully expanded, ready for implementation |
| `needs-info` | Cannot proceed without more information from reporter |
| `needs-split` | Issue too large, should be broken into smaller issues |
| `bug` | Confirmed bug (if not already labeled) |
| `enhancement` | Confirmed enhancement (if not already labeled) |
| `hold` | DO NOT APPLY - only humans set this to pause implementation |

**Important:** If an issue has the `hold` label, do NOT expand it. Skip it and move to the next issue.
