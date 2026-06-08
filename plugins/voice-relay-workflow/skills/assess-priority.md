---
name: assess-priority
description: Assess and prioritize ready issues for implementation
triggers:
  - /assess-priority
  - /prioritize
---

# Assess Priority

Evaluate all `ready` issues and determine which one to implement next. This skill runs inline within the orchestrator conversation (not spawned as a separate worker).

## Usage

```
/assess-priority
```

or

```
/prioritize
```

## When to Use

The orchestrator calls this skill when:
- There are multiple `ready` issues
- No priority labels have been assigned yet
- Or priorities need reassessment after a merge

## Priority Factors

Assess each issue across these dimensions:

### 1. Impact (Weight: High)

| Level | Description |
|-------|-------------|
| **Critical** | Blocking production, data loss risk, security issue |
| **High** | Significant user pain, affects core functionality |
| **Medium** | Noticeable improvement, affects secondary features |
| **Low** | Nice to have, polish, minor improvements |

### 2. Urgency (Weight: High)

| Level | Description |
|-------|-------------|
| **Critical** | Must be fixed immediately |
| **High** | Should be done this sprint/week |
| **Medium** | Should be done soon, but not blocking |
| **Low** | Can wait, no time pressure |

### 3. Complexity (Weight: Medium - inverse)

| Level | Description |
|-------|-------------|
| **Low** | Simple change, well-understood, < 1 hour |
| **Medium** | Moderate change, some investigation needed, 1-4 hours |
| **High** | Complex change, significant work, 4+ hours |

*Lower complexity = higher priority when other factors are equal (quick wins)*

### 4. Dependencies (Weight: Medium)

| Factor | Impact |
|--------|--------|
| Blocks other issues | Higher priority |
| Blocked by other issues | Lower priority (or defer) |
| Foundation for future work | Higher priority |
| Standalone | Neutral |

### 5. Risk (Weight: Low - inverse)

| Level | Description |
|-------|-------------|
| **Low** | Safe change, well-tested area, easy rollback |
| **Medium** | Some risk, needs careful testing |
| **High** | Risky change, touches critical paths, hard to rollback |

*Higher risk = may need more careful sequencing*

## Priority Matrix

Combine factors into a priority label:

| Priority | Criteria |
|----------|----------|
| `priority:critical` | Critical impact OR critical urgency |
| `priority:high` | High impact + High urgency, OR Critical + any blocker |
| `priority:medium` | Medium impact/urgency, OR High + Low complexity (quick win) |
| `priority:low` | Low impact + Low urgency, OR nice-to-have improvements |

## Assessment Process

### Gather ready issues

```bash
# List all issues with 'ready' label
gh issue list --repo jpshackelford/voice-relay --label "ready" --json number,title,labels,body --jq '.[] | {number, title, labels: [.labels[].name]}'
```

### Read each issue

For each ready issue, read the full content including technical comments:

```bash
gh issue view {number} --repo jpshackelford/voice-relay --comments
```

### Score each issue

Create a mental (or written) scorecard:

```
Issue #9 - Scope messages to sessions
  Impact: High (core functionality)
  Urgency: High (users confused by message mixing)
  Complexity: Medium (requires schema change)
  Dependencies: None
  Risk: Medium (database migration)
  → Priority: HIGH

Issue #10 - Workspace Home
  Impact: Medium (UX improvement)
  Urgency: Low (not blocking anything)
  Complexity: Low (UI only)
  Dependencies: None
  Risk: Low (no backend changes)
  → Priority: MEDIUM (but good quick win)
```

### Apply labels

```bash
# Apply priority label
gh issue edit {number} --repo jpshackelford/voice-relay --add-label "priority:high"

# Can also remove old priority if reassessing
gh issue edit {number} --repo jpshackelford/voice-relay --remove-label "priority:medium" --add-label "priority:high"
```

### Return recommendation

After assessing all ready issues, return to the orchestrator with:

```
PRIORITY ASSESSMENT COMPLETE

Recommended next issue: #9 - Scope messages to sessions
  Priority: HIGH
  Rationale: Core functionality issue affecting user experience, 
             moderate complexity, no blockers.

Other ready issues:
  #10 - Workspace Home (MEDIUM) - Good quick win after #9
  #11 - Session View (MEDIUM) - Depends on #9
  #12 - Join via QR (LOW) - Nice to have
```

## Tie-Breaking Rules

When two issues have the same priority:

1. **Prefer lower complexity** (quick wins build momentum)
2. **Prefer issues that unblock others** (dependencies)
3. **Prefer bugs over enhancements** (fix before build)
4. **Prefer older issues** (don't let things languish)

## Special Cases

### All Issues Are Low Priority

If all ready issues are low priority:
- Still pick the best one
- Note in WORKLOG that we're in "polish mode"

### Critical Issue Appears

If a new critical issue appears:
- It jumps the queue immediately
- May need to pause current PR work (orchestrator decision)

### Blocked Issues

If an issue is blocked by external factors:
- Add `blocked` label
- Add comment explaining what it's blocked on
- Skip in priority assessment until unblocked

## Output Format

The skill should output a structured recommendation:

```
## Priority Assessment

**Assessed:** {count} ready issues

**Recommendation:** Implement Issue #{number} next

| Issue | Priority | Rationale |
|-------|----------|-----------|
| #{number} - {title} | `{priority}` ⬅️ NEXT | {brief rationale} |
| #{number} - {title} | `{priority}` | {brief rationale} |
| ... | ... | ... |

**Labels Applied:** 
- Issue #{n}: `priority:{level}`
- Issue #{n}: `priority:{level}`
```

The orchestrator uses this output to decide which issue to spawn an implementation worker for.
