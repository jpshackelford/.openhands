---
name: terminal-recording
description: This skill should be used when the user asks to "record a terminal demo", "create a CLI demo", "demonstrate a fix in a PR", "show the feature working", or needs to create GIF recordings of terminal sessions for pull request demonstrations. Use VHS by Charmbracelet to create reproducible, professional terminal recordings.
triggers:
- terminal recording
- terminal demo
- cli demo
- record demo
- demonstrate
- vhs
- gif recording
---

# Terminal Recording for PR Demos

Create professional terminal recordings to demonstrate bug fixes or new features in pull requests using VHS by Charmbracelet.

## Quick Start

### Installation

```bash
# Install VHS and dependencies
sudo apt-get update && sudo apt-get install -y ffmpeg
go install github.com/charmbracelet/vhs@latest

# Install ttyd (required dependency)
wget -qO- https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 > /tmp/ttyd
chmod +x /tmp/ttyd
sudo mv /tmp/ttyd /usr/local/bin/ttyd

# Verify installation
vhs --version
```

### Recording Workflow

Two approaches depending on the situation:

#### Option A: Scripted Recording (Recommended for PRs)

Create a `.tape` file that scripts the exact commands:

```bash
# Create a tape file
cat > demo.tape << 'EOF'
# Demo Settings
Output demo.gif
Set FontSize 16
Set Width 800
Set Height 400
Set Theme "Dracula"

# Demo the command
Type "echo 'Hello, this is a demo!'"
Sleep 500ms
Enter
Sleep 2s
EOF

# Generate the GIF
vhs demo.tape
```

#### Option B: Interactive Recording

Record terminal activity live, then edit:

```bash
# Record interactively (exit shell to stop)
vhs record > demo.tape

# Edit the generated tape file as needed
# Then render it
vhs demo.tape
```

## Creating Effective PR Demos

### Demo Template for Bug Fixes

```tape
Output bugfix-demo.gif
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Dracula"
Set TypingSpeed 50ms

# Title
Type "# Demonstrating Bug Fix"
Enter
Sleep 1s

# Show the fix working
Type "your-command-here --with-args"
Enter
Sleep 2s

# Show expected output
Type "echo 'Bug is now fixed!'"
Enter
Sleep 2s
```

### Demo Template for New Features

```tape
Output feature-demo.gif
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Monokai Pro"
Set TypingSpeed 40ms

# Feature introduction
Type "# New Feature: Feature Name"
Enter
Sleep 1s

# Demonstrate usage
Type "new-command --help"
Enter
Sleep 2s

Type "new-command --option value"
Enter
Sleep 3s
```

## VHS Command Reference

### Settings

| Command | Description | Example |
|---------|-------------|---------|
| `Output <file>` | Output file (.gif, .mp4, .webm) | `Output demo.gif` |
| `Set FontSize <n>` | Font size in pixels | `Set FontSize 16` |
| `Set Width <n>` | Terminal width | `Set Width 800` |
| `Set Height <n>` | Terminal height | `Set Height 400` |
| `Set Theme "<name>"` | Color theme | `Set Theme "Dracula"` |
| `Set TypingSpeed <time>` | Delay per keystroke | `Set TypingSpeed 50ms` |
| `Set Padding <n>` | Frame padding | `Set Padding 20` |

### Actions

| Command | Description | Example |
|---------|-------------|---------|
| `Type "<text>"` | Type text | `Type "echo hello"` |
| `Enter` | Press Enter | `Enter` |
| `Sleep <time>` | Pause recording | `Sleep 2s` |
| `Ctrl+<key>` | Control sequence | `Ctrl+C` |
| `Hide` | Stop capturing frames | `Hide` |
| `Show` | Resume capturing frames | `Show` |

### Popular Themes

- `Dracula` - Dark purple theme (recommended)
- `Monokai Pro` - Vibrant colors
- `GitHub Dark` - GitHub-style dark
- `One Dark` - Atom-style
- `Nord` - Arctic blue tones

List all themes: `vhs themes`

## Publishing and Embedding in PRs

### Option 1: Publish to VHS Hosting (Easiest)

```bash
# Publish and get a shareable URL
vhs demo.tape --publish

# Returns URL like: https://vhs.charm.sh/vhs-xxxxx.gif
```

Then embed in PR description:
```markdown
## Demo

![Feature Demo](https://vhs.charm.sh/vhs-xxxxx.gif)
```

### Option 2: Commit to Repository

```bash
# Generate GIF
vhs demo.tape

# Add to repo (consider a docs/ or assets/ folder)
mkdir -p docs/demos
mv demo.gif docs/demos/

# Commit
git add docs/demos/demo.gif
git commit -m "Add demo GIF for feature X"
```

Then reference in PR:
```markdown
## Demo

![Feature Demo](docs/demos/demo.gif)
```

### Option 3: Upload to GitHub Issue/PR

1. Generate the GIF: `vhs demo.tape`
2. Drag-and-drop `demo.gif` into the PR description
3. GitHub auto-hosts the image

## Best Practices for PR Demos

### Keep It Short
- 5-15 seconds ideal
- Focus on the specific fix/feature
- Remove unnecessary typing delays

### Use Hide/Show for Setup

```tape
Output demo.gif
Set Theme "Dracula"

# Setup (not recorded)
Hide
Type "cd /path/to/project && make build"
Enter
Sleep 3s
Show

# Demo (recorded)
Type "./my-tool --demo"
Enter
Sleep 2s
```

### Add Context with Comments

```tape
# Comments are ignored in output but help maintain the tape file
# This demo shows the new --verbose flag working correctly

Type "mytool --verbose"
Enter
Sleep 2s
```

### Consistent Styling

For project consistency, save a base template:

```tape
# base-settings.tape
Set FontSize 16
Set Width 900
Set Height 500
Set Theme "Dracula"
Set TypingSpeed 50ms
Set Padding 20
```

Then source it:

```tape
Source base-settings.tape
Output my-demo.gif

Type "actual demo commands"
Enter
```

## Troubleshooting

### VHS Not Found
```bash
export PATH=$PATH:$(go env GOPATH)/bin
```

### ttyd Not Found
```bash
# Re-install ttyd
wget -qO- https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 > /tmp/ttyd
chmod +x /tmp/ttyd
sudo mv /tmp/ttyd /usr/local/bin/ttyd
```

### GIF Too Large
- Reduce dimensions: `Set Width 700` `Set Height 350`
- Reduce framerate: `Set Framerate 15`
- Shorten the demo
- Use `.webm` or `.mp4` for longer recordings

### Slow Recording
Ensure ffmpeg is installed: `sudo apt-get install -y ffmpeg`

## Example: Complete PR Demo Workflow

```bash
# 1. After fixing a bug or implementing a feature, create the tape
cat > pr-demo.tape << 'EOF'
Output pr-demo.gif
Set FontSize 16
Set Width 900
Set Height 450
Set Theme "Dracula"
Set TypingSpeed 40ms

Type "# Bug Fix: Issue #123 - Command now handles edge case"
Enter
Sleep 1s

Type "mytool process --input edge-case.txt"
Enter
Sleep 3s

Type "echo 'Success! No more crash.'"
Enter
Sleep 2s
EOF

# 2. Generate the GIF
vhs pr-demo.tape

# 3. Publish for easy embedding
vhs pr-demo.tape --publish
# Copy the returned URL

# 4. Add to PR description:
# ![Demo](https://vhs.charm.sh/vhs-xxxxx.gif)
```

## Additional Resources

- [VHS GitHub Repository](https://github.com/charmbracelet/vhs)
- [VHS Themes](https://github.com/charmbracelet/vhs/blob/main/THEMES.md)
- [VHS Examples](https://github.com/charmbracelet/vhs/tree/main/examples)
