#!/usr/bin/env python3
"""
Daily Worklog Generator - Token-efficient OpenHands conversation analyzer
Generates HTML worklog with synthesized objectives and PR/issue links
"""
import os, json, sys, re
from urllib.request import Request, urlopen
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API_KEY = os.environ.get('OH_API_KEY')
BASE_URL = "https://app.all-hands.dev/api/v1"

def api_request(url):
    """Make authenticated API request"""
    req = Request(url)
    req.add_header('Authorization', f'Bearer {API_KEY}')
    req.add_header('Accept', 'application/json')
    with urlopen(req) as response:
        return json.loads(response.read())

def get_user_messages(conv_id, limit=10):
    """Fetch user messages from conversation"""
    url = f"{BASE_URL}/conversation/{conv_id}/events/search?kind__eq=MessageEvent&limit={limit}"
    return api_request(url).get('items', [])

def get_finish_message(conv_id):
    """Get finish message from conversation (if any)"""
    url = f"{BASE_URL}/conversation/{conv_id}/events/search?kind__eq=ActionEvent&limit=20"
    data = api_request(url)
    for item in reversed(data.get('items', [])):
        if item.get('tool_name') == 'finish':
            return item.get('action', {}).get('message', '')
    return None

def extract_text(content):
    """Extract text from message content (handles various formats)"""
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

def synthesize_goal(user_texts):
    """Synthesize user's objective from their messages"""
    if not user_texts:
        return "No clear objective"
    
    full_text = ' '.join(user_texts)
    first_lower = user_texts[0].lower()
    
    # Extract PR numbers
    pr_nums = re.findall(r'#(\d+)|/pull/(\d+)', full_text)
    pr_nums = [n[0] or n[1] for n in pr_nums]
    
    # Detect intent and synthesize objective
    if any(phrase in first_lower for phrase in ['create an html', 'worklog', 'html page', 'generate.*html']):
        return "Build HTML worklog showing today's conversation goals and outputs"
    
    elif any(word in first_lower for word in ['rebase', 'merge conflict']) and pr_nums:
        return f"Rebase and resolve merge conflicts in PR #{pr_nums[0]}"
    
    elif 'file an issue' in first_lower or 'file issue' in first_lower:
        return "File GitHub issues for identified bugs/improvements"
    
    elif 'automation' in full_text.lower() and 'ghost' in full_text.lower():
        return "Debug why Canvas automation link appears ghosted in SaaS"
    
    elif 'jira' in full_text.lower() and 'repository' in full_text.lower():
        return "Fix JIRA integration repository fetching issue"
    
    elif any(phrase in first_lower[:100] for phrase in ['can you tell', 'what', 'find', 'locate', 'where is']):
        if 'branch' in full_text.lower() and 'canvas' in full_text.lower():
            return "Identify recent branch created in Agent-Canvas repo"
        elif 'admin url' in full_text.lower():
            return "Find admin URL for OHE shared-2 deployment"
        elif 'slack' in full_text.lower() and 'message' in full_text.lower():
            return "Read and process Slack channel messages"
        return first_lower[:150].split('?')[0] + "?" if '?' in first_lower[:150] else "Investigate and gather information"
    
    elif first_lower.strip().startswith('clone'):
        repos = re.findall(r'OpenHands/([a-zA-Z0-9_-]+)', full_text)
        if repos:
            return f"Clone and examine {repos[0]} repository"
        return "Clone repository for investigation"
    
    elif any(word in first_lower[:100] for word in ['extend', 'add support for']):
        if 'tickster' in full_text.lower():
            return "Extend Tickster tool to support additional platforms"
        return "Extend functionality to support new features"
    
    elif 'migrate' in first_lower or 'replace' in first_lower:
        if 'lxa' in full_text.lower():
            return "Migrate from lxa to tkt in PR workflow"
        return "Migrate or refactor code"
    
    # Fallback: clean up first message and use it
    first = re.sub(r'^(please|can you|could you|i want you to|i need you to)\s+', '', user_texts[0], flags=re.I)
    first_sent = first.split('.')[0] if '.' in first[:150] else first[:150]
    return first_sent.strip()[:180]

def extract_links(user_texts, finish_msg):
    """Extract PR and issue links from conversation"""
    all_text = ' '.join(user_texts)
    if finish_msg:
        all_text += ' ' + finish_msg
    
    pr_links = {}
    issue_links = {}
    
    # Extract GitHub PR URLs
    pr_matches = re.findall(r'(https://github\.com/([^/]+)/([^/]+)/pull/(\d+))', all_text)
    for full_url, org, repo, num in pr_matches:
        key = f"{org}/{repo}#{num}"
        if key not in pr_links:
            pr_links[key] = {'url': full_url, 'org': org, 'repo': repo, 'num': num}
    
    # Extract GitHub issue URLs
    issue_matches = re.findall(r'(https://github\.com/([^/]+)/([^/]+)/issues/(\d+))', all_text)
    for full_url, org, repo, num in issue_matches:
        key = f"{org}/{repo}#{num}"
        if key not in issue_links:
            issue_links[key] = {'url': full_url, 'org': org, 'repo': repo, 'num': num}
    
    return pr_links, issue_links

def format_outcomes(pr_links, issue_links):
    """Format PR and issue links as HTML"""
    outcomes = []
    
    # Add PR links (limit 2)
    pr_list = list(pr_links.values())
    for pr in pr_list[:2]:
        outcomes.append(f'<a href="{pr["url"]}" target="_blank">PR #{pr["num"]}</a> ({pr["repo"]})')
    
    # Add issue links
    issue_list = list(issue_links.values())
    if len(issue_list) == 1:
        issue = issue_list[0]
        outcomes.append(f'<a href="{issue["url"]}" target="_blank">Issue #{issue["num"]}</a> ({issue["repo"]})')
    elif len(issue_list) > 1:
        links_str = ', '.join([f'<a href="{i["url"]}" target="_blank">#{i["num"]}</a>' for i in issue_list[:3]])
        if len(issue_list) > 3:
            outcomes.append(f'{len(issue_list)} issues: {links_str}, ...')
        else:
            outcomes.append(f'{len(issue_list)} issues: {links_str}')
    
    return " • ".join(outcomes) if outcomes else ""

def analyze_conversation(conv_id):
    """Analyze single conversation - token-efficient"""
    try:
        # Get user messages (1 API call)
        messages = get_user_messages(conv_id, limit=10)
        if not messages:
            return "No user messages found", ""
        
        # Extract text from messages
        user_texts = []
        for msg in messages:
            content = msg.get('content') or msg.get('llm_message', {}).get('content', '')
            text = extract_text(content)
            if text and len(text.strip()) > 10:
                user_texts.append(text.strip())
        
        if not user_texts:
            return "No details available", ""
        
        # Synthesize objective
        goal = synthesize_goal(user_texts)
        
        # Get finish message (1 API call)
        finish_msg = get_finish_message(conv_id)
        
        # Extract links
        pr_links, issue_links = extract_links(user_texts, finish_msg)
        
        # Format outcomes
        outcomes = format_outcomes(pr_links, issue_links)
        
        return goal, outcomes
        
    except Exception as e:
        print(f"  Error analyzing conversation: {e}", file=sys.stderr)
        return "Unable to analyze conversation", ""

def generate_html(convs, today_et):
    """Generate HTML worklog"""
    html = f'''<!DOCTYPE html>
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
            max-width: 1200px;
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
            margin-bottom: 1.5rem;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        .conv:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(4px);
        }}
        .conv-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .conv-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #667eea;
            text-decoration: none;
            flex: 1;
            min-width: 200px;
        }}
        .conv-title:hover {{
            color: #764ba2;
            text-decoration: underline;
        }}
        .conv-time {{
            font-size: 0.9rem;
            color: #6c757d;
            white-space: nowrap;
        }}
        .conv-goal {{
            color: #495057;
            line-height: 1.7;
            margin-bottom: 0.75rem;
            font-size: 1rem;
        }}
        .conv-outputs {{
            background: #e8f5e9;
            border-left: 3px solid #4caf50;
            padding: 0.75rem;
            margin-top: 0.75rem;
            border-radius: 4px;
            font-size: 0.9rem;
            color: #2e7d32;
        }}
        .conv-outputs::before {{
            content: "✓ ";
            font-weight: bold;
        }}
        .conv-outputs a {{
            color: #1976d2;
            text-decoration: none;
            font-weight: 500;
        }}
        .conv-outputs a:hover {{
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
            .stats {{
                gap: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 Worklog</h1>
            <div class="subtitle">{today_et}</div>
            <div class="stats">
                <div class="stat">
                    <strong>{len(convs)}</strong>
                    <span>Conversations</span>
                </div>
            </div>
        </header>
        <main>'''
    
    return html

def main():
    """Main worklog generator"""
    print("🔄 Generating worklog...", file=sys.stderr)
    
    # Get timezone
    et_tz = ZoneInfo('America/New_York')
    now_et = datetime.now(et_tz)
    
    # Support optional date parameter (for testing/historical worklogs)
    import sys as sys_module
    if len(sys_module.argv) > 1 and sys_module.argv[1] == '--yesterday':
        from datetime import timedelta
        now_et = now_et - timedelta(days=1)
        print("📅 Generating worklog for YESTERDAY", file=sys.stderr)
    
    today_et_start = now_et.replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc_start = today_et_start.astimezone(timezone.utc)
    today_et = now_et.strftime('%Y-%m-%d %A')
    
    # Fetch conversations (1 API call)
    print(f"📡 Fetching conversations since {today_et_start.strftime('%Y-%m-%d %I:%M %p ET')}...", file=sys.stderr)
    url = f"{BASE_URL}/app-conversations/search?created_at__gte={today_utc_start.isoformat().replace('+00:00','Z')}&limit=100"
    convs = api_request(url).get('items', [])
    print(f"✅ Found {len(convs)} conversations", file=sys.stderr)
    
    # Generate HTML
    html = generate_html(convs, today_et)
    
    # Process each conversation
    for i, c in enumerate(convs, 1):
        print(f"  {i}/{len(convs)}: {c['title'][:60]}...", file=sys.stderr)
        
        dt_utc = datetime.fromisoformat(c['created_at'].replace('Z','+00:00'))
        dt_et = dt_utc.astimezone(et_tz)
        time_str = dt_et.strftime('%I:%M %p ET')
        
        # Analyze conversation (2-3 API calls)
        goal, outcomes = analyze_conversation(c['id'])
        
        # Build HTML for this conversation
        html += f'''
            <div class="conv">
                <div class="conv-header">
                    <a href="https://app.all-hands.dev/conversations/{c["id"]}" target="_blank" class="conv-title">
                        {i}. {c["title"]}
                    </a>
                    <span class="conv-time">{time_str}</span>
                </div>
                <div class="conv-goal">{goal}</div>'''
        
        if outcomes:
            html += f'''
                <div class="conv-outputs">{outcomes}</div>'''
        
        html += f'''
                <div class="meta">
                    <span class="badge">🆔 {c["id"][:8]}</span>
                </div>
            </div>'''
    
    # Close HTML
    html += '''
        </main>
        <footer>
            Generated with OpenHands Cloud API • <a href="https://github.com/OpenHands/OpenHands" style="color: #667eea;">OpenHands</a>
        </footer>
    </div>
</body>
</html>'''
    
    # Write to file
    with open('/tmp/worklog.html', 'w') as f:
        f.write(html)
    
    print(f"\n✅ Generated worklog with {len(convs)} conversations", file=sys.stderr)
    print(f"📄 Saved to /tmp/worklog.html", file=sys.stderr)
    print(f"🌐 Serve with: python3 .agents/skills/worklog/serve_worklog.py", file=sys.stderr)

if __name__ == '__main__':
    main()
