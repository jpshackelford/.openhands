#!/usr/bin/env python3
"""
Enhanced Daily Worklog Generator v3 - LLM-powered synthesis
Uses parallel LLM calls to synthesize deep understanding of each conversation
"""
import os, json, sys, re, asyncio
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API_KEY = os.environ.get('OH_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
BASE_URL = "https://app.all-hands.dev/api/v1"

# LLM config for synthesis
LITELLM_ENDPOINT = os.environ.get('LITELLM_ENDPOINT_URL', 'https://api.openai.com/v1')
LITELLM_KEY = os.environ.get('LITELLM_PROXY_KEY') or os.environ.get('OPENAI_API_KEY')
SYNTHESIS_MODEL = os.environ.get('SYNTHESIS_MODEL', 'gpt-4o-mini')

def api_request(url):
    """Make authenticated API request to OpenHands"""
    req = Request(url)
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Accept', 'application/json')
    with urlopen(req) as response:
        return json.loads(response.read())

def github_api_request(url):
    """Make authenticated GitHub API request"""
    if not GITHUB_TOKEN:
        return None
    req = Request(url)
    req.add_header('Authorization', f'token {GITHUB_TOKEN}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    try:
        with urlopen(req) as response:
            return json.loads(response.read())
    except HTTPError as e:
        print(f"  GitHub API error: {e}", file=sys.stderr)
        return None

def llm_synthesize(prompt, max_tokens=300):
    """Make synchronous LLM call for synthesis"""
    if not LITELLM_KEY:
        print("  Warning: No LLM key available for synthesis", file=sys.stderr)
        return None
    
    try:
        req = Request(f"{LITELLM_ENDPOINT}/chat/completions")
        req.add_header('Authorization', f'Bearer {LITELLM_KEY}')
        req.add_header('Content-Type', 'application/json')
        
        data = json.dumps({
            "model": SYNTHESIS_MODEL,
            "messages": [
                {"role": "system", "content": "You synthesize conversation purposes concisely. Answer what problem is being solved, why it matters, what was done, and what's left. Use 1-2 clear sentences. Never quote raw text."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": 0.3
        }).encode()
        
        req.data = data
        with urlopen(req) as response:
            result = json.loads(response.read())
            return result['choices'][0]['message']['content'].strip()
    
    except Exception as e:
        print(f"  LLM synthesis error: {e}", file=sys.stderr)
        return None

# ============================================================================
# EXTRACTION TOOLS - Streamlined data gathering
# ============================================================================

def extract_text(content):
    """Extract text from message content"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                texts.append(item.get('text', ''))
            elif isinstance(item, str):
                texts.append(item)
        return ' '.join(texts)
    return str(content)

def get_messages_by_source(conv_id, source='user', limit=20):
    """Fetch messages filtered by source"""
    url = f"{BASE_URL}/conversation/{conv_id}/events/search?kind__eq=MessageEvent&limit=50"
    data = api_request(url)
    
    messages = []
    for item in data.get('items', []):
        if item.get('source') == source:
            content = item.get('content') or item.get('llm_message', {}).get('content', '')
            text = extract_text(content)
            if text and len(text.strip()) > 10:
                messages.append(text.strip())
                if len(messages) >= limit:
                    break
    return messages

def get_finish_message(conv_id):
    """Get finish message if present"""
    url = f"{BASE_URL}/conversation/{conv_id}/events/search?kind__eq=ActionEvent&limit=30"
    data = api_request(url)
    for item in reversed(data.get('items', [])):
        if item.get('tool_name') == 'finish':
            return item.get('action', {}).get('message', '')
    return None

def extract_pr_issue_urls(text):
    """Extract GitHub PR and issue URLs"""
    pr_pattern = r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)'
    issue_pattern = r'https://github\.com/([^/]+)/([^/]+)/issues/(\d+)'
    
    prs = []
    issues = []
    
    for match in re.finditer(pr_pattern, text):
        org, repo, num = match.groups()
        prs.append({'url': match.group(0), 'org': org, 'repo': repo, 'number': num})
    
    for match in re.finditer(issue_pattern, text):
        org, repo, num = match.groups()
        issues.append({'url': match.group(0), 'org': org, 'repo': repo, 'number': num})
    
    # Deduplicate
    seen_prs = set()
    unique_prs = []
    for pr in prs:
        key = f"{pr['org']}/{pr['repo']}#{pr['number']}"
        if key not in seen_prs:
            seen_prs.add(key)
            unique_prs.append(pr)
    
    seen_issues = set()
    unique_issues = []
    for issue in issues:
        key = f"{issue['org']}/{issue['repo']}#{issue['number']}"
        if key not in seen_issues:
            seen_issues.add(key)
            unique_issues.append(issue)
    
    return unique_prs, unique_issues

def fetch_pr_details(org, repo, number):
    """Fetch PR details from GitHub"""
    url = f"https://api.github.com/repos/{org}/{repo}/pulls/{number}"
    data = github_api_request(url)
    
    if not data:
        return None
    
    # Clean body - remove excessive newlines and limit length
    body = (data.get('body') or '').strip()
    body = re.sub(r'\n\n+', '\n', body)  # Collapse multiple newlines
    body = body[:800]  # Increased from 500 to get more context
    
    return {
        'number': number,
        'title': data.get('title', ''),
        'body': body,
        'state': data.get('state', ''),
        'labels': [l['name'] for l in data.get('labels', [])],
        'url': data.get('html_url', '')
    }

def fetch_issue_details(org, repo, number):
    """Fetch issue details from GitHub"""
    url = f"https://api.github.com/repos/{org}/{repo}/issues/{number}"
    data = github_api_request(url)
    
    if not data:
        return None
    
    body = (data.get('body') or '').strip()
    body = re.sub(r'\n\n+', '\n', body)
    body = body[:800]
    
    return {
        'number': number,
        'title': data.get('title', ''),
        'body': body,
        'state': data.get('state', ''),
        'labels': [l['name'] for l in data.get('labels', [])],
        'url': data.get('html_url', '')
    }

# ============================================================================
# CONTEXT GATHERING - Collect all data before synthesis
# ============================================================================

def gather_conversation_context(conv_id):
    """Gather all relevant context for a conversation (no synthesis yet)"""
    try:
        # Gather messages
        user_messages = get_messages_by_source(conv_id, 'user', limit=15)
        agent_messages = get_messages_by_source(conv_id, 'agent', limit=10)
        finish_msg = get_finish_message(conv_id)
        
        if not user_messages and not agent_messages:
            return None
        
        # Extract PR/issue URLs
        all_text = ' '.join(user_messages + agent_messages)
        if finish_msg:
            all_text += ' ' + finish_msg
        
        prs, issues = extract_pr_issue_urls(all_text)
        
        # Fetch GitHub details
        pr_details = []
        issue_details = []
        
        if GITHUB_TOKEN:
            for pr in prs[:2]:  # Limit to first 2
                details = fetch_pr_details(pr['org'], pr['repo'], pr['number'])
                if details:
                    pr_details.append(details)
            
            for issue in issues[:2]:
                details = fetch_issue_details(issue['org'], issue['repo'], issue['number'])
                if details:
                    issue_details.append(details)
        
        return {
            'user_messages': user_messages[:5],  # First 5 user messages
            'agent_messages': agent_messages[:3],  # First 3 agent messages
            'finish_message': finish_msg,
            'pr_details': pr_details,
            'issue_details': issue_details
        }
        
    except Exception as e:
        print(f"    Error gathering context: {e}", file=sys.stderr)
        return None

# ============================================================================
# LLM SYNTHESIS - Use LLM to understand and synthesize
# ============================================================================

def synthesize_title_and_purpose(context):
    """Use LLM to synthesize title and purpose from gathered context"""
    
    if not context:
        return "Empty conversation", "No messages found"
    
    # Build synthesis prompt with clear examples
    prompt_parts = []
    
    # Add PR/issue context if available
    if context['pr_details']:
        pr = context['pr_details'][0]
        prompt_parts.append(f"PR #{pr['number']}: {pr['title']}")
        if pr['body']:
            prompt_parts.append(f"PR Description: {pr['body'][:500]}")
    
    if context['issue_details']:
        issue = context['issue_details'][0]
        prompt_parts.append(f"Issue #{issue['number']}: {issue['title']}")
        if issue['body']:
            prompt_parts.append(f"Issue Description: {issue['body'][:500]}")
    
    # Add conversation messages
    if context['user_messages']:
        prompt_parts.append(f"User asked: {context['user_messages'][0][:300]}")
    
    if context['agent_messages']:
        prompt_parts.append(f"Agent responded: {context['agent_messages'][0][:300]}")
    
    if context['finish_message']:
        prompt_parts.append(f"Final summary: {context['finish_message'][:300]}")
    
    context_text = "\n\n".join(prompt_parts)
    
    # Create synthesis prompt with clear examples
    synthesis_prompt = f"""Given this conversation context, generate two things:

1. TITLE: A clear 5-10 word title describing the real work (not git actions)
2. PURPOSE: 1-2 sentences explaining what problem is being solved, why it matters, what was accomplished, and what's left unfinished

Context:
{context_text}

EXAMPLES:

Bad (quoting/actions):
Title: Resolve merge conflicts in PR #15006
Purpose: Working on: > **Stacked on #14937** (`feat/super-roles`). Please review/merge that PR first...

Good (synthesis):
Title: Super-admin management endpoint for enterprise auth
Purpose: Adding grant/revoke/list endpoints for super-admin privileges in the enterprise authentication system. Implementation complete with API routes, validation, and tests. Rebased onto feat/super-roles branch and pushed for review.

Bad (generic):
Title: Clone and examine automation repository
Purpose: Setting up repository for investigation

Good (specific):
Title: Fix automation link ghosting in Canvas SaaS
Purpose: Investigating why automation links appear ghosted in the Canvas SaaS UI. Found root cause in CSS visibility rules conflicting with authentication state. Fix implemented and PR opened.

Now generate TITLE and PURPOSE for the conversation above.

Format your response as:
TITLE: [your title]
PURPOSE: [your purpose]"""

    # Call LLM for synthesis
    synthesis = llm_synthesize(synthesis_prompt, max_tokens=250)
    
    if not synthesis:
        # Fallback to rule-based if LLM fails
        if context['pr_details']:
            title = context['pr_details'][0]['title'][:80]
            purpose = f"Working on PR #{context['pr_details'][0]['number']}: {context['pr_details'][0]['title']}"
        elif context['user_messages']:
            title = context['user_messages'][0][:80]
            purpose = context['user_messages'][0][:200]
        else:
            title = "Conversation"
            purpose = "Details unavailable"
        return title, purpose
    
    # Parse LLM response
    title_match = re.search(r'TITLE:\s*(.+?)(?:\n|$)', synthesis)
    purpose_match = re.search(r'PURPOSE:\s*(.+?)(?:\n\n|$)', synthesis, re.DOTALL)
    
    title = title_match.group(1).strip() if title_match else "Conversation"
    purpose = purpose_match.group(1).strip() if purpose_match else synthesis[:200]
    
    return title, purpose

def format_outcomes(context):
    """Format PR/issue links with numbers"""
    outcomes = []
    
    # Add PR links with numbers
    for pr in context.get('pr_details', [])[:2]:
        state_badge = "✓" if pr['state'] == 'closed' else "→"
        outcomes.append(
            f'{state_badge} <a href="{pr["url"]}" target="_blank">PR #{pr["number"]}: {pr["title"][:60]}</a>'
        )
    
    # Add issue links with numbers
    for issue in context.get('issue_details', [])[:2]:
        state_badge = "✓" if issue['state'] == 'closed' else "→"
        outcomes.append(
            f'{state_badge} <a href="{issue["url"]}" target="_blank">Issue #{issue["number"]}: {issue["title"][:60]}</a>'
        )
    
    return outcomes

# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def main():
    """Generate enhanced worklog with LLM-powered synthesis"""
    print("🔄 Generating enhanced worklog with LLM synthesis...", file=sys.stderr)
    
    if not LITELLM_KEY:
        print("⚠️  Warning: No LLM key found. Synthesis will use fallback rules.", file=sys.stderr)
        print("   Set LITELLM_PROXY_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY", file=sys.stderr)
    
    # Get timezone
    et_tz = ZoneInfo('America/New_York')
    now_et = datetime.now(et_tz)
    
    # Support date parameter
    import sys as sys_module
    if len(sys_module.argv) > 1 and sys_module.argv[1] == '--yesterday':
        from datetime import timedelta
        now_et = now_et - timedelta(days=1)
        print("📅 Generating worklog for YESTERDAY", file=sys.stderr)
    
    today_et_start = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc_start = today_et_start.astimezone(timezone.utc)
    today_et = now_et.strftime('%Y-%m-%d %A')
    
    # Fetch conversations
    print(f"📡 Fetching conversations since {today_et_start.strftime('%Y-%m-%d %I:%M %p ET')}...", file=sys.stderr)
    url = f"{BASE_URL}/app-conversations/search?created_at__gte={today_utc_start.isoformat().replace('+00:00','Z')}&limit=100"
    convs = api_request(url).get('items', [])
    print(f"✅ Found {len(convs)} conversations", file=sys.stderr)
    
    if not GITHUB_TOKEN:
        print("⚠️  GITHUB_TOKEN not set - PR/issue details will be limited", file=sys.stderr)
    
    # Generate HTML header
    html = generate_html_header(today_et, len(convs))
    
    # Process each conversation
    print("\n🧠 Analyzing conversations with LLM synthesis...", file=sys.stderr)
    for i, c in enumerate(convs, 1):
        print(f"  {i}/{len(convs)}: {c['title'][:60]}...", file=sys.stderr)
        
        dt_utc = datetime.fromisoformat(c['created_at'].replace('Z','+00:00'))
        dt_et = dt_utc.astimezone(et_tz)
        time_str = dt_et.strftime('%I:%M %p ET')
        
        # Gather context
        print(f"    Gathering context...", file=sys.stderr)
        context = gather_conversation_context(c['id'])
        
        if not context:
            title = "Empty conversation"
            purpose = "No messages found"
            outcomes = []
        else:
            # Synthesize with LLM
            print(f"    Synthesizing with LLM...", file=sys.stderr)
            title, purpose = synthesize_title_and_purpose(context)
            outcomes = format_outcomes(context)
        
        # Build HTML
        html += f'''
            <div class="conv">
                <h2 class="conv-title">{i}. {title}</h2>
                <div class="conv-header">
                    <a href="https://app.all-hands.dev/conversations/{c["id"]}" target="_blank" class="conv-link">
                        View conversation →
                    </a>
                    <span class="conv-time">{time_str}</span>
                </div>
                <div class="conv-purpose">{purpose}</div>'''
        
        if outcomes:
            outcomes_html = '<br>'.join(outcomes)
            html += f'''
                <div class="conv-outcomes">{outcomes_html}</div>'''
        
        html += f'''
                <div class="meta">
                    <span class="badge">🆔 {c["id"][:8]}</span>
                </div>
            </div>'''
    
    # Close HTML
    html += '''
        </main>
        <footer>
            Generated with OpenHands Cloud API + GitHub API + LLM Synthesis v3
        </footer>
    </div>
</body>
</html>'''
    
    # Write to file
    with open('/tmp/worklog.html', 'w') as f:
        f.write(html)
    
    print(f"\n✅ Generated enhanced worklog with {len(convs)} conversations", file=sys.stderr)
    print(f"📄 Saved to /tmp/worklog.html", file=sys.stderr)
    print(f"🌐 Serve with: python3 skills/worklog/serve_worklog.py", file=sys.stderr)

def generate_html_header(today_et, conv_count):
    """Generate HTML header and styling"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Worklog {today_et}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            min-height: 100vh;
            margin: 0;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem 3rem;
        }}
        h1 {{
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0;
            font-weight: 700;
        }}
        .subtitle {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        .stats {{
            display: flex;
            gap: 2rem;
            margin-top: 1.5rem;
        }}
        .stat {{
            background: rgba(255,255,255,0.2);
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }}
        .stat strong {{
            font-size: 1.5rem;
            display: block;
            font-weight: 700;
        }}
        .stat span {{
            font-size: 0.9rem;
            opacity: 0.9;
        }}
        main {{
            padding: 2rem 3rem;
        }}
        .conv {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 1.5rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        .conv:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(4px);
        }}
        .conv-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: #2c3e50;
            margin: 0 0 0.75rem 0;
        }}
        .conv-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .conv-link {{
            font-size: 0.9rem;
            color: #667eea;
            text-decoration: none;
        }}
        .conv-link:hover {{
            text-decoration: underline;
        }}
        .conv-time {{
            font-size: 0.9rem;
            color: #6c757d;
            white-space: nowrap;
        }}
        .conv-purpose {{
            color: #495057;
            line-height: 1.7;
            margin: 1rem 0;
            font-size: 1.05rem;
            font-weight: 400;
        }}
        .conv-outcomes {{
            background: #e8f5e9;
            border-left: 3px solid #4caf50;
            padding: 0.75rem;
            margin-top: 1rem;
            border-radius: 4px;
            font-size: 0.95rem;
            color: #2e7d32;
        }}
        .conv-outcomes a {{
            color: #1976d2;
            text-decoration: none;
            font-weight: 500;
        }}
        .conv-outcomes a:hover {{
            text-decoration: underline;
        }}
        .meta {{
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: #6c757d;
            margin-top: 0.75rem;
        }}
        .badge {{
            background: #e9ecef;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }}
        footer {{
            text-align: center;
            padding: 1.5rem;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 0.9rem;
        }}
        @media (max-width: 768px) {{
            body {{
                padding: 1rem;
            }}
            header, main {{
                padding: 1.5rem;
            }}
            h1 {{
                font-size: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 Worklog v3</h1>
            <div class="subtitle">{today_et} • LLM-Synthesized</div>
            <div class="stats">
                <div class="stat">
                    <strong>{conv_count}</strong>
                    <span>Conversations</span>
                </div>
            </div>
        </header>
        <main>'''

if __name__ == '__main__':
    main()
