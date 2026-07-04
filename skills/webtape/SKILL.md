---
name: webtape
description: Create declarative browser demo videos with AI voice-over, similar to VHS for terminal recordings. Use when the user wants to record a web app demo, create a browser tutorial video, generate product demos with narration, or needs to automate web recording with Playwright.
triggers:
  - webtape
  - browser recording
  - web demo
  - web video
  - browser demo
  - playwright recording
  - web app demo
  - narrated browser demo
---

# WebTape - Browser Demo Recording

Create professional web application demo videos using a declarative DSL, inspired by [charmbracelet/vhs](https://github.com/charmbracelet/vhs).

## Quick Start

### Installation (already available in OpenHands sandbox)

```bash
pip install playwright imageio-ffmpeg
playwright install chromium
```

### Create a .webtape file

```tape
Output my-demo.mp4
Set Width 1280
Set Height 720
Set TypingSpeed 60ms

# @voice eleven:rachel

Navigate "http://localhost:3000"
Sleep 1s

# @narrate:before "Welcome to our product demo."
Click "#get-started"
Sleep 500ms

# @narrate:during "Let me fill in the registration form."
Type "#email" "user@example.com"
Type "#password" "secret123"
Sleep 1s

# @narrate:after "Now let's submit and see the dashboard."
Click "button[type=submit]"
Sleep 2s
```

### Run WebTape

```bash
cd /path/to/webtape
python webtape.py demo.webtape -v
```

## DSL Reference

### Configuration Commands

| Command | Description | Example |
|---------|-------------|---------|
| `Output <file>` | Output filename (.mp4, .webm) | `Output demo.mp4` |
| `Set Width <n>` | Browser width in pixels | `Set Width 1280` |
| `Set Height <n>` | Browser height in pixels | `Set Height 720` |
| `Set TypingSpeed <time>` | Delay per keystroke | `Set TypingSpeed 50ms` |
| `Set Framerate <n>` | Video framerate | `Set Framerate 30` |

### Browser Actions

| Command | Description | Example |
|---------|-------------|---------|
| `Navigate "url"` | Navigate to URL | `Navigate "https://example.com"` |
| `Click "selector"` | Click an element | `Click "#submit-btn"` |
| `Type "selector" "text"` | Type text with visual delay | `Type "#email" "user@test.com"` |
| `Fill "selector" "text"` | Fill input instantly | `Fill "#name" "John Doe"` |
| `Press "key"` | Press keyboard key | `Press "Enter"` |
| `Sleep <time>` | Pause for duration | `Sleep 2s` or `Sleep 500ms` |
| `Wait "selector"` | Wait for element | `Wait ".loading-done"` |
| `Scroll "dir" <amount>` | Scroll page | `Scroll "down" "300"` |
| `Hover "selector"` | Hover over element | `Hover ".tooltip-trigger"` |
| `Highlight "selector"` | Add red outline | `Highlight "#important"` |
| `Unhighlight "selector"` | Remove highlight | `Unhighlight "#important"` |
| `Screenshot "file"` | Save screenshot | `Screenshot "step1.png"` |

### Narration (AI Voice-Over)

WebTape supports AI-generated voice-over using ElevenLabs TTS.

#### Set the voice

```tape
# @voice eleven:rachel
```

Available voices: `rachel`, `adam`, `josh`, `bella`, `antoni`, `domi`, `elli`, `arnold`, `sam`, `nicole`

#### Add narration to actions

```tape
# @narrate:before "This text is spoken before the action."
Click "#button"

# @narrate:during "This is spoken while the action runs."
Type "#input" "Hello World"

# @narrate:after "This is spoken after the action completes."
Navigate "https://example.com"
```

| Macro | Behavior |
|-------|----------|
| `# @narrate:before "text"` | Speak first, then execute action |
| `# @narrate:during "text"` | Speak while action executes |
| `# @narrate:after "text"` | Execute action, then speak |

### Environment Variables

- `ELEVENLABS_API_KEY` - Required for TTS narration

## CLI Options

```bash
python webtape.py [OPTIONS] TAPEFILE

Options:
  -v, --verbose       Verbose output
  -o, --output FILE   Override output filename
  --no-narration      Disable TTS (video only)
  --voice NAME        Override voice (e.g., rachel, adam)
  --list-voices       List available TTS voices
```

## Example: Product Demo

```tape
Output product-demo.mp4
Set Width 1920
Set Height 1080
Set TypingSpeed 50ms

# @voice eleven:adam

# @narrate:before "Welcome to our product walkthrough."
Navigate "https://myapp.example.com"
Sleep 2s

# @narrate:before "First, let's sign up for an account."
Click "a.signup"
Sleep 1s

Highlight "#email"
Sleep 500ms

# @narrate:during "I'll enter my email address."
Type "#email" "demo@example.com"
Unhighlight "#email"
Sleep 500ms

Type "#password" "SecurePass123!"
Sleep 500ms

# @narrate:before "Now I'll click the create account button."
Click "#create-account"
Sleep 3s

# @narrate:after "And that's how easy it is to get started!"
Sleep 2s
```

## Example: Bug Fix Demo for PR

```tape
Output bugfix-demo.mp4
Set Width 1280
Set Height 720

Navigate "http://localhost:3000"
Sleep 1s

# @narrate:before "This demo shows the fix for issue number 42."

# Show the problematic flow
Click "#trigger-bug"
Sleep 2s

# @narrate:after "As you can see, the error no longer occurs."
Sleep 1s
```

## Comparison with Terminal Recording (VHS)

| Feature | VHS (Terminal) | WebTape (Browser) |
|---------|----------------|-------------------|
| Target | CLI applications | Web applications |
| Engine | ttyd + chromium | Playwright |
| DSL | `.tape` files | `.webtape` files |
| Output | GIF, MP4, WebM | MP4, WebM |
| Voice-Over | ElevenLabs TTS | ElevenLabs TTS |
| Selectors | N/A | CSS selectors |

## Troubleshooting

### Browser won't launch

```bash
# Ensure Playwright browsers are installed
playwright install chromium
```

### No audio in video

- Check `ELEVENLABS_API_KEY` is set
- Use `--verbose` to see TTS generation logs
- Try `--list-voices` to verify API connection

### Video too large

- Reduce resolution: `Set Width 1280` `Set Height 720`
- Use `.webm` format for smaller files
- Shorten pauses with smaller `Sleep` values

### Element not found

- Use `Wait "selector"` before interacting
- Verify selector with browser dev tools
- Add `Sleep` after navigation for page load

## Architecture

```
.webtape file
    │
    ▼
WebTapeParser ──► Config + Actions
    │
    ▼
WebTapeRunner
    │
    ├──► Playwright (headless browser)
    │         │
    │         ▼
    │    Video Recording
    │
    └──► ElevenLabs TTS
              │
              ▼
         Audio Segments
              │
    ──────────┴──────────
              │
              ▼
         FFmpeg Mixing
              │
              ▼
        Final Video (MP4)
```

## Files

- `webtape.py` - Main CLI tool
- `scripts/tts.py` - ElevenLabs TTS integration
- `scripts/__init__.py` - Module exports

## See Also

- [VHS (Terminal Recording)](https://github.com/charmbracelet/vhs)
- [Playwright Documentation](https://playwright.dev/python/)
- [ElevenLabs API](https://elevenlabs.io/docs)
