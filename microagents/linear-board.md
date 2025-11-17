---
agent: CodeActAgent
triggers:
  - "linear board"
  - "linear issues"
  - "fde board"
  - "linear api"
  - "linear task"
  - "linear project"
  - "update linear"
  - "create linear issue"
  - "linear status"
  - "linear summary"
---

# Linear Board Management Microagent

This microagent provides comprehensive guidance for managing Linear boards, specifically the FDE (Field Development Engineering) board, including querying, updating, and creating issues using both the Linear API and linearctl CLI tool.

## Purpose

This microagent helps developers and project managers:

1. Query and summarize Linear board issues
2. Update existing issue status, priority, and other fields
3. Create new issues and assign them appropriately
4. Export and analyze issue data
5. Perform bulk operations on multiple issues

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

### 1. Get FDE Board Summary

The FDE board aggregates issues across teams for the "INTERNAL - FDE Projects" project.

**Query all FDE-related issues:**

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{
    "query": "query { issues(first: 250, filter: { or: [ { assignee: { email: { eq: \"john-mason@all-hands.dev\" } } }, { assignee: { email: { eq: \"alona@all-hands.dev\" } } } ] }) { nodes { identifier title state { name } assignee { email } team { name key } project { name } } } }"
  }' | jq -r '.data.issues.nodes[] | "\(.identifier) - \(.title) - \(.state.name) - \(.assignee.email) - Project: \(.project.name // "None")"'
```

**Get summary for a specific user:**

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{
    "query": "query { issues(first: 250, filter: { assignee: { email: { eq: \"john-mason@all-hands.dev\" } } }) { nodes { identifier title state { name } project { name } } } }"
  }' > /tmp/linear_issues.json

# Count total issues
echo "Total Issues: $(jq '.data.issues.nodes | length' /tmp/linear_issues.json)"

# Count by status
echo -e "\nBy Status:"
jq -r '.data.issues.nodes[] | .state.name' /tmp/linear_issues.json | sort | uniq -c | sort -rn

# List In Progress issues
echo -e "\nIn Progress:"
jq -r '.data.issues.nodes[] | select(.state.name == "In Progress") | "- \(.identifier): \(.title)"' /tmp/linear_issues.json

# List Todo issues
echo -e "\nTodo:"
jq -r '.data.issues.nodes[] | select(.state.name == "Todo") | "- \(.identifier): \(.title)"' /tmp/linear_issues.json
```

**Using linearctl (simpler approach):**

```bash
# List your assigned issues
lc issue mine

# Get specific issue details
lc issue get ALL-4105
```

### 2. Update Existing Issues

**Update issue status:**

```bash
# Mark issue as In Progress
lc issue update ALL-4105 --state "In Progress"

# Mark issue as Done
lc issue update ALL-4105 --state "Done"

# Mark as Todo
lc issue update ALL-4105 --state "Todo"
```

**Update multiple fields at once:**

```bash
lc issue update ALL-4105 \
  --state "In Progress" \
  --priority 2 \
  --assignee "john-mason@all-hands.dev" \
  --title "Updated title"
```

**Update priority levels:**

```bash
# Priority levels: 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
lc issue update ALL-4105 --priority 1
```

**Bulk update multiple issues:**

```bash
# Mark multiple issues as Done
for ISSUE_ID in ALL-4105 ALL-4059 ALL-4020; do
    lc issue update $ISSUE_ID --state Done
    echo "Updated $ISSUE_ID"
done
```

### 3. Create New Issues

**Create a new FDE issue:**

```bash
lc issue create \
  --team "All Hands AI" \
  --title "New FDE task" \
  --description "Details about the task" \
  --priority 3 \
  --project "INTERNAL - FDE Projects"
```

**Create and assign with labels:**

```bash
lc issue create \
  --team "All Hands AI" \
  --title "Support new customer onboarding" \
  --description "Help customer X with self-hosted setup" \
  --assignee "john-mason@all-hands.dev" \
  --priority 2 \
  --state "Todo" \
  --labels "customer-support,urgent" \
  --project "INTERNAL - FDE Projects"
```

**Create with due date:**

```bash
lc issue create \
  --team FDE \
  --title "Q1 Planning" \
  --due-date 2025-12-31 \
  --project "INTERNAL - FDE Projects"
```

## Advanced Operations

### Export Issues to CSV

```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: $LINEAR_TOKEN" \
  -d '{"query": "query { issues(first: 250, filter: { team: { key: { eq: \"FDE\" } } }) { nodes { identifier title state { name } assignee { email } priority createdAt } } }"}' \
  | jq -r '.data.issues.nodes[] | [.identifier, .title, .state.name, .assignee.email, .priority, .createdAt] | @csv' \
  > issues.csv
```

### Search Issues by Text

```bash
lc issue list --search "self-hosted" --limit 100
```

### List Available Workflow States

```bash
lc status list --team FDE
```

## GraphQL Query Examples

### Get Issues for Specific Project

```graphql
query {
  issues(first: 250, filter: {
    project: { name: { eq: "INTERNAL - FDE Projects" } }
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

### Get Issues for Multiple Teams

```graphql
query {
  issues(first: 250, filter: {
    or: [
      { team: { key: { eq: "FDE" } } },
      { team: { key: { eq: "ALL" } } }
    ]
  }) {
    nodes {
      identifier
      title
      state { name }
      team { key name }
      assignee { email }
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

**Issues not showing in team query but visible on web:**

Custom views (like `/view/fdes-8de84f7512b8`) filter by project or assignee across teams. Use GraphQL queries with appropriate filters instead of team-based queries.

## Common Use Cases

### Daily Standup Summary
```bash
# Get your current work
lc issue mine --state "In Progress"

# Get your upcoming work
lc issue mine --state "Todo" --limit 5
```

### Weekly Planning
```bash
# Create planning issue
lc issue create \
  --team "All Hands AI" \
  --title "Weekly Planning - $(date +%Y-%m-%d)" \
  --description "Planning session for upcoming week" \
  --project "INTERNAL - FDE Projects"
```

### Customer Issue Tracking
```bash
# Create customer issue
lc issue create \
  --team "All Hands AI" \
  --title "Customer: [COMPANY] - [ISSUE_SUMMARY]" \
  --description "Customer issue details..." \
  --labels "customer-support" \
  --priority 2 \
  --project "INTERNAL - FDE Projects"
```

## Best Practices

1. **Use descriptive titles**: Include customer name or project context
2. **Set appropriate priorities**: Use priority levels consistently across the team
3. **Add relevant labels**: Use labels for categorization and filtering
4. **Update status regularly**: Keep issue status current for accurate reporting
5. **Use projects**: Assign issues to the correct project for proper tracking
6. **Set due dates**: For time-sensitive work, always include due dates