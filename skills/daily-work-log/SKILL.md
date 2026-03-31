---
name: daily-work-log
description: Analyze OpenHands conversations, Slack messages, and GitHub activity from the day to create a structured Notion work log page with standup items, completed work, work in process, and categorized follow-up actions.
triggers:
  - work log
  - daily log
  - conversation summary
  - what did I do today
  - analyze conversations
  - notion work log
  - end of day summary
  - what did I work on
---

# Daily Work Log Analysis

This skill helps you analyze your day's work across multiple sources (Slack, GitHub, OpenHands conversations) and create a structured Notion work log page.

## Quick Start

```
Analyze my work from today and create a Notion work log page.
```

## Data Sources

The skill gathers information from multiple sources to build a complete picture:

| Source | What It Provides |
|--------|------------------|
| **Slack** | Standup posts, discussions, commitments made, help requested |
| **GitHub** | PRs/issues touched, reviews done, comments made |
| **OpenHands** | Detailed work done, files created, external actions taken |
| **Calendar/Meetings** | Context for discussions (user provides) |

## Process Overview

1. **Determine timezone and target date**
2. **Gather Slack activity** - Standup posts, messages sent, commitments made
3. **Gather GitHub activity** - PRs and issues touched (external verification)
4. **Retrieve OpenHands conversations** from the day
5. **Extract intent** from human messages in each conversation
6. **Cross-reference** all sources to build complete picture
7. **Present summary** for user review and categorization
8. **Create Notion page** with structured sections
9. **Retrieve sandbox files** if needed and create subpages

---

## Step 0: Determine Timezone and Target Date

Ask the user for their timezone. For US timezones:
- **Eastern (ET)**: UTC-5 (EST) or UTC-4 (EDT)
- **Central (CT)**: UTC-6 (CST) or UTC-5 (CDT)
- **Mountain (MT)**: UTC-7 (MST) or UTC-6 (MDT)
- **Pacific (PT)**: UTC-8 (PST) or UTC-7 (PDT)

Use the appropriate date for "yesterday" or "today" based on their timezone.

---

## Step 1: Gather Slack Activity

**Why Slack first?** Slack messages reveal:
- What the user committed to in standup
- Discussions that provide context for work done
- Promises made ("I'll do X", "Let me check on Y")
- Help requested from others

### Search for User's Messages

Use the Slack MCP tools to search for messages sent by the user:

```
slack_search_public(
  query="from:@me",
  sort="timestamp",
  sort_dir="asc"
)
```

For a specific date range, use date modifiers:
```
query="from:@me after:2026-03-29 before:2026-03-31"
```

### What to Extract from Slack

| Type | How to Identify | Use in Work Log |
|------|-----------------|-----------------|
| **Standup posts** | Morning message with plans/commitments | → 📅 Standup Items table |
| **Status updates** | EOD messages, progress reports | → ✅ Completed Work |
| **Commitments made** | "I'll do X", "Let me handle Y" | → 🔄 Follow-up Actions |
| **Help requested** | Questions asked, assistance sought | → Note in relevant section |
| **Help provided** | Answering others' questions | → 🔧 Other Work |
| **Discussions** | Threads about technical topics | → Context for GitHub/OpenHands work |

### Identify Standup Items

Look for patterns like:
- Messages in #standup or similar channels
- Morning messages listing planned work
- Bulleted/numbered lists of tasks

Extract each item to track against actual completion.

### Identify Commitments and Follow-ups

Scan messages for language indicating commitments:
- "I'll...", "I will...", "Let me..."
- "I can help with...", "I'll take a look at..."
- "Following up on...", "Still working on..."
- Responses to requests that imply action

---

## Step 2: Gather GitHub Activity

**Why GitHub?** GitHub PRs and issues provide external verification of work done:
- Cross-reference conversation claims with actual PR/issue activity
- Identify work done outside of OpenHands (direct GitHub work)
- Get accurate links and statuses for the work log
- Spot conversations that created PRs but didn't mention them clearly

### Get GitHub Username

```bash
gh api user --jq '.login'
```

### Search for PRs Authored/Updated

```bash
gh api -X GET "search/issues" \
  -f q="author:{username} is:pr updated:{YYYY-MM-DD}" \
  --jq '.items[] | {
    repo: (.repository_url | split("/") | .[-1]),
    number: .number,
    title: .title,
    state: .state,
    url: .html_url
  }'
```

### Search for PRs Where User Was Involved

This catches PRs where you commented, reviewed, or were mentioned:

```bash
gh api -X GET "search/issues" \
  -f q="involves:{username} is:pr updated:{YYYY-MM-DD} -author:{username}" \
  --jq '.items[] | {
    repo: (.repository_url | split("/") | .[-1]),
    number: .number,
    title: .title,
    state: .state,
    url: .html_url
  }'
```

### Search for PRs You Reviewed

```bash
gh api -X GET "search/issues" \
  -f q="reviewed-by:{username} is:pr updated:{YYYY-MM-DD}" \
  --jq '.items[] | {
    repo: (.repository_url | split("/") | .[-1]),
    number: .number,
    title: .title,
    url: .html_url
  }'
```

### Search for Issues Authored/Updated

```bash
gh api -X GET "search/issues" \
  -f q="author:{username} is:issue updated:{YYYY-MM-DD}" \
  --jq '.items[] | {
    repo: (.repository_url | split("/") | .[-1]),
    number: .number,
    title: .title,
    state: .state,
    url: .html_url
  }'
```

### Search for Issues Where User Was Involved

```bash
gh api -X GET "search/issues" \
  -f q="involves:{username} is:issue updated:{YYYY-MM-DD} -author:{username}" \
  --jq '.items[] | {
    repo: (.repository_url | split("/") | .[-1]),
    number: .number,
    title: .title,
    url: .html_url
  }'
```

### Combined Quick Script

```bash
USERNAME=$(gh api user --jq '.login')
DATE="2026-03-30"  # Replace with target date

echo "=== GitHub Activity for $USERNAME on $DATE ==="
echo ""
echo "## PRs Authored/Updated"
gh api "search/issues" -f q="author:$USERNAME is:pr updated:$DATE" \
  --jq '.items[] | "- [\(.repository_url | split("/") | .[-1])] #\(.number): \(.title) (\(.state))\n  \(.html_url)"'

echo ""
echo "## PRs Involved (not author)"
gh api "search/issues" -f q="involves:$USERNAME is:pr updated:$DATE -author:$USERNAME" \
  --jq '.items[] | "- [\(.repository_url | split("/") | .[-1])] #\(.number): \(.title)\n  \(.html_url)"'

echo ""
echo "## Issues Authored/Updated"
gh api "search/issues" -f q="author:$USERNAME is:issue updated:$DATE" \
  --jq '.items[] | "- [\(.repository_url | split("/") | .[-1])] #\(.number): \(.title) (\(.state))\n  \(.html_url)"'

echo ""
echo "## Issues Involved (not author)"
gh api "search/issues" -f q="involves:$USERNAME is:issue updated:$DATE -author:$USERNAME" \
  --jq '.items[] | "- [\(.repository_url | split("/") | .[-1])] #\(.number): \(.title)\n  \(.html_url)"'
```

### GitHub Search Modifiers Reference

| Modifier | Example | Purpose |
|----------|---------|---------|
| `author:` | `author:username` | Created by user |
| `involves:` | `involves:username` | Author, commenter, reviewer, or mentioned |
| `reviewed-by:` | `reviewed-by:username` | User submitted a review |
| `commenter:` | `commenter:username` | User commented |
| `mentions:` | `mentions:username` | User was @mentioned |
| `assignee:` | `assignee:username` | Assigned to user |
| `is:pr` | `is:pr` | Pull requests only |
| `is:issue` | `is:issue` | Issues only |
| `is:open` | `is:open` | Open items only |
| `is:merged` | `is:merged` | Merged PRs only |
| `updated:` | `updated:2026-03-30` | Updated on specific date |
| `created:` | `created:>=2026-03-30` | Created on/after date |
| `repo:` | `repo:owner/name` | Specific repository |

### Present GitHub Summary

Before diving into conversations, present this to the user:

```
## GitHub Activity Summary for [Date]

### PRs
| Repo | # | Title | Status | Role |
|------|---|-------|--------|------|
| sdk | 2495 | feat(plugin): Support multiple... | open | author |
| OpenHands | 12699 | feat(frontend): Add /launch... | open | author |
| sdk | 2447 | feat(observability): custom ports | open | reviewer |

### Issues
| Repo | # | Title | Status | Role |
|------|---|-------|--------|------|
| automation | 19 | Queue-based dispatch... | open | author |
| OpenHands | 13454 | V1 API: Conversation Tagging | open | author |
```

This gives you a verified list of external outputs to cross-reference with conversations.

---

## Step 3: List Today's OpenHands Conversations

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?limit=50&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Accept: application/json"
```

Filter results for today's date by checking `created_at` timestamps.

## Step 4: Extract Intent from Each Conversation

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

## Step 5: Identify External Actions (What Escaped the Sandbox?)

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

## Step 6: Cross-Reference and Present Summary

Combine GitHub activity with conversation analysis to create a complete picture.

### Matching Logic

For each GitHub PR/issue, try to find the conversation that worked on it:
- Search conversation actions for `git push` to the same branch
- Look for PR URLs in agent messages
- Match issue numbers mentioned in conversation text

For each conversation, verify external claims:
- If conversation says "created PR #123" → verify it appears in GitHub activity
- If conversation says "updated issue" → check if it shows in `involves:` search

### Combined Summary Table

```
| # | Source | Title | External Output | Verified? | Status |
|---|--------|-------|-----------------|-----------|--------|
| 1 | Conv + GH | PR Review | PR #2334 | ✅ Found | ✅ Done |
| 2 | Conv only | Research | (sandbox file) | N/A | 📁 Retrieve |
| 3 | Conv + GH | Feature | Issue #19 | ✅ Found | ✅ Done |
| 4 | GH only | PR #2447 review | PR #2447 | ✅ | ✅ Done |
```

### Unmatched Items

Flag these for user attention:
- **GitHub activity with no conversation**: Work done outside OpenHands (or conversation deleted)
- **Conversation claiming PR/issue not in GitHub**: May have failed, or PR is in different org
- **Conversation with no external output**: May need sandbox file retrieval

## Step 7: Verification Questions

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

## Step 8: Create Notion Work Log Page

### Page Structure

The final page structure organizes work into clear sections:

```markdown
# Work Log - [Date]

Summary of OpenHands conversations and work accomplished today.

---

## 📅 Standup Items
Items from morning standup post ([time]):

| Item | Status | GitHub Link | Notes |
|------|--------|-------------|-------|
| [Standup commitment 1] | ✅ | [#123](url) | Completed |
| [Standup commitment 2] | ⏳ Follow-up | | Waiting on X |

## 🔧 Other Work
Work done that wasn't in standup:

| Item | Status | GitHub Link | Notes |
|------|--------|-------------|-------|
| [Ad-hoc task 1] | ✅ | [#456](url) | Description |
| [Research task] | ⏳ Follow-up | | Not yet organized |

## 🔄 Follow-up Actions

### Carry-over Items
Items ongoing from before today:

| Action | Due/Next Step |
|--------|---------------|
| [Ongoing task 1] | When X happens |
| [Ongoing task 2] | This week |

### New Items (from [Date])
New follow-ups identified today:

| Action | Owner | Due/Next Step |
|--------|-------|---------------|
| [New commitment 1] | [Name] | This week |
| [New commitment 2] | [Name] | Before [date] |

### GitHub Issues & PRs Requiring My Action

| Issue/PR | Title | Repository | Next Step |
|----------|-------|------------|-----------|
| [#2334](url) | fix(terminal): filter... | software-agent-sdk | Get reviewed and merged |

## ✅ Completed Work

### 1. [Task Name]
[Description of work done]

Link: [PR/Issue/Page](https://...)

Status: ✅ Complete

## 🔄 Work in Process

### 1. [Task Name]
[Description of ongoing work]

Link: [relevant links]

## GitHub Issues & PRs
---
Detailed reference section for all GitHub activity:

### 1. [PR/Issue Title]
[Full description of work done]

Link: [PR #123](url)
Status: ✅ Complete / ⏳ In Progress

## Communications
[Things learned and shared with others]

## Meetings
- [Meeting 1]
- [Meeting 2]

---

*Generated: [timestamp] via OpenHands conversation analysis*
```

### Section Purposes

| Section | Purpose |
|---------|---------|
| **📅 Standup Items** | Track completion of morning commitments |
| **🔧 Other Work** | Capture ad-hoc work not planned in standup |
| **🔄 Follow-up Actions** | Consolidated view of all pending items |
| **├─ Carry-over Items** | Ongoing from previous days |
| **├─ New Items** | New commitments made today |
| **└─ GitHub PRs/Issues** | PRs/issues needing your action |
| **✅ Completed Work** | Detailed descriptions of finished work |
| **🔄 Work in Process** | Started but not complete |
| **GitHub Issues & PRs** | Reference section with full details |
| **Communications** | Knowledge sharing |
| **Meetings** | Meeting notes/attendees |

### Categorizing Follow-up Items

When creating the Follow-up Actions section, split items into:

**Carry-over Items** - Ongoing from before today:
- Items mentioned as "still pending" or "continuing"
- Recurring responsibilities
- Items waiting on external dependencies
- Use 2-column table (Action, Due/Next Step) - owner is implicit

**New Items from [Date]** - Identified today:
- New commitments made in conversations
- Action items from meetings
- New tasks discovered during work
- Use 3-column table (Action, Owner, Due/Next Step) when multiple people involved

**GitHub Issues & PRs Requiring My Action** - PRs/issues needing your next step:
- Always include Title column for quick scanning
- Link the issue/PR number
- Include repository name
- Describe the specific next step needed

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

## Step 9: Retrieve Files from Paused Sandboxes

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
User: "I'm in Eastern timezone. What did I work on yesterday? Create a work log."

Agent: "I'll gather your activity from March 30. Let me check Slack, GitHub, and OpenHands..."

Agent: [Searches Slack for user's messages]
       "Found your standup post at 7:46 AM with 6 items, plus several other messages."

Agent: [Queries GitHub for PRs/issues]
       "Found 5 PRs authored/updated and 2 issues you were involved with."

Agent: [Lists OpenHands conversations]
       "Found 8 conversations from yesterday."

Agent: "Here's what I found:

## Summary for March 30

### Standup Items (from Slack)
| Item | Matched To |
|------|------------|
| JPMC v1 upgrade check-in | Conv #3, GitHub discussions |
| AMD prospect call | ✅ Meeting (no OpenHands) |
| Self-hosted backlog | Conv #5, Notion updates |

### GitHub Activity
| PR/Issue | Title | Role |
|----------|-------|------|
| #2334 | fix(terminal): filter... | author |
| #2447 | Laminar custom ports | reviewer |

### OpenHands Conversations
| # | Intent | External Output |
|---|--------|-----------------|
| 1 | PR review fix | PR #2334 pushed |
| 2 | Plugin comparison | (sandbox file) |
| 3 | Self-hosted roadmap | Notion page updated |

What's the status of each? Any files to retrieve from #2?"

User: "#1 and #3 done. #2 has a report I want to save. Also add the Tech Council 
presentation to follow-ups - I committed to that in a meeting."

Agent: [Creates Notion page with full structure]
       [Resumes sandbox #2, retrieves report.md, creates subpage]

Agent: "Done! Work log created with:
- 6 standup items tracked
- 3 GitHub PRs documented  
- Follow-up actions split into carry-over vs new items
- Report saved as subpage

View: [Notion link]"
```

---

## Tips

1. **Ask for timezone first** - Critical for accurate date filtering
2. **Start with Slack** - Standup posts provide structure for the whole log
3. **Cross-reference sources** - GitHub verifies claims, conversations provide detail
4. **Split follow-ups** - Carry-over (ongoing) vs New (from today) helps prioritize
5. **Include PR titles** - Makes the GitHub table scannable at a glance
6. **Run at end of day** for complete picture
7. **Check sandbox_status** before trying to resume - may already be running
8. **Use markdown field** for Notion pages - much easier than building block arrays
9. **Link conversations** in pending items so you can resume them easily
10. **Create subpages** for long content rather than cramming into main page
