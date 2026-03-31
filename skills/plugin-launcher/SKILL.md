---
name: plugin-launcher
description: Generate HTML test pages and launch badges for OpenHands plugins. Use when you need to create a launch URL, test page, or README badge for a plugin in OpenHands/extensions or any GitHub repository.
triggers:
  - plugin launcher
  - launch page
  - launch badge
  - plugin test page
  - launch url
  - openhands launch
  - /launch
---

# Plugin Launcher

Generate HTML test pages and launch badges for OpenHands plugins that use the `/launch` route.

## URL Format

The launch endpoint uses base64-encoded JSON for plugin configuration:

```
https://app.all-hands.dev/launch?plugins=BASE64_JSON&message=URL_ENCODED_MESSAGE
```

### PluginSpec Interface

```typescript
interface PluginSpec {
  source: string;       // Plugin source: 'github:owner/repo' or git URL
  ref?: string | null;  // Optional branch, tag, or commit
  repo_path?: string;   // Subdirectory path within the repository
  parameters?: Record<string, unknown>; // User-provided configuration
}
```

## Generating a Launch URL

Use the bundled script to generate a launch URL:

```bash
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --ref "main" \
  --repo-path "plugins/pr-review" \
  --message "Start a PR review session" \
  --base-url "https://app.all-hands.dev"
```

Or manually construct:

```python
import base64
import json
import urllib.parse

plugins = [{
    "source": "github:OpenHands/extensions",
    "ref": "main",
    "repo_path": "plugins/pr-review"
}]

plugins_b64 = base64.b64encode(json.dumps(plugins).encode()).decode()
message = urllib.parse.quote("Start a PR review session")
url = f"https://app.all-hands.dev/launch?plugins={plugins_b64}&message={message}"
```

## Generating an HTML Test Page

Use the script to generate a full HTML test page:

```bash
python3 <this-skill-path>/scripts/generate_test_page.py \
  --source "github:OpenHands/extensions" \
  --repo-path "plugins/pr-review" \
  --output pr-review-test.html
```

This generates an HTML page similar to the one used in PR #12699, with:
- Configurable base URL field
- Launch button for the plugin
- Dark theme styling
- Test scenario descriptions

## Launch Badge for README

Add a badge to a plugin README that launches OpenHands with that plugin:

### Markdown Badge Format

```markdown
[![Launch with OpenHands](https://img.shields.io/badge/Launch%20with-OpenHands-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](LAUNCH_URL)
```

### Generate Badge URL

```bash
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:owner/repo" \
  --badge
```

## Example: Generate for an Extensions Plugin

To create a test page for the `pr-review` plugin:

```bash
cd /path/to/workspace

# Generate test page
python3 <this-skill-path>/scripts/generate_test_page.py \
  --source "github:OpenHands/extensions" \
  --repo-path "plugins/pr-review" \
  --ref "main" \
  --title "PR Review Plugin Test" \
  --output pr-review-test.html

# Generate badge markdown for README
python3 <this-skill-path>/scripts/generate_launch_url.py \
  --source "github:OpenHands/extensions" \
  --repo-path "plugins/pr-review" \
  --badge
```

## Simple URL Format (Dev/Testing)

For quick testing, use the simple URL format:

```
https://app.all-hands.dev/launch?plugin_source=github:owner/repo&plugin_ref=main
```

This is parsed as a single plugin without parameters.

## API Reference

The launch route is a frontend route that uses the `POST /api/v1/app-conversations` endpoint to create conversations with plugins. See the [OpenHands API docs](https://app.all-hands.dev/docs) for the full API specification.
