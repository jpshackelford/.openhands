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
2. Clone the repo, set up the environment
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
- Browser/OS if relevant: [...]
```

**Add Comment With Technical Detail:**
```markdown
## 🔍 Root Cause Analysis

**Location:** `src/path/to/file.py` lines 42-58

**Cause:** [Explanation of why the bug occurs]

**Evidence:**
- [Code snippet or log output showing the issue]

## 💡 Proposed Fix

**Approach:** [High-level description]

**Files to modify:**
- `src/path/to/file.py` - [what changes]
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
- `src/path/to/file.py` - [what changes]
- `src/new_file.py` - [new file if needed]
- `tests/...` - [test files]

**Database changes:** [Yes/No, describe if yes]

**API changes:** [Yes/No, describe if yes]

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
gh issue view {number} --repo jpshackelford/voice-relay

# Update issue body
gh issue edit {number} --repo jpshackelford/voice-relay --body "new body here"

# Or use body from file
gh issue edit {number} --repo jpshackelford/voice-relay --body-file /tmp/issue-body.md

# Add a comment
gh issue comment {number} --repo jpshackelford/voice-relay --body "comment here"

# Add ready label
gh issue edit {number} --repo jpshackelford/voice-relay --add-label "ready"

# Remove needs-triage label if present
gh issue edit {number} --repo jpshackelford/voice-relay --remove-label "needs-triage"
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

**Issue is hard-blocked by another open issue:**

When investigation reveals that this issue cannot be implemented until one or more *other* open issues land first (missing schema, missing API surface, missing dependency PR, etc.), mark it `on-hold` and document the blockers in a **machine-parseable** comment so the orchestrator's unblock pass can lift the label automatically when the blockers close.

```markdown
## 🛑 on-hold rationale

This issue is hard-blocked by:

Blocked by #<N1>
Blocked by #<N2>

[One short paragraph explaining what each blocker provides and how it unblocks this issue.]

Remove `on-hold` and add `ready` once the blockers above close. The orchestrator's unblock pass will do this automatically; manual unblocking is also fine.

_This comment was posted by an AI agent (OpenHands expansion worker) on behalf of @jpshackelford._
```

- Add label: `on-hold` (and the appropriate `scope:*` / `priority:*` / type labels)
- Do NOT add `ready` label — the unblock pass adds it when all blockers close
- The `Blocked by #N` lines (one per blocker, each on its own line) are the **only** form the orchestrator's unblock pass parses. Phrases like "depends on #N" or "once #N lands" in prose are *not* parsed; if you want machine handling, you must include the literal `Blocked by #N` form. (Prose is still fine for humans; just add the machine form as well.)

## WORKLOG.md Update

Before exiting, update WORKLOG.md on main:

```markdown
### {timestamp} - Expansion Worker (`{conv_id}`)

✅ **Expanded Issue #{number}**

- Issue: [{title}](https://github.com/jpshackelford/voice-relay/issues/{number})
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
| `on-hold` | Hard-blocked by one or more *other open* issues. Comment MUST include one `Blocked by #N` line per blocker so the orchestrator's unblock pass can lift the label when all blockers close. Do NOT combine with `ready`. |
| `bug` | Confirmed bug (if not already labeled) |
| `enhancement` | Confirmed enhancement (if not already labeled) |
