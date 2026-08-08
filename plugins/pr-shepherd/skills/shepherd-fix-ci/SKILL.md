---
name: shepherd-fix-ci
description: Diagnose and fix CI failures on a PR. Analyzes failed checks, classifies failures as branch-related vs flaky, makes fixes or retries as appropriate. Use when /shepherd reports CI = RED or CI = CONFLICT.
triggers:
- /shepherd-fix-ci
---

# Shepherd Fix CI

Diagnose and fix CI failures on a PR.

## When to Use

- `/shepherd` reports CI = RED
- `/shepherd` reports CI = CONFLICT  
- "Fix the CI on PR #123"
- "Why is CI failing?"
- "Resolve the merge conflict"

## Usage

```bash
/shepherd-fix-ci owner/repo#123
/shepherd-fix-ci https://github.com/owner/repo/pull/123
```

## Workflow

### Step 1: Get Failure Details

```bash
# Get PR info including CI status
gh pr view <number> --json headRefName,statusCheckRollup,mergeable

# List failed checks
gh pr checks <number> --fail

# Get specific failed run details
gh run view <run-id> --json jobs,conclusion,url,headSha

# Get failure logs
gh run view <run-id> --log-failed
```

### Step 2: Classify the Failure

**Branch-Related (fix required):**
- Compile/build errors in changed files
- Type check errors in modified code
- Test failures in changed areas
- Lint errors introduced by PR
- Snapshot mismatches from UI changes

**Flaky/Infrastructure (retry):**
- Network/DNS timeouts
- Dependency download failures
- Runner provisioning errors
- GitHub Actions infrastructure issues
- External service rate limits
- Non-deterministic test failures in unchanged areas

**Merge Conflict:**
- `mergeable: CONFLICTING`
- Requires manual conflict resolution

### Step 3: Take Action

#### For Branch-Related Failures

1. Check out the PR branch:
   ```bash
   gh pr checkout <number>
   ```

2. Reproduce locally if possible:
   ```bash
   # Run the failing test/check locally
   make test
   make lint
   make typecheck
   ```

3. Fix the issue

4. Commit with descriptive message:
   ```bash
   git commit -m "fix: CI failure on PR #<n>
   
   - Fixed <specific issue>
   - <Additional context>"
   ```

5. Push:
   ```bash
   git push
   ```

6. Verify CI starts:
   ```bash
   gh pr checks <number> --watch
   ```

#### For Flaky/Infrastructure Failures

1. Confirm failure is not branch-related (check logs)

2. Rerun failed jobs:
   ```bash
   gh run rerun <run-id> --failed
   ```

3. Monitor:
   ```bash
   gh run watch <run-id>
   ```

4. If fails again after 2-3 retries, investigate deeper or escalate

#### For Merge Conflicts

1. Check out the PR branch:
   ```bash
   gh pr checkout <number>
   ```

2. Fetch and merge main:
   ```bash
   git fetch origin main
   git merge origin/main
   ```

3. Resolve conflicts in each file

4. Complete the merge:
   ```bash
   git add .
   git commit -m "chore: resolve merge conflicts with main"
   ```

5. Push:
   ```bash
   git push
   ```

## Classification Heuristics

### Signs of Branch-Related Failure

- Error messages reference files in the PR diff
- Test names match changed functionality
- Compile errors in modified modules
- Lint rules failing on new code
- Type errors in changed signatures

### Signs of Flaky/Infrastructure Failure

```
# Network issues
ETIMEDOUT
ECONNRESET
DNS resolution failed
429 Too Many Requests

# Runner issues
Runner provisioning failed
No runner available
Runner disconnected

# GitHub infrastructure
GitHub API rate limit exceeded
Service unavailable
Internal server error
```

### Ambiguous Cases

If classification is unclear:
1. Read full logs carefully
2. Check if failure is deterministic (same error on retry)
3. Look for patterns in CI history
4. When in doubt, try one fix attempt before retrying

## Delegation Options

### For Simple Fixes
Handle directly with the workflow above.

### For Complex/Ongoing CI Issues
Delegate to `/babysit-pr` for continuous monitoring:
```bash
/babysit-pr owner/repo#123
```

### For Background Processing
```bash
lxa run --background --job-name "fix-ci-123" \
  --task "Fix CI failure on owner/repo#123.
  
  Failed check: <check-name>
  Error summary: <error-details>
  
  Steps:
  1. Check out PR branch
  2. Reproduce failure locally
  3. Fix the issue
  4. Commit and push
  5. Verify CI passes"
```

## Output Format

```
CI Diagnosis for owner/repo#123
===============================

Failed Checks:
  - tests (run 12345): FAILURE
  - lint (run 12346): SUCCESS
  - typecheck (run 12347): SUCCESS

Analyzing tests failure...

Classification: BRANCH-RELATED
Reason: Test failure in src/feature.py which was modified in this PR

Error Details:
  File: tests/test_feature.py
  Test: test_new_functionality
  Error: AssertionError: expected 42, got 41

Action: Fixing locally...

[... fix applied ...]

Committed: abc1234 "fix: correct calculation in feature.py"
Pushed to PR branch.

Waiting for CI... (use `gh pr checks 123 --watch` to monitor)
```

## Error Handling

| Situation | Response |
|-----------|----------|
| Can't determine failure type | Report logs, ask for guidance |
| Multiple unrelated failures | Address one at a time |
| Flaky retry limit reached | Escalate to human |
| Can't reproduce locally | Fix based on CI logs |
| Conflict resolution unclear | Ask for guidance on resolution |

## Related Skills

- `/shepherd` - Get initial status
- `/shepherd-advance` - Auto-determine action
- `/babysit-pr` - Intensive monitoring for complex CI issues
