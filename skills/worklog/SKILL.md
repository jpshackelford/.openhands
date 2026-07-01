# Daily Worklog Generator

Generate an HTML worklog of your OpenHands conversations with **LLM-synthesized deep understanding**, PR/issue links, and concrete outcomes.

## Quick Start

```bash
# Generate today's worklog (requires LLM API key)
python3 .agents/skills/worklog/generate_worklog.py

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

## Generated Output

Creates `/tmp/worklog.html` with:
- Modern, styled interface
- Clickable conversation titles → OpenHands Cloud
- Synthesized objectives (not raw quotes)
- Clickable PR and issue links → GitHub
- US Eastern Time display

## Files

- `generate_worklog.py` - Main worklog generator (token-efficient)
- `serve_worklog.py` - Simple HTTP server for viewing
- `SKILL.md` - This documentation

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
trigger: cron
schedule: "0 17 * * 1-5"  # 5 PM ET weekdays
task: |
  Generate and publish today's worklog:
  1. Run generate_worklog.py
  2. Serve on port 12000
  3. Notify via Slack (optional)
```

## Customization

**Change timezone**: Edit `et_tz = ZoneInfo('America/New_York')` in `generate_worklog.py`

**Adjust synthesis**: Edit `synthesize_goal()` function to add more patterns

**Style**: Modify CSS in HTML template section

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
