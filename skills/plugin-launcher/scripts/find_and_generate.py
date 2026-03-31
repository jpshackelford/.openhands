#!/usr/bin/env python3
"""Find a plugin or skill by name in a repository and generate a launch URL/badge."""

import argparse
import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from typing import Any


def github_api_get(endpoint: str, token: str | None = None) -> dict | list | None:
    """Make a GET request to the GitHub API."""
    url = f"https://api.github.com{endpoint}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        return None


def github_raw_get(owner: str, repo: str, path: str, ref: str = "main") -> str | None:
    """Get raw file content from GitHub."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.read().decode()
    except Exception:
        return None


def find_in_marketplace(owner: str, repo: str, name: str, token: str | None = None) -> dict | None:
    """Look for a plugin/skill in the marketplace.json file."""
    # Check for .claude-plugin/marketplace.json
    content = github_api_get(f"/repos/{owner}/{repo}/contents/.claude-plugin/marketplace.json", token)
    
    if content is None:
        return None
    
    # Check if it's a symlink (content is just a path)
    if isinstance(content, dict) and content.get("type") == "file":
        # Decode content
        if content.get("encoding") == "base64":
            file_content = base64.b64decode(content["content"]).decode()
        else:
            file_content = content.get("content", "")
        
        # Check if it's a symlink/redirect
        file_content = file_content.strip()
        if file_content.startswith("../") or file_content.startswith("./"):
            # It's a relative path, fetch the actual file
            # Resolve the path (e.g., "../marketplaces/default.json")
            actual_path = file_content.lstrip("./")
            if actual_path.startswith("../"):
                actual_path = actual_path[3:]  # Remove "../"
            marketplace_content = github_raw_get(owner, repo, actual_path)
            if marketplace_content:
                file_content = marketplace_content
        
        # Try to parse as JSON
        try:
            marketplace = json.loads(file_content)
        except json.JSONDecodeError:
            return None
        
        # Look for the plugin/skill in the marketplace
        plugins = marketplace.get("plugins", [])
        plugin_root = marketplace.get("metadata", {}).get("pluginRoot", "./plugins")
        plugin_root = plugin_root.lstrip("./")
        
        for plugin in plugins:
            if plugin.get("name") == name:
                source_path = plugin.get("source", f"./{name}").lstrip("./")
                return {
                    "name": name,
                    "repo_path": f"{plugin_root}/{source_path}" if not source_path.startswith(plugin_root) else source_path,
                    "description": plugin.get("description"),
                    "type": "skill" if "skill" in plugin_root.lower() else "plugin"
                }
    
    return None


def find_in_directory(owner: str, repo: str, name: str, directory: str, token: str | None = None) -> dict | None:
    """Check if a plugin/skill exists in a specific directory."""
    content = github_api_get(f"/repos/{owner}/{repo}/contents/{directory}/{name}", token)
    
    if content is None or not isinstance(content, list):
        return None
    
    # Verify it's a valid plugin/skill
    file_names = [f["name"] for f in content if f["type"] == "file"]
    dir_names = [f["name"] for f in content if f["type"] == "dir"]
    
    # Check for skill marker
    if "SKILL.md" in file_names:
        return {
            "name": name,
            "repo_path": f"{directory}/{name}",
            "type": "skill"
        }
    
    # Check for plugin markers
    if ".claude-plugin" in dir_names or "commands" in dir_names or "plugin.json" in file_names:
        return {
            "name": name,
            "repo_path": f"{directory}/{name}",
            "type": "plugin"
        }
    
    # If we found something but can't determine type, assume based on directory
    return {
        "name": name,
        "repo_path": f"{directory}/{name}",
        "type": "skill" if "skill" in directory.lower() else "plugin"
    }


def find_plugin_or_skill(owner: str, repo: str, name: str, token: str | None = None) -> dict | None:
    """Find a plugin or skill by name in a repository."""
    # First, check the marketplace
    result = find_in_marketplace(owner, repo, name, token)
    if result:
        return result
    
    # Check common directories
    for directory in ["skills", "plugins", "."]:
        result = find_in_directory(owner, repo, name, directory, token)
        if result:
            return result
    
    return None


def generate_launch_url(source: str, repo_path: str, ref: str = "main",
                        message: str | None = None,
                        base_url: str = "https://app.all-hands.dev") -> str:
    """Generate a launch URL."""
    plugin_spec = {"source": source, "ref": ref, "repo_path": repo_path}
    plugins_b64 = base64.b64encode(json.dumps([plugin_spec]).encode()).decode()
    
    url = f"{base_url}/launch?plugins={plugins_b64}"
    if message:
        url += f"&message={urllib.parse.quote(message)}"
    return url


def generate_badge_markdown(launch_url: str, label: str) -> str:
    """Generate shields.io badge markdown."""
    logo_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
    logo_b64 = base64.b64encode(logo_svg.encode()).decode()
    label_encoded = urllib.parse.quote(label)
    badge_url = f"https://img.shields.io/badge/{label_encoded}-blue?logo=data:image/svg+xml;base64,{logo_b64}"
    return f"[![{label}]({badge_url})]({launch_url})"


def main():
    parser = argparse.ArgumentParser(
        description="Find a plugin or skill by name and generate a launch URL/badge"
    )
    parser.add_argument(
        "--repo", "-r", required=True,
        help="GitHub repository (owner/repo)"
    )
    parser.add_argument(
        "--name", "-n", required=True,
        help="Plugin or skill name to find"
    )
    parser.add_argument(
        "--ref", default="main",
        help="Branch, tag, or commit (default: main)"
    )
    parser.add_argument(
        "--message", "-m",
        help="Optional message for the launch modal"
    )
    parser.add_argument(
        "--base-url", "-u", default="https://app.all-hands.dev",
        help="Base URL for OpenHands"
    )
    parser.add_argument(
        "--badge", "-b", action="store_true",
        help="Output as markdown badge"
    )
    parser.add_argument(
        "--badge-label", "-l",
        help="Custom badge label (default: 'Try <name>')"
    )
    parser.add_argument(
        "--json", "-j", action="store_true",
        help="Output result as JSON"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed search progress"
    )
    
    args = parser.parse_args()
    
    # Parse repo
    repo_parts = args.repo.strip("/").split("/")
    if len(repo_parts) != 2:
        print(f"Error: Invalid repository format. Expected 'owner/repo', got '{args.repo}'", file=sys.stderr)
        sys.exit(1)
    owner, repo = repo_parts
    
    # Get GitHub token from environment
    token = os.environ.get("GITHUB_TOKEN")
    
    if args.verbose:
        print(f"Searching for '{args.name}' in {owner}/{repo}...", file=sys.stderr)
    
    # Find the plugin/skill
    result = find_plugin_or_skill(owner, repo, args.name, token)
    
    if result is None:
        print(f"Error: Could not find '{args.name}' in {owner}/{repo}", file=sys.stderr)
        print("\nTry checking:", file=sys.stderr)
        print(f"  - https://github.com/{owner}/{repo}/tree/main/skills/{args.name}", file=sys.stderr)
        print(f"  - https://github.com/{owner}/{repo}/tree/main/plugins/{args.name}", file=sys.stderr)
        sys.exit(1)
    
    if args.verbose:
        print(f"Found {result['type']}: {result['name']} at {result['repo_path']}", file=sys.stderr)
    
    # Generate launch URL
    source = f"github:{owner}/{repo}"
    launch_url = generate_launch_url(
        source=source,
        repo_path=result["repo_path"],
        ref=args.ref,
        message=args.message,
        base_url=args.base_url
    )
    
    if args.json:
        output = {
            "name": result["name"],
            "type": result["type"],
            "repo_path": result["repo_path"],
            "source": source,
            "ref": args.ref,
            "launch_url": launch_url,
        }
        if result.get("description"):
            output["description"] = result["description"]
        print(json.dumps(output, indent=2))
    elif args.badge:
        label = args.badge_label or f"Try {result['name'].replace('-', ' ').title()}"
        print(generate_badge_markdown(launch_url, label))
    else:
        print(launch_url)


if __name__ == "__main__":
    main()
