# Plugin Launcher Skill

Help users create "Try It" badges and test pages for their OpenHands plugins and skills, making it easy for others to launch conversations with pre-configured extensions.

## Why Use This Skill?

When you publish a plugin or skill, you want users to try it easily. This skill helps you:

- **Add a "Try It" badge** to your README that launches OpenHands with your plugin pre-loaded
- **Create test pages** for manually testing plugins during development
- **Generate launch URLs** that can be shared in documentation, issues, or Slack

## Triggers

This skill activates when users mention:
- `plugin launcher`, `launch badge`, `launch page`
- `skill badge`, `plugin test page`
- `launch url`, `openhands launch`, `/launch`

## Example Conversations

### Adding a Badge to a Plugin README

**Human:** I have a plugin called "city-weather" in my repo jpshackelford/openhands-sample-plugins. Can you create a badge I can add to the README so people can try it?

**Agent:** I'll generate a launch badge for your city-weather plugin.

*The agent finds the plugin in your repository and generates:*

```markdown
[![Try City Weather](https://img.shields.io/badge/Try%20City%20Weather-blue?logo=...)](https://app.all-hands.dev/launch?plugins=...)
```

Add this to the top of your README.md. When clicked, it opens OpenHands Cloud with your plugin pre-configured.

---

### Finding and Creating a Badge for a Skill

**Human:** Create a launch badge for the github skill in OpenHands/extensions

**Agent:** I'll look up the github skill in the OpenHands/extensions repository and generate a badge.

*The agent searches the marketplace.json, finds the skill at `skills/github`, and outputs the badge markdown.*

---

### Creating a Test Page for Development

**Human:** I'm working on a new plugin in my feature branch. Can you create an HTML test page so I can test launching it?

**Agent:** I'll create a test page for your plugin. What's the repository and plugin path?

**Human:** It's in myorg/myrepo, plugins/new-feature, on the "dev" branch

**Agent:** *Creates an HTML file with a launch button, configurable base URL, and copy-to-clipboard functionality.*

Here's your test page: `new-feature-test.html`. Open it in a browser, adjust the base URL if needed (e.g., for staging), and click Launch to test.

---

### Getting a Launch URL to Share

**Human:** Give me a launch URL for the pr-review plugin that I can share in Slack

**Agent:** Here's the launch URL for the pr-review plugin:

```
https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9wci1yZXZpZXcifV0=
```

Anyone who clicks this link will be prompted to log in, then see a modal to start a conversation with the pr-review plugin loaded.

## What You Get

| Request | Output |
|---------|--------|
| "Create a badge for my plugin" | Markdown badge you can paste into README |
| "Generate a test page" | HTML file with launch button and dark theme |
| "Give me a launch URL" | Direct URL to share |
| "Find the X plugin/skill and create a badge" | Agent searches the repo and generates badge |
| "Create a badge with editable parameters" | Badge that opens a form with input fields |

## Plugin Parameters

If your plugin defines parameters in `.claude-plugin/plugin.json`, the launch modal will show editable form fields:

```json
{
  "name": "my-plugin",
  "parameters": {
    "repo_url": {
      "type": "string",
      "description": "Repository URL to analyze",
      "required": true
    },
    "depth": {
      "type": "number", 
      "default": 3
    }
  }
}
```

When you ask for a badge with parameters, the agent will read these definitions and generate a URL that shows input fields in the launch modal. Users can fill in or modify values before starting the conversation.

## How It Works

1. **You describe** what plugin or skill you want to create a badge/URL for
2. **The agent finds it** by checking the repository's marketplace.json or standard directories (`plugins/`, `skills/`)
3. **The agent generates** a properly-formatted launch URL with base64-encoded configuration
4. **You use the output** in your README, documentation, or share directly

## Technical Details

For agents and advanced users, this skill includes scripts in the `scripts/` directory. See [SKILL.md](./SKILL.md) for the full technical reference including:

- URL format and PluginSpec interface
- Manual URL construction
- Repository structure patterns
- Script usage details
