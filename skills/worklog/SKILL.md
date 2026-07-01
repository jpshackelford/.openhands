# Daily Worklog Generator

Generate a worklog of your OpenHands conversations with **LLM-synthesized deep understanding**, PR/issue links, and concrete outcomes. Supports multiple output formats: **text**, **markdown**, and **HTML**.

## 🎯 Agent Guidance: Handling Worklog Requests

When a user asks for a worklog, determine their intent:

**Clear Intent Indicators:**
- "show me my worklog" / "what did I work on today" → **Text to stdout**
- "create a worklog dashboard" / "host my worklog" → **HTML + serve**
- "generate worklog for documentation" / "add to my notes" → **Markdown**

**If Ambiguous:**
Ask the user:
> "Would you like me to:
> 1. Show you the worklog directly (text output)
> 2. Create an HTML dashboard you can view in browser
> 3. Generate markdown for documentation
> 
> Let me know which format works best for you."

**Default Behavior:**
- If user seems to want a quick answer → Use text format with `--stdout`
- If user mentions "hosting", "serving", "dashboard", or "browser" → Use HTML + serve
- If user mentions "document", "save", or "file" → Use markdown

## When to Use What Format

- 📝 **Text output** (`--format text --stdout`): Direct response to user, quick summary, copy-paste into chat
- 📄 **Markdown output** (`--format markdown`): Documentation, notes, GitHub/Notion integration
- 🌐 **HTML output** (`--format html` + serve): Visual dashboard, browser viewing, presentations

## Quick Start

### For Direct User Response (Text)
```bash
# Print today's worklog to stdout as text
python3 .agents/skills/worklog/generate_worklog.py --format text --stdout

# Or save to file
python3 .agents/skills/worklog/generate_worklog.py --format text -o /tmp/worklog.txt
```

### For Documentation (Markdown)
```bash
# Generate markdown worklog
python3 .agents/skills/worklog/generate_worklog.py --format markdown -o ~/worklog.md
```

### For Visual Dashboard (HTML)
```bash
# Generate HTML worklog
python3 .agents/skills/worklog/generate_worklog.py --format html

# Serve on port 12000
python3 .agents/skills/worklog/serve_worklog.py &

# View at https://work-1-tahhvksgnhffxrqu.prod-runtime.all-hands.dev/
```

## What It Does

**Uses LLM to deeply understand each conversation**:
- 🎯 **Synthesized Purpose**: What problem you were solving, why it matters, what was accomplished, what's left
- 🔗 **PR/Issue Links**: Automatically extracted with numbers (PR #123, Issue #456)
- ✅ **Concrete Outcomes**: Clickable links to PRs and issues
- 🕐 **Time**: When the conversation started (US Eastern Time)

**Real synthesis, not quoting**:
- LLM analyzes user messages, agent responses, and GitHub PR/issue descriptions
- Generates 1-2 clear sentences explaining the real work
- No raw quotes or markdown fragments
- Answers: What? Why? What was done? What's left?

## Output Formats

### Text Format
Plain text output suitable for:
- Direct agent responses to users
- Quick copy-paste summaries
- Terminal viewing
- Slack/chat messages

### Markdown Format  
Structured markdown suitable for:
- Documentation files
- GitHub README sections
- Notion pages
- Wiki entries
- Version control

### HTML Format
Rich visual dashboard suitable for:
- Browser viewing
- Presentations
- Hosted worklog servers
- Team sharing

All formats include:
- Synthesized objectives (not raw quotes)
- Clickable PR and issue links
- US Eastern Time display
- Conversation IDs and links

## Files

- `generate_worklog.py` - Main worklog generator with format support
- `serve_worklog.py` - Simple HTTP server for viewing HTML output
- `SKILL.md` - This documentation

## Command-Line Options

```bash
python3 .agents/skills/worklog/generate_worklog.py [options]

Options:
  --format {text,markdown,html}  Output format (default: html)
  --output PATH, -o PATH         Output file path (default: /tmp/worklog.{ext})
  --stdout                       Print to stdout instead of file
  --date-offset N                Days offset from today (0=today, -1=yesterday)
  --timezone TZ                  IANA timezone name (default: America/New_York)
```

### Examples

```bash
# Generate yesterday's worklog as text to stdout
python3 .agents/skills/worklog/generate_worklog.py --format text --stdout --date-offset -1

# Generate markdown for documentation
python3 .agents/skills/worklog/generate_worklog.py --format markdown -o ~/docs/worklog-$(date +%Y-%m-%d).md

# Generate HTML with custom timezone
python3 .agents/skills/worklog/generate_worklog.py --format html --timezone "Europe/London"
```

## Environment

**Required:**
- `OH_API_KEY` - OpenHands Cloud API key
- `LITELLM_PROXY_KEY` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM API key for synthesis
- Python 3.9+ with `zoneinfo` support

**Optional:**
- `GITHUB_TOKEN` - For fetching PR/issue descriptions (highly recommended)
- `LITELLM_ENDPOINT_URL` - LiteLLM endpoint (default: OpenAI)
- `SYNTHESIS_MODEL` - Model for synthesis (default: `gpt-4o-mini`)

## Usage in Automation

For daily worklogs, run via OpenHands automation:

```yaml
# Text summary to Slack
trigger: cron
schedule: "0 17 * * 1-5"  # 5 PM ET weekdays
task: |
  Generate text worklog and post to Slack:
  1. Run: python3 .agents/skills/worklog/generate_worklog.py --format text --stdout
  2. Post output to #daily-worklogs channel

# HTML dashboard
trigger: cron
schedule: "0 17 * * 1-5"
task: |
  Generate and serve HTML worklog:
  1. Run: python3 .agents/skills/worklog/generate_worklog.py --format html
  2. Serve: python3 .agents/skills/worklog/serve_worklog.py
  3. Share link to team
```

## Customization

**Change timezone**: Use `--timezone` flag (e.g., `--timezone "Europe/London"`)

**Adjust synthesis**: Edit `synthesize_title_and_purpose()` function to modify LLM prompts

**HTML style**: Modify CSS in `generate_html_header()` function

**Output format**: All renderers (`render_text`, `render_markdown`, `render_html`) can be customized

## Objective Synthesis Logic

Detects intent from user messages:
- **Merge/rebase** → "Rebase and resolve merge conflicts in PR #X"
- **File issue** → "File GitHub issues for identified bugs/improvements"  
- **Debug** → Contextual description based on keywords
- **Clone** → "Clone and examine X repository"
- **Investigation** → Question-based objective

Extracts entities:
- PR numbers from `#123` or `/pull/123`
- GitHub PR/issue URLs
- Repository names from `OpenHands/repo-name`

## Token Efficiency

**Per conversation**:
- Data gathering: 2-3 OpenHands API calls (user messages, agent messages, finish message)
- GitHub API: 0-2 calls for PR/issue details (if GITHUB_TOKEN set)
- LLM synthesis: 1 call (~300-500 tokens) for title + purpose generation

**Total for 20 conversations**: 
- ~60-80 OpenHands API calls
- ~8-12K tokens (including LLM synthesis)
- **Still 4-5x cheaper** than full event inspection (~50K tokens)

**Key advantage**: Real understanding vs. raw event data
