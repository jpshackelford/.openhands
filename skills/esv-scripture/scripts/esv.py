#!/usr/bin/env python3
"""Fetch ESV passage text with paragraph breaks and no verse numbers.

Supply an ESV API token in the ESV_API_KEY environment variable. For quotation
and publication rules, see https://www.crossway.org/permissions/ and
https://api.esv.org/; this client does not certify compliance for a work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API_URL = "https://api.esv.org/v3/passage/text/"
_ESV_SUFFIX_RE = re.compile(r"\s*\(ESV\)\s*$")


def _read_cache(cache_dir: Path | None, cache_key: str) -> dict[str, Any] | None:
    if not cache_dir:
        return None
    cache_file = cache_dir / f"{cache_key}.json"
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
    return None


def _write_cache(cache_dir: Path | None, cache_key: str, payload: dict[str, Any]) -> None:
    if not cache_dir:
        return
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{cache_key}.json"
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def fetch_esv_payload(
    reference: str,
    api_key: str,
    include_passage_references: bool = False,
    include_headings: bool = False,
    indent_paragraphs: int = 0,
    line_length: int = 0,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
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

    cache_key = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode("utf-8")
    ).hexdigest()[:24]

    cached = _read_cache(cache_dir, cache_key)
    if cached is not None:
        return cached

    if not api_key or not api_key.strip():
        raise RuntimeError("ESV_API_KEY is required in the environment (see https://api.esv.org/)")

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Token {api_key.strip()}",
            "User-Agent": "ESV-CLI-Tool/1.0",
        },
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

    _write_cache(cache_dir, cache_key, payload)
    return payload


def fetch_esv_passage(
    reference: str,
    api_key: str,
    include_passage_references: bool = False,
    include_headings: bool = False,
    indent_paragraphs: int = 0,
    line_length: int = 0,
    cache_dir: Path | None = None,
) -> str:
    payload = fetch_esv_payload(
        reference=reference,
        api_key=api_key,
        include_passage_references=include_passage_references,
        include_headings=include_headings,
        indent_paragraphs=indent_paragraphs,
        line_length=line_length,
        cache_dir=cache_dir,
    )
    passages = payload.get("passages", [])
    return "\n\n".join(p.strip() for p in passages if p.strip())


def parse_clean_paragraphs(
    raw_text: str,
    canonical_ref: str = "",
    strip_reference_header: bool = True,
    strip_esv_suffix: bool = True,
) -> list[str]:
    """Split raw ESV passage text into clean paragraphs suitable for handout layout."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_text.strip()) if b.strip()]
    if (
        strip_reference_header
        and len(blocks) > 1
        and canonical_ref
        and blocks[0].lower().replace("–", "-") == canonical_ref.lower().replace("–", "-")
    ):
        blocks = blocks[1:]

    cleaned: list[str] = []
    for i, block in enumerate(blocks):
        # Collapse internal single newlines (from line wrapping) into spaces
        para = " ".join(line.strip() for line in block.splitlines() if line.strip())
        if strip_esv_suffix and i == len(blocks) - 1:
            para = _ESV_SUFFIX_RE.sub("", para).strip()
        if para:
            cleaned.append(para)
    return cleaned


def fetch_esv_structured(
    reference: str,
    api_key: str,
    include_headings: bool = False,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Fetch ESV passage and return structured JSON with canonical reference and paragraphs."""
    payload = fetch_esv_payload(
        reference=reference,
        api_key=api_key,
        include_passage_references=False,
        include_headings=include_headings,
        indent_paragraphs=0,
        line_length=0,
        cache_dir=cache_dir,
    )
    canonical = payload.get("canonical", reference)
    passages = payload.get("passages", [])
    raw_text = "\n\n".join(p.strip() for p in passages if p.strip())

    # Separate paragraphs per sub-passage or combined
    paragraphs = parse_clean_paragraphs(
        raw_text,
        canonical_ref=canonical,
        strip_reference_header=True,
        strip_esv_suffix=True,
    )
    passage_meta = payload.get("passage_meta", [])
    return {
        "query": reference,
        "canonical": canonical,
        "raw_text": raw_text,
        "paragraphs": paragraphs,
        "copyright": "(ESV)",
        "passage_meta": passage_meta,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch ESV Bible text with paragraph breaks preserved and verse numbers omitted."
    )
    parser.add_argument(
        "reference",
        nargs="*",
        help="Passage reference (e.g., 'John 11:35', 'Romans 8:28-39', 'Psalm 23').",
    )
    parser.add_argument(
        "--include-reference",
        "-r",
        action="store_true",
        help="Include the passage reference header before the text.",
    )
    parser.add_argument(
        "--include-headings",
        action="store_true",
        help="Include section headings.",
    )
    parser.add_argument(
        "--indent-paragraphs",
        type=int,
        default=0,
        help="Number of spaces to indent paragraphs (default: 0).",
    )
    parser.add_argument(
        "--line-length",
        type=int,
        default=0,
        help="Maximum line length (default: 0, no wrapping).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (default, includes '(ESV)' suffix) or 'json' (structured with clean paragraphs array and copyright metadata).",
    )
    parser.add_argument(
        "--batch",
        action="append",
        default=[],
        metavar="REF",
        help="Fetch multiple references in one invocation (can be passed multiple times; outputs JSON list when combined with --format json).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional directory to cache ESV API responses locally (respecting Crossway storage limits).",
    )

    args = parser.parse_args()
    api_key = os.environ.get("ESV_API_KEY", "").strip()

    queries: list[str] = list(args.batch)
    if args.reference:
        queries.append(" ".join(args.reference))

    if not queries:
        parser.error("Provide at least one passage reference or --batch <REF>.")

    try:
        if args.format == "json":
            results = [
                fetch_esv_structured(
                    reference=q,
                    api_key=api_key,
                    include_headings=args.include_headings,
                    cache_dir=args.cache_dir,
                )
                for q in queries
            ]
            out = results[0] if (len(results) == 1 and not args.batch) else results
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            outputs = [
                fetch_esv_passage(
                    reference=q,
                    api_key=api_key,
                    include_passage_references=args.include_reference,
                    include_headings=args.include_headings,
                    indent_paragraphs=args.indent_paragraphs,
                    line_length=args.line_length,
                    cache_dir=args.cache_dir,
                )
                for q in queries
            ]
            print("\n\n".join(outputs))
    except (RuntimeError, ValueError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
