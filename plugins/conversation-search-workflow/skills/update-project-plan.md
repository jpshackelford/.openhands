# Update Project Plan

Reflect on work done and update project documentation with learnings. This skill is used at key checkpoints:
- After implementing a feature (before moving PR to ready)
- After addressing review feedback (if learnings impact the plan)
- After merging (to mark complete and identify next work)

## Usage

```
/update-plan
```

or

```
/reflect
```

## When to Use

### After Implementation (Required)
Before moving a PR from draft to ready:
1. What did you learn while implementing?
2. Does this change what the next step should be?
3. Are there insights that affect later phases of the plan?
4. Mark the current item as in-progress or complete

### After Review Round (If Applicable)
If review feedback revealed something important:
1. Did the reviewer point out a fundamental issue?
2. Does this change the architectural approach?
3. Should the plan be updated to reflect new understanding?

### After Merge (Required)
When a PR is merged:
1. Mark the work item as complete
2. Note the PR number for reference
3. Identify the next work item
4. Capture any learnings for future work

## How to Update

### 1. Read the Current Plan

The plan typically lives in `AGENTS.md` or a design doc. Read it to understand:
- What's the overall structure?
- What items are marked complete?
- What's the current item being worked on?
- What are the upcoming items?

### 2. Reflect on Learnings

Think about:
- What worked well?
- What was harder than expected?
- What would you do differently?
- What does the next person need to know?

### 3. Update the Document

Make updates that are:
- **Specific**: Not "learned a lot" but "discovered the chunking strategy needs to account for code blocks"
- **Actionable**: If it affects future work, make that clear
- **Concise**: Capture the essence, not a novel

### 4. Commit the Changes

```bash
git add AGENTS.md  # or the relevant doc
git commit -m "docs: update plan after implementing {feature}

- Mark {item} as complete
- Add learnings about {topic}
- Clarify next steps for {next item}"
git push
```

## Example Updates

### Marking Progress
```markdown
### Phase 2: Ingestion Pipeline
- [x] Minio client wrapper
- [x] Event parser (read from Minio)
- [ ] Text builder (chunking, contextual enrichment)  ← IN PROGRESS
- [ ] Embedding generator (LiteLLM integration)
```

### Adding Learnings
```markdown
### Learnings

**Event Parser (PR #42)**
- Events are stored as gzipped JSON, need to decompress before parsing
- Some events have nested structures up to 5 levels deep
- Consider adding a max-depth parameter to avoid memory issues with malformed events
```

### Clarifying Next Steps
```markdown
### Phase 2: Ingestion Pipeline
...
- [ ] Text builder (chunking, contextual enrichment)
  - Note: Based on event parser work, need to handle code blocks specially
  - Code blocks should not be split mid-block
  - Consider markdown-aware chunking strategy
```

## Commit Message Format

Use conventional commits:
- `docs: update plan after implementing {feature}`
- `docs: mark {phase} complete, add learnings`
- `docs: clarify next steps for {feature}`

## Important Notes

- **Always commit plan updates** before moving to the next phase
- **Be specific** about learnings - vague notes aren't helpful
- **Update next steps** if your work revealed something about them
- **Keep it concise** - this is documentation, not a journal
