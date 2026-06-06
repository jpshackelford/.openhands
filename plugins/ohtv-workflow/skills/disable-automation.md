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

The orchestrator should disable itself when it detects **two consecutive `<!-- orchestrator-status: quiet -->` markers** in WORKLOG.md, indicating:
- No new work has appeared for multiple check cycles
- All PRs are merged or waiting for external input
- The project has reached a natural pause point

The trigger source of the run (cron-fired, user-invoked, manually dispatched) is **not** relevant — every entry with a `quiet` marker counts.

## Automation ID

**CRITICAL:** This automation's ID is:
```
ed08056a-b8d8-41ac-adb3-1d8d105e0cef
```

This ID identifies the "OHTV Workflow Orchestrator" automation in OpenHands Cloud. Use this exact ID when making the disable API call.

### Fallback: Lookup by Name

If the hardcoded ID returns 404 (automation was recreated), look it up by name. The lookup returns the **enabled** automation matching the name:

```bash
AUTOMATION_ID=$(curl -s "https://app.all-hands.dev/api/automation/v1?limit=100" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
matches = [a for a in data['automations']
           if a['name'] == 'OHTV Workflow Orchestrator' and a['enabled']]
if not matches:
    sys.exit('No enabled automation named OHTV Workflow Orchestrator')
print(matches[0]['id'])
")
echo "Resolved automation ID: $AUTOMATION_ID"
```

Use `$AUTOMATION_ID` in place of the hardcoded UUID in the curl commands below if the hardcoded ID is stale.

## How to Disable

Make a PATCH request to the OpenHands automation API:

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Expected Response

Success (HTTP 200):
```json
{
  "id": "ed08056a-b8d8-41ac-adb3-1d8d105e0cef",
  "name": "OHTV Workflow Orchestrator",
  "enabled": false,
  ...
}
```

### Verification

After disabling, verify the automation is disabled:

```bash
curl -s "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['enabled'], d['name'])"
```

Should output:
```
False OHTV Workflow Orchestrator
```

## Detection Logic

The orchestrator should check WORKLOG.md for consecutive `quiet` status markers:

```bash
# Get the last two status markers from WORKLOG.md (most recent two orchestrator decisions).
LAST_TWO_MARKERS=$(grep -oE "orchestrator-status: (spawn|quiet)" WORKLOG.md | tail -2)
QUIET_COUNT=$(echo "$LAST_TWO_MARKERS" | grep -c "quiet" || true)

# If both of the last two markers are 'quiet', this run would be the 3rd consecutive — disable.
if [ "$QUIET_COUNT" -eq 2 ]; then
  echo "Two consecutive quiet periods detected — disabling automation."
fi
```

Example pattern to detect (only the markers matter — English phrasing of the body is irrelevant):

```markdown
### 2025-05-05 10:30 UTC - Orchestrator
✅ Nothing actionable in scope; both slots idle.
<!-- orchestrator-status: quiet -->

### 2025-05-05 11:00 UTC - Orchestrator
✅ Still no new work, still both slots idle.
<!-- orchestrator-status: quiet -->
```

After the second `quiet` marker above, the next orchestrator run must auto-disable instead of emitting a third `quiet` marker.

## WORKLOG Entry When Disabling

After disabling, append to WORKLOG.md. A disable is an action, so the marker is `spawn`:

```markdown
### {timestamp} - Orchestrator

🔒 **Auto-disabled due to inactivity**

Two consecutive quiet periods detected — no work to pick up.
Automation has been disabled to prevent unnecessary runs.

To re-enable:
1. Open https://app.all-hands.dev/automations
2. Find "OHTV Workflow Orchestrator"
3. Toggle the enable switch

OR run:
```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

<!-- orchestrator-status: spawn -->

---
```

## Re-enabling

To re-enable the automation (via API or UI):

### Via API
```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/ed08056a-b8d8-41ac-adb3-1d8d105e0cef" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Via UI
1. Go to https://app.all-hands.dev/automations
2. Find "OHTV Workflow Orchestrator" in the list
3. Click the enable toggle

## Environment Variables Required

- `OPENHANDS_API_KEY` - OpenHands Cloud API key for automation management
