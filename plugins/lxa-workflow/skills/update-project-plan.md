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
gh issue view {number} --repo jpshackelford/lxa

# List related open issues
gh issue list --repo jpshackelford/lxa --state open --json number,title
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
gh issue comment {number} --repo jpshackelford/lxa --body "**Note from Issue #X implementation:**
- Discovered that {finding}
- This affects this issue because {reason}
- Suggested approach: {recommendation}"
```

### 4. File New Issues if Needed

If work revealed new requirements or follow-up work:

```bash
gh issue create --repo jpshackelford/lxa \
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
gh issue comment 18 --repo jpshackelford/lxa --body "**Note from Issue #15 (Add --json output):**
- The output formatting is handled in \`src/lxa/formatters.py\`
- This issue can leverage the same formatter infrastructure
- Consider using the \`--format\` flag pattern instead of separate flags"
```

### Filing a Follow-up Issue
```bash
gh issue create --repo jpshackelford/lxa \
  --title "Add --format flag for flexible output formats" \
  --body "Discovered during Issue #15 implementation.

## Context
While implementing --json output, realized we could support multiple formats
(json, csv, table) with a unified --format flag.

## Proposed Solution
Add \`--format {json|csv|table}\` flag that replaces individual format flags.

## Acceptance Criteria
- [ ] --format json produces JSON output
- [ ] --format csv produces CSV output  
- [ ] --format table produces current default output
- [ ] Default is table for backward compatibility"
```

## CLI-Specific Learnings

For lxa as a CLI tool, common learnings to capture include:

### Flag/Option Design
- Did the flag naming feel natural?
- Are there related flags that should be grouped?
- Should this be a subcommand instead of a flag?

### Output Formatting
- Is the output parseable by scripts?
- Does it work well with pipes and redirection?
- Are error messages clear and actionable?

### Performance
- Are there operations that are unexpectedly slow?
- Should there be progress indicators for long operations?
- Are there caching opportunities?

### Error Handling
- What edge cases were discovered?
- Are error messages helpful for debugging?
- Should certain errors be warnings instead?

## Important Notes

- **Keep learnings specific** - vague notes aren't helpful
- **Link to the source issue** when adding comments to other issues
- **File new issues** for substantial follow-up work rather than expanding scope
- **Acceptance criteria** in new issues should be clear and testable
- **Consider backward compatibility** when noting CLI changes
