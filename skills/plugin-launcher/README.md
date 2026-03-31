# Plugin Launcher Skill

Generate launch URLs, HTML test pages, and README badges for OpenHands plugins and skills.

## Installation

Add this skill to your OpenHands workspace:

```bash
/add-skill https://github.com/jpshackelford/.openhands/skills/plugin-launcher
```

Or reference it directly in your conversation.

## Quick Start

### Generate a Badge for a Skill

```bash
python3 scripts/find_and_generate.py \
  --repo "OpenHands/extensions" \
  --name "github" \
  --badge
```

Output:
```markdown
[![Try Github](https://img.shields.io/badge/Try%20Github-blue?logo=...)](https://app.all-hands.dev/launch?plugins=...)
```

### Generate a Badge for a Plugin

```bash
python3 scripts/find_and_generate.py \
  --repo "jpshackelford/openhands-sample-plugins" \
  --name "city-weather" \
  --badge
```

### Generate an HTML Test Page

```bash
python3 scripts/generate_test_page.py \
  --source "github:OpenHands/extensions" \
  --repo-path "skills/github" \
  --output test-page.html
```

## Scripts

| Script | Description |
|--------|-------------|
| `find_and_generate.py` | Find a plugin/skill by name in a repo and generate URL or badge |
| `generate_launch_url.py` | Generate a launch URL or badge from explicit parameters |
| `generate_test_page.py` | Generate an HTML test page for manual testing |

## Examples

### Add a "Try It" Badge to Your Plugin README

1. Find your plugin and generate the badge:
   ```bash
   python3 scripts/find_and_generate.py \
     --repo "your-org/your-repo" \
     --name "your-plugin" \
     --badge \
     --badge-label "Try My Plugin"
   ```

2. Copy the output and paste it at the top of your README.md

### Test a Plugin Before Release

1. Generate a test page:
   ```bash
   python3 scripts/generate_test_page.py \
     --source "github:your-org/your-repo" \
     --repo-path "plugins/your-plugin" \
     --ref "feature-branch" \
     --output test.html
   ```

2. Open `test.html` in a browser and click "Launch"

## How It Works

The `/launch` route in OpenHands Cloud accepts a `plugins` query parameter containing a base64-encoded JSON array of plugin specifications:

```
https://app.all-hands.dev/launch?plugins=BASE64_ENCODED_JSON
```

Each plugin spec has this structure:
```json
{
  "source": "github:owner/repo",
  "ref": "main",
  "repo_path": "plugins/my-plugin"
}
```

This skill automates generating these URLs correctly.

## See Also

- [SKILL.md](./SKILL.md) - Full skill documentation with all options
- [OpenHands Extensions](https://github.com/OpenHands/extensions) - Official plugins and skills
- [OpenHands API Docs](https://app.all-hands.dev/docs) - API reference
