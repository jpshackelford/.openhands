#!/usr/bin/env python3
"""Inspect PDF page count, per-page text density, spillover warnings, and render PNG previews.

Uses poppler utilities (`pdfinfo`, `pdftotext`, `pdftoppm`) if available, with
automatic fallback to `pypdf`. Zero virtualenv headaches: runs under any system
or project Python 3 interpreter.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _get_page_count_pdfinfo(pdf_path: Path) -> int | None:
    if not shutil.which("pdfinfo"):
        return None
    res = subprocess.run(
        ["pdfinfo", str(pdf_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return None
    for line in res.stdout.splitlines():
        if line.startswith("Pages:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _get_pages_text_pdftotext(pdf_path: Path, page_count: int) -> list[str] | None:
    if not shutil.which("pdftotext"):
        return None
    pages: list[str] = []
    for p in range(1, page_count + 1):
        res = subprocess.run(
            ["pdftotext", "-f", str(p), "-l", str(p), str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return None
        pages.append(res.stdout)
    return pages


def _get_pages_pypdf(pdf_path: Path) -> list[str]:
    import pypdf  # type: ignore

    reader = pypdf.PdfReader(str(pdf_path))
    return [page.extract_text() or "" for page in reader.pages]


def inspect_pdf(
    pdf_path: Path,
    expect_pages: int | None = None,
    preview_dir: Path | None = None,
    dpi: int = 150,
) -> dict[str, Any]:
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    page_count = _get_page_count_pdfinfo(pdf_path)
    pages_text: list[str] | None = None
    if page_count is not None:
        pages_text = _get_pages_text_pdftotext(pdf_path, page_count)

    if pages_text is None:
        pages_text = _get_pages_pypdf(pdf_path)
        page_count = len(pages_text)

    page_stats: list[dict[str, Any]] = []
    warnings: list[str] = []

    for idx, text in enumerate(pages_text, start=1):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        # Exclude running header and "Page N" footer from substantive char count
        body_lines = [
            line
            for line in lines
            if not re.fullmatch(r"Page\s+\d+", line)
        ]
        char_count = sum(len(line) for line in body_lines)
        word_count = sum(len(line.split()) for line in body_lines)
        first_line = body_lines[0] if body_lines else ""
        last_line = body_lines[-1] if body_lines else ""

        page_stats.append(
            {
                "page": idx,
                "lines": len(body_lines),
                "words": word_count,
                "chars": char_count,
                "first_line": first_line[:90],
                "last_line": last_line[:90],
            }
        )

        if idx > 1 and char_count < 350:
            warnings.append(
                f"Page {idx} has very low text density ({char_count} chars, {word_count} words) — likely an unintended spillover page."
            )

    if expect_pages is not None and page_count != expect_pages:
        warnings.append(
            f"Expected {expect_pages} page(s), but PDF has {page_count} page(s)."
        )

    previews: list[str] = []
    if preview_dir is not None:
        if not shutil.which("pdftoppm"):
            warnings.append("pdftoppm not found on PATH; skipped PNG preview generation.")
        else:
            preview_dir.mkdir(parents=True, exist_ok=True)
            prefix = preview_dir / pdf_path.stem
            res = subprocess.run(
                ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                previews = sorted(
                    str(p) for p in preview_dir.glob(f"{pdf_path.stem}-*.png")
                )
            else:
                warnings.append(f"pdftoppm failed: {res.stderr.strip()}")

    return {
        "file": str(pdf_path),
        "size_bytes": pdf_path.stat().st_size,
        "pages": page_count,
        "expected_pages": expect_pages,
        "ok": len(warnings) == 0,
        "warnings": warnings,
        "page_stats": page_stats,
        "previews": previews,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect PDF page count, per-page text density, and optionally render PNG previews."
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF file to inspect.")
    parser.add_argument(
        "--expect-pages",
        type=int,
        default=None,
        help="Expected page count (exits non-zero if actual page count differs or spillover is detected).",
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        default=None,
        help="Optional directory to render PNG page previews using pdftoppm.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Resolution for pdftoppm PNG previews (default: 150).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output inspection report as JSON.",
    )

    args = parser.parse_args()
    try:
        report = inspect_pdf(
            pdf_path=args.pdf,
            expect_pages=args.expect_pages,
            preview_dir=args.preview_dir,
            dpi=args.dpi,
        )
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"PDF: {report['file']} ({report['size_bytes']:,} bytes)")
        print(f"Total Pages: {report['pages']}")
        for ps in report["page_stats"]:
            print(
                f"  Page {ps['page']}: {ps['lines']} lines, {ps['words']} words, {ps['chars']} chars"
                f" | start={ps['first_line']!r} ... end={ps['last_line']!r}"
            )
        if report["previews"]:
            print(f"Rendered {len(report['previews'])} preview PNG(s):")
            for p in report["previews"]:
                print(f"  {p}")
        if report["warnings"]:
            print("WARNINGS:")
            for w in report["warnings"]:
                print(f"  ! {w}")

    if args.expect_pages is not None and not report["ok"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
