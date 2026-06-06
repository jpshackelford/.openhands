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

**CRITICAL:** Read the automation ID from `.agents/resources/orchestration.md`:

```bash
# Extract the automation ID from the orchestration config
AUTOMATION_ID=$(grep -A1 "## Automation" .agents/resources/orchestration.md | grep "ID:" | sed 's/.*ID: //')
echo "Automation ID: $AUTOMATION_ID"
```

The orchestration.md file should contain:
```markdown
## Automation
- ID: your-automation-uuid-here
```

## How to Disable

Make a PATCH request to the OpenHands automation API:

```bash
# Read the automation ID from config
AUTOMATION_ID=$(grep -A1 "## Automation" .agents/resources/orchestration.md | grep "ID:" | sed 's/.*ID: //')

curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

### Expected Response

Success (HTTP 200):
```json
{
  "id": "{AUTOMATION_ID}",
  "name": "{Automation Name}",
  "enabled": false,
  ...
}
```

### Verification

After disabling, verify the automation is disabled:

```bash
curl -s "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" | jq '.enabled, .name'
```

Should output:
```
false
"{Automation Name}"
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
2. Find your workflow orchestrator automation
3. Toggle the enable switch

OR run:
```bash
AUTOMATION_ID=$(grep -A1 "## Automation" .agents/resources/orchestration.md | grep "ID:" | sed 's/.*ID: //')
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
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
AUTOMATION_ID=$(grep -A1 "## Automation" .agents/resources/orchestration.md | grep "ID:" | sed 's/.*ID: //')
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

### Via UI
1. Go to https://app.all-hands.dev/automations
2. Find your workflow orchestrator automation in the list
3. Click the enable toggle

## Environment Variables Required

- `OPENHANDS_API_KEY` - OpenHands Cloud API key for automation management
