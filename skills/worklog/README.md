# 📋 Daily Worklog Skill

LLM-powered worklog generator for OpenHands conversations with **deep synthesized understanding** and PR/issue links.

## Quick Start

```bash
# Generate today's worklog and start server
bash .agents/skills/worklog/run_worklog.sh

# Or run components separately:
python3 .agents/skills/worklog/generate_worklog.py
python3 .agents/skills/worklog/serve_worklog.py &
```

**View at:** https://work-1-tahhvksgnhffxrqu.prod-runtime.all-hands.dev/

## What It Generates

For each conversation today, the worklog shows:

- **🎯 Synthesized Purpose**: LLM-generated understanding of what problem was being solved, why it matters, what was accomplished, and what's left
- **🔗 PR/Issue Links**: Clickable links with numbers (PR #123: Title)
- **✅ Outcomes**: All PRs and issues with state indicators (→ open, ✓ closed)
- **🕐 Time**: When the conversation started (US Eastern Time)
- **📋 Link**: Direct link to conversation in OpenHands Cloud

## Token Efficiency

**Per 20 conversations: ~8-12K tokens**

Compare to full event inspection: ~50K tokens (4-5x more expensive!)

### How It Works

1. **Gather context** (efficient, no LLM):
   - Batch fetch all conversations from today (1 API call)
   - Per conversation: user messages, agent messages, finish message (2-3 calls)
   - Fetch PR/issue details from GitHub API (0-2 calls if GITHUB_TOKEN set)

2. **Synthesize with LLM** (gpt-4o-mini by default):
   - Send gathered context to LLM with clear examples
   - LLM generates title and 1-2 sentence purpose
   - Understands real work, not just actions taken
   - ~300-500 tokens per conversation

3. **Generate HTML**: Modern, responsive UI with all synthesized insights

## Features

### LLM-Powered Synthesis

Uses an LLM (gpt-4o-mini by default) to truly understand each conversation:

**What it analyzes:**
- User messages: What you asked for
- Agent messages: What the agent understood and did
- Finish messages: What was accomplished
- PR/issue descriptions: What the actual work is about

**What it generates:**
- **Title**: Clear 5-10 word description of the real work
- **Purpose**: 1-2 sentences answering:
  - What problem was being solved?
  - Why does it matter?
  - What was accomplished?
  - What's left unfinished?

**Example:**
- ❌ Bad (quoting): "Working on: > **Stacked on #14937**..."
- ✅ Good (synthesis): "Adding super-admin management endpoints to enable programmatic grant/revoke of admin privileges in the enterprise auth system. Implementation complete and pushed for review."

### Link Extraction

Automatically finds and makes clickable:
- GitHub PR URLs → `[PR #123] (repo-name)`
- GitHub Issue URLs → `[Issue #456] (repo-name)`
- Multiple issues → Shows count + first 3 links

### Styling

Modern, responsive design with:
- Gradient header
- Hover effects on conversations
- Color-coded outcomes (green = success)
- Mobile-friendly layout

## Files

```
.agents/skills/worklog/
├── SKILL.md            # Skill documentation
├── README.md           # This file
├── generate_worklog.py # Main generator (token-efficient)
├── serve_worklog.py    # HTTP server
└── run_worklog.sh      # Convenience script (both)
```

## Environment

**Required:**
- `OH_API_KEY` - OpenHands Cloud API key (auto-injected)
- `LITELLM_PROXY_KEY` or `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - LLM API key for synthesis

**Optional:**
- `GITHUB_TOKEN` - For fetching PR/issue descriptions (highly recommended)
- `LITELLM_ENDPOINT_URL` - LiteLLM endpoint (default: OpenAI)
- `SYNTHESIS_MODEL` - Model for synthesis (default: `gpt-4o-mini`)
- Change timezone: Edit `ZoneInfo('America/New_York')` in generator
- Change port: Edit `PORT = 12000` in server

## Examples

### Daily Worklog (Default)

```bash
python3 .agents/skills/worklog/generate_worklog.py
# Generates worklog for today (US Eastern timezone)
```

### Custom Date (for testing)

```python
# Edit generate_worklog.py temporarily:
# Change: today_et_start = now_et.replace(...)
# To:     today_et_start = now_et.replace(...) - timedelta(days=1)
```

### Automation (Cron)

Run daily at 5 PM ET on weekdays:

```yaml
# OpenHands Automation
trigger: cron
schedule: "0 17 * * 1-5"
task: |
  cd /workspace/project
  python3 .agents/skills/worklog/generate_worklog.py
  python3 .agents/skills/worklog/serve_worklog.py &
```

## Customization

### Add New Patterns

Edit `synthesize_goal()` in `generate_worklog.py`:

```python
elif 'my pattern' in first_lower:
    return "My custom objective description"
```

### Change Styling

Edit CSS in `generate_html()` function:

```python
.conv {{
    background: #your-color;  # Change conversation background
    border-left: 4px solid #your-accent;  # Change accent color
}}
```

### Adjust Token Usage

- **Fewer API calls**: Reduce `limit=10` in `get_user_messages()`
- **More detail**: Increase limit (trades tokens for detail)
- **Skip finish messages**: Comment out `get_finish_message()` call

## Troubleshooting

**No conversations found:**
- Check timezone (script uses ET, may be different day in ET vs UTC)
- Verify date range with test script
- Confirm OH_API_KEY is set

**Server won't start:**
- Port 12000 already in use: `pkill -f serve_worklog.py`
- Check logs: `cat /tmp/worklog_server.log`

**Poor objective synthesis:**
- Add custom patterns in `synthesize_goal()`
- Check first user message is substantive
- Verify message extraction is working

## Development

### Test Pattern Matching

```python
# Quick test
python3 << 'EOF'
from generate_worklog import synthesize_goal
test_msgs = ["Please help rebase PR #15006"]
print(synthesize_goal(test_msgs))
EOF
```

### Debug API Calls

Add debug logging:

```python
def api_request(url):
    print(f"DEBUG: {url}", file=sys.stderr)
    # ... rest of function
```

## See Also

- [SKILL.md](SKILL.md) - Full skill documentation
- [OpenHands Cloud API](https://app.all-hands.dev/api/docs) - API reference
- [OpenHands Docs](https://docs.openhands.dev) - General documentation
