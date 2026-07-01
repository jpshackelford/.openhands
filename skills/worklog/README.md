# 📋 Daily Worklog Skill

Token-efficient worklog generator for OpenHands conversations with synthesized objectives and PR/issue links.

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

- **🎯 Objective**: Synthesized from your messages (not raw quotes)
- **✅ Outcomes**: Clickable links to PRs/issues created
- **🕐 Time**: When the conversation started (US Eastern Time)
- **🔗 Link**: Direct link to conversation in OpenHands Cloud

## Token Efficiency

**Per 20 conversations: ~40-60 API calls, ~2-3K tokens**

Compare to full event inspection: ~200 calls, ~50K tokens (17x more expensive!)

### How It Works

1. **Single batch fetch**: Get all conversations from today (1 API call)
2. **Per conversation**:
   - Fetch user messages (1 call, limit 10)
   - Fetch finish message (1 call, limit 20)
   - Extract PR/issue URLs from text (no API calls)
3. **Synthesize objectives**: Pattern matching + entity extraction (no API calls)

## Features

### Objective Synthesis

Detects patterns in your messages to create concise objectives:

- **"rebase" + PR #** → "Rebase and resolve merge conflicts in PR #123"
- **"file an issue"** → "File GitHub issues for identified bugs/improvements"
- **"clone OpenHands/repo"** → "Clone and examine repo repository"
- **Questions** → Preserves your question as objective
- **Fallback** → Uses cleaned first sentence

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

**Optional:**
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
