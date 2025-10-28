---
name: OpenHands Workspace Setup
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers:
  - "setup the workspace for openhands development"
  - "setup openhands workspace"
  - "prepare openhands development environment"
  - "clone openhands repositories"
---

# OpenHands Workspace Setup Microagent

This microagent helps set up a complete OpenHands development workspace by cloning all necessary repositories and preparing the environment for development.

## Purpose

When asked to setup the workspace for OpenHands development, this microagent will:

1. Clone all core OpenHands repositories to `/workspace/project/`
2. Provide guidance on running setup scripts before making code changes
3. Remind developers to read repository-specific documentation

## Required Repositories

The following repositories should be cloned for a complete OpenHands development environment:

```bash
# Navigate to workspace
cd /workspace/project

# Clone core OpenHands repositories
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/OpenHands.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/OpenHands-Cloud.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/infra.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/agent-sdk.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/deploy.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/docs-enterprise.git
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/runtime-api.git

# Verify all repositories were cloned successfully
ls -la /workspace/project/
```

## Authentication

- The `GITHUB_TOKEN` environment variable is already available in the environment
- Use HTTPS cloning format: `https://${GITHUB_TOKEN}@github.com/All-Hands-AI/REPO.git`
- No additional authentication setup is required

## Pre-Development Setup

Before making code changes to any repository:

1. **Run the setup script**: Execute the `.openhands/setup.sh` file within the repository where you intend to make code changes
2. **Read repository documentation**: Review the `.openhands/microagents/repo.md` file for any repository-specific guidelines and information

## Usage Example

When a user requests workspace setup, execute the repository cloning commands and remind them about the pre-development requirements:

```bash
# Example workflow
cd /workspace/project
git clone https://${GITHUB_TOKEN}@github.com/All-Hands-AI/OpenHands.git
# ... (clone other repositories)

# Before making changes to OpenHands repository:
cd OpenHands
./.openhands/setup.sh
cat .openhands/microagents/repo.md
```

## Important Notes

- This microagent does not have specific triggers - it responds to natural language requests about workspace setup
- Always verify successful cloning of all repositories
- Ensure the workspace directory `/workspace/project/` exists before cloning
- The setup process may take several minutes depending on repository sizes