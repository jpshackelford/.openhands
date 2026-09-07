# OpenHands Skills Collection

This repository contains custom OpenHands skills for development workflows.

## Skills

### LXA Integration Skills

These skills integrate [LXA (Long Execution Agent)](https://github.com/jpshackelford/lxa) tools for enhanced autonomous development workflows.

| Skill | Description | Triggers |
|-------|-------------|----------|
| [lxa-board-workflow](./skills/lxa-board-workflow/SKILL.md) | Daily workflow using LXA board management for unified issue/PR tracking | `lxa board`, `board workflow`, `what needs attention` |
| [lxa-implementation-workflow](./skills/lxa-implementation-workflow/SKILL.md) | Design document-driven implementation with orchestrator/task agents | `lxa implement`, `design driven`, `milestone implementation` |
| [lxa-pr-refinement](./skills/lxa-pr-refinement/SKILL.md) | Two-phase PR refinement (self-review + respond to reviews) | `lxa refine`, `pr refinement`, `address reviews` |

### Development Workflow Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [design-doc](./skills/design-doc/SKILL.md) | Create structured design documents | `design doc`, `design document` |
| [github-pr-inline-comments](./skills/github-pr-inline-comments/SKILL.md) | Post inline PR comments via GitHub API | `inline comment`, `pr comment` |
| [linear-board](./skills/linear-board/SKILL.md) | Interact with Linear project management | `linear`, `linear board` |

### OpenHands Platform Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [openhands-cloud-api](./skills/openhands-cloud-api/SKILL.md) | Use OpenHands Cloud API | `cloud api`, `openhands api` |
| [openhands-staging-deploy](./skills/openhands-staging-deploy/SKILL.md) | Deploy to OpenHands staging | `staging deploy` |
| [openhands-workspace-setup](./skills/openhands-workspace-setup/SKILL.md) | Set up OpenHands workspace | `workspace setup` |

### Utility Skills

| Skill | Description | Triggers |
|-------|-------------|----------|
| [terminal-recording](./skills/terminal-recording/SKILL.md) | Record terminal sessions | `record terminal`, `asciinema` |

## LXA Integration Overview

The LXA skills provide enhanced workflows compared to traditional approaches:

### Board Management

**Before (manual Linear + GitHub scanning):**
```bash
# Fetch Linear tickets
curl -s -X POST https://api.linear.app/graphql ...

# Check GitHub PRs separately
gh pr list --author @me
```

**After (unified board):**
```bash
lxa board status --attention
```

### Implementation Workflow

**Before (context loss across sessions):**
- Agent forgets architectural decisions
- Manual task tracking
- Context rot in long sessions

**After (design-driven):**
```bash
lxa implement --loop --refine
```
- Design document provides persistent context
- Journal captures learnings across tasks
- Automatic progress tracking via checklists

### PR Refinement

**Before (manual review iteration):**
```bash
# Check threads, fix each, reply, resolve, wait for CI...
# Repeat many times
```

**After (automated phases):**
```bash
lxa refine https://github.com/owner/repo/pull/42 --auto-merge
```

## Prerequisites

For LXA skills:
- LXA installed: `pip install lxa` or from [jpshackelford/lxa](https://github.com/jpshackelford/lxa)
- `GITHUB_TOKEN` with appropriate scopes
- `LLM_API_KEY` or equivalent for implementation/refinement

## Templates

| Template | Description |
|----------|-------------|
| [design-document-template.md](./templates/design-document-template.md) | Standard design document structure |

## Usage

Configure your OpenHands `marketplace_path` to point to this repository.

## References

- [LXA Documentation](https://github.com/jpshackelford/lxa)
- [neubig/workflow](https://github.com/neubig/workflow) - Original workflow patterns
- [OpenHands Documentation](https://docs.openhands.dev/)
