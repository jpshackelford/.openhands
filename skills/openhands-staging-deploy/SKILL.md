---
name: openhands-staging-deploy
description: Deploy OpenHands PRs to staging environment. Use when you need to deploy an OpenHands PR to staging, create a preview PR in the deploy repo, update an existing preview deployment with the latest code, or check deployment status. Triggers include "deploy to staging", "create preview PR", "staging deployment", "deploy PR", "preview environment".
---

# OpenHands Staging Deployment

Deploy OpenHands PRs to the staging environment via the All-Hands-AI/deploy repository.

## Quick Start

Use the bundled script for common operations:

```bash
# Deploy an OpenHands PR to staging (creates or updates preview PR, then deploys)
python scripts/deploy_to_staging.py 12699 --deploy

# Only create the preview PR (no deployment)
python scripts/deploy_to_staging.py 12699 --create-only

# Only update existing preview PR with latest commit
python scripts/deploy_to_staging.py 12699 --update-only

# Update and deploy to staging
python scripts/deploy_to_staging.py 12699 --deploy
```

The script will:
1. Get the latest commit SHA from the OpenHands PR
2. Check if a preview PR already exists
3. Create or update the preview PR as needed
4. Optionally trigger deployment to staging

## Overview

The deploy repo uses preview PRs to deploy specific OpenHands PR commits to staging. Each preview PR:
- Has a branch named `ohpr-{PR_NUMBER}-{random}` (e.g., `ohpr-12699-607`)
- Has title "Preview: OpenHands PR #{number}"
- Updates image tags in `.github/workflows/deploy.yaml`
- Auto-deploys when pushed to the branch

## Manual Workflow

### Step 1: Get OpenHands PR Information

```bash
OHPR_NUMBER=12345  # Replace with actual PR number
PR_DATA=$(curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/OpenHands/pulls/$OHPR_NUMBER")
COMMIT_SHA=$(echo "$PR_DATA" | jq -r '.head.sha')
PR_STATE=$(echo "$PR_DATA" | jq -r '.state')

echo "OpenHands PR #$OHPR_NUMBER"
echo "  State: $PR_STATE"
echo "  HEAD SHA: $COMMIT_SHA"
```

### Step 2: Check for Existing Preview PR

```bash
# List all open preview PRs for this OpenHands PR
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/deploy/pulls?state=open&per_page=100" | \
  jq -r --arg num "$OHPR_NUMBER" '.[] | select(.title | contains("OpenHands PR #" + $num)) | 
    "PR #\(.number): \(.head.ref) - \(.title)\n  URL: \(.html_url)"'
```

### Step 3a: Create New Preview PR (if none exists)

Option A - Trigger the GitHub workflow (preferred):
```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/All-Hands-AI/deploy/actions/workflows/create-openhands-preview-pr.yaml/dispatches" \
  -d "{\"ref\": \"main\", \"inputs\": {\"prNumber\": \"$OHPR_NUMBER\"}}"
```

Option B - Manually create the PR:
```bash
cd /tmp && rm -rf deploy-temp
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/deploy.git deploy-temp
cd deploy-temp

BRANCH_NAME="ohpr-$OHPR_NUMBER-$((RANDOM % 1000 + 1))"
git checkout -b "$BRANCH_NAME"

# Update deploy.yaml with the commit SHA
# The runtime image tag format is: {commit_sha}-nikolaik
yq e -i ".env.OPENHANDS_SHA = \"$COMMIT_SHA\"" .github/workflows/deploy.yaml
yq e -i ".env.OPENHANDS_RUNTIME_IMAGE_TAG = \"${COMMIT_SHA}-nikolaik\"" .github/workflows/deploy.yaml

git add .github/workflows/deploy.yaml
git commit -m "Auto-update deploy.yaml SHAs for OpenHands PR #$OHPR_NUMBER"
git push -u origin "$BRANCH_NAME"

# Create the PR using gh CLI
gh pr create \
  --title "Preview: OpenHands PR #$OHPR_NUMBER" \
  --body "**Preview branch for OpenHands PR #$OHPR_NUMBER**

This branch updates the deployment configuration to use the latest commit from OpenHands/OpenHands PR #$OHPR_NUMBER.

**Changes:**
- \`OPENHANDS_SHA\` → \`$COMMIT_SHA\`
- \`OPENHANDS_RUNTIME_IMAGE_TAG\` → \`${COMMIT_SHA}-nikolaik\`

**Source PR:** https://github.com/All-Hands-AI/OpenHands/pull/$OHPR_NUMBER" \
  --base main
```

### Step 3b: Update Existing Preview PR

```bash
# Get the existing preview PR branch
DEPLOY_PR_INFO=$(curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/deploy/pulls?state=open&per_page=100" | \
  jq -r --arg num "$OHPR_NUMBER" '.[] | select(.title | contains("OpenHands PR #" + $num)) | 
    {number: .number, branch: .head.ref}' | head -1)
    
DEPLOY_PR_NUMBER=$(echo "$DEPLOY_PR_INFO" | jq -r '.number')
DEPLOY_BRANCH=$(echo "$DEPLOY_PR_INFO" | jq -r '.branch')

cd /tmp && rm -rf deploy-temp
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/deploy.git deploy-temp
cd deploy-temp
git checkout "$DEPLOY_BRANCH"

# Update with latest commit SHA
yq e -i ".env.OPENHANDS_SHA = \"$COMMIT_SHA\"" .github/workflows/deploy.yaml
yq e -i ".env.OPENHANDS_RUNTIME_IMAGE_TAG = \"${COMMIT_SHA}-nikolaik\"" .github/workflows/deploy.yaml

git add .github/workflows/deploy.yaml
git commit -m "Update to latest commit from OpenHands PR #$OHPR_NUMBER

OPENHANDS_SHA: $COMMIT_SHA
OPENHANDS_RUNTIME_IMAGE_TAG: ${COMMIT_SHA}-nikolaik"
git push
```

### Step 4: Deploy to Staging

After the preview PR exists, trigger deployment to staging:

```bash
# Get the SHA of the preview branch tip
DEPLOY_BRANCH_SHA=$(curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/deploy/branches/$DEPLOY_BRANCH" | jq -r '.commit.sha')

curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/All-Hands-AI/deploy/actions/workflows/deploy.yaml/dispatches" \
  -d "{
    \"ref\": \"$DEPLOY_BRANCH\",
    \"inputs\": {
      \"deployEnvironment\": \"staging\",
      \"openhandsPrNumber\": \"$OHPR_NUMBER\"
    }
  }"
```

### Step 5: Monitor Deployment

Check the workflow run status:
```bash
# List recent workflow runs for the deploy workflow
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/deploy/actions/workflows/deploy.yaml/runs?per_page=5" | \
  jq -r '.workflow_runs[] | "\(.id): \(.status) - \(.conclusion // "in_progress") - \(.head_branch)"'
```

## Image Tag Formats

| Variable | Format | Example |
|----------|--------|---------|
| `OPENHANDS_SHA` | Full commit SHA | `e688fba761d896a80dfa6b05b7c2221620e7b8be` |
| `OPENHANDS_RUNTIME_IMAGE_TAG` | `{sha}-nikolaik` | `e688fba761d896a80dfa6b05b7c2221620e7b8be-nikolaik` |

## Important Notes

1. **Preview PRs auto-close after 5 days** - The `close-stale-ohpr.yml` workflow closes old preview PRs
2. **Staging deployment requires workflow_dispatch** - Just pushing to a preview branch deploys to feature environment, not staging
3. **The deploy repo uses `All-Hands-AI/deploy`** - Note: The org name is `All-Hands-AI` (with hyphens)
4. **Branch naming** - Preview branches follow pattern `ohpr-{PR_NUMBER}-{random}`
5. **Enterprise image tag** - For enterprise builds, can override with `sha-{OPENHANDS_SHA}` or `pr-{number}` format

## Staging Environment URL

After deployment, the staging environment is available at:
- **Main app**: https://staging.all-hands.dev
- **Feature branch**: https://{branch-sanitized}.staging.all-hands.dev

## Troubleshooting

### Check if images exist
```bash
# Check if runtime image exists
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/orgs/openhands/packages/container/runtime/versions" | \
  jq -r --arg tag "${COMMIT_SHA}-nikolaik" '.[] | select(.metadata.container.tags[] | contains($tag)) | .metadata.container.tags[]' | head -5
```

### View current deploy.yaml values
```bash
curl -sL -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/All-Hands-AI/deploy/contents/.github/workflows/deploy.yaml?ref=$DEPLOY_BRANCH" | \
  jq -r '.content' | base64 -d | head -50
```
