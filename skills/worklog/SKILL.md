# Daily Worklog Generator

Generate an HTML worklog of your OpenHands conversations with synthesized objectives, PR/issue links, and concrete outcomes.

## Quick Start

```bash
# Generate today's worklog
python3 .agents/skills/worklog/generate_worklog.py

# Serve on port 12000
python3 .agents/skills/worklog/serve_worklog.py &

# View at https://work-1-tahhvksgnhffxrqu.prod-runtime.all-hands.dev/
```

## What It Does

**Analyzes each conversation** from today to determine:
- 🎯 **Objective**: What you were trying to achieve (synthesized, not quoted)
- ✅ **Outcomes**: PRs opened, issues filed, with clickable links
- 🕐 **Time**: When the conversation started (US Eastern Time)

**Token-efficient design**:
- Single API call to list conversations
- Batched event fetching (2-3 API calls per conversation)
- Lightweight objective synthesis from user messages
- Automatic PR/issue link extraction

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

Requires:
- `OH_API_KEY` - OpenHands Cloud API key
- Python 3.9+ with `zoneinfo` support

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
- 1 call to get user messages (limit 10)
- 1 call to get finish message
- 0 calls if conversation has no user messages

**Total for 20 conversations**: ~40 API calls, ~2-3K tokens

Compare to full event inspection: ~200 API calls, ~50K tokens
