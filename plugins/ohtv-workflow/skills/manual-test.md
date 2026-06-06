---
name: manual-test
description: Run manual blackbox tests and post structured results to PR
triggers:
  - /manual-test
  - /test-pr
---

# Manual Test

Run manual blackbox tests for a PR and post structured test results as a PR comment. This step is **required** before code review begins, and may need to be **repeated** after significant changes from review feedback.

## Usage

```
/manual-test
```

Then provide:
- **pr_number**: The PR number to test (e.g., 42)
- **is_retest** (optional): Whether this is a re-test after review changes

## Why Manual Testing?

The ohtv project requires manual testing before code review because:
1. **CLI tools need real testing** - Unit tests don't catch UX issues
2. **Reviewers need context** - The test report shows what was verified
3. **Reproducibility** - Structured reports let humans repeat the tests
4. **Quality gate** - No PR gets reviewed without documented testing

## When Testing is Required

### Initial Testing
- PR is ready for review but has no manual test results
- Even if review has already started (comments exist), testing must happen first
- CI must be green before testing

### Re-Testing (After Review Changes)
Testing must be repeated when:
- Significant code changes were made after the last test
- Review feedback caused behavioral changes (not just style/docs)
- More than 50 lines of non-test code changed since last test

Re-testing is NOT required when only:
- Test files changed
- Documentation/comments changed
- Type hints added

## Test Workflow

### 1. Set Up Test Environment

```bash
# Clone the repo if needed
gh repo clone jpshackelford/ohtv /tmp/ohtv-test 2>/dev/null || true
cd /tmp/ohtv-test

# Checkout the PR branch
gh pr checkout {pr_number}

# Install dependencies
uv sync

# Verify installation
uv run ohtv --help
```

### 1b. Sync Conversation History (If Needed)

Many ohtv commands require conversation data. Sync history before testing:

```bash
# Light sync - recent conversations only (fast, good for most tests)
uv run ohtv sync -n 20

# Medium sync - more history for commands that analyze patterns
uv run ohtv sync -n 50

# Full sync - extensive history for aggregate analysis or search tests
uv run ohtv sync -n 200

# Time-based sync - last N hours
uv run ohtv sync --since $(date -u -d '4 hours ago' +%Y-%m-%dT%H:%M:%S)
```

**Choose sync depth based on what you're testing:**
- `list`, `show`, `refs` commands → `-n 20` is usually enough
- `search`, `ask` (RAG) commands → `-n 50` or more for meaningful results
- Aggregate analysis, statistics → `-n 200` or time-based for representative data

### 2. Understand What Changed

Read the PR to understand what needs testing:

```bash
# View the PR description
gh pr view {pr_number}

# See what files changed
gh pr diff {pr_number} --name-only

# Read the diff to understand the changes
gh pr diff {pr_number}
```

Identify:
- New commands or flags to test
- Changed behavior to verify
- Edge cases mentioned in the PR description

### 3. Design Test Scenarios

Based on what changed, design test scenarios that:
- Cover the **happy path** (normal usage)
- Test **edge cases** (empty input, errors, limits)
- Verify **output formats** (table, JSON, CSV if applicable)
- Check **integration** with other commands
- **Test README examples** - Copy examples from README.md and verify they work

### 3b. Verify Documentation Accuracy

Since docs are updated BEFORE testing, verify the README is accurate:

```bash
# Find examples in README for the new feature
grep -A5 "ohtv {new_command}" README.md

# Run each example exactly as documented
# If an example fails or output differs significantly, note it in the test report
```

**Important:** If README examples don't work or are misleading, this is a test failure. Document it and the docs worker will fix it.

### 4. Execute Tests

Run each test scenario and document:
- **Command executed**
- **Expected result**
- **Actual result** (copy real output)
- **Pass/Fail status**

Example test execution:
```bash
# Test 1: Basic invocation
uv run ohtv list -A --idle
# Expected: Shows idle column with color coding
# Result: ✅ PASS - idle column shows, red < 7m, green >= 7m

# Test 2: Custom threshold
uv run ohtv list -A --idle 10
# Expected: Threshold changes to 10 minutes
# Result: ✅ PASS - colors now based on 10m threshold
```

### 5. Run Unit Tests

Always verify unit tests still pass:

```bash
uv run python -m pytest tests/ -v --tb=short
```

Document the result:
- Number of tests passed
- Any failures (should be 0)

### 6. Post Test Report to PR

Post a **structured test report** as a PR comment using the template below.

```bash
gh pr comment {pr_number} --body "$(cat <<'EOF'
## Manual Test Results for PR #{pr_number}

_This comment was created by an AI agent (OpenHands) on behalf of @jpshackelford._

### Test Setup

- Branch: `{branch_name}`
- Python: {python_version}
- Platform: {platform}
- ohtv installed via: `uv sync`

### Test Summary

| Test | Command | Status | Notes |
|------|---------|--------|-------|
| 1 | `ohtv {command}` | ✅ PASS | {notes} |
| 2 | `ohtv {command}` | ✅ PASS | {notes} |
| 3 | `ohtv {command}` | ❌ FAIL | {what went wrong} |

### Detailed Results

#### Test 1: {Test Name}

**Command:**
```bash
uv run ohtv {command}
```

**Expected:** {what should happen}

**Actual output:**
```
{paste actual output here}
```

**Result:** ✅ PASS

---

#### Test 2: {Test Name}

... (repeat for each test)

---

### Unit Tests

```
uv run python -m pytest tests/ -v --tb=short
```

**Result:** {N} tests passed ✅

---

**Summary:** All tests pass / {N} tests pass, {M} fail

EOF
)"
```

## Test Report Template

The test report MUST include these sections:

1. **Header** - "Manual Test Results for PR #N"
2. **Attribution** - Note this was created by AI on behalf of user
3. **Test Setup** - Environment details
4. **Test Summary Table** - Quick overview with Pass/Fail
5. **Detailed Results** - Each test with command, expected, actual, result
6. **Unit Tests** - pytest output summary
7. **Overall Summary** - Final verdict

## Example: Good Test Report

Here's an example from a real ohtv PR:

```markdown
## Manual Test Results for PR #40

_This comment was created by an AI agent (OpenHands) on behalf of @jpshackelford._

### Test Setup

Created 3 test conversations with varying idle times and refs:
- **Conversation 1**: 2 min idle (active - should show **red**)
- **Conversation 2**: 15 min idle (quiet - should show **green**)
- **Conversation 3**: 45 min idle with PR/issue refs (gym #3012, gym #50)

### Test Results ✅

| Test | Command | Status | Notes |
|------|---------|--------|-------|
| 1 | `ohtv list -A` | ✅ PASS | Default list with refs showing |
| 2 | `ohtv list -A --idle` | ✅ PASS | Idle column replaces Duration |
| 3 | `ohtv list -A --idle 10` | ✅ PASS | Custom 10m threshold works |
| 4 | `ohtv list -A --no-refs` | ✅ PASS | Refs hidden when flag used |

### Color Verification

Verified ANSI color codes are correct:
- `[31m` (red) for idle < threshold
- `[32m` (green) for idle >= threshold

### Unit Tests

All **835 unit tests pass** ✅

---

**Summary**: All functionality works as documented in the PR description.
```

## What Counts as a Valid Manual Test

Manual testing means **blackbox testing through the CLI** - treating the tool as users would. You MUST test through the command-line interface, not by importing Python functions.

### ✅ VALID - Tests user-facing CLI interface:
```bash
# These are valid tests - they use the CLI like a real user
uv run ohtv list -A --label "key=value"
uv run ohtv show abc1234 --summary
uv run ohtv gen objs -n 10 -F json
uv run ohtv search "error handling" --limit 5
```

### ❌ INVALID - Tests internal implementation:
```python
# DO NOT DO THIS - testing internal functions is NOT manual testing
from ohtv.cli import _filter_by_label
result = _filter_by_label(conversations, "key=value")

# DO NOT DO THIS - calling functions directly bypasses the user interface
from ohtv.transcript import extract_action_summary
extract_action_summary(event_with_summary, include_command=True)

# DO NOT DO THIS - Python interpreter tests are NOT manual tests
python -c "from ohtv.store import ConversationStore; store.list_by_label('foo=bar')"
```

**Rule of thumb:** If a user can't type it in their terminal, it's not a valid manual test. Internal function testing belongs in pytest unit tests, not manual test reports.

### Why This Matters

1. **Unit tests already cover internals** - pytest tests the functions; manual tests verify the user experience
2. **CLI is the contract** - Users interact via CLI; we need to verify that interface works
3. **Integration matters** - CLI testing catches argument parsing, output formatting, and error handling that function-level tests miss
4. **Reproducibility** - Other humans can copy/paste CLI commands to verify; they can't easily reproduce Python interpreter sessions

## What Makes a Good Test Report

✅ **DO:**
- Test ONLY through CLI commands (`uv run ohtv ...`)
- Test real functionality, not just "it runs"
- Include actual command output (not paraphrased)
- Document edge cases tested
- Note any bugs found during testing
- Include environment details for reproducibility
- Run and report unit test results

❌ **DON'T:**
- **Test internal functions via Python interpreter** (e.g., `extract_action_summary(event)`)
- **Use `python -c "from X import Y; Y(...)"` patterns** - that's what unit tests are for
- **Import and call Python functions directly** - test ONLY through CLI commands
- **Bypass the CLI** to test "faster" - if users can't do it, don't test it that way
- Skip error case testing
- Fabricate output that wasn't actually run
- Post vague "it works" statements
- Forget to test all new flags/options
- Skip unit tests

## Re-Test Report Format

When re-testing after review changes, use this modified format:

```markdown
## Re-Test Results for PR #42 (Round 2)

_This comment was created by an AI agent (OpenHands) on behalf of @jpshackelford._

### Context

Re-testing after review round 2. Changes since last test:
- Fixed timezone handling in idle calculation
- Added defensive check for naive datetimes

### What Was Re-Tested

| Area | Previous Status | Current Status | Notes |
|------|-----------------|----------------|-------|
| Idle calculation | ✅ PASS | ✅ PASS | Still works |
| Timezone edge case | ⚠️ Not tested | ✅ PASS | New test added |
| Color thresholds | ✅ PASS | ✅ PASS | No regression |

### New/Changed Tests

#### Test: Naive datetime handling
**Command:** `uv run ohtv list -A --idle`

**Purpose:** Verify no crash when conversation has naive datetime

**Result:** ✅ PASS - gracefully handles naive timestamps

### Regression Check

All 12 tests from initial test run still pass ✅

### Unit Tests

All **837 unit tests pass** ✅ (2 new tests added)

---

**Summary:** All changes verified. No regressions detected.
```

### Key Differences from Initial Test Report

1. **Header indicates round** - "Re-Test Results (Round N)"
2. **Context section** - What changed since last test
3. **Comparison table** - Previous vs current status
4. **Regression check** - Explicitly note previous tests still pass
5. **Focus on changes** - Don't repeat all original tests, focus on what changed

## After Posting

Once the test report is posted:
1. Verify the comment appears on the PR
2. Log success and exit
3. The orchestrator will advance to code review phase (or merge if approved)

## Error Handling

If testing reveals bugs:
1. Document the failure in the test report
2. Post the report anyway (with failures noted)
3. Exit - implementation worker will be spawned to fix

If environment setup fails:
1. Report the specific error
2. Exit - don't post incomplete test reports
