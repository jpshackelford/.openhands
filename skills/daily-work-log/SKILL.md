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
| **Slack** | Standup posts, discussions, commitments made, help requested, message count |
| **GitHub** | PRs/issues touched, reviews done, comments made |
| **OpenHands** | Detailed work done, files created, external actions taken |
| **Calendar (iCal)** | Meeting schedule with times, organizers, and participants |

## Process Overview

1. **Determine timezone and target date**
2. **Gather Slack activity** - Standup posts, messages sent, commitments made, message count
3. **Gather GitHub activity** - PRs and issues touched (external verification)
4. **Gather calendar data** - Meetings from iCal feed
5. **Retrieve OpenHands conversations** from the day
6. **Extract intent** from human messages in each conversation
7. **Cross-reference** all sources to build complete picture
8. **Identify communications** - Things learned/shared not captured elsewhere
9. **Present summary** for user review and categorization
10. **Create Notion page** with structured sections
11. **Retrieve sandbox files** if needed and create subpages

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

### Constructing Slack Message Permalinks

**IMPORTANT**: To link directly to specific Slack messages in the work log, use this format:

```
https://{workspace}.slack.com/archives/{channel_id}/p{timestamp_without_period}
```

Where:
- `{workspace}` is your Slack workspace (e.g., `allhandsai`)
- `{channel_id}` is the channel ID (e.g., `C09EC5A0KRQ`)
- `{timestamp_without_period}` is the message timestamp with the period removed

For example, if a message has `ts: "1775044942.271039"` in channel `C09EC5A0KRQ`:
```
https://allhandsai.slack.com/archives/C09EC5A0KRQ/p1775044942271039
```

For thread replies, add the thread timestamp:
```
https://allhandsai.slack.com/archives/{channel_id}/p{timestamp}?thread_ts={parent_ts}&cid={channel_id}
```

**Tip**: The Slack search results include `channel_id` and message timestamps. Use these to construct permalinks for the Communications section.

### Count Total Messages

Track the total number of messages sent and break down by channel:

```
slack_search_public_and_private(
  query="from:<@USER_ID> on:YYYY-MM-DD",
  limit=20,
  include_context=false,
  response_format="concise"
)
```

Continue paginating until no more results. Provide summary like:

```
**You sent 20 Slack messages on March 30, 2026.**

Breakdown by channel:
- **#forward-deployed-engineering**: 4 messages
- **#proj-self-hosted**: 3 messages
- **DM with Robert**: 3 messages
- ...
```

---

## Step 2: Gather Calendar Data (iCal)

**Why Calendar?** Meetings provide context for discussions and account for time spent:
- Shows which meetings you attended
- Identifies who you met with
- Accounts for time not captured in Slack/GitHub/OpenHands

### Fetch Calendar Data

If the user provides an iCal URL (via secret or directly):

```bash
curl -s "$ICAL_SECRET_ADDR" > /tmp/calendar.ics
```

### Parse with Python

```python
from icalendar import Calendar
from datetime import datetime, date
import pytz

TARGET_DATE = date(2026, 3, 30)
TZ = pytz.timezone('America/New_York')

with open('/tmp/calendar.ics', 'rb') as f:
    cal = Calendar.from_ical(f.read())

meetings = []
for component in cal.walk():
    if component.name == "VEVENT":
        start = component.get('dtstart').dt
        end = component.get('dtend')
        summary = str(component.get('summary', 'No Title'))
        attendees = component.get('attendee', [])
        organizer = component.get('organizer')
        
        # Filter to target date
        if isinstance(start, datetime):
            start = start.astimezone(TZ)
            event_date = start.date()
        else:
            event_date = start
            
        if event_date == TARGET_DATE:
            # Calculate duration
            duration_mins = None
            if end:
                end_dt = end.dt
                if isinstance(end_dt, datetime):
                    end_dt = end_dt.astimezone(TZ)
                    duration_mins = int((end_dt - start).total_seconds() / 60)
            
            # Format time WITHOUT leading zeros: "1:00 PM" not "01:00 PM"
            time_str = start.strftime('%-I:%M %p') if isinstance(start, datetime) else "All day"
            duration_str = f"({duration_mins} mins)" if duration_mins else ""
            
            # Get organizer name
            org_name = ""
            if organizer:
                org_email = str(organizer).replace('mailto:', '')
                org_name = org_email.split('@')[0]
                # Use "(external)" or "(recurring)" for cryptic calendar IDs
                if org_name.startswith('c_'):
                    org_name = "(recurring)" if "recurring" in summary.lower() else "(external)"
            
            # Get participant list (excluding organizer)
            participants = []
            if attendees:
                for a in (attendees if isinstance(attendees, list) else [attendees]):
                    email = str(a).replace('mailto:', '')
                    name = email.split('@')[0]
                    if name != org_name:
                        participants.append(name)
            
            meetings.append({
                'summary': summary,
                'time': f"{time_str} {duration_str}",
                'organizer': org_name,
                'participants': ', '.join(participants[:4]) + (f" +{len(participants)-4} more" if len(participants) > 4 else "")
            })
```

### Meetings Table Format

| Meeting | Time | Organizer | Participants |
|---------|------|-----------|--------------|
| FDE Team Interview - Chris Nelson | 11:00 AM (45 mins) | (external) | john-mason, alona |
| OpenHands all hands | 12:00 PM (30 mins) | robert | john-mason, openhands-staff, cliff.yang |
| Engineering Office Hours | 1:00 PM (60 mins) | (recurring) | ash, john-mason, engineering-team +2 more |
| Quick Huddle - McAfee | 2:00 PM (15 mins) | clarke | john-mason, calvin, rajiv.shah |

**Time format**: `H:MM AM/PM (NN mins)` - no leading zeros on the hour.

---

## Step 3: Gather GitHub Activity

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

## Step 4: List Today's OpenHands Conversations

**IMPORTANT**: Use the `/search` endpoint with date filters. The response contains items in the `.items[]` array, NOT at the root level.

```bash
# For Eastern timezone (UTC-4 during EDT), use appropriate UTC offsets
curl -s "https://app.all-hands.dev/api/v1/app-conversations/search?created_at__gte=2026-04-01T04:00:00Z&created_at__lt=2026-04-02T04:00:00Z&limit=50" \
  -H "Authorization: Bearer $OH_API_KEY" \
  | jq '[.items[] | {id: .id, title: .title, created_at: .created_at}] | sort_by(.created_at)'
```

**Key points:**
- Use `/search` endpoint, NOT `/app-conversations` directly
- Filter by `created_at__gte` (start of day in UTC) and `created_at__lt` (end of day in UTC)
- Results are in `.items[]` array
- For Eastern timezone (EDT = UTC-4): midnight local = 04:00 UTC

### Alternative: List and Filter

If the search endpoint doesn't return expected results, you can list recent conversations and filter:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?limit=100&sort_by=created_at&sort_order=desc" \
  -H "Authorization: Bearer $OH_API_KEY" \
  | jq --arg start "2026-04-01" --arg end "2026-04-02" \
    '[.items[] | select(.created_at >= $start and .created_at < $end)]'
```

**Note**: Results are paginated. Check for `next_page_id` and use `page_id` parameter for subsequent pages.

## Step 5: Extract Intent from Each Conversation

**Important**: A single message rarely tells the full story. Retrieve ALL human messages to understand the user's evolving goal:

```bash
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search?kind__eq=MessageEvent&limit=100" \
  -H "Authorization: Bearer $OH_API_KEY" \
  | jq '[.items[] | select(.source == "user") | {timestamp: .timestamp, content: .content}]'
```

**Note**: The events search endpoint uses:
- Path: `/api/v1/conversation/{id}/events/search` (singular "conversation")
- Filter: `kind__eq=MessageEvent` for messages
- Results in `.items[]` array

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
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search?kind__eq=ActionEvent&limit=50" \
  -H "Authorization: Bearer $OH_API_KEY" \
  | jq '[.items[] | select(.tool_name == "finish")] | last'
```

The finish message often summarizes what was accomplished and what remains.

### Event Kind Filters

| Filter Value | Description |
|--------------|-------------|
| `MessageEvent` | User and agent messages |
| `ActionEvent` | Agent tool calls (filter by `.tool_name`) |
| `ObservationEvent` | Tool results |

## Step 6: Identify External Actions (What Escaped the Sandbox?)

**Critical question**: The sandbox is ephemeral. What work was saved outside of it?

Scan the conversation events for actions that persisted work externally:

```bash
# Get all actions to analyze what was done
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search?kind__eq=ActionEvent&limit=100" \
  -H "Authorization: Bearer $OH_API_KEY" \
  | jq '[.items[] | {tool: .tool_name, summary: .summary}]'
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
curl -s "https://app.all-hands.dev/api/v1/conversation/{id}/events/search?kind__eq=ActionEvent&limit=100" \
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

## Step 7: Cross-Reference and Present Summary

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

### Identify Communications Content

After cross-referencing, identify Slack messages that are NOT accounted for in other sections:

**These belong in Communications:**
- Advice given to others (not tied to a specific deliverable)
- Knowledge shared (commit history, context, confirmations)
- Things learned from others (articles, tips, discussions)
- Discussions that don't result in action items

**These belong elsewhere:**
- Standup posts → 📅 Standup Items
- Commitments made → 🔄 Follow-up Actions
- Work discussions → Notes in relevant sections
- Help provided on a tracked item → Notes in that item's section

Split into two categories:
- **Shared**: Things you provided to others
- **Learned**: New information you received

---

## Step 8: Verification Questions

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

## Step 9: Create Notion Work Log Page

### Creating vs Updating Pages

**IMPORTANT**: The Notion MCP's `update_page_markdown` tool has a complex API that is prone to validation errors. Instead of trying to update an existing page:

**Recommended approach for updates:**
1. **Delete the existing page** using `patch_page` with `in_trash: true`
2. **Create a new page** using `post_page` with the `markdown` field

This is more reliable than trying to use `update_page_markdown` which requires specific `type` and nested structure parameters that often fail validation.

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

Conversations not captured in other sections:

### Shared
- [Advised Rajiv on McAfee deployment](https://allhandsai.slack.com/archives/C0A8MKT4RSA/p1775044942271039) - Recommended front-loading connectivity validation before kickoff.
- [Shared code quality CI approach](https://allhandsai.slack.com/archives/C0ALCEFB7AQ/p1775069225318279) - method/file line limits in #proj-automations.
- [Confirmed self-hosted customer list](https://allhandsai.slack.com/archives/C0A8MKT4RSA/p1775058460350129) - Verified with Alona.

### Learned
- [Claude Code power-user tips](https://allhandsai.slack.com/archives/C07P44PGXU2/p1775051891612679) (#competition) - Clarke shared Boris Cherny's thread.

**You sent 20 Slack messages on March 30, 2026.**

Breakdown by channel:
- **#forward-deployed-engineering**: 4 messages
- **#proj-self-hosted**: 3 messages
- **DM with Robert**: 3 messages
- ...

## Meetings

| Meeting | Time | Organizer | Participants |
|---------|------|-----------|--------------|
| FDE Team Interview - Chris Nelson | 11:00 AM (45 mins) | (external) | john-mason, alona |
| OpenHands all hands | 12:00 PM (30 mins) | robert | john-mason, openhands-staff, cliff.yang |
| Engineering Office Hours | 1:00 PM (60 mins) | (recurring) | ash, john-mason, engineering-team +2 more |
| Quick Huddle - McAfee | 2:00 PM (15 mins) | clarke | john-mason, calvin, rajiv.shah |
| [INT] AMD engagement plan sync | 3:30 PM (30 mins) | cliff.yang | john-mason, rajiv.shah, robert, smit |
| Platform Team - OHE Release | 4:30 PM (25 mins) | john-mason | ash, ray, ai.vong, joe.laverty +2 more |

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
| **Communications** | Things learned/shared, with Slack message count |
| **├─ Shared** | Advice, context, confirmations you provided |
| **├─ Learned** | New information you received |
| **└─ Message Count** | Total messages sent with channel breakdown |
| **Meetings** | Table with time, organizer, participants |

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

### Updating Existing Pages

**Avoid using `update_page_markdown`** - it has a complex API with required parameters like `type` (must be one of `insert_content`, `replace_content_range`, `update_content`, or `replace_content`) and nested structures like `replace_content.new_str` that are prone to validation errors.

**Instead, to modify an existing work log page:**

1. **Read the current content** using `retrieve_page_markdown`
2. **Delete the page** using `patch_page` with body `{"in_trash": true}`
3. **Create a new page** with the updated content using `post_page` with `markdown` field

This delete-and-recreate approach is more reliable than trying to use the update API.

### Adding Hyperlinks to Existing Blocks

If you need to update a specific block, use `update_a_block` with rich_text containing links:

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

## Step 10: Retrieve Files from Paused Sandboxes

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
| `notion.patch_page` | Updating page properties (including trash) |
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
| `/app-conversations/search` | GET | Search conversations with filters |
| `/app-conversations?ids=X` | GET | Get specific conversation(s) |
| `/conversation/{id}/events/search` | GET | Search conversation events |
| `/sandboxes/{id}/resume` | POST | Resume paused sandbox |

### Conversation Search Parameters

| Parameter | Example | Purpose |
|-----------|---------|---------|
| `created_at__gte` | `2026-04-01T04:00:00Z` | Created after (inclusive) |
| `created_at__lt` | `2026-04-02T04:00:00Z` | Created before (exclusive) |
| `limit` | `50` | Max results per page |
| `page_id` | `{next_page_id}` | Pagination cursor |

### Event Search Parameters

| Parameter | Values |
|-----------|--------|
| `kind__eq` | `MessageEvent`, `ActionEvent`, `ObservationEvent` |
| `sort_order` | `TIMESTAMP` (default), `TIMESTAMP_DESC` |
| `limit` | Number of events (max 100) |
| `page_id` | Pagination cursor |

### Response Structure

Both search endpoints return results in this structure:
```json
{
  "items": [...],           // Array of results
  "next_page_id": "...",    // For pagination (null if no more)
  "total": 123              // Total count (may be approximate)
}
```

---

## Example Session

```
User: "I'm in Eastern timezone. What did I work on yesterday? Create a work log."

Agent: "I'll gather your activity from March 30. Let me check Slack, GitHub, calendar, 
       and OpenHands..."

Agent: [Searches Slack for user's messages]
       "Found your standup post at 7:46 AM with 6 items, plus 19 other messages."

Agent: [Fetches calendar data]
       "Found 6 meetings on your calendar."

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
| AMD prospect call | ✅ Meeting at 3:30 PM |
| Self-hosted backlog | Conv #5, Notion updates |

### Meetings (from Calendar)
| Meeting | Time | Organizer |
|---------|------|-----------|
| OpenHands all hands | 12:00 PM (30 mins) | robert |
| Engineering Office Hours | 1:00 PM (60 mins) | (recurring) |
| Quick Huddle - McAfee | 2:00 PM (15 mins) | clarke |
| AMD engagement plan sync | 3:30 PM (30 mins) | cliff.yang |

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

### Slack Messages Not Captured Above
- Advised Rajiv on McAfee deployment (front-load connectivity validation)
- Thanked Clarke for Boris Cherny's Claude Code tips thread
- Confirmed self-hosted customer list with Alona

What's the status of each? Any files to retrieve from #2?"

User: "#1 and #3 done. #2 has a report I want to save. Also add the Tech Council 
presentation to follow-ups - I committed to that in a meeting."

Agent: [Creates Notion page with full structure]
       [Resumes sandbox #2, retrieves report.md, creates subpage]

Agent: "Done! Work log created with:
- 6 standup items tracked
- 6 meetings documented with times and organizers  
- 3 GitHub PRs documented
- Communications split into Shared/Learned
- 20 Slack messages counted with channel breakdown
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
11. **Time format for meetings** - Use `H:MM AM/PM (NN mins)` without leading zeros
12. **Communications ≠ Work** - Only include Slack threads not captured elsewhere
13. **Count Slack messages** - Provides a quick metric of communication volume
14. **Calendar via iCal** - Install `icalendar` and `pytz` packages for parsing
15. **Split Communications** - Separate "Shared" (gave) from "Learned" (received)
16. **Use /search endpoint** for conversations - results are in `.items[]` array
17. **Delete-and-recreate** for Notion updates - more reliable than `update_page_markdown`
18. **Construct Slack permalinks** - Use `https://{workspace}.slack.com/archives/{channel_id}/p{ts_without_period}`
