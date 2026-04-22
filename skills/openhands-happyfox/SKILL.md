---
name: openhands-happyfox
description: OpenHands-specific HappyFox help desk configuration. Contains instance details, statuses, priorities, custom fields, and workflows for the OpenHands support portal at support.openhands.dev.
triggers:
  - openhands support
  - openhands helpdesk
  - openhands ticket
  - support ticket
  - happyfox openhands
  - file support ticket
  - create support ticket
---

# OpenHands HappyFox Help Desk

This skill provides OpenHands-specific configuration for the HappyFox help desk at `support.openhands.dev`. Use this alongside the generic `happyfox` skill for API operations.

## Instance Configuration

| Setting | Value |
|---------|-------|
| **URL** | `https://support.openhands.dev` |
| **API Base** | `https://support.openhands.dev/api/1.1/json/` |
| **API Key Variable** | `$HFOX_API_KEY` |
| **Auth Code Variable** | `$HFOX_AUTH_CODE` |

## Categories

| ID | Name | Description |
|----|------|-------------|
| 1 | OpenHands Support | Default category for all tickets |

## Statuses

| ID | Name | Behavior | Usage |
|----|------|----------|-------|
| 1 | **New** | pending | Newly created ticket, not yet triaged |
| 5 | **Info Needed** | pending | Waiting for more information from customer |
| 2 | **Investigation** | pending | Actively being investigated by support |
| 7 | **Waiting On Eng** | pending | Escalated to engineering team |
| 6 | **Delivered** | pending | Solution delivered, awaiting confirmation |
| 3 | **On Hold** | pending | Paused - waiting on external dependency |
| 4 | **Closed** | completed | Ticket resolved and closed |

### Status Workflow

```
New → Investigation → Waiting On Eng → Delivered → Closed
      ↓                                    ↓
      Info Needed ←←←←←←←←←←←←←←←←←←←←←←←←
      ↓
      On Hold (if blocked)
```

## Priorities

| ID | Name | Order | Usage |
|----|------|-------|-------|
| 2 | **Total Outage** | 1 | Complete service unavailable |
| 3 | **Critical Block** | 2 | Critical functionality broken, no workaround |
| 1 | **Major Block** | 3 | Major functionality broken, workaround exists |
| 4 | **Partial Failure** | 4 | Some features not working |
| 5 | **Minor Issue** | 5 | Small bugs or inconveniences |
| 7 | **Security Concern** | 6 | Security-related issues |
| 6 | **General Request or Question** | 7 | Questions, feature requests (default) |

## Custom Fields

### Ticket Custom Fields

| ID | Name | Type | Required | Options |
|----|------|------|----------|---------|
| 1 | **Product Type** | choice | Yes | See below |
| 2 | **Conversation URL / Conversation ID** | text | No | Link to related conversation |

#### Product Type Options (t-cf-1)

| Choice ID | Value | Description |
|-----------|-------|-------------|
| 2 | OpenHands SaaS (Web) | Cloud-hosted OpenHands at app.all-hands.dev |
| 1 | OpenHands Self-Hosted | Enterprise self-hosted deployment |
| 3 | CLI | OpenHands command-line interface |
| 4 | Opensource Docker Build | Community Docker deployment |
| 5 | Not Applicable | General questions, not product-specific |

## Staff / Agents

| ID | Name | Email | Active |
|----|------|-------|--------|
| 1 | Alona King | alona@openhands.dev | ✓ |
| 6 | Ash Clarke | ash@openhands.dev | ✓ |
| 8 | Chris Nelson | chris.nelson@openhands.dev | ✓ |
| 7 | Chuck Butkus | chuck@openhands.dev | ✓ |
| 3 | Joe Pelletier | joe@openhands.dev | ✓ |
| 5 | John-Mason Shackelford | john-mason@openhands.dev | ✓ |

## Quick Reference Commands

### Create a New Ticket

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/tickets/" \
  -d '{
    "name": "Customer Name",
    "email": "customer@example.com",
    "category": 1,
    "subject": "Issue summary",
    "text": "Detailed description of the issue...",
    "priority": 6,
    "t-cf-1": 2
  }' | jq
```

**Required fields:**
- `name`, `email`: Customer contact info
- `category`: Always `1` (OpenHands Support)
- `subject`, `text`: Issue details
- `t-cf-1`: Product Type (required)

### Create Ticket for SaaS User with Conversation Link

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/tickets/" \
  -d '{
    "name": "Customer Name",
    "email": "customer@example.com",
    "category": 1,
    "subject": "Agent stuck in loop",
    "text": "The agent keeps repeating the same action...",
    "priority": 4,
    "t-cf-1": 2,
    "t-cf-2": "https://app.all-hands.dev/conversations/abc123"
  }' | jq
```

### List Open Tickets

```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  "https://support.openhands.dev/api/1.1/json/tickets/?status=_pending&size=50" | jq
```

### List Tickets Waiting on Engineering

```bash
curl -s -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  'https://support.openhands.dev/api/1.1/json/tickets/?status=_all&q=status:"Waiting On Eng"' | jq
```

### Add Staff Reply and Change Status

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 5,
    "html": "<p>Your reply here...</p>",
    "update_customer": true,
    "status": 6
  }' | jq
```

### Escalate to Engineering

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 5,
    "status": 7,
    "html": "<p>Escalating to engineering for further investigation.</p>",
    "update_customer": true
  }' | jq
```

### Close a Ticket

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/ticket/TICKET_NUMBER/staff_update/" \
  -d '{
    "staff": 5,
    "status": 4,
    "html": "<p>Closing this ticket. Please reopen if you need further assistance.</p>",
    "update_customer": true
  }' | jq
```

### Add Private Note (Internal)

```bash
curl -s -X POST -u "$HFOX_API_KEY:$HFOX_AUTH_CODE" \
  -H "Content-Type: application/json" \
  "https://support.openhands.dev/api/1.1/json/ticket/TICKET_NUMBER/staff_pvtnote/" \
  -d '{
    "staff": 5,
    "html": "<p>Internal note: Confirmed this is a known issue in v1.2.3</p>",
    "alert": "s"
  }' | jq
```

## Common Workflows

### New Ticket Triage

1. Review ticket details and set appropriate priority
2. Set Product Type if not already set
3. Add Conversation URL if customer references one
4. Move to "Investigation" status
5. Assign to appropriate agent

### Escalation to Engineering

1. Add private note with technical details
2. Update status to "Waiting On Eng"
3. Tag with relevant labels (e.g., `bug`, `feature-request`)
4. Link to GitHub issue if created

### Resolution Flow

1. Deliver solution → Status: "Delivered"
2. Wait for customer confirmation (3 business days)
3. If confirmed or no response → Status: "Closed"
4. If issue persists → Back to "Investigation"

## Best Practices

1. **Always set Product Type** - Required field, helps with reporting
2. **Include Conversation URLs** - Links help engineering debug issues
3. **Use appropriate priorities** - Reserve Total Outage for true emergencies
4. **Add private notes** - Document technical findings for future reference
5. **Update customers** - Set `update_customer: true` for visibility
6. **Use staff ID 5** for John-Mason when creating automated tickets
