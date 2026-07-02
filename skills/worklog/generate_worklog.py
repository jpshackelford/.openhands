#!/usr/bin/env python3
"""
Enhanced Daily Worklog Generator v5 - Optimized for token efficiency

Key optimizations:
- Single event fetch per conversation (3+ API calls -> 1)
- Engagement pre-filtering (skip ~30% of low-engagement conversations)
- Smarter GitHub fetching (only first PR gets full details)
- Client-side filtering reduces API overhead
"""
import os, json, sys, re, asyncio, argparse, time
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

API_KEY = os.environ.get('OH_API_KEY') or os.environ.get('OPENHANDS_API_KEY')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
BASE_URL = os.environ.get('OPENHANDS_CLOUD_API_URL', 'https://app.all-hands.dev').rstrip('/') + '/api/v1'

# LLM config for synthesis
LITELLM_ENDPOINT = os.environ.get('LITELLM_ENDPOINT_URL', 'https://api.openai.com/v1')
LITELLM_KEY = os.environ.get('LITELLM_PROXY_KEY') or os.environ.get('OPENAI_API_KEY')
SYNTHESIS_MODEL = os.environ.get('SYNTHESIS_MODEL', 'gpt-4o-mini')

# Engagement threshold for LLM synthesis (skip conversations below this)
MIN_ENGAGEMENT_SCORE = int(os.environ.get('MIN_ENGAGEMENT_SCORE', '5'))

# Retry configuration
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '5'))
INITIAL_BACKOFF = float(os.environ.get('INITIAL_BACKOFF', '1.0'))

def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, initial_backoff=INITIAL_BACKOFF, **kwargs):
    """Retry a function with exponential backoff for rate limits and transient errors"""
    import random
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except HTTPError as e:
            # Retry on rate limits (429) and server errors (5xx)
            if e.code == 429 or (500 <= e.code < 600):
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter
                    backoff = initial_backoff * (2 ** attempt) + random.uniform(0, 1)
                    print(f"  Rate limit/server error (HTTP {e.code}), retrying in {backoff:.1f}s (attempt {attempt + 1}/{max_retries})...", file=sys.stderr)
                    time.sleep(backoff)
                    continue
            # Don't retry on other errors (401, 403, 404, etc.)
            raise
        except Exception as e:
            # Don't retry on non-HTTP errors
            raise
    
    # If we exhausted all retries
    raise Exception(f"Max retries ({max_retries}) exceeded")

def api_request(url):
    """Make authenticated API request to OpenHands with retry logic"""
    def _make_request():
        req = Request(url)
        req.add_header('X-Access-Token', API_KEY)
        req.add_header('Accept', 'application/json')
        with urlopen(req) as response:
            return json.loads(response.read())
    
    return retry_with_backoff(_make_request)

def github_api_request(url):
    """Make authenticated GitHub API request with retry logic"""
    if not GITHUB_TOKEN:
        return None
    
    def _make_request():
        req = Request(url)
        req.add_header('Authorization', f'token {GITHUB_TOKEN}')
        req.add_header('Accept', 'application/vnd.github.v3+json')
        with urlopen(req) as response:
            return json.loads(response.read())
    
    try:
        return retry_with_backoff(_make_request)
    except HTTPError as e:
        print(f"  GitHub API error: HTTP {e.code} {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  GitHub API error: {type(e).__name__}: {e}", file=sys.stderr)
        return None

def llm_synthesize(prompt, max_tokens=300):
    """Make synchronous LLM call for synthesis with retry logic"""
    if not LITELLM_KEY:
        print("  Warning: No LLM key available for synthesis", file=sys.stderr)
        return None
    
    def _make_llm_request():
        url = f"{LITELLM_ENDPOINT.rstrip('/')}/chat/completions"
        req = Request(url, method='POST')
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
    
    try:
        return retry_with_backoff(_make_llm_request)
    except HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')[:200] if e.fp else ''
        print(f"  LLM synthesis error: HTTP {e.code} {e.reason} - {error_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  LLM synthesis error: {type(e).__name__}: {e}", file=sys.stderr)
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

# ============================================================================
# OPTIMIZED EVENT FETCHING - Single API call per conversation
# ============================================================================

def fetch_all_events(conv_id, limit=100):
    """Fetch all events in a single API call (OPTIMIZATION: was 3+ calls)
    
    Note: API maximum limit is 100
    """
    url = f"{BASE_URL}/conversation/{conv_id}/events/search?limit={limit}"
    data = api_request(url)
    return data.get('items', [])

def extract_messages_from_events(events, source='user', limit=5):
    """Extract messages from events (client-side filtering)"""
    messages = []
    for event in events:
        if event.get('kind') == 'MessageEvent' and event.get('source') == source:
            content = event.get('content') or event.get('llm_message', {}).get('content', '')
            text = extract_text(content)
            if text and len(text.strip()) > 10:
                messages.append(text.strip())
                if len(messages) >= limit:
                    break
    return messages

def extract_finish_message_from_events(events):
    """Extract finish message from events (client-side filtering)"""
    for event in reversed(events):
        if event.get('kind') == 'ActionEvent' and event.get('tool_name') == 'finish':
            return event.get('action', {}).get('message', '')
    return None

def compute_engagement_score(events):
    """
    Compute engagement score (0-100) based on conversation characteristics.
    
    Simple heuristic:
    - User messages: 20 points each (max 60)
    - Actions taken: 2 points each (max 20)
    - Has finish message: 20 points
    
    This helps identify "real work" vs fire-and-forget or abandoned conversations.
    """
    user_msg_count = sum(1 for e in events 
                        if e.get('kind') == 'MessageEvent' 
                        and e.get('source') == 'user')
    
    action_count = sum(1 for e in events 
                      if e.get('kind') == 'ActionEvent')
    
    has_finish = any(e.get('tool_name') == 'finish' for e in events 
                    if e.get('kind') == 'ActionEvent')
    
    # Scoring
    score = 0
    score += min(user_msg_count * 20, 60)  # Max 60 for user messages
    score += min(action_count * 2, 20)     # Max 20 for actions
    score += 20 if has_finish else 0       # 20 for completion
    
    return min(score, 100)

def should_synthesize(events, min_score=None):
    """
    Decide if conversation warrants LLM synthesis.
    
    Skip conversations with:
    - Single user message and no completion (likely abandoned)
    - No meaningful actions
    - Very low engagement score
    """
    if min_score is None:
        min_score = MIN_ENGAGEMENT_SCORE
    
    score = compute_engagement_score(events)
    return score >= min_score

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
    """
    Gather all relevant context for a conversation (OPTIMIZED VERSION).
    
    Key optimizations:
    - Single API call to fetch all events (was 3+ calls)
    - Client-side filtering and extraction
    - Pre-filter low-engagement conversations before LLM synthesis
    - Only fetch GitHub details for first PR/issue (was 2+ each)
    """
    try:
        # OPTIMIZATION: Single API call instead of 3+
        # Note: API max limit is 100
        events = fetch_all_events(conv_id, limit=100)
        
        if not events:
            return None
        
        # OPTIMIZATION: Pre-filter low-engagement conversations
        if not should_synthesize(events):
            engagement_score = compute_engagement_score(events)
            print(f"    ⏭️  Skipping low-engagement conversation (score: {engagement_score}/100)", file=sys.stderr)
            return None
        
        # Extract messages client-side (no more API calls)
        user_messages = extract_messages_from_events(events, 'user', limit=5)
        agent_messages = extract_messages_from_events(events, 'agent', limit=3)
        finish_msg = extract_finish_message_from_events(events)
        
        if not user_messages and not agent_messages:
            return None
        
        # Extract PR/issue URLs
        all_text = ' '.join(user_messages + agent_messages)
        if finish_msg:
            all_text += ' ' + finish_msg
        
        prs, issues = extract_pr_issue_urls(all_text)
        
        # OPTIMIZATION: Only fetch details for FIRST PR or issue (was 2+ each)
        pr_details = []
        issue_details = []
        
        if GITHUB_TOKEN:
            if prs:
                # Fetch only first PR (most relevant)
                pr = prs[0]
                details = fetch_pr_details(pr['org'], pr['repo'], pr['number'])
                if details:
                    pr_details.append(details)
            
            # Only fetch issue if no PRs (avoid redundant API calls)
            if issues and not prs:
                issue = issues[0]
                details = fetch_issue_details(issue['org'], issue['repo'], issue['number'])
                if details:
                    issue_details.append(details)
        
        # Return all data including for outcomes formatting
        return {
            'user_messages': user_messages,
            'agent_messages': agent_messages,
            'finish_message': finish_msg,
            'pr_details': pr_details,
            'issue_details': issue_details,
            'all_prs': prs,        # All PRs found (for outcomes, no extra API calls)
            'all_issues': issues,  # All issues found (for outcomes)
            'engagement_score': compute_engagement_score(events)
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

**IMPORTANT**: Focus on what the USER asked for, not the content mentioned in the agent's response. If the user asks to "generate a worklog", "review today's work", "show what I worked on", then the conversation is about GENERATING A SUMMARY/WORKLOG, not about the specific topics mentioned in that summary.

Context:
{context_text}

EXAMPLES:

Bad (quoting/actions):
Title: Resolve merge conflicts in PR #15006
Purpose: Working on: > **Stacked on #14937** (`feat/super-roles`). Please review/merge that PR first...

Good (synthesis):
Title: Super-admin management endpoint for enterprise auth
Purpose: Adding grant/revoke/list endpoints for super-admin privileges in the enterprise authentication system. Implementation complete with API routes, validation, and tests. Rebased onto feat/super-roles branch and pushed for review.

Bad (confusing meta with content):
User asked: what have I been working on today?
Agent responded: Here's a summary: 1. Fixed auth bug, 2. Reviewed PR #123...
Title: Fix authentication bug in user login
[This is WRONG - the conversation is about generating a summary, not fixing auth]

Good (recognizing meta-conversation):
User asked: what have I been working on today?
Agent responded: Here's a summary: 1. Fixed auth bug, 2. Reviewed PR #123...
Title: Daily work summary and progress review
Purpose: Generating a comprehensive summary of today's work activities to track progress. Summary completed showing multiple tasks across authentication, code review, and infrastructure work.

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
    
    # Add PR links with detailed info (we fetched these)
    for pr in context.get('pr_details', []):
        state_badge = "✓" if pr['state'] == 'closed' else "→"
        outcomes.append(
            f'{state_badge} <a href="{pr["url"]}" target="_blank">PR #{pr["number"]}: {pr["title"][:60]}</a>'
        )
    
    # Add additional PRs (found but not detailed - no extra API calls)
    detailed_pr_nums = {pr['number'] for pr in context.get('pr_details', [])}
    for pr in context.get('all_prs', []):
        if pr['number'] not in detailed_pr_nums:
            # Simple link without state/title (we didn't fetch it)
            pr_url = f"https://github.com/{pr['org']}/{pr['repo']}/pull/{pr['number']}"
            outcomes.append(
                f'→ <a href="{pr_url}" target="_blank">PR #{pr["number"]}</a>'
            )
    
    # Add issue links with detailed info
    for issue in context.get('issue_details', []):
        state_badge = "✓" if issue['state'] == 'closed' else "→"
        outcomes.append(
            f'{state_badge} <a href="{issue["url"]}" target="_blank">Issue #{issue["number"]}: {issue["title"][:60]}</a>'
        )
    
    # Add additional issues (found but not detailed)
    detailed_issue_nums = {issue['number'] for issue in context.get('issue_details', [])}
    for issue in context.get('all_issues', []):
        if issue['number'] not in detailed_issue_nums:
            issue_url = f"https://github.com/{issue['org']}/{issue['repo']}/issues/{issue['number']}"
            outcomes.append(
                f'→ <a href="{issue_url}" target="_blank">Issue #{issue["number"]}</a>'
            )
    
    return outcomes

# ============================================================================
# DATA GATHERING - Fetch and structure worklog data
# ============================================================================

def gather_worklog_data(date_offset=0, timezone_name='America/New_York'):
    """
    Gather worklog data for a specific date.
    Returns structured data without any rendering.
    
    Args:
        date_offset: Days to offset from today (0=today, -1=yesterday)
        timezone_name: IANA timezone name for date boundaries
    
    Returns:
        dict with 'date', 'conversations', and 'metadata'
    """
    et_tz = ZoneInfo(timezone_name)
    now_et = datetime.now(et_tz)
    
    if date_offset != 0:
        now_et = now_et + timedelta(days=date_offset)
    
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
    
    if not LITELLM_KEY:
        print("⚠️  Warning: No LLM key found. Synthesis will use fallback rules.", file=sys.stderr)
    
    # Process each conversation - gather data only
    print("\n🧠 Analyzing conversations with LLM synthesis...", file=sys.stderr)
    conversations_data = []
    
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
        
        # Store structured data
        conversations_data.append({
            'index': i,
            'id': c['id'],
            'original_title': c['title'],
            'synthesized_title': title,
            'purpose': purpose,
            'outcomes': outcomes,
            'time': time_str,
            'time_obj': dt_et,
            'context': context
        })
    
    return {
        'date': today_et,
        'date_obj': now_et,
        'timezone': timezone_name,
        'conversations': conversations_data,
        'total_count': len(conversations_data)
    }

def generate_html_header(today_et, conv_count):
    """Generate HTML header and styling - Agent Canvas themed"""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Worklog {today_et}</title>
    <style>
        :root {{
            /* Agent Canvas cool-grey palette (neutral theme) */
            --cool-grey-50: #F7F7F7;
            --cool-grey-100: #ECECEC;
            --cool-grey-200: #DCDCDC;
            --cool-grey-300: #BEBEBE;
            --cool-grey-400: #979797;
            --cool-grey-500: #737373;
            --cool-grey-600: #565656;
            --cool-grey-700: #404040;
            --cool-grey-800: #313131;
            --cool-grey-900: #282828;
            --cool-grey-925: #202020;
            --cool-grey-950: #181818;
            --cool-grey-975: #101010;
            
            /* Semantic colors matching Agent Canvas */
            --bg-primary: var(--cool-grey-950);
            --bg-secondary: var(--cool-grey-900);
            --bg-tertiary: var(--cool-grey-925);
            --bg-elevated: var(--cool-grey-800);
            --text-primary: var(--cool-grey-100);
            --text-secondary: var(--cool-grey-300);
            --text-tertiary: var(--cool-grey-400);
            --accent-primary: #60a5fa;
            --accent-hover: #93c5fd;
            --border-color: var(--cool-grey-800);
            --success-bg: rgba(96, 165, 250, 0.05);
            --success-border: var(--cool-grey-700);
            --success-text: var(--text-secondary);
        }}
        
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 2rem;
            min-height: 100vh;
            margin: 0;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: var(--bg-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color);
            overflow: hidden;
        }}
        
        header {{
            background: var(--bg-tertiary);
            border-bottom: 1px solid var(--border-color);
            padding: 2rem 3rem;
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0;
            font-weight: 700;
            color: var(--text-primary);
        }}
        
        .subtitle {{
            font-size: 1.1rem;
            color: var(--text-secondary);
        }}
        
        .stats {{
            display: flex;
            gap: 2rem;
            margin-top: 1.5rem;
        }}
        
        .stat {{
            background: var(--bg-elevated);
            border: 1px solid var(--border-color);
            padding: 0.75rem 1.25rem;
            border-radius: 8px;
        }}
        
        .stat strong {{
            font-size: 1.5rem;
            display: block;
            font-weight: 700;
            color: var(--accent-primary);
        }}
        
        .stat span {{
            font-size: 0.9rem;
            color: var(--text-secondary);
        }}
        
        main {{
            padding: 2rem 3rem;
        }}
        
        .conv {{
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-left: 3px solid var(--accent-primary);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 8px;
            transition: all 0.2s ease;
        }}
        
        .conv:hover {{
            border-left-width: 4px;
            background: var(--bg-elevated);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        
        .conv-title {{
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--text-primary);
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
            color: var(--accent-primary);
            text-decoration: none;
            transition: color 0.2s ease;
        }}
        
        .conv-link:hover {{
            color: var(--accent-hover);
            text-decoration: underline;
        }}
        
        .conv-time {{
            font-size: 0.9rem;
            color: var(--text-tertiary);
            white-space: nowrap;
        }}
        
        .conv-purpose {{
            color: var(--text-secondary);
            line-height: 1.7;
            margin: 1rem 0;
            font-size: 1.05rem;
            font-weight: 400;
        }}
        
        .conv-outcomes {{
            background: var(--success-bg);
            border-left: 3px solid var(--success-border);
            padding: 0.75rem 1rem;
            margin-top: 1rem;
            border-radius: 6px;
            font-size: 0.95rem;
            color: var(--success-text);
        }}
        
        .conv-outcomes a {{
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }}
        
        .conv-outcomes a:hover {{
            color: var(--accent-hover);
            text-decoration: underline;
        }}
        
        .meta {{
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: var(--text-tertiary);
            margin-top: 0.75rem;
        }}
        
        .badge {{
            background: var(--bg-elevated);
            border: 1px solid var(--border-color);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            color: var(--text-secondary);
        }}
        
        footer {{
            text-align: center;
            padding: 1.5rem;
            background: var(--bg-tertiary);
            border-top: 1px solid var(--border-color);
            color: var(--text-tertiary);
            font-size: 0.9rem;
        }}
        
        footer .version {{
            font-size: 0.7rem;
            opacity: 0.6;
            margin-top: 0.25rem;
            display: block;
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
                flex-direction: column;
                gap: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📋 Worklog</h1>
            <div class="subtitle">{today_et} • LLM-Synthesized</div>
            <div class="stats">
                <div class="stat">
                    <strong>{conv_count}</strong>
                    <span>Conversations</span>
                </div>
            </div>
        </header>
        <main>'''

# ============================================================================
# RENDERERS - Convert data to different output formats
# ============================================================================

def render_text(data):
    """Render worklog data as plain text"""
    lines = []
    lines.append(f"📋 Worklog for {data['date']}")
    lines.append("=" * 70)
    lines.append(f"Total conversations: {data['total_count']}")
    lines.append("")
    
    for conv in data['conversations']:
        lines.append(f"{conv['index']}. {conv['synthesized_title']}")
        lines.append(f"   Time: {conv['time']}")
        lines.append(f"   {conv['purpose']}")
        
        if conv['outcomes']:
            lines.append(f"   Outcomes:")
            for outcome in conv['outcomes']:
                # Strip HTML tags for text output
                clean_outcome = re.sub(r'<[^>]+>', '', outcome)
                lines.append(f"      {clean_outcome}")
        
        lines.append(f"   Conversation ID: {conv['id'][:8]}")
        lines.append(f"   Link: https://app.all-hands.dev/conversations/{conv['id']}")
        lines.append("")
    
    return '\n'.join(lines)

def render_markdown(data):
    """Render worklog data as markdown"""
    lines = []
    lines.append(f"# 📋 Worklog for {data['date']}")
    lines.append("")
    lines.append(f"**Total conversations:** {data['total_count']}")
    lines.append("")
    
    for conv in data['conversations']:
        lines.append(f"## {conv['index']}. {conv['synthesized_title']}")
        lines.append("")
        lines.append(f"**Time:** {conv['time']} | [View conversation](https://app.all-hands.dev/conversations/{conv['id']})")
        lines.append("")
        lines.append(conv['purpose'])
        lines.append("")
        
        if conv['outcomes']:
            lines.append("**Outcomes:**")
            for outcome in conv['outcomes']:
                # Convert HTML links to markdown
                clean_outcome = re.sub(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', r'[\2](\1)', outcome)
                clean_outcome = re.sub(r'<[^>]+>', '', clean_outcome)
                lines.append(f"- {clean_outcome}")
            lines.append("")
        
        lines.append(f"_Conversation ID: `{conv['id'][:8]}`_")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return '\n'.join(lines)

def render_html(data):
    """Render worklog data as HTML"""
    html = generate_html_header(data['date'], data['total_count'])
    
    for conv in data['conversations']:
        html += f'''
            <div class="conv">
                <h2 class="conv-title">{conv['index']}. {conv['synthesized_title']}</h2>
                <div class="conv-header">
                    <a href="https://app.all-hands.dev/conversations/{conv["id"]}" target="_blank" class="conv-link">
                        View conversation →
                    </a>
                    <span class="conv-time">{conv['time']}</span>
                </div>
                <div class="conv-purpose">{conv['purpose']}</div>'''
        
        if conv['outcomes']:
            outcomes_html = '<br>'.join(conv['outcomes'])
            html += f'''
                <div class="conv-outcomes">{outcomes_html}</div>'''
        
        html += f'''
                <div class="meta">
                    <span class="badge">🆔 {conv["id"][:8]}</span>
                </div>
            </div>'''
    
    html += '''
        </main>
        <footer>
            Generated with OpenHands Cloud API + GitHub API + LLM Synthesis
            <span class="version">v6</span>
        </footer>
    </div>
</body>
</html>'''
    
    return html

# ============================================================================
# MAIN - CLI entry point
# ============================================================================

def validate_environment():
    """Validate required environment variables and give helpful error messages"""
    errors = []
    warnings = []
    
    # Check required: OpenHands API key
    if not API_KEY:
        errors.append("❌ Missing required OpenHands API key")
        errors.append("   Set one of: OH_API_KEY or OPENHANDS_API_KEY")
        errors.append("   Get your key from: https://app.all-hands.dev/settings")
    
    # Check recommended: LLM key for synthesis
    if not LITELLM_KEY:
        warnings.append("⚠️  No LLM API key found - synthesis will be disabled")
        warnings.append("   Set one of: LITELLM_PROXY_KEY or OPENAI_API_KEY")
        warnings.append("   Without this, you'll only get basic conversation titles")
    
    # Check optional: GitHub token for PR/issue details
    if not GITHUB_TOKEN:
        warnings.append("⚠️  GITHUB_TOKEN not set - PR/issue details will be limited")
        warnings.append("   Set GITHUB_TOKEN to fetch full PR and issue descriptions")
    
    # Print warnings
    if warnings:
        for warning in warnings:
            print(warning, file=sys.stderr)
        print(file=sys.stderr)
    
    # Exit on errors
    if errors:
        print("\n🛑 Environment validation failed:\n", file=sys.stderr)
        for error in errors:
            print(error, file=sys.stderr)
        print("\nFor more details, see the skill documentation.", file=sys.stderr)
        sys.exit(1)

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description='Generate worklog with LLM synthesis in multiple formats'
    )
    parser.add_argument(
        '--format', 
        choices=['text', 'markdown', 'html'], 
        default='html',
        help='Output format (default: html)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: /tmp/worklog.{ext})'
    )
    parser.add_argument(
        '--date',
        help='Specific date (YYYY-MM-DD, e.g., 2026-06-15)'
    )
    parser.add_argument(
        '--date-offset',
        type=int,
        default=0,
        help='Days offset from today (0=today, -1=yesterday, etc.)'
    )
    parser.add_argument(
        '--timezone',
        default='America/New_York',
        help='IANA timezone name (default: America/New_York)'
    )
    parser.add_argument(
        '--stdout',
        action='store_true',
        help='Print to stdout instead of file'
    )
    
    args = parser.parse_args()
    
    # Validate environment before doing any work
    validate_environment()
    
    # Calculate date offset from absolute date if provided
    date_offset = args.date_offset
    if args.date:
        try:
            from zoneinfo import ZoneInfo
            target_date = datetime.fromisoformat(args.date)
            today = datetime.now(ZoneInfo(args.timezone)).replace(hour=0, minute=0, second=0, microsecond=0)
            date_offset = (target_date - today.replace(tzinfo=None)).days
            print(f"📅 Generating worklog for {args.date} (offset: {date_offset} days)", file=sys.stderr)
        except ValueError as e:
            print(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)
    
    # Gather data
    print(f"🔄 Generating worklog in {args.format} format...", file=sys.stderr)
    data = gather_worklog_data(date_offset=date_offset, timezone_name=args.timezone)
    
    # Render based on format
    if args.format == 'text':
        output = render_text(data)
        ext = 'txt'
    elif args.format == 'markdown':
        output = render_markdown(data)
        ext = 'md'
    else:  # html
        output = render_html(data)
        ext = 'html'
    
    # Output
    if args.stdout:
        print(output)
    else:
        output_path = args.output or f'/tmp/worklog.{ext}'
        with open(output_path, 'w') as f:
            f.write(output)
        
        print(f"\n✅ Generated worklog with {data['total_count']} conversations", file=sys.stderr)
        print(f"📄 Saved to {output_path}", file=sys.stderr)
        
        if args.format == 'html':
            print(f"🌐 Serve with: python3 skills/worklog/serve_worklog.py", file=sys.stderr)

if __name__ == '__main__':
    main()
