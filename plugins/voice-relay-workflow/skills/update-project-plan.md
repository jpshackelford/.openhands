---
name: update-project-plan
description: Reflect on learnings and update issue comments with notes
triggers:
  - /update-plan
  - /reflect
---

# Update Project Plan

Reflect on work done and capture learnings as comments on GitHub issues. This skill is used at key checkpoints:
- After implementing a feature (before moving PR to ready)
- After addressing review feedback (if learnings impact other issues)
- After merging (to note any follow-up items)

## Usage

```
/update-plan
```

or

```
/reflect
```

## When to Use

### After Implementation (Recommended)
Before moving a PR from draft to ready:
1. What did you learn while implementing?
2. Does this change what the next issue should be?
3. Are there insights that affect other open issues?
4. Are there new issues that should be filed?

### After Review Round (If Applicable)
If review feedback revealed something important:
1. Did the reviewer point out a fundamental issue?
2. Does this change the architectural approach for other issues?
3. Should notes be added to related issues?

### After Merge (If Applicable)
When a PR is merged and the issue auto-closes:
1. Were there any learnings that affect future issues?
2. Should new issues be filed for follow-up work?
3. Were acceptance criteria met or partially deferred?

## How to Capture Learnings

### 1. Review the Issue and Related Issues

```bash
# View the current issue
gh issue view {number} --repo jpshackelford/voice-relay

# List related open issues
gh issue list --repo jpshackelford/voice-relay --state open --json number,title
```

### 2. Reflect on Learnings

Think about:
- What worked well?
- What was harder than expected?
- What would you do differently?
- What does the next issue need to know?

### 3. Add Comments to Issues

If learnings affect other issues, add a comment:

```bash
gh issue comment {number} --repo jpshackelford/voice-relay --body "**Note from Issue #X implementation:**
- Discovered that {finding}
- This affects this issue because {reason}
- Suggested approach: {recommendation}"
```

### 4. File New Issues if Needed

If work revealed new requirements or follow-up work:

```bash
gh issue create --repo jpshackelford/voice-relay \
  --title "Follow-up: {description}" \
  --body "Discovered during Issue #{original_number} implementation.

## Context
{what was discovered}

## Proposed Solution
{suggested approach}

## Acceptance Criteria
- [ ] {criterion 1}
- [ ] {criterion 2}"
```

## Example Updates

### Adding Learning to Related Issue
```bash
gh issue comment 11 --repo jpshackelford/voice-relay --body "**Note from Issue #9 (Scope messages to sessions):**
- The session_devices table already tracks device-session associations
- This issue can leverage that table for detecting connected devices
- The WebSocket handler now broadcasts with session scope - will need to respect that"
```

### Filing a Follow-up Issue
```bash
gh issue create --repo jpshackelford/voice-relay \
  --title "F5: Add session expiration and cleanup" \
  --body "Discovered during Issue #9 implementation - sessions never expire.

## Context
Sessions are created but never cleaned up. Over time this could lead to stale sessions accumulating.

## Proposed Solution
Add background job to expire sessions after 24h of inactivity and clean up orphaned session_devices records.

## Acceptance Criteria
- [ ] Sessions marked expired after 24h inactivity
- [ ] Expired sessions not shown in UI
- [ ] session_devices cleaned up for expired sessions"
```

## Important Notes

- **Keep learnings specific** - vague notes aren't helpful
- **Link to the source issue** when adding comments to other issues
- **File new issues** for substantial follow-up work rather than expanding scope
- **Acceptance criteria** in new issues should be clear and testable
