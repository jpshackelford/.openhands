---
name: cli-testing
description: This skill should be used when manually testing CLI tools, documenting test results for pull requests, verifying command-line interface behavior, or reporting CLI test outcomes. Use this skill when asked to "test the CLI", "run manual tests", "verify CLI behavior", "document test results", or "report testing outcomes in a PR".
triggers:
- manual testing
- manual test
- cli testing
- test cli
- verify cli
- test results
- testing report
- document tests
---

# Manual CLI Testing and PR Reporting

Patterns and best practices for manually testing command-line interface tools and reporting results in pull requests.

## Quick Start

### Run a CLI Test

```bash
# Test help command
mytool --help
echo "Exit code: $?"

# Test with specific arguments
mytool process --input file.txt 2>&1
echo "Exit code: $?"

# Test error handling (nonexistent file)
mytool process --input /nonexistent/file.txt 2>&1
echo "Exit code: $?"
```

### Document Results

Format test results for PR comments using this pattern:

```markdown
## Manual Testing Results

| Test | Command | Expected | Actual | Status |
|------|---------|----------|--------|--------|
| Help | `mytool --help` | Exit 0, shows usage | Exit 0, shows usage | ✅ |
| Basic | `mytool process file.txt` | Processes file | Processed | ✅ |
| Error | `mytool process /missing` | Exit 1, error msg | Exit 1, error msg | ✅ |

**Summary**: 3/3 tests passed
```

## CLI Testing Philosophy

### Test Like a User

The most valuable CLI tests invoke the tool exactly as a user would:

1. **Use the actual command** - Don't test internal functions; test the CLI entry point
2. **Capture real output** - Check stdout, stderr, and exit codes
3. **Test in isolation** - Use temp directories to avoid side effects
4. **Include edge cases** - Invalid inputs, missing files, permission errors

### What to Test

| Category | Examples |
|----------|----------|
| **Help/Usage** | `--help`, `--version`, no arguments |
| **Happy Path** | Standard command with valid inputs |
| **Error Handling** | Missing files, invalid arguments, permission denied |
| **Edge Cases** | Empty files, very long paths, special characters |
| **Options** | Flag combinations, conflicting options |

## Testing Patterns

### Pattern 1: Basic Command Testing

```bash
# Setup
WORKDIR=$(mktemp -d)
cd "$WORKDIR"
echo "test content" > input.txt

# Test
OUTPUT=$(mytool process input.txt 2>&1)
EXIT_CODE=$?

# Verify
if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT" | grep -q "success"; then
    echo "✅ PASS: Basic processing works"
else
    echo "❌ FAIL: Expected success, got exit $EXIT_CODE"
    echo "Output: $OUTPUT"
fi

# Cleanup
rm -rf "$WORKDIR"
```

### Pattern 2: Error Case Testing

```bash
# Test nonexistent file
OUTPUT=$(mytool process /does/not/exist 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] && echo "$OUTPUT" | grep -qi "error\|not found"; then
    echo "✅ PASS: Correct error handling for missing file"
else
    echo "❌ FAIL: Expected error, got exit $EXIT_CODE"
fi
```

### Pattern 3: Help Command Testing

```bash
# Test --help returns 0 and shows usage
OUTPUT=$(mytool --help 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ] && echo "$OUTPUT" | grep -qi "usage"; then
    echo "✅ PASS: Help command works"
else
    echo "❌ FAIL: Help command failed"
fi
```

### Pattern 4: Subprocess Testing (pytest)

For automated testing, invoke CLI via subprocess for true end-to-end testing:

```python
import subprocess
from pathlib import Path

def test_cli_help():
    """CLI --help should return exit code 0."""
    result = subprocess.run(
        ["mytool", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()

def test_cli_processes_file(tmp_path: Path):
    """CLI should process a valid input file."""
    # Setup
    input_file = tmp_path / "input.txt"
    input_file.write_text("test content")
    
    # Execute
    result = subprocess.run(
        ["mytool", "process", str(input_file)],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    
    # Verify
    assert result.returncode == 0
    assert "processed" in result.stdout.lower()

def test_cli_error_missing_file():
    """CLI should fail gracefully for missing files."""
    result = subprocess.run(
        ["mytool", "process", "/nonexistent/file.txt"],
        capture_output=True,
        text=True
    )
    assert result.returncode != 0
    assert "error" in result.stderr.lower() or "not found" in result.stderr.lower()
```

## PR Reporting Format

### Test Summary Comment

Post test results as a PR comment using this format:

```markdown
## 🧪 Manual Testing Results

### Test Environment
- OS: macOS 15.x / Ubuntu 22.04
- Tool version: mytool v1.2.3
- Python: 3.11

### Tests Performed

| # | Test Case | Command | Expected | Actual | Status |
|---|-----------|---------|----------|--------|--------|
| 1 | Help displays | `mytool --help` | Exit 0, usage text | Exit 0, usage shown | ✅ |
| 2 | Version shows | `mytool --version` | Exit 0, version | Exit 0, "v1.2.3" | ✅ |
| 3 | Basic processing | `mytool process input.txt` | Processes file | File processed | ✅ |
| 4 | Missing file error | `mytool process /missing` | Exit 1, error | Exit 1, "not found" | ✅ |
| 5 | Empty input | `mytool process empty.txt` | Handles gracefully | Warning shown | ✅ |

### Detailed Results

<details>
<summary>Test 1: Help displays</summary>

```
$ mytool --help
Usage: mytool [OPTIONS] COMMAND [ARGS]...

Options:
  --help     Show this message and exit.
  --version  Show the version and exit.

Commands:
  process    Process input files
  validate   Validate configuration

Exit code: 0
```
</details>

<details>
<summary>Test 4: Missing file error</summary>

```
$ mytool process /missing/file.txt
Error: File not found: /missing/file.txt

Exit code: 1
```
</details>

### Summary

**Result**: ✅ All 5 tests passed

---
*Tests performed manually by AI assistant (OpenHands) on behalf of the user.*
```

### Issue/Bug Testing Report

When testing a specific bug fix:

```markdown
## 🐛 Bug Fix Verification: Issue #123

### Before (on main branch)
```
$ mytool process --edge-case
Traceback (most recent call last):
  File "...", line 42, in process
    raise ValueError("Unhandled edge case")
ValueError: Unhandled edge case
Exit code: 1
```

### After (on this PR)
```
$ mytool process --edge-case
Edge case handled successfully
Exit code: 0
```

### Additional Tests
| Related Scenario | Result |
|-----------------|--------|
| Normal case still works | ✅ |
| Other edge cases unaffected | ✅ |
| Regression tests pass | ✅ |

**Verdict**: ✅ Bug fix verified
```

### Feature Testing Report

When testing a new feature:

```markdown
## ✨ Feature Testing: New `--verbose` Flag

### Test Cases

| Test | Command | Expected Behavior | Actual | Status |
|------|---------|-------------------|--------|--------|
| Default (no flag) | `mytool process` | Minimal output | ✅ Minimal output | ✅ |
| With --verbose | `mytool process --verbose` | Detailed output | ✅ Shows details | ✅ |
| Short form -v | `mytool process -v` | Same as --verbose | ✅ Same behavior | ✅ |
| Combined with others | `mytool process -v --dry-run` | Both work | ✅ Compatible | ✅ |

### Example Output with --verbose

```
$ mytool process input.txt --verbose
[INFO] Starting processing...
[DEBUG] Reading file: input.txt (42 bytes)
[DEBUG] Parsing content...
[INFO] Found 3 items
[DEBUG] Processing item 1/3
[DEBUG] Processing item 2/3
[DEBUG] Processing item 3/3
[INFO] Processing complete
Exit code: 0
```

**Summary**: Feature works as designed
```

## Best Practices

### ✅ Do

- **Test the CLI entry point**, not internal functions
- **Capture both stdout and stderr** with `2>&1`
- **Check exit codes** - they're part of the contract
- **Use temp directories** to avoid polluting the workspace
- **Document the environment** (OS, versions)
- **Include actual command output** in reports
- **Test both success and failure paths**

### ❌ Don't

- Don't skip error cases - they're often where bugs hide
- Don't assume exit code 0 means success - verify output too
- Don't test in production directories
- Don't rely solely on exit codes - check actual output
- Don't forget to clean up temp files
- Don't make reports vague - include exact commands and output

## Common Test Scenarios

### Testing Help Output

```bash
# Verify help text contains expected sections
mytool --help | grep -q "Usage:" && echo "✅ Has usage" || echo "❌ Missing usage"
mytool --help | grep -q "Options:" && echo "✅ Has options" || echo "❌ Missing options"
mytool --help | grep -q "Commands:" && echo "✅ Has commands" || echo "❌ Missing commands"
```

### Testing Exit Codes

```bash
# Document expected exit codes
# 0 = success
# 1 = general error
# 2 = invalid arguments

mytool process valid.txt
[ $? -eq 0 ] && echo "✅ Success returns 0"

mytool process /missing
[ $? -eq 1 ] && echo "✅ Missing file returns 1"

mytool --invalid-flag
[ $? -eq 2 ] && echo "✅ Invalid arg returns 2"
```

### Testing Stdin/Stdout Piping

```bash
# Test piped input
echo "input data" | mytool process -
[ $? -eq 0 ] && echo "✅ Accepts stdin"

# Test piped output
OUTPUT=$(echo "input" | mytool process - | cat)
[ -n "$OUTPUT" ] && echo "✅ Produces stdout"
```

### Testing Interactive Features

```bash
# Test with expect for interactive prompts (if needed)
expect << 'EOF'
spawn mytool configure
expect "Enter name:"
send "testuser\r"
expect "Save? (y/n)"
send "y\r"
expect eof
EOF
```

## Reporting Checklist

Before posting test results to a PR:

- [ ] All tests run in a clean environment
- [ ] Both success and failure cases tested
- [ ] Exit codes verified
- [ ] Actual output captured and included
- [ ] Test environment documented
- [ ] Edge cases considered
- [ ] Summary clearly states pass/fail count
- [ ] Format is consistent and readable

## Additional Resources

- [GNU Coding Standards: Exit Status](https://www.gnu.org/software/libc/manual/html_node/Exit-Status.html)
- [POSIX Exit Codes](https://pubs.opengroup.org/onlinepubs/9699919799/)
- [CLI Testing with pytest](https://docs.pytest.org/en/stable/)
