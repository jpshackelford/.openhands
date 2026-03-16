# Terminal Recording Skill

Create professional terminal GIF recordings to demonstrate bug fixes or new features in pull requests.

## Overview

This skill teaches agents how to use [VHS by Charmbracelet](https://github.com/charmbracelet/vhs) to create reproducible, scripted terminal recordings that can be embedded directly in PR descriptions.

## Use Cases

- **Bug Fix Demonstrations**: Show a bug is fixed with a visual demo
- **Feature Showcases**: Demonstrate new CLI features in action
- **Manual Testing Evidence**: Provide visual proof that changes work as expected
- **Documentation**: Create GIFs for README files and docs

## Why VHS?

| Feature | Benefit |
|---------|---------|
| Scriptable `.tape` files | Reproducible, version-controlled recordings |
| GIF/MP4/WebM output | Embeds directly in GitHub/GitLab PRs |
| Built-in hosting | `vhs --publish` for instant sharing |
| Professional themes | Clean, consistent terminal appearance |

## Quick Example

```bash
# Install VHS
go install github.com/charmbracelet/vhs@latest

# Create a demo tape
cat > demo.tape << 'EOF'
Output demo.gif
Set Theme "Dracula"
Type "echo 'Hello World'"
Enter
Sleep 2s
EOF

# Generate GIF
vhs demo.tape

# Publish for PR embedding
vhs demo.tape --publish
```

## Triggers

This skill activates when users mention:
- "record a terminal demo"
- "create a CLI demo"
- "demonstrate a fix"
- "show the feature working"
- "terminal recording"
- "gif recording"
