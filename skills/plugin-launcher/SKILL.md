---
name: plugin-launcher
description: Generate HTML test pages and launch badges for OpenHands plugins and skills. Use when you need to create a launch URL, test page, or README badge for a plugin or skill in OpenHands/extensions or any GitHub repository.
triggers:
  - plugin launcher
  - launch page
  - launch badge
  - plugin test page
  - skill badge
  - launch url
  - openhands launch
  - /launch
---

# Plugin & Skill Launcher

Generate HTML test pages and launch badges for OpenHands plugins and skills that use the `/launch` route.

## Quick Reference

| Content Type | Location Pattern | Example |
|--------------|------------------|---------|
| Plugin | `plugins/<name>/` | `plugins/pr-review/` |
| Skill | `skills/<name>/` | `skills/github/` |

## Finding Plugins and Skills in a Repository

When given a repository URL or name, follow these steps to locate plugins/skills:

### Step 1: Check for Marketplace Configuration

Look for a marketplace manifest that lists available plugins/skills:

```bash
# Check for .claude-plugin/marketplace.json (may be a symlink)
curl -s "https://api.github.com/repos/OWNER/REPO/contents/.claude-plugin/marketplace.json"

# If it's a symlink (content is a path), follow it:
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/marketplaces/default.json"
```

The marketplace JSON contains a `plugins` array with each plugin/skill's metadata:

```json
{
  "metadata": {
    "pluginRoot": "./skills"
  },
  "plugins": [
    {
      "name": "github",
      "source": "./github",
      "description": "Interact with GitHub..."
    }
  ]
}
```

### Step 2: Check Standard Directories

If no marketplace file exists, check standard directory structures:

```bash
# List plugins directory
curl -s "https://api.github.com/repos/OWNER/REPO/contents/plugins" | jq -r '.[].name'

# List skills directory  
curl -s "https://api.github.com/repos/OWNER/REPO/contents/skills" | jq -r '.[].name'
```

### Step 3: Verify the Plugin/Skill Exists

Confirm the plugin/skill has the required files:

```bash
# For plugins: check for .claude-plugin/plugin.json or commands/
curl -s "https://api.github.com/repos/OWNER/REPO/contents/plugins/PLUGIN_NAME"

# For skills: check for SKILL.md
curl -s "https://api.github.com/repos/OWNER/REPO/contents/skills/SKILL_NAME/SKILL.md"
```

## URL Format

The launch endpoint uses base64-encoded JSON for plugin/skill configuration:

```
https://app.all-hands.dev/launch?plugins=BASE64_JSON&message=URL_ENCODED_MESSAGE
```

### PluginSpec Interface

```typescript
interface PluginSpec {
  source: string;       // Source: 'github:owner/repo' or git URL
  ref?: string | null;  // Optional branch, tag, or commit
  repo_path?: string;   // Subdirectory path (e.g., 'skills/github' or 'plugins/pr-review')
  parameters?: Record<string, unknown>; // User-provided configuration (see below)
}
```

## Plugin Parameters

Plugins can define configurable parameters in `.claude-plugin/plugin.json`. When included in a launch URL, these parameters appear as editable form fields in the launch modal.

### Parameter Definition Format (in plugin.json)

```json
{
  "name": "my-plugin",
  "parameters": {
    "repo_url": {
      "type": "string",
      "description": "GitHub repository URL",
      "required": true
    },
    "review_depth": {
      "type": "string",
      "description": "How thorough the review should be",
      "default": "standard"
    },
    "include_tests": {
      "type": "boolean",
      "default": true
    },
    "max_files": {
      "type": "number",
      "default": 10
    }
  }
}
```

### Including Parameters in Launch URL

Parameters are passed in the `parameters` field of the PluginSpec:

```python
plugins = [{
    "source": "github:owner/repo",
    "ref": "main",
    "repo_path": "plugins/my-plugin",
    "parameters": {
        "repo_url": "",           # Empty string = empty input field for user to fill
        "review_depth": "thorough",  # Pre-filled value
        "include_tests": True,
        "max_files": 20
    }
}]
```

### Empty vs Pre-filled Parameters

| Value in URL | UI Behavior |
|--------------|-------------|
| `""` (empty string) | Empty text input field |
| `null` | Empty text input field |
| `"value"` | Pre-filled text input |
| `0` | Number input showing 0 |
| `false` | Unchecked checkbox |
| `true` | Checked checkbox |

**Tip:** Use empty strings for required parameters to show an empty field that users must fill in.

## Generating Launch URLs and Badges

### For a Skill

```bash
# Generate launch URL for a skill
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --repo-path "skills/github" \
  --ref "main"

# Generate badge for a skill
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --repo-path "skills/github" \
  --badge \
  --badge-label "Try GitHub Skill"
```

### For a Plugin

```bash
# Generate launch URL for a plugin
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --repo-path "plugins/pr-review" \
  --ref "main" \
  --message "Start a PR review session"

# Generate badge for a plugin
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --repo-path "plugins/pr-review" \
  --badge \
  --badge-label "Try PR Review"
```

### Using the Find Script

Use the helper script to find and generate badges for a skill/plugin by name:

```bash
# Find a skill by name and generate a badge
python3 <this-skill-path>/scripts/find_and_generate.py \
  --repo "OpenHands/extensions" \
  --name "github" \
  --badge

# Find a plugin by name
python3 <this-skill-path>/scripts/find_and_generate.py \
  --repo "jpshackelford/openhands-sample-plugins" \
  --name "city-weather" \
  --badge
```

## Launch Badge Examples

### Example: Skill Badge (github skill)

[![Try GitHub Skill](https://img.shields.io/badge/Try%20GitHub%20Skill-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAic2tpbGxzL2dpdGh1YiJ9XQ==)

### Example: Plugin Badge (pr-review plugin)

[![Launch with OpenHands](https://img.shields.io/badge/Launch%20with-OpenHands-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9wci1yZXZpZXcifV0=)

### Markdown Badge Format

```markdown
[![Badge Text](https://img.shields.io/badge/LABEL-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](LAUNCH_URL)
```

## Generating an HTML Test Page

```bash
python3 <this-skill-path>/scripts/generate_test_page.py \
  --source "github:OpenHands/extensions" \
  --repo-path "skills/github" \
  --output github-skill-test.html
```

This generates an HTML page with:
- Configurable base URL field
- Launch button
- Dark theme styling
- URL copy functionality

## Repository Structure Patterns

### OpenHands/extensions (Official)

```
extensions/
├── .claude-plugin/
│   └── marketplace.json -> ../marketplaces/default.json
├── marketplaces/
│   └── default.json          # Lists all skills
├── plugins/
│   └── pr-review/            # Plugin with workflows
└── skills/
    ├── github/
    │   └── SKILL.md
    ├── gitlab/
    │   └── SKILL.md
    └── ...
```

### Custom Plugin Repository

```
my-plugins/
├── .claude-plugin/
│   └── marketplace.json      # Optional: plugin catalog
├── plugins/
│   └── my-plugin/
│       ├── .claude-plugin/
│       │   └── plugin.json   # Plugin manifest
│       └── commands/
│           └── run.md        # Slash commands
└── README.md
```

### Custom Skills Repository

```
my-skills/
├── skills/
│   └── my-skill/
│       └── SKILL.md          # Skill definition
└── README.md
```

## Simple URL Format (Dev/Testing)

For quick testing without base64 encoding:

```
https://app.all-hands.dev/launch?plugin_source=github:owner/repo&plugin_ref=main
```

## Manual URL Construction

```python
import base64
import json
import urllib.parse

# For a skill
config = [{
    "source": "github:OpenHands/extensions",
    "ref": "main",
    "repo_path": "skills/github"
}]

# For a plugin
config = [{
    "source": "github:OpenHands/extensions",
    "ref": "main", 
    "repo_path": "plugins/pr-review"
}]

plugins_b64 = base64.b64encode(json.dumps(config).encode()).decode()
url = f"https://app.all-hands.dev/launch?plugins={plugins_b64}"
```

## API Reference

The launch route is a frontend route that uses the `POST /api/v1/app-conversations` endpoint to create conversations with plugins/skills. See the [OpenHands API docs](https://app.all-hands.dev/docs) for the full API specification.
