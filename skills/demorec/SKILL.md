---
name: demorec
description: Create professional demo recordings using demorec. This skill guides you through the complete demo creation process from message development to final recording. Use when asked to "record a demo", "create a video demo", "demonstrate this feature", or "create a PR demo".
triggers:
- demo recording
- record demo
- video demo
- demonstrate
- demorec
- create demo
- PR demo
- show this working
---

# Creating Professional Demos with demorec

demorec is a declarative tool for creating professional demo videos that seamlessly mix terminal and browser interactions—perfect for product demos, tutorials, and PR walkthroughs.

---

## Part 1: What Makes a Good Demo

### The Foundation: Problem → Solution → Impact

A good demo starts by describing:
1. **The problem solved** — What pain point or challenge does this address?
2. **Why it matters** — What's at stake if this problem goes unsolved?
3. **The positive impact** — What does the world look like with this solution in place?

Avoid flowery language, buzzwords, and unnecessary adjectives. Focus on clear, direct statements that deliver meaningful content.

### The Core Formula: WHO + WHAT + WOW

A great demo = **WHO** (specific user) + **WHAT** (outcome they achieve) + **WOW** (measurable differentiator)

### The 5 Rules

1. **Be specific about WHO** — Name a real user type, not "users" or "customers." Vague users = vague impact.

2. **Frame WHAT around outcomes, not features** — Describe what the user *achieves*, not what they *use*.

3. **Define success criteria** — What would a successful solution look like? Then show how your approach delivers it.

4. **Quantify the WOW** — If you can't measure the improvement, it's a wish, not a differentiator.

5. **Focus on one scenario** — One user, one problem, one win. A focused demo lands harder than a feature tour. Pick a scenario that illustrates the story in a single logical flow, not a list of disconnected features.

### Demo Structure: Tell → Show → Remind → Act

When you transition to the demo itself:

1. **Tell** — Tell the viewer what they're about to see and why it matters
2. **Show** — Describe what they're seeing as you show it
3. **Remind** — At wrap-up, remind the viewer what they just saw and how it ticks the boxes on what a successful solution looks like
4. **Act** — End with a call to action, not "thank you." What should the viewer do next? Try it? Sign up? Review the PR? Give them a clear next step.

### Examples

**✅ Good Demo Framing:**
> "A first-time homebuyer can identify and compare mortgage options that fit their budget **in under 5 minutes**, without needing to call a bank representative."

- **Who:** First-time homebuyer (specific)
- **What:** Identify and compare mortgage options fitting their budget
- **Wow:** Under 5 minutes, no phone call needed (measurable, differentiating)

**✅ Good Demo Framing:**
> "A procurement officer can respond to a supply chain disruption **within minutes instead of days**, with a complete impact analysis automatically generated."

- **Who:** Procurement officer
- **What:** Respond to supply chain disruption with impact analysis
- **Wow:** Minutes instead of days, automatic (measurable transformation)

**❌ Bad Demo Framing:**
> "Users can use our dashboard to view their data."

- Who is "users"? (too vague)
- What outcome? Just viewing? (not meaningful)
- No wow factor—what's differentiated or measurable?

**❌ Bad Demo Framing:**
> "We built a mobile app with push notifications."

- This is an *implementation*, not an outcome
- No user specified
- No measurable success criteria

### Quick Gut-Check Before You Demo

Before recording, ask yourself:

- Does it name a real user (not "users" or "customers")?
- Does it describe an outcome they *achieve*, not a feature they *use*?
- Could a competitor watch this and *not* immediately know your implementation?
- Can you measure whether you hit the "wow"?

**If you answer "no" to any of these, reframe it.**

---

## Part 2: The Demo Creation Process

Creating an effective demo is a structured process. Follow these steps:

### Step 1: Determine Your Message

Before writing any script, clearly define:
- **What is the one key takeaway?** Your audience should leave with a single, clear understanding.
- **Who is your audience?** Technical users, stakeholders, or end users?
- **What problem does this solve?** Frame the demo around the value proposition.

### Step 2: Develop a High-Level Script

Write out the narrative flow in plain language before any technical implementation:

1. **Opening** - Hook the viewer. State the problem or goal.
2. **Context** - Brief background (keep minimal).
3. **Demonstration** - The core action sequence.
4. **Resolution** - Show the successful outcome.
5. **Closing** - Reinforce the key message.

Example outline:
```
Opening: "Today I'll show you how [feature] solves [problem]"
Context: "Previously, users had to [old way]. Now..."
Demo: [sequence of actions showing the feature]
Result: "As you can see, [outcome]"
Closing: "This makes [benefit] possible for [audience]"
```

### Step 3: Review Script for Flow and Impact

Before any technical work:

- **Read aloud** - Does it sound natural?
- **Time it** - Is it too long? Aim for concise (1-3 minutes for most demos).
- **Check transitions** - Do ideas flow logically?
- **Verify impact** - Does every section serve the message?
- **Cut ruthlessly** - Remove anything that doesn't directly support the message.

### Step 4: Create Presentation Materials (If Required)

Some demos benefit from slides or visual aids:

- Title/intro slides
- Architecture diagrams
- Before/after comparisons
- Summary slides

demorec supports Marp presentations with `@mode presentation`:

```tape
@mode presentation "slides.md"
Set Theme "openhands"
Slide 1 4s
```

### Step 5: Practice Commands and Motions

Before writing the demorec script:

1. **Execute the full sequence manually** - Identify timing, gotchas, and edge cases.
2. **Note exact commands** - Copy the precise commands you'll use.
3. **Time each action** - How long does each step take?
4. **Plan pauses** - Where should viewers have time to absorb?
5. **Identify highlight moments** - What should draw attention?

### Step 6: Write the demorec File

Now translate your practiced sequence into a `.demorec` script:

```tape
Output my-demo.mp4
Set Width 1280
Set Height 720

# @voice edge:jenny

@mode terminal
Set Theme "Dracula"

# @narrate:before "Let's see how this feature works."
Type "my-command --flag"
Enter
Sleep 2s
```

See [Technical Reference](#technical-reference) below for full command syntax.

### Step 7: Preview, Revise, and Preview Again

Use the preview command to iterate without full video rendering:

```bash
# Preview with verification
demorec preview script.demorec --rows 30

# Preview with frame capture for debugging
demorec preview script.demorec --rows 30 -o ./frames
```

**Iterate until satisfied:**
1. Preview the execution
2. Check timing and pacing
3. Verify narration placement
4. Adjust and preview again
5. Repeat until the flow feels right

### Step 8: Record the Final Video

Once preview looks good:

```bash
demorec record my-demo.demorec
```

This generates:
- `my-demo.mp4` - The video file
- `my-demo.srt` - Subtitles (if narration is used)

### Step 9: Post in PR or Applicable Location

For PR demos:
- Upload to GitHub (drag into PR description or comment)
- Include in release notes
- Link in documentation

For other uses:
- Share via appropriate channel (Slack, documentation site, etc.)
- Consider accessibility (subtitles, transcripts)

---

## Part 3: Technical Reference

### Installation

```bash
# With uv (recommended)
uv tool install demorec

# Or with pip
pip install demorec

# Install browser dependencies
demorec install
```

### System Dependencies

demorec requires several system dependencies beyond Python packages:

```bash
# Install Playwright browsers (required for all recording)
playwright install --with-deps chromium

# Install ttyd for terminal recording (real PTY support)
wget -qO /tmp/ttyd https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64
chmod +x /tmp/ttyd
sudo mv /tmp/ttyd /usr/local/bin/ttyd
ttyd --version

# Install ffmpeg for video processing and vim for code review demos
sudo apt-get update && sudo apt-get install -y vim ffmpeg
```

**Summary of dependencies:**
| Dependency | Purpose |
|------------|---------|
| Playwright + Chromium | Browser automation and screen capture (terminal + browser modes) |
| ttyd | Real PTY support for terminal recording (actual shell execution) |
| ffmpeg | Video segment concatenation, audio mixing, subtitle embedding |
| vim | Code review demos with syntax highlighting |

### CLI Commands

```bash
# Record a demo
demorec record my-demo.demorec

# Record with options
demorec record my-demo.demorec -o output.mp4 --voice adam

# Validate syntax without recording
demorec validate my-demo.demorec

# Preview without recording video
demorec preview my-demo.demorec --rows 30

# Calculate vim stage directions for highlighting
demorec stage --rows 30 --highlights "6-8,27-35"

# List available TTS voices
demorec voices

# Show version
demorec --version
```

### Script Syntax

#### Global Settings

```tape
Output filename.mp4       # Output filename
Set Width 1280            # Video width in pixels
Set Height 720            # Video height in pixels
```

#### Mode Switching

```tape
@mode terminal            # Switch to terminal mode (default session)
@mode browser             # Switch to browser mode
@mode presentation "slides.md"  # Switch to presentation mode
```

#### Named Terminal Sessions

Use named sessions for multi-terminal demos (e.g., server + client):

```tape
@mode terminal            # Default terminal session
@mode terminal:server     # Named session "server"
@mode terminal:client     # Named session "client"
```

Each named session is independent and persistent. Switch between them freely—state is preserved.

#### Terminal Commands

```tape
Set Theme "Dracula"       # Set terminal theme
Type "command"            # Type text
Enter                     # Press Enter
Sleep 2s                  # Wait 2 seconds
Ctrl+C                    # Key combination
Escape                    # Press Escape
```

#### Browser Commands

```tape
Navigate "https://example.com"   # Go to URL
Click "#selector"                # Click element
Type "#input" "text"             # Type into element
Fill "#input" "text"             # Fill instantly (no typing animation)
Press "Enter"                    # Press key
Sleep 2s                         # Wait
Wait "#element"                  # Wait for element to appear
Scroll "down" 200                # Scroll page
Hover "#element"                 # Hover over element
Highlight "#element"             # Highlight element
Unhighlight "#element"           # Remove highlight
Screenshot "filename.png"        # Take screenshot
```

#### Presentation Commands

```tape
Slide 1 4s                # Show slide 1 for 4 seconds
Slide 2                   # Show slide 2 (default duration)
```

#### Narration

```tape
# @voice edge:jenny                          # Set voice
# @narrate:before "Text to speak"            # Speak, then action
# @narrate:during "Text to speak"            # Speak during action
# @narrate:after "Text to speak"             # Action, then speak
```

### Best Practices for demorec Scripts

#### Persistent Sessions

Terminal sessions persist across mode switches. You can:
- Set up environment variables in terminal, switch to browser, and return to terminal with state intact
- Run a server in one terminal, view it in browser, make requests from another terminal
- Maintain working directory and shell history across the entire demo

This eliminates the need to repeat setup commands when switching modes.

#### Named Sessions for Multi-Terminal Demos

Common patterns:

| Pattern | Sessions | Use Case |
|---------|----------|----------|
| Server + Client | `terminal:server`, `terminal:client` | API demos, network tools |
| Build + Run | `terminal:build`, `terminal:run` | CI/CD demos, compilation |
| Edit + Test | `terminal:editor`, `terminal:test` | Development workflow demos |

#### Terminal Size Control

Use the preview rows setting to control visible lines:

```bash
demorec preview script.demorec --rows 30
```

#### Vim Highlighting in Code Reviews

For vim-based code review demos, use the stage command to calculate navigation:

```bash
demorec stage --rows 30 --highlights "6-8,11-16,27-35"
```

This outputs optimal vim commands:
```
Block 1: lines 6-8 (3 lines)
  Goto:      6G
  Center:    zz
  Select:    V8G
```

#### Narration Timing

| Scenario | Directive | Example |
|----------|-----------|---------|
| Announce what you'll do | `@narrate:before` | "Let's scroll to the API methods" |
| Describe what's visible | `@narrate:after` | "Here's the User dataclass with four fields" |
| Explain during action | `@narrate:during` | Background explanation while typing |

### Sample demorec Files

#### Simple Terminal Demo

```tape
# hello.demorec
Output hello.mp4
Set Width 1280
Set Height 720

@mode terminal
Set Theme "Dracula"

Type "echo 'Hello from demorec!'"
Enter
Sleep 2s

Type "ls -la"
Enter
Sleep 2s
```

#### Terminal + Browser Mixed Demo

```tape
# mixed.demorec
Output mixed-demo.mp4
Set Width 1280
Set Height 720

# ─── TERMINAL: Start server ───
@mode terminal
Set Theme "Dracula"

Type "python -m http.server 8000 &"
Enter
Sleep 2s

# ─── BROWSER: Show result ───
@mode browser

Navigate "http://localhost:8000"
Sleep 2s

Highlight "h1"
Sleep 2s
```

#### Narrated Code Review

```tape
# code-review.demorec
Output code-review.mp4
Set Width 1280
Set Height 720

# @voice edge:jenny

@mode terminal
Set Theme "Dracula"

# @narrate:before "Let's review the changes in this pull request."
Type "vim src/main.py"
Enter
Sleep 1s

Type ":set number"
Enter
Sleep 0.5s

# Go to the changed function
Type "27G"
Sleep 0.3s
Type "zt"
Sleep 0.3s
Type "V"
Type "35G"
Sleep 0.5s

# @narrate:after "This function now handles edge cases properly."
Sleep 1s

Escape
Type ":q!"
Enter

# @narrate:after "That covers the key changes in this PR."
Sleep 1s
```

#### Multi-Terminal Server + Client Demo

```tape
# server-client.demorec
Output server-client-demo.mp4
Set Width 1280
Set Height 720

# @voice edge:jenny

# ─── Set up environment in default terminal ───
@mode terminal
# @narrate:before "Let's set up our environment first."
Type "export API_KEY='secret-token-xyz'"
Enter
Sleep 500ms
Type "echo 'API Key configured:' $API_KEY"
Enter
Sleep 1s

# ─── Start server in named session ───
@mode terminal:server
# @narrate:before "Now let's start our server in a separate terminal."
Type "cd /tmp && echo '<h1>Hello!</h1>' > index.html"
Enter
Sleep 500ms
Type "python3 -m http.server 8080"
Enter
Sleep 2s

# ─── View in browser ───
@mode browser
# @narrate:before "Let's see the server in the browser."
Navigate "http://localhost:8080"
Sleep 2s

# ─── Make requests from client terminal ───
@mode terminal:client
# @narrate:before "Now let's make requests from a client terminal."
Type "curl http://localhost:8080/"
Enter
Sleep 1s

# ─── Back to server - show logs ───
@mode terminal:server
# @narrate:after "Notice the request logs in the server terminal."
Sleep 2s
Ctrl+C
Sleep 500ms

# ─── Original terminal state preserved ───
@mode terminal
# @narrate:before "And our original terminal still has its state."
Type "echo $API_KEY"
Enter
Sleep 1s
# @narrate:after "Environment preserved across all mode switches!"
```

#### Presentation with Live Demo

```tape
# presentation.demorec
Output presentation.mp4
Set Width 1920
Set Height 1080

# @voice edge:jenny

# ─── INTRO SLIDES ───
@mode presentation "intro.md"
Set Theme "default"

# @narrate:during "Welcome to this feature overview."
Slide 1 4s

# ─── LIVE DEMO ───
@mode terminal
Set Theme "Dracula"

# @narrate:before "Let me show you how it works."
Type "myapp demo"
Enter
Sleep 3s

# ─── CLOSING ───
@mode presentation "intro.md"

# @narrate:during "Try it yourself at example.com/demo"
Slide 10 4s
```

### Troubleshooting

#### Common Issues

1. **PS1JSON artifacts in OpenHands**: demorec automatically cleans these.

2. **Browser not launching**: Run `demorec install` to set up Playwright browsers.

3. **Narration not playing**: Ensure `ELEVENLABS_API_KEY` is set for premium voices, or use `edge:` voices which are free.

4. **Video dimensions mismatch**: Use consistent `Set Width` and `Set Height` across all modes.

#### Debugging with Frames

Capture frame-by-frame output for debugging:

```bash
demorec preview script.demorec --rows 30 -o ./frames
```

This saves terminal state as `.txt` files and browser state as `.png` files at each step.

---

## Resources

- **Repository**: [jpshackelford/demorec](https://github.com/jpshackelford/demorec)
- **Examples**: See the `examples/` directory in the repo
- **Project Context**: `docs/PROJECT_CONTEXT.md` for architecture details
