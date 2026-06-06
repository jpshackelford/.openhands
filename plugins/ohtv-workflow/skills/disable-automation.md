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

### 🚨 Do NOT use any other ID

There are stale references to a previous automation ID (`c202ca20-60d5-4f5b-9d53-3d7308c1d95b`, name `"OHTV Workflow Orchestrator (feature branch, disabled)"`) sprinkled throughout `WORKLOG.md` history. **That automation is archived. Disabling it again is a no-op and means the live `ed08056a…` automation will keep firing.**

Rules:

1. **The ONLY trusted source for the automation ID is this skill file.** Do not copy an ID from `WORKLOG.md`, from your conversation context, or from any other historical document — even if the entry looks recent or authoritative.
2. **Before calling PATCH to disable, GET the automation first and assert two things:**
   - `id == "ed08056a-b8d8-41ac-adb3-1d8d105e0cef"`
   - `name == "OHTV Workflow Orchestrator"` (NOT `"OHTV Workflow Orchestrator (feature branch, disabled)"`)
   - `enabled == true` (if it's already `false`, abort — you'd be disabling something already disabled, which strongly suggests wrong ID)
3. **If the GET response's `name` includes `(feature branch, disabled)` or `(disabled)`, STOP.** You have the wrong ID. Re-read this skill file and use `ed08056a…`.
4. **After PATCH, re-GET and confirm `name` and `enabled=false`.** Log both fields to the worklog entry verbatim so a human can audit.

### Pre-disable verification snippet

Run this before the PATCH call:

```bash
AUTOMATION_ID="ed08056a-b8d8-41ac-adb3-1d8d105e0cef"
RESPONSE=$(curl -s "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}")
NAME=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('name',''))")
ENABLED=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('enabled',''))")

if [ "$NAME" != "OHTV Workflow Orchestrator" ]; then
  echo "ABORT: Wrong automation. Got name='$NAME'. Expected 'OHTV Workflow Orchestrator'."
  exit 1
fi
if [ "$ENABLED" != "True" ]; then
  echo "ABORT: Automation already disabled. Got enabled='$ENABLED'."
  exit 1
fi
echo "OK to disable: $AUTOMATION_ID ($NAME, enabled=$ENABLED)"
```

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
