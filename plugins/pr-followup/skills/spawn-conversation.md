---
name: spawn-conversation
description: Start a new OpenHands conversation (worker) and verify it is running
triggers:
  - /spawn-conversation
---

# Spawn Conversation

Start a worker conversation via the OpenHands API to do heavy work on one of your
PRs (confirm-problem, QA, addressing review with code changes, adding tests).
Verify it started, then return control. **Do not** wait for it to finish — the
next `/follow-up` wake-up reconciles its result.

## Usage

```
/spawn-conversation
```

Provide:
- **repository**: the target repo to check out (e.g. `OpenHands/OpenHands`)
- **title**: descriptive title (include the repo#PR)
- **prompt**: the task, usually starting with one of this plugin's skills
  (`/address-review`, `/qa-pr`, `/confirm-problem`)
- **pr_number**: the PR the worker operates on
- **plugins**: load this plugin so the worker has the skills

## Step 1: Start the conversation

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "X-Access-Token: $OH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "selected_repository": "OpenHands/OpenHands",
    "git_provider": "github",
    "title": "[address-review] OpenHands/OpenHands#15001",
    "initial_message": {
      "content": [{"type": "text", "text": "/address-review for PR #15001. Be deferential to human feedback; treat all-hands-bot and *[bot] accounts as agents. Do not merge."}],
      "run": true
    },
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/pr-followup",
        "ref": "main"
      }
    ],
    "pr_number": [15001]
  }'
```

The response returns a start task with an `id` and `status` (`WORKING`).

## Step 2: Poll until ready

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations/start-tasks/search" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq --arg id "TASK_ID" '.items[] | select(.id == $id)'
```

Status progression: `WORKING` → `WAITING_FOR_SANDBOX` → `PREPARING_REPOSITORY` →
`SETTING_UP_SKILLS` → `STARTING_CONVERSATION` → `READY`. Poll every 3–5 s, time
out after ~90 s.

## Step 3: Verify it is running

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids=CONVERSATION_ID" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq '.[0] | {execution_status, conversation_url}'
```

Expect `execution_status: running`.

## Step 4: Return and exit

Record the `conversation_id` (7-char prefix is enough) and `conversation_url` so
`/follow-up` can add a row to the worklog **Active Workers** table. Then exit.

## Important

- The worker prompt must restate the guardrails: **deferential to humans,
  agents = config Agents list + `[bot]`, never merge.** A worker may not have the
  worklog `config.md` in front of it, so pass the agent accounts explicitly if it
  needs them.
- Fire and forget. Monitoring completion is `/follow-up`'s job next cycle.
- Keep concurrency polite (default one active worker) — these are shared repos
  and shared CI.

## Error handling

- Start task `ERROR` → report the detail, exit.
- Poll timeout (>90 s) → report last known status, exit.
- `execution_status` `error`/`stuck` → report, exit, and note in **Needs you**.

## Reference

- `POST /api/v1/app-conversations` — start
- `GET /api/v1/app-conversations/start-tasks/search` — poll start status
- `GET /api/v1/app-conversations?ids=` — conversation details
- OpenAPI: https://app.all-hands.dev/openapi.json
