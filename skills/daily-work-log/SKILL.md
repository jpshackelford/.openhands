---
name: daily-work-log
description: Analyze OpenHands conversations from the day and create a Notion work log page with completed work, pending items, and preserved sandbox files.
triggers:
  - work log
  - daily log
  - conversation summary
  - what did I do today
  - analyze conversations
  - notion work log
  - end of day summary
---

# Daily Work Log Analysis

This skill helps you analyze your OpenHands conversations from the day and create a structured Notion work log page.

## Quick Start

```
Analyze my OpenHands conversations from today and create a private Notion work log page.
```

## Process Overview

1. **Retrieve conversations** from today via OpenHands API
2. **Extract intent** from first human message of each
3. **Present summary table** for user review
4. **Ask verification questions** about completion status
5. **Create Notion page** with categorized work items
6. **Retrieve sandbox files** if needed and create subpages

---

## Step 1: List Today's Conversations

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?limit=50&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Accept: application/json"
```

Filter results for today's date by checking `created_at` timestamps.

## Step 2: Extract Intent from Each Conversation

**Important**: A single message rarely tells the full story. Retrieve ALL human messages to understand the user's evolving goal:

```bash
curl -s "https://app.all-hands.dev/api/v1/conversations/{conversation_id}/events?kind__eq=HUMAN_MESSAGE&sort_order=TIMESTAMP_ASC" \
  -H "Authorization: Bearer $OH_API_KEY"
```

### Why All Messages Matter

- **First message** may be vague: "help me with this PR"
- **Middle messages** clarify intent: "actually focus on the test failures"
- **Later messages** reveal the real goal: "can you also update the docs?"
- **Final messages** often confirm completion or request follow-up

### Analyzing the Message Sequence

Look for patterns across the conversation:

1. **Initial request** - What did they start with?
2. **Clarifications** - What details did they add?
3. **Pivots** - Did the goal change mid-conversation?
4. **Confirmations** - What did they explicitly approve or accept?
5. **Follow-ups** - What loose ends were mentioned?

### Also Get the Finish Message

```bash
curl -s "https://app.all-hands.dev/api/v1/conversations/{conversation_id}/events?kind__eq=AGENT_FINISH&limit=1&sort_order=TIMESTAMP_DESC" \
  -H "Authorization: Bearer $OH_API_KEY"
```

The finish message often summarizes what was accomplished and what remains.

### Event Kind Filters

| Filter Value | Description |
|--------------|-------------|
| `HUMAN_MESSAGE` | User messages (get ALL of these) |
| `AGENT_FINISH` | Agent completion messages |
| `ACTION` | Agent tool calls |
| `OBSERVATION` | Tool results |

## Step 3: Identify External Actions (What Escaped the Sandbox?)

**Critical question**: The sandbox is ephemeral. What work was saved outside of it?

Scan the conversation events for actions that persisted work externally:

```bash
# Get all actions to analyze what was done
curl -s "https://app.all-hands.dev/api/v1/conversations/{conversation_id}/events?kind__eq=ACTION&sort_order=TIMESTAMP_ASC" \
  -H "Authorization: Bearer $OH_API_KEY"
```

### External Actions to Look For

| Category | Actions | Evidence |
|----------|---------|----------|
| **Git** | `git push`, `git commit` | Branch pushed, commits made |
| **GitHub** | PR created/updated, issue created/commented | API calls to github.com |
| **Notion** | Page created/updated | `notion.post_page`, `notion.update_a_block` |
| **Slack** | Message sent | `slack_send_message` |
| **Linear** | Issue created/updated | `linear.save_issue` |
| **File uploads** | Gists, attachments | `gh gist create`, attachment APIs |

### What This Tells You

- **External actions found** → Work is preserved, can verify it exists
- **No external actions** → Work only exists in sandbox (may need retrieval)
- **Partial actions** → Some work saved, some may be lost

### Quick Analysis Script

```bash
curl -s "https://app.all-hands.dev/api/v1/conversations/{id}/events?kind__eq=ACTION" \
  -H "Authorization: Bearer $OH_API_KEY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
external_actions = []
for item in data.get('items', []):
    action = item.get('action', {})
    tool = item.get('tool_name', '')
    
    # Check for external actions
    if tool in ['terminal']:
        cmd = action.get('command', '')
        if any(x in cmd for x in ['git push', 'gh pr', 'gh issue', 'curl -X POST', 'curl -X PUT']):
            external_actions.append(f'Terminal: {cmd[:80]}...')
    elif tool in ['default_create_pr', 'default_create_mr']:
        external_actions.append(f'PR created')
    elif 'notion' in tool:
        external_actions.append(f'Notion: {tool}')
    elif 'slack' in tool:
        external_actions.append(f'Slack: {tool}')
    elif 'linear' in tool:
        external_actions.append(f'Linear: {tool}')

if external_actions:
    print('External actions found:')
    for a in external_actions:
        print(f'  - {a}')
else:
    print('No external actions found - work may only exist in sandbox')
"
```

## Step 4: Present Summary Table

```
| # | Title | Goal | External Output | Status |
|---|-------|------|-----------------|--------|
| 1 | PR Review | Fix test failures | PR #2334 updated | ✅ |
| 2 | Research | Compare plugins | None (file in sandbox) | 📁 |
| 3 | Slack thread | Draft GitHub issue | Issue #19 created | ✅ |
```

## Step 5: Verification Questions

For each conversation, determine:

1. **External Output**: What was saved outside the sandbox? (PR, issue, Notion page, Slack message, etc.)
2. **Sandbox Files**: Any valuable files that exist only in the sandbox?
3. **Completion**: Is the user's goal fully achieved, or is follow-up needed?

### Categories

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ **Done** | Work complete AND delivered externally | Document with links |
| 🔄 **Pending** | Started but needs follow-up | Note next steps |
| 📁 **Retrieve** | Valuable work only in sandbox | Resume sandbox, save content |
| ℹ️ **Info** | Lookup/research, no output expected | Brief note only |
| ⚠️ **Lost?** | Work done but no external save | May need to redo |

---

## Step 6: Create Notion Work Log Page

### Page Structure

```markdown
# Work Log - [Date]

Summary of OpenHands conversations and work accomplished today.

---

## ✅ Completed Work

### 1. [Task Name]
[Description of work done]

Link: [PR/Issue/Page](https://...)

Status: ✅ Complete

---

## 📋 [Special Category]
(For major collaborative work like roadmap updates)

---

## 🔄 Pending / Follow-up

1. [Task](https://conversation-link) - [what needs to happen]
2. [Task] - [next steps]

---

## ℹ️ Informational Lookups

• [Quick lookup 1]
• [Quick lookup 2]

---

*Generated: [timestamp] via OpenHands conversation analysis*
```

### Creating with Markdown

Use the Notion MCP `post_page` tool with the `markdown` field:

```json
{
  "parent": {"type": "page_id", "page_id": "[parent-id]"},
  "properties": {
    "title": {"title": [{"type": "text", "text": {"content": "Work Log YYYY-MM-DD"}}]}
  },
  "markdown": "[full markdown content]"
}
```

**The `markdown` field automatically converts:**
- Headers (##, ###)
- Tables (with | syntax)
- Code blocks
- Links `[text](url)`
- Bullet and numbered lists

### Adding Hyperlinks to Existing Blocks

Use `update_a_block` with rich_text containing links:

```json
{
  "paragraph": {
    "rich_text": [
      {"type": "text", "text": {"content": "Link: "}},
      {"type": "text", "text": {"content": "PR #123", "link": {"url": "https://github.com/..."}}}
    ]
  }
}
```

---

## Step 7: Retrieve Files from Paused Sandboxes

If a conversation has files that need to be preserved:

### Check Sandbox Status

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids={conversation_id}" \
  -H "Authorization: Bearer $OH_API_KEY"
# Look for: "sandbox_status": "PAUSED"
# Note the: "sandbox_id"
```

### Resume the Sandbox

```bash
curl -s -X POST "https://app.all-hands.dev/api/v1/sandboxes/{sandbox_id}/resume" \
  -H "Authorization: Bearer $OH_API_KEY"
```

### Wait and Get Session Details

Poll until `sandbox_status` becomes `RUNNING`:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids={conversation_id}" \
  -H "Authorization: Bearer $OH_API_KEY"
# Extract: session_api_key, conversation_url
```

### Download the File

```bash
# Extract agent_url from conversation_url (everything before /api/conversations)
curl -s "{agent_url}/api/file/download//{absolute_file_path}" \
  -H "X-Session-API-Key: {session_api_key}"
```

**Note**: Use double slash `//` before the absolute path.

### Create Notion Subpage

Use `post_page` with the file content in the `markdown` field to create a subpage under the work log.

---

## MCP Tool Approvals

These Notion operations require human approval at:
**https://openhands-context-layer.vercel.app/case-by-case-approvals**

| Tool | Purpose |
|------|---------|
| `notion.post_page` | Creating new pages |
| `notion.update_a_block` | Updating existing blocks |
| `notion.delete_a_block` | Deleting blocks |
| `notion.create_file` | File uploads |

Approval persists for the session after first grant.

---

## API Quick Reference

### Base URL
```
https://app.all-hands.dev/api/v1/
```

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/app-conversations` | GET | List conversations |
| `/app-conversations?ids=X` | GET | Get specific conversation(s) |
| `/conversations/{id}/events` | GET | Get conversation events |
| `/sandboxes/{id}/resume` | POST | Resume paused sandbox |

### Query Parameters for Events

| Parameter | Values |
|-----------|--------|
| `kind__eq` | `HUMAN_MESSAGE`, `AGENT_FINISH`, `ACTION`, `OBSERVATION` |
| `sort_order` | `TIMESTAMP_ASC`, `TIMESTAMP_DESC` |
| `limit` | Number of events (default varies) |

---

## Example Session

```
User: "List my OpenHands conversations from today"

Agent: [Presents numbered table with titles, intents, durations]

User: "Status: #1 done, #2 has a report file I need, #3 was just a lookup"

Agent: "I'll create the work log. For #2, what's the file path?"

User: "/workspace/project/report.md"

Agent: [Creates Notion page, resumes sandbox #2, retrieves file, creates subpage]

Agent: "Done! Here's your work log: [Notion link]"
```

---

## Tips

1. **Run at end of day** for complete picture
2. **Check sandbox_status** before trying to resume - may already be running
3. **Use markdown field** for Notion pages - much easier than building block arrays
4. **Link conversations** in pending items so you can resume them easily
5. **Create subpages** for long content rather than cramming into main page
