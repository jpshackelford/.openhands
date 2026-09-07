# WebTape - VHS-like Browser Recording Tool

A proof of concept for creating declarative web app demo videos, inspired by [charmbracelet/vhs](https://github.com/charmbracelet/vhs).

## Overview

WebTape lets you write browser automation scripts in a simple declarative DSL (similar to VHS `.tape` files) that can be rendered into video demos. Perfect for:

- Creating product demos
- Recording bug reproductions
- Generating tutorial videos
- Testing web applications visually

## Installation

```bash
pip install playwright
playwright install chromium
pip install imageio-ffmpeg  # For video conversion
```

## Quick Start

1. Create a `.webtape` file:

```tape
Output my_demo.mp4
Set Width 1280
Set Height 720
Set TypingSpeed 60ms

Navigate "http://localhost:3000"
Sleep 1s

Click "#login-btn"
Type "#email" "user@example.com"
Type "#password" "secret123"
Click "button[type=submit]"
Sleep 2s
```

2. Run WebTape:

```bash
python webtape.py my_demo.webtape -v
```

## DSL Reference

### Configuration

| Command | Description | Example |
|---------|-------------|---------|
| `Output <file>` | Output file (.mp4, .webm, .gif) | `Output demo.mp4` |
| `Set Width <n>` | Browser width in pixels | `Set Width 1280` |
| `Set Height <n>` | Browser height in pixels | `Set Height 720` |
| `Set TypingSpeed <time>` | Delay per keystroke | `Set TypingSpeed 50ms` |
| `Set Framerate <n>` | Video framerate | `Set Framerate 30` |

### Actions

| Command | Description | Example |
|---------|-------------|---------|
| `Navigate "url"` | Navigate to URL | `Navigate "https://example.com"` |
| `Click "selector"` | Click an element | `Click "#submit-btn"` |
| `Type "selector" "text"` | Type text into element | `Type "#email" "user@test.com"` |
| `Fill "selector" "text"` | Fill input instantly | `Fill "#name" "John Doe"` |
| `Press "key"` | Press a keyboard key | `Press "Enter"` |
| `Sleep <time>` | Pause for duration | `Sleep 2s` or `Sleep 500ms` |
| `Wait "selector"` | Wait for element to appear | `Wait ".loading-done"` |
| `Scroll "dir" <amount>` | Scroll the page | `Scroll "down" "300"` |
| `Hover "selector"` | Hover over element | `Hover ".tooltip-trigger"` |
| `Highlight "selector"` | Add red outline to element | `Highlight "#important"` |
| `Unhighlight "selector"` | Remove highlight | `Unhighlight "#important"` |
| `Screenshot "file"` | Save screenshot | `Screenshot "step1.png"` |

### Narration (Voice-Over)

Add AI narration using special comment macros:

```tape
# @voice eleven:rachel

# @narrate:before "Welcome to the demo."
Navigate "https://example.com"

# @narrate:during "Watch as I fill in the form."
Type "#email" "user@example.com"

# @narrate:after "That completes the setup."
Click "#submit"
```

| Macro | Behavior |
|-------|----------|
| `# @voice eleven:<name>` | Set ElevenLabs voice |
| `# @narrate:before "text"` | Speak first, then run action |
| `# @narrate:during "text"` | Speak while action runs |
| `# @narrate:after "text"` | Run action, then speak |

## Comparison with Terminal Recording (VHS)

| Feature | VHS (Terminal) | WebTape (Browser) |
|---------|----------------|-------------------|
| Target | CLI applications | Web applications |
| Engine | ttyd + chromium | Playwright |
| DSL | `.tape` files | `.webtape` files |
| Output | GIF, MP4, WebM | MP4, WebM, GIF |
| Voice-Over | ElevenLabs TTS | ElevenLabs TTS |
| Selectors | N/A | CSS selectors |

## Architecture

```
.webtape file
    │
    ▼
WebTapeParser ──► Config + Actions
    │
    ▼
WebTapeRunner ──► Playwright (headless)
    │                  │
    ▼                  ▼
Narration      Video Recording
(ElevenLabs)   (browser context)
    │                  │
    └──────┬───────────┘
           ▼
       Final Video
      (with audio)
```

## Future Enhancements

- [ ] Full ElevenLabs TTS integration
- [ ] Audio mixing with video
- [ ] GIF output support
- [ ] Mouse cursor visualization
- [ ] Page transitions/animations
- [ ] Multi-page flows
- [ ] Environment variables in scripts
- [ ] Include/source other webtape files
- [ ] Recording existing browser sessions (codegen mode)

## Related Projects

- [charmbracelet/vhs](https://github.com/charmbracelet/vhs) - Terminal GIF recorder (inspiration)
- [Playwright](https://playwright.dev/) - Browser automation
- [rrweb](https://www.rrweb.io/) - Web session recording/replay

## License

MIT
