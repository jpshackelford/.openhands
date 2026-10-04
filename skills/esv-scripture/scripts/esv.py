#!/usr/bin/env python3
"""Fetch ESV passage text with paragraph breaks and no verse numbers.

Supply an ESV API token in the ESV_API_KEY environment variable. For quotation
and publication rules, see https://www.crossway.org/permissions/ and
https://api.esv.org/; this client does not certify compliance for a work.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.esv.org/v3/passage/text/"


def fetch_esv_passage(
    reference: str,
    api_key: str,
    include_passage_references: bool = False,
    include_headings: bool = False,
    indent_paragraphs: int = 0,
    line_length: int = 0,
) -> str:
    params = {
        "q": reference,
        "include-verse-numbers": "false",
        "include-first-verse-numbers": "false",
        "include-passage-references": "true" if include_passage_references else "false",
        "include-headings": "true" if include_headings else "false",
        "include-footnotes": "false",
        "include-footnote-body": "false",
        "include-short-copyright": "true",
        "indent-paragraphs": str(indent_paragraphs),
        "line-length": str(line_length),
    }

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Token {api_key.strip()}", "User-Agent": "ESV-CLI-Tool/1.0"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_msg = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP Error {exc.code}: {exc.reason}\n{error_msg}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error connecting to ESV API: {exc.reason}") from exc

    passages = payload.get("passages", [])
    if not passages:
        raise ValueError(f"No passage found for reference: {reference!r}")
    return "\n\n".join(p.strip() for p in passages if p.strip())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch ESV Bible text with paragraph breaks preserved and verse numbers omitted."
    )
    parser.add_argument(
        "reference",
        nargs="+",
        help="Passage reference (e.g., 'John 11:35', 'Romans 8:28-39', 'Psalm 23').",
    )
    parser.add_argument(
        "--include-reference", "-r", action="store_true",
        help="Include the passage reference header before the text.",
    )
    parser.add_argument(
        "--include-headings", action="store_true", help="Include section headings."
    )
    parser.add_argument(
        "--indent-paragraphs", type=int, default=0,
        help="Number of spaces to indent paragraphs (default: 0).",
    )
    parser.add_argument(
        "--line-length", type=int, default=0,
        help="Maximum line length (default: 0, no wrapping).",
    )

    args = parser.parse_args()
    api_key = os.environ.get("ESV_API_KEY", "").strip()
    if not api_key:
        parser.error("ESV_API_KEY is required in the environment (see https://api.esv.org/)")

    try:
        text = fetch_esv_passage(
            reference=" ".join(args.reference),
            api_key=api_key,
            include_passage_references=args.include_reference,
            include_headings=args.include_headings,
            indent_paragraphs=args.indent_paragraphs,
            line_length=args.line_length,
        )
        print(text)
    except (RuntimeError, ValueError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
