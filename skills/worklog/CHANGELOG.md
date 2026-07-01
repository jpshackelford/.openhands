# Worklog Skill Enhancement - v6

## Summary

Enhanced the worklog skill to separate automation-triggered conversations from manual work with a tabbed interface and rich automation metadata display.

## Key Changes

### 1. Automation Detection and Categorization

- **Trigger field detection**: Uses the `trigger` field from conversations to identify automation-triggered work
- **Tag extraction**: Extracts automation metadata from conversation tags:
  - `automationname`: Human-readable automation name
  - `automationid`: Automation UUID
  - `automationrunid`: Run UUID  
  - `automationtrigger`: Trigger type (cron, event)

### 2. Tabbed HTML Interface

Added three tabs in HTML output:
- **All Conversations**: Shows all conversations (default view)
- **Manual Work**: Only conversations initiated manually (trigger != 'automation')
- **Automations**: Only automation-triggered conversations

### 3. Enhanced Metadata Display

#### HTML Format
- Automation name displayed in trigger badge (e.g., "🤖 Dad Joke Time")
- Additional badges for:
  - ⏰ Trigger type (cron/event)
  - 🔧 Automation ID (first 8 chars with full ID in tooltip)
  - ▶️ Run ID (first 8 chars with full ID in tooltip)

#### Text Format
- Shows automation name and trigger type
- Displays automation ID and run ID
- Summary counts: "Total: X (Manual: Y, Automations: Z)"

#### Markdown Format
- Bold automation name with emoji
- Inline automation IDs
- Enhanced metadata section

### 4. Statistics Enhancement

Header now shows breakdown:
- Total Conversations
- Manual Work count
- Automations count

## API Fields Used

From the OpenHands Cloud API `/api/v1/app-conversations/search`:

```json
{
  "trigger": "automation",
  "tags": {
    "automationname": "Dad Joke Time",
    "automationid": "58d196ac-1210-4bf7-b7e0-d59c44f2dd2c",
    "automationrunid": "068ffb89-f49f-4a1e-a64a-785a888d286a",
    "automationtrigger": "cron"
  }
}
```

## Example Output

### HTML Tabs
```
┌─────────────────────────────────────────────────┐
│ All Conversations (10) │ Manual Work (7) │ Automations (3) │
└─────────────────────────────────────────────────┘
```

### Automation Card
```html
┌─────────────────────────────────────────────────┐
│ 1. Dad Joke Request                              │
│ View conversation → | 02:30 PM ET                │
│                                                   │
│ Automated dad joke delivery as scheduled.        │
│                                                   │
│ 🆔 c94edd79 | 🤖 Dad Joke Time | ⏰ cron          │
│ 🔧 58d196ac | ▶️ 068ffb89                        │
└─────────────────────────────────────────────────┘
```

## Backward Compatibility

- All existing functionality preserved
- Text and Markdown formats enhanced (not breaking)
- HTML format still works for conversations without automation metadata
- Empty automation tab shown if no automation conversations exist

## Testing

To test the enhanced worklog:

```bash
# Generate HTML worklog
cd /workspace/project
python3 .agents/skills/worklog/generate_worklog.py --format html

# Serve and view
python3 .agents/skills/worklog/serve_worklog.py &
```

Then open the worklog URL to see the tabbed interface with automation metadata.
