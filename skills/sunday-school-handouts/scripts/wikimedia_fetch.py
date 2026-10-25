#!/usr/bin/env python3
"""Download Creative Commons / Public Domain images and license metadata from Wikimedia Commons.

Accepts Wikimedia Commons `File:...` titles, full wiki URLs, or `File:...=local_name.jpg`
mappings. Resolves direct image URLs and attribution/license metadata through the
MediaWiki API with compliant User-Agent headers and automatic rate-limit backoff.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "SundaySchoolCurriculumBot/1.0 (https://github.com/jpshackelford; educational use) Python-urllib/3"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    text = _TAG_RE.sub("", raw)
    return " ".join(html.unescape(text).split())


def normalize_file_title(spec: str) -> tuple[str, str | None]:
    """Parse 'File:Foo.jpg' or 'https://commons.../File:Foo.jpg=custom_name.jpg'."""
    custom_name: str | None = None
    if "=" in spec and not spec.startswith("http"):
        spec, custom_name = spec.split("=", 1)
    elif "=" in spec and spec.startswith("http"):
        # Check if '=' is an assignment at the end rather than query string
        last_eq = spec.rfind("=")
        if "title=" not in spec[last_eq - 6 : last_eq + 1]:
            spec, custom_name = spec[:last_eq], spec[last_eq + 1 :]

    spec = urllib.parse.unquote(spec.strip())
    if "File:" in spec:
        idx = spec.rfind("File:")
        title = spec[idx:]
    else:
        title = f"File:{spec}"
    # Normalize spaces
    title = title.replace("_", " ")
    return title, custom_name


def fetch_commons_info(file_title: str) -> dict[str, Any]:
    params = {
        "action": "query",
        "titles": file_title,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "format": "json",
    }
    url = f"{COMMONS_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1" or "imageinfo" not in page:
            raise ValueError(f"File not found on Wikimedia Commons: {file_title!r}")
        ii = page["imageinfo"][0]
        ext = ii.get("extmetadata", {})
        width = ii.get("width", 0)
        height = ii.get("height", 0)
        orientation = "landscape" if width >= height else "portrait"
        return {
            "title": page.get("title", file_title),
            "url": ii["url"],
            "descriptionurl": ii.get("descriptionurl", ""),
            "width": width,
            "height": height,
            "orientation": orientation,
            "mime": ii.get("mime", ""),
            "artist": _strip_html(ext.get("Artist", {}).get("value", "")),
            "credit": _strip_html(ext.get("Credit", {}).get("value", "")),
            "license_short": _strip_html(ext.get("LicenseShortName", {}).get("value", "")),
            "license_url": _strip_html(ext.get("LicenseUrl", {}).get("value", "")),
            "description": _strip_html(ext.get("ImageDescription", {}).get("value", "")),
        }
    raise ValueError(f"No imageinfo returned for: {file_title!r}")


def download_file(url: str, dest: Path, max_retries: int = 4) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    delay = 2.0
    for attempt in range(1, max_retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                dest.write_bytes(resp.read())
            return
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"HTTP {exc.code} downloading {url}: {exc.reason}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch Wikimedia Commons images and attribution metadata."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="Wikimedia Commons File title or URL (optional '=local_filename.jpg' suffix).",
    )
    parser.add_argument(
        "--out-dir",
        "-o",
        type=Path,
        default=Path("images"),
        help="Destination directory for downloaded images (default: ./images).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional path to write JSON metadata manifest (defaults to <out-dir>/attribution.json).",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Fetch metadata and dimensions without downloading the image binaries.",
    )

    args = parser.parse_args()
    manifest_path = args.manifest or (args.out_dir / "attribution.json")

    existing_manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            existing_manifest = {}

    results: list[dict[str, Any]] = []
    for idx, item in enumerate(args.files):
        if idx > 0:
            time.sleep(1.0)
        file_title, custom_name = normalize_file_title(item)
        info = fetch_commons_info(file_title)
        default_filename = file_title.removeprefix("File:").replace(" ", "_")
        local_name = custom_name or default_filename
        local_path = args.out_dir / local_name

        if not args.metadata_only:
            download_file(info["url"], local_path)
            info["local_path"] = str(local_path)
            info["size_bytes"] = local_path.stat().st_size

        existing_manifest[local_name] = info
        results.append(info)

    if not args.metadata_only:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(existing_manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
