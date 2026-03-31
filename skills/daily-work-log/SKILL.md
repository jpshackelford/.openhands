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

Get the first human message to understand what the user wanted:

```bash
curl -s "https://app.all-hands.dev/api/v1/conversations/{conversation_id}/events?kind__eq=HUMAN_MESSAGE&limit=1&sort_order=TIMESTAMP_ASC" \
  -H "Authorization: Bearer $OH_API_KEY"
```

Get the finish message (if any) to see the outcome:

```bash
curl -s "https://app.all-hands.dev/api/v1/conversations/{conversation_id}/events?kind__eq=AGENT_FINISH&limit=1&sort_order=TIMESTAMP_DESC" \
  -H "Authorization: Bearer $OH_API_KEY"
```

### Event Kind Filters

| Filter Value | Description |
|--------------|-------------|
| `HUMAN_MESSAGE` | User messages |
| `AGENT_FINISH` | Agent completion messages |
| `ACTION` | Agent tool calls |
| `OBSERVATION` | Tool results |

## Step 3: Present Summary Table

```
| # | Title | Intent Summary | Duration | Status |
|---|-------|----------------|----------|--------|
| 1 | PR Review | Review PR #2334 comments | 45 min | ? |
| 2 | Research | Compare OpenAI vs OpenHands plugins | 30 min | ? |
```

## Step 4: Verification Questions

For each conversation, determine:

1. **Delivery**: Was work delivered outside sandbox? (GitHub PR, Notion page, Slack message, etc.)
2. **Status**: Complete, pending follow-up, or informational only?
3. **Files**: Any sandbox files that should be preserved?

Categories:
- ✅ **Done** - Work complete and delivered
- 🔄 **Pending** - Needs follow-up action
- ℹ️ **Informational** - Lookup/research, no action needed
- 📁 **Has Files** - Sandbox contains files to preserve

---

## Step 5: Create Notion Work Log Page

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

## Step 6: Retrieve Files from Paused Sandboxes

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
