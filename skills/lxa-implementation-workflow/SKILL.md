---
name: lxa-implementation-workflow
description: Design document-driven implementation using LXA's orchestrator and task agents. Solves the context continuation problem for long-horizon development tasks.
triggers:
- lxa implement
- design driven
- milestone implementation
- long horizon
- autonomous implementation
---

# LXA Implementation Workflow

This skill uses LXA's design document-driven approach to implement complex features autonomously while maintaining context across agent boundaries.

## The Continuation Problem

Traditional chat-based development loses context when:
- Context window fills up
- Session is interrupted
- Agent needs to be restarted

LXA solves this by:
1. Scoping each agent to a **single, well-defined task**
2. Using **design documents** as persistent context
3. Maintaining a **journal** of learnings across task boundaries

## Workflow Overview

```
┌─────────────────┐     ┌────────────────┐     ┌─────────────────┐
│   Design        │ ──► │ Implementation │ ──► │ Reconciliation  │
│   Phase         │     │     Phase      │     │     Phase       │
└─────────────────┘     └────────────────┘     └─────────────────┘
    Human creates        Agent-driven          Updates design doc
    design doc           milestone work        with code refs
```

## Prerequisites

- LXA installed: `pip install lxa` or from [jpshackelford/lxa](https://github.com/jpshackelford/lxa)
- `LLM_API_KEY` or `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- `GITHUB_TOKEN` for PR creation
- Git repository with clean working tree

## Quick Start

### 1. Create a Design Document

Create `.pr/design.md` (or use `doc/design/feature-name.md` for persistent designs):

```markdown
# Feature Name

## 1. Problem Statement
What problem are we solving?

## 2. Proposed Solution
High-level approach.

## 3. Technical Design
### 3.1 Component A
Details...

## 4. Implementation Plan

### 4.1 Foundation (M1)
**Goal**: Basic infrastructure.

- [ ] src/module.py - Create base classes
- [ ] tests/test_module.py - Unit tests

### 4.2 Core Logic (M2)
**Goal**: Main functionality.

- [ ] src/core.py - Implement business logic
- [ ] tests/test_core.py - Integration tests
```

### 2. Run Implementation

```bash
# Single milestone iteration
lxa implement

# Continuous autonomous execution (Ralph Loop)
lxa implement --loop

# With automatic PR refinement
lxa implement --loop --refine

# With auto-merge when done
lxa implement --loop --refine --auto-merge
```

### 3. Monitor Progress

- Watch the terminal for real-time progress
- Check the draft PR on GitHub
- Review commits as they're pushed

## Design Document Structure

### Required Sections

| Section | Purpose |
|---------|---------|
| **Problem Statement** | What problem are we solving |
| **Proposed Solution** | High-level approach |
| **Technical Design** | Architecture details |
| **Implementation Plan** | Milestones with task checklists |

### Milestone Format

```markdown
### 5.1 Component Name (M1)

**Goal**: What this milestone achieves.

**Demo**: How to verify it works.

#### Checklist

- [ ] path/to/file.py - Description of what to implement
- [ ] tests/test_file.py - Tests for the implementation
```

Key elements:
- `(M1)`, `(M2)`, etc. - Milestone numbers for tracking
- `**Goal**:` - Clear success criteria
- Checkbox format: `- [ ]` unchecked, `- [x]` checked

## How It Works

### Orchestrator Agent

The orchestrator is a thin, long-lived agent that:

1. Reads the design document
2. Finds the current milestone
3. Creates a feature branch
4. Delegates tasks to task agents
5. Commits and pushes changes
6. Creates/updates a draft PR
7. Outputs `ALL_MILESTONES_COMPLETE` when done

### Task Agents

Short-lived sub-agents that:

1. Read the design document for context
2. Read the journal for prior learnings
3. Implement the assigned task
4. Write tests (TDD encouraged)
5. Run lints and fix issues
6. Commit the work
7. Write a journal entry

### Journal as Memory

The journal (`.pr/journal.md`) captures:

```markdown
## Task Name (2024-01-15 10:30)

### Files Read
- src/config.py - Learned about configuration patterns

### Files Modified
- src/new_feature.py - Created new module

### Lessons Learned
- Pydantic v2 uses model_validate() not parse_obj()
- Must import from openhands.sdk, not openhands
```

**Important**: Lessons learned are for **gotchas and pitfalls**, NOT accomplishments.

## Comparison with sub-agent-delegation

### Traditional Delegation (neubig/workflow)

```python
# Spawn sub-agents
{"command": "spawn", "ids": ["task1", "task2"]}

# Delegate tasks
{"command": "delegate", "tasks": {
    "task1": "Implement feature X",
    "task2": "Write tests for X"
}}
```

**Pros**: Parallel execution
**Cons**: No persistent context, no progress tracking

### LXA Implementation

```bash
lxa implement .pr/design.md --loop
```

**Pros**:
- Design document provides context
- Journal preserves learnings
- Checklist tracks progress
- Fresh context per task (no rot)
- Automatic PR management

**Cons**:
- Sequential task execution
- Requires design doc upfront

## Advanced Options

### Design Path Configuration

```bash
# Default: .pr/design.md (transient, deleted after merge)
lxa implement

# Persistent design in doc/design/
lxa implement --keep-design

# Custom path
lxa implement --design-path doc/design/my-feature.md
```

### Ralph Loop Options

```bash
# Set max iterations (default: 20)
lxa implement --loop --max-iterations 50

# Enable refinement after implementation
lxa implement --loop --refine

# Configure quality bar for auto-merge
lxa implement --loop --refine --allow-merge good_taste
```

### Integrated Refinement

When `--refine` is enabled:

1. Implementation completes all milestones
2. Self-review phase runs (agent reviews its own code)
3. PR is marked ready for review
4. After human review, respond phase addresses comments
5. If `--auto-merge`: squash merge when approved

## Reconciliation (Post-Merge)

After PR merge, update the design doc to reference actual code:

```bash
lxa reconcile .pr/design.md --dry-run  # Preview
lxa reconcile .pr/design.md            # Apply
```

**Before:**
```markdown
### 4.4 ImplementationChecklistTool

Parses the design document to extract implementation plan state.
The tool uses regex to find markdown checkboxes...
[detailed implementation description]
```

**After:**
```markdown
### 4.4 ImplementationChecklistTool

See `src/tools/checklist.py::ImplementationChecklistTool`

Parses the design document to extract implementation plan state.
```

## When to Use This vs. Simple Delegation

| Use LXA Implementation | Use Simple Delegation |
|----------------------|----------------------|
| Multi-day features | Quick tasks (<30 min) |
| Complex architecture | Independent subtasks |
| Need progress tracking | Need parallel execution |
| Context preservation critical | Context fits in one session |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Design document not found" | Create `.pr/design.md` or use `--design-path` |
| "Pre-flight check failed" | Ensure clean git working tree |
| Agent stuck | Check journal for recent context |
| Checklist not updating | Verify milestone format `(M1)` |

## Example: Full Implementation

```bash
# 1. Create design document
cat > .pr/design.md << 'EOF'
# Add User Authentication

## 1. Problem Statement
Need secure user login for the app.

## 2. Proposed Solution
JWT-based authentication with refresh tokens.

## 3. Implementation Plan

### 3.1 Token Generation (M1)
**Goal**: JWT creation and validation.

- [ ] src/auth/tokens.py - Token generation
- [ ] tests/auth/test_tokens.py - Token tests

### 3.2 Login Endpoint (M2)
**Goal**: REST API for login.

- [ ] src/auth/routes.py - Login/logout routes
- [ ] tests/auth/test_routes.py - API tests
EOF

# 2. Run implementation
lxa implement --loop --refine

# 3. Monitor the PR on GitHub
# 4. Review and approve
# 5. Merge or auto-merge
```

## References

- [LXA Implementation Agent Design](https://github.com/jpshackelford/lxa/blob/main/doc/design/implementation-agent-design.md)
- [sub-agent-delegation skill](https://github.com/neubig/workflow/blob/main/skills/sub-agent-delegation/SKILL.md)
- [Artifact Path Configuration](https://github.com/jpshackelford/lxa/blob/main/doc/reference/artifact-path-configuration.md)
