#!/usr/bin/env python3
"""Render Sunday School scripture reading handouts to PDF with automatic page fitting.

Supports:
1. Rendering a JSON specification file directly to PDF (--pdf) and/or generating a
   standalone, self-contained Python generator script (--emit-py) matching the
   exact repository pattern (e.g., josiah_reform_and_the_law.py, zephaniah_day_of_the_lord.py).
2. Automatically fetching missing `paragraphs` from Crossway's ESV API via esv.py
   when `ESV_API_KEY` is set in the environment.
3. Automatically tuning CSS typography (font-size, line-height, section margins)
   using WeasyPrint's in-memory Document.pages so the handout fits `target_pages`
   cleanly without spilling a few orphan lines onto an extra page.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path
from typing import Any

# Ensure Homebrew library path is visible to ctypes/cffi on macOS before importing weasyprint
if sys.platform == "darwin":
    brew_lib_dir = "/opt/homebrew/lib"
    if os.path.exists(brew_lib_dir):
        current_dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if brew_lib_dir not in current_dyld.split(":"):
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
                f"{brew_lib_dir}:{current_dyld}" if current_dyld else brew_lib_dir
            )


# Candidate typography presets ordered from most spacious to most compact
STYLE_PRESETS: list[dict[str, Any]] = [
    {
        "name": "spacious",
        "font_size_pt": 10.5,
        "line_height": 1.46,
        "section_margin_px": 20,
        "para_margin_px": 10,
        "banner_margin_px": 22,
    },
    {
        "name": "standard",
        "font_size_pt": 10.2,
        "line_height": 1.44,
        "section_margin_px": 18,
        "para_margin_px": 9,
        "banner_margin_px": 18,
    },
    {
        "name": "balanced",
        "font_size_pt": 10.0,
        "line_height": 1.42,
        "section_margin_px": 16,
        "para_margin_px": 8,
        "banner_margin_px": 16,
    },
    {
        "name": "compact",
        "font_size_pt": 9.6,
        "line_height": 1.38,
        "section_margin_px": 14,
        "para_margin_px": 7,
        "banner_margin_px": 14,
    },
    {
        "name": "dense",
        "font_size_pt": 9.2,
        "line_height": 1.34,
        "section_margin_px": 12,
        "para_margin_px": 6,
        "banner_margin_px": 12,
    },
]

DEFAULT_ATTRIBUTION = (
    "<strong>Scripture quotations</strong> are from the ESV® Bible "
    "(The Holy Bible, English Standard Version®), copyright © 2001 by Crossway, "
    "a publishing ministry of Good News Publishers. Used by permission. "
    "All rights reserved."
)


def _find_esv_module() -> Path | None:
    """Locate esv.py relative to this script or in the workspace."""
    here = Path(__file__).resolve().parent
    candidates = [
        here.parent.parent / "esv-scripture" / "scripts" / "esv.py",
        Path.home() / ".gemini" / "config" / "skills" / "esv-scripture" / "scripts" / "esv.py",
        Path.home() / ".openhands" / "plugins" / "installed" / "esv-scripture" / "scripts" / "esv.py",
        Path.cwd() / "esv-cli" / "esv.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def resolve_passages(
    spec: dict[str, Any],
    cache_dir: Path | None = None,
) -> list[tuple[str, str, str, list[str]]]:
    """Resolve sections from spec into (title, reference, intro, paragraphs) tuples.

    If a section omits `paragraphs`, fetches them automatically using esv.py.
    """
    esv_script = _find_esv_module()
    esv_mod = None
    if esv_script is not None:
        import importlib.util

        spec_loader = importlib.util.spec_from_file_location("esv_cli_mod", esv_script)
        if spec_loader and spec_loader.loader:
            esv_mod = importlib.util.module_from_spec(spec_loader)
            sys.modules["esv_cli_mod"] = esv_mod
            spec_loader.loader.exec_module(esv_mod)

    api_key = os.environ.get("ESV_API_KEY", "").strip()
    passages: list[tuple[str, str, str, list[str]]] = []

    raw_sections = spec.get("sections") or spec.get("passages") or []
    for sec in raw_sections:
        title = sec["title"]
        reference = sec["reference"]
        intro = sec.get("intro") or sec.get("introduction") or ""
        paragraphs = sec.get("paragraphs")

        if not paragraphs:
            if esv_mod is None or not hasattr(esv_mod, "fetch_esv_structured"):
                raise RuntimeError(
                    f"Section {title!r} ({reference}) has no 'paragraphs' and esv.py could not be loaded."
                )
            # Normalize en-dashes to hyphens for API query
            api_query = reference.replace("–", "-")
            result = esv_mod.fetch_esv_structured(
                reference=api_query,
                api_key=api_key,
                include_headings=False,
                cache_dir=cache_dir,
            )
            paragraphs = result["paragraphs"]

        passages.append((title, reference, intro, list(paragraphs)))

    return passages


def build_html(
    title: str,
    subtitle: str,
    running_header: str,
    passages: list[tuple[str, str, str, list[str]]],
    preset: dict[str, Any] | None = None,
    attribution_html_inner: str = DEFAULT_ATTRIBUTION,
) -> str:
    p = preset or STYLE_PRESETS[2]
    sections = []
    for sec_title, reference, introduction, paragraphs in passages:
        reading = "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        sections.append(
            f'<section class="reading-section">'
            f'<div class="section-lead">'
            f"<h2>{escape(sec_title)} <span>{escape(reference)}</span></h2>"
            f'<div class="reading-intro">{escape(introduction)}</div>'
            f"</div>{reading}</section>"
        )

    attribution_html = f"""
<footer class="attribution-box">
    <div class="attribution-text">
        {attribution_html_inner}
    </div>
</footer>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
    @page {{
        size: letter portrait;
        margin: 14mm 16mm 16mm 16mm;
        background-color: #FAFAF7;
        @top-left {{
            content: "{escape(running_header)}";
            font-family: 'Times New Roman', serif;
            font-size: 7.5pt;
            letter-spacing: 1px;
            color: #64748B;
            border-bottom: 0.5pt solid #CBD5E1;
            padding-bottom: 4px;
        }}
        @bottom-right {{
            content: "Page " counter(page);
            font-family: 'Times New Roman', serif;
            font-size: 7.5pt;
            color: #64748B;
            border-top: 0.5pt solid #CBD5E1;
            padding-top: 4px;
        }}
    }}

    *, *::before, *::after {{ box-sizing: border-box; }}
    body {{
        margin: 0; padding: 0;
        font-family: 'Georgia', 'Times New Roman', serif;
        color: #1E293B; background-color: #FAFAF7;
    }}
    .title-banner {{
        background-color: #0F172A; color: #F8FAFC;
        padding: 16px 20px 14px 20px; margin-bottom: {p['banner_margin_px']}px;
        border-radius: 4px; border-bottom: 3px solid #991B1B;
    }}
    .title-banner h1 {{
        margin: 0 0 4px 0; font-size: 16pt; font-weight: 700;
        letter-spacing: 0.5px; color: #FFFFFF;
        text-transform: uppercase;
    }}
    .title-banner .subtitle {{
        font-size: 9pt; color: #CBD5E1; margin: 0;
        line-height: 1.3; font-style: italic;
    }}

    .scripture-reading {{
        font-size: {p['font_size_pt']}pt;
        line-height: {p['line_height']};
        column-count: 2;
        column-gap: 30px;
        column-rule: 1px solid #E2E8F0;
    }}

    .reading-section {{
        margin-bottom: {p['section_margin_px']}px;
        orphans: 4;
        widows: 4;
    }}
    .section-lead {{ break-inside: avoid; break-after: avoid; }}

    .reading-section h2 {{
        font-size: 11pt; line-height: 1.3;
        color: #991B1B; margin: 0 0 7px 0;
    }}
    .reading-section h2 span {{
        font-size: 8.5pt; font-weight: normal; color: #64748B;
        display: block; margin-top: 2px;
    }}
    .reading-intro {{
        font-size: 9pt; line-height: 1.38; color: #475569;
        border-left: 2px solid #CBD5E1;
        padding-left: 10px; margin-bottom: 11px;
        font-style: italic;
    }}
    .reading-section p {{
        margin: 0 0 {p['para_margin_px']}px;
        text-align: justify;
    }}

    .attribution-box {{
        margin-top: 20px;
        padding: 12px 16px;
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 3px solid #0F172A;
        border-radius: 4px;
        display: flex;
        align-items: center;
        gap: 20px;
        break-inside: avoid;
    }}
    .attribution-text {{
        font-size: 8pt;
        line-height: 1.35;
        color: #475569;
    }}
</style>
</head>
<body>
<div class="title-banner">
    <h1>{escape(title)}</h1>
    <div class="subtitle">{escape(subtitle)}</div>
</div>
<div class="scripture-reading">
{"".join(sections)}
</div>
{attribution_html}
</body>
</html>
"""


def render_pdf_with_autofit(
    title: str,
    subtitle: str,
    running_header: str,
    passages: list[tuple[str, str, str, list[str]]],
    output_pdf: Path,
    target_pages: int | None = 2,
) -> tuple[dict[str, Any], int]:
    """Render PDF with WeasyPrint, stepping through presets if target_pages is specified."""
    import weasyprint

    chosen_preset = STYLE_PRESETS[0]
    chosen_doc = None

    for preset in STYLE_PRESETS:
        html_str = build_html(
            title=title,
            subtitle=subtitle,
            running_header=running_header,
            passages=passages,
            preset=preset,
        ).replace("\u00a0", " ")
        doc = weasyprint.HTML(string=html_str).render()
        chosen_preset = preset
        chosen_doc = doc
        if target_pages is None or len(doc.pages) <= target_pages:
            break

    assert chosen_doc is not None
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    chosen_doc.write_pdf(output_pdf)
    return chosen_preset, len(chosen_doc.pages)


def emit_standalone_py(
    title: str,
    subtitle: str,
    running_header: str,
    passages: list[tuple[str, str, str, list[str]]],
    preset: dict[str, Any],
    output_py: Path,
    pdf_filename: str,
) -> None:
    """Emit a clean, self-contained Python script matching the repo convention."""
    passages_Formatted = "[\n"
    for sec_title, ref, intro, paras in passages:
        passages_Formatted += "    (\n"
        passages_Formatted += f"        {json.dumps(sec_title, ensure_ascii=False)},\n"
        passages_Formatted += f"        {json.dumps(ref, ensure_ascii=False)},\n"
        passages_Formatted += f"        {json.dumps(intro, ensure_ascii=False)},\n"
        passages_Formatted += "        [\n"
        for para in paras:
            passages_Formatted += f"            {json.dumps(para, ensure_ascii=False)},\n"
        passages_Formatted += "        ],\n"
        passages_Formatted += "    ),\n"
    passages_Formatted += "]"

    code = f'''from html import escape
import os
from pathlib import Path
import sys

# Ensure Homebrew library path is visible to ctypes/cffi on macOS
if sys.platform == "darwin":
    brew_lib_dir = "/opt/homebrew/lib"
    if os.path.exists(brew_lib_dir):
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
            brew_lib_dir + ":" + os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        )

import weasyprint


lesson_dir = Path(__file__).resolve().parent

passages = {passages_Formatted}

sections = []
for title, reference, introduction, paragraphs in passages:
    reading = "\\n".join(f"<p>{{escape(paragraph)}}</p>" for paragraph in paragraphs)
    sections.append(
        f'<section class="reading-section">'
        f'<div class="section-lead">'
        f'<h2>{{escape(title)}} <span>{{escape(reference)}}</span></h2>'
        f'<div class="reading-intro">{{escape(introduction)}}</div>'
        f"</div>{{reading}}</section>"
    )

attribution_html = """
<footer class="attribution-box">
    <div class="attribution-text">
        <strong>Scripture quotations</strong> are from the ESV® Bible
        (The Holy Bible, English Standard Version®), copyright © 2001 by Crossway,
        a publishing ministry of Good News Publishers. Used by permission.
        All rights reserved.
    </div>
</footer>
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
    @page {{{{
        size: letter portrait;
        margin: 14mm 16mm 16mm 16mm;
        background-color: #FAFAF7;
        @top-left {{{{
            content: "{escape(running_header)}";
            font-family: 'Times New Roman', serif;
            font-size: 7.5pt;
            letter-spacing: 1px;
            color: #64748B;
            border-bottom: 0.5pt solid #CBD5E1;
            padding-bottom: 4px;
        }}}}
        @bottom-right {{{{
            content: "Page " counter(page);
            font-family: 'Times New Roman', serif;
            font-size: 7.5pt;
            color: #64748B;
            border-top: 0.5pt solid #CBD5E1;
            padding-top: 4px;
        }}}}
    }}}}

    *, *::before, *::after {{{{ box-sizing: border-box; }}}}
    body {{{{
        margin: 0; padding: 0;
        font-family: 'Georgia', 'Times New Roman', serif;
        color: #1E293B; background-color: #FAFAF7;
    }}}}
    .title-banner {{{{
        background-color: #0F172A; color: #F8FAFC;
        padding: 16px 20px 14px 20px; margin-bottom: {preset['banner_margin_px']}px;
        border-radius: 4px; border-bottom: 3px solid #991B1B;
    }}}}
    .title-banner h1 {{{{
        margin: 0 0 4px 0; font-size: 16pt; font-weight: 700;
        letter-spacing: 0.5px; color: #FFFFFF;
        text-transform: uppercase;
    }}}}
    .title-banner .subtitle {{{{
        font-size: 9pt; color: #CBD5E1; margin: 0;
        line-height: 1.3; font-style: italic;
    }}}}

    .scripture-reading {{{{
        font-size: {preset['font_size_pt']}pt;
        line-height: {preset['line_height']};
        column-count: 2;
        column-gap: 30px;
        column-rule: 1px solid #E2E8F0;
    }}}}

    .reading-section {{{{
        margin-bottom: {preset['section_margin_px']}px;
        orphans: 4;
        widows: 4;
    }}}}
    .section-lead {{{{ break-inside: avoid; break-after: avoid; }}}}

    .reading-section h2 {{{{
        font-size: 11pt; line-height: 1.3;
        color: #991B1B; margin: 0 0 7px 0;
    }}}}
    .reading-section h2 span {{{{
        font-size: 8.5pt; font-weight: normal; color: #64748B;
        display: block; margin-top: 2px;
    }}}}
    .reading-intro {{{{
        font-size: 9pt; line-height: 1.38; color: #475569;
        border-left: 2px solid #CBD5E1;
        padding-left: 10px; margin-bottom: 11px;
        font-style: italic;
    }}}}
    .reading-section p {{{{
        margin: 0 0 {preset['para_margin_px']}px;
        text-align: justify;
    }}}}

    .attribution-box {{{{
        margin-top: 20px;
        padding: 12px 16px;
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-left: 3px solid #0F172A;
        border-radius: 4px;
        display: flex;
        align-items: center;
        gap: 20px;
        break-inside: avoid;
    }}}}
    .attribution-text {{{{
        font-size: 8pt;
        line-height: 1.35;
        color: #475569;
    }}}}
</style>
</head>
<body>
<div class="title-banner">
    <h1>{escape(title)}</h1>
    <div class="subtitle">{escape(subtitle)}</div>
</div>
<div class="scripture-reading">
{{"".join(sections)}}
</div>
{{attribution_html}}
</body>
</html>
"""

output_pdf = lesson_dir / "{pdf_filename}"
clean_html = html.replace("\\u00a0", " ")
weasyprint.HTML(string=clean_html).write_pdf(output_pdf)
print(f"Generated {{output_pdf}}")
'''
    output_py.parent.mkdir(parents=True, exist_ok=True)
    output_py.write_text(code, encoding="utf-8")


def _reexec_in_venv_if_needed() -> None:
    """If weasyprint is not importable in current python, auto-discover ./bin/python."""
    try:
        import weasyprint  # noqa: F401
        return
    except ImportError:
        pass

    candidates = [
        Path.cwd() / "bin" / "python",
        Path.home() / "code" / "jpshackelford" / "sunday-school-2026-27" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            if Path(sys.executable).resolve() != candidate.resolve():
                os.execv(str(candidate), [str(candidate), *sys.argv])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a Sunday School scripture reading handout from a JSON spec."
    )
    parser.add_argument(
        "spec",
        type=Path,
        help="Path to the JSON reading spec file.",
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=None,
        help="Output PDF file path (defaults to <spec_stem>.pdf in the spec's directory).",
    )
    parser.add_argument(
        "--emit-py",
        type=Path,
        default=None,
        help="Optional path to emit a standalone Python generator script (<name>.py) with embedded ESV paragraphs and auto-fitted CSS.",
    )
    parser.add_argument(
        "--target-pages",
        type=int,
        default=None,
        help="Target maximum page count for automatic typography fitting (default: 2, or spec's target_pages).",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Optional directory to cache ESV API responses.",
    )

    args = parser.parse_args()
    _reexec_in_venv_if_needed()

    spec_data = json.loads(args.spec.read_text(encoding="utf-8"))
    title = spec_data["title"]
    subtitle = spec_data["subtitle"]
    running_header = spec_data.get("running_header", title.upper())
    target_pages = (
        args.target_pages
        if args.target_pages is not None
        else spec_data.get("target_pages", 2)
    )

    output_pdf = args.pdf or args.spec.with_suffix(".pdf")
    passages = resolve_passages(spec_data, cache_dir=args.cache_dir)

    preset, page_count = render_pdf_with_autofit(
        title=title,
        subtitle=subtitle,
        running_header=running_header,
        passages=passages,
        output_pdf=output_pdf,
        target_pages=target_pages,
    )
    print(
        f"Rendered {output_pdf} ({page_count} pages, preset={preset['name']!r}, "
        f"font={preset['font_size_pt']}pt, line_height={preset['line_height']})"
    )

    if args.emit_py:
        emit_standalone_py(
            title=title,
            subtitle=subtitle,
            running_header=running_header,
            passages=passages,
            preset=preset,
            output_py=args.emit_py,
            pdf_filename=output_pdf.name,
        )
        print(f"Emitted standalone script {args.emit_py}")


if __name__ == "__main__":
    main()
