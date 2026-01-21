---
name: linear-board
description: Manage Linear boards, query issues, update status, and create new issues using the Linear API and linearctl CLI. Use when working with Linear project management.
triggers:
  - linear board
  - linear issues
  - fde board
  - linear api
  - linear task
  - linear project
  - update linear
  - create linear issue
  - linear status
  - linear summary
---

# Linear Board Management

This skill provides comprehensive guidance for managing Linear boards, including querying, updating, and creating issues using both the Linear API and linearctl CLI tool.

## Prerequisites

- **Linear API Token**: Available as `$LINEAR_TOKEN` environment variable
- **Node.js and npm**: Required for linearctl installation
- **jq**: For JSON processing (usually pre-installed)

## Quick Setup

If linearctl is not already installed:

```bash
# Install linearctl globally
npm install -g linearctl

# Initialize with your API token
echo "$LINEAR_TOKEN" | linearctl init

# Verify installation
lc team list
```

## Core Operations

### 1. Get Board Summary

**Query issues for a user:**

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{
    "query": "query { issues(first: 250, filter: { assignee: { email: { eq: \"user@example.com\" } } }) { nodes { identifier title state { name } project { name } } } }"
  }' > /tmp/linear_issues.json

# Count total issues
echo "Total Issues: $(jq '.data.issues.nodes | length' /tmp/linear_issues.json)"

# Count by status
echo -e "\nBy Status:"
jq -r '.data.issues.nodes[] | .state.name' /tmp/linear_issues.json | sort | uniq -c | sort -rn

# List In Progress issues
echo -e "\nIn Progress:"
jq -r '.data.issues.nodes[] | select(.state.name == "In Progress") | "- \(.identifier): \(.title)"' /tmp/linear_issues.json
```

**Using linearctl (simpler approach):**

```bash
# List your assigned issues
lc issue mine

# Get specific issue details
lc issue get ISSUE-123
```

### 2. Update Existing Issues

```bash
# Mark issue as In Progress
lc issue update ISSUE-123 --state "In Progress"

# Mark issue as Done
lc issue update ISSUE-123 --state "Done"

# Update multiple fields at once
lc issue update ISSUE-123 \
  --state "In Progress" \
  --priority 2 \
  --assignee "user@example.com" \
  --title "Updated title"

# Priority levels: 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
lc issue update ISSUE-123 --priority 1

# Bulk update multiple issues
for ISSUE_ID in ISSUE-123 ISSUE-456 ISSUE-789; do
    lc issue update $ISSUE_ID --state Done
    echo "Updated $ISSUE_ID"
done
```

### 3. Create New Issues

```bash
# Create a new issue
lc issue create \
  --team "Team Name" \
  --title "New task" \
  --description "Details about the task" \
  --priority 3 \
  --project "Project Name"

# Create and assign with labels
lc issue create \
  --team "Team Name" \
  --title "Support request" \
  --description "Issue details..." \
  --assignee "user@example.com" \
  --priority 2 \
  --state "Todo" \
  --labels "customer-support,urgent" \
  --project "Project Name"

# Create with due date
lc issue create \
  --team "Team Name" \
  --title "Q1 Planning" \
  --due-date 2025-12-31 \
  --project "Project Name"
```

## Advanced Operations

### Export Issues to CSV

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{"query": "query { issues(first: 250, filter: { team: { key: { eq: \"TEAM\" } } }) { nodes { identifier title state { name } assignee { email } priority createdAt } } }"}' \
  | jq -r '.data.issues.nodes[] | [.identifier, .title, .state.name, .assignee.email, .priority, .createdAt] | @csv' \
  > issues.csv
```

### Search Issues by Text

```bash
lc issue list --search "keyword" --limit 100
```

### List Available Workflow States

```bash
lc status list --team TEAM
```

## GraphQL Query Examples

### Get Issues for Specific Project

```graphql
query {
  issues(first: 250, filter: {
    project: { name: { eq: "Project Name" } }
  }) {
    nodes {
      identifier
      title
      state { name }
      assignee { name email }
    }
  }
}
```

### Get Issues with Specific Labels

```graphql
query {
  issues(first: 250, filter: {
    labels: { name: { contains: "urgent" } }
  }) {
    nodes {
      identifier
      title
      labels { nodes { name } }
    }
  }
}
```

## Troubleshooting

**linearctl says "API Key: Not configured":**
```bash
echo "$LINEAR_TOKEN" | linearctl init
```

**curl returns authentication errors:**
```bash
# Verify token is set
echo $LINEAR_TOKEN

# If empty, export it
export LINEAR_TOKEN="your-token-here"
```

## Common Use Cases

### Daily Standup Summary
```bash
# Get your current work
lc issue mine --state "In Progress"

# Get your upcoming work
lc issue mine --state "Todo" --limit 5
```

## Best Practices

1. **Use descriptive titles**: Include customer name or project context
2. **Set appropriate priorities**: Use priority levels consistently across the team
3. **Add relevant labels**: Use labels for categorization and filtering
4. **Update status regularly**: Keep issue status current for accurate reporting
5. **Use projects**: Assign issues to the correct project for proper tracking
6. **Set due dates**: For time-sensitive work, always include due dates
