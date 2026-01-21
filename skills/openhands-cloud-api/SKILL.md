---
name: openhands-cloud-api
description: Query and debug OpenHands Cloud conversations using the V1 API. Use when investigating conversation events, debugging agent issues, or accessing conversation history on app.all-hands.dev.
triggers:
  - openhands api
  - openhands cloud api
  - conversation events
  - v1 api
  - OH_API_KEY
  - debug conversation
  - conversation history
  - inspect conversation
---

# OpenHands Cloud API

This skill provides guidance for working with the OpenHands Cloud API to query conversations, inspect events, and debug agent issues.

## Authentication

Use the `OH_API_KEY` environment variable for authentication:

```bash
curl -s "https://app.all-hands.dev/api/..." \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Accept: application/json"
```

## API Endpoint Structure

The OpenHands Cloud has two API versions:
- **Legacy (v0)**: `/api/conversations/...` - Being deprecated
- **V1 (current)**: `/api/v1/conversation/...` - Use this

## Common Endpoints

### List Conversations

```bash
curl -s "https://app.all-hands.dev/api/conversations" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Accept: application/json" | jq
```

Response includes:
```json
{
  "results": [
    {
      "conversation_id": "uuid",
      "title": "Conversation Title",
      "status": "RUNNING|STOPPED",
      "runtime_status": "STATUS$READY|STATUS$ERROR",
      "url": "https://{runtime}.prod-runtime.all-hands.dev/api/...",
      "session_api_key": "...",
      "conversation_version": "V1"
    }
  ]
}
```

### Search/List Events (V1 API)

```bash
# Get events for a conversation
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search" \
  -H "Authorization: Bearer $OH_API_KEY" \
  -H "Accept: application/json" | jq

# With pagination
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search?limit=100" \
  -H "Authorization: Bearer $OH_API_KEY"

# Get next page
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/search?page_id={next_page_id}" \
  -H "Authorization: Bearer $OH_API_KEY"
```

### Count Events

```bash
curl -s "https://app.all-hands.dev/api/v1/conversation/{conversation_id}/events/count" \
  -H "Authorization: Bearer $OH_API_KEY"
```

## Event Structure

Events have a `kind` field indicating their type:

| Kind | Source | Description |
|------|--------|-------------|
| `ActionEvent` | agent | Agent tool call (has `tool_call_id`, `action`) |
| `ObservationEvent` | environment | Tool result (has `tool_call_id`, `action_id`, `observation`) |
| `MessageEvent` | user | User message (has `llm_message`) |
| `ConversationStateUpdateEvent` | environment | State change (has `key`, `value`) |

### Key Event Fields

**ActionEvent:**
```json
{
  "id": "event-uuid",
  "kind": "ActionEvent",
  "source": "agent",
  "tool_name": "terminal",
  "tool_call_id": "toolu_xxx",  // Links to ObservationEvent
  "action": { "command": "...", "kind": "TerminalAction" },
  "llm_response_id": "chatcmpl-xxx"
}
```

**ObservationEvent:**
```json
{
  "id": "event-uuid",
  "kind": "ObservationEvent",
  "source": "environment",
  "tool_name": "terminal",
  "tool_call_id": "toolu_xxx",  // Matches ActionEvent
  "action_id": "action-event-uuid",  // Points to ActionEvent.id
  "observation": { "content": [...], "kind": "TerminalObservation" }
}
```

## Debugging Conversations

### Analyze Event Timeline

```bash
curl -s "https://app.all-hands.dev/api/v1/conversation/{id}/events/search?limit=100" \
  -H "Authorization: Bearer $OH_API_KEY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, item in enumerate(data.get('items', [])):
    ts = item.get('timestamp', 'N/A')
    source = item.get('source', 'N/A')
    kind = item.get('kind', 'N/A')
    print(f'{i}: [{ts}] [{source}] {kind}')
"
```

### Find Errors

```bash
curl -s "https://app.all-hands.dev/api/v1/conversation/{id}/events/search?limit=100" \
  -H "Authorization: Bearer $OH_API_KEY" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i, item in enumerate(data.get('items', [])):
    if 'code' in item and 'detail' in item:
        print(f'Event {i}: code={item.get(\"code\")}')
        print(f'  detail: {str(item.get(\"detail\", \"\"))[:500]}')
"
```

### Check Tool Call Matching

Each `ActionEvent` with a `tool_call_id` should have exactly one matching `ObservationEvent`:

```bash
curl -s "https://app.all-hands.dev/api/v1/conversation/{id}/events/search?limit=100" \
  -H "Authorization: Bearer $OH_API_KEY" | python3 -c "
import json, sys
from collections import Counter

data = json.load(sys.stdin)
items = data.get('items', [])

action_ids = set()
observed_ids = set()

for item in items:
    if item.get('kind') == 'ActionEvent':
        action_ids.add(item.get('id'))
    elif item.get('kind') == 'ObservationEvent':
        observed_ids.add(item.get('action_id'))

unmatched = action_ids - observed_ids
print(f'Total actions: {len(action_ids)}')
print(f'Total observations: {len(observed_ids)}')
print(f'Unmatched actions: {unmatched if unmatched else \"None\"}')

# Check for duplicate observations
obs_action_ids = [item.get('action_id') for item in items if item.get('kind') == 'ObservationEvent']
duplicates = [id for id, count in Counter(obs_action_ids).items() if count > 1]
if duplicates:
    print(f'WARNING: Actions with multiple observations: {duplicates}')
"
```

## Common Issues

### "Service Temporarily Unavailable"
The conversation's runtime may be paused or crashed. Check `runtime_status` in the conversation list.

### Tool Use / Tool Result Mismatch
If you see errors like:
```
messages.59: `tool_use` ids were found without `tool_result` blocks immediately after
```

This indicates duplicate or mismatched tool calls. Use the tool call matching script above to diagnose.

### 404 on Events Endpoint
- Make sure you're using `/api/v1/conversation/` (not `/api/conversations/`)
- The conversation must exist and you must have access

## Tips

1. **Always use V1 API** (`/api/v1/`) for event queries
2. **Save responses locally** for analysis: `> /tmp/events.json`
3. **Use jq for quick filtering**: `jq '.items[] | select(.kind == "ActionEvent")'`
4. **Check runtime_status** before querying events - paused runtimes may not respond
