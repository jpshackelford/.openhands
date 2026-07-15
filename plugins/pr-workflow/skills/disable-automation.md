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

The orchestrator should disable itself when it detects **two consecutive unproductive entries** in WORKLOG.md — that is, cycles that are either **quiet** or **idle**:

- **Quiet** — no new work has appeared: all PRs are merged or absent, no ready issues, no expansion candidates, and the project has reached a natural pause point.
- **Idle** — an in-scope PR/issue exists but its only blocker is a **non-actionable, already-escalated gate** (a human has been asked to act, or a required automated check fails identically regardless of PR content) **and there has been no new repo activity since the escalation** (head SHA unchanged; no new commits, comments, or reviews). See the orchestrate skill's [Escalated, Non-Actionable Gate](orchestrate.md#anti-stall-an-escalated-non-actionable-gate-is-not-an-excuse-to-spin-forever) section.

Both mean the orchestrator has no move that changes the outcome, so continuing to wake every cycle only reposts the same entry. A normal, still-actionable `⏳ **Waiting for Review**` (review just triggered, author mid-push, worker running, CI in progress) is **not** unproductive and must not count.

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

The orchestrator should check WORKLOG.md for two consecutive **unproductive** entries — quiet (`All quiet`) or idle (`— idle`):

```bash
# Get the last 2 orchestrator entries from WORKLOG.md
tail -100 WORKLOG.md | grep -E "^### [0-9]{4}-[0-9]{2}-[0-9]{2}.*Orchestrator$|All quiet|— idle" | tail -4
```

If the output shows TWO consecutive entries that are each quiet or idle, then disable.

Example pattern to detect (both quiet):
```
### 2025-05-05 10:30 UTC - Orchestrator
✅ **All quiet** - No action needed
### 2025-05-05 11:00 UTC - Orchestrator  
✅ **All quiet** - No action needed
```

Example pattern to detect (both idle — a PR is stuck on an escalated, non-actionable gate with no new activity):
```
### 2025-05-05 10:30 UTC - Orchestrator
⏳ **Waiting for Review** — idle (escalated 10:04, head unchanged)
### 2025-05-05 11:00 UTC - Orchestrator
⏳ **Waiting for Review** — idle (still blocked, no new commits/reviews)
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
