#!/usr/bin/env python3
"""Generate HTML test pages for OpenHands plugins."""

import argparse
import base64
import json
import sys
import urllib.parse
from pathlib import Path

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
      max-width: 900px;
      margin: 0 auto;
      padding: 20px;
      background: #1a1a2e;
      color: #eaeaea;
    }}
    h1 {{
      color: #4ecdc4;
      border-bottom: 2px solid #4ecdc4;
      padding-bottom: 10px;
    }}
    h2 {{
      color: #ff6b6b;
      margin-top: 30px;
    }}
    .config {{
      background: #16213e;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 25px;
    }}
    .config label {{
      display: block;
      margin-bottom: 8px;
      font-weight: 600;
    }}
    .config input {{
      width: 100%;
      padding: 10px;
      border: 1px solid #4ecdc4;
      border-radius: 4px;
      background: #0f0f23;
      color: #eaeaea;
      font-size: 14px;
      box-sizing: border-box;
    }}
    .test-case {{
      background: #16213e;
      padding: 20px;
      margin: 20px 0;
      border-radius: 8px;
      border-left: 4px solid #4ecdc4;
    }}
    .test-case h3 {{
      margin-top: 0;
      color: #f8f8f2;
    }}
    .test-case p {{
      margin: 10px 0;
      color: #bbb;
    }}
    .test-case strong {{
      color: #ff79c6;
    }}
    .test-case code {{
      background: #0f0f23;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 12px;
      color: #50fa7b;
    }}
    .test-case button {{
      background: #4ecdc4;
      color: #1a1a2e;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      margin-top: 10px;
    }}
    .test-case button:hover {{
      background: #45b7b0;
    }}
    .instructions {{
      background: #2d2d44;
      padding: 15px;
      border-radius: 8px;
      margin: 20px 0;
    }}
    .instructions ol {{
      margin: 0;
      padding-left: 20px;
    }}
    .instructions li {{
      margin: 8px 0;
    }}
    .plugin-info {{
      background: #0f0f23;
      padding: 15px;
      border-radius: 8px;
      margin: 15px 0;
      font-family: monospace;
      font-size: 13px;
    }}
    .plugin-info pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
    }}
    .url-display {{
      background: #0f0f23;
      padding: 10px;
      border-radius: 4px;
      margin-top: 10px;
      word-break: break-all;
      font-family: monospace;
      font-size: 12px;
      color: #50fa7b;
    }}
    .copy-btn {{
      background: #666;
      color: white;
      border: none;
      padding: 5px 10px;
      border-radius: 3px;
      cursor: pointer;
      font-size: 12px;
      margin-left: 10px;
    }}
    .copy-btn:hover {{
      background: #888;
    }}
  </style>
</head>
<body>
  <h1>🚀 {title}</h1>
  <p>{description}</p>

  <div class="config">
    <label for="baseUrl">Base URL (your OpenHands server):</label>
    <input type="text" id="baseUrl" value="{default_base_url}" placeholder="https://app.all-hands.dev">
  </div>

  <div class="instructions">
    <h3>📋 Instructions</h3>
    <ol>
      <li>Verify the "Base URL" points to your OpenHands instance</li>
      <li>Click "Launch Plugin" to open the launch modal</li>
      <li>Review plugin configuration and click "Start Conversation"</li>
    </ol>
  </div>

  <h2>Plugin Configuration</h2>
  
  <div class="plugin-info">
    <pre>{plugin_json}</pre>
  </div>

  <div class="test-case">
    <h3>Launch: {plugin_name}</h3>
    <p><strong>Source:</strong> <code>{source}</code></p>
    {ref_html}
    {repo_path_html}
    {message_html}
    <div class="url-display" id="launchUrl"></div>
    <button onclick="launchPlugin()">Launch Plugin</button>
    <button class="copy-btn" onclick="copyUrl()">Copy URL</button>
  </div>

  <h2>Generated URLs</h2>

  <div class="test-case">
    <h3>Full URL (Base64 encoded)</h3>
    <p>Production format with base64-encoded plugin configuration:</p>
    <div class="url-display" id="fullUrl"></div>
    <button class="copy-btn" onclick="copyFullUrl()">Copy</button>
  </div>

  {simple_url_section}

  <script>
    const pluginConfig = {plugin_json_js};
    const message = {message_js};

    function getBaseUrl() {{
      return document.getElementById('baseUrl').value.replace(/\\/$/, '');
    }}

    function encodePlugins(plugins) {{
      return btoa(JSON.stringify(plugins));
    }}

    function generateFullUrl() {{
      const baseUrl = getBaseUrl();
      let url = `${{baseUrl}}/launch?plugins=${{encodePlugins(pluginConfig)}}`;
      if (message) {{
        url += `&message=${{encodeURIComponent(message)}}`;
      }}
      return url;
    }}

    function generateSimpleUrl() {{
      const baseUrl = getBaseUrl();
      const plugin = pluginConfig[0];
      let url = `${{baseUrl}}/launch?plugin_source=${{encodeURIComponent(plugin.source)}}`;
      if (plugin.ref) {{
        url += `&plugin_ref=${{encodeURIComponent(plugin.ref)}}`;
      }}
      return url;
    }}

    function updateUrls() {{
      document.getElementById('launchUrl').textContent = generateFullUrl();
      document.getElementById('fullUrl').textContent = generateFullUrl();
      const simpleEl = document.getElementById('simpleUrl');
      if (simpleEl) {{
        simpleEl.textContent = generateSimpleUrl();
      }}
    }}

    function launchPlugin() {{
      window.open(generateFullUrl(), '_blank');
    }}

    function copyUrl() {{
      navigator.clipboard.writeText(generateFullUrl());
    }}

    function copyFullUrl() {{
      navigator.clipboard.writeText(generateFullUrl());
    }}

    function copySimpleUrl() {{
      navigator.clipboard.writeText(generateSimpleUrl());
    }}

    // Update URLs when base URL changes
    document.getElementById('baseUrl').addEventListener('input', updateUrls);
    
    // Initial URL generation
    updateUrls();
  </script>
</body>
</html>
'''

SIMPLE_URL_SECTION = '''
  <div class="test-case">
    <h3>Simple URL (Dev/Testing)</h3>
    <p>Simpler format for testing (single plugin, no parameters):</p>
    <div class="url-display" id="simpleUrl"></div>
    <button class="copy-btn" onclick="copySimpleUrl()">Copy</button>
  </div>
'''


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


def generate_test_page(plugin: dict, title: str, description: str,
                       message: str | None = None,
                       default_base_url: str = "https://app.all-hands.dev",
                       include_simple_url: bool = True) -> str:
    """Generate an HTML test page for a plugin."""
    
    plugin_json = json.dumps([plugin], indent=2)
    plugin_json_js = json.dumps([plugin])
    
    # Extract plugin name from source
    source = plugin.get("source", "")
    plugin_name = source.split("/")[-1] if "/" in source else source
    if plugin.get("repo_path"):
        plugin_name = plugin["repo_path"].split("/")[-1]
    
    # Build optional HTML sections
    ref_html = f'<p><strong>Ref:</strong> <code>{plugin.get("ref", "")}</code></p>' if plugin.get("ref") else ""
    repo_path_html = f'<p><strong>Path:</strong> <code>{plugin.get("repo_path", "")}</code></p>' if plugin.get("repo_path") else ""
    message_html = f'<p><strong>Message:</strong> {message}</p>' if message else ""
    
    simple_url_section = SIMPLE_URL_SECTION if include_simple_url else ""
    
    return HTML_TEMPLATE.format(
        title=title,
        description=description,
        default_base_url=default_base_url,
        plugin_json=plugin_json,
        plugin_json_js=plugin_json_js,
        plugin_name=plugin_name,
        source=source,
        ref_html=ref_html,
        repo_path_html=repo_path_html,
        message_html=message_html,
        message_js=json.dumps(message),
        simple_url_section=simple_url_section,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML test pages for OpenHands plugins"
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
        "--title", "-t",
        help="Page title (default: derived from plugin name)"
    )
    parser.add_argument(
        "--description", "-d", default="Test page for launching this plugin with OpenHands",
        help="Page description"
    )
    parser.add_argument(
        "--base-url", "-u", default="https://app.all-hands.dev",
        help="Default base URL (default: https://app.all-hands.dev)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--parameters", "-P",
        help="JSON string of parameters to include"
    )
    parser.add_argument(
        "--no-simple-url", action="store_true",
        help="Don't include simple URL section"
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
    
    plugin = create_plugin_spec(args.source, args.ref, args.repo_path, parameters)
    
    # Derive title from plugin if not provided
    title = args.title
    if not title:
        source = plugin.get("source", "")
        plugin_name = source.split("/")[-1] if "/" in source else source
        if plugin.get("repo_path"):
            plugin_name = plugin["repo_path"].split("/")[-1]
        title = f"{plugin_name} Plugin Test"
    
    html = generate_test_page(
        plugin=plugin,
        title=title,
        description=args.description,
        message=args.message,
        default_base_url=args.base_url,
        include_simple_url=not args.no_simple_url,
    )
    
    if args.output:
        Path(args.output).write_text(html)
        print(f"Generated: {args.output}")
    else:
        print(html)


if __name__ == "__main__":
    main()
