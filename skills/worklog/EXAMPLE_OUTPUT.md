# Enhanced Worklog Example Output

## What We Found in the API

Automation-triggered conversations contain rich metadata in their `tags` field:

```json
{
  "id": "c94edd79b86f46fd88e53da5531c0683",
  "title": "✨ Dad Joke Request",
  "trigger": "automation",
  "tags": {
    "automationname": "Dad Joke Time",
    "automationid": "58d196ac-1210-4bf7-b7e0-d59c44f2dd2c",
    "automationrunid": "068ffb89-f49f-4a1e-a64a-785a888d286a",
    "automationtrigger": "cron"
  }
}
```

## HTML Output - Tabbed Interface

The HTML worklog now includes three tabs:

```
┌────────────────────────────────────────────────────────────────┐
│  📋 Worklog v6                                                 │
│  2026-07-01 Tuesday • LLM-Synthesized                          │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │   10     │  │    7     │  │    3     │                     │
│  │  Total   │  │  Manual  │  │  Auto    │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ [All Conversations (10)] [Manual Work (7)] [Automations (3)]   │
└────────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When you click "Automations" tab:

┌────────────────────────────────────────────────────────────────┐
│ 1. Dad Joke Request                                            │
│                                                                 │
│ View conversation → ················· 02:30 PM ET              │
│                                                                 │
│ Automated dad joke delivery as scheduled by the Dad Joke Time  │
│ automation.                                                     │
│                                                                 │
│ 🆔 c94edd79  🤖 Dad Joke Time  ⏰ cron                         │
│ 🔧 58d196ac  ▶️ 068ffb89                                       │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ 2. OHTV Workflow Orchestration                                 │
│                                                                 │
│ View conversation → ················· 03:45 PM ET              │
│                                                                 │
│ Orchestrated the OHTV project workflow including build, test,  │
│ and deployment stages.                                         │
│                                                                 │
│ 🆔 ed60b00a  🤖 OHTV Workflow Orchestrator  ⏰ cron            │
│ 🔧 c202ca20  ▶️ aeb0c912                                       │
└────────────────────────────────────────────────────────────────┘
```

## Text Output Example

```
📋 Worklog for 2026-07-01 Tuesday
======================================================================
Total conversations: 10 (Manual: 7, Automations: 3)

1. Dad Joke Request
   Time: 02:30 PM ET
   🤖 Automation: Dad Joke Time (cron)
   Automated dad joke delivery as scheduled by the Dad Joke Time automation.
   Conversation ID: c94edd79
   Automation ID: 58d196ac
   Run ID: 068ffb89
   Link: https://app.all-hands.dev/conversations/c94edd79b86f46fd88e53da5531c0683

2. Fix merge conflicts in PR #456
   Time: 09:15 AM ET
   Resolved merge conflicts between feature branch and main, ensuring all tests pass.
   Outcomes:
      PR #456: Fix authentication flow - https://github.com/org/repo/pull/456
   Conversation ID: abc12345
   Link: https://app.all-hands.dev/conversations/abc12345...
```

## Markdown Output Example

```markdown
# 📋 Worklog for 2026-07-01 Tuesday

**Total conversations:** 10 (Manual: 7, Automations: 3)

## 1. Dad Joke Request

**Time:** 02:30 PM ET | [View conversation](https://app.all-hands.dev/conversations/c94edd79b86f46fd88e53da5531c0683)

🤖 **Automation:** Dad Joke Time (cron)

Automated dad joke delivery as scheduled by the Dad Joke Time automation.

_Conversation ID: `c94edd79`_ | _Automation ID: `58d196ac`_ | _Run ID: `068ffb89`_

---

## 2. Fix merge conflicts in PR #456

**Time:** 09:15 AM ET | [View conversation](https://app.all-hands.dev/conversations/abc12345...)

Resolved merge conflicts between feature branch and main, ensuring all tests pass.

**Outcomes:**
- [PR #456: Fix authentication flow](https://github.com/org/repo/pull/456)

_Conversation ID: `abc12345`_

---
```

## Benefits

1. **Separate View**: Quickly see what work was done manually vs automatically
2. **Traceability**: Automation ID and Run ID let you track back to the automation configuration
3. **Context**: Automation name tells you which automation ran
4. **Trigger Type**: Know if it was cron-scheduled or event-triggered
5. **Statistics**: At-a-glance breakdown of manual vs automated work

## Use Cases

- **End-of-day review**: See all your manual work separate from automation runs
- **Automation monitoring**: Check the "Automations" tab to verify scheduled tasks ran
- **Debugging**: Use automation ID and run ID to investigate failed automation runs
- **Reporting**: Show stakeholders manual work vs automated processes
- **Time tracking**: Understand time spent on manual tasks vs automation-driven work
