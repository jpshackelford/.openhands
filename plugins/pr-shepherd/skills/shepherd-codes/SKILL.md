---
name: shepherd-codes
description: Reference for interpreting lxa pr list history codes. Explains what each character means, case conventions, common patterns, and how to determine next actions from history.
triggers:
- /shepherd-codes
- /history-codes
---

# PR History Codes Reference

Complete reference for interpreting the history codes from `lxa pr list`.

## Code Meanings

| Code | Action | Description |
|------|--------|-------------|
| `o` | Opened | PR was created |
| `h` | Help | Review was requested |
| `r` / `R` | Review | Changes requested |
| `c` / `C` | Comment | Comment added (not a formal review) |
| `f` / `F` | Fix | Commits pushed after a review |
| `a` / `A` | Approved | PR approved |
| `m` | Merged | PR was merged |
| `k` | Killed | PR was closed without merging |

## Case Convention

The case of each letter indicates **who performed the action**:

- **lowercase** = Action by the reference user (you, the PR author in `lxa pr list`)
- **UPPERCASE** = Action by someone else (a reviewer)

### Examples

| Code | Meaning |
|------|---------|
| `o` | You opened the PR |
| `R` | Someone else requested changes |
| `f` | You pushed fixes |
| `A` | Someone else approved |
| `oRfA` | You opened, they reviewed, you fixed, they approved |

## Reading History Strings

History strings are read **left to right** chronologically:

```
oRfA
│││└─ Approved (by reviewer)
││└── Fixes pushed (by you)
│└─── Changes requested (by reviewer)
└──── Opened (by you)
```

## Common Patterns

### Successful Cycles

| Pattern | Meaning | Status |
|---------|---------|--------|
| `oA` | Approved on first review | Ready to merge |
| `oRfA` | One review cycle, then approved | Ready to merge |
| `oRfRfA` | Two review cycles, then approved | Ready to merge |
| `oAm` | Approved and merged | Done |
| `oRfAm` | Full cycle, merged | Done |

### In Progress

| Pattern | Meaning | Who Acts Next |
|---------|---------|---------------|
| `o` | Just opened | Reviewer |
| `oR` | Changes requested | Author (you) |
| `oRf` | Fixes pushed | Reviewer |
| `oRfR` | More changes requested | Author (you) |
| `oRfRf` | More fixes pushed | Reviewer |

### Terminal States

| Pattern | Meaning | Status |
|---------|---------|--------|
| `...m` | Ends with merge | Done ✓ |
| `...k` | Ends with close | Closed (abandoned) |

## The Last Character Rule

The **last character** tells you the most recent action and who should act next:

| Ends With | What Just Happened | Who Acts Next |
|-----------|-------------------|---------------|
| `o` | Just opened | Reviewer reviews |
| `R` | Changes requested | Author fixes |
| `f` | Fixes pushed | Reviewer re-reviews |
| `A` | Approved | Ready to merge |
| `m` | Merged | Done |
| `k` | Killed | Done |
| `c` / `C` | Comment added | Depends on comment |

## Decision Matrix from History

Use this to determine what action to take:

```
History ends with 'm'?
└─ Yes → Done (merged)

History ends with 'k'?
└─ Yes → Done (closed)

History ends with 'A' (approved)?
└─ Yes → Ready to merge
   └─ Action: /shepherd-merge

History ends with 'R' (changes requested)?
└─ Yes → Reviewer wants changes
   └─ Are you the author?
      ├─ Yes → Address feedback
      │  └─ Action: /shepherd-respond
      └─ No → Wait for author

History ends with 'f' (fixes pushed)?
└─ Yes → Waiting for re-review
   └─ Action: Wait (or nudge reviewer if stale)

History ends with 'o' (just opened)?
└─ Yes → Needs initial review
   └─ If draft: /shepherd-self-review
   └─ If ready: Wait for reviewer
```

## Perspective Matters

### From Author's View (`lxa pr list`)

When you're the PR author:
- `oRf` = "I opened, reviewer requested changes, I pushed fixes"
- lowercase = your actions, UPPERCASE = reviewer actions

### From Reviewer's View (`lxa review`)

When you're reviewing someone else's PR:
- `oRf` = "Author opened, I requested changes, they pushed fixes"
- lowercase = your actions (as reviewer), UPPERCASE = author actions

The perspective flips based on which command you're using.

## Examples with Full Analysis

### Example 1: `oRf`

```
History: oRf
Position: Fixes pushed, awaiting re-review

Timeline:
  o - PR opened (by author)
  R - Changes requested (by reviewer)
  f - Fixes pushed (by author)

Current state: Ball is in reviewer's court
Next action: Wait for re-review (or nudge if stalled)
```

### Example 2: `oRfRfA`

```
History: oRfRfA
Position: Approved after multiple cycles

Timeline:
  o  - PR opened
  R  - First review: changes requested
  f  - Author pushed fixes
  R  - Second review: more changes requested
  f  - Author pushed more fixes
  A  - Third review: approved!

Current state: Ready to merge
Next action: /shepherd-merge
```

### Example 3: `oCcCc`

```
History: oCcCc
Position: Discussion in progress

Timeline:
  o - PR opened
  C - Someone commented
  c - You replied
  C - They responded
  c - You replied again

Current state: Discussion ongoing
Next action: Depends on comment content - may need formal review
```

### Example 4: `oAf`

```
History: oAf
Position: Approved, but then more commits pushed

Timeline:
  o - PR opened
  A - Approved
  f - More commits pushed (after approval!)

Current state: May need re-review (commits after approval)
Next action: Check if reviewer wants to re-review new commits
```

## Additional Status Columns

History codes work alongside other `lxa pr list` columns:

| Column | Values | Meaning |
|--------|--------|---------|
| **CI** | 🟢/🔴/⏳/⚠️ | green/red/pending/conflict |
| **State** | draft/ready/merged/closed | PR state |
| **💬** | 0, 1, 2... | Unresolved thread count |

### Combined Decision Making

```
CI = RED?
└─ Fix CI first, regardless of history

Threads > 0?
└─ Respond to threads, regardless of history

Then check history for next action.
```

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ PR HISTORY CODES QUICK REFERENCE                        │
├─────────────────────────────────────────────────────────┤
│ o = Opened       h = Help requested    m = Merged       │
│ r/R = Review     f/F = Fix pushed      k = Killed       │
│ a/A = Approved   c/C = Comment                          │
├─────────────────────────────────────────────────────────┤
│ CASE: lowercase = you, UPPERCASE = other person         │
├─────────────────────────────────────────────────────────┤
│ LAST CHAR → NEXT ACTION:                                │
│   A → merge    R → fix    f → wait    m/k → done        │
└─────────────────────────────────────────────────────────┘
```

## Related Skills

- `/shepherd` - Get situational awareness
- `/shepherd-advance` - Take action based on history
