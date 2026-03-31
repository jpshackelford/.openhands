#!/usr/bin/env python3
"""Generate launch URLs and badges for OpenHands plugins."""

import argparse
import base64
import json
import sys
import urllib.parse


def create_plugin_spec(source: str, ref: str | None = None, 
                       repo_path: str | None = None,
                       parameters: dict | None = None) -> dict:
    """Create a plugin specification dictionary."""
    spec = {"source": source}
    if ref:
        spec["ref"] = ref
    if repo_path:
        spec["repo_path"] = repo_path
    if parameters:
        spec["parameters"] = parameters
    return spec


def generate_launch_url(plugins: list[dict], message: str | None = None,
                        base_url: str = "https://app.all-hands.dev") -> str:
    """Generate a launch URL for the given plugins."""
    plugins_json = json.dumps(plugins)
    plugins_b64 = base64.b64encode(plugins_json.encode()).decode()
    
    url = f"{base_url}/launch?plugins={plugins_b64}"
    if message:
        url += f"&message={urllib.parse.quote(message)}"
    return url


def generate_simple_url(source: str, ref: str | None = None,
                        base_url: str = "https://app.all-hands.dev") -> str:
    """Generate a simple launch URL (dev/testing format)."""
    url = f"{base_url}/launch?plugin_source={urllib.parse.quote(source)}"
    if ref:
        url += f"&plugin_ref={urllib.parse.quote(ref)}"
    return url


def generate_badge_markdown(launch_url: str, label: str = "Launch with OpenHands") -> str:
    """Generate a shields.io badge markdown for the launch URL."""
    # OpenHands logo as base64 SVG (simple circle with 'i' icon)
    logo_svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="white" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>'
    logo_b64 = base64.b64encode(logo_svg.encode()).decode()
    
    # URL encode the label for shields.io
    label_encoded = urllib.parse.quote(label)
    badge_url = f"https://img.shields.io/badge/{label_encoded}-blue?logo=data:image/svg+xml;base64,{logo_b64}"
    
    return f"[![{label}]({badge_url})]({launch_url})"


def main():
    parser = argparse.ArgumentParser(
        description="Generate launch URLs and badges for OpenHands plugins"
    )
    parser.add_argument(
        "--source", "-s", required=True,
        help="Plugin source (e.g., 'github:owner/repo')"
    )
    parser.add_argument(
        "--ref", "-r",
        help="Branch, tag, or commit reference"
    )
    parser.add_argument(
        "--repo-path", "-p",
        help="Subdirectory path within the repository"
    )
    parser.add_argument(
        "--message", "-m",
        help="Optional message to display in the launch modal"
    )
    parser.add_argument(
        "--base-url", "-u", default="https://app.all-hands.dev",
        help="Base URL for OpenHands (default: https://app.all-hands.dev)"
    )
    parser.add_argument(
        "--simple", action="store_true",
        help="Generate simple URL format (for dev/testing)"
    )
    parser.add_argument(
        "--badge", action="store_true",
        help="Output as markdown badge"
    )
    parser.add_argument(
        "--badge-label", default="Launch with OpenHands",
        help="Badge label text"
    )
    parser.add_argument(
        "--parameters", "-P",
        help="JSON string of parameters to include"
    )
    
    args = parser.parse_args()
    
    # Parse parameters if provided
    parameters = None
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON for parameters: {args.parameters}", file=sys.stderr)
            sys.exit(1)
    
    if args.simple:
        url = generate_simple_url(args.source, args.ref, args.base_url)
    else:
        plugin = create_plugin_spec(args.source, args.ref, args.repo_path, parameters)
        url = generate_launch_url([plugin], args.message, args.base_url)
    
    if args.badge:
        print(generate_badge_markdown(url, args.badge_label))
    else:
        print(url)


if __name__ == "__main__":
    main()
