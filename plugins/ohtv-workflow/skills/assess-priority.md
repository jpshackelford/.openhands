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
| **Critical** | Blocking usage, data loss risk, security issue |
| **High** | Significant user pain, affects core CLI functionality |
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
| **High** | Risky change, touches critical paths |

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

### Step 1: Gather Ready Issues

```bash
# List all issues with 'ready' label
gh issue list --repo jpshackelford/ohtv --label "ready" --json number,title,labels,body --jq '.[] | {number, title, labels: [.labels[].name]}'
```

### Step 2: Read Each Issue

For each ready issue, read the full content including technical comments:

```bash
gh issue view {number} --repo jpshackelford/ohtv --comments
```

### Step 3: Score Each Issue

Create a mental (or written) scorecard:

```
Issue #15 - Add --json output flag
  Impact: Medium (useful for scripting)
  Urgency: Low (workarounds exist)
  Complexity: Low (straightforward addition)
  Dependencies: None
  Risk: Low (additive change)
  → Priority: MEDIUM (but good quick win)

Issue #16 - Fix conversation sync timeout
  Impact: High (blocks usage for large histories)
  Urgency: High (users hitting this regularly)
  Complexity: Medium (needs investigation)
  Dependencies: None
  Risk: Medium (touches core sync logic)
  → Priority: HIGH
```

### Step 4: Apply Labels

```bash
# Apply priority label
gh issue edit {number} --repo jpshackelford/ohtv --add-label "priority:high"

# Can also remove old priority if reassessing
gh issue edit {number} --repo jpshackelford/ohtv --remove-label "priority:medium" --add-label "priority:high"
```

### Step 5: Return Recommendation

After assessing all ready issues, return to the orchestrator with:

```
PRIORITY ASSESSMENT COMPLETE

Recommended next issue: #16 - Fix conversation sync timeout
  Priority: HIGH
  Rationale: Core functionality issue affecting user experience,
             moderate complexity, no blockers.

Other ready issues:
  #15 - Add --json output flag (MEDIUM) - Good quick win after #16
  #17 - Improve error messages (LOW) - Nice to have
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

### Hold Issues

Issues with the `hold` label should NOT be implemented:
- Human has explicitly put the issue on hold
- Skip in priority assessment entirely
- Do not remove the `hold` label - only humans should do that

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
