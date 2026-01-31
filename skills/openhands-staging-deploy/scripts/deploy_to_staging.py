#!/usr/bin/env python3
"""
Deploy an OpenHands PR to staging environment.

Usage:
    python deploy_to_staging.py <openhands_pr_number> [--create-only] [--update-only] [--deploy]

Arguments:
    openhands_pr_number: The PR number from All-Hands-AI/OpenHands repo

Options:
    --create-only: Only create the preview PR, don't deploy to staging
    --update-only: Only update existing preview PR with latest commit
    --deploy: After creating/updating, trigger staging deployment

Environment:
    GITHUB_TOKEN: Required for GitHub API access
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import http.client
import urllib.parse

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
DEPLOY_REPO = "All-Hands-AI/deploy"
OPENHANDS_REPO = "All-Hands-AI/OpenHands"


def github_api(endpoint, method="GET", data=None, follow_redirects=True, max_redirects=5):
    """Make a GitHub API request with redirect handling."""
    url = f"https://api.github.com/{endpoint}"

    for _ in range(max_redirects):
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "openhands-staging-deploy",
        }

        body = None
        if data:
            headers["Content-Type"] = "application/json"
            body = json.dumps(data)

        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        response_body = response.read().decode()

        if response.status in (301, 302, 307, 308) and follow_redirects:
            location = response.getheader("Location")
            if location:
                url = location
                # For 307/308, preserve the method and body
                if response.status not in (307, 308):
                    method = "GET"
                    data = None
                continue

        if response.status == 204:
            return None
        if response.status == 404:
            return None
        if response.status >= 400:
            print(f"GitHub API error: {response.status} - {response_body}", file=sys.stderr)
            return None
        if response_body:
            return json.loads(response_body)
        return None

    print("Too many redirects", file=sys.stderr)
    return None


def get_openhands_pr_info(pr_number):
    """Get information about an OpenHands PR."""
    pr_data = github_api(f"repos/{OPENHANDS_REPO}/pulls/{pr_number}")
    if not pr_data:
        print(f"Error: Could not find OpenHands PR #{pr_number}", file=sys.stderr)
        sys.exit(1)

    return {
        "number": pr_data["number"],
        "state": pr_data["state"],
        "head_sha": pr_data["head"]["sha"],
        "head_ref": pr_data["head"]["ref"],
        "title": pr_data["title"],
        "html_url": pr_data["html_url"],
    }


def find_existing_preview_pr(openhands_pr_number):
    """Find an existing preview PR for the given OpenHands PR."""
    prs = github_api(f"repos/{DEPLOY_REPO}/pulls?state=open&per_page=100")
    if not prs:
        return None

    search_title = f"OpenHands PR #{openhands_pr_number}"
    for pr in prs:
        if search_title in pr.get("title", ""):
            return {
                "number": pr["number"],
                "branch": pr["head"]["ref"],
                "title": pr["title"],
                "html_url": pr["html_url"],
                "head_sha": pr["head"]["sha"],
            }
    return None


def trigger_create_preview_workflow(openhands_pr_number):
    """Trigger the create-openhands-preview-pr workflow."""
    print(f"Triggering preview PR creation workflow for OpenHands PR #{openhands_pr_number}...")
    github_api(
        f"repos/{DEPLOY_REPO}/actions/workflows/create-openhands-preview-pr.yaml/dispatches",
        method="POST",
        data={"ref": "main", "inputs": {"prNumber": str(openhands_pr_number)}},
    )
    print("Workflow triggered. Check GitHub Actions for progress.")
    print(f"  https://github.com/{DEPLOY_REPO}/actions/workflows/create-openhands-preview-pr.yaml")


def update_deploy_yaml(deploy_yaml_path, commit_sha):
    """Update deploy.yaml with new SHA values using sed (yq fallback)."""
    runtime_tag = f"{commit_sha}-nikolaik"

    # Try yq first, fall back to sed
    try:
        subprocess.run(
            ["yq", "e", "-i", f'.env.OPENHANDS_SHA = "{commit_sha}"', deploy_yaml_path],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["yq", "e", "-i", f'.env.OPENHANDS_RUNTIME_IMAGE_TAG = "{runtime_tag}"', deploy_yaml_path],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        # yq not installed, use sed
        # Update OPENHANDS_SHA line
        subprocess.run(
            [
                "sed",
                "-i",
                f's/^  OPENHANDS_SHA: .*/  OPENHANDS_SHA: "{commit_sha}"/',
                deploy_yaml_path,
            ],
            check=True,
            capture_output=True,
        )
        # Update OPENHANDS_RUNTIME_IMAGE_TAG line
        subprocess.run(
            [
                "sed",
                "-i",
                f's/^  OPENHANDS_RUNTIME_IMAGE_TAG: .*/  OPENHANDS_RUNTIME_IMAGE_TAG: "{runtime_tag}"/',
                deploy_yaml_path,
            ],
            check=True,
            capture_output=True,
        )


def update_preview_pr(deploy_branch, commit_sha, openhands_pr_number):
    """Update an existing preview PR with a new commit SHA."""
    print(f"Updating preview branch {deploy_branch} with commit {commit_sha[:12]}...")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = os.path.join(tmpdir, "deploy")

        # Clone the repo
        subprocess.run(
            ["git", "clone", f"https://{GITHUB_TOKEN}@github.com/{DEPLOY_REPO}.git", repo_dir],
            check=True,
            capture_output=True,
        )

        # Checkout the preview branch
        subprocess.run(
            ["git", "checkout", deploy_branch],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        # Update deploy.yaml
        deploy_yaml = os.path.join(repo_dir, ".github/workflows/deploy.yaml")
        runtime_tag = f"{commit_sha}-nikolaik"

        update_deploy_yaml(deploy_yaml, commit_sha)

        # Commit and push
        subprocess.run(
            ["git", "add", ".github/workflows/deploy.yaml"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

        commit_msg = f"""Update to latest commit from OpenHands PR #{openhands_pr_number}

OPENHANDS_SHA: {commit_sha}
OPENHANDS_RUNTIME_IMAGE_TAG: {runtime_tag}"""

        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_dir,
            capture_output=True,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode()
            if "nothing to commit" in stderr:
                print("No changes to commit - already at latest SHA.")
                return
            raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)

        subprocess.run(
            ["git", "push"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )

    print(f"Preview branch updated successfully.")


def trigger_staging_deployment(deploy_branch, openhands_pr_number):
    """Trigger deployment to staging environment."""
    print(f"Triggering staging deployment from branch {deploy_branch}...")
    github_api(
        f"repos/{DEPLOY_REPO}/actions/workflows/deploy.yaml/dispatches",
        method="POST",
        data={
            "ref": deploy_branch,
            "inputs": {
                "deployEnvironment": "staging",
                "openhandsPrNumber": str(openhands_pr_number),
            },
        },
    )
    print("Staging deployment triggered.")
    print(f"  Monitor at: https://github.com/{DEPLOY_REPO}/actions/workflows/deploy.yaml")


def main():
    parser = argparse.ArgumentParser(description="Deploy an OpenHands PR to staging")
    parser.add_argument("pr_number", type=int, help="OpenHands PR number")
    parser.add_argument("--create-only", action="store_true", help="Only create preview PR")
    parser.add_argument("--update-only", action="store_true", help="Only update existing PR")
    parser.add_argument("--deploy", action="store_true", help="Trigger staging deployment")
    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Get OpenHands PR info
    print(f"\n=== OpenHands PR #{args.pr_number} ===")
    oh_pr = get_openhands_pr_info(args.pr_number)
    print(f"  Title: {oh_pr['title']}")
    print(f"  State: {oh_pr['state']}")
    print(f"  HEAD SHA: {oh_pr['head_sha'][:12]}")
    print(f"  URL: {oh_pr['html_url']}")

    if oh_pr["state"] != "open":
        print(f"\nWarning: PR is {oh_pr['state']}, not open")

    # Check for existing preview PR
    print(f"\n=== Checking for existing preview PR ===")
    preview_pr = find_existing_preview_pr(args.pr_number)

    if preview_pr:
        print(f"Found existing preview PR #{preview_pr['number']}")
        print(f"  Branch: {preview_pr['branch']}")
        print(f"  URL: {preview_pr['html_url']}")

        if args.create_only:
            print("\n--create-only specified but preview PR already exists.")
            sys.exit(0)

        # Update existing PR
        print(f"\n=== Updating preview PR ===")
        update_preview_pr(preview_pr["branch"], oh_pr["head_sha"], args.pr_number)

        if args.deploy:
            print(f"\n=== Deploying to staging ===")
            trigger_staging_deployment(preview_pr["branch"], args.pr_number)

    else:
        print("No existing preview PR found.")

        if args.update_only:
            print("\n--update-only specified but no preview PR exists.")
            sys.exit(1)

        # Create new preview PR via workflow
        print(f"\n=== Creating preview PR ===")
        trigger_create_preview_workflow(args.pr_number)

        if args.deploy:
            print("\nNote: Cannot deploy to staging until preview PR is created.")
            print("Wait for the workflow to complete, then run again with --deploy")

    print("\n=== Done ===")
    print(f"Staging URL (after deployment): https://staging.all-hands.dev")


if __name__ == "__main__":
    main()
