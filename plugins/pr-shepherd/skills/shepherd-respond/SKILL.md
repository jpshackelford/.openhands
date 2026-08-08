---
name: shepherd-respond
description: Respond to review comments on a PR. Reads unresolved threads, evaluates feedback, makes fixes, replies with commit SHAs, and resolves threads. Use when /shepherd reports threads > 0.
triggers:
- /shepherd-respond
---

# Shepherd Respond - Address Review Comments

Respond to review comments on a PR.

## When to Use

- `/shepherd` reports 💬 > 0 (unresolved threads)
- "Address the review comments on PR #123"
- "Respond to reviewers"
- History shows `R` (changes requested)

## Usage

```bash
/shepherd-respond owner/repo#123
/shepherd-respond https://github.com/owner/repo/pull/123

# Background execution
lxa refine <URL> --background --phase respond
```

## Workflow

### Step 1: Get Unresolved Threads

```bash
# Via GraphQL
gh api graphql -f query='
{
  repository(owner: "OWNER", name: "REPO") {
    pullRequest(number: NUMBER) {
      reviewThreads(first: 50) {
        nodes {
          id
          isResolved
          path
          line
          comments(first: 10) {
            nodes { 
              body 
              author { login }
              createdAt
            }
          }
        }
      }
    }
  }
}'
```

### Step 2: For Each Unresolved Thread

1. **Read** the comment chain and understand the request
2. **Evaluate** if feedback is valid and actionable:
   - Is it technically correct?
   - Is the change within scope?
   - Does it conflict with user intent?
3. **Decide**: implement, discuss, or respectfully decline

### Step 3: If Implementing

1. Check out PR branch:
   ```bash
   gh pr checkout <number>
   ```

2. Make the fix

3. Commit with descriptive message:
   ```bash
   git commit -m "Address review: <description>
   
   Responds to feedback from @<reviewer> on <file>"
   ```

4. Track which thread this commit addresses

### Step 4: After All Fixes

1. Push all commits:
   ```bash
   git push
   ```

2. Wait for CI:
   ```bash
   gh pr checks <number> --watch
   ```

### Step 5: Reply and Resolve Threads

For each addressed thread:

```bash
# Reply with commit SHA
gh api graphql -f query='
mutation {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: "THREAD_ID"
    body: "Fixed in abc1234"
  }) { comment { id } }
}'

# Mark resolved
gh api graphql -f query='
mutation {
  resolveReviewThread(input: {threadId: "THREAD_ID"}) {
    thread { isResolved }
  }
}'
```

## Review Response Principles

### 1. Evaluate Before Acting

Not all feedback must be implemented. Assess:
- Does this genuinely improve code quality?
- Is the concern valid for this context?
- Is it style preference vs. substantive issue?

### 2. Fix Root Causes, Not Symptoms

- Prefer proper fixes over workarounds
- If using `# type: ignore` or similar, explain why
- Ask: "Am I fixing this or hiding it?"

### 3. Stay In Scope

- Don't implement new features while responding
- Avoid scope creep beyond PR's purpose
- Suggest follow-up PRs for out-of-scope ideas

### 4. Reasonable Cleanup Is OK

- Opportunistic cleanup in touched areas is acceptable
- Keep cleanup proportional to the change

### 5. Explain Decisions

When declining feedback:
```
Thanks for the suggestion! I considered this but decided to keep 
the current approach because [reason]. Happy to discuss further 
if you feel strongly about it.
```

When implementing:
```
Good catch! Fixed in abc1234.
```

## Handling Different Comment Types

| Comment Type | Response |
|--------------|----------|
| Bug/correctness issue | Fix and reference commit |
| Performance concern | Evaluate, fix if valid, explain if not |
| Style/preference | Usually defer to reviewer if minor |
| Architectural concern | Discuss, may need larger changes |
| Question (no action needed) | Answer the question |
| Nitpick explicitly labeled | Optional to address |

## Output Format

```
Review Response for owner/repo#123
==================================

Found 3 unresolved threads:

Thread 1: @reviewer on src/feature.py:42
  Comment: "This could cause a null pointer exception"
  Action: IMPLEMENTING
  Fix: Added null check
  Commit: abc1234

Thread 2: @reviewer on src/utils.py:15
  Comment: "Consider using a constant here"
  Action: IMPLEMENTING  
  Fix: Extracted to TIMEOUT_SECONDS constant
  Commit: def5678

Thread 3: @reviewer on README.md:10
  Comment: "Typo in documentation"
  Action: IMPLEMENTING
  Fix: Corrected spelling
  Commit: def5678 (same commit)

Pushed 2 commits.
CI status: Waiting...

Replying to threads...
  ✓ Thread 1: Replied and resolved
  ✓ Thread 2: Replied and resolved
  ✓ Thread 3: Replied and resolved

All threads addressed.
```

## Alternative: lxa refine

For automated refinement loop with built-in principles:

```bash
lxa refine <URL> --phase respond
```

This handles the full loop including CI waits and thread resolution.

## Related Skills

- `/shepherd` - Get initial status
- `/shepherd-advance` - Auto-determine action
- `/shepherd-codes` - Understand history codes
