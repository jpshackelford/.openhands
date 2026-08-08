---
name: disable-automation
description: Disable this orchestrator's automation in OpenHands Cloud
triggers:
  - /disable-automation
---

# Disable Automation

Disable this orchestrator's automation in OpenHands Cloud without deleting it. The automation can be re-enabled later through the OpenHands UI or API.

## Usage

```
/disable-automation
```

## When to Use

The orchestrator should disable itself when it detects **two consecutive "quiet" entries** in WORKLOG.md, indicating:
- No new work has appeared for multiple check cycles
- All PRs are merged or waiting for external input
- The project has reached a natural pause point

## Automation ID

**CRITICAL:** This automation's ID is:
```
54a6d9ad-d1e3-462b-8f74-b7fc6da7de71
```

This ID identifies the "LXA Workflow Orchestrator" automation in OpenHands Cloud. Use this exact ID when making the disable API call.

## How to Disable

Make a PATCH request to the OpenHands automation API:

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/54a6d9ad-d1e3-462b-8f74-b7fc6da7de71" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Expected Response

Success (HTTP 200):
```json
{
  "id": "54a6d9ad-d1e3-462b-8f74-b7fc6da7de71",
  "name": "LXA Workflow Orchestrator",
  "enabled": false,
  ...
}
```

### Verification

After disabling, verify the automation is disabled:

```bash
curl -s "https://app.all-hands.dev/api/automation/v1/54a6d9ad-d1e3-462b-8f74-b7fc6da7de71" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" | jq '.enabled, .name'
```

Should output:
```
false
"LXA Workflow Orchestrator"
```

## Detection Logic

The orchestrator should check WORKLOG.md for consecutive quiet entries:

```bash
# Get the last 2 orchestrator entries from WORKLOG.md
tail -100 WORKLOG.md | grep -E "^### [0-9]{4}-[0-9]{2}-[0-9]{2}.*Orchestrator$|All quiet" | tail -4
```

If the output shows TWO consecutive entries that both contain "All quiet", then disable:

Example pattern to detect:
```
### 2025-05-05 10:30 UTC - Orchestrator
✅ **All quiet** - No action needed
### 2025-05-05 11:00 UTC - Orchestrator  
✅ **All quiet** - No action needed
```

## WORKLOG Entry When Disabling

After disabling, append to WORKLOG.md:

```markdown
### {timestamp} - Orchestrator

🔒 **Auto-disabled due to inactivity**

Two consecutive quiet periods detected - no work to pick up.
Automation has been disabled to prevent unnecessary runs.

To re-enable:
1. Open https://app.all-hands.dev/automations
2. Find "LXA Workflow Orchestrator"
3. Toggle the enable switch

OR run:
```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/54a6d9ad-d1e3-462b-8f74-b7fc6da7de71" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

---
```

## Re-enabling

To re-enable the automation (via API or UI):

### Via API
```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/54a6d9ad-d1e3-462b-8f74-b7fc6da7de71" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Via UI
1. Go to https://app.all-hands.dev/automations
2. Find "LXA Workflow Orchestrator" in the list
3. Click the enable toggle

## Environment Variables Required

- `OPENHANDS_API_KEY` - OpenHands Cloud API key for automation management
