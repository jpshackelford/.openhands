---
name: openhands-workspace-setup
description: Set up a complete OpenHands development workspace by cloning all necessary repositories. Use when preparing for OpenHands development work.
triggers:
  - setup the workspace for openhands development
  - setup openhands workspace
  - prepare openhands development environment
  - clone openhands repositories
  - openhands development setup
  - openhands workspace
---

# OpenHands Workspace Setup

This skill helps set up a complete OpenHands development workspace by cloning all necessary repositories and preparing the environment for development.

## Repository Overview

OpenHands repositories are split between two GitHub organizations:

### OpenHands Organization (github.com/OpenHands)
Public/open-source repositories:
- **OpenHands** - Main OpenHands application
- **software-agent-sdk** - Agent SDK for building AI agents
- **runtime-api** - Runtime API service
- **deploy** - Deployment configurations
- **docs** - Public documentation
- **skills** - Official skill registry

### All-Hands-AI Organization (github.com/All-Hands-AI)
Internal/enterprise repositories:
- **OpenHands-Cloud** - Cloud platform
- **infra** - Infrastructure configurations
- **docs-enterprise** - Enterprise documentation
- **runtime** - Runtime service

## Quick Setup

```bash
# Navigate to workspace
cd /workspace/project

# Clone core OpenHands repositories
git clone https://${GITHUB_TOKEN}@github.com/OpenHands/OpenHands.git
git clone https://${GITHUB_TOKEN}@github.com/OpenHands/software-agent-sdk.git
git clone https://${GITHUB_TOKEN}@github.com/OpenHands/runtime-api.git
git clone https://${GITHUB_TOKEN}@github.com/OpenHands/deploy.git

# Clone internal repositories (requires appropriate access)
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/OpenHands-Cloud.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/infra.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/docs-enterprise.git

# Verify all repositories were cloned successfully
ls -la /workspace/project/
```

## Authentication

- The `GITHUB_TOKEN` environment variable is already available in the environment
- Use HTTPS cloning format: `https://${GITHUB_TOKEN}@github.com/ORG/REPO.git`
- No additional authentication setup is required

## Pre-Development Setup

Before making code changes to any repository:

1. **Run the setup script**: Execute the `.openhands/setup.sh` file within the repository where you intend to make code changes (if it exists)
2. **Read repository documentation**: Review the `AGENTS.md` or `.openhands/microagents/repo.md` file for repository-specific guidelines

## Usage Example

```bash
# Clone and set up OpenHands main repo
cd /workspace/project
git clone https://${GITHUB_TOKEN}@github.com/OpenHands/OpenHands.git
cd OpenHands

# Run setup if available
if [ -f .openhands/setup.sh ]; then
    ./.openhands/setup.sh
fi

# Read repo guidelines
cat AGENTS.md 2>/dev/null || cat .openhands/microagents/repo.md 2>/dev/null
```

## Repository Descriptions

| Repository | Organization | Purpose |
|------------|--------------|---------|
| OpenHands | OpenHands | Core application - AI coding agent |
| software-agent-sdk | OpenHands | SDK for building software agents |
| runtime-api | OpenHands | API for managing runtime environments |
| deploy | OpenHands | Deployment scripts and configurations |
| OpenHands-Cloud | All-Hands-AI | Cloud platform and UI |
| infra | All-Hands-AI | Infrastructure as code |
| docs-enterprise | All-Hands-AI | Enterprise documentation |
