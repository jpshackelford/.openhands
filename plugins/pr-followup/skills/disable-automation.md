---
name: disable-automation
description: Auto-disable this automation after consecutive quiet wake-ups
triggers:
  - /disable-automation
---

# Disable Automation

Disable this follow-up automation in OpenHands Cloud (without deleting it) after
consecutive quiet wake-ups, so it stops consuming runs while you have nothing in
flight. It can be re-enabled any time from the UI or API.

## When to use

Invoke this when the current wake-up is **quiet** and the previous worklog entry
was **also** quiet. A cycle is quiet only when:

- you have no open PRs that need an action, AND
- there are no active workers, AND
- there are no **Needs you** items.

`waiting` (a human reviewer owes you a review), active workers, errored workers,
and any **Needs you** item are **not** quiet — never disable in those states.

## Automation ID

Read it from the worklog `config.md`:

```bash
AUTOMATION_ID=$(grep -A2 "## Automation" config.md | grep -i "ID:" | sed 's/.*ID:[[:space:]]*//')
echo "Automation ID: $AUTOMATION_ID"
```

## Disable

```bash
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false}'
```

Verify:

```bash
curl -s "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" | jq '.enabled, .name'
```

## Worklog entry when disabling

Append a short entry to today's day file (see [`/worklog`](worklog.md)):

```markdown
### HH:MM EST — Follow-up

🔒 **Auto-disabled** after two quiet cycles — no open PRs need action and nothing needs you.

Re-enable from https://app.all-hands.dev/automations, or new PR activity that
your re-enable hook watches for will turn it back on.

---
```

## Re-enabling

```bash
AUTOMATION_ID=$(grep -A2 "## Automation" config.md | grep -i "ID:" | sed 's/.*ID:[[:space:]]*//')
curl -X PATCH "https://app.all-hands.dev/api/automation/v1/${AUTOMATION_ID}" \
  -H "Authorization: Bearer ${OPENHANDS_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

Or toggle it in the UI at https://app.all-hands.dev/automations.

## Environment

- `OPENHANDS_API_KEY` — used to manage the automation (enable/disable).
