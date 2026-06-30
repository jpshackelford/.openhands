---
name: spawn-conversation
description: Start a new OpenHands conversation and verify it's running
triggers:
  - /spawn-conversation
---

# Spawn Conversation

Start a new OpenHands conversation via the API. Verify it started and is running, then return control. Do NOT monitor for completion - that's the orchestrator's job on subsequent wake-ups.

## Usage

```
/spawn-conversation
```

Then provide:
- **repository**: GitHub repo (e.g., `OpenHands/conversation-search`)
- **title**: Descriptive title for the conversation
- **prompt**: The task/instructions for the new conversation
- **plugins** (optional): List of plugins to load (e.g., `github:owner/repo`)
- **pr_number** (optional): PR number if working on a specific PR

## API Mechanics

### Step 1: Start the Conversation

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "X-Access-Token: $OH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "selected_repository": "OpenHands/conversation-search",
    "git_provider": "github",
    "title": "[Impl] Add semantic search",
    "initial_message": {
      "content": [{"type": "text", "text": "Your prompt here"}],
      "run": true
    },
    "plugins": [
      {
        "source": "github:jpshackelford/.openhands",
        "repo_path": "plugins/conversation-search-workflow",
        "ref": "add-conversation-search-workflow-plugin"
      }
    ],
    "pr_number": [123]
  }'
```

**Plugin fields:**
- `source`: GitHub repo containing the plugin
- `repo_path`: Subdirectory path to the plugin
- `ref`: Branch, tag, or commit SHA (use PR branch until merged to main)

**Response** returns a start task:
```json
{
  "id": "task-uuid",
  "status": "WORKING",
  "app_conversation_id": null,
  ...
}
```

### Step 2: Poll Until Ready

Poll the start task until status is `READY` or `ERROR`:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations/start-tasks/search" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq --arg id "TASK_ID" '.items[] | select(.id == $id)'
```

**Status progression:**
- `WORKING` → `WAITING_FOR_SANDBOX` → `PREPARING_REPOSITORY` → `SETTING_UP_SKILLS` → `STARTING_CONVERSATION` → `READY`

Poll every 3-5 seconds, timeout after ~90 seconds if not `READY`.

### Step 3: Verify Agent is Running

Once `READY`, extract `app_conversation_id` and check the conversation:

```bash
curl -s "https://app.all-hands.dev/api/v1/app-conversations?ids=CONVERSATION_ID" \
  -H "X-Access-Token: $OH_API_KEY" \
| jq '.[0] | {execution_status, sandbox_status, conversation_url}'
```

**Expected:** `execution_status` should be `running` (or transition to it shortly).

Valid execution statuses: `idle`, `running`, `paused`, `waiting_for_confirmation`, `finished`, `error`, `stuck`

### Step 4: Post to Slack

Once verified the conversation started, post a notification to `#proj-conv-search-prototype`:

```
🚀 *Launched: {Worker Type}*

{Description of what the worker will do}
{If PR exists: Link to PR}

📎 <https://app.all-hands.dev/conversations/{conversation_id}|Watch progress>
```

Example:
```
🚀 *Launched: Review Worker*

Addressing feedback on <https://github.com/OpenHands/conversation-search/pull/5|PR #5: Add semantic search>

📎 <https://app.all-hands.dev/conversations/abc123|Watch progress>
```

### Step 5: Return and Exit

Once verified the conversation started and Slack notification sent:
1. Report the `conversation_url` (e.g., `https://app.all-hands.dev/conversations/{id}`)
2. Note the `conversation_id` for tracking
3. **EXIT** - do not wait for the conversation to finish

## Important Notes

- **Authentication**: Uses `$OH_API_KEY` environment variable
- **Plugins**: When specified, the new conversation loads these plugins and has access to their skills
- **PR Number**: When working on a PR, pass the PR number so the conversation has that context
- **Fire and forget**: This skill only ensures the conversation started. Monitoring completion is the orchestrator's responsibility on subsequent wake-ups.

## Error Handling

- If start task shows `ERROR` status, report the error detail and exit
- If polling times out (>90s), report timeout and the last known status
- If conversation shows `error` or `stuck` execution status, report and exit

## Example

**Starting an implementation worker:**
```
Repository: OpenHands/conversation-search
Title: [Impl] Add semantic search
Prompt: |
  Read the design doc in AGENTS.md. Implement the next pending item.
  Follow the PR workflow: branch, implement with tests (>80% coverage), 
  lint, commit, push, create draft PR, monitor CI until green,
  then reflect and update the plan before moving PR to ready.
Plugins: github:jpshackelford/.openhands/plugins/conversation-search-workflow@add-conversation-search-workflow-plugin
```

The plugin path includes `@branch` to load from the PR branch. Once merged, change to `@main` or omit the ref.

## Reference

- OpenAPI spec: https://app.all-hands.dev/openapi.json
- Key endpoints:
  - `POST /api/v1/app-conversations` - Start conversation
  - `GET /api/v1/app-conversations/start-tasks/search` - Poll start status
  - `GET /api/v1/app-conversations?ids=` - Get conversation details
