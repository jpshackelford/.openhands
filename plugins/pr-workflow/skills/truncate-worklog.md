---
name: truncate-worklog
description: Archive old worklog entries while preserving recent productive work context
triggers:
  - /truncate-worklog
---

# Truncate Worklog

Archives old entries from `WORKLOG.md` to daily archive files while ensuring the main worklog always contains enough context for agents to understand recent productive work.

## Key Principle

**Keep entries spanning at least 6 hours of productive work.**

- "Productive work" = entries where actual work happened (launches, completions, merges)
- "Status checks" = passive entries (waiting, all quiet) — don't count toward the 6-hour span
- This ensures agents always have meaningful context, even during quiet periods

## Usage

```
/truncate-worklog
```

Or called automatically by the orchestrator as a housekeeping step.

## Entry Classification

### Productive Work Entries (count toward 6-hour span)

These entries represent actual work being done:

| Indicator | Example |
|-----------|---------|
| `🚀 **Launched:` | Spawning a worker (testing / merge / parallel-spawn umbrella) |
| `🔍 **Launched:` | Spawning an expansion worker |
| `🛠 **Launched:` | Spawning an implementation worker |
| `✅ **Completed:` | PR or task completed |
| `✅ **Merged:` | PR merged |
| `✅ **Expanded` | Issue expanded |
| `✅ **Addressed` | Review feedback addressed |
| `✅ **Created:` | PR or issue created |
| `📋 **Following Human Instructions**` | Acting on instructions |
| `🔒 **Auto-disabled` | Automation state change |

The 🔍/🛠 emoji variants mirror the variant-cue table in `orchestrate.md` so single-worker expansion and implementation spawns are correctly classified as productive (and anchor the 6-hour retention window) rather than being silently treated as status checks.

### Status Check Entries (don't count toward span)

These are passive observations, not productive work:

| Indicator | Example |
|-----------|---------|
| `⏳ **Waiting**` | Waiting for something |
| `✅ **All quiet**` | Nothing to do |
| `Action Taken: None` | No action taken |
| `Action Taken:\nNone` | Multi-line none |

## Algorithm

```
┌─────────────────────────────────────────────────────────────────┐
│  TRUNCATE WORKLOG                                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. PARSE WORKLOG.md                                            │
│     ├─ Extract static header (everything before "## Log")       │
│     └─ Parse entries: timestamp, content, productive flag       │
│                                                                  │
│  2. CLASSIFY ENTRIES                                            │
│     ├─ Scan content for productive indicators                   │
│     └─ Mark each entry as productive=true/false                 │
│                                                                  │
│  3. CALCULATE 6-HOUR PRODUCTIVE SPAN                            │
│     ├─ Walk entries newest → oldest                             │
│     ├─ Track: newest_productive_ts, oldest_productive_ts        │
│     ├─ Span = newest_productive_ts - oldest_productive_ts       │
│     └─ Stop when span ≥ 6 hours OR out of entries               │
│                                                                  │
│  4. DETERMINE CUTOFF                                            │
│     ├─ Keep all entries from cutoff_ts forward                  │
│     ├─ Include status entries within the productive window      │
│     └─ If ALL entries are old with no recent productive work:   │
│         → Keep everything (don't create empty worklog)          │
│                                                                  │
│  5. ARCHIVE OLD ENTRIES                                         │
│     ├─ Group by entry date (YYYY-MM-DD from timestamp)          │
│     ├─ Append to WORKLOG_ARCHIVE_YYYY-MM-DD.md                  │
│     └─ Create archive file if doesn't exist                     │
│                                                                  │
│  6. REWRITE WORKLOG.md                                          │
│     ├─ Static header + "## Log" marker                          │
│     └─ Kept entries (newest at bottom)                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Complete Script

Here's the full implementation as a Python script:

```python
#!/usr/bin/env python3
"""
Truncate WORKLOG.md by archiving old entries while preserving
at least 6 hours of productive work context.
"""

import re
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict

def is_productive(content: str) -> bool:
    """Determine if an entry represents productive work."""
    productive_indicators = [
        # Worker spawns — emoji choice mirrors orchestrate.md's variant-cue table.
        '🚀 **Launched:',
        '🚀 **Spawned:',
        '🔍 **Launched:',  # expansion worker
        '🛠 **Launched:',  # implementation worker
        '✅ **Completed:',
        '✅ **Merged:',
        '✅ **Expanded',
        '✅ **Addressed',
        '✅ **Created:',
        '📋 **Following Human Instructions**',
        '🔒 **Auto-disabled',
    ]

    status_indicators = [
        '⏳ **Waiting**',
        '✅ **All quiet**',
        'Action Taken: None',
        'Action Taken:\nNone',
    ]

    for indicator in status_indicators:
        if indicator in content:
            return False

    for indicator in productive_indicators:
        if indicator in content:
            return True

    return False

def parse_worklog(worklog_path: str) -> tuple[str, list[dict]]:
    """Parse WORKLOG.md into header and entries."""
    with open(worklog_path, 'r') as f:
        content = f.read()

    # Split at "## Log" marker
    parts = re.split(r'(^## Log$)', content, maxsplit=1, flags=re.MULTILINE)

    if len(parts) < 3:
        # No "## Log" section found
        return content, []

    header = parts[0] + parts[1]  # Everything up to and including "## Log"
    entries_section = parts[2]

    # Parse individual entries
    entries = []
    raw_entries = re.split(r'\n---\n', entries_section)

    for raw in raw_entries:
        raw = raw.strip()
        if not raw:
            continue

        # Extract timestamp: ### 2026-05-06 19:15 UTC - ...
        match = re.match(r'^### (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) UTC', raw)
        if not match:
            continue

        date_str, time_str = match.groups()
        timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        timestamp = timestamp.replace(tzinfo=timezone.utc)

        entries.append({
            'timestamp': timestamp,
            'date': date_str,
            'content': raw,
            'productive': is_productive(raw)
        })

    return header, entries

def calculate_cutoff(entries: list[dict], min_hours: int = 6) -> datetime:
    """Calculate the cutoff timestamp for retention."""
    if not entries:
        return datetime.min.replace(tzinfo=timezone.utc)

    # Sort newest first
    sorted_entries = sorted(entries, key=lambda e: e['timestamp'], reverse=True)
    productive = [e for e in sorted_entries if e['productive']]

    if not productive:
        # No productive work - keep everything
        return datetime.min.replace(tzinfo=timezone.utc)

    newest = productive[0]['timestamp']
    oldest_in_window = newest

    for entry in productive:
        oldest_in_window = entry['timestamp']
        span = newest - oldest_in_window
        if span >= timedelta(hours=min_hours):
            break

    return oldest_in_window

def archive_entries(entries: list[dict], repo_path: str):
    """Archive entries to daily archive files."""
    by_date = defaultdict(list)
    for entry in entries:
        by_date[entry['date']].append(entry)

    for date, date_entries in sorted(by_date.items()):
        date_entries.sort(key=lambda e: e['timestamp'])
        archive_file = os.path.join(repo_path, f"WORKLOG_ARCHIVE_{date}.md")
        archive_content = "\n\n---\n".join(e['content'] for e in date_entries)

        if os.path.exists(archive_file):
            with open(archive_file, 'a') as f:
                f.write(f"\n\n---\n{archive_content}")
        else:
            header = f"""# OHTV Worklog Archive - {date}

Archived entries from WORKLOG.md for {date}.

---

{archive_content}"""
            with open(archive_file, 'w') as f:
                f.write(header)

        print(f"📦 Archived {len(date_entries)} entries to WORKLOG_ARCHIVE_{date}.md")

def truncate_worklog(repo_path: str = ".", min_hours: int = 6, dry_run: bool = False):
    """Main truncation function."""
    worklog_path = os.path.join(repo_path, "WORKLOG.md")

    if not os.path.exists(worklog_path):
        print("❌ WORKLOG.md not found")
        return

    header, entries = parse_worklog(worklog_path)

    if not entries:
        print("📋 No entries to process")
        return

    print(f"📋 Found {len(entries)} total entries")
    productive_count = sum(1 for e in entries if e['productive'])
    print(f"   └─ {productive_count} productive, {len(entries) - productive_count} status checks")

    cutoff = calculate_cutoff(entries, min_hours)

    # Split entries
    to_keep = [e for e in entries if e['timestamp'] >= cutoff]
    to_archive = [e for e in entries if e['timestamp'] < cutoff]

    if not to_archive:
        print("✅ Nothing to archive - all entries within retention window")
        return

    # Calculate productive span of kept entries
    kept_productive = [e for e in to_keep if e['productive']]
    if kept_productive:
        kept_productive_sorted = sorted(kept_productive, key=lambda e: e['timestamp'])
        if len(kept_productive_sorted) >= 2:
            span = kept_productive_sorted[-1]['timestamp'] - kept_productive_sorted[0]['timestamp']
        else:
            span = timedelta(0)
        print(f"📊 Keeping {len(to_keep)} entries spanning {span} of productive work")

    print(f"📦 Archiving {len(to_archive)} old entries")

    if dry_run:
        print("🔍 DRY RUN - no changes made")
        for e in to_archive:
            print(f"   Would archive: {e['date']} {e['timestamp'].strftime('%H:%M')} - {'🚀' if e['productive'] else '⏳'}")
        return

    # Archive old entries
    archive_entries(to_archive, repo_path)

    # Rewrite WORKLOG.md
    to_keep.sort(key=lambda e: e['timestamp'])
    entries_content = "\n\n---\n".join(e['content'] for e in to_keep)
    new_content = f"{header}\n\n{entries_content}\n"

    with open(worklog_path, 'w') as f:
        f.write(new_content)

    print(f"✅ WORKLOG.md updated - kept {len(to_keep)} entries")

if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    truncate_worklog(".", min_hours=6, dry_run=dry_run)
```

## Bash Quick Check

For the orchestrator to quickly decide if truncation is needed:

```bash
# Only run truncation if WORKLOG.md is large (>300 lines)
WORKLOG_LINES=$(wc -l < WORKLOG.md 2>/dev/null || echo 0)
if [ "$WORKLOG_LINES" -gt 300 ]; then
  echo "WORKLOG.md has $WORKLOG_LINES lines - running truncation"
  # Run the Python script inline or from a file
fi
```

## When to Run

1. **Automatically**: Called by orchestrator at start of each run (if worklog is large)
2. **Manually**: `/truncate-worklog` when you want to clean up
3. **Scheduled**: Could be added to cron, but orchestrator integration is preferred

## Edge Cases Handled

| Scenario | Behavior |
|----------|----------|
| No entries | Do nothing |
| All entries are productive | Keep 6-hour span, archive rest |
| All entries are status checks | Keep everything (no productive work to anchor) |
| Mixed entries | Keep productive span + status checks within window |
| Only 1 productive entry | Keep everything (can't establish span) |
| 48 hours of inactivity | Keep all entries (they're the "recent" context) |
| Entry dates span multiple days | Archive to correct daily files |

## Files Modified

After running truncation:

- `WORKLOG.md` - Reduced to recent entries
- `WORKLOG_ARCHIVE_YYYY-MM-DD.md` - Created/appended for each day with archived entries

## Commit Pattern

When truncation runs as part of orchestrator:

```bash
git add WORKLOG.md WORKLOG_ARCHIVE_*.md
git commit -m "chore: archive worklog entries older than 6hr productive window"
git push origin main
```
